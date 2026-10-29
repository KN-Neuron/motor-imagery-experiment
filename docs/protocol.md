# Protokół badania: motor imagery (lewa / prawa dłoń)

Dokument opisuje protokół zaimplementowany w aplikacji w formie, którą można
dołączyć do wniosku do komisji etycznej. Pola oznaczone `[DO UZUPEŁNIENIA]`
wypełnia zespół badawczy: aplikacja i ten dokument **nie zawierają** numeru
zgody komisji ani jej nazwy.

> Parametry poniżej to **wartości domyślne** z `trials.example.config.yaml`.
> Aktualne wartości każdej sesji są zapisane w `session_metadata.json`
> (`trial_config`). Każda zmiana protokołu w kodzie musi być odzwierciedlona
> w tym pliku (zob. [Rejestr zmian protokołu](#rejestr-zmian-protokołu)).

## 1. Informacje formalne

| Pole | Wartość |
|------|---------|
| Tytuł badania | `[DO UZUPEŁNIENIA]` |
| Kierownik badania / kontakt | `[DO UZUPEŁNIENIA]` |
| Jednostka | Koło Naukowe Neuron, Politechnika Wrocławska |
| Komisja etyczna / numer zgody | `[DO UZUPEŁNIENIA]` |
| Administrator danych / IOD | `[DO UZUPEŁNIENIA]` |
| Wersja protokołu | `[DO UZUPEŁNIENIA]` (wersja aplikacji: hash commita w metadanych) |

## 2. Cel badania

Zebranie oznaczonych nagrań EEG podczas wyobrażania sobie (motor imagery) oraz
wykonywania (motor execution) zaciskania lewej i prawej dłoni, w celu
trenowania i oceny klasyfikatorów dla interfejsu mózg–komputer (projekt
BrainBoard). Dodatkowo rejestrowane są krótkie sekwencje artefaktów (mruganie,
zaciśnięcie szczęki, ruch głową) oraz spoczynek, potrzebne do czyszczenia
i oceny sygnału. `[DO UZUPEŁNIENIA: hipotezy / pytania badawcze]`

## 3. Uczestnicy

- Liczba uczestników: `[DO UZUPEŁNIENIA]`
- Kryteria włączenia / wyłączenia: `[DO UZUPEŁNIENIA]` (np. pełnoletność,
  brak chorób neurologicznych, brak padaczki: dobór kryteriów należy do
  zespołu i komisji).
- Rekrutacja i wynagrodzenie: `[DO UZUPEŁNIENIA]`

## 4. Zadania i struktura sesji

Sprzęt: czepek EEG BrainAccess (sucha / półsucha elektroda, model zapisany
w metadanych), próbkowanie 250 Hz (wartość z konfiguracji czepka). Monitor
wyświetla bodźce, uczestnik siedzi nieruchomo.

Kolejność (każdy punkt jest znacznikiem lub blokiem w `events.tsv`):

1. **Ekran uczestnika** (eksperymentator): pseudonim, numer sesji, potwierdzenie
   zgody. Brak imienia, nazwiska i innych danych bezpośrednio identyfikujących.
2. **Kontrola jakości sygnału** (≈ 10 s spoczynku): RMS i amplituda na kanał,
   ostrzeżenia (kanał płaski, nasycony, szum sieciowy 50 Hz, dryf DC, silny
   szum). Eksperymentator może poprawić kontakt elektrod albo kontynuować mimo
   ostrzeżeń: fakt kontynuacji jest zapisany w metadanych. Fragment spoczynku
   jest zapisywany (`qc_rest.npy`).
3. **Instrukcja** (ekran, po polsku i angielsku; kontynuacja klawiszem SPACJA).
4. *(opcjonalnie, domyślnie wyłączone)* **Procedura weryfikacyjna:** 3×
   mrugnięcie, 3× zaciśnięcie szczęki, 15 s oczy otwarte, 15 s oczy zamknięte
   (weryfikacja artefaktów i rytmu alfa); `condition=qc`.
5. **Blok spoczynku:** 2 min z oczami otwartymi, wzrok na krzyżyku
   (`REST_EYES_OPEN`); opcjonalnie spoczynek z oczami zamkniętymi
   (`REST_EYES_CLOSED`), domyślnie 0 s.
6. **Trening:** po 2 próby każdej klasy (4 próby), znacznik `PRACTICE`,
   `practice=true`: wykluczone z analizy.
7. **Bloki MI:** 4 bloki × 20 prób każdej z klas (lewa / prawa dłoń), czyli
   160 prób; w każdym bloku kolejność jest losowa, zbalansowana, a ta sama
   klasa nie występuje częściej niż 3 razy z rzędu. Między blokami ekran
   „Odpoczynek, naciśnij SPACJĘ” (przerwa wg potrzeb uczestnika).
8. **Blok artefaktów** (osobny, nie miesza się z blokami MI,
   `condition=artifact`): po 10 prób: podwójne mrugnięcie, zaciśnięcie szczęki,
   ruch głową.
9. **Ekran końcowy.**

Domyślnie klasy MI to **wyobrażenie** (`left_hand_imagery`,
`right_hand_imagery`: „WYOBRAŹ SOBIE zaciskanie LEWEJ dłoni, nie ruszaj
ręką”). Klasy **wykonania** (`left_hand_execution`, `right_hand_execution`:
„ZACIŚNIJ LEWĄ dłoń”) są dostępne jako osobne klasy w konfiguracji i nie są
mieszane z wyobrażeniem, o ile nie włączy się ich jawnie. `[DO UZUPEŁNIENIA:
czy badanie obejmuje wykonanie ruchu]`

### Przebieg jednej próby

| Etap | Domyślnie | Znacznik |
|------|-----------|----------|
| Fiksacja (krzyżyk) | 1,5 s | `FIXATION` |
| Wskazówka (tekst + obraz) | 1,0 s | `CUE_<KLASA>` |
| Okno wyobrażenia / wykonania | 4,0 s | `<KLASA>` (np. `LEFT_HAND_IMAGERY`) |
| Odstęp między próbami (pusty ekran), losowy | 2,0–3,5 s | `ITI` |

Odstęp (ITI) jest losowany jednostajnie z zadanego zakresu; ziarno generatora
(`seed`) jest zapisane w metadanych, więc sesję można odtworzyć.

### Szacowany czas

Z domyślnej konfiguracji (obliczone z generatora sesji): spoczynek 2 min,
trening ≈ 0,6 min, bloki MI ≈ 24,4 min, artefakty ≈ 4,6 min, razem
**≈ 31,5 min zapisu** + 7 ekranów sterowanych klawiszem (instrukcja, trening,
przerwy, koniec) + zakładanie czepka i kontrola jakości. Całkowity czas wizyty
`[DO UZUPEŁNIENIA po sesji pilotażowej]`. Uczestnik może w każdej chwili
wstrzymać sesję (przycisk pauzy) lub ją przerwać.

### Informacja zwrotna

Domyślnie **brak** informacji zwrotnej o „poprawności” (`feedback: none`).
Tryb `demo` (wyniki losowe, wyraźnie oznaczone na ekranie jako „FEEDBACK DEMO,
NIE PRAWDZIWY KLASYFIKATOR”) służy wyłącznie do pokazów i nie powinien być
używany w badaniu. Tryb `model` wymaga wytrenowanego klasyfikatora (obecnie
nie istnieje). Znaczniki `RESULT_*` są zapisywane tylko przy włączonym
feedbacku, a kolumna `feedback_mode` w `events.tsv` zapisuje tryb.

## 5. Zbierane dane

| Dane | Plik | Uwagi |
|------|------|-------|
| Sygnał EEG | `session.edf` | pseudonimizowany, 250 Hz |
| Znaczniki zdarzeń | `events.tsv` | onset, blok, próba, warunek, flagi |
| Synchronizacja | `sync_log.tsv` | czasy zegara monotonicznego |
| Metadane sesji | `session_metadata.json` | wersja aplikacji, sprzęt, konfiguracja, ziarno |
| Uczestnik | `participants.tsv` | kod, wiek (liczba lub przedział), płeć (opcjonalnie), ręczność, rozmiar czepka, doświadczenie z BCI, zgoda + data |
| Sesja | `sessions.tsv` | zmęczenie i sen (skala 1–5, opcjonalnie), notatki eksperymentatora |

Nie są zapisywane: imię, nazwisko, kontakt, nagrania wideo ani audio.
Pola wrażliwe (płeć, wiek, zmęczenie, sen, EHI) są opcjonalne. Notatki
eksperymentatora to tekst dowolny: **nie wolno w nich wpisywać danych
identyfikujących** (aplikacja nie jest w stanie tego sprawdzić).

Nagrania EEG mogą stanowić dane osobowe (szczególnie w połączeniu z innymi
danymi); kwalifikację prawną (RODO) określa `[DO UZUPEŁNIENIA]`.

## 6. Ryzyka i niedogodności

- Brak znanego ryzyka zdrowotnego związanego z pasywnym zapisem EEG (czepek
  rejestruje sygnał, nie stymuluje). Możliwy dyskomfort / ucisk czepka,
  zmęczenie i nuda przy ≈ 30 min powtarzalnych zadań, zmęczenie oczu.
- Migające bodźce (SSVEP) **nie są częścią domyślnego protokołu**. Jeśli
  zostaną włączone (`ssvep_focus`), wymagają oceny ryzyka u osób wrażliwych na
  migotanie (padaczka fotogenna) i wykluczenia takich osób. `[DO UZUPEŁNIENIA]`
- Przerwy: ekrany odpoczynku między blokami, pauza w dowolnym momencie.
- Zasady postępowania przy złym samopoczuciu uczestnika: `[DO UZUPEŁNIENIA]`.

## 7. Przechowywanie, anonimizacja i bezpieczeństwo danych

- Dane są pseudonimizowane: uczestnik jest identyfikowany kodem `sub-XXX`.
  Walidacja odrzuca kody ze spacjami, polskimi znakami i ostrzega przed
  kodami przypominającymi imię i nazwisko.
- Klucz łączący kod z tożsamością (jeśli istnieje, np. w dokumentach zgody)
  przechowuje się **osobno** od danych, w miejscu dostępnym tylko dla
  `[DO UZUPEŁNIENIA]`. Aplikacja takiego klucza nie tworzy.
- Katalog `sessions/` jest wyłączony z repozytorium (`.gitignore`) i nie może
  być publikowany przed spełnieniem wymogów komisji i RODO.
- Miejsce i okres przechowywania, kopie zapasowe, szyfrowanie dysku, dostęp:
  `[DO UZUPEŁNIENIA]`.
- Udostępnianie danych (np. zbiór w formacie BIDS przygotowany przez
  `tools/export_bids.py`) wyłącznie w formie pseudonimizowanej i zgodnie ze
  zgodą uczestnika: `[DO UZUPEŁNIENIA]`. Dla wiarygodnej anonimizacji
  rozważyć wiek w przedziałach i usunięcie pola notatek przed publikacją.

## 8. Zgoda i wycofanie zgody

- Zgoda świadoma jest zbierana na piśmie przed sesją (`[DO UZUPEŁNIENIA:
  wzór formularza]`); aplikacja wymaga potwierdzenia zgody i jej daty, aby
  rozpocząć nagranie (pola `consent_given`, `consent_date`).
- Uczestnik może przerwać sesję w każdej chwili bez podania przyczyny. Przerwana
  sesja jest oznaczona (`ABORTED`, `session_completed: false`).
- Wycofanie zgody: `[DO UZUPEŁNIENIA: procedura, termin, usunięcie danych]`.
  Ponieważ dane są pseudonimizowane, usunięcie wymaga zachowania klucza
  kodu (lub innej ustalonej procedury); po anonimizacji i publikacji
  usunięcie może być niemożliwe: należy to jasno napisać w formularzu zgody.

## 9. Ograniczenia metodologiczne (do ujawnienia w opisie metod)

- Opóźnienie marker → ekran → EEG **nie zostało zmierzone** (procedura:
  [latency.md](latency.md)). Do czasu pomiaru nie należy raportować dokładności
  czasowej poniżej okresu próbkowania.
- Wykrywanie utraty próbek nie działa dla czepka BrainAccess (SDK: brak
  potwierdzonego licznika próbek).
- Ostatni rekord EDF jest dopełniony zerami; koniec danych: `END_OF_DATA` i
  `n_samples_real`.
- Zakres EDF ±3200 µV; próbki spoza zakresu są obcinane (liczone w metadanych).
- Progi kontroli jakości to wartości startowe, niezwalidowane.
- SSVEP jest niezwalidowany (miganie z zegara, bez synchronizacji z VSync).
- Analiza domyślna: pominąć `practice=true` oraz próby z `interrupted=true`
  (wszystkie wiersze o tym samym `block_id` i `trial_id`).

## Rejestr zmian protokołu

Każda zmiana zachowania aplikacji wpływająca na protokół jest tu opisana.

| Zmiana | Opis |
|--------|------|
| Feedback | Usunięto fałszywy feedback (wynik = prawdziwa klasa bodźca). Domyślnie `none`; `demo` oznaczony na ekranie; `model` tylko interfejs. `RESULT_*` tylko przy włączonym feedbacku. |
| Imagery / execution | Rozdzielone klasy `*_imagery` i `*_execution`; stare `*_clench` mapują się na wykonanie z ostrzeżeniem. Jednoznaczne instrukcje PL/EN. |
| Struktura sesji | Instrukcja, trening (`PRACTICE`), bloki z przerwami, ograniczenie serii tej samej klasy, spoczynek jako osobny blok, ITI z jitterem (2,0–3,5 s zamiast stałego odstępu), ziarno zapisane w metadanych. |
| Artefakty | Osobny blok `condition=artifact`, nie mieszany z MI. |
| Pauza | Licznik kroku zatrzymywany na czas pauzy; krok z pauzą: `interrupted=true`. Wcześniej krok kończył się natychmiast po wznowieniu. |
| Znaczniki | `sync_log.tsv`, `DATA_GAP` (gdy sterownik raportuje), `END_OF_DATA`, ostrzeżenie o przycięciu sygnału. |
| SSVEP | Miganie liczone z zegara; ostrzeżenie o odświeżaniu monitora; oznaczone jako niezwalidowane. |
| Metadane | Kod uczestnika + numer sesji zamiast dowolnej nazwy folderu; `participants.tsv`, `sessions.tsv`, `session_metadata.json`; eksport BIDS. |
| Kontrola jakości | Ekran jakości sygnału przed nagraniem; opcjonalna procedura weryfikacyjna. |
