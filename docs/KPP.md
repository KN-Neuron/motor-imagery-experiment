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
- **Wersja dokumentu:** 1.1 (protokół badawczy: bloki, imagery/execution, metadane BIDS)

---

## 2. Cel projektu

### 2.1 Problem

Projekt BrainBoard ma na celu stworzenie klawiatury sterowanej aktywnością mózgu (BCI). Żeby taki system działał, potrzebny jest model klasyfikujący sygnały EEG — a żeby wytrenować i skalibrować taki model, trzeba zbierać oznaczone dane od konkretnych użytkowników. Nie istniało gotowe, wystarczająco elastyczne narzędzie do tego celu dopasowane do naszego sprzętu (BrainAccess) i paradygmatów (motor imagery, SSVEP).

### 2.2 Motywacja

Motor Imagery Experiment to niezbędna infrastruktura danych dla projektu BrainBoard — bez zebranych i poprawnie oznaczonych sesji EEG nie można wytrenować modelu klasyfikatora, który ma docelowo sterować klawiaturą. Aplikacja jest środkiem do celu, nie celem samym w sobie.

---

## 3. Przegląd rozwiązania

### 3.1 Opis ogólny

Desktopowa aplikacja do zbierania danych EEG w badaniu motor imagery (lewa/prawa ręka): sesje kalibracyjne i eksperymentalne mają ten sam protokół (instrukcja, kontrola jakości sygnału, spoczynek, trening, bloki MI, osobny blok artefaktów). Informacja zwrotna jest domyślnie wyłączona. Dane wyjściowe to EDF+ (ciągłe EEG z adnotacjami), `events.tsv` (BIDS + kolumny block/trial/condition), `sync_log.tsv`, `session_metadata.json` oraz `participants.tsv` / `sessions.tsv`; eksport do BIDS-EEG: `tools/export_bids.py`. Opis protokołu do wniosku o zgodę komisji: [protocol.md](protocol.md).

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

- **FlowController** — główna pętla (QTimer 10ms), maszyna stanów (MainMenu / Calibration / Experiment); trzyma referencję do aktualnie wybranego headsetu (może być `None`).
- **HeadsetSelectionDialog** — dialog pokazywany przy starcie aplikacji; użytkownik wybiera model headsetu z listy (wypełnianej z `brainaccess.config.yaml`) lub tryb MOCK (syntetyczne dane), klika Connect. Dialog tworzy driver, sprawdza połączenie i przekazuje gotowy `EEGHeadset` do FlowController.
- **MainMenuState** — pełni rolę "lobby" między sesjami: uruchamia kalibrację lub eksperyment, obsługuje powrót po sesji i reakcję na rozłączenie czepka (przycisk Reconnect).
- **EEGHeadset** — abstrakcja headseta; obsługuje BrainAccess SDK (HALO / MIDI / MAXI / SAMPLE) oraz MockDriver (syntetyczne dane). Wybór sterownika jest dynamiczny — dokonywany w runtime przez menu, nie przy starcie.
- **SampleManager** — buduje całą sesję jako bloki prób (FIXATION → CUE → zadanie → ITI z jitterem), z ziarnem losowania i ograniczeniem serii tej samej klasy; artefakty w osobnym bloku.
- **SessionState** — wspólna logika sesji eksperymentu i kalibracji: licznik kroku zatrzymywany na czas pauzy, markery z metadanymi, feedback `none|model|demo`, kontrola jakości przed nagraniem.
- **SessionSaver** — subskrybent EEGHeadset; zapisuje EDF+, `events.tsv`, `sync_log.tsv` i `session_metadata.json`.
- **GUI** — widoki PyQt6 rysowane przez QPainter, ciemny motyw; komunikacja przez kolejkę zdarzeń.

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

- **Dialog wyboru headseta przy starcie:**
  - Dlaczego: wybranie czepka jest warunkiem koniecznym do jakiejkolwiek pracy z aplikacją — dialog wymusza tę decyzję przed wejściem do menu. Użytkownik wybiera model z listy (lub MOCK) i klika Connect; dopiero po udanym połączeniu pojawia się menu główne.
  - Alternatywy: wybór headseta w menu głównym (poprzednia wersja) — komplikował menu i wymagał dodatkowego stanu "brak headseta" obsługiwanego w każdym miejscu aplikacji. Po rozłączeniu fizycznym użytkownik wraca do menu i może wcisnąć Reconnect bez ponownego dialogu.

