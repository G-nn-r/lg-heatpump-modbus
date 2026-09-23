"""A poll costs as few Modbus round-trips as the register map allows."""

from __future__ import annotations

from modbus_connection.mock import MockModbusUnit

from lg_heatpump_modbus import (
    THERMA_V,
    THERMA_V_HEATING_ONLY,
    THERMA_V_SINGLE_CIRCUIT,
    LgHeatPump,
)


async def test_full_poll_is_seven_block_reads(
    pump: LgHeatPump, unit: MockModbusUnit
) -> None:
    await pump.async_update()

    blocks = [
        (event.register_type, event.address, event.count) for event in unit.read_events
    ]
    assert blocks == [
        ("input", 9997, 2),  # identity block: product group + device info
        ("input", 0, 13),  # the first contiguous measurement block
        ("input", 16, 1),  # the isolated liquid-pipe reading
        ("input", 18, 7),  # the remaining contiguous diagnostics block
        ("discrete_input", 0, 17),  # every status flag
        ("holding", 0, 10),  # every setpoint
        ("coil", 0, 6),  # every command
    ]


async def test_identity_is_read_once(pump: LgHeatPump, unit: MockModbusUnit) -> None:
    await pump.async_update()
    unit.read_events.clear()

    await pump.async_update()

    assert not [event for event in unit.read_events if event.address == 9997]


async def test_no_block_exceeds_the_modbus_ceiling(
    pump: LgHeatPump, unit: MockModbusUnit
) -> None:
    await pump.async_update()

    assert all(event.count <= 125 for event in unit.read_events)


async def test_readings_and_settings_poll_their_own_blocks(
    pump: LgHeatPump, unit: MockModbusUnit
) -> None:
    await pump.async_update_readings()
    unit.read_events.clear()

    report = await pump.async_update_settings()

    assert report.updated == ["controls", "switches"]
    assert [event.register_type for event in unit.read_events] == ["holding", "coil"]


async def test_a_model_without_a_second_circuit_never_reads_it(
    unit: MockModbusUnit,
) -> None:
    pump = LgHeatPump(unit, model=THERMA_V_SINGLE_CIRCUIT)

    await pump.async_update()

    assert pump.serves("target_temperature_circuit_2") is False
    assert pump.controls.target_temperature_circuit_2 is None
    holding = [
        (event.address, event.count)
        for event in unit.read_events
        if event.register_type == "holding"
    ]
    assert holding == [(0, 5), (8, 2)]  # registers 5-7 are never asked for


async def test_a_model_without_hot_water_never_reads_it(
    unit: MockModbusUnit,
) -> None:
    pump = LgHeatPump(unit, model=THERMA_V_HEATING_ONLY)

    await pump.async_update()

    assert pump.controls.dhw_target_temperature is None
    assert pump.sensors.dhw_tank_temperature is None
    assert pump.switches.dhw is None


async def test_excluded_datapoints_narrow_the_plan(unit: MockModbusUnit) -> None:
    pump = LgHeatPump(unit, excluded_datapoints=["solar_collector_temperature"])

    await pump.async_update()

    assert pump.serves("solar_collector_temperature") is False
    assert pump.sensors.solar_collector_temperature is None
    assert pump.sensors.dhw_tank_temperature == 48.2  # neighbours still read


async def test_the_default_model_serves_the_whole_map(unit: MockModbusUnit) -> None:
    pump = LgHeatPump(unit)

    assert pump.model is THERMA_V
    assert all(pump.serves(name) for name in pump.sensors.declared_fields)
    assert all(pump.serves(name) for name in pump.controls.declared_fields)


async def test_read_raw_covers_every_space(pump: LgHeatPump) -> None:
    raw = await pump.async_read_raw()

    assert set(raw) == {"input", "holding", "coil", "discrete"}
    assert raw["input"][12] == 0x10000 - 42
    assert raw["input"][9998] == 0x1A2B
    assert raw["holding"][8] == 500
    assert raw["coil"][0] is True
    assert raw["discrete"][3] is True
