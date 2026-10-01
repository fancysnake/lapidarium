# Strona twórcy TTRPG — model treści i architektura

Specyfikacja projektu open source (silnik) i jego pierwszej instancji (strona autora). Dokument dla człowieka i dla Claude Code.

**Stos:** Django + PostgreSQL, szablony Django, czysty CSS, minimalny JS. **Zero Node.** Hosting: Docker na Coolify.

---

## 1. Zasady

### 1.1 POSSE — Publish on your Own Site, Syndicate Elsewhere
Strona jest **źródłem prawdy**. Social media, YouTube, itch i SoundCloud to kanały dystrybucji, które mogą zniknąć, zmienić zasady albo uciąć zasięgi. Wynikają z tego cztery reguły:
- Każda rzecz ma kanoniczny adres na stronie. Na zewnątrz linkuje się do niego, a nie odwrotnie.
- Każda encja ma listę `syndication` z kopiami lub zapowiedziami na zewnątrz (post na FB, film na YT, strona na itch).
- Strona wystawia własne feedy (RSS „co nowego”, iCal kalendarza), więc da się ją śledzić bez żadnej platformy.
- Newsletter jest kanałem, który kontrolujesz. Social media są dodatkiem.

### 1.2 Trwałość mimo bazy danych
Treść żyje w Postgresie (wygoda edycji), ale **co noc jest eksportowana do czytelnych plików** (markdown z frontmatterem i media) w repozytorium git. To jednocześnie backup, historia zmian i droga ucieczki: jeśli aplikacja kiedyś umrze, treść zostaje.

### 1.3 Dwie warstwy: model danych ≠ nawigacja
- **Model danych** opisuje, *czym są* treści: rzeczy, kontenery, relacje.
- **Nawigacja** odpowiada na intencje odwiedzających („chcę posłuchać”, „chcę zagrać”). Menu i drzwi na głównej to konfigurowalne *widoki* (filtry) na model, a nie osobne byty.

### 1.4 Każda podstrona to potencjalne pierwsze wejście
Ruch z postów i filmów trafia na podstrony, a nie na główną. Każda strona szczegółów ma więc ramkę autora, linki do kontenera nadrzędnego, powiązane rzeczy i zachętę do newslettera.

### 1.5 Automatyzacja zamiast skrupulatności
Wszystko, co da się wyliczyć, jest wyliczane: daty modyfikacji, linki zwrotne, „co nowego”, przenoszenie wydarzeń do archiwum. Wszystko, co wpisuje się ręcznie, jest walidowane **w momencie zapisu w adminie**. Szczegóły w sekcji 6.

### 1.6 Najpierw HTML i serwer, JS tylko jako ulepszenie
Każda strona działa bez JavaScriptu. Filtry to parametry GET, interakcje to natywne elementy HTML (`<details>`, `<dialog>`, Popover API). JS i ewentualnie HTMX dochodzą punktowo, gdy konkretna strona tego wymaga.

---

## 2. Model treści

### 2.1 Warstwy

| Warstwa | Typy | Strona szczegółów |
|---|---|---|
| Rzeczy | `Song`, `Game`, `Session`, `Event`, `Article`, `Graphic` | tak (poza grafikami: opcjonalnie) |
| Kontenery | `Project`, `Initiative` | tak |
| Profil | `Profile` (singleton), `Link` | strona „O mnie” |
| Zewnętrzne | `ExternalItem` | nie, linkuje na zewnątrz |

**Projekt** jest ograniczony wynikiem: grupuje rzeczy, ma status `ongoing | finished | abandoned`. Przykłady: album, kampania, seria memów, gra z dodatkami.
**Inicjatywa** jest ograniczona czasem: ma `start_date` i opcjonalny `end_date` (brak oznacza „do teraz”), opisuje rolę lub działalność. Przykłady: organizator konwentu 2019–, pisanie erpegowych piosenek 2021–.

Hierarchia (wszystkie poziomy opcjonalne): `rzecz → projekt → inicjatywa`. Rzecz może należeć do wielu projektów, a projekt do wielu inicjatyw.

