"""Generate strings.json and translations/{en,pl}.json from one table.

Usage: python3 tools/gen_translations.py
"""
import json
from pathlib import Path

out = Path(__file__).resolve().parent.parent / "custom_components" / "thessla_green_airpack"

# (en, pl)
N = {
 "sensor": {
  "outside_temperature": ("Temperature – intake (outside)", "Temperatura czerpni"),
  "supply_temperature": ("Temperature – supply", "Temperatura nawiewu"),
  "exhaust_temperature": ("Temperature – extract", "Temperatura wywiewu"),
  "fpx_temperature": ("Temperature – after FPX", "Temperatura za FPX"),
  "duct_supply_temperature": ("Temperature – duct supply", "Temperatura nawiewu za nagrzewnicą kanałową"),
  "gwc_temperature": ("Temperature – GWC", "Temperatura GWC"),
  "ambient_temperature": ("Temperature – ambient", "Temperatura otoczenia"),
  "required_temperature": ("Temperature – comfort target", "Temperatura zadana KOMFORT"),
  "supply_air_flow": ("Supply airflow", "Strumień nawiewu"),
  "exhaust_air_flow": ("Exhaust airflow", "Strumień wywiewu"),
  "supply_flowrate": ("Target supply airflow", "Zadany strumień nawiewu"),
  "exhaust_flowrate": ("Target exhaust airflow", "Zadany strumień wywiewu"),
  "supply_percentage": ("Supply intensity", "Intensywność nawiewu"),
  "exhaust_percentage": ("Exhaust intensity", "Intensywność wywiewu"),
  "min_percentage": ("Minimum intensity", "Minimalna intensywność"),
  "max_percentage": ("Maximum intensity", "Maksymalna intensywność"),
  "supply_filter_wear": ("Supply filter wear", "Zużycie filtra nawiewnego"),
  "exhaust_filter_wear": ("Exhaust filter wear", "Zużycie filtra wywiewnego"),
  "heat_recovery_efficiency": ("Heat recovery efficiency", "Sprawność odzysku ciepła"),
  "supply_filter_date": ("Supply filter replacement due", "Termin wymiany filtra nawiewnego"),
  "exhaust_filter_date": ("Exhaust filter replacement due", "Termin wymiany filtra wywiewnego"),
  "active_alarms": ("Active alarms", "Aktywne alarmy"),
  "stop_ahu_code": ("Stop alarm code", "Kod alarmu zatrzymującego"),
  "dac_supply": ("Supply fan control voltage", "Napięcie sterujące wentylatora nawiewnego"),
  "dac_exhaust": ("Exhaust fan control voltage", "Napięcie sterujące wentylatora wywiewnego"),
  "dac_heater": ("Duct heater control voltage", "Napięcie sterujące nagrzewnicy"),
  "dac_cooler": ("Duct cooler control voltage", "Napięcie sterujące chłodnicy"),
  "firmware": ("Firmware", "Oprogramowanie"),
  "schedule_period": ("Schedule period", "Odcinek czasowy harmonogramu"),
 },
 "binary_sensor": {
  "alarm": ("Warning (E)", "Ostrzeżenie (E)"),
  "error": ("Error (S)", "Błąd (S)"),
  "bypass_actuator": ("Bypass", "Bypass"),
  "antifreeze_mode": ("FPX anti-freeze", "System FPX"),
  "gwc_regen_flag": ("GWC regeneration", "Regeneracja GWC"),
  "constant_flow_active": ("Constant flow", "Constant Flow"),
  "post_heater_on": ("ERV post-heater", "Nagrzewnica wtórna ERV"),
  "power_supply_fans": ("Fans power", "Zasilanie wentylatorów"),
  "gwc_relay": ("GWC relay", "Przekaźnik GWC"),
  "heating_cable": ("Heating cable", "Kabel grzejny"),
  "duct_water_heater_pump": ("Water heater pump", "Pompa nagrzewnicy wodnej"),
  "work_permit": ("Operation confirmation (Expansion)", "Potwierdzenie pracy (Expansion)"),
  "info_output": ("Operation confirmation output (O1)", "Wyjście potwierdzenia pracy (O1)"),
  "hood_output": ("Hood damper output", "Wyjście przepustnicy okapu"),
  "expansion": ("Expansion module", "Moduł Expansion"),
  "fire_alarm_input": ("Fire alarm input (P.POZ.)", "Wejście P.POZ."),
  "duct_heater_protection": ("Duct heater thermal protection", "Zabezpieczenie termiczne nagrzewnicy kanałowej"),
  "ahu_filter_protection": ("FPX heater thermal protection", "Zabezpieczenie termiczne nagrzewnicy FPX"),
  "dp_ahu_filter_overflow": ("Filter pressure switch (DP1)", "Presostat filtrów (DP1)"),
  "dp_duct_filter_overflow": ("Duct filter pressure switch", "Presostat filtra kanałowego"),
  "hood_input": ("Hood input", "Wejście OKAP"),
  "contamination_sensor": ("Air quality input", "Wejście czujnika jakości powietrza"),
  "airing_sensor": ("Humidity input", "Wejście czujnika wilgotności"),
  "airing_switch": ("Airing switch input", "Wejście włącznika WIETRZENIE"),
  "airing_mini": ("AirS airing", "AirS – wietrzenie"),
  "fan_speed_1_input": ("AirS gear 1", "AirS – bieg 1"),
  "fan_speed_2_input": ("AirS gear 2", "AirS – bieg 2"),
  "fan_speed_3_input": ("AirS gear 3", "AirS – bieg 3"),
  "fireplace_input": ("Fireplace input", "Wejście KOMINEK"),
  "empty_house_input": ("Empty house input", "Wejście PUSTY DOM"),
 },
 "switch": {
  "power": ("Power", "Zasilanie"),
  "bypass_enabled": ("Bypass enabled", "Bypass aktywny"),
  "gwc_enabled": ("GWC enabled", "GWC aktywny"),
 },
 "number": {
  "air_flow_rate_manual": ("Manual airflow", "Intensywność – tryb manualny"),
  "air_flow_rate_temporary": ("Temporary airflow", "Intensywność – tryb chwilowy"),
  "supply_air_temperature_manual": ("Manual supply temperature", "Temperatura nawiewu – tryb manualny"),
  "supply_air_temperature_temporary": ("Temporary supply temperature", "Temperatura nawiewu – tryb chwilowy"),
  "fan_speed_1_coef": ("AirS gear 1 intensity", "AirS – intensywność biegu 1"),
  "fan_speed_2_coef": ("AirS gear 2 intensity", "AirS – intensywność biegu 2"),
  "fan_speed_3_coef": ("AirS gear 3 intensity", "AirS – intensywność biegu 3"),
  "hood_supply_coef": ("Hood supply intensity", "OKAP – intensywność nawiewu"),
  "hood_exhaust_coef": ("Hood exhaust intensity", "OKAP – intensywność wywiewu"),
  "fireplace_supply_coef": ("Fireplace supply surplus", "KOMINEK – różnicowanie strumieni"),
  "airing_bathroom_coef": ("Bathroom airing intensity", "WIETRZENIE (łazienka) – intensywność"),
  "airing_coef": ("Room airing intensity", "WIETRZENIE (pokoje) – intensywność"),
  "contamination_coef": ("Air quality airing intensity", "WIETRZENIE (jakość powietrza) – intensywność"),
  "empty_house_coef": ("Empty house intensity", "PUSTY DOM – intensywność"),
  "airing_switch_coef": ("Switch airing intensity", "WIETRZENIE (przełącznik) – intensywność"),
  "open_window_coef": ("Open windows exhaust intensity", "OTWARTE OKNA – intensywność wywiewu"),
  "airing_panel_mode_time": ("Room airing duration", "WIETRZENIE (pokoje) – czas"),
  "airing_switch_mode_time": ("Bell switch airing duration", "WIETRZENIE (dzwonkowy) – czas"),
  "airing_switch_mode_on_delay": ("Switch airing on delay", "WIETRZENIE – opóźnienie załączenia"),
  "airing_switch_mode_off_delay": ("Switch airing off delay", "WIETRZENIE – opóźnienie wyłączenia"),
  "fireplace_mode_time": ("Fireplace duration", "KOMINEK – czas"),
  "min_bypass_temperature": ("Bypass minimum outside temperature", "Bypass – min. temperatura zewnętrzna"),
  "air_temperature_summer_free_heating": ("Bypass free heating temperature", "Bypass – temperatura freeheating"),
  "air_temperature_summer_free_cooling": ("Bypass free cooling temperature", "Bypass – temperatura freecooling"),
  "bypass_coef_1": ("Bypass airflow unbalance", "Bypass – różnicowanie strumieni"),
  "bypass_coef_2": ("Bypass supply intensity", "Bypass – intensywność nawiewu"),
  "min_gwc_air_temperature": ("GWC lower threshold", "GWC – dolny próg temperatury"),
  "max_gwc_air_temperature": ("GWC upper threshold", "GWC – górny próg temperatury"),
  "delta_t_gwc": ("GWC regeneration temperature difference", "GWC – różnica temperatur regeneracji"),
  "gwc_regen_period": ("GWC regeneration duration", "GWC – czas regeneracji"),
 },
 "time": {
  "manual_airing_time_to_start": ("Manual mode airing start", "Start wietrzenia w trybie manualnym"),
  "start_gwc_regen_winter_time": ("GWC winter regeneration start", "GWC – start regeneracji zimą"),
  "stop_gwc_regen_winter_time": ("GWC winter regeneration end", "GWC – koniec regeneracji zimą"),
  "start_gwc_regen_summer_time": ("GWC summer regeneration start", "GWC – start regeneracji latem"),
  "stop_gwc_regen_summer_time": ("GWC summer regeneration end", "GWC – koniec regeneracji latem"),
  "pres_check_time": ("Filter check time", "Godzina kontroli filtrów"),
 },
 "button": {
  "supply_filter_replaced": ("Supply filter replaced", "Wymieniono filtr nawiewny"),
  "exhaust_filter_replaced": ("Exhaust filter replaced", "Wymieniono filtr wywiewny"),
  "redetect": ("Re-detect hardware", "Wykryj ponownie sprzęt"),
 },
}

