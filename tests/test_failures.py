"""One sub-system failing does not take the rest of the poll with it."""

from __future__ import annotations

import pytest
from modbus_connection import (
    IllegalDataAddressError,
    IllegalFunctionError,
    ModbusConnectionError,
    ModbusTimeoutError,
)
from modbus_connection.mock import MockModbusConnection, MockModbusUnit

from lg_heatpump_modbus import LgHeatPump


async def test_one_refused_block_is_reported_not_raised(
    pump: LgHeatPump, unit: MockModbusUnit
) -> None:
    unit.fail_read(0, IllegalDataAddressError(), register_type="holding")

    report = await pump.async_update()

    assert not report.ok
    assert report.updated == ["sensors", "states", "switches"]
    assert set(report.failed) == {"controls"}
    assert pump.sensors.outdoor_temperature == -4.2  # the rest still refreshed


async def test_a_failed_component_keeps_its_previous_values(
    pump: LgHeatPump, unit: MockModbusUnit
) -> None:
    await pump.async_update()
    unit.fail_read(0, IllegalDataAddressError(), register_type="holding")

    await pump.async_update()

    assert pump.controls.dhw_target_temperature == 50.0


async def test_a_dead_link_stops_the_poll_immediately(
    pump: LgHeatPump, unit: MockModbusUnit
) -> None:
    unit.fail_requests(ModbusConnectionError())

    with pytest.raises(ModbusConnectionError):
        await pump.async_update()


async def test_a_device_that_answers_nothing_raises(
    pump: LgHeatPump, unit: MockModbusUnit
) -> None:
    unit.fail_requests(ModbusTimeoutError())

    with pytest.raises(ModbusTimeoutError):
        await pump.async_update()


async def test_a_later_timeout_is_reported(
    pump: LgHeatPump, unit: MockModbusUnit
) -> None:
    unit.fail_read(0, ModbusTimeoutError(), register_type="holding")

    report = await pump.async_update()

    assert set(report.failed) == {"controls"}
    assert "sensors" in report.updated


async def test_a_unit_refusing_identity_still_sets_up(
    pump: LgHeatPump, unit: MockModbusUnit
) -> None:
    unit.fail_read(9998, IllegalDataAddressError(), register_type="input")

    report = await pump.async_update()

    assert report.ok
    assert pump.info.product_info is None
    assert pump.sensors.outdoor_temperature == -4.2


async def test_an_unsupported_function_on_identity_still_sets_up(
    pump: LgHeatPump, unit: MockModbusUnit
) -> None:
    unit.fail_read(9998, IllegalFunctionError(), register_type="input")

    report = await pump.async_update()

    assert report.ok


async def test_setup_is_retried_until_it_runs(
    pump: LgHeatPump, unit: MockModbusUnit
) -> None:
    unit.fail_requests(ModbusConnectionError())
    with pytest.raises(ModbusConnectionError):
        await pump.async_update()

    unit.fail_requests(None)
    report = await pump.async_update()

    assert report.ok
    assert pump.info.product_info == 0x1A2B


async def test_update_listeners_fire_for_refreshed_components(
    pump: LgHeatPump,
) -> None:
    seen: list[str] = []
    pump.sensors.add_update_listener(lambda: seen.append("sensors"))
    pump.controls.add_update_listener(lambda: seen.append("controls"))

    await pump.async_update()

    assert seen == ["sensors", "controls"]


async def test_update_listeners_do_not_fire_for_a_failed_component(
    pump: LgHeatPump, unit: MockModbusUnit
) -> None:
    seen: list[str] = []
    pump.controls.add_update_listener(lambda: seen.append("controls"))
    unit.fail_read(0, IllegalDataAddressError(), register_type="holding")

    await pump.async_update()

    assert seen == []


async def test_a_dropped_link_reconnects_on_the_next_poll(
    mock_modbus_connection: MockModbusConnection,
    pump: LgHeatPump,
) -> None:
    await pump.async_update()
    mock_modbus_connection.simulate_connection_lost()
    assert mock_modbus_connection.connected is False

    report = await pump.async_update()

    assert report.ok
    assert mock_modbus_connection.connected is True