### 2.2 Model bazowy `Entry` (polimorficzny)
Wszystkie rzeczy i kontenery dziedziczą po jednym modelu `Entry` (rekomendacja: `django-polymorphic`, dziedziczenie wielotabelowe). Dzięki temu:
- `Entry.objects.all()` zwraca obiekty właściwych podtypów, więc „co nowego”, wyszukiwarka i eksport to jedno zapytanie;
- relacje „wszystko z wszystkim” to zwykłe FK/M2M do `Entry`;
- admin ma wspólny autocomplete do wybierania dowolnej encji.

Odrzucona alternatywa: `GenericForeignKey`. Gorzej działa w adminie, w zapytaniach i przy integralności referencji.

### 2.3 Pola wspólne (`Entry`)

| Pole | Typ Django | Uwagi |
|---|---|---|
| `slug` | `SlugField` | unikalny w obrębie typu; generowany z tytułu, edytowalny |
| `title` | `CharField` | wymagane |
| `summary` | `CharField(max 200)` | 1 zdanie; wymagane; karty, og:description |
| `body` | `TextField` (markdown) | opis / AAR / tekst artykułu |
| `date` | `DateField` | data powstania / publikacji / wydarzenia |
| `created_at` | `DateTimeField(auto_now_add)` | wyliczane |
| `updated_at` | `DateTimeField(auto_now)` | wyliczane |
| `tags` | M2M → `Tag` | własny prosty model, bez dodatkowych bibliotek |
| `featured` | `BooleanField` | kandydat do drzwi na głównej |
| `cover` | FK → `Graphic` (null) | również og:image |
| `related` | M2M → `Entry` | luźne powiązania (symetryczne) |
| `part_of` | M2M → `Entry` (tylko `Project` / `Initiative`) | przynależność do kontenera |
| `syndication` | inline `SyndicationLink(url, platform)` | kopie na zewnątrz (POSSE) |
| `status` | `draft | published` | tylko `published` jest widoczne publicznie |
| `license` | `CharField` (choices z konfiguracji) | opcjonalnie |

Linki zwrotne („użyto w…”, „należy do…”, „rzeczy w tym projekcie”) to zapytania odwrotne (`related_name`). Pokazuje się je na stronie i jako tylko-do-odczytu w adminie, nigdy nie wpisuje ręcznie.

### 2.4 Pola specyficzne

**`Session`** — sesja RPG
- `hook` *(wymagane)*: jednozdaniowa premisa („ucieczka przed kosmicznym łosiem”). To główny element prezentacji.
- `system`: string
- `format`: `one-shot | campaign-session | convention | online | other`
- `recording`: URL (walidowany jako YouTube)
- `body` = AAR (opcjonalny)
- `players`: string[] (ksywki, opcjonalnie, za zgodą graczy)
- Kampania to `Project`, do którego sesja należy przez `part_of`. Jest opcjonalna i drugorzędna w prezentacji.

**`Song`**
- `audio_links`: inline (SoundCloud, YT, Bandcamp…)
- `audio_file`: plik (opcjonalnie, własny hosting)
- `body` = tekst piosenki (opcjonalnie)
- `inspired_by`: FK → `Entry` (sesja, gra, kampania), opcjonalnie

**`Game`**
- `itch_url`: URL (walidowany jako itch.io)
- `release_status`: `released | beta | in-progress`
- `genre`, `players` (np. „2–5”), `session_length`, `version`

**`Event`**
- `start_date` *(wymagane)*, `end_date`
- `location`: string; `online`: bool
- `role` *(wymagane)*: `organizer | speaker | gm | attendee`
- `url`: strona wydarzenia
- **Przyszłe** wydarzenia trafiają do kalendarza i na główną (najbliższe 1–2). **Przeszłe** automatycznie przechodzą do archiwum (filtr po dacie w widoku, bez ręcznej zmiany statusu).

**`Article`** — baza wiedzy (wiki, nie blog)
- `section` *(wymagane)*: FK → `WikiSection` (nazwa, slug, kolejność)
- `order`: liczba, kolejność w dziale
- `cover` zwykle wskazuje mem z tezą artykułu (mem = zajawka, artykuł = rozwinięcie)

