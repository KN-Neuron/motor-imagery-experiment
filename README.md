# Motor Imagery Experiment

A desktop application for BCI (Brain-Computer Interface) experiments using the BrainAccess EEG headset. Collects EEG data during calibration and experiment sessions based on motor imagery, SSVEP, and other paradigms. Built by KN Neuron student research group.

## Features

- **Calibration** -- displays sequences of visual cues (hand clench, blink, head movement, SSVEP) and records EEG responses. After each cue, a classifier provides feedback (currently random -- real model to be integrated).
- **Experiment** -- runs sessions with selected cues, recording a continuous EEG stream.
- **Data export** -- continuous EEG recording to EDF+ format with built-in annotations and a BIDS-style events TSV.

## Requirements

- Python 3.13+
- Poetry
- BrainAccess SDK (`brainaccess` 3.6.1) -- for headset communication
- BrainAccess headset (HALO 4CH, MIDI 16CH, MAXI 32CH or SAMPLE 64CH) -- optional, the app also works in mock mode

## Installation

```bash
git clone https://github.com/KN-Neuron/motor-imagery-experiment.git
cd motor-imagery-experiment
poetry install
```

To also install development tools (black, flake8, mypy):

```bash
poetry install --with dev
```

## Running

```bash
poetry run python -m src.main
```

The app starts in the main menu, with no headset connected. From there:

1. Pick a model from the dropdown (populated from `brainaccess.config.yaml`).
2. Optionally tick **Use mock driver** to run on synthetic data with that model's channel layout.
3. Click **Connect**. This is synchronous -- the UI may freeze for a few seconds while the SDK negotiates Bluetooth.

Once connected, you can start a calibration or experiment session. The headset can be swapped at any time (Disconnect → change selection → Connect) without restarting the app. If Bluetooth drops mid-session, the app writes a `DISCONNECTED` marker into the EDF, returns to the menu, and you can reconnect from there.

### No-headset mode (Alt-shortcut)

For UI smoke tests without any driver, hold **Alt** while clicking Start Experiment / Start Calibration. The session runs without an EEG stream: no EDF output, the classifier returns random predictions. For a more realistic dry-run with valid EDF output, use the **Use mock driver** checkbox in the menu instead.

## Configuration

Both runtime config files (`trials.config.yaml`, `brainaccess.config.yaml`) are gitignored. Copy them from the committed templates on first setup:

```bash
cp trials.example.config.yaml trials.config.yaml
cp brainaccess.example.config.yaml brainaccess.config.yaml
```

### `trials.config.yaml`

Main configuration file for experiment and calibration sessions:

```yaml
experiment:
  trials_per_class: 5        # repetitions per cue type
  strategy: stratified        # stratified | random
  fixation_ms: 700            # fixation cross duration
  cue_ms: 2000                # cue (motor imagery task) duration
  rest_ms: 700                # rest period between trials
  cues:                       # active cue types
    - double_blink
    - left_hand_clench
    - right_hand_clench
    - jaw_clench
    - head_movement
    - ssvep_focus

calibration:
  trials_per_class: 3
  strategy: stratified
  fixation_ms: 700
  cue_ms: 700
  rest_ms: 700
  result_ms: 500              # classification result display duration
  cues:
    - head_movement
    - ssvep_focus
```

All parameters can also be adjusted in the config dialog at session start (including cue selection via checkboxes and a custom session folder name).

### `brainaccess.config.yaml`

Per-model headset configuration -- the file lists every headset variant the app can use, with channel-to-position mapping (10-20 system), channel count, and sample rate. The main-menu dropdown is populated from this file at runtime.

```yaml
headsets:
  HALO_4CH:
    device_name: "BA HALO 001"     # exact BLE name from the device label / Windows Bluetooth
    n_channels: 4
    sample_rate_hz: 250
    channel_map: {0: "Fp1", 1: "Fp2", 2: "O1", 3: "O2"}

  MIDI_16CH_BASE:
    device_name: "BA MIDI 026"
    n_channels: 16
    sample_rate_hz: 250
    channel_map: {0: "Fp1", 1: "Fp2", ..., 15: "F8"}

  MAXI_32CH:
    device_name: "BA MAXI XXX"     # replace XXX with the serial from the device label
    n_channels: 32
    sample_rate_hz: 250
    channel_map: {0: "Fp1", 1: "Fp2", 2: "AF3", ..., 31: "O2"}

  SAMPLE_64CH:
    device_name: "Sample 64-Channel Headset"
    n_channels: 64
    sample_rate_hz: 250
    channel_map: {0: "Fp1", 1: "Fp2", ..., 63: "PO4"}
```

**Field semantics:**