WEEK = {"monday": ("Monday","Poniedziałek"), "tuesday": ("Tuesday","Wtorek"), "wednesday": ("Wednesday","Środa"),
        "thursday": ("Thursday","Czwartek"), "friday": ("Friday","Piątek"), "saturday": ("Saturday","Sobota"), "sunday": ("Sunday","Niedziela")}
MODES = {"auto": ("Automatic","Automatyczny"), "manual": ("Manual","Manualny"), "temporary": ("Temporary","Chwilowy")}
SPECIAL = {
 "none": ("None","Brak"), "hood": ("Hood","Okap"), "fireplace": ("Fireplace","Kominek"),
 "airing_bell_switch": ("Airing (bell switch)","Wietrzenie (przeł. dzwonkowy)"),
 "airing_switch": ("Airing (on/off switch)","Wietrzenie (przełącznik)"),
 "airing_hygrostat": ("Airing (hygrostat)","Wietrzenie (higrostat)"),
 "airing_air_quality": ("Airing (air quality)","Wietrzenie (jakość powietrza)"),
 "airing_manual": ("Airing (manual)","Wietrzenie (ręczne)"),
 "airing_auto_schedule": ("Airing (auto schedule)","Wietrzenie (tryb automatyczny)"),
 "airing_manual_schedule": ("Airing (manual mode schedule)","Wietrzenie (tryb manualny)"),
 "open_windows": ("Open windows","Otwarte okna"), "empty_house": ("Empty house","Pusty dom"),
}
STATE_SENSORS = {
 "operating_mode": (("Operating mode","Tryb pracy"), MODES),
 "active_function": (("Active function","Aktywna funkcja"), SPECIAL),
 "bypass_state": (("Bypass state","Stan bypass"), {"inactive": ("Inactive","Nieaktywny"), "free_heating": ("Free heating","Freeheating"), "free_cooling": ("Free cooling","Freecooling")}),
 "gwc_state": (("GWC state","Stan GWC"), {"inactive": ("Inactive","Nieaktywny"), "winter": ("Winter","Zima"), "summer": ("Summer","Lato")}),
 "comfort_state": (("Comfort state","Stan trybu KOMFORT"), {"inactive": ("Inactive","Nieaktywny"), "heating": ("Heating","Grzanie"), "cooling": ("Cooling","Chłodzenie")}),
 "fpx_state": (("FPX mode","Tryb FPX"), {"off": ("Off","Wyłączony"), "fpx1": ("FPX1","FPX1"), "fpx2": ("FPX2","FPX2")}),
 "schedule_day": (("Schedule day","Dzień harmonogramu"), WEEK),
}
SELECTS = {
 "season_mode": (("Season","Sezon"), {"summer": ("Summer","Lato"), "winter": ("Winter","Zima")}),
 "special_mode": (("Special function","Funkcja specjalna"), {k: SPECIAL[k] for k in ("none","hood","fireplace")} | {"airing": ("Airing","Wietrzenie"), "open_windows": SPECIAL["open_windows"], "empty_house": SPECIAL["empty_house"]}),
 "comfort_mode_panel": (("ECO / COMFORT","EKO / KOMFORT"), {"eco": ("ECO","EKO"), "comfort": ("COMFORT","KOMFORT")}),
 "bypass_user_mode": (("Bypass mode","Tryb bypass"), {"damper_only": ("Damper only","Tylko przepustnica"), "damper_unbalance": ("Damper + airflow unbalance","Przepustnica + różnicowanie"), "damper_exhaust_off": ("Damper + exhaust fan off","Przepustnica + wyłączenie wywiewu")}),
 "gwc_regen": (("GWC regeneration","Regeneracja GWC"), {"none": ("None","Brak"), "daily": ("Daily schedule","Dobowa"), "temperature": ("Temperature","Temperaturowa")}),
 "post_heater_mode": (("ERV heater mode","Tryb nagrzewnicy ERV"), {"inactive": ("Inactive","Nieaktywna"), "mode_1": ("Mode 1","Tryb 1"), "mode_2": ("Mode 2","Tryb 2")}),
 "pres_check_day": (("Filter check day","Dzień kontroli filtrów"), WEEK),
}

