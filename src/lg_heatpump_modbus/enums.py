"""Enumerated register values.

Only codes that the validated register map documents are declared. An
undocumented code decodes to ``None`` rather than being guessed at, so a device
that reports something unexpected is visible instead of silently mislabeled.
"""

from __future__ import annotations

from enum import IntEnum


class OperationMode(IntEnum):
    """Requested operation mode (holding register 0)."""

    # TODO verify
    COOL = 0
    AUTO = 3
    HEAT = 4


class ControlMethod(IntEnum):
    """Which temperature the controller regulates on (holding register 1)."""

    # TODO verify
    WATER_OUTLET = 0
    WATER_INLET = 1
    ROOM_AIR = 2


class EnergyState(IntEnum):
    """Smart-grid energy state (input register 11 / holding register 9)."""

    # TODO verify
    NOT_USED = 0                  # tested by G-nn-r
    FORCED_OFF = 1                # not tested
    NORMAL = 2                    # not tested
    ON_RECOMMENDATION = 3         # not tested
    ON_COMMAND = 4                # not tested
    ON_COMMAND_STEP_2 = 5         # not tested
    ON_RECOMMENDATION_STEP_1 = 6  # not tested
    ENERGY_SAVING = 7             # not tested
    SUPER_ENERGY_SAVING = 8       # not tested


class Circuit(IntEnum):
    """The two water circuits a heat pump can drive."""

    # TODO verify
    CIRCUIT_1 = 1
    CIRCUIT_2 = 2
