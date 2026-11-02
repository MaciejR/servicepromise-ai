# T2 — trwałe zadania katalogowe

Kontynuacja techniczna zgodnie z poleceniem użytkownika z 2 listopada 2026. Otwarte kryteria biznesowe z pilotażu nadal nie są spełnione.

Dodano API `/api/catalog/jobs`: utworzenie zadania z CSV i walutą, odczyt przez token zamówienia, demonstracyjny checkout oraz pobranie wyniku `products.csv`. Nowa ścieżka korzysta z reguł, nie wykonuje transakcji PayPal i nie jest jeszcze wdrożona w Azure. Dotychczasowy frontend nie obsługuje tych ekranów.

Wersjonowana, addytywna migracja tworzy osobne tabele katalogu; nie zmienia tabel ani polityki historycznych zamówień. Zapisywany jest snapshot wejścia, słownika, kontraktu i wyceny. Checkout jednorazowo kolejkuje pracę i ustala budżet 10 minut. Worker zapisuje każdą próbę przed jej wykonaniem oraz wynik pozycji. Po restarcie wznawia niedokończone zadanie, pomijając odebrane pozycje. Przerwana próba zużywa limit; po dwóch próbach pozycja jest niedostarczona. Brak zgodnego kontraktu blokuje dalsze przetwarzanie. Wynik końcowy i pojedyncze symulowane rozliczenie są zapisywane atomowo.

Obsługiwana konfiguracja: SQLite, jedna instancja aplikacji, jeden proces Uvicorn i jeden worker. Nie uruchamiać kilku instancji na tej samej bazie — odzyskiwanie po starcie zakłada wyłączność procesu. Nie trzymamy transakcji bazy podczas wywołania ekstraktora. PostgreSQL pozostaje obsługiwany przez dawną aplikację, ale nowe endpointy katalogu zwracają dla niego 503.

Walidacja: **50 testów przeszło**. Pięć nowych testów obejmuje powtarzalną migrację, niezmienną wycenę i checkout, ochronę tokenem, wznowienie po symulowanym przerwaniu, równoległe przetwarzanie i pełny przepływ API z pobraniem CSV.

Kolejne elementy planu: ekran katalogu T3, niezależna walidacja danych i użyteczności T4, później Sandbox T5. Nowa ścieżka nie ma jeszcze trwałych operacji finansowych ani produkcyjnej autoryzacji użytkowników. Nie zastępuje kompletnego T5 ani walidacji migracji na kopii danych wdrożenia.
