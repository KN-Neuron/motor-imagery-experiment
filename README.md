# Motor Imagery Experiment

A desktop application for BCI (Brain-Computer Interface) experiments using the BrainAccess EEG headset. Collects EEG data during calibration and experiment sessions based on motor imagery, SSVEP, and other paradigms. Built by KN Neuron student research group.

## Features

- **Research protocol** -- instruction screen, optional signal-quality check, resting-state block, practice trials, class-balanced left/right hand motor-imagery blocks (with breaks), and a separate artifact block. See [docs/protocol.md](docs/protocol.md).
- **Imagery vs. execution** -- `left/right_hand_imagery` (imagine, do not move) and `left/right_hand_execution` (really clench) are different classes with unambiguous Polish/English instructions.
- **Calibration** -- the same protocol; optional feedback `none | model | demo` (default `none`, no feedback). `demo` is random and is labelled on screen as "FEEDBACK DEMO, NIE PRAWDZIWY KLASYFIKATOR". `model` is an interface (`Classifier.predict`) without a model yet.
- **Pseudonymised metadata** -- participant code (`sub-001`), session number, consent, and per-session metadata (`participants.tsv`, `sessions.tsv`, `session_metadata.json`).
- **Data export** -- continuous EEG in EDF+ with annotations, `events.tsv` with block/trial/condition columns, `sync_log.tsv` with monotonic-clock timestamps, and `tools/export_bids.py` for a BIDS-EEG layout.

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

On launch, a headset selection dialog appears. Pick a model from the dropdown (populated from `brainaccess.config.yaml`) or select **MOCK (no hardware)** to run on synthetic data. Click **Connect** -- this is synchronous and may freeze for a few seconds while the SDK negotiates Bluetooth.

Once connected, the main menu appears and you can start a calibration or experiment session. If Bluetooth drops mid-session, the app writes a `DISCONNECTED` marker into the EDF, returns to the menu, and you can reconnect from there.

### MOCK mode (no hardware)

Choose **MOCK (no hardware)** in the headset dialog. The whole session runs on synthetic data and produces every output file, so it is the way to rehearse the protocol and to run the tests (`poetry run pytest` needs no hardware and no BrainAccess SDK).

### Running a session with a BrainAccess headset

1. Copy the config templates (see below) and set `device_name` / `channel_map` for your cap in `brainaccess.config.yaml`.
2. Start the app, pick the headset model, **Connect**.
3. **Start Experiment**: fill in the participant screen (pseudonym such as `sub-001`, session number, consent -- never a name), then pass the **signal-quality check** (10 s of rest; red bars are warnings, "Continue despite warnings" is recorded in the metadata).
4. The session runs: instruction (SPACE) -> optional check procedure -> rest block -> practice -> MI blocks (SPACE after each break) -> artifact block -> end screen.
5. Pause with the sidebar button; the step timer stops while paused and the interrupted step is flagged `interrupted=true`.

### No-headset mode (Alt-shortcut)

For UI smoke tests without any driver, hold **Alt** while clicking Start Experiment / Start Calibration. The session runs without an EEG stream: no EDF output, no participant screen and no quality check. For a realistic dry-run with valid output files, select **MOCK (no hardware)** instead.

## Configuration

Both runtime config files (`trials.config.yaml`, `brainaccess.config.yaml`) are gitignored. Copy them from the committed templates on first setup:

```bash
cp trials.example.config.yaml trials.config.yaml
cp brainaccess.example.config.yaml brainaccess.config.yaml
```

### `trials.config.yaml`

Main configuration file for experiment and calibration sessions. The committed template [`trials.example.config.yaml`](trials.example.config.yaml) documents every key; the important ones:

