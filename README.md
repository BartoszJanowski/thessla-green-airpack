# Thessla Green AirPack for Home Assistant

A Home Assistant integration for **Thessla Green AirPack4** recuperators (heat-recovery ventilation units). It connects over Modbus through any Modbus TCP → RTU gateway (Elfin EW11/EW10, Waveshare, USR, …).

- **Read and change settings:** operating mode, airflow, season, special functions (hood, fireplace, airing, open windows, empty house), ECO/COMFORT, bypass, GWC, special-function intensities and durations, and filter replacement.
- **Two-way sync:** changes made on the Air++ panel (or AirS, or AirMobile) show up in Home Assistant on the next poll. The default interval is 30 s.
- **Never breaks on other models:** the integration probes which registers your unit actually has.
  - Missing registers (e.g. ERV on units without it) are skipped instead of failing the whole update.
  - Sensors that aren't fitted are hidden.
  - A value the unit can't read right now shows *Unknown*.
- **Dashboard card:** a live air-flow diagram similar to the Air++ unit screen. It is registered automatically.
- English and Polish.

## Supported devices

All AirPack4 variants covered by the manufacturer's `MODBUS_USER_AirPack_4` register map:

| | Enthalpy | Energy+ | Energy++ |
|---|---|---|---|
| **h** (horizontal) | 300 / 400 / 500 | 300 / 400 / 500 | 300 / 400 / 500 |
| **v** (vertical) | 300 / 400 / 500 | 300 / 400 / 500 / 550 | 300 / 400 / 500 / 550 |

Optional hardware is detected automatically: GWC, duct heater/cooler, constant flow (CF), the Expansion module, and ERV. If you add hardware later, press **Re-detect hardware** on the device page.

## Hardware setup

1. Wire the gateway's RS-485 A/B to the AirPack's **Air-B** port. The Air++ panel keeps its own port.
2. Configure the gateway's serial side as **9600 baud, 8 data bits, no parity, 1 stop bit**.
3. Set the gateway protocol to **Modbus TCP ↔ RTU conversion**.
   - On an Elfin EW11, that means *Protocol: Modbus*. Its local port is usually `502` or `8899`.
   - Transparent / raw TCP mode is **not** supported.
4. The AirPack's Modbus address defaults to **10** (allowed range 10–19).

## Installation

### HACS (custom repository)
1. HACS → ⋮ → *Custom repositories* → add this repository's URL, category **Integration**.
2. Install **Thessla Green AirPack** and restart Home Assistant.

### Manual
Copy `custom_components/thessla_green_airpack` to `<config>/custom_components/` and restart Home Assistant.

### Add the device
Go to *Settings → Devices & services → Add integration → Thessla Green AirPack*. Enter:
- the gateway's IP address and port
- the device address (10)
- your model

**Options:**
- **Polling interval:** 5–300 s.
- **Request timeout.**
- **Delay between requests:** raise it for flaky Wi-Fi gateways.
- **Read-only mode:** blocks every write. Useful for a first, cautious install.

## Entities (overview)

| Type | What |
|---|---|
| Fan | **Ventilation** – airflow % and presets *Automatic / Manual / Temporary*. Changing airflow in Automatic starts a *Temporary* override, exactly like the Air++ panel. |
| Switch | Power, bypass enabled, GWC enabled |
| Select | Season, special function, ECO/COMFORT, bypass mode, GWC regeneration |
| Sensor | Temperatures (outside, supply, extract, FPX, duct, GWC, ambient), airflow m³/h, intensity %, filter wear %, filter dates, heat-recovery efficiency, active function, bypass/GWC/COMFORT/FPX state, active alarms |
| Binary sensor | Warning (E), error (S), bypass damper, FPX, GWC regeneration, outputs and inputs (diagnostic) |
| Number / Time | Manual/temporary airflow and temperatures, AirS gears, special-function intensities and durations, bypass and GWC parameters |
| Button | Supply / exhaust filter replaced, re-detect hardware |

Some things are deliberately **not** exposed:
- Weekly schedules (planned).
- Settings that could lock you out or require service access: Modbus port settings, factory reset, product key, calibration.

## Dashboard card

```yaml
type: custom:thessla-airpack-card
# device_id: optional – defaults to the first AirPack
# title: optional
```

The card shows:
- intake → filter → FPX → supply fan → heat exchanger → supply
- extract → filter → exhaust fan → heat exchanger → exhaust

Temperatures, airflow, fan intensity and filter wear appear along those paths. When the **bypass** opens, the supply air is drawn around the exchanger. GWC, FPX and the duct heater are drawn only if your unit has them. Tap any element to open its entity.

## Troubleshooting

- **"Gateway reachable but the AirPack does not answer"**:
  - Check the device address (10).
  - Check A/B wiring.
  - Check the gateway serial settings (9600 8N1).
  - Make sure the gateway is in Modbus TCP→RTU mode.
- **Slow or unreliable Wi-Fi gateway:** increase *Delay between requests* (e.g. 50–100 ms) and the timeout. Don't connect two Modbus clients to the same gateway at once.
- **Which registers does my unit have?** Download *Diagnostics* from the device page, or run the read-only probe:

  ```bash
  pip install pymodbus
  python -I tools/probe.py --host 192.168.1.50 --port 502 --unit 10 --json probe-out.json
  ```

  The probe can only send Modbus *read* requests. Writes are blocked twice: by a client proxy, and by a check of the function code before any frame is sent.

## Development

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements_test.txt
.venv/bin/python -m pytest
```

- `tools/card_preview.html`: open it in a browser to see the card in several scenarios with mocked data. Add `?lang=pl` for Polish and `?w=360` for phone width.
- `tools/gen_translations.py`: regenerates `strings.json` and `translations/{en,pl}.json`.

## Disclaimer

This is an unofficial project, not affiliated with Thessla Green. Changing ventilation settings is at your own risk.