- `device_name` -- the Bluetooth advertising name; the SDK matches against this string verbatim. Check the device label and your OS Bluetooth pairing list. Mismatch -> `connect()` fails.
- `n_channels` -- must equal the length of `channel_map` (validated on load).
- `sample_rate_hz` -- on Maxi/MIDI hardware this is fixed to 250 Hz by SDK; HALO/MINI also support 500 Hz.
- `channel_map` -- ordered map of hardware index -> 10-20 electrode position. Order must match the physical electrode layout of your specific cap, otherwise EDF channel labels will be misaligned with the recorded signal.

**Adding a new headset model** requires two changes:

1. Add the entry under `headsets:` in `brainaccess.config.yaml` (and the corresponding template in `brainaccess.example.config.yaml`).
2. Add a matching value to `HeadsetModel` enum in [`src/eeg_headset/headset_config.py`](src/eeg_headset/headset_config.py). The dropdown only shows models present in *both* the YAML and the enum.

## Keyboard shortcuts

| Shortcut | Action |
|----------|--------|
| ESC      | Abort calibration/experiment (available when paused) |
| Q        | Quit the application (available in main menu) |
| Pause    | Sidebar button |

## Output data

Sessions are saved to the `sessions/` directory:

```
sessions/
  calibrations/
    2026-03-28_12-23-05/      # or custom name from config dialog
      session.edf             # continuous EEG recording (EDF+ with annotations)
      events.tsv              # markers in BIDS format (onset, duration, trial_type)
  experiments/
    my-session/
      session.edf
      events.tsv
```

### EDF+ format (`session.edf`)

EDF+ is the standard EEG container, readable by MNE-Python, EEGLAB, FieldTrip, EDFbrowser. `SessionSaver` writes the file incrementally during the session. Physical range is +/-3200 uV at 16-bit resolution.

Annotations embedded in the file include trial phase markers (`FIXATION`, `REST`, step-type names like `LEFT_HAND_CLENCH`), session boundaries (`experiment_start` / `calibration_start`), pause events (`PAUSED` / `RESUMED`), classifier feedback in calibration (`RESULT_<class>`), and `DISCONNECTED` if the headset drops mid-session. Onsets are computed from `sample_idx / sample_rate`, so they are free of OS scheduler jitter and aligned with the recorded signal at sample-rate precision.

Reading with MNE-Python:
```python
import mne
raw = mne.io.read_raw_edf("sessions/calibrations/.../session.edf")
print(raw.info)
print(raw.annotations)
```

### events.tsv (BIDS format)

