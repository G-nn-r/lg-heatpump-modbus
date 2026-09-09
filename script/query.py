#!/usr/bin/env python3

"""Query an LG heat pump over Modbus and print every value.

Connects over Modbus TCP (a network gateway) or a serial/USB port, reads the
whole heat pump once, and dumps every sub-system's values to the terminal.
Handy for checking a real installation without any application around it.

The library itself only needs the connection protocol; this script selects a
concrete backend, so install the ``cli`` extra first::

    pip install "lg-heatpump-modbus[cli]"
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import time

from modbus_connection import ModbusError
from modbus_connection.cli_helper import (
    CountingUnit,
    add_connection_args,
    connect_from_args,
    print_component,
)

from lg_heatpump_modbus import MODELS, LgHeatPump

# (label, attribute name on LgHeatPump) — the order sections are printed in.
SECTIONS: list[tuple[str, str]] = [
    ("Device", "info"),
    ("Measurements", "sensors"),
    ("Status", "states"),
    ("Settings", "controls"),
    ("Switches", "switches"),
]

DEFAULT_UNIT_ID = 1


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse the connection arguments plus the unit id and model."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    add_connection_args(parser)
    # The unit id is not part of connecting — it varies per device and per tool
    # — so it is added alongside the connection arguments rather than by them.
    parser.add_argument(
        "--unit",
        type=int,
        default=DEFAULT_UNIT_ID,
        help=f"Modbus unit/station address (default: {DEFAULT_UNIT_ID})",
    )
    parser.add_argument(
        "--model",
        choices=sorted(MODELS),
        default="therma_v",
        help="Device model deciding which datapoints are read (default: therma_v)",
    )
    return parser.parse_args(argv)


def _print(pump: LgHeatPump) -> None:
    """Print every sub-system of the heat pump."""
    for label, attribute in SECTIONS:
        print()
        print_component(getattr(pump, attribute), title=label)


def _print_derived(pump: LgHeatPump) -> None:
    """Print the values the library derives from several registers."""
    print()
    print("Derived")
    print(f"  compressor speed          {_fmt(pump.sensors.compressor_speed)} rpm")
    print(
        "  water temperature spread  "
        f"{_fmt(pump.sensors.water_temperature_difference)} K"
    )
    print(f"  backup heater steps       {_fmt(pump.states.backup_heater_steps)}")


def _fmt(value: object) -> str:
    """Format a possibly-absent value for the terminal."""
    return "-" if value is None else str(value)


async def _run(args: argparse.Namespace) -> int:
    """Connect, read the heat pump once, print it and report the read count."""
    try:
        connection = await connect_from_args(args)
    except ModbusError as err:
        print(f"Could not connect: {err}", file=sys.stderr)
        return 1

    counting = CountingUnit(connection.for_unit(args.unit))
    try:
        pump = LgHeatPump(counting, model=args.model)
        start = time.monotonic()
        report = await pump.async_update()
        elapsed = time.monotonic() - start
    except ModbusError as err:
        print(f"Error reading the heat pump: {err}", file=sys.stderr)
        return 1
    finally:
        await connection.close()

    _print(pump)
    _print_derived(pump)
    for name, error in report.failed.items():
        print(f"\n{name} did not answer: {error}", file=sys.stderr)
    print(f"\nQueried in {elapsed * 1000:.0f} ms ({counting.reads} Modbus reads)")
    return 0 if report.ok else 1


def main() -> int:
    """Run the query script."""
    return asyncio.run(_run(_parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
