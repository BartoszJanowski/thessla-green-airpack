"""Device families and models.

Every family has its own register map. All AirPack4 variants share one map;
optional hardware is detected at runtime, so the model mainly sets naming.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .registers import AIRPACK4_REGISTERS, Reg, by_key


@dataclass(frozen=True)
class Family:
    """A group of devices sharing one Modbus register map."""

    key: str
    name: str
    registers: tuple[Reg, ...]
    index: dict[str, Reg] = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "index", by_key(self.registers))


AIRPACK4 = Family("airpack4", "AirPack4", AIRPACK4_REGISTERS)

FAMILIES: dict[str, Family] = {AIRPACK4.key: AIRPACK4}

_AIRPACK4_VARIANTS = (
    *(f"{size}h {kind}" for kind in ("Enthalpy", "Energy++", "Energy+") for size in (300, 400, 500)),
    *(f"{size}v Enthalpy" for size in (300, 400, 500)),
    *(f"{size}v {kind}" for kind in ("Energy++", "Energy+") for size in (300, 400, 500, 550)),
)

# model key -> (display name, family key)
MODELS: dict[str, tuple[str, str]] = {
    "airpack4_" + v.lower().replace(" ", "_").replace("+", "p"): (f"AirPack4 {v}", AIRPACK4.key)
    for v in _AIRPACK4_VARIANTS
}

DEFAULT_MODEL = "airpack4_400v_energypp"
assert DEFAULT_MODEL in MODELS


def family_for_model(model: str) -> Family:
    """Family for a model key (falls back to AirPack4)."""
    _, family_key = MODELS.get(model, ("", AIRPACK4.key))
    return FAMILIES[family_key]


def model_name(model: str) -> str:
    """Display name for a model key."""
    return MODELS.get(model, (model, ""))[0]
