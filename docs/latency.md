# Opóźnienie marker → ekran → EEG

**Status: niezmierzone.** Ten dokument opisuje procedurę pomiaru i zawiera
szablon wyników. Żadne liczby opóźnienia nie są tu podane, bo nie zostały
zmierzone; do czasu pomiaru nie należy raportować dokładności czasowej
lepszej niż okres próbkowania (4 ms przy 250 Hz), a i to dotyczy wyłącznie
przeliczenia indeksu próbki na czas, nie opóźnienia bodźca.

## Skąd może brać się opóźnienie

```
tick (10 ms) -> add_marker -> paintEvent -> kompozytor / VSync -> monitor
                     |
                     +-> indeks próbki = próbki odebrane do tej chwili
                         (+ opóźnienie transmisji Bluetooth i bufora SDK)
```

1. **Marker vs. rzeczywista próbka:** marker dostaje numer próbki *odebranej*
   przez aplikację. Próbki są opóźnione względem rzeczywistości o czas
   transmisji i buforowania w czepku / SDK (nieznany).
2. **Marker vs. ekran:** marker jest zapisywany w chwili, gdy logika zmienia
   krok, a nie gdy piksele się zmieniają. Pętla ma 10 ms; rysowanie, kompozytor
   systemu i monitor dodają kolejne opóźnienie i jitter.
3. **Zegar monotoniczny:** `sync_log.tsv` zapisuje `perf_counter_ns` markera,
   czas ostatniego pakietu EEG, planowany start kroku i koniec pierwszego
   `paintEvent` (`display_perf_counter_ns`). To **nie** jest chwila pojawienia
   się obrazu na ekranie, tylko dolna granica (obraz pojawia się później).
   Rozstęp `display - marker` mierzy część opóźnienia po stronie oprogramowania.

## Procedura (fotodioda)

Wymagany sprzęt (jeśli go nie ma, zostaw pola puste: `[DO UZUPEŁNIENIA]`):

- fotodioda / czujnik światła przyklejony do rogu ekranu w miejscu białego
  kwadratu (200×200 px w lewym górnym rogu);
- tor sygnałowy sprowadzający wyjście czujnika do zakresu wejścia EEG
  (zwykle wymaga dzielnika / wzmacniacza: napięcia fotodiody są o rzędy
  wielkości większe od µV, a zakres EDF to ±3200 µV);
- wejście kanału EEG (lub wejście pomocnicze), do którego można podłączyć ten
  sygnał. Czy dany czepek BrainAccess udostępnia takie wejście: `[DO
  SPRAWDZENIA W DOKUMENTACJI SPRZĘTU]`.

Kroki:

1. Ustaw te same warunki co w badaniu: monitor, rozdzielczość, odświeżanie,
   tryb pełnoekranowy, ten sam komputer, to samo połączenie z czepkiem.
2. Zapisz parametry sprzętu w szablonie poniżej.
3. Uruchom nagranie:
   ```bash
   python tools/measure_latency.py record --model MAXI_32CH --flashes 100
   ```
   (`--mock` do próby bez sprzętu; wtedy brak fotodiody i `analyze` nie ma
   sensu). Skrypt miga białym kwadratem co 1 s i przy każdym błysku zapisuje
   marker `FLASH` do zwykłej sesji w `sessions/latency/`.
4. Przeanalizuj:
   ```bash
   python tools/measure_latency.py analyze sessions/latency/<katalog> --channel <kanał>
   ```
   Skrypt wykrywa narastające zbocza w kanale z fotodiodą i dla każdego markera
   `FLASH` podaje czas do najbliższego następnego zbocza, oraz (z
   `sync_log.tsv`) czas marker → koniec `paintEvent`. Wyniki: `latency_results.json`
   w katalogu sesji (mediana, 5. i 95. percentyl, min, max, liczba sparowanych
   błysków).
5. Powtórz pomiar dla każdej konfiguracji używanej w badaniu (pełny ekran /
   okno, każdy używany monitor) i zapisz wyniki osobno.
6. Rozdzielczość pomiaru wynosi jedną próbkę (4 ms przy 250 Hz) plus jitter
   czasu narastania fotodiody i progu: podaj ją razem z wynikiem.

Procedura zastępcza bez fotodiody (**tylko transmisja**, nie ekran):
podłącz generator sygnału testowego do wejścia EEG, wyzwalaj go i zapisuj
marker w tej samej chwili z poziomu skryptu; różnica daje opóźnienie
marker → EEG, ale pomija opóźnienie wyświetlania.

## Szablon wyników

Wypełnij po pomiarze. Nie przepisuj wartości z innych instalacji.

| Pole | Wartość |
|------|---------|
| Data, osoba mierząca | `[DO UZUPEŁNIENIA]` |
| Wersja aplikacji (hash commita) | `[DO UZUPEŁNIENIA]` |
| Komputer / system | `[DO UZUPEŁNIENIA]` |
| Monitor (model, rozdzielczość, odświeżanie Hz) | `[DO UZUPEŁNIENIA]` |
| Tryb wyświetlania (pełny ekran / okno, VSync) | `[DO UZUPEŁNIENIA]` |
| Czepek (model, nazwa urządzenia), wersja SDK | `[DO UZUPEŁNIENIA]` |
| Czujnik / tor sygnałowy, kanał | `[DO UZUPEŁNIENIA]` |
| Liczba błysków / sparowanych zboczy | `[DO UZUPEŁNIENIA]` |
| Opóźnienie marker → zbocze, mediana [ms] | `[DO UZUPEŁNIENIA]` |
| 5. – 95. percentyl [ms] | `[DO UZUPEŁNIENIA]` |
| Min / max [ms] | `[DO UZUPEŁNIENIA]` |
| Marker → koniec `paintEvent`, mediana [ms] | `[DO UZUPEŁNIENIA]` |
| Rozdzielczość pomiaru [ms] | `[DO UZUPEŁNIENIA]` |
| Czy opóźnienie jest stałe (można odjąć)? | `[DO UZUPEŁNIENIA]` |
| Uwagi / anomalie (gubione klatki, skoki) | `[DO UZUPEŁNIENIA]` |

Jeśli opóźnienie jest stabilne (mały jitter), można je odjąć przy analizie
(przesunięcie onsetów); jeśli jitter jest porównywalny z oknami analizy,
należy to opisać w metodach.
