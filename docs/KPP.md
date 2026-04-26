# KPP — Kompleksowe Podsumowanie Projektu

## 1. Informacje ogólne
- **Nazwa projektu:** Motor Imagery Experiment
- **Projekt nadrzędny:** BrainBoard
- **Zespół:**
  - Grzegorz Szczepanek — lider projektu
  - Tomasz Stefaniak — flow_controller, GUI, integracja
  - Wiktor Dembny — sample_manager
  - Mikołaj Popik — eeg_headset
- **Okres realizacji:** 2025–2026
- **Repozytorium:** https://github.com/KN-Neuron/motor-imagery-experiment
- **Wersja dokumentu:** 1.0

---

## 2. Cel projektu

### 2.1 Problem

Projekt BrainBoard ma na celu stworzenie klawiatury sterowanej aktywnością mózgu (BCI). Żeby taki system działał, potrzebny jest model klasyfikujący sygnały EEG — a żeby wytrenować i skalibrować taki model, trzeba zbierać oznaczone dane od konkretnych użytkowników. Nie istniało gotowe, wystarczająco elastyczne narzędzie do tego celu dopasowane do naszego sprzętu (BrainAccess) i paradygmatów (motor imagery, SSVEP).

### 2.2 Motywacja

Motor Imagery Experiment to niezbędna infrastruktura danych dla projektu BrainBoard — bez zebranych i poprawnie oznaczonych sesji EEG nie można wytrenować modelu klasyfikatora, który ma docelowo sterować klawiaturą. Aplikacja jest środkiem do celu, nie celem samym w sobie.

---

## 3. Przegląd rozwiązania

### 3.1 Opis ogólny

Desktopowa aplikacja do prowadzenia sesji EEG: kalibracyjnych (użytkownik wykonuje zadania motoryczne, aplikacja zapisuje odpowiedzi EEG i pokazuje wynik klasyfikatora) oraz eksperymentalnych (rejestracja ciągłego strumienia EEG ze znacznikami). Dane wyjściowe to pliki EDF+ (ciągłe EEG z adnotacjami) oraz events.tsv w formacie BIDS.

### 3.2 Architektura

```
[GUI (PyQt6)]
      │  zdarzenia (event queue)
      ▼
[FlowController — maszyna stanów, tick 10ms]
      │                    │
      ▼                    ▼
[SampleManager]     [EEGHeadset]
 sekwencje prób       poll() → RingBuffer
                              → SessionSaver → EDF+ / events.tsv
                              → Subscribers
```

### 3.3 Główne komponenty

- **FlowController** — główna pętla (QTimer 10ms), maszyna stanów (MainMenu / Calibration / Experiment)
- **EEGHeadset** — abstrakcja headseta; obsługuje BrainAccess SDK oraz MockDriver (syntetyczne dane)
- **SampleManager** — generuje sekwencje prób (FIXATION → CUE → REST) wg konfiguracji
- **SessionSaver** — subskrybent EEGHeadset; zapisuje dane na bieżąco do EDF+ i events.tsv
- **GUI** — widoki PyQt6 rysowane przez QPainter, ciemny motyw; komunikacja przez kolejkę zdarzeń

---

## 4. Technologie i decyzje projektowe

### 4.1 Stack technologiczny

- **Język:** Python 3.13+
- **GUI:** PyQt6 (renderowanie przez QPainter, bez plików .ui)
- **EEG SDK:** BrainAccess 3.6.1
- **Zapis danych:** pyedflib (EDF+), PyYAML (konfiguracja)
- **Narzędzia dev:** Poetry, black, flake8, mypy, pre-commit, pytest, GitHub Actions

### 4.2 Kluczowe decyzje

- **QTimer zamiast wątku EEG:**
  - Dlaczego: prostszy model współbieżności, brak potrzeby synchronizacji między wątkami; 10ms tick jest wystarczający dla danych 250 Hz
  - Alternatywy: osobny wątek do pollingu EEG — większa złożoność bez realnych korzyści przy tym sample rate

- **Kolejka zdarzeń GUI → stan zamiast Qt signals:**
  - Dlaczego: stany odpytują GUI w tick(), co daje deterministyczny przepływ; signals/slots rozpraszałyby logikę przejść po callbackach
  - Alternatywy: bezpośrednie Qt signals — trudniejsze do testowania i śledzenia przepływu

- **Wzorzec subskrybentów w EEGHeadset:**
  - Dlaczego: SessionSaver i potencjalnie klasyfikator mogą niezależnie odbierać dane bez modyfikacji kodu headseta
  - Alternatywy: bezpośrednie wywołania z FlowController — silne sprzężenie

