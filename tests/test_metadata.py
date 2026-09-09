"""Every datapoint carries neutral metadata locating and describing it."""

from __future__ import annotations

import pytest

from lg_heatpump_modbus import EnergyState, LgHeatPump, OperationMode


def test_metadata_locates_a_holding_register(pump: LgHeatPump) -> None:
    metadata = pump.controls.require_metadata_for("dhw_target_temperature")

    assert metadata.value_kind == "number"
    assert metadata.register_type == "holding"
    assert metadata.address == 8
    assert metadata.writable is True
    assert metadata.number is not None
    assert metadata.number.unit == "°C"
    assert metadata.number.digits == 1
    assert metadata.number.step == 0.1
    assert metadata.number.min_value == 30.0
    assert metadata.number.max_value == 80.0


def test_metadata_locates_an_input_register(pump: LgHeatPump) -> None:
    metadata = pump.sensors.require_metadata_for("outdoor_temperature")

    assert metadata.register_type == "input"
    assert metadata.address == 12
    assert metadata.writable is False


def test_metadata_locates_a_coil(pump: LgHeatPump) -> None:
    metadata = pump.switches.require_metadata_for("silent_mode")

    assert metadata.value_kind == "boolean"
    assert metadata.register_type == "coil"
    assert metadata.address == 2
    assert metadata.writable is True
    assert metadata.boolean is not None


def test_metadata_locates_a_discrete_input(pump: LgHeatPump) -> None:
    metadata = pump.states.require_metadata_for("compressor")

    assert metadata.value_kind == "boolean"
    assert metadata.register_type == "discrete"
    assert metadata.address == 3
    assert metadata.writable is False


def test_enum_metadata_lists_every_option(pump: LgHeatPump) -> None:
    metadata = pump.controls.require_metadata_for("operation_mode")

    assert metadata.value_kind == "enum"
    assert metadata.enum is not None
    assert metadata.enum.enum_type is OperationMode
    assert [option.key for option in metadata.enum.options] == ["cool", "auto", "heat"]
    assert [option.value for option in metadata.enum.options] == [0, 3, 4]


def test_energy_state_options_cover_the_documented_codes(pump: LgHeatPump) -> None:
    metadata = pump.sensors.require_metadata_for("energy_state")

    assert metadata.enum is not None
    assert metadata.enum.enum_type is EnergyState
    assert len(metadata.enum.options) == 9


def test_raw_metadata_has_no_number_block(pump: LgHeatPump) -> None:
    metadata = pump.info.require_metadata_for("product_info")

    assert metadata.value_kind == "raw"
    assert metadata.register_type == "input"
    assert metadata.address == 9998
    assert metadata.number is None


def test_every_declared_field_carries_metadata(pump: LgHeatPump) -> None:
    for component in pump.components:
        assert set(component.datapoints) == set(component.declared_fields)


def test_every_datapoint_has_a_description(pump: LgHeatPump) -> None:
    for component in pump.components:
        for name, metadata in component.datapoints.items():
            assert metadata.description, f"{name} has no description"


def test_metadata_for_an_unknown_field_raises(pump: LgHeatPump) -> None:
    assert pump.controls.metadata_for("nope") is None
    with pytest.raises(KeyError):
        pump.controls.require_metadata_for("nope")


async def test_available_datapoints_lists_what_was_read(pump: LgHeatPump) -> None:
    assert pump.sensors.available_datapoints() == ()

    await pump.sensors.async_update()

    assert "outdoor_temperature" in pump.sensors.available_datapoints()


async def test_values_returns_every_declared_field(pump: LgHeatPump) -> None:
    await pump.controls.async_update()

    values = pump.controls.values()

    assert set(values) == set(pump.controls.declared_fields)
    assert values["dhw_target_temperature"] == 50.0