**`Graphic`**
- `kind` *(wymagane)*: `meme | map | illustration | other` (lista rozszerzalna w konfiguracji)
- `image` *(wymagane)*: `ImageField`
- `alt` *(wymagane)*: tekst alternatywny; dla memów to transkrypcja tekstu z obrazka
- Grafika jest niezależna, a inne encje wskazują ją przez `cover`. Ta sama mapa może być okładką kilku rzeczy.
- Seria grafik na jeden temat to `Project`.

**`Project`**
- `project_status` *(wymagane)*: `ongoing | finished | abandoned`
- `start_date`, `end_date`

**`Initiative`**
- `start_date` *(wymagane)*, `end_date` (brak = trwa)
- `role`: string („organizator”, „autor”)

**`Profile`** (singleton)
- `name`, `handle`, `tagline` (jedno zdanie: kim jestem i co robię), `photo`, `bio`, `email`

**`Link`**
- `platform`, `url`, `label`, `order`

**`ExternalItem`** — pozycje z zewnętrznych feedów
- `source` (youtube, itch, …), `external_id`, `title`, `url`, `published_at`, `thumbnail_url`
- `entry`: FK → `Entry` (null). Ustawiane automatycznie, gdy URL pokrywa się z `SyndicationLink` encji; wtedy „co nowego” linkuje do strony, nie na zewnątrz.

---

## 3. Nawigacja i strony

### 3.1 Drzwi (konfigurowalne)
Każde drzwi to: etykieta, filtr na model, sposób wyboru perełki, warunek widoczności. Definiowane w ustawieniach instancji (`SITE_DOORS`).

| Drzwi | Filtr | Perełka |
|---|---|---|
| Piosenki | `Song` | najnowsza `featured` |
| Gry | `Game` | najnowsza `featured` |
| Sesje RPG | `Session` | ostatnio prowadzona (hook + okładka) |
| Wydarzenia | `Event` | najbliższe przyszłe, inaczej ostatnie |
| Artykuły | `Article` | `featured`; **drzwi ukryte, gdy artykułów < N** |
| Memy | `Graphic`, `kind=meme` | losowa lub `featured`; etykietę można zmienić na „Grafiki” bez zmian w danych |

### 3.2 Strona główna — odpowiada na 3 pytania
1. **Co to za gość / co to za strona:** zdjęcie, handle, `tagline`.
2. **Co fajnego tu znajdę:** drzwi z perełkami (konkretna rzecz, nie nazwa kategorii).
3. **Czy to żyje:** 3–5 pozycji „co nowego” i najbliższe wydarzenie.
4. Stopka: newsletter, e-mail, linki.

### 3.3 Strona sesji
1. Hook jako nagłówek, pod nim system, data, format i kampania (jeśli jest).
2. Okładka lub nagranie (embed YT ładowany dopiero po kliknięciu, żeby nie wciągać skryptów Google przy wejściu).
3. AAR.
4. Powiązane: memy, piosenka zainspirowana sesją, inne sesje z kampanii.
5. Ramka autora i newsletter (to może być pierwsze wejście).

### 3.4 Trasy

| Trasa | Zawartość |
|---|---|
| `/` | główna |
| `/o-mnie/` | profil, oś czasu inicjatyw i projektów, kontakt |
| `/piosenki/`, `/gry/`, `/sesje/`, `/grafiki/` | listy z filtrami (GET: `?tag=`, `?rok=`, `?rodzaj=`) |
| `/<typ>/<slug>/` | strona szczegółów |
| `/wydarzenia/` | kalendarz (przyszłe) i archiwum (przeszłe) |
| `/wiki/`, `/wiki/<sekcja>/<slug>/` | baza wiedzy z nawigacją po działach |
| `/projekty/<slug>/`, `/inicjatywy/<slug>/` | kontenery z listą rzeczy |
| `/nowe/` | pełna lista „co nowego” |
| `/szukaj/?q=` | wyszukiwarka (Postgres full-text) |
| `/rss.xml` | feed „co nowego” (framework syndication Django) |
| `/kalendarz.ics` | feed iCal przyszłych wydarzeń |

Nazwy tras są tłumaczalne (i18n), polskie podane jako przykład instancji.

