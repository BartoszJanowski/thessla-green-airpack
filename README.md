<img src="assets/icon.svg" width="96" align="right" alt="">

# Thessla Green AirPack4 for Home Assistant

**[English](#english) · [Polski](#polski)**

An unofficial Home Assistant integration for **Thessla Green AirPack4** heat-recovery ventilation units. It talks Modbus through a TCP → RTU gateway (Elfin EW11/EW10, Waveshare, USR, …).

---

<a id="english"></a>

## English

### Features

- **Control:** airflow, operating mode (Automatic / Manual / Temporary), season, special functions (fireplace, airing, open windows, empty house, hood), ECO / COMFORT, power, bypass and GWC.
- **Settings:** the user and installer settings from the Air++ menu: special-function intensities and durations, bypass and GWC parameters, AirS gears, per-mode airflow and supply temperature.
- **Two-way sync:** changes made on the Air++ panel, AirS or AirMobile appear in Home Assistant on the next poll.
- **Never breaks on other models:** the integration probes which registers your unit has.
  - Missing registers are skipped.
  - Sensors that aren't fitted are hidden.
  - A value the unit can't read right now shows *Unknown* instead of an error.
- **Live flow diagram:** shown in an **AirPack4** sidebar panel and as a dashboard card, similar to the Air++ unit screen. It shows temperatures, airflow, fans, filters, FPX, GWC, the duct heater and the bypass.
- **Diagnostics:** alarms with descriptions, filter wear and replacement dates, a read-only mode, and diagnostics download.
- **Languages:** English and Polish.

### Supported devices

All AirPack4 variants covered by the manufacturer's `MODBUS_USER_AirPack_4` register map:

| | Enthalpy | Energy+ | Energy++ |
|---|---|---|---|
| **h** (horizontal) | 300 / 400 / 500 | 300 / 400 / 500 | 300 / 400 / 500 |
| **v** (vertical) | 300 / 400 / 500 | 300 / 400 / 500 / 550 | 300 / 400 / 500 / 550 |

- Tested on an **AirPack4 400v Energy++**, firmware **4.87.2**.
- Optional hardware is detected automatically: GWC, duct heater/cooler, constant flow (CF), ERV post-heater, and the Expansion module.

**Requirements:**
- Home Assistant **2025.10** or newer. The integration icon needs **2026.3** or newer.
- A Modbus TCP → RTU gateway on the same network as Home Assistant.

### 1. Connect the gateway

1. Wire the gateway's RS-485 **A/B** to the AirPack's **Air-B** port. The Air++ panel keeps its own port, so the two don't interfere.
2. Configure the gateway's serial side as **9600 baud, 8 data bits, no parity, 1 stop bit (8N1)**.
3. Set the gateway protocol to **Modbus TCP ↔ RTU conversion**.
   - **Elfin EW11 / EW10:** open the web page (default user/password `admin`/`admin`) → *Communication Settings* → *Protocol*: **Modbus**. Note the **Local Port**. The Elfin default is **8899**; many other gateways use **502**.
   - **Waveshare:** use the *Modbus TCP to RTU* mode.
   - Transparent / raw TCP mode is **not** supported.
4. Give the gateway a fixed IP address, for example with a DHCP reservation in your router.
5. The AirPack's Modbus device address is **10** by default (allowed range 10–19).

### 2. Install

**Home Assistant 2026.11 and newer: Marketplace.** HACS is now built into Home Assistant as the *Marketplace*.
1. *Settings → Marketplace* → **⋮** (top right) → **Custom repositories**.
2. Repository: `https://github.com/BartoszJanowski/thessla-green-airpack`, type **Integration** → **Add**.
3. Search for **Thessla Green AirPack4** → **Download**.
4. Restart Home Assistant: *Settings → System → ⋮ → Restart*.

**Home Assistant 2026.10 and older: HACS.** The same steps, starting from **HACS → ⋮ → Custom repositories**.

If you upgrade Home Assistant to 2026.11, an installation made through HACS is taken over by the Marketplace automatically.

**Manual:** copy `custom_components/thessla_green_airpack` to `<config>/custom_components/`, then restart Home Assistant.

### 3. Add the device

*Settings → Devices & services → + Add integration → Thessla Green AirPack4*:

| Field | Value |
|---|---|
| Name | Anything, e.g. `Recuperator` |
| Gateway host / IP | The gateway's IP address, e.g. `192.168.1.50` |
| TCP port | The gateway's Modbus port: `8899` (Elfin default) or `502` |
| Modbus device address | `10`, unless changed on the unit |
| Model | Your AirPack4 variant. It only sets the device name; hardware is detected automatically |

The first setup takes a few seconds while the integration checks which registers your unit has.

To change the IP, port or address later: *Devices & services → Thessla Green AirPack4 → ⋮ → Reconfigure*.

### 4. Options

*Devices & services → Thessla Green AirPack4 → ⚙ / Configure*:

| Option | Default | What it does |
|---|---|---|
| **Polling interval** | 30 s | How often the unit is read (5–300 s). One read takes about 2 s over Wi-Fi. 10–15 s makes panel changes show up faster. Below 10 s gains little but loads the gateway and the HA database more. Reading never wears the unit. |
| **Request timeout** | 3 s | How long to wait for an answer. Increase it for an unreliable Wi-Fi gateway. |
| **Delay between requests** | 0 ms | Pause between Modbus requests. Set 50–100 ms if you see intermittent *Unavailable* states. |
| **Special functions available on the panel** | all | Functions offered in the *Special function* selector. Untick the ones your installer has not configured (often *Hood*), because this can't be detected over Modbus. |
| **Read-only mode** | off | Blocks **every** write to the unit: Home Assistant only reads, and attempts to change something show an error. Recommended for the first day. Turn it off when you want to control the unit from Home Assistant. |

The integration reloads automatically after you save the options.

### 5. Controls and operating modes

The **Ventilation** fan entity is the main control:

| Preset | Meaning |
|---|---|
| **Automatic** | The unit follows its weekly schedule. Schedules are edited on the Air++ panel. |
| **Manual** | Constant airflow. Uses the *Manual airflow* setting. |
| **Temporary** | A temporary override. |

Changing the **airflow %**:
- in **Automatic** starts a **Temporary** override, exactly like turning the knob on the Air++ panel,
- in **Manual** changes the manual airflow.

0 % is rejected. Use the **Power** switch to turn the unit off.

Other controls:
- **Power:** turns the unit on and off, like the panel's power button.
- **Season:** summer / winter. This selects the summer or winter schedule.
- **Special function:** none / fireplace / airing / open windows / empty house / hood. The *Active function* sensor also shows functions started by wall switches or sensors.
- **ECO / COMFORT:** COMFORT keeps the supply temperature using the duct heater/cooler or the ERV post-heater, if fitted.

Under **Configuration** (device page):
- per-mode airflow and supply temperature. The *Temporary* ones are hidden by default because the Ventilation entity handles them.
- bypass and GWC on/off and their parameters,
- special-function intensities and durations,
- AirS gears,
- filter replacement buttons: press after replacing a filter (units without AFC).

Under **Diagnostics:** firmware, inputs and outputs, control voltages, and **Re-detect hardware**. Press that after fitting new hardware, such as a GWC.

Entity order on the device page is alphabetical. That is how Home Assistant works, and an integration can't change it.

### 6. Flow diagram

- **Sidebar panel:** **AirPack4** in the sidebar shows the live diagram full-page. It's also opened by the **Visit** button on the device page.
  - To hide it from the sidebar, long-press the sidebar title and hide *AirPack4*.
- **Dashboard card:** edit a dashboard → **+ Add card** → search **Thessla**. Or add a *Manual* card:

  ```yaml
  type: custom:thessla-airpack-card
  # device_id: optional – defaults to the first AirPack
  # title: optional
  ```

What the diagram shows:
- Each air path with temperature, fan intensity, airflow and filter wear.
- When the **bypass** opens, the exchanger fades and shows *BYPASS*, and supply air is drawn along the bypass path.
- FPX, GWC and the duct heater appear only if your unit has them.
- Tapping an element opens its entity.

### 7. Updating

New versions are published as [GitHub releases](https://github.com/BartoszJanowski/thessla-green-airpack/releases). Home Assistant shows them as an update, with the release notes.
- *Settings → Updates*, or *Marketplace / HACS → Thessla Green AirPack4*, → **Update**.
- To check for a new version right away: **⋮ → Update information**.
- Restart Home Assistant, then hard-refresh the browser (Ctrl+F5 / Cmd+Shift+R).

### 8. Troubleshooting

- **"Cannot connect to the gateway":** check the IP address and port, and that the gateway is reachable from Home Assistant.
- **"The gateway is reachable but the AirPack does not answer":**
  - Check the device address (10).
  - Check A/B wiring (try swapping A and B).
  - Check the gateway serial settings (9600 8N1).
  - Make sure the gateway is in Modbus TCP→RTU mode.
- **Entities briefly become *Unavailable*:** increase *Delay between requests* and *Request timeout*. Don't connect two Modbus clients to the same gateway at once (for example an old integration and this one).
- **Entity names are in English although the interface is in Polish:** entity names follow the *system* language (*Settings → System → General → Language*), not your profile language. Set it to Polski and restart.
- **The card can't be found:** hard-refresh the browser. In the mobile app, pull down to reload.
- **Which registers does my unit have?**
  - Device page → **⋮ → Download diagnostics**.
  - Or run the read-only probe. It can only send Modbus *read* requests:

    ```bash
    pip install pymodbus
    python -I tools/probe.py --host 192.168.1.50 --port 8899 --unit 10 --json probe-out.json
    ```

### 9. Reporting problems

Please open an [issue](https://github.com/BartoszJanowski/thessla-green-airpack/issues/new/choose). Include:
- your model and firmware,
- the Home Assistant and integration versions,
- the **diagnostics** file (it does not contain your IP address or serial number).

Pull requests are not accepted; please describe the change in an issue instead.

### Development

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements_test.txt
.venv/bin/python -m pytest
```

- `tools/card_preview.html`: the card with mocked data. Add `?lang=pl` for Polish and `?w=360` for phone width.
- `tools/gen_translations.py`: regenerates `strings.json` and `translations/{en,pl}.json`.
- `assets/icon.svg`: source of the icon in `brand/`. It's an original design, not the manufacturer's logo.

---

<a id="polski"></a>

## Polski

### Możliwości

- **Sterowanie:** intensywność, tryb pracy (automatyczny / manualny / chwilowy), sezon, funkcje specjalne (kominek, wietrzenie, otwarte okna, pusty dom, okap), EKO / KOMFORT, zasilanie, bypass i GWC.
- **Ustawienia:** nastawy użytkownika i instalatora z menu Air++: intensywności i czasy funkcji specjalnych, parametry bypassu i GWC, biegi AirS, intensywność i temperatura nawiewu dla trybów.
- **Synchronizacja w obie strony:** zmiany z panelu Air++, AirS lub AirMobile pojawiają się w Home Assistancie przy następnym odczycie.
- **Nie psuje się na innych modelach:** integracja sprawdza, które rejestry ma Twoja centrala.
  - Brakujące rejestry są pomijane.
  - Niezamontowane czujniki są ukrywane.
  - Chwilowo nieodczytana wartość pokazuje się jako *Nieznany* zamiast błędu.
- **Schemat pracy na żywo:** w panelu **AirPack4** w menu bocznym i jako karta na pulpit, podobny do ekranu Air++. Pokazuje temperatury, przepływy, wentylatory, filtry, FPX, GWC, nagrzewnicę i bypass.
- **Diagnostyka:** alarmy z opisami, zużycie i terminy wymiany filtrów, tryb tylko do odczytu i pobieranie diagnostyki.
- **Języki:** polski i angielski.

### Obsługiwane urządzenia

Wszystkie odmiany AirPack4 z mapy rejestrów producenta `MODBUS_USER_AirPack_4`:

| | Enthalpy | Energy+ | Energy++ |
|---|---|---|---|
| **h** (poziome) | 300 / 400 / 500 | 300 / 400 / 500 | 300 / 400 / 500 |
| **v** (pionowe) | 300 / 400 / 500 | 300 / 400 / 500 / 550 | 300 / 400 / 500 / 550 |

- Przetestowane na **AirPack4 400v Energy++**, oprogramowanie **4.87.2**.
- Wyposażenie dodatkowe wykrywane jest automatycznie: GWC, nagrzewnica/chłodnica kanałowa, Constant Flow (CF), nagrzewnica wtórna ERV i moduł Expansion.

**Wymagania:**
- Home Assistant **2025.10** lub nowszy. Ikona integracji wymaga wersji **2026.3** lub nowszej.
- Bramka Modbus TCP → RTU w tej samej sieci co Home Assistant.

### 1. Podłączenie bramki

1. Podłącz **A/B** z RS-485 bramki do portu **Air-B** centrali. Panel Air++ zostaje na swoim porcie, więc sobie nie przeszkadzają.
2. Ustaw port szeregowy bramki: **9600 bodów, 8 bitów danych, bez parzystości, 1 bit stopu (8N1)**.
3. Ustaw w bramce tryb **konwersji Modbus TCP ↔ RTU**.
   - **Elfin EW11 / EW10:** otwórz stronę bramki (domyślnie login/hasło `admin`/`admin`) → *Communication Settings* → *Protocol*: **Modbus**. Zanotuj **Local Port**. Domyślny port Elfina to **8899**, wiele innych bramek używa **502**.
   - **Waveshare:** wybierz tryb *Modbus TCP to RTU*.
   - Tryb transparentny („raw TCP”) **nie** jest obsługiwany.
4. Nadaj bramce stały adres IP, np. przez rezerwację DHCP w routerze.
5. Adres Modbus centrali to domyślnie **10** (dozwolony zakres 10–19).

### 2. Instalacja

**Home Assistant 2026.11 i nowszy: Marketplace.** HACS jest teraz wbudowany w Home Assistanta jako *Marketplace*.
1. *Ustawienia → Marketplace* → **⋮** (prawy górny róg) → **Niestandardowe repozytoria** (Custom repositories).
2. Repozytorium: `https://github.com/BartoszJanowski/thessla-green-airpack`, typ **Integracja** → **Dodaj**.
3. Wyszukaj **Thessla Green AirPack4** → **Pobierz**.
4. Uruchom ponownie Home Assistanta: *Ustawienia → System → ⋮ → Uruchom ponownie*.

**Home Assistant 2026.10 i starszy: HACS.** Te same kroki, zaczynając od **HACS → ⋮ → Niestandardowe repozytoria**.

Po aktualizacji Home Assistanta do 2026.11 instalację z HACS automatycznie przejmuje Marketplace.

**Ręcznie:** skopiuj `custom_components/thessla_green_airpack` do `<config>/custom_components/`, potem uruchom ponownie Home Assistanta.

### 3. Dodanie centrali

*Ustawienia → Urządzenia oraz usługi → + Dodaj integrację → Thessla Green AirPack4*:

| Pole | Wartość |
|---|---|
| Nazwa | Dowolna, np. `Rekuperator` |
| Adres bramki / IP | Adres IP bramki, np. `192.168.1.50` |
| Port TCP | Port Modbus bramki: `8899` (domyślny w Elfinie) lub `502` |
| Adres urządzenia Modbus | `10`, chyba że zmieniono go w centrali |
| Model | Twoja odmiana AirPack4. Wpływa tylko na nazwę urządzenia, sprzęt jest wykrywany automatycznie |

Pierwsza konfiguracja trwa kilka sekund, bo integracja sprawdza, które rejestry ma Twoja centrala.

Zmiana IP, portu lub adresu później: *Urządzenia oraz usługi → Thessla Green AirPack4 → ⋮ → Skonfiguruj ponownie*.

### 4. Opcje

*Urządzenia oraz usługi → Thessla Green AirPack4 → ⚙ / Konfiguruj*:

| Opcja | Domyślnie | Działanie |
|---|---|---|
| **Interwał odpytywania** | 30 s | Jak często odczytywana jest centrala (5–300 s). Jeden odczyt przez Wi‑Fi trwa ok. 2 s. Przy 10–15 s zmiany z panelu pojawiają się szybciej. Poniżej 10 s zysk jest niewielki, a bramka i baza HA są bardziej obciążone. Odczyt nie zużywa centrali. |
| **Limit czasu zapytania** | 3 s | Jak długo czekać na odpowiedź. Zwiększ przy niestabilnej bramce Wi‑Fi. |
| **Opóźnienie między zapytaniami** | 0 ms | Przerwa między zapytaniami Modbus. Ustaw 50–100 ms, jeśli encje chwilami robią się *Niedostępne*. |
| **Funkcje specjalne dostępne na panelu** | wszystkie | Funkcje w wyborze *Funkcja specjalna*. Odznacz te, których instalator nie skonfigurował (często *Okap*), bo tego nie da się wykryć przez Modbus. |
| **Tryb tylko do odczytu** | wyłączony | Blokuje **każdy** zapis do centrali: Home Assistant tylko czyta, a próba zmiany kończy się komunikatem błędu. Zalecany na pierwszy dzień. Wyłącz, gdy chcesz sterować centralą z Home Assistanta. |

Po zapisaniu opcji integracja sama się przeładowuje.

### 5. Sterowanie i tryby pracy

Główną kontrolką jest encja **Wentylacja**:

| Tryb | Znaczenie |
|---|---|
| **Automatyczny** | Centrala pracuje według harmonogramu tygodniowego. Harmonogram edytuje się na panelu Air++. |
| **Manualny** | Stała intensywność, z nastawy *Intensywność – tryb manualny*. |
| **Chwilowy** | Tymczasowa zmiana. |

Zmiana **intensywności %**:
- w trybie **automatycznym** włącza tryb **chwilowy**, dokładnie jak pokrętło na panelu Air++,
- w trybie **manualnym** zmienia intensywność manualną.

0 % jest odrzucane. Do wyłączenia centrali służy przełącznik **Zasilanie**.

Pozostałe kontrolki:
- **Zasilanie:** włącza i wyłącza centralę, jak przycisk na panelu.
- **Sezon:** lato / zima. Wybiera harmonogram letni lub zimowy.
- **Funkcja specjalna:** brak / kominek / wietrzenie / otwarte okna / pusty dom / okap. Czujnik *Aktywna funkcja* pokazuje też funkcje uruchomione przyciskami lub czujnikami podłączonymi do centrali.
- **EKO / KOMFORT:** KOMFORT utrzymuje temperaturę nawiewu nagrzewnicą/chłodnicą kanałową lub nagrzewnicą wtórną ERV, jeśli są zamontowane.

W sekcji **Konfiguracja** (strona urządzenia):
- intensywność i temperatura nawiewu dla trybów. Nastawy trybu *chwilowego* są domyślnie ukryte, bo obsługuje je encja Wentylacja.
- włączanie bypassu i GWC oraz ich parametry,
- intensywności i czasy funkcji specjalnych,
- biegi AirS,
- przyciski wymiany filtrów: naciśnij po wymianie filtra (centrale bez AFC).

W sekcji **Diagnostyka:** oprogramowanie, wejścia i wyjścia, napięcia sterujące oraz **Wykryj ponownie sprzęt**. Użyj go po zamontowaniu nowego sprzętu, np. GWC.

Kolejność encji na stronie urządzenia jest alfabetyczna. Tak działa Home Assistant, a integracja nie może jej zmienić.

### 6. Schemat pracy

- **Panel w menu bocznym:** **AirPack4** pokazuje schemat na żywo na całym ekranie. Otwiera go też przycisk **Odwiedź** na stronie urządzenia.
  - Żeby ukryć go w menu, przytrzymaj tytuł menu bocznego i ukryj *AirPack4*.
- **Karta na pulpit:** edytuj pulpit → **+ Dodaj kartę** → wyszukaj **Thessla**. Możesz też dodać kartę *Ręczna*:

  ```yaml
  type: custom:thessla-airpack-card
  # device_id: opcjonalnie – domyślnie pierwsza centrala
  # title: opcjonalnie
  ```

Co pokazuje schemat:
- Każdą ścieżkę powietrza z temperaturą, intensywnością wentylatora, przepływem i zużyciem filtra.
- Gdy otworzy się **bypass**, wymiennik przygasa i pokazuje *BYPASS*, a nawiew płynie linią bypassu.
- FPX, GWC i nagrzewnica pojawiają się tylko wtedy, gdy centrala je ma.
- Kliknięcie elementu otwiera jego encję.

### 7. Aktualizacja

Nowe wersje są publikowane jako [wydania na GitHubie](https://github.com/BartoszJanowski/thessla-green-airpack/releases). Home Assistant pokazuje je jako aktualizację, razem z listą zmian.
- *Ustawienia → Aktualizacje* albo *Marketplace / HACS → Thessla Green AirPack4* → **Aktualizuj**.
- Żeby od razu sprawdzić nową wersję: **⋮ → Aktualizuj informacje**.
- Uruchom ponownie Home Assistanta, potem zrób twarde odświeżenie przeglądarki (Ctrl+F5 / Cmd+Shift+R).

### 8. Rozwiązywanie problemów

- **„Nie można połączyć się z bramką”:** sprawdź adres IP i port oraz to, czy bramka jest osiągalna z Home Assistanta.
- **„Bramka odpowiada, ale centrala nie”:**
  - Sprawdź adres urządzenia (10).
  - Sprawdź okablowanie A/B (spróbuj zamienić A i B).
  - Sprawdź ustawienia portu szeregowego bramki (9600 8N1).
  - Upewnij się, że bramka jest w trybie Modbus TCP→RTU.
- **Encje chwilami są *Niedostępne*:** zwiększ *Opóźnienie między zapytaniami* i *Limit czasu zapytania*. Nie podłączaj dwóch klientów Modbus do jednej bramki naraz (np. starej integracji i tej).
- **Nazwy encji są po angielsku, choć interfejs jest po polsku:** nazwy encji zależą od języka *systemu* (*Ustawienia → System → Ogólne → Język*), a nie języka profilu. Ustaw Polski i uruchom HA ponownie.
- **Karty nie ma na liście:** zrób twarde odświeżenie przeglądarki. W aplikacji mobilnej przeciągnij ekran w dół.
- **Które rejestry ma moja centrala?**
  - Strona urządzenia → **⋮ → Pobierz diagnostykę**.
  - Albo uruchom sondę tylko do odczytu. Może wysyłać wyłącznie zapytania *odczytu* Modbus:

    ```bash
    pip install pymodbus
    python -I tools/probe.py --host 192.168.1.50 --port 8899 --unit 10 --json probe-out.json
    ```

### 9. Zgłaszanie problemów

Załóż [zgłoszenie (issue)](https://github.com/BartoszJanowski/thessla-green-airpack/issues/new/choose). Podaj:
- model i wersję oprogramowania centrali,
- wersje Home Assistanta i integracji,
- plik **diagnostyki** (nie zawiera adresu IP ani numeru seryjnego).

Pull requesty nie są przyjmowane. Opisz proponowaną zmianę w zgłoszeniu.

---

## Disclaimer / Zastrzeżenie

This is an unofficial project, not affiliated with Thessla Green. Changing ventilation settings is at your own risk. Licensed under the MIT License.

Projekt nieoficjalny, niezwiązany z Thessla Green. Zmiany ustawień wentylacji wykonujesz na własną odpowiedzialność. Licencja MIT.
