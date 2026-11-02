# ServicePromise AI — plan korekt MVP

Data: 2 listopada 2026. Status: wykonano lokalny prototyp techniczny T0–T1 i porównanie Azure OpenAI z parserem regułowym. Szczegóły: [wyniki pilotażu](CATALOG_PILOT_RESULTS.md). Weryfikacja z rzeczywistym odbiorcą, pomiar pracy ręcznej i import do sklepu pozostają do wykonania. Nowa ścieżka nie jest wdrożona w publicznej aplikacji.

Decyzja po pilotażu: wstrzymać inwestycję w T2–T5 do pozyskania rzeczywistych danych pokazujących przewagę AI nad regułami. Na obecnych 60 syntetycznych przypadkach obie metody osiągnęły 60/60 zgodnych decyzji. Nie spełniono bramki G1.

## 1. Decyzja i hipoteza produktu

Zmieniamy demonstracyjną usługę „brief marketingowy za 12 USD” na przygotowanie katalogu produktów z danych dostawcy. Zachowujemy ServicePromise AI jako nazwę roboczą oraz bazę techniczną zamówień, płatności i historii zdarzeń.

Docelowy użytkownik: osoba prowadząca mały sklep albo obsługująca katalogi kilku sklepów, która ręcznie przepisuje i porządkuje informacje od dostawców.

Hipoteza wartości: użytkownik otrzymuje plik do importu, raport problemów oraz jasne rozliczenie za dostarczone pozycje. Łączny czas przygotowania i kontroli powinien być krótszy niż praca ręczna. Popyt, cena i oszczędność czasu nie są jeszcze potwierdzone.

Obietnica MVP: „Przygotujemy uzgodnione pozycje katalogu zgodnie z pokazanym schematem. Spróbujemy poprawić błędy. Za niedostarczone pozycje zwrócimy przypisaną im część opłaty”. Nie obiecujemy bezbłędności wszystkich informacji o produkcie, wzrostu sprzedaży ani zgodności prawnej oferty.

## 2. Zakres pierwszej wersji

- Jedna usługa, jeden sprzedawca i jedna partia do 20 prostych produktów.
- Wejście: CSV UTF-8, maksymalnie 256 KiB, ze stałymi kolumnami `source_id`, `sku`, `name`, `price`, `currency`, `supplier_text`. Nazwa, SKU, cena i waluta są wartościami źródłowymi wskazanymi przez użytkownika; opis może zawierać nieuporządkowane atrybuty.
- Jedna waluta cen produktów w partii, jawnie wybrana w formularzu. Waluta rozliczenia usługi jest odrębna; w Sandbox używamy USD. Nie przeliczamy cen produktów.
- AI wydobywa i porządkuje ograniczony zestaw atrybutów: kolor i materiał. Do wartości dołącza dosłowny fragment źródła. Brakująca informacja ma pozostać pusta; domysły nie są uzupełnieniem danych.
- Kontrakt `catalog-v1` określa wymagane pola i atrybuty przed wyceną. Początkowo obsługujemy proste produkty z wybranego, wąskiego rodzaju asortymentu; przykładem do walidacji są tekstylia domowe. Nie obiecujemy obsługi dowolnej kategorii.
- Wynik: CSV zaakceptowanych pozycji, osobny raport odrzuceń i dowodów oraz rozliczenie partii. Odrzucone pozycje nie trafiają do pliku przeznaczonego do importu.
- Jeden profil eksportu dla nowych prostych produktów Shopify, jako szkice. Dokładne nagłówki, zależności pól i mapowanie atrybutów ustalamy z aktualnym przykładowym plikiem Shopify i sprawdzamy rzeczywistym importem testowym. Do tego czasu używamy określenia „plik zgodny z naszym schematem”, bez deklaracji potwierdzonej zgodności z importerem Shopify.
- Atrybuty trafiają do ustalonych tagów, np. `color:blue`, a nie do nieutworzonych automatycznie metafieldów. Opis źródłowy jest zachowany po bezpiecznym przygotowaniu do eksportu; generowanie tekstów reklamowych nie wchodzi do tej wersji.

Poza zakresem: warianty produktów, zdjęcia, OCR/PDF, pobieranie stron dostawców, edycja istniejącego katalogu, publikacja przez API sklepu, tłumaczenia, marketplace wielu sprzedawców, subskrypcje i obsługa pieniędzy produkcyjnych.

## 3. Warunki odbioru i granice gwarancji