CONFIG = {
 "step": {
  "user": {
   "title": ("Thessla Green AirPack", "Thessla Green AirPack"),
   "description": ("Connect through a Modbus TCP → RTU gateway (e.g. Elfin EW11, Waveshare) wired to the AirPack Air-B port (9600 8N1).",
                   "Połączenie przez bramkę Modbus TCP → RTU (np. Elfin EW11, Waveshare) podłączoną do portu Air-B centrali (9600 8N1)."),
   "data": {"name": ("Name","Nazwa"), "host": ("Gateway host / IP","Adres bramki / IP"), "port": ("TCP port","Port TCP"),
            "unit_id": ("Modbus device address","Adres urządzenia Modbus"), "model": ("Model","Model")},
   "data_description": {"unit_id": ("AirPack default is 10 (range 10–19).","Domyślnie 10 (zakres 10–19)."),
                        "model": ("Optional hardware is detected automatically.","Wyposażenie dodatkowe wykrywane jest automatycznie.")},
  },
  "reconfigure": {
   "title": ("Change connection","Zmiana połączenia"),
   "data": {"host": ("Gateway host / IP","Adres bramki / IP"), "port": ("TCP port","Port TCP"), "unit_id": ("Modbus device address","Adres urządzenia Modbus")},
  },
 },
 "error": {
  "cannot_connect": ("Cannot connect to the gateway. Check IP address and port.","Nie można połączyć się z bramką. Sprawdź adres IP i port."),
  "no_response": ("The gateway is reachable but the AirPack does not answer. Check the device address, wiring and gateway serial settings (9600 8N1, Modbus TCP→RTU).",
                  "Bramka odpowiada, ale centrala nie. Sprawdź adres urządzenia, okablowanie i ustawienia portu szeregowego bramki (9600 8N1, Modbus TCP→RTU)."),
  "invalid_response": ("The device does not look like an AirPack.","Urządzenie nie wygląda na centralę AirPack."),
  "unknown": ("Unexpected error","Nieoczekiwany błąd"),
 },
 "abort": {
  "already_configured": ("This AirPack is already configured","Ta centrala jest już skonfigurowana"),
  "reconfigure_successful": ("Connection updated","Połączenie zaktualizowane"),
  "wrong_device": ("A different AirPack answered at this address","Pod tym adresem odpowiada inna centrala"),
 },
}
OPTIONS = {
 "step": {"init": {
  "title": ("Options","Opcje"),
  "data": {"scan_interval": ("Polling interval","Interwał odpytywania"), "timeout": ("Request timeout","Limit czasu zapytania"),
           "request_delay": ("Delay between requests","Opóźnienie między zapytaniami"), "read_only": ("Read-only mode","Tryb tylko do odczytu"),
           "special_functions": ("Special functions available on the panel","Funkcje specjalne dostępne na panelu")},
  "data_description": {"request_delay": ("Increase for slow or unreliable gateways.","Zwiększ dla wolnych lub niestabilnych bramek."),
                       "read_only": ("Block every write to the device.","Blokuje każdy zapis do centrali."),
                       "special_functions": ("Shown in the Special function selector. Untick functions your installer has not configured (e.g. Hood) - this cannot be detected over Modbus.",
                                             "Pokazywane w wyborze funkcji specjalnej. Odznacz funkcje, których instalator nie skonfigurował (np. Okap) - nie da się tego wykryć przez Modbus.")},
 }},
}
EXC = {
 "read_only": ("The integration is in read-only mode.","Integracja działa w trybie tylko do odczytu."),
 "invalid_value": ("The device rejected the value.","Centrala odrzuciła wartość."),
 "write_failed": ("Writing to the device failed: {error}","Zapis do centrali nie powiódł się: {error}"),
 "out_of_range": ("Value out of range: {error}","Wartość poza zakresem: {error}"),
 "use_power_switch": ("Airflow cannot be 0%. Use the Power switch to turn the unit off.","Intensywność nie może wynosić 0%. Użyj przełącznika Zasilanie, aby wyłączyć centralę."),
 "detect_failed": ("Hardware detection failed: {error}","Wykrywanie sprzętu nie powiodło się: {error}"),
}