```yaml
experiment:
  n_blocks: 4                      # MI blocks
  trials_per_class_per_block: 20
  max_consecutive_same_class: 3
  practice_trials_per_class: 2     # PRACTICE block, excluded from analysis
  fixation_ms: 1500
  cue_ms: 1000                     # instruction on screen (CUE_* marker)
  task_ms: 4000                    # imagery/execution window (class marker)
  iti_min_ms: 2000                 # jittered inter-trial interval (ITI marker)
  iti_max_ms: 3500
  rest_eyes_open_ms: 120000        # rest block at the start (0 = off)
  rest_eyes_closed_ms: 0
  cues: [left_hand_imagery, right_hand_imagery]
  artifact_cues: [double_blink, jaw_clench, head_movement]   # separate block
  seed: null                       # null = random, always saved in metadata
  feedback: none                   # none | model | demo
```

Old configs keep working: `left_hand_clench` / `right_hand_clench` are read as the *execution* classes (with a `FutureWarning`), `trials_per_class` becomes `trials_per_class_per_block` with a single block, and `rest_ms` / `strategy` are ignored with a warning.

Most parameters can also be changed in the config dialog at session start; the rest (rest block, seed, quality thresholds, SSVEP frequency) come from the YAML.

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

Sessions are saved per participant and session number (no free-text folder names):

```
sessions/
  experiments/                     # or calibrations/
    participants.tsv               # one row per participant (upserted)
    sessions.tsv                   # one row per recorded session
    sub-001/
      ses-01/
        session.edf                # continuous EEG (EDF+ with annotations)
        events.tsv                 # markers (original 3 columns + new ones)
        sync_log.tsv               # monotonic-clock timestamps per marker
        session_metadata.json      # app version, headset, seed, config, QC, ...
        qc_rest.npy                # resting fragment from the quality check
```

The data directory must not be committed or shared before the ethics/data-protection requirements in [docs/protocol.md](docs/protocol.md) are met.

### EDF+ format (`session.edf`)

EDF+ is the standard EEG container, readable by MNE-Python, EEGLAB, FieldTrip, EDFbrowser. `SessionSaver` writes the file incrementally during the session. Physical range is +/-3200 uV at 16-bit resolution; the saver counts samples outside this range (clipped in the file), prints a warning and stores the counts in the metadata -- dry electrodes with a large DC offset can saturate.

**Last record.** EDF records are 1 s long, so the last record is zero-padded. The real end of the data is marked by the `END_OF_DATA` annotation and stored as `n_samples_real` in `session_metadata.json`; analysis must cut the signal there (e.g. `raw.crop(tmax=n_samples_real / sfreq - 1 / sfreq)`).

**Lost samples.** If a driver reports lost samples (optional `pop_dropped_samples()`), the saver inserts zeros so the timeline stays aligned, writes a `DATA_GAP` annotation with the gap duration and counts it in the metadata. **Limitation:** the BrainAccess driver does not implement this: it is not known whether the SDK exposes a packet counter or timestamps, so real gaps are currently not detected. `session_metadata.json` stores `wall_clock_elapsed_s` and `expected_samples_from_wall_clock` next to `n_samples_real` as a coarse drift check.

Annotations: `INSTRUCTION`, `REST_EYES_OPEN`, `REST_EYES_CLOSED`, `PRACTICE`, `FIXATION`, `CUE_<CLASS>`, `<CLASS>` (e.g. `LEFT_HAND_IMAGERY`), `ITI`, `BREAK`, `END`, `RESULT_<CLASS>` (only when feedback is on), `PAUSED` / `RESUMED`, `DATA_GAP`, `DISCONNECTED`, `ABORTED`, `END_OF_DATA`, and `experiment_start` / `calibration_start`.

Reading with MNE-Python:
```python
import mne
raw = mne.io.read_raw_edf("sessions/experiments/sub-001/ses-01/session.edf")
print(raw.info)
print(raw.annotations)
```

### events.tsv