| Sprawdzenie | Jak je wykonujemy | Skutek |
| --- | --- | --- |
| Poprawne wejście | Parser CSV, limity, unikalne identyfikatory, obowiązkowe wartości, cena typu Decimal, zgodna waluta | Jawnie nieprawidłowe wiersze wyłączone przed płatnością; użytkownik widzi powód |
| Zachowanie danych krytycznych | Porównanie SKU, ceny i waluty z niezmiennym źródłem po ściśle zdefiniowanej normalizacji | Rozbieżność blokuje odbiór pozycji |
| Kompletność pozycji | Wszystkie pola wymagane przez zaakceptowany kontrakt `catalog-v1` | Brak oznacza poprawkę, następnie niedostarczenie |
| Dowód dla atrybutu | Fragment źródła istnieje w `supplier_text`; normalizacja korzysta z jawnego słownika, a dopasowanie sprawdza właściwy fragment | Niepotwierdzony atrybut nie przechodzi odbioru |
| Niejednoznaczność | Sprzeczne wartości albo brak jednoznacznego mapowania na dozwoloną wartość | `needs_review`; po zakończeniu automatycznej próby pozycja pozostaje niedostarczona |
| Eksport | Zgodne nagłówki i zależności, poprawne kodowanie/quoting, unikalne identyfikatory eksportowe, kontrolowany status szkicu | Wadliwy plik nie jest gotową dostawą |
| Sugestia AI | Opcjonalny komentarz do niepewności | Nie ustala statusu płatności ani kwoty zwrotu |

Sam fakt, że cytat występuje w źródle, nie dowodzi poprawnego przypisania znaczenia. Dlatego ograniczamy słowniki i kategorie, mierzymy zgodność na danych opisanych przez człowieka oraz nie przedstawiamy sprawdzenia cytatu jako dowodu prawdziwości produktu.

Usuwamy średnią ocen 0–100 jako podstawę rozliczenia, próg 70, warunki liczby słów i nagłówków oraz procentowe kary za formatowanie tekstu. Wersja `v1` pozostaje historyczną polityką wcześniejszych zamówień; nie zmieniamy ich warunków wstecz.

## 4. Wycena i zwroty

1. Kontrola wejścia wskazuje wiersze dopuszczone i odrzucone. Użytkownik zatwierdza dokładną listę pozycji objętych usługą.
2. Serwer zapisuje niezmienny snapshot wejścia, kontraktu, profilu eksportu, pozycji, cen jednostkowych i limitu prób. Zmiana danych wymaga nowej wyceny.
3. Cena demonstracyjna to 1 USD za pozycję. To parametr testowy, nie zweryfikowana cena rynkowa. Kwoty zapisujemy w centach; ceny produktów obsługujemy oddzielnie.
4. Po potwierdzeniu płatności wykonujemy przetwarzanie i walidację. Każda pozycja ma najwyżej jedną próbę poprawy poza pierwszym przetworzeniem. Poprawka dostaje konkretne kody błędów; dane źródłowe pozostają niezmienne.
5. Pozycje bez potwierdzonego spełnienia kontraktu po tej próbie mają status niedostarczonych. W MVP `needs_review` nie blokuje bezterminowo rozliczenia i jest traktowane jako niedostarczenie. Operator nie może ręcznie obniżyć zwrotu po zakupie.
6. Zwrot jest sumą cen niedostarczonych pozycji. Przykład: 20 × 1 USD, 18 odebranych, 2 niedostarczone → 2 USD zwrotu. Pełne niedostarczenie → pełny zwrot. Nie stosujemy limitu 50%.
7. Błąd dostawcy AI jest błędem wykonania, a nie niską oceną jakości. Po ograniczonej ponownej próbie niedokończone pozycje kwalifikują się do zwrotu. Zapisane, poprawnie dostarczone pozycje nie są generowane ponownie.
8. Gdy wspólny plik eksportu jest niepoprawny, najpierw odtwarzamy go z zapisanych danych. Jeśli nie da się dostarczyć poprawnego pliku w budżecie zadania, całą dostawę uznajemy za nieudaną.
9. Zadanie ma konfigurowalny budżet wykonania i odtwarzalny stan. Na początek 10 minut na partię; to limit operacyjny i moment finalizacji niedostarczonych pozycji, bez obietnic szybkości modelu. Jeżeli aplikacja jest niedostępna, rozliczenie następuje po wznowieniu — nie reklamujemy gwarantowanego terminu przelewu.

MVP realizuje jedną finalną decyzję i najwyżej jeden zwrot dla danej partii. Ponowna próba komunikacji z PayPal używa tej samej zapisanej operacji i kwoty. Zmiana decyzji po finalizacji wymagałaby osobnego procesu, który jest poza zakresem tej wersji.