Tab-separated event list following the [BIDS](https://bids-specification.readthedocs.io/) events convention. Generated alongside the EDF on session stop.

```
onset     duration  trial_type
0.000     0.700     FIXATION
0.700     2.000     LEFT_HAND_CLENCH
2.700     0.700     REST
```

`duration` is computed as the gap to the next marker (or the session end for the last entry). Onsets are aligned with EDF annotations -- both come from the same `(sample_idx, label)` list.

---

## Architecture

### Project structure

```
src/
  main.py                              # Entry point (creates GUIManager + FlowController)
  trials_config/trials_config.py       # YAML config loader + dataclasses

  flow_controller/
    flow_controller.py                 # Main loop (QTimer 10ms tick), state machine, owns eeg_headset
    states/
      flow_state.py                    # Base state class (enter/tick/exit lifecycle)
      main_menu_state.py               # Main menu: headset selection, connect/disconnect, session entry
      calibration_state.py             # Calibration: cue -> classify -> show result
      experiment_state.py              # Experiment: cue -> record
    session_saver/
      session_saver.py                 # Continuous EEG-to-EDF writer + markers + events TSV

  eeg_headset/
    eeg_headset.py                     # Headset interface (poll, subscribe, annotate)
    ring_buffer.py                     # Circular buffer for EEG samples
    headset_config.py                  # HeadsetModel enum + YAML config loader
    cmd/demo.py                        # Standalone CLI demo of EEG capture
    drivers/
      headset_driver.py                # Protocol (interface) for drivers
      brainaccess.py                   # BrainAccess SDK driver (delegates is_connected/is_streaming to SDK)
      mock.py                          # Mock driver (synthetic EEG data)
      playback.py                      # Replay driver (plays back recorded EEG)

  sample_manager/
    sample_manager.py                  # Trial sequence generator (FIXATION -> CUE -> REST)
    experiment_step_type.py            # Step type enum + CLASSIFIABLE constant
    sampling_strategies.py             # StratifiedSampler, RandomSampler

  gui/
    gui_manager.py                     # GUI coordinator, view switching
    views/
      view.py                          # Base view class (shortcuts, events)
      main_menu_view.py                # Main menu view (model dropdown + connect/disconnect)
      experiment_view.py               # Experiment view
      calibration_view.py              # Calibration view (+ classification result)
      utils/pixmap_cache.py            # Cached image loader for cue assets
    dialogs/
      _shared.py                       # Shared dialog styles + layout helpers
      _cues.py                         # Cue checkbox helpers (used by experiment + calibration dialogs)
      experiment_config_dialog.py      # Experiment session setup
      calibration_config_dialog.py     # Calibration session setup
    shared/
      button.py                        # Styled button widget
      sidebar.py                       # Side panel (fullscreen, pause, quit)
```

### Flow Controller -- state machine

The core of the application. `FlowController` runs a QTimer with a 10ms tick (100 FPS). Each tick:

1. `eeg_headset.poll()` -- reads new samples and forwards them to subscribers (only when the headset is set, connected and streaming)
2. `current_state.tick()` -- the current state processes GUI events and manages transitions

States follow the `enter(**kwargs)` -> `tick()` (repeated) -> `exit()` lifecycle. Transitions happen via `change_state(state, **kwargs)`; kwargs are forwarded to `enter()`. Each state reads what it needs (e.g. `kwargs.get("no_eeg_mode", False)` in session states) and ignores the rest.

```
MainMenuState  -->  CalibrationState  -->  MainMenuState
               -->  ExperimentState   -->  MainMenuState
```

**Headset ownership.** `FlowController.eeg_headset` is `Optional[EEGHeadset]` and starts as `None`. Only `MainMenuState` mutates it: building a driver from the dropdown selection on Connect, clearing it on Disconnect. Session states read it through the live property `FlowState.eeg_headset` (re-resolved per access, not cached at state construction), so a swap in the menu is immediately visible to the next state.

If the headset's SDK reports disconnection during a session (`BrainAccessDriver.is_connected` delegates to `EEGManager.is_connected()` from the SDK), the session state writes a `DISCONNECTED` marker, finalizes the EDF, and transitions back to the main menu. The user can reconnect and start a new session without restarting the app.

### EEG Headset -- subscriber pattern

`EEGHeadset` abstracts the headset behind a `HeadsetDriver` protocol. Data from `poll()` flows to:

- **RingBuffer** -- circular buffer holding the last N seconds (for on-demand slice reads)
- **Subscribers** -- callbacks registered via `add_subscriber()`. SessionSaver registers as a subscriber and writes each chunk to EDF in real time.

Drivers:
- `BrainAccessDriver` -- real BrainAccess headset
- `MockDriver` -- generates synthetic EEG data (alpha-band sine waves + Gaussian noise, +/-60 uV range)

### Session Saver -- continuous EDF recording

`SessionSaver` registers as a subscriber on `EEGHeadset`. Each data chunk from `poll()` is immediately buffered and flushed to EDF once a full record (1 second) is ready. States only call `add_marker(label)` on step transitions -- the marker records the current sample index.

```
poll() -> chunk -> SessionSaver.on_chunk() -> buffer -> EDF (every 1s)
state.tick() -> add_marker("LEFT_HAND") -> marker list -> EDF annotations + events.tsv
```

On `stop_session()`, remaining samples are flushed, annotations are written to EDF, and events.tsv is generated.

### Sample Manager -- trial generation

`SampleManager` generates step sequences based on configuration. Each trial consists of a triplet:

```
FIXATION (fixation cross) -> CUE (motor imagery task) -> REST (rest period)
```

Sampling strategies:
- **StratifiedSampler** -- equal count of each cue type, then shuffled
- **RandomSampler** -- purely random cue selection

### GUI -- PyQt6 with QPainter

The interface is built on `QStackedWidget` (fast view switching) with a side panel (`Sidebar`). Views are rendered via `paintEvent()` using QPainter -- no .ui files. Dark theme (purple/blue).

GUI-to-State communication: views maintain a `pending_events` list, states poll it in `tick()` (event queue instead of Qt signals -- simpler flow control).

## Development

### Tests

```bash
poetry run pytest                  # all tests
poetry run pytest -m unit          # unit tests
poetry run pytest -m integration   # integration tests
```

### Formatting and linting

```bash
poetry run black src/ tests/       # formatting
poetry run flake8 src/ tests/      # lint
poetry run mypy src/               # type check
```

### Pre-commit hooks

```bash
pre-commit install
```

Hooks automatically run black, flake8, and mypy before each commit.

### CI/CD

GitHub Actions:
- **python-ci.yml** -- formatting, linting, type checking, tests + coverage
- **pre-commit.yml** -- hook verification
- **security-scan.yml** -- dependency scanning (weekly)