- **MockDriver:**
  - Dlaczego: umożliwia pracę i testowanie całego stosu bez fizycznego headseta (sygnały alfa + szum gaussowski)
  - Alternatywy: mocker w testach — nie pokrywa integracji GUI/flow

---

## 5. Implementacja

### 5.1 Struktura projektu

```
src/
  main.py
  trials_config/trials_config.py

  flow_controller/
    flow_controller.py
    states/
      flow_state.py
      main_menu_state.py
      calibration_state.py
      experiment_state.py
    session_saver/
      session_saver.py

  eeg_headset/
    eeg_headset.py
    ring_buffer.py
    headset_config.py
    cmd/demo.py
    drivers/
      headset_driver.py
      brainaccess.py
      mock.py
      playback.py

  sample_manager/
    sample_manager.py
    experiment_step_type.py
    sampling_strategies.py

  gui/
    gui_manager.py
    views/
      view.py
      main_menu_view.py
      experiment_view.py
      calibration_view.py
      utils/pixmap_cache.py
    shared/
      button.py
      sidebar.py
      config_dialog.py

trials.config.yaml
brainaccess.config.yaml
```

### 5.2 Kluczowe elementy

**FlowController** — centralny orkiestrator. Każdy tick (10ms):
1. `eeg_headset.poll()` — odczyt nowych próbek, przekazanie do subskrybentów
2. `current_state.tick()` — stan przetwarza zdarzenia GUI i zarządza przejściami

**SessionSaver** — subskrybuje dane z EEGHeadset. Każdy chunk jest buforowany i zapisywany do EDF co 1 sekundę (pełny rekord). Stany wywołują tylko `add_marker(label)` przy przejściach — reszta jest automatyczna.

**SampleManager** — generuje sekwencje trójek (FIXATION → CUE → REST) według strategii StratifiedSampler (równa liczba każdego cue, losowa kolejność) lub RandomSampler.

### 5.3 Nietrywialne rozwiązania

**Precyzja znaczników czasowych w EDF:** Znaczniki nie są zapisywane z timestampem zegara systemowego, lecz z indeksem próbki (`sample_idx / sample_rate`). Eliminuje to dryft i niedokładności wynikające z opóźnień pętli czy OS schedulera.

**MockDriver z realistycznym sygnałem:** Syntetyczne dane to fale sinusoidalne w paśmie alfa (8–12 Hz) z szumem gaussowskim w zakresie ±60 µV — wystarczające do testowania całego stosu bez headseta, włącznie z zapisem EDF.

---

## 6. Jak uruchomić projekt

### 6.1 Wymagania

- Python 3.13+
- Poetry
- BrainAccess SDK (`brainaccess` 3.6.1)
- Headset BrainAccess HALO 4CH lub MIDI 16CH — opcjonalnie (tryb mock działa bez headseta)

### 6.2 Instalacja

```bash
git clone https://github.com/KN-Neuron/motor-imagery-experiment.git
cd motor-imagery-experiment
poetry install
```

Opcjonalnie, z narzędziami dev:

```bash
poetry install --with dev
```

### 6.3 Uruchomienie

```bash
poetry run python -m src.main
```

### 6.4 First steps

- Bez headseta: przytrzymaj **Alt** podczas klikania Start — aplikacja użyje MockDriver z syntetycznymi danymi EEG.
- Z headsetem: podłącz urządzenie BrainAccess, upewnij się że SDK jest zainstalowane, uruchom normalnie.
- Konfiguracja sesji (liczba prób, typy cue, nazwa folderu) dostępna przez dialog przed startem.
- Dane sesji trafiają do katalogu `sessions/calibrations/` lub `sessions/experiments/`.

---

## 7. Wyniki

### 7.1 Co działa

- Pełny przepływ kalibracji: sekwencja cue → zapis EEG → wynik klasyfikatora (obecnie placeholder — losowy)
- Pełny przepływ eksperymentu: sekwencja prób z ciągłym zapisem EEG
- Eksport danych: EDF+ z adnotacjami + events.tsv (BIDS)
- Tryb mock: pełna funkcjonalność bez fizycznego headseta
- Konfiguracja sesji przez UI (typy cue, liczba prób, nazwa folderu)
- Obsługa dwóch modeli headseta: HALO 4CH i MIDI 16CH

### 7.2 Demo

