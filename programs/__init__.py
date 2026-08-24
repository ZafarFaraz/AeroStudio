"""Registry of the nine programs displayed by the dashboard."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from . import (
    battery_check,
    color_check,
    flip,
    figure_eight,
    forward_back,
    full_turn,
    gentle_dance,
    hover,
    led_colors,
    obstacle_scout,
    orientation_check,
    rainbow_square,
    sensor_check,
    side_to_side,
    square,
    temperature_check,
    triangle,
    zigzag,
)

Log = Callable[[str], None]
ShouldStop = Callable[[], bool]
Runner = Callable[[Any, Log, ShouldStop], None]


@dataclass(frozen=True)
class Program:
    name: str
    description: str
    icon_name: str
    run: Runner


def _programs(*modules: Any) -> tuple[Program, ...]:
    """Convert program modules into immutable dashboard entries."""
    return tuple(
        Program(
            module.NAME,
            module.DESCRIPTION,
            module.__name__.rsplit(".", 1)[-1],
            module.run,
        )
        for module in modules
    )


BASIC_PROGRAMS = _programs(
    battery_check,
    sensor_check,
    led_colors,
    temperature_check,
    orientation_check,
    color_check,
)

SIMPLE_PROGRAMS = _programs(
    hover,
    forward_back,
    side_to_side,
    triangle,
    zigzag,
    gentle_dance,
)

ADVANCED_PROGRAMS = _programs(
    square,
    full_turn,
    flip,
    figure_eight,
    obstacle_scout,
    rainbow_square,
)

PROGRAMS = BASIC_PROGRAMS + SIMPLE_PROGRAMS + ADVANCED_PROGRAMS