def pick(tree, i):
    if isinstance(tree, tuple): return tree[i]
    return {k: pick(v, i) for k, v in tree.items()}

def build(i):
    ent = {plat: {k: {"name": v[i]} for k, v in items.items()} for plat, items in N.items()}
    for k, (name, states) in STATE_SENSORS.items():
        ent["sensor"][k] = {"name": name[i], "state": {s: v[i] for s, v in states.items()}}
    ent["select"] = {k: {"name": name[i], "state": {s: v[i] for s, v in states.items()}} for k, (name, states) in SELECTS.items()}
    ent["fan"] = {"ventilation": {"name": ("Ventilation","Wentylacja")[i],
                  "state_attributes": {"preset_mode": {"state": {s: v[i] for s, v in MODES.items()}},
                                       "airflow": {"name": ("Airflow","Intensywność")[i]}}}}
    selector = {"special_functions": {"options": {
        "hood": ("Hood","Okap")[i], "fireplace": ("Fireplace","Kominek")[i], "airing": ("Airing","Wietrzenie")[i],
        "open_windows": ("Open windows","Otwarte okna")[i], "empty_house": ("Empty house","Pusty dom")[i]}}}
    return {"config": pick(CONFIG, i), "options": pick(OPTIONS, i), "selector": selector, "entity": ent,
            "exceptions": {k: {"message": v[i]} for k, v in EXC.items()}}

en, pl = build(0), build(1)
(out / "strings.json").write_text(json.dumps(en, indent=2, ensure_ascii=False) + "\n")
(out / "translations" / "en.json").write_text(json.dumps(en, indent=2, ensure_ascii=False) + "\n")
(out / "translations" / "pl.json").write_text(json.dumps(pl, indent=2, ensure_ascii=False) + "\n")
print("ok", sum(len(v) for v in en["entity"].values()), "entities")
