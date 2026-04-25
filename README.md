# Hex-O-Spell Experiment

A desktop application for BCI (Brain-Computer Interface) experiments using the BrainAccess EEG headset. Collects EEG data during calibration and experiment sessions based on motor imagery, SSVEP, and other paradigms. Built by KN Neuron student research group.

## Features

- **Calibration** -- displays sequences of visual cues (hand clench, blink, head movement, SSVEP) and records EEG responses. After each cue, a classifier provides feedback (currently random -- real model to be integrated).
- **Experiment** -- runs sessions with selected cues, recording a continuous EEG stream.
- **Data export** -- continuous EEG recording to EDF+ format with built-in annotations and a BIDS-style events TSV.

## Requirements

- Python 3.13+
- Poetry
- BrainAccess SDK (`brainaccess` 3.6.1) -- for headset communication
- BrainAccess headset (HALO 4CH or MIDI 16CH) -- optional, the app also works in mock mode

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

### No-headset mode

If no headset is connected, you can start calibration/experiment by holding **Alt** while clicking the Start button. The app will use a MockDriver that generates synthetic EEG data -- all UI and logic work identically.

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

Headset model configuration -- channel-to-position mapping (10-20 system), sample rate:

```yaml
headsets:
  HALO_4CH:
    device_name: "BA HALO 001"
    n_channels: 4
    sample_rate_hz: 250
    channel_map: {0: "Fp1", 1: "Fp2", 2: "O1", 3: "O2"}

  MIDI_16CH_BASE:
    device_name: "BA MIDI 026"
    n_channels: 16
    sample_rate_hz: 250
    channel_map: {0: "Fp1", 1: "Fp2", ..., 15: "F8"}
```

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

### EDF+ format

- Continuous recording of all EEG channels
- Annotations embedded in the file (label + onset in seconds)
- Physical range: +/-3200 uV, 16-bit resolution
- Reading with MNE-Python:
  ```python
  import mne
  raw = mne.io.read_raw_edf("sessions/calibrations/.../session.edf")
  print(raw.info)
  print(raw.annotations)
  ```

### events.tsv (BIDS format)

```
onset     duration  trial_type
0.000     0.700     FIXATION
0.700     2.000     LEFT_HAND_CLENCH
2.700     0.700     REST
```

Onsets and durations are computed from precise sample indices (sample_idx / sample_rate).

---

## Architecture

### Project structure

```
src/
  main.py                              # Entry point
  config/config.py                     # YAML config loader + dataclasses

  flow_controller/
    flow_controller.py                 # Main loop (QTimer 10ms tick), state machine
    states/
      flow_state.py                    # Base state class (enter/tick/exit lifecycle)
      main_menu_state.py               # Main menu handling
      calibration_state.py             # Calibration: cue -> classify -> show result
      experiment_state.py              # Experiment: cue -> record
    session_saver/
      session_saver.py                 # Continuous EEG-to-EDF writer + markers + events TSV

  eeg_headset/
    eeg_headset.py                     # Headset interface (poll, subscribe, annotate)
    ring_buffer.py                     # Circular buffer for EEG samples
    headset_config.py                  # Headset model config loader from YAML
    drivers/
      headset_driver.py                # Protocol (interface) for drivers
      brainaccess.py                   # BrainAccess SDK driver
      mock.py                          # Mock driver (synthetic EEG data)

  sample_manager/
    sample_manager.py                  # Trial sequence generator (FIXATION -> CUE -> REST)
    experiment_step_type.py            # Step type enum + CLASSIFIABLE constant
    sampling_strategies.py             # StratifiedSampler, RandomSampler

  gui/
    gui_manager.py                     # GUI coordinator, view switching
    views/
      view.py                          # Base view class (shortcuts, events)
      main_menu_view.py                # Main menu view
      experiment_view.py               # Experiment view
      calibration_view.py              # Calibration view (+ classification result)
    shared/
      button.py                        # Styled button widget
      sidebar.py                       # Side panel (fullscreen, pause, quit)
      config_dialog.py                 # Session config dialogs
```

### Flow Controller -- state machine

The core of the application. `FlowController` runs a QTimer with a 10ms tick (100 FPS). Each tick:

1. `eeg_headset.poll()` -- reads new samples from the headset and forwards them to subscribers
2. `current_state.tick()` -- the current state processes GUI events and manages transitions

States follow the `enter()` -> `tick()` (repeated) -> `exit()` lifecycle. Transitions happen via `change_state()`.

```
MainMenuState  -->  CalibrationState  -->  MainMenuState
               -->  ExperimentState   -->  MainMenuState
```

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