Pobranie opłaty przed pracą odpowiada usłudze przetwarzania partii z możliwością częściowego niedostarczenia. To także hipoteza do sprawdzenia z użytkownikiem. Jeśli odbiorcy preferują rozliczenie wyłącznie po wyniku, należy porównać wariant autoryzacji i późniejszego pobrania; nie wybieramy zwrotów tylko dla efektu demonstracji.

## 5. Etapy i kryteria przejścia

| Etap | Zadania i wynik | Warunek zakończenia | Szacunek aktywnej pracy |
| --- | --- | --- | --- |
| T0 — potrzeba i kontrakt | Dwa przykładowe pliki z jednego rodzaju asortymentu; ręczny rezultat odniesienia; rozmowy z 1–2 odbiorcami, jeśli mamy do nich dostęp; zamrożony schemat i warunki odbioru | Umiemy wskazać, kto wykonuje tę pracę, co poprawia ręcznie i za jaki rezultat zapłaci. Przykłady pokazują potrzebę przetwarzania języka, nie tylko zmiany nazw kolumn | 2–3 h + oczekiwanie na materiały |
| T1 — próba wartości AI | Narzędzie lokalne: ekstrakcja → dowody → walidacja → jedna poprawka → eksport. Bez płatności | Przegląd przez człowieka pokazuje oszczędność pracy i brak przeoczonych zmian pól krytycznych. Jeśli narzędzie wymaga podobnej lub większej pracy niż ręczne przygotowanie, wracamy do zakresu | 3–5 h |
| T2 — zamówienia i rozliczenie | Model partii i pozycji, zapis kontraktu, migracja, trwały stan zadania, czysta funkcja wyliczająca rozliczenie | Po restarcie można wznowić pracę; równoległe żądania nie uruchamiają drugiego zadania ani drugiego rozliczenia | 4–6 h |
| T3 — ekran produktu | Wgranie CSV, podgląd, wycena, wyniki pozycji, porównanie źródła i wyniku, pobranie plików i kwota rozliczenia | Użytkownik przechodzi całą ścieżkę; odróżnia dane demonstracyjne, prawdziwe AI oraz status zwrotu | 3–4 h |
| T4 — weryfikacja przed PayPal | Zestaw opisanych przypadków, próba importu Shopify, pomiar czasu wraz z kontrolą, testy błędów i granic rozliczenia | Spełniona bramka G1 opisana poniżej; w przeciwnym razie korygujemy zakres i nie dokładamy integracji płatności | 2–3 h |
| T5 — PayPal Sandbox | Checkout/capture, rzeczywisty częściowy i pełny zwrot, odtwarzanie niepewnych odpowiedzi, potwierdzanie statusu | Udokumentowane testy pełnej i częściowej dostawy, timeoutu i powtórzenia żądania; żaden zwrot oczekujący nie jest oznaczony jako zakończony | 3–5 h |
| T6 — wdrożenie i zgłoszenie | Sprawdzenie migracji, wdrożenie Azure, scenariusz demo, README, publiczne repo i film | Cały scenariusz działa na wdrożeniu, a opis odpowiada rzeczywistym możliwościom | 2–3 h |

Łącznie orientacyjnie 19–29 godzin pracy technicznej i przygotowawczej. Szacunek nie obejmuje oczekiwania na próbki, dostępu do sklepu testowego, logowania ani nieprzewidzianych problemów dostawców. Po T1 należy go zaktualizować. Przy budżecie 10–15 godzin najpierw realizujemy T0–T1 i podejmujemy decyzję o dalszej inwestycji; nie obiecujemy całego zakresu w tym czasie.

### G1 — warunki rozpoczęcia integracji PayPal

