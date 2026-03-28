# Hex-O-Spell Experiment

Aplikacja desktopowa (PyQt6) do eksperymentów EEG — zbieranie danych z headsetu BrainAccess w ramach kalibracji i właściwego eksperymentu BCI (Brain-Computer Interface). Projekt koła naukowego KN NEURON.

## Cel aplikacji

1. **Kalibracja** — wyświetlanie cue'ów wizualnych (motor imagery, mrugnięcia, ruchy głowy, SSVEP) i nagrywanie odpowiedzi EEG w celu trenowania klasyfikatora
2. **Eksperyment** — uruchamianie sesji z wykorzystaniem skalibrowanych cue'ów i zapis danych
3. **Eksport danych** — zapis EEG do formatu EDF+ z adnotacjami w formacie BIDS events TSV

## Stack technologiczny

- Python 3.13+, PyQt6, BrainAccess SDK (`brainaccess` v3.6.1)
- Dane: `pyedflib` (EDF+), NumPy, format BIDS
- Konfiguracja: YAML (`trials_config.yaml`)
- Jakość kodu: Black, Flake8, MyPy, pytest, pre-commit hooks
- CI: GitHub Actions

## Struktura projektu

```
src/
├── main.py                        # Entry point — inicjalizacja GUI, headsetu, flow controllera
├── config/config.py               # Loader konfiguracji YAML
├── gui/
│   ├── gui_manager.py             # Koordynator GUI, przełączanie widoków (QStackedWidget)
│   ├── shared/                    # Button, Sidebar, ConfigDialog
│   └── views/                     # MainMenuView, ExperimentView, CalibrationView (rysowane QPainterem)
├── flow_controller/
│   ├── flow_controller.py         # Maszyna stanów, tick co 10ms (100 FPS)
│   ├── states/                    # FlowState (abstrakcja), MainMenuState, CalibrationState, ExperimentState
│   └── session_saver/             # Zapis CSV → konwersja do EDF + BIDS events TSV
├── eeg_headset/
│   ├── eeg_headset.py             # Interfejs headsetu z ring bufferem
│   ├── ring_buffer.py             # Bufor kołowy na próbki EEG
│   └── drivers/                   # HeadsetDriver Protocol, BrainAccessDriver, MockDriver
└── sample_manager/
    ├── sample_manager.py          # Generator sekwencji triali (FIXATION → CUE → REST)
    ├── experiment_step_type.py    # Enum: FIXATION, REST, DOUBLE_BLINK, LEFT_HAND, RIGHT_HAND, ...
    └── sampling_strategies.py     # StratifiedSampler, RandomSampler
```

Inne ważne pliki:
- `trials_config.yaml` — konfiguracja eksperymentu i kalibracji (cue'y, czasy, strategia)
- `brainaccess_headsets_config.yaml` — konfiguracja modeli headsetów (kanały, sample rate)
- `sessions/` — katalog wyjściowy z zapisanymi sesjami (calibrations/, experiments/)
- `res/imgs/` — obrazki cue'ów i logo

## Wzorce architektoniczne

- **State Machine** — `FlowState` z cyklem `enter()`/`tick()`/`exit()`, stany przełączane przez `FlowController`
- **Event Queue** — widoki GUI trzymają `pending_events`, stany pollują je w `tick()` (zamiast sygnałów Qt)
- **Driver Protocol** — `HeadsetDriver` jako protokół z implementacjami `BrainAccessDriver` i `MockDriver`
- **Strategy Pattern** — `StratifiedSampler` / `RandomSampler` do generowania triali
- **Custom painting** — GUI renderowane przez `paintEvent()` z QPainter, bez plików .ui

## Uruchamianie

```bash
pip install -e .
python -m src.main
```

Tryb bez headsetu: Alt+klik na przycisku Start Experiment/Calibration w menu.

## Testy i jakość kodu

```bash
pytest                  # wszystkie testy
pytest -m unit          # unit testy
black src/ tests/       # formatowanie
flake8 src/ tests/      # lint
mypy src/               # type check
```

## Konwencje

- Pełne type hints (MyPy z `disallow_untyped_defs`)
- Logowanie przez `print(f"[ModuleName] ...")`
- Język kodu: angielski; commity: polski
- Ciemny motyw GUI (dark purple/blue)
- Sesje autozapisywane z timestampem do `sessions/`
- Pauza/wznowienie wspierane w kalibracji i eksperymencie
- Skróty: ESC = abort, Q = quit
