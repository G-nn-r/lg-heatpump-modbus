"""Writes reach the right register, and invalid values never leave the library."""

from __future__ import annotations

import pytest
from modbus_connection import IllegalDataValueError
from modbus_connection.mock import MockModbusUnit

from lg_heatpump_modbus import (
    ControlMethod,
    LgHeatPump,
    LgValueValidationError,
    OperationMode,
)


async def test_write_setpoint_scales_the_value(
    pump: LgHeatPump, unit: MockModbusUnit
) -> None:
    await pump.controls.set_dhw_target_temperature(48.5)

    assert unit.holding[8] == 485


async def test_write_negative_shift_uses_twos_complement(
    pump: LgHeatPump, unit: MockModbusUnit
) -> None:
    await pump.controls.set_shift_in_auto_mode(1, -3)

    assert unit.holding[4] == 0x10000 - 3


@pytest.mark.parametrize(
    ("circuit", "address"),
    [(1, 2), (2, 5)],
)
async def test_write_target_temperature_per_circuit(
    pump: LgHeatPump, unit: MockModbusUnit, circuit: int, address: int
) -> None:
    await pump.controls.set_target_temperature(circuit, 37.0)

    assert unit.holding[address] == 370


async def test_write_operation_mode(pump: LgHeatPump, unit: MockModbusUnit) -> None:
    await pump.controls.set_operation_mode(OperationMode.COOL)

    assert unit.holding[0] == 0


async def test_write_control_method(pump: LgHeatPump, unit: MockModbusUnit) -> None:
    await pump.controls.set_control_method(ControlMethod.ROOM_AIR)

    assert unit.holding[1] == 2


@pytest.mark.parametrize(
    ("method", "address"),
    [
        ("set_heating_circuit", 0),
        ("set_dhw", 1),
        ("set_silent_mode", 2),
        ("set_dhw_disinfection", 3),
        ("set_emergency_stop", 4),
        ("set_trigger_emergency_operation", 5),
    ],
)
async def test_write_coils(
    pump: LgHeatPump, unit: MockModbusUnit, method: str, address: int
) -> None:
    await getattr(pump.switches, method)(True)

    assert unit.coils[address] is True


async def test_a_single_register_write_uses_fc06(
    pump: LgHeatPump, unit: MockModbusUnit
) -> None:
    events = []
    unit.on_write(events.append)

    await pump.controls.set_dhw_target_temperature(52.0)

    assert len(events) == 1
    assert events[0].function_code == 0x06
    assert events[0].address == 8
    assert events[0].values == [520]


@pytest.mark.parametrize(
    ("method", "value"),
    [
        ("set_dhw_target_temperature", 95.0),
        ("set_dhw_target_temperature", 10.0),
    ],
)
async def test_out_of_range_write_is_rejected_locally(
    pump: LgHeatPump, unit: MockModbusUnit, method: str, value: float
) -> None:
    before = unit.holding[8]

    with pytest.raises(LgValueValidationError):
        await getattr(pump.controls, method)(value)

    assert unit.holding[8] == before


@pytest.mark.parametrize("value", [-6, 6])
async def test_out_of_range_shift_is_rejected_locally(
    pump: LgHeatPump, value: int
) -> None:
    with pytest.raises(LgValueValidationError):
        await pump.controls.set_shift_in_auto_mode(1, value)


async def test_unknown_enum_write_is_rejected_locally(pump: LgHeatPump) -> None:
    with pytest.raises(LgValueValidationError, match="OperationMode"):
        await pump.controls.write("operation_mode", 7)


async def test_read_only_field_cannot_be_written(pump: LgHeatPump) -> None:
    with pytest.raises(AttributeError):
        await pump.sensors.write("outdoor_temperature", 5.0)


async def test_discrete_input_cannot_be_written(pump: LgHeatPump) -> None:
    with pytest.raises(AttributeError):
        await pump.states.write("compressor", True)


async def test_a_write_the_device_refuses_propagates(
    pump: LgHeatPump, unit: MockModbusUnit
) -> None:
    unit.fail_write(8, IllegalDataValueError())

    with pytest.raises(IllegalDataValueError):
        await pump.controls.set_dhw_target_temperature(55.0)

    assert unit.holding[8] == 500  # unchanged


async def test_writable_datapoints_are_declared(pump: LgHeatPump) -> None:
    assert pump.controls.writable_datapoints == (
        "operation_mode",
        "control_method",
        "target_temperature_circuit_1",
        "room_air_setpoint_circuit_1",
        "shift_in_auto_mode_circuit_1",
        "target_temperature_circuit_2",
        "room_air_setpoint_circuit_2",
        "shift_in_auto_mode_circuit_2",
        "dhw_target_temperature",
    )
    assert pump.switches.writable_datapoints == (
        "heating_circuit",
        "dhw",
        "silent_mode",
        "dhw_disinfection",
        "emergency_stop",
        "trigger_emergency_operation",
    )
    assert pump.sensors.writable_datapoints == ()
    assert pump.states.writable_datapoints == ()