### 3.5 „Co nowego”
Generowane automatycznie:
- wewnętrzne: `Entry` posortowane po `greatest(date, updated_at)`, z rozróżnieniem „dodano” / „zaktualizowano”. Drobne poprawki można oznaczyć checkboxem „nie pokazuj w co nowego”.
- zewnętrzne: `ExternalItem` pobierane komendą `fetch_feeds` uruchamianą cyklicznie (zadanie zaplanowane w Coolify). YouTube ma RSS per kanał; itch i inne źródła do sprawdzenia.

### 3.6 Newsletter i kontakt
- Formularz newslettera wysyła do dostawcy przez **adapter** (interfejs w Pythonie: `subscribe(email)`). Implementacje na start: Listmonk (self-hosted na Coolify) i jeden dostawca zewnętrzny. Instancja wybiera adapter w ustawieniach.
- Kontakt: formularz z prostą ochroną przed spamem (honeypot i limit), wysyłka przez SMTP; alternatywnie `mailto:`.
- Brak komentarzy (świadoma decyzja).

---

## 4. Frontend i motywy

### 4.1 Zasada zero Node
- Brak `package.json`, `node_modules` i bundlera. CI failuje, jeśli `package.json` pojawi się w repo.
- CSS: czysty, z natywnym zagnieżdżaniem, zmiennymi, container queries.
- JS: małe, niezależne moduły ES jako progressive enhancement. HTMX (jeśli potrzebny) jako pojedynczy plik w `static/vendor/`.
- Statyki: Whitenoise z `CompressedManifestStaticFilesStorage` (hashowanie i kompresja bez bundlera).

### 4.2 Motywy — trzy poziomy nadpisywania
Silnik generuje **semantyczny, stabilny HTML**. Motyw instancji zmienia wygląd, nie strukturę (chyba że świadomie nadpisze szablon).

| Poziom | Co zmienia | Jak |
|---|---|---|
| 1. Tokeny | kolory, fonty, skala typografii, odstępy, promienie, cienie | plik `tokens.css` nadpisujący zmienne CSS (`--color-bg`, `--font-display`, `--space-3`…) |
| 2. Komponenty | wygląd konkretnych komponentów (karta, drzwi, nagłówek sesji) | `theme.css` celujący w stabilne klasy komponentów |
| 3. Szablony | struktura HTML wybranych fragmentów | nadpisanie szablonu Django w katalogu motywu (kolejność loaderów: motyw → silnik) |

Struktura motywu:
```
themes/<nazwa>/
  theme.toml        # nazwa, autor, wersja, wymagana wersja silnika, fonty
  tokens.css        # poziom 1 (wymagany)
  theme.css         # poziom 2 (opcjonalny)
  templates/        # poziom 3 (opcjonalny)
  static/           # fonty, tekstury, ikony
```

Kontrakt motywu:
- **Lista tokenów jest częścią publicznego API silnika** i jest wersjonowana. Zmiana nazwy tokenu to zmiana łamiąca.
- **Klasy komponentów są stabilne** i udokumentowane (konwencja w stylu BEM: `.door`, `.door__pick`, `.session-hero__hook`).
- Szablony komponentów są małe i rozdzielone (`components/door.html`, `components/author-box.html`), żeby nadpisanie jednego nie wymagało kopiowania całej strony.
- Tryb ciemny: motyw może dostarczyć drugi zestaw tokenów pod `prefers-color-scheme: dark`.
- Silnik dostarcza motyw domyślny i co najmniej jeden alternatywny jako przykład.

**Motyw domyślny jest czarno-biały.** Zasada: jeśli układ działa w czerni i bieli, zadziała z kolorami. Motyw bazowy `base` używa wyłącznie czerni, bieli i szarości, więc hierarchia (typografia, odstępy, ramki) musi działać bez koloru. Kolor to wyłącznie warstwa motywu instancji.

**Kolory semantyczne jako tokeny.** Dwie grupy:
- marka: `--color-brand` (logo, główne CTA, linki ogólne), `--color-brand-contrast` (tekst na kolorze marki);
- rodzaje aktywności: `--color-type-session`, `--color-type-song`, `--color-type-game`, `--color-type-graphic`, `--color-type-event`, `--color-type-article`, `--color-type-project`, `--color-type-initiative`, każdy z wariantem `-tint` (jasne tło).