Aplikację można uruchomić na dowolnej maszynie z Pythonem 3.13 bez headseta (tryb mock). Pełną sesję kalibracyjną z zapisem EDF można przeprowadzić i odczytać w MNE-Python:

```python
import mne
raw = mne.io.read_raw_edf("sessions/calibrations/.../session.edf")
print(raw.annotations)
```

### 7.3 Metryki

Klasyfikator w tej aplikacji jest placeholderem (losowe odpowiedzi) — rzeczywisty model klasyfikacyjny jest częścią szerszego projektu BrainBoard i będzie integrowany osobno. Aplikacja jest odpowiedzialna za zbieranie danych, nie za ich analizę.

---

## 8. Problemy i wyzwania

```
Problem: Precyzja znaczników czasowych

Opis: Znaczniki zdarzeń (onset prób) zapisywane z timestampem systemowym
      miały nieakceptowalny dryft przy długich sesjach — OS scheduler
      i opóźnienia pętli wprowadzały błąd rzędu dziesiątek ms.

Rozwiązanie: Znaczniki zapisywane jako indeks próbki EEG (sample_idx),
             przeliczany na czas przez sample_idx / sample_rate.
             Dokładność ograniczona tylko przez sample rate headseta (250 Hz → 4ms).
```

```
Problem: Testowanie bez headseta

Opis: BrainAccess SDK wymaga fizycznego urządzenia i sterowników Bluetooth.
      Uniemożliwiało to testowanie i development poza laboratorium.

Rozwiązanie: MockDriver generujący syntetyczne dane EEG (alfa + szum gaussowski).
             Aktywowany przez Alt+Start bez zmian w kodzie logiki.
```

```
Problem: Sprzężenie GUI z logiką eksperymentu

Opis: Qt signals/slots prowadziły do rozproszenia logiki przejść między stanami
      po wielu callbackach, trudnych do śledzenia i testowania.

Rozwiązanie: Widoki gromadzą zdarzenia w liście pending_events;
             stany odpytują ją w każdym tick(). Przepływ pozostaje deterministyczny
             i scentralizowany w FlowController.
```

---

## 9. Wnioski

### 9.1 Czego się nauczyliśmy

- Jak zintegrować zewnętrzne SDK sprzętowe (BrainAccess) z własną architekturą przez warstwę abstrakcji (protokół `HeadsetDriver`)
- Jak projektować aplikacje real-time z precyzyjnymi wymaganiami czasowymi bez wielowątkowości
- Jak zapisywać dane neurofizjologiczne w standardowych formatach (EDF+, BIDS) gotowych do dalszej analizy
- Wartość MockDriver — umożliwił równoległy rozwój wszystkich modułów bez zależności od fizycznego sprzętu

### 9.2 Co zrobilibyśmy inaczej

- Klasyfikator jako stub od początku — zamiast losowego placeholdera, interfejs gotowy do podpięcia prawdziwego modelu
- Więcej testów integracyjnych z MockDriver od wczesnych etapów
- Konsekwentniejsze stosowanie helperów w klasach stanów od początku — przy pierwszej iteracji `enter()`/`tick()` urosły do funkcji 40-50 linijkowych, refactor wprowadziliśmy dopiero później

---

## 10. Możliwe rozwinięcia

- Podpięcie rzeczywistego klasyfikatora EEG (model trenowany na zebranych danych)
- Wizualizacja sygnału EEG w czasie rzeczywistym podczas sesji
- Rozszerzenie o nowe paradygmaty BCI (P300, inne warianty SSVEP)
- Integracja z pipeline'em treningowym modelu w projekcie BrainBoard
- Eksport do dodatkowych formatów (np. BrainVision, CSV)

---

## 11. Reproducibility Checklist

**Sprawdź przed oddaniem:**

- [x] Projekt da się uruchomić na czystym środowisku (tryb mock bez headseta)
- [x] Instrukcja uruchomienia działa krok po kroku
- [x] Wszystkie zależności są opisane (pyproject.toml)
- [x] Demo działa zgodnie z opisem

---

## 12. Załączniki

- [README.md](../README.md) — dokumentacja techniczna projektu
- Konfiguracja sesji: `trials.config.yaml`, `brainaccess.config.yaml` (template'y: `*.example.config.yaml`)
- Format danych wyjściowych: EDF+ (MNE-Python), events.tsv (BIDS)

---

## 13. Status projektu

W trakcie — aplikacja do zbierania danych gotowa; integracja z klasyfikatorem i projekt BrainBoard w toku.

---
