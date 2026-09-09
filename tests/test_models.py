"""Device models describe variants as data, not as code."""

from __future__ import annotations

import pytest

from lg_heatpump_modbus import (
    MODELS,
    THERMA_V,
    THERMA_V_HEATING_ONLY,
    THERMA_V_SINGLE_CIRCUIT,
    LgHeatPump,
    ModelDefinition,
    get_model,
)
from lg_heatpump_modbus.configurations.models import (
    CIRCUIT_2_DATAPOINTS,
    DHW_DATAPOINTS,
    SOLAR_DATAPOINTS,
)


def test_every_model_is_registered_under_its_key() -> None:
    assert set(MODELS) == {
        "therma_v",
        "therma_v_single_circuit",
        "therma_v_heating_only",
    }
    for key, model in MODELS.items():
        assert model.key == key


def test_get_model_returns_the_registered_definition() -> None:
    assert get_model("therma_v") is THERMA_V


def test_get_model_rejects_an_unknown_key() -> None:
    with pytest.raises(ValueError, match="Unknown model"):
        get_model("therma_x")


def test_the_full_model_excludes_nothing() -> None:
    assert THERMA_V.excluded_datapoints == frozenset()


def test_a_single_circuit_model_excludes_circuit_2() -> None:
    excluded = THERMA_V_SINGLE_CIRCUIT.excluded_datapoints

    assert CIRCUIT_2_DATAPOINTS <= excluded
    assert SOLAR_DATAPOINTS <= excluded
    assert not DHW_DATAPOINTS & excluded


def test_a_heating_only_model_excludes_hot_water() -> None:
    assert DHW_DATAPOINTS <= THERMA_V_HEATING_ONLY.excluded_datapoints


def test_supported_keeps_declaration_order() -> None:
    names = ("dhw_tank_temperature", "outdoor_temperature", "dhw_target_temperature")

    assert THERMA_V_HEATING_ONLY.supported(names) == ("outdoor_temperature",)


def test_a_model_cannot_claim_three_circuits() -> None:
    with pytest.raises(ValueError, match="1 or 2 circuits"):
        ModelDefinition(key="odd", name="Odd", circuits=3)


def test_a_model_can_be_named_by_key(unit: object) -> None:
    pump = LgHeatPump(unit, model="therma_v_single_circuit")  # type: ignore[arg-type]

    assert pump.model is THERMA_V_SINGLE_CIRCUIT
    assert pump.model_name == "LG Therma V (single circuit)"


def test_naming_an_unknown_model_raises(unit: object) -> None:
    with pytest.raises(ValueError, match="Unknown model"):
        LgHeatPump(unit, model="therma_x")  # type: ignore[arg-type]


def test_a_new_variant_needs_no_code(unit: object) -> None:
    """A variant is a ModelDefinition; nothing else has to change."""
    variant = ModelDefinition(
        key="oem_variant",
        name="OEM variant",
        circuits=1,
        has_solar=False,
        has_mixing_valve=False,
        has_refrigerant_diagnostics=False,
    )

    pump = LgHeatPump(unit, model=variant)  # type: ignore[arg-type]

    assert pump.model_name == "OEM variant"
    assert pump.serves("high_pressure") is False
    assert pump.serves("water_outlet_temperature") is True


def test_the_heat_pump_reports_its_identity(pump: LgHeatPump) -> None:
    assert pump.manufacturer == "LG"
    assert pump.model_name == "LG Therma V"
    assert pump.component_names == (
        "info",
        "sensors",
        "states",
        "controls",
        "switches",
    )