- **Konfiguracja modeli w pliku YAML:**
  - Dlaczego: dropdown w menu jest budowany z `brainaccess.config.yaml` w runtime — dodanie nowego czepka (np. nowy egzemplarz Maxi z innym numerem seryjnym) nie wymaga zmiany w kodzie aplikacyjnym, tylko wpisu w YAML i odpowiednika w `HeadsetModel` enum.
  - Alternatywy: lista modeli zaszyta w kodzie — gorsza skalowalność dla koła, gdzie na różnych egzemplarzach pracuje wiele osób.

---

## 5. Implementacja

Pełna struktura katalogów i opis poszczególnych modułów: zob. [README.md → Project structure](../README.md#project-structure).

Kluczowe zmiany strukturalne względem pierwszej iteracji: `session_saver/` wyniesiony na poziom `src/` (był pod `flow_controller/`); w `eeg_headset/` dodano podmoduł `ipc/` z `IpcHeadsetDriver`, `worker.py` i `protocol.py` — izolacja BrainAccess SDK w subprocesie na Windows.

### 5.1 Kluczowe elementy

**FlowController** — centralny orkiestrator. Każdy tick (10ms):
1. `eeg_headset.poll()` — odczyt nowych próbek, przekazanie do subskrybentów (jeśli headset jest podłączony i strumień aktywny).
2. `current_state.tick()` — stan przetwarza zdarzenia GUI i zarządza przejściami.

**HeadsetSelectionDialog** — wyświetlany przy starcie aplikacji. Wczytuje listę dostępnych modeli z `brainaccess.config.yaml`, prezentuje dropdown; użytkownik wybiera model (lub MOCK) i klika Connect. Dialog tworzy odpowiedni driver (BrainAccessDriver lub MockDriver) i przekazuje gotowy `EEGHeadset` do FlowController. Dopiero po udanym połączeniu otwiera się menu główne.

**MainMenuState** — "lobby" między sesjami. Obsługuje start kalibracji/eksperymentu oraz Reconnect po rozłączeniu czepka. Gdy headset zniknie w trakcie sesji, ExperimentState/CalibrationState wykrywają to i wracają do menu, gdzie użytkownik może połączyć ponownie bez restartu aplikacji.

**SessionSaver** — subskrybuje dane z EEGHeadset. Każdy chunk jest buforowany i zapisywany do EDF co 1 sekundę (pełny rekord). Stany wywołują tylko `add_marker(label)` przy przejściach — reszta jest automatyczna.

**SampleManager** — generuje sekwencje trójek (FIXATION → CUE → REST) według strategii StratifiedSampler (równa liczba każdego cue, losowa kolejność) lub RandomSampler.

### 5.2 Nietrywialne rozwiązania

**Precyzja znaczników czasowych w EDF:** Znaczniki nie są zapisywane z timestampem zegara systemowego, lecz z indeksem próbki (`sample_idx / sample_rate`). Eliminuje to dryft i niedokładności wynikające z opóźnień pętli czy OS schedulera.

**MockDriver z realistycznym sygnałem:** Syntetyczne dane to fale sinusoidalne z szumem gaussowskim — każdy kanał ma inną częstotliwość (8 Hz, 10 Hz, 12 Hz, 14 Hz... zależnie od indeksu kanału), amplituda ~50 µV, szum ~10 µV. Wystarczające do testowania całego stosu bez headseta, włącznie z zapisem EDF. MockDriver może operować na configu dowolnego modelu czepka (HALO, MIDI, MAXI, SAMPLE), więc emuluje zarówno liczbę kanałów jak i nazwy elektrod tego konkretnego sprzętu.

**Wykrywanie rozłączenia z natywnego SDK:** `BrainAccessDriver.is_connected` nie trzyma własnej flagi — deleguje pytanie do `EEGManager.is_connected()` z SDK BrainAccess, które zna prawdziwy stan łącza Bluetooth. Dzięki temu odpięcie czepka w trakcie nagrywania jest wykrywane natychmiast w pętli FlowController, sesja zostaje czysto zakończona z markerem `DISCONNECTED` w EDF, a aplikacja pozostaje w pełni funkcjonalna (nie wymaga restartu).

**Headset jako pole opcjonalne:** `FlowController.eeg_headset` startuje jako `None` i jest ustawiany dopiero po wybraniu modelu w menu. Stany sesji odczytują headset przez property w klasie bazowej, co oznacza że podmiana czepka w menu jest natychmiast widoczna dla kolejnego uruchomienia eksperymentu — bez restartu, bez resetu konfiguracji, bez ponownego ładowania YAML.

---

## 6. Jak uruchomić projekt

Wymagania, instalacja, pierwsze kroki: zob. [README.md → Requirements / Installation / Running](../README.md#requirements).

W skrócie: `poetry install`, `poetry run python -m src.main`, w menu głównym wybierz model headseta (lub zaznacz "Use mock driver"), kliknij Connect, kliknij Start Experiment / Start Calibration.

---

## 7. Wyniki

### 7.1 Co działa

- Pełny protokół sesji w trybie MOCK: instrukcja → kontrola jakości → blok spoczynku → trening → bloki MI z przerwami → blok artefaktów → ekran końcowy
- Domyślnie brak informacji zwrotnej; tryb `demo` (losowy) jest oznaczony na ekranie jako „FEEDBACK DEMO, NIE PRAWDZIWY KLASYFIKATOR”
- Pauza zatrzymuje licznik kroku; przerwany krok ma `interrupted=true`
- Eksport danych: EDF+ z adnotacjami + events.tsv + sync_log.tsv + metadane; `tools/export_bids.py`
- Tryb mock: pełna funkcjonalność bez fizycznego headseta, z konfiguracją kanałów dowolnego modelu
- Wybór headseta w dialogu startowym (HALO 4CH, MIDI 16CH, MAXI 32CH, SAMPLE 64CH oraz MOCK) — po rozłączeniu możliwy Reconnect z menu bez restartu aplikacji
- Wykrywanie rozłączenia czepka w trakcie sesji: marker `DISCONNECTED` w EDF, czyste zamknięcie sesji, powrót do menu
- Konfiguracja sesji przez UI (bloki, liczba prób, czasy, ITI, feedback, klasy) oraz ekran uczestnika (kod `sub-001`, numer sesji, zgoda)

### 7.2 Demo

Aplikację można uruchomić na dowolnej maszynie z Pythonem 3.13 bez headseta (tryb mock). Pełną sesję kalibracyjną z zapisem EDF można przeprowadzić i odczytać w MNE-Python:

```python
import mne
raw = mne.io.read_raw_edf("sessions/calibrations/.../session.edf")
print(raw.annotations)
```

### 7.3 Metryki

Aplikacja nie zawiera klasyfikatora. Wcześniejsza wersja pokazywała w kalibracji prawdziwą klasę bodźca jako „wynik klasyfikatora” (uczestnik zawsze widział „trafione”) — zostało to usunięte. Obecnie `feedback: none` (domyślnie), `demo` (losowe, z czerwonym oznaczeniem na ekranie) oraz `model` (tylko interfejs `Classifier.predict`, bez modelu). Rzeczywisty model jest częścią projektu BrainBoard. Aplikacja zbiera dane, nie analizuje ich.

### 7.4 Format danych wyjściowych

Każda sesja produkuje folder `sub-XXX/ses-YY/` (plus `participants.tsv` i `sessions.tsv` w katalogu danych) z plikami:

- **`session.edf`** — pełny zapis EEG w formacie **EDF+**, czyli standardzie de facto klinicznego i badawczego EEG (czytany przez MNE-Python, EEGLAB, FieldTrip i inne). Zawiera ciągły strumień próbek dla wszystkich kanałów aktywnego czepka, etykietowanych nazwami w systemie 10-20 (Fp1, F3, Cz, ...). Wewnątrz pliku zaszyte są też adnotacje opisujące kolejne fazy próby (FIXATION, CUE, REST), pauzy, wynik klasyfikatora w trybie kalibracji oraz markery rozłączenia czepka jeśli wystąpiło.
- **`events.tsv`** — lista zdarzeń w formacie **BIDS** (Brain Imaging Data Structure), standardzie wymaganym przez większość neurosharing platforms (OpenNeuro itp.). Plik tabularny z kolumnami `onset`, `duration`, `trial_type` oraz (dodane) `block_id`, `trial_id`, `condition`, `planned_duration`, `actual_duration`, `interrupted`, `practice`, `feedback_mode` — gotowy do parsowania w pandas. Domyślna analiza pomija `practice=true` i próby z `interrupted=true`.
- **`sync_log.tsv`** — znaczniki czasu zegara monotonicznego (`perf_counter_ns`) każdego markera, czas ostatniego pakietu EEG, planowany start i rzeczywiste wyświetlenie kroku (koniec pierwszego `paintEvent`); do szacowania opóźnień ([latency.md](latency.md)).
- **`session_metadata.json`** — wersja aplikacji (hash commita), model headsetu, `channel_map`, częstotliwość próbkowania, jednostki, wersja SDK, ziarno losowania, pełna konfiguracja prób, tryb feedbacku, system, odświeżanie monitora, wynik kontroli jakości, liczba rzeczywistych próbek.
- **`qc_rest.npy`** — fragment spoczynku z kontroli jakości.

Oba formaty są otwarte, niezależne od żadnego konkretnego producenta, czytelne za 10 lat. EDF zapisywany jest na bieżąco w trakcie sesji, natomiast `events.tsv`, `sync_log.tsv` i `session_metadata.json` powstają dopiero przy zamknięciu sesji. Przy awarii procesu pozostaje wyłącznie (możliwie niepełny) EDF — nie zakładaj, że ta ścieżka została przetestowana.

### 7.5 Protokół badawczy, ograniczenia i pomiary przed pierwszą sesją

Protokół (klasy, bloki, liczba prób, czas sesji, ryzyka, anonimizacja) opisuje [protocol.md](protocol.md). Znane ograniczenia:

- **Opóźnienie markerów nie jest zmierzone.** Marker to liczba próbek odebranych w chwili startu kroku; opóźnienie wyświetlania (rysowanie, kompozytor, monitor) i transmisji Bluetooth jest nieznane aż do wykonania procedury z [latency.md](latency.md). Wcześniejsze stwierdzenie „dokładność ograniczona tylko przez sample rate (4 ms)” dotyczyło wyłącznie przeliczenia indeksu próbki na czas, nie opóźnienia bodźca.
- **SSVEP niezwalidowany.** Miganie liczone z zegara (nie z liczby klatek), ale niesynchronizowane z VSync i niezmierzone; rygorystyczne SSVEP wymaga np. PsychoPy.
- **Brak walidacji klasyfikatora** (`feedback=model` to tylko interfejs).
- **Utrata próbek** nie jest wykrywana dla BrainAccess: nie wiadomo, czy SDK udostępnia licznik próbek lub znacznik czasu pakietu. Mechanizm `DATA_GAP` działa dla sterowników implementujących `pop_dropped_samples()` (np. mock).
- **Ostatni rekord EDF** jest dopełniany zerami; koniec danych oznacza adnotacja `END_OF_DATA` i `n_samples_real` w metadanych.
- **Zakres EDF ±3200 µV**: próbki poza zakresem są obcinane w pliku; aplikacja liczy je i ostrzega.
- **Progi kontroli jakości** są wartościami startowymi, niezwalidowanymi dla suchych elektrod BrainAccess.

**Co trzeba zmierzyć przed pierwszą sesją:**

- [ ] opóźnienie marker → ekran → EEG i jego jitter ([latency.md](latency.md));
- [ ] czy SDK BrainAccess podaje licznik próbek / znacznik czasu pakietu;
- [ ] typowy offset DC i amplitudę elektrod względem zakresu ±3200 µV;
- [ ] częstotliwość odświeżania monitora i gubienie klatek na ekranie bodźców;
- [ ] progi kontroli jakości na kilku sesjach pilotażowych;
- [ ] pełna sesja pilotażowa: czas trwania, zmęczenie, liczba przerwanych prób.

---

## 8. Problemy i wyzwania

```
Problem: Precyzja znaczników czasowych

Opis: Znaczniki zdarzeń (onset prób) zapisywane z timestampem systemowym
      miały nieakceptowalny dryft przy długich sesjach — OS scheduler
      i opóźnienia pętli wprowadzały błąd rzędu dziesiątek ms.

Rozwiązanie: Znaczniki zapisywane jako indeks próbki EEG (sample_idx),
             przeliczany na czas przez sample_idx / sample_rate.
             To usuwa dryft zegara systemowego względem sygnału, ale NIE mierzy
             opóźnienia wyświetlania ani transmisji (nieznane, zob. latency.md).
             Dodatkowo sync_log.tsv zapisuje zegar monotoniczny i czas
             wyświetlenia kroku.
```

```
Problem: Testowanie bez headseta

Opis: BrainAccess SDK wymaga fizycznego urządzenia i sterowników Bluetooth.
      Uniemożliwiało to testowanie i development poza laboratorium.

Rozwiązanie: MockDriver generujący syntetyczne dane EEG (alfa + szum gaussowski),
             wybierany w dialogu startowym. Wszystkie testy (pytest) działają
             na mocku, bez SDK i bez sprzętu.
```

```
Problem: Sprzężenie GUI z logiką eksperymentu

Opis: Qt signals/slots prowadziły do rozproszenia logiki przejść między stanami
      po wielu callbackach, trudnych do śledzenia i testowania.

Rozwiązanie: Widoki gromadzą zdarzenia w liście pending_events;
             stany odpytują ją w każdym tick(). Przepływ pozostaje deterministyczny
             i scentralizowany w FlowController.
```

```
Problem: Niewidzialne rozłączenie czepka w trakcie nagrywania

Opis: Pierwsza wersja drivera trzymała własne flagi `is_connected` ustawiane
      tylko w connect()/disconnect(). Gdy Bluetooth zrywał się fizycznie
      (rozładowany czepek, zakłócenie), aplikacja dalej myślała że nagrywa —
      a w rzeczywistości EDF nie dostawał nowych próbek, markery wpadały
      ze złym sample_idx, badany kończył sesję bez ostrzeżenia.

Rozwiązanie: BrainAccessDriver deleguje is_connected/is_streaming bezpośrednio
             do EEGManager z SDK BrainAccess, które zna prawdziwy stan łącza BLE.
             FlowController w każdym ticku sprawdza tę prawdę. Gdy SDK zwróci
             False w środku sesji, ExperimentState/CalibrationState dodają marker
             DISCONNECTED, zamykają plik EDF i wracają do menu — gdzie użytkownik
             może spokojnie połączyć ponownie i kontynuować.
```

```
Problem: Sztywny wybór headseta przy starcie aplikacji

Opis: Pierwsza wersja pokazywała jednorazowy dialog wyboru headseta przy starcie.
      Każda zmiana sprzętu (np. test na innym egzemplarzu Maxi, przełączenie
      na mock dla testu UI) wymagała restartu całej aplikacji. Po rozłączeniu
      czepka też nie było jak go ponownie podłączyć bez restartu.

Rozwiązanie: Dialog wyboru headseta pozostał przy starcie, ale po rozłączeniu
             czepka w trakcie sesji użytkownik wraca do menu głównego i może
             wcisnąć Reconnect bez ponownego otwierania dialogu.
             FlowController.eeg_headset jest opcjonalny — ustawiany przez dialog
             przy starcie, aktualizowany przez Reconnect w MainMenuState.
```

```
Problem: Kwantyzacja czasu trwania prób w events.tsv do wielokrotności ~100ms

Opis: Wartości duration w events.tsv (np. dla cue 4000ms) bywają zapisane jako
      4100ms lub 3900ms zamiast dokładnie 4000ms. Skoki są wielokrotnością ~100ms,
      nie są losowym jitterem.

Przyczyna: BrainAccess SDK dostarcza dane przez Bluetooth w paczkach po ~25 próbek
           (250 Hz → paczka co ~100ms). add_marker() zapisuje znacznik jako bieżący
           sample_idx (total_samples + buffer_pos). Gdy QElapsedTimer wykryje
           przekroczenie duration_ms i wywoła add_marker(), buffer_pos wskazuje
           na granicę ostatnio dostarczonej paczki BT — stąd granulacja 100ms.

Wpływ na dane: Czas trwania bodźca dla badanego jest poprawny — QElapsedTimer
               pilnuje rzeczywistego czasu wyświetlania cue. Błąd dotyczy tylko
               pozycji markera w pliku TSV (i EDF annotations), nie samego sygnału EEG.
               Dla motor imagery różnica 100ms jest pomijalna.

Nierozwiązane: Można by korygować sample_idx o overshoot (elapsed - duration_ms
               przeliczony na próbki), ale przy aktualnym zastosowaniu nie ma
               wystarczającego uzasadnienia dla tej złożoności.
```

```
Problem: Null pointer dereference w BrainAccess SDK na Windows

Opis: Podczas integracji z BrainAccess SDK na Windows aplikacja crashowała
      z EXCEPTION_ACCESS_VIOLATION (odczyt spod adresu 0x0000000000000000)
      podczas tworzenia obiektu EEGManager — jeszcze przed nawiązaniem
      połączenia BLE z urządzeniem. Problem nie dotyczył konfiguracji EEG
      ani czepka, lecz wewnętrznej inicjalizacji natywnego runtime'u SDK.

      Analiza stacktrace wskazała na natywną bibliotekę DLL (_dll.ba_eeg_manager_new()).
      Jest to klasyczny null pointer dereference w bibliotece C — crash następuje
      bezpośrednio w kodzie natywnym i nie można go przechwycić mechanizmem
      wyjątków Pythona. Przyczyna: wcześniejsze załadowanie PyQt6 wprowadza
      zależności DLL, które kolidują z inicjalizacją natywnego runtime'u SDK
      BrainAccess na Windows.

Rozwiązanie: Na Windows driver BrainAccess jest uruchamiany w osobnym subprocesie
             (multiprocessing.spawn), który startuje bez załadowanego PyQt6.
             Komunikacja z procesem głównym odbywa się przez pipe (IpcHeadsetDriver).
             Na Linux/macOS problem nie występuje — driver działa w tym samym procesie.
             Obejście jest przezroczyste dla reszty aplikacji: IpcHeadsetDriver
             implementuje ten sam protokół HeadsetDriver co BrainAccessDriver.
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
- Asynchroniczne łączenie z czepkiem w wątku — dziś `connect()` blokuje GUI na 5–10 s podczas negocjacji Bluetooth na Windows
- Pełna zgodność BIDS: dodanie sidecar `*_eeg.json` z metadanymi sesji (TaskName, PowerLineFrequency, EEGReference) oraz hierarchii folderów `sub-XX/ses-YY/eeg/`

---

## 11. Reproducibility Checklist

**Sprawdź przed oddaniem:**

- [x] Projekt da się uruchomić na czystym środowisku (tryb mock bez headseta)
- [x] Instrukcja uruchomienia działa krok po kroku
- [x] Wszystkie zależności są opisane (pyproject.toml)
- [x] Demo działa zgodnie z opisem

---

## 12. Załączniki

- [README.md](../README.md) — dokumentacja techniczna projektu (instrukcja uruchomienia, struktura kodu, konfiguracja headsetów, szczegóły formatu EDF)
- Konfiguracja sesji: `trials.config.yaml`, `brainaccess.config.yaml` (template'y: `*.example.config.yaml`)

---

## 13. Status projektu

W trakcie — protokół zbierania danych zaimplementowany i przetestowany na mocku; przed pierwszą sesją z uczestnikiem wymagane są pomiary z sekcji 7.5 (opóźnienie, SDK) oraz zgoda komisji ([protocol.md](protocol.md)). Integracja z klasyfikatorem i projekt BrainBoard w toku.

---
