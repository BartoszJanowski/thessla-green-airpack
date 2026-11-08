"""Every entity, state and option must be translated in EN and PL."""

import json
from pathlib import Path

import pytest

from custom_components.thessla_green_airpack import (
    binary_sensor,
    number,
    select,
    sensor,
    switch,
)
from custom_components.thessla_green_airpack import time as time_platform

BASE = Path(__file__).parent.parent / "custom_components" / "thessla_green_airpack"
LANGS = {
    "strings": json.loads((BASE / "strings.json").read_text()),
    "en": json.loads((BASE / "translations" / "en.json").read_text()),
    "pl": json.loads((BASE / "translations" / "pl.json").read_text()),
}

PLATFORMS = {
    "sensor": sensor.SENSORS,
    "binary_sensor": binary_sensor.BINARY_SENSORS,
    "select": select.SELECTS,
    "switch": switch.SWITCHES,
    "number": number.NUMBERS,
    "time": time_platform.TIMES,
}
EXTRA = {
    "sensor": ["firmware"],
    "fan": ["ventilation"],
    "button": ["supply_filter_replaced", "exhaust_filter_replaced", "redetect"],
}


@pytest.mark.parametrize("lang", LANGS)
def test_entities_translated(lang: str) -> None:
    entity = LANGS[lang]["entity"]
    for platform, descriptions in PLATFORMS.items():
        for d in descriptions:
            key = d.translation_key or d.key
            assert key in entity[platform], f"{lang}: {platform}.{key}"
            states = entity[platform][key].get("state", {})
            for option in getattr(d, "options", None) or []:
                assert option in states, f"{lang}: {platform}.{key} state {option}"
            for option in getattr(d, "mapping", {}).values():
                assert option in states, f"{lang}: {platform}.{key} option {option}"
    for platform, keys in EXTRA.items():
        for key in keys:
            assert key in entity[platform], f"{lang}: {platform}.{key}"


@pytest.mark.parametrize("lang", LANGS)
def test_exceptions_translated(lang: str) -> None:
    source = (BASE / "coordinator.py").read_text() + (BASE / "fan.py").read_text() + (BASE / "button.py").read_text()
    import re

    for key in set(re.findall(r'translation_key="([a-z_]+)"', source)):
        assert key in LANGS[lang]["exceptions"], f"{lang}: exception {key}"