Tab-separated event list following the [BIDS](https://bids-specification.readthedocs.io/) events convention. The first three columns are unchanged; the others were added.

| Column | Meaning |
|--------|---------|
| `onset`, `duration`, `trial_type` | as before; `duration` = time to the next marker |
| `block_id` | block number (1-based, over the whole session) |
| `trial_id` | trial number within the block |
| `condition` | `imagery`, `execution`, `artifact`, `rest`, (`ssvep`, `qc`) |
| `planned_duration`, `actual_duration` | seconds; `actual_duration` is wall-clock time of the step (includes a pause) |
| `interrupted` | `true` if a pause happened during the step |
| `practice` | `true` for practice trials |
| `feedback_mode` | `none` / `model` / `demo` |

Default analysis: drop `practice=true` rows, and drop the whole trial (same `block_id` + `trial_id`) if any of its rows has `interrupted=true`. Missing values are `n/a`.

### sync_log.tsv

One row per marker: `sample_index`, `perf_counter_ns` (monotonic clock when the marker was written), `last_packet_perf_counter_ns` (when the last EEG chunk arrived), `planned_start_perf_counter_ns` and `display_perf_counter_ns` (end of the first `paintEvent` of the step). These timestamps allow estimating display and transmission latency; see [docs/latency.md](docs/latency.md). `t0_perf_counter_ns` / `t0_unix_ns` in the metadata anchor the clock.

### BIDS export

```bash
python tools/export_bids.py sessions/experiments bids_out
```

Writes `sub-XXX/ses-YY/eeg/sub-XXX_ses-YY_task-motorimagery_{eeg.edf,events.tsv,channels.tsv,electrodes.tsv,eeg.json}`, `dataset_description.json`, `participants.tsv`; extra files go to `sourcedata/`. Electrode positions, EEG reference and software filters are written as `n/a` (the app does not know them). The original recording is not modified.

## Known limitations

- **Marker latency is not measured.** Markers are written at the sample count received when the step starts; the display delay (paint, compositor, monitor) and Bluetooth transmission delay are unknown until you run the procedure in [docs/latency.md](docs/latency.md). Do not assume sub-sample accuracy.
- **SSVEP is not validated.** Flicker is computed from a monotonic clock (not from frame counts) but is not locked to VSync and its timing has not been measured. Rigorous SSVEP needs a VSync-synchronised stimulus (e.g. PsychoPy). The app warns when the monitor refresh rate is not an even multiple of the frequency.
- **No classifier is validated.** `feedback=model` is only an interface; `demo` is random.
- **Data gaps are not detected on BrainAccess** (see above).
- **Quality thresholds are starting values**, not validated for BrainAccess dry electrodes.
- The BrainAccess SDK driver and the Windows IPC path were not exercised in this change (no headset or Windows machine was available); everything was tested with the mock driver.

## What to measure before the first session

- [ ] Marker -> screen -> EEG latency and its jitter ([docs/latency.md](docs/latency.md)).
- [ ] Whether the BrainAccess SDK provides a packet counter / timestamp (for `DATA_GAP`); otherwise compare `n_samples_real` with `expected_samples_from_wall_clock` on a long recording.
- [ ] Typical DC offset / amplitude of your electrodes vs. the +/-3200 uV EDF range.
- [ ] Monitor refresh rate and whether the cue screen drops frames.
- [ ] Quality thresholds (`quality:` in the config) on a few pilot recordings.
- [ ] A full pilot session: duration, fatigue, number of interrupted trials.

## Architecture

### Project structure

```
src/
  main.py                              # Entry point (creates GUIManager + FlowController)
  trials_config/trials_config.py       # YAML config loader + dataclasses

  session_saver/
    session_saver.py                   # EDF writer + markers + events.tsv + sync_log.tsv + metadata
  session_metadata/                    # Participant validation, participants/sessions TSV, app/system info
  signal_quality/                      # Pre-recording signal checks (RMS, flat, saturation, 50 Hz, drift)
  feedback/feedback.py                 # Classifier protocol, DemoClassifier (random), make_classifier

  flow_controller/
    flow_controller.py                 # Main loop (QTimer 10ms tick), state machine, owns eeg_headset
    states/
      flow_state.py                    # Base state class (enter/tick/exit lifecycle)
      main_menu_state.py               # Main menu: session entry, reconnect after disconnect
      session_state.py                 # Shared session logic (blocks, pause, markers, feedback, QC)
      calibration_state.py             # Calibration (SessionState + result screen duration)
      experiment_state.py              # Experiment (SessionState)
    step_timer.py                      # Step timer that stops while paused

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
    ipc/
      ipc_driver.py                    # IPC wrapper driver (Windows: runs BrainAccess in subprocess)
      worker.py                        # Subprocess entrypoint (runs real driver, communicates via pipe)
      protocol.py                      # Message types + DriverRecipe TypedDict

  sample_manager/
    sample_manager.py                  # Session/block/trial generator (seeded, balanced, jittered ITI)
    experiment_step_type.py            # Step types (imagery/execution/artifact/rest), legacy names
    texts.py                           # Polish/English participant-facing texts

  gui/
    gui_manager.py                     # GUI coordinator, view switching
    views/
      view.py                          # Base view class (shortcuts, events)
      main_menu_view.py                # Main menu view
      session_view.py                  # Full-screen session view (cues, screens, feedback, SSVEP)
      ssvep.py                         # Clock-based flicker + refresh-rate check (not validated)
      experiment_view.py               # Experiment view (SessionView subclass)
      calibration_view.py              # Calibration view (SessionView subclass)
      utils/pixmap_cache.py            # Cached image loader for cue assets
    dialogs/
      _shared.py                       # Shared dialog styles + layout helpers
      _cues.py                         # Cue checkbox helpers (used by experiment + calibration dialogs)
      headset_selection_dialog.py      # Headset selection at app launch
      session_config_dialog.py         # Experiment / calibration setup
      participant_dialog.py            # Participant + consent entry screen
      quality_dialog.py                # Signal-quality check before recording
    shared/
      button.py                        # Styled button widget
      sidebar.py                       # Side panel (fullscreen, pause, quit)

tools/
  export_bids.py                       # Export sessions to a BIDS-EEG layout
  measure_latency.py                   # Marker -> screen -> EEG latency measurement
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

`SessionSaver` registers as a subscriber on `EEGHeadset`. Each data chunk from `poll()` is immediately buffered and flushed to EDF once a full record (1 second) is ready. States call `add_marker(label, block_id=..., ...)` on step transitions -- the marker records the current sample index and `perf_counter_ns`.

```
poll() -> chunk -> SessionSaver.on_chunk() -> buffer -> EDF (every 1s)
state.tick() -> add_marker("LEFT_HAND_IMAGERY", ...) -> marker list -> EDF annotations + events.tsv + sync_log.tsv
```

On `stop_session()`, remaining samples are flushed (zero-padded record, `END_OF_DATA` marker), annotations are written to EDF, and events.tsv, sync_log.tsv and session_metadata.json are generated.

### Sample Manager -- session structure

`SampleManager(config)` builds the whole session as a queue of `ExperimentStep`s. Order: instruction screen, [check procedure], [rest block], [practice], MI blocks (separated by `BREAK` screens that wait for SPACE), artifact block, [SSVEP block], end screen. One trial:

```
FIXATION -> CUE_<CLASS> (cue_ms) -> <CLASS> (task_ms) -> ITI (random in [iti_min_ms, iti_max_ms])
```

Each block contains `trials_per_class_per_block` trials of every class in random order with at most `max_consecutive_same_class` identical classes in a row. All randomness (class order and ITI) comes from one `random.Random(seed)`: the same seed reproduces the same session, and the seed is stored in `session_metadata.json`.

### Session states

`ExperimentState` and `CalibrationState` share `SessionState`: pause-aware `StepTimer`, markers with block/trial/condition, feedback handling (`src/feedback`), participant tables, and the quality check. `src/session_metadata` holds participant validation and the TSV/JSON writers.

### GUI -- PyQt6 with QPainter

The interface is built on `QStackedWidget` (fast view switching) with a side panel (`Sidebar`). Views are rendered via `paintEvent()` using QPainter -- no .ui files. Dark theme (purple/blue).

GUI-to-State communication: views maintain a `pending_events` list, states poll it in `tick()` (event queue instead of Qt signals -- simpler flow control).

## Development

### Tests

```bash
poetry run pytest                  # all tests (no hardware / SDK needed, Qt runs offscreen)
```

### Formatting and linting

```bash
poetry run black src/ tests/ tools/   # formatting
poetry run flake8 src/ tests/ tools/  # lint
poetry run mypy src/                  # type check
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
