# Kontrakt prototypu: catalog-textiles-v1

Status: lokalny prototyp T0–T1, bez integracji nowego procesu z publiczną aplikacją i bez transakcji płatniczych.

## Wejście

CSV UTF-8, opcjonalny BOM, do 256 KiB i 20 wierszy, z dokładnym nagłówkiem:

```csv
source_id,sku,name,price,currency,supplier_text
```

Identyfikatory muszą być unikalne, wszystkie pola niepuste. `supplier_text` ma maksymalnie 2000 znaków; pozostałe pola do 160. Cena ma postać dziesiętną z kropką i maksymalnie dwiema cyframi po kropce. Nie używamy float, nie zmieniamy SKU i nie usuwamy zer początkowych. Jedna partia używa jednej jawnie wskazanej waluty produktu: PLN, EUR, USD lub GBP. Zapis ceny jest zachowany w eksporcie.

Wiersze o błędnej cenie, walucie, duplikatach lub treści zaczynającej się jak formuła arkusza są wyłączane przed demonstracyjną wyceną. Nie dopisujemy apostrofów do SKU. Plik o złej strukturze lub przekroczonych limitach jest odrzucany w całości. Użytkownik nie zatwierdza zakupów w tym prototypie; wycena stanowi wyłącznie część raportu lokalnego.

## Ekstrakcja

Nazwa, SKU, cena i waluta pozostają danymi źródłowymi. Model otrzymuje wyłącznie `source_id`, `supplier_text`, opis kontraktu i ewentualne błędy poprzedniej próby. Schemat odpowiedzi zabrania pól ceny, zwrotu, SKU i dodatkowych instrukcji.

Wydobywamy dwa wymagane atrybuty:

- kolor: blue, red, green, white, black, beige, grey;
- materiał: cotton, linen, polyester, wool.

Obsługiwane polskie i angielskie aliasy oraz reguły pól są jawne w `backend/app/catalog/core.py`. Nie wykonujemy swobodnej klasyfikacji kolorów ani domyślnego sprowadzania mieszanek do jednego materiału.

Każda wartość modelu zawiera `value`, dosłowny `term` i dosłowny `quote`. Walidator wymaga, aby term odpowiadał wartości ze słownika i występował we właściwym fragmencie źródła. Jawne pola produktu, takie jak `Kolor:` i `Product material:`, mają pierwszeństwo przed wzmianką o etykiecie/opakowaniu. Sprzeczne pola, nieobsługiwane wartości, rozpoznana negacja i brak atrybutu blokują odbiór. Rozpoznawanie kontekstu i negacji jest ograniczone; poprawność walidatora nie jest gwarancją prawdy źródła.

Jedna pierwsza próba i najwyżej jedna poprawka. Po poprawce wynik jest `accepted` albo `undelivered`, z kodami przyczyn. Błąd dostawcy modelu jest błędem wykonania, nie oceną jakości. Identyfikatory odpowiedzi modelu muszą odpowiadać dokładnie przesłanej partii.

## Eksport i rozliczenie demonstracyjne

`products.csv` zawiera wyłącznie odebrane pozycje, jako szkice Shopify według sprawdzonych nagłówków. Opis źródłowy jest kodowany jako tekst HTML, aby nie wykonywać osadzonych znaczników. Raport zachowuje źródło, wycenę, błędy, próby, dowody, hash danych i hash eksportu. Hash nie jest podpisem ani dowodem autentyczności informacji.

Cena próbna to 100 centów USD za wiersz dopuszczony przed przetwarzaniem. Kwota kwalifikująca się do zwrotu to 100 centów razy liczba niedostarczonych pozycji; pełne niedostarczenie odpowiada 100% wyceny. Każdy raport ma `simulation=true` i `payment_executed=false`. Żaden proces tego prototypu nie wywołuje PayPal.

Prototyp zapisuje wynik na koniec lokalnego uruchomienia. Trwałe zamówienia, wznowienie po restarcie, wersjonowane migracje, budżet zadania i operacje finansowe należą do T2 i dalszych etapów. Nie deklarujemy, że są już zaimplementowane w nowej ścieżce.

## Uruchomienie

Z katalogu `backend/`, po instalacji dotychczasowych zależności:

```bash
python -m app.catalog.cli ../examples/catalog/supplier_messy.csv \
  --provider rules --currency PLN --output ../evaluation/catalog/manual-rules

python -m app.catalog.cli ../examples/catalog/supplier_messy.csv \
  --provider azure --currency PLN --env-file .env \
  --output ../evaluation/catalog/manual-azure
```

Wymagane są istniejące `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_DEPLOYMENT` w lokalnym `.env` lub środowisku. Wykorzystujemy pierwszeństwo zmiennych środowiska nad `.env`; inny klucz w środowisku trzeba usunąć albo poprawić przed uruchomieniem. Sekrety nie trafiają do repo ani plików wynikowych.

Porównanie na danych próbnych:

```bash
python tools/benchmark_catalog.py --provider rules --split all \
  --output ../evaluation/catalog/rules
python tools/benchmark_catalog.py --provider azure --split development \
  --output ../evaluation/catalog/azure-development
python tools/benchmark_catalog.py --provider azure --split holdout \
  --output ../evaluation/catalog/azure-holdout
python -m pytest -q
```

Wywołania Azure naliczają zużycie modelu. Nie wymagają danych PayPal ani zmiany `PAYMENT_MODE`. Parser regułowy jest rzeczywistą implementacją deterministyczną; nie jest fixture udającą model. Oczekiwane etykiety zbioru próbnego są używane tylko do pomiaru, nigdy jako odpowiedzi ekstraktora.
