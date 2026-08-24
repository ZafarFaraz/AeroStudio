"""Command blocks available in the dashboard's visual program builder."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable


Log = Callable[[str], None]
ShouldStop = Callable[[], bool]
Executor = Callable[[Any, Log, ShouldStop], None]
Condition = Callable[[Any, Log], bool]


@dataclass(frozen=True)
class BlockAction:
    """One visual block and the drone command it executes."""

    name: str
    category: str
    color: str
    execute: Executor | None = None
    kind: str = "command"
    python_code: str = ""
    condition: Condition | None = None
    repeat_count: int = 0
    max_iterations: int = 0


def _simple(action: Callable[[Any], object]) -> Executor:
    def execute(drone: Any, log: Log, should_stop: ShouldStop) -> None:
        action(drone)

    return execute


def _wait(drone: Any, log: Log, should_stop: ShouldStop) -> None:
    for _ in range(10):
        if should_stop():
            return
        time.sleep(0.1)


def _battery(drone: Any, log: Log, should_stop: ShouldStop) -> None:
    log(f"Battery: {drone.get_battery()}%")


def _front_sensor(drone: Any, log: Log, should_stop: ShouldStop) -> None:
    log(f"Front distance: {drone.get_front_range('cm')} cm")


def _front_is_clear(drone: Any, log: Log) -> bool:
    distance = drone.get_front_range("cm")
    is_clear = distance > 80
    log(f"Condition: front distance {distance} cm → {str(is_clear).lower()}")
    return is_clear


def _flip(direction: str) -> Executor:
    def execute(drone: Any, log: Log, should_stop: ShouldStop) -> None:
        battery = drone.get_battery()
        if battery < 50:
            raise RuntimeError(f"Flip needs at least 50% battery; current level is {battery}%")
        if should_stop():
            return
        log(f"Flipping {direction}...")
        drone.flip(direction)
        if not should_stop():
            drone.hover(1)

    return execute


def _polygon(name: str, sides: int, distance: int, turn: int) -> Executor:
    def execute(drone: Any, log: Log, should_stop: ShouldStop) -> None:
        for side in range(1, sides + 1):
            if should_stop():
                return
            log(f"{name}: side {side} of {sides}")
            drone.move_forward(distance, "cm", 0.45)
            if should_stop():
                return
            drone.turn_right(turn)

    return execute


def _zigzag(drone: Any, log: Log, should_stop: ShouldStop) -> None:
    for leg, turn in enumerate((45, -90, 90, -45), start=1):
        if should_stop():
            return
        log(f"Zigzag: leg {leg} of 4")
        drone.move_forward(30, "cm", 0.45)
        if should_stop():
            return
        if turn > 0:
            drone.turn_right(turn)
        else:
            drone.turn_left(abs(turn))


def _figure_eight(drone: Any, log: Log, should_stop: ShouldStop) -> None:
    for loop_name, turn in (("right", drone.turn_right), ("left", drone.turn_left)):
        for side in range(1, 5):
            if should_stop():
                return
            log(f"Figure eight: {loop_name} loop {side} of 4")
            drone.move_forward(30, "cm", 0.45)
            if should_stop():
                return
            turn(90)


def _circle(drone: Any, log: Log, should_stop: ShouldStop) -> None:
    for segment in range(1, 9):
        if should_stop():
            return
        log(f"Circle: segment {segment} of 8")
        drone.move_forward(22, "cm", 0.4)
        if should_stop():
            return
        drone.turn_right(45)


def _rainbow_square(drone: Any, log: Log, should_stop: ShouldStop) -> None:
    colors = (
        ("red", 255, 0, 0),
        ("green", 0, 255, 0),
        ("blue", 0, 80, 255),
        ("purple", 170, 0, 255),
    )
    for side, (name, red, green, blue) in enumerate(colors, start=1):
        if should_stop():
            return
        log(f"Rainbow square: side {side} is {name}")
        drone.set_drone_LED(red, green, blue, 100)
        drone.move_forward(40, "cm", 0.45)
        if should_stop():
            return
        drone.turn_right(90)
    drone.set_drone_LED(255, 255, 255, 100)


BLOCK_ACTIONS = (
    BlockAction("Take off", "Flight", "#2563eb", _simple(lambda d: d.takeoff())),
    BlockAction("Land", "Flight", "#2563eb", _simple(lambda d: d.land())),
    BlockAction("Hover 1 second", "Flight", "#2563eb", _simple(lambda d: d.hover(1))),
    BlockAction("Forward 30 cm", "Movement", "#7c3aed", _simple(lambda d: d.move_forward(30, "cm", 0.5))),
    BlockAction("Backward 30 cm", "Movement", "#7c3aed", _simple(lambda d: d.move_backward(30, "cm", 0.5))),
    BlockAction("Left 30 cm", "Movement", "#7c3aed", _simple(lambda d: d.move_left(30, "cm", 0.5))),
    BlockAction("Right 30 cm", "Movement", "#7c3aed", _simple(lambda d: d.move_right(30, "cm", 0.5))),
    BlockAction("Up 30 cm", "Movement", "#7c3aed", _simple(lambda d: d.move_distance(0, 0, 0.3, 0.5))),
    BlockAction("Down 30 cm", "Movement", "#7c3aed", _simple(lambda d: d.move_distance(0, 0, -0.3, 0.5))),
    BlockAction("Turn left 90°", "Movement", "#7c3aed", _simple(lambda d: d.turn_left(90))),
    BlockAction("Turn right 90°", "Movement", "#7c3aed", _simple(lambda d: d.turn_right(90))),
    BlockAction("LED red", "Lights", "#dc2626", _simple(lambda d: d.set_drone_LED(255, 0, 0, 100))),
    BlockAction("LED green", "Lights", "#16a34a", _simple(lambda d: d.set_drone_LED(0, 255, 0, 100))),
    BlockAction("LED blue", "Lights", "#0284c7", _simple(lambda d: d.set_drone_LED(0, 80, 255, 100))),
    BlockAction("LED white", "Lights", "#475569", _simple(lambda d: d.set_drone_LED(255, 255, 255, 100))),
    BlockAction("Wait 1 second", "Utility", "#b45309", _wait),
    BlockAction("Read battery", "Utility", "#b45309", _battery),
    BlockAction("Read front sensor", "Utility", "#b45309", _front_sensor),
    BlockAction(
        "Flip backward",
        "Tricks",
        "#c2410c",
        _flip("back"),
        python_code='drone.flip("back")',
    ),
    BlockAction(
        "Flip forward",
        "Tricks",
        "#c2410c",
        _flip("front"),
        python_code='drone.flip("front")',
    ),
    BlockAction(
        "Flip left",
        "Tricks",
        "#c2410c",
        _flip("left"),
        python_code='drone.flip("left")',
    ),
    BlockAction(
        "Flip right",
        "Tricks",
        "#c2410c",
        _flip("right"),
        python_code='drone.flip("right")',
    ),
    BlockAction(
        "Turn 360°",
        "Tricks",
        "#c2410c",
        _simple(lambda d: d.turn_right(360)),
        python_code="drone.turn_right(360)",
    ),
    BlockAction(
        "Square path",
        "Tricks",
        "#c2410c",
        _polygon("Square", 4, 40, 90),
        python_code="for _ in range(4):",
    ),
    BlockAction(
        "Triangle path",
        "Tricks",
        "#c2410c",
        _polygon("Triangle", 3, 40, 120),
        python_code="for _ in range(3):",
    ),
    BlockAction(
        "Zigzag path",
        "Tricks",
        "#c2410c",
        _zigzag,
        python_code="for turn in zigzag_turns:",
    ),
    BlockAction(
        "Circle path",
        "Tricks",
        "#c2410c",
        _circle,
        python_code="for _ in range(8):",
    ),
    BlockAction(
        "Figure-eight path",
        "Tricks",
        "#c2410c",
        _figure_eight,
        python_code="for direction in (right, left):",
    ),
    BlockAction(
        "Rainbow square",
        "Tricks",
        "#c2410c",
        _rainbow_square,
        python_code="for colour in colours:",
    ),
    BlockAction(
        "If path is clear",
        "Logic",
        "#0f766e",
        kind="if",
        python_code="if front_distance > 80:",
        condition=_front_is_clear,
    ),
    BlockAction(
        "Otherwise",
        "Logic",
        "#0f766e",
        kind="else",
        python_code="else:",
    ),
    BlockAction(
        "End if",
        "Logic",
        "#0f766e",
        kind="end_if",
        python_code="# end if",
    ),
    BlockAction(
        "Repeat 3 times",
        "Logic",
        "#0f766e",
        kind="repeat",
        python_code="for i in range(3):",
        repeat_count=3,
    ),
    BlockAction(
        "End repeat",
        "Logic",
        "#0f766e",
        kind="end_repeat",
        python_code="# end for",
    ),
    BlockAction(
        "While path is clear",
        "Logic",
        "#0f766e",
        kind="while",
        python_code="while front_distance > 80:",
        condition=_front_is_clear,
        max_iterations=5,
    ),
    BlockAction(
        "End while",
        "Logic",
        "#0f766e",
        kind="end_while",
        python_code="# end while",
    ),
)


BLOCKS_BY_KIND = {block.kind: block for block in BLOCK_ACTIONS if block.kind != "command"}
