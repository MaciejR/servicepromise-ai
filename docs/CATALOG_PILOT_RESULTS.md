# ServicePromise AI — wyniki prototypu T0–T1

## Follow-up on product versus packaging context, 3 November 2026

The revised Azure prompt asks for an exact quotation describing the product and abstains when the product color is absent. On eight new synthetic descriptions, the rules provider correctly identified the color or its absence in 3/8 cases and Azure in 7/8. The shared contract accepted two correct rows with either provider. It accepted two incorrect packaging colors from rules and none from Azure in this run. Two correct Azure suggestions were withheld because the validator still found competing colors. The remaining Azure error was an abstention on a product color stated in the source.

The application labels extracted values on withheld items as unverified proposals. A proposal does not enter the exported CSV or count as a delivered item. The test used one evaluation run per provider, a small synthetic sample and labels authored with the experiment. Operator review time and performance on original supplier data remain unmeasured.

2 listopada 2026. Wynik: lokalny prototyp działa, ale nie potwierdziliśmy przewagi AI ani wartości biznesowej scenariusza.

## Co wykonano

- Kontrakt `catalog-textiles-v1`: CSV wejściowy, limity, zakres kolorów i materiałów, kryteria odbioru i cena próbna.
- Lokalny pipeline: kontrola wejścia → ekstrakcja → walidacja dowodów i konfliktów → najwyżej jedna poprawka → CSV szkiców + raport + symulacja rozliczenia.
- Dwa rzeczywiste ekstraktory: deterministyczny parser regułowy oraz Azure OpenAI, niezależne od PayPal. Etykiety oczekiwań nie są odczytywane przez ekstraktory.
- 60 syntetycznych przypadków i dwa małe przykłady faktów z publicznych stron produktów. Pochodzenie i ograniczenia opisano w `examples/catalog/PROVENANCE.md`.
- Testy wejścia, eksportu, źródłowych SKU/cen, negacji i konfliktów, wymyślonych dowodów, próby poprawy, awarii AI i pełnego/częściowego rozliczenia.

## Wyniki rzeczywistych uruchomień

| Pomiar | Reguły | Azure OpenAI |
| --- | --- | --- |
| Decyzje zgodne z oczekiwaniami | 60/60 | 60/60 |
| Poprawnie odebrane kompletne przypadki | 44/44 | 44/44 |
| Błędne odbiory według etykiet próbnych | 0 | 0 |
| Błędne odrzucenia kompletnych przypadków | 0 | 0 |
| Poprawnie niedostarczone po przetwarzaniu | 10 | 10 |
| Wyłączone przed wyceną | 6 | 6 |
| Łączny czas procesu, bez pracy człowieka | 0,013 s | 123,413 s |
| Żądania modelu w teście 60 przypadków | 0 | 16 |
| Tokeny wejścia + wyjścia w tym teście | 0 | 13 880 |

Azure uruchomiono na istniejącym wdrożeniu `servicepromise-chat`; 40 przypadków rozwojowych zajęło 89,094 s, a 20 odłożonych 34,319 s. Czasy zależą od sieci, dostawcy i sekwencyjnego wykonywania małych partii. Są to pomiary tej próby, nie benchmark wydajności usługi produkcyjnej.

W dodatkowych dwóch publicznych przykładach obie metody odebrały DVALA i pozostawiły GURLI jako niedostarczony: kolor `naturalny` nie ma dozwolonego mapowania w kontrakcie. Nie zmienialiśmy słownika tylko po to, żeby zaakceptować ten przykład. Te dwa przypadki nie są wliczone do tabeli 60 przypadków.

`python -m pytest -q`: **45 testów przeszło**, obejmując dotychczasowe 12 testów aplikacji i 33 nowe przypadki prototypu. Nie zmieniano produkcyjnego frontendu, więc poprzedni build nie jest nową weryfikacją katalogu. Nie wykonano nowego wdrożenia ani transakcji PayPal.

## Co oznacza wynik

Przy obecnym kontrakcie walidator musi sam rozpoznać jedną jednoznaczną wartość z krótkiego słownika. Ten sam zestaw reguł potrafi ją wydobyć. LLM nie poszerza zatem zbioru dopuszczonych wyników, dodaje za to czas i koszt wywołań. W tym zakresie nie mamy uzasadnienia do przedstawiania AI jako istotnego wyróżnika produktu.

To również ograniczenie eksperymentu: przypadki i oczekiwania przygotował asystent, według tego samego wąskiego kontraktu. Podział 40/20 nie jest niezależną walidacją. W odłożonej części są tylko poprawne przypadki i błędy wejścia; przypadki niejednoznaczne znajdują się w części rozwojowej. Konieczny jest osobny, niezależnie opisany zestaw z rzeczywistych plików. Nie należy przedstawiać 60/60 jako wyniku generalizacji na katalogi klientów.

Nie zmierzono czasu ręcznej pracy, oszczędności 40%, gotowości do zapłaty ani faktycznej zgodności importu w sklepie. Nie mamy jeszcze oryginalnych plików dostawcy od potencjalnego użytkownika. Publiczne skróty faktów i syntetyczne dane nie zastępują takich materiałów.

## Decyzja i dalszy krok

**Wstrzymać T2–T5 do testu na rzeczywistych danych.** Baza prototypu jest gotowa do tego testu; nie ma obecnie podstaw do przebudowy płatności i UI wokół samego koloru oraz materiału.

Następny materiał potrzebny do decyzji: 1–2 anonimowe pliki dostawcy, ich oczekiwany import oraz przykłady poprawek wykonywanych ręcznie. Sprawdzamy ten sam pipeline i mierzymy czas wraz z kontrolą. Jeśli najtrudniejsza praca dotyczy rozumienia wariantów, wymiarów, kategorii lub dopasowania oferty do istniejących produktów, należy najpierw zaprojektować małą próbę dokładnie tego zadania, zamiast dodawać je od razu do MVP.

Warunek dalszej inwestycji pozostaje zgodny z planem: obserwowalna oszczędność pracy i wiarygodne kryteria odbioru. Jeśli dane wystarczy obsłużyć parserem, uczciwym rezultatem jest narzędzie regułowe — bez udawania przewagi AI.

## Gdzie są dowody

- `evaluation/catalog/rules/summary.json`: 60 przypadków parsera.
- `evaluation/catalog/azure-development/summary.json`: 40 przypadków Azure.
- `evaluation/catalog/azure-holdout/summary.json`: 20 przypadków Azure.
- Podkatalogi `simple`, `messy`, `edge`: pełne raporty i pliki wynikowe każdej grupy.
- `evaluation/catalog/public-rules/` i `public-azure/`: dodatkowe dwa publiczne przykłady.
- `backend/tests/test_catalog.py`: testy lokalnych reguł i przepływu, w tym provider z podstawionymi błędami. Testy z podstawieniem nie są przedstawiane jako rzeczywiste wywołania Azure.