Szablony nie używają tych tokenów bezpośrednio, tylko przez `--type-color` i `--type-tint` ustawiane na elemencie z `data-type="session"` itd. Dzięki temu karta, etykieta, link „wszystkie…”, wpis w „co nowego” i znacznik w menu kolorują się automatycznie według typu treści, a strona szczegółów przyjmuje kolor swojego typu. W motywie `base` wszystkie `--color-type-*` są czarne, a `-tint` jasnoszare.

Reguły dostępności (sprawdzane przez system check motywu): każdy `--color-type-*` i `--color-brand` ma kontrast co najmniej 4.5:1 z `--color-bg`, a każdy `--color-type-*` także ze swoim `-tint` (tekst w kolorze typu na jego tle, np. etykieta `.read-aloud__label`); typ zawsze ma też etykietę tekstową, więc kolor nie jest jedynym nośnikiem informacji.

Motyw instancji autora: układ „Ekran MG” (Spectral / Spectral SC / Barlow Condensed), białe tło, marka `#008000`, kolory typów: sesje `#6B3FA0`, piosenki `#C2410C`, gry `#1D5FA8`, grafiki `#A16207`, wydarzenia `#BE185D`.

Wybór motywu: `SITE_THEME = "nazwa"` w ustawieniach. Podgląd motywu w adminie (strona z wszystkimi komponentami na przykładowych danych) służy też jako dokumentacja komponentów.

### 4.3 Walidacja motywu
Django system check (`checks.register`) przy starcie:
- `tokens.css` definiuje wszystkie wymagane tokeny (błąd, jeśli brakuje);
- `theme.toml` deklaruje zgodną wersję silnika (ostrzeżenie, jeśli niezgodna);
- nadpisane szablony istnieją w silniku (ostrzeżenie o szablonie, którego silnik już nie używa);
- kontrast `--color-brand` i każdego `--color-type-*` względem `--color-bg` oraz każdego `--color-type-*` względem jego `-tint` wynosi co najmniej 4.5:1 (błąd, jeśli nie).

---

## 5. Architektura open source

### 5.1 Podział silnik / instancja
- **Silnik** (repo open source, pakiet pip): aplikacje Django (modele, admin, widoki, szablony, motyw domyślny), walidacja, komendy zarządzania, adaptery newslettera, obraz Dockera.
- **Instancja** (repo autora): ustawienia, motyw, `docker-compose.yml`, repo z eksportem treści. **Sama treść żyje w bazie**, nie w repo kodu.

W repo silnika jest projekt `example/` z danymi demonstracyjnymi (fixture) do developmentu, testów i jako żywa dokumentacja.

### 5.2 Konfiguracja instancji (ustawienia Django)
- tożsamość (nazwa, domena, język)
- włączone typy treści (ktoś bez piosenek po prostu je wyłącza; wyłączony typ znika z adminu, menu i tras)
- drzwi na głównej (`SITE_DOORS`)
- rozszerzenia enumów (`Graphic.kind`, `Session.format`)
- źródła zewnętrznych feedów
- adapter newslettera
- motyw (`SITE_THEME`)
- progi walidacji (np. minimalna liczba artykułów do pokazania drzwi)

### 5.3 Deployment
- Jeden obraz: gunicorn + Whitenoise; usługa Postgres; wolumen na media (albo S3-kompatybilny storage).
- `docker-compose.yml` gotowy pod Coolify; zadania cykliczne: `fetch_feeds`, `export_content`, `check_content`.
- Panel admina pod niestandardowym adresem; opcjonalnie 2FA.
- Cache: cache widoków czyszczony sygnałem przy zapisie `Entry` (strona jest w praktyce tylko do odczytu, więc to wystarcza).

### 5.4 Internacjonalizacja
Teksty interfejsu i nazwy tras przez standardowe i18n Django (pl na start, en jako drugi język). Treść instancji jednojęzyczna; wielojęzyczność treści poza zakresem v1.

### 5.5 Licencje (do decyzji)
Kod silnika na licencji permisywnej (np. MIT). Treść instancji osobno, przez pole `license` per encja.

---

## 6. Walidacja — „ważne rzeczy sprawdzają się same”