- Zestaw 60 produktów: 20 prostych, 20 z nieuporządkowanymi opisami, 20 z brakami/sprzecznościami i danymi brzegowymi. Materiały syntetyczne są oznaczone; nie przedstawiamy ich jako dowodu popytu. Co najmniej 20 przypadków jest odłożonych i nie służy do strojenia promptów lub słowników.
- Dla każdego przypadku człowiek ustala oczekiwane wartości, fragmenty źródła oraz dopuszczalny wynik: odebrany, wyłączony przed zakupem lub niedostarczony po przetworzeniu.
- Na odłożonym zestawie nie obserwujemy błędnie przyjętego SKU, ceny ani waluty. To wynik małej próby, nie obietnica zerowego ryzyka produkcyjnego.
- Co najmniej 90% pozycji z kompletnymi i jednoznacznymi danymi przechodzi po najwyżej jednej poprawce. Mianownik i liczba wykluczeń są raportowane, aby nie poprawiać wyniku ukrywaniem trudnych pozycji.
- Niepewne lub sprzeczne dane nie są eksportowane jako potwierdzone. Rejestrujemy też błędne odrzucenia; narzędzie, które zwraca wszystko, nie spełnia celu.
- W porównaniu na tych samych danych czas automatyzacji wraz z kontrolą i poprawkami jest przynajmniej o 40% krótszy od przygotowania ręcznego. To cel testu, nie obecny rezultat ani deklaracja marketingowa.
- Jeden rzeczywisty import do sklepu testowego potwierdza zgodność ustalonego profilu. Bez dostępu do sklepu nie przechodzimy z deklaracji zgodności schematu do deklaracji potwierdzonej integracji Shopify.
- Kwoty zgadzają się z wynikiem dla 0%, części i 100% niedostarczenia; wiersze odrzucone przed zakupem nie są płatne; klient widzi zasady przed checkoutem.

## 6. Mapa zmian w obecnym kodzie

| Obszar | Planowana zmiana |
| --- | --- |
| `backend/app/config.py` | Oddzielić `AI_MODE=fixture|azure` od `PAYMENT_MODE=demo|sandbox`. Umożliwić kontrolowany test prawdziwego AI bez PayPal. Kombinacja Sandbox + fixture jest dostępna wyłącznie w testach; działania z płatnym AI nadal wymagają autoryzacji i limitu zużycia |
| `backend/app/quality.py` | Wycofać generowanie briefów z nowej ścieżki. Dodać moduły ekstrakcji, walidacji, eksportu i deterministycznego rozliczenia. Walidatory nie wykonują wywołań modelu |
| `backend/app/db.py` | Dodać osobne tabele dla `CatalogJob`, `CatalogItem`, zapisów prób i finalnego rozliczenia. Zapisać źródło, jego hash, wersję kontraktu, wycenę, błędy walidacji, historię prób i finansowe identyfikatory |
| Migracje | Wprowadzić wersjonowaną migrację; samo `create_all` nie wystarczy. Wykonać kopię SQLite i próbę migracji na jej kopii. Historycznych zamówień z polityką v1 nie przeliczać nowymi regułami |
| `backend/app/main.py` | Dodać osobną ścieżkę API `/api/catalog/jobs`: przygotowanie i wycena, potwierdzenie kontraktu, checkout/capture, uruchomienie, odczyt statusu, pliki i rozliczenie. Wycena i kwoty zawsze po stronie serwera |
| Wykonanie zadania | Dla jednej instancji użyć trwałych rekordów kolejki i jednego ograniczonego workera w aplikacji. Zapis przed wywołaniem zewnętrznym, zapis wyniku każdej ukończonej pozycji, wznowienie po restarcie i rozpoznanie przeterminowanej pracy. Nie trzymać transakcji SQLite przez wywołania AI lub PayPal |
| `backend/app/paypal.py` | Zachować bazę OAuth/Orders/Payments, zmienić opis usługi i podłączyć nowy snapshot kwoty. Utrwalać zamiar operacji przed wywołaniem. Sprawdzać wynik i zasób dostawcy po niepewnej odpowiedzi; uwzględnić zasady i okres przechowywania idempotency keys |
| `frontend/src/main.tsx` | Zastąpić brief, wskaźnik 70/100 i kary procentowe widokami partii. Wydzielić komponenty i typy: import, wycena, wyniki, dowody, rozliczenie. Pokazać, co zostało dostarczone, dlaczego coś odrzucono i czy zwrot jest wymagany, wysłany, oczekujący czy potwierdzony |
| `backend/tests/` | Dodać testy reguł, rozliczeń, retry/restartu, izolacji zadań i błędów dostawców. Zestaw ewaluacji modelu prowadzić osobno od testów z mockami |
| README i deployment | Zaktualizować obietnicę, zakres, źródła i instrukcje. Oddzielnie podawać wyniki testów modelu, testów z mockami i rzeczywistych testów Sandbox. Rozbudowa infrastruktury nie jest pierwszym zadaniem |

Trwały worker w jednej instancji jest kompromisem MVP, nie architekturą do skalowania. Wznawianie może powtórzyć wywołanie AI po awarii pomiędzy odpowiedzią a zapisem; ustalamy limit prób i kosztu. Operacje finansowe wymagają osobnego potwierdzania u dostawcy i nie mogą opierać się na założeniu, że brak odpowiedzi oznacza brak wykonania.

## 7. Niezbędne testy zachowania

