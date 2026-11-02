# Pochodzenie danych próbnych

`supplier_simple.csv`, `supplier_messy.csv` i `supplier_edge.csv` są **syntetyczne**. Wygenerował je skrypt `backend/tools/build_catalog_examples.py`. Nie są eksportami klienta ani wynikami wywiadów. Oczekiwane odpowiedzi w `expected.json` są zapisane przez asystenta i wymagają niezależnego przeglądu człowieka.

Podział obejmuje 40 przypadków rozwojowych i 20 odłożonych. Odłożonych przypadków nie użyto do dostrajania promptu po pierwszym wywołaniu Azure; nie stanowią jednak niezależnie przygotowanego zbioru, ponieważ dane i oczekiwania opracował ten sam asystent. Taki podział potwierdza działanie prototypu, nie jakość produkcyjną ani kryteria biznesowe G1.

## Publiczne przykłady faktów

`public_references.csv` zawiera dwa małe, ręcznie zestawione przykłady faktów z publicznych stron IKEA. Nie jest oryginalnym plikiem dostawcy ani informacją o współpracy. Nie kopiujemy pełnych opisów, zdjęć ani katalogu. Treść kolumny `supplier_text` jest skróconym zestawieniem atrybutów; nazwy i ceny dotyczą pozycji/pakietów na stronie, nie normalizowanej ceny jednej sztuki. Dane są migawką z 2 listopada 2026 i nie są aktualizowane automatycznie.

| source_id | Źródło | Zapisane fakty |
| --- | --- | --- |
| public-dvala | https://www.ikea.com/pl/pl/p/dvala-poszewka-niebieski-10615461/ | SKU 106.154.61; niebieski; bawełna; cena pakietu 19,99 PLN |
| public-gurli | https://www.ikea.com/pl/pl/p/gurli-poszewka-naturalny-80598731/ | SKU 805.987.31; naturalny; bawełna; cena 9,99 PLN |

`naturalny` nie jest mapowany automatycznie na `beige`, mimo że zdjęcie może tak wyglądać. To zamierzone ograniczenie słownika: próba ma pokazać również niedostarczenie bez zgadywania. Słownik nie był rozszerzany po tym teście.

## Profil eksportu

Nagłówki sprawdzono w dokumentacji Shopify: https://help.shopify.com/en/manual/products/import-export/using-csv . Eksport zawiera status `draft`, `Published on online store=false`, kolumny opcji dla pojedynczego wariantu i cenę bez symbolu waluty. Import w sklepie nie został wykonany. Przed użyciem cena produktu musi być interpretowana w tej samej walucie co waluta sklepu; CSV nie wykonuje przewalutowania.