### 6.1 Trzy poziomy

**Poziom 1: model i formularz (przy zapisie w adminie).** Błąd blokuje zapis i pokazuje komunikat przy polu.
- wymagane pola, typy, choices, formaty URL (walidatory per pole: YouTube, itch.io)
- `CheckConstraint`: `end_date ≥ start_date`
- `UniqueConstraint`: slug w obrębie typu
- uwaga: walidacja M2M (`part_of`, `related`) nie działa w `Model.clean()`, dlatego trafia do `clean()` formularza admina

**Poziom 2: integralność grafu.** Błędy blokują zapis albo publikację, ostrzeżenia trafiają do raportu.

| Reguła | Gdzie | Poziom |
|---|---|---|
| `part_of` wskazuje tylko `Project` / `Initiative` | formularz | błąd |
| brak cykli w `part_of` | formularz | błąd |
| opublikowana encja nie wskazuje draftu (cover, related, part_of) | formularz przy publikacji | błąd |
| grafika ma plik i `alt` | model | błąd |
| sesja ma `hook` | model | błąd |
| projekt ma co najmniej 1 rzecz | raport | ostrzeżenie |
| każde widoczne drzwi mają co najmniej 1 perełkę | raport | ostrzeżenie |
| wydarzenie z `role=gm` minęło, a brak powiązanej sesji | raport | ostrzeżenie („dopisać sesję/AAR?”) |
| linki `syndication` / `recording` odpowiadają | raport (cyklicznie) | ostrzeżenie |
| encja bez `cover` na liście z okładkami | raport | ostrzeżenie (użyty fallback) |
| inicjatywa bez nowych rzeczy od > X miesięcy | raport | informacja („zakończyć?”) |

**Poziom 3: wyliczanie zamiast wpisywania.**
- `created_at`, `updated_at`, slug z tytułu
- linki zwrotne, przynależność, „co nowego”, archiwum wydarzeń
- powiązanie `ExternalItem` z encją po URL
- og:image z `cover`, fallback generowany z tytułu

### 6.2 Gdzie walidacja działa
1. **przy zapisie w adminie** (poziom 1 i błędy poziomu 2)
2. **„Zdrowie treści”**: strona w adminie z listą ostrzeżeń i linkami do poprawy
3. **komenda `check_content`**: ten sam raport w terminalu i w CI (`--json`), uruchamiana też cyklicznie; ostrzeżenia mogą trafiać mailem
4. **CI na każdym pushu silnika**: testy, migracje, `check_content` na danych demo, zakaz `package.json`, system checks motywów

### 6.3 Mniej okazji do błędów w adminie
- autocomplete dla wszystkich relacji
- inline’y: linki syndykacji, linki audio, podgląd linków zwrotnych
- akcje masowe (np. „oznacz jako featured”, „przypisz do projektu”)
- szybkie dodawanie grafiki z telefonu: admin działa na mobile, a formularz grafiki ma minimum pól (plik, alt, rodzaj, opcjonalnie powiązanie)

---

## 7. Eksport i import treści
- `export_content`: każda opublikowana encja zostaje zapisana jako markdown z frontmatterem (YAML) w `content/<typ>/<slug>.md`, media są kopiowane obok. Jeśli zawartość się zmieniła, komenda robi commit do repo eksportu. Uruchamiana co noc.
- `import_content`: odwrotność, do odtworzenia instancji, migracji albo startu nowej instancji z plików.
- Format eksportu jest udokumentowany i wersjonowany, bo to część obietnicy trwałości.

---

## 8. Pytania otwarte
1. **Nazwa projektu open source.**
2. **Adapter newslettera na start:** Listmonk (self-hosted, pełna kontrola) czy usługa zewnętrzna (mniej utrzymania).
3. **itch i inne źródła:** jakie feedy są faktycznie dostępne; ewentualnie ręczne wpisy przez `syndication`.
4. **Zgoda graczy:** czy ksywki w sesjach i AAR wymagają pola zgody.
5. **Media:** wolumen na Coolify czy storage S3-kompatybilny (wpływa na backup i eksport).
6. **Kolory typów dla artykułów, projektów i inicjatyw:** dobrać, gdy te działy pojawią się na stronie.