1. Wejście: puste, zduplikowane i błędne wiersze, różne kodowania, przecinki/cudzysłowy, nietypowe znaki w SKU, limity wielkości; odrzucenia przed zakupem są widoczne.
2. Odbiór: cena i SKU pozostają identyczne; zmiana odstępów lub formatowania opisu nie tworzy sztucznej kary; identyczny tekst z inną kolejnością nie zmienia rozliczenia.
3. Dowody: brak atrybutu, sprzeczne kolory, kilka cen w opisie, nieistniejący cytat, błędna normalizacja, instrukcje umieszczone w opisie dostawcy. Materiał źródłowy nie może zmienić kontraktu, wyceny ani uprawnień.
4. Poprawka: rzeczywiste naprawienie pola, nieudana naprawa, limit dwóch przetworzeń, ponowne pobranie wyniku bez ponownego generowania.
5. Rozliczenie: 20/20, 18/20, 0/20, różne zapisane ceny jednostkowe, awaria AI, awaria wspólnego eksportu, brak podwójnego zwrotu przy równoległych żądaniach.
6. Trwałość: restart w trakcie zadania i po jego zakończeniu; crash po odpowiedzi dostawcy, ale przed zapisem; wznowienie bez zmiany zaakceptowanego kontraktu.
7. Pliki: poprawne nagłówki i zależności wybranego importera, bezpieczna obsługa treści zaczynającej się od znaków formuł arkusza bez zmiany wartości SKU/ceny, dostęp do plików wyłącznie dla posiadacza danego zamówienia.
8. PayPal: anulowany checkout, niepotwierdzony capture, rozbieżna kwota/waluta, utracona odpowiedź, zwrot częściowy i pełny, `PENDING`, sprawdzenie końcowego statusu i ponowione żądanie. W MVP wystarczy autoryzowane odpytywanie statusu i odzyskiwanie po restarcie; webhooki są osobnym rozszerzeniem, jeśli zostaje czas.

## 8. Wdrożenie i pokaz konkursowy

Przed wdrożeniem wykonać kopię danych, sprawdzić migrację i przygotować zgodny powrót do poprzedniego wdrożenia z zachowaniem danych. Nowe tabele nie zmieniają warunków zamówień legacy. Pierwsze wdrożenie poprawionego katalogu działa na płatnościach demonstracyjnych; prawdziwe AI jest dostępne w kontrolowanym trybie z limitem partii i kosztu. Dopiero po G1 przechodzimy do Sandbox.

Scenariusz filmu: problem ręcznego przygotowania danych → podgląd źródła i warunków → zakup Sandbox → prawdziwe przetwarzanie AI → poprawka błędnej pozycji → dowód pozostającej niezgodności → CSV i odpowiadający jej zwrot Sandbox. Jeśli potrzebne jest deterministyczne zasymulowanie awarii, pokazujemy jawny scenariusz testowy; nie przedstawiamy fixture jako rzeczywistego wyniku modelu. Bezpieczne wejście z autentyczną niejednoznacznością jest lepszym przykładem niż ukryta manipulacja wynikiem.

Zgłoszenie: publiczne repo z licencją, instrukcje uruchomienia, działająca demonstracja i film krótszy niż 3 minuty. Termin organizatora: 12 listopada 2026, 12:00 PST, czyli 21:00 w Polsce. Zalecany bufor na gotowe zgłoszenie: 11 listopada; to termin planistyczny, a nie utworzone przypomnienie.

## 9. Kolejność rozpoczęcia

Pierwszy pakiet pracy to T0–T1: ustalenie profilu wejścia/wyjścia, ręczne opisanie przypadków oraz lokalny prototyp ekstrakcji z raportem. Jego wynikiem ma być decyzja: kontynuujemy, zawężamy asortyment albo zatrzymujemy ten scenariusz. Dotychczasowy koszt hostowania i kodu nie jest argumentem za dalszą inwestycją.

## Źródła sprawdzone 2 listopada 2026

- PayPal AI Hackathon — wymagania, kryteria i termin: https://paypalaihackathon.devpost.com/
- PayPal — pełne i częściowe zwroty przechwyconej płatności: https://developer.paypal.com/checkout/refund-payment
- Shopify — aktualny format CSV i zależności pól: https://help.shopify.com/en/manual/products/import-export/using-csv
- Shopify — proces importu: https://help.shopify.com/en/manual/products/import-export/import-products

Plan produktu, ceny testowe, szacunki czasu i progi G1 są naszymi założeniami do weryfikacji. Dokumentacja dostawców potwierdza możliwości integracji, ale nie popyt ani wyniki naszego rozwiązania.
