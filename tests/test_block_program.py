"""Behavior tests for student-facing Block Builder control flow."""

from __future__ import annotations

import unittest

from block_actions import BLOCK_ACTIONS
from block_program import (
    BlockProgramError,
    ExecutionResult,
    execute_program,
    parse_program,
    sequence_indents,
    validate_flight_safety,
)


BLOCK = {block.name: block for block in BLOCK_ACTIONS}


class FakeDrone:
    def __init__(
        self, distances: list[int] | None = None, battery: int = 80
    ) -> None:
        self.distances = iter(distances or [])
        self.battery = battery
        self.actions: list[str] = []

    def get_front_range(self, unit: str = "cm") -> int:
        return next(self.distances)

    def takeoff(self) -> None:
        self.actions.append("takeoff")

    def land(self) -> None:
        self.actions.append("land")

    def move_forward(self, *args: object) -> None:
        self.actions.append("forward")

    def move_backward(self, *args: object) -> None:
        self.actions.append("backward")

    def get_battery(self) -> int:
        return self.battery

    def hover(self, seconds: int) -> None:
        self.actions.append("hover")

    def flip(self, direction: str) -> None:
        self.actions.append(f"flip-{direction}")

    def turn_right(self, degrees: int) -> None:
        self.actions.append(f"right-{degrees}")

    def turn_left(self, degrees: int) -> None:
        self.actions.append(f"left-{degrees}")

    def set_drone_LED(self, *args: object) -> None:
        self.actions.append("led")


class BlockProgramTests(unittest.TestCase):
    def test_if_else_chooses_true_branch(self) -> None:
        sequence = (
            BLOCK["Take off"],
            BLOCK["If path is clear"],
            BLOCK["Forward 30 cm"],
            BLOCK["Otherwise"],
            BLOCK["Backward 30 cm"],
            BLOCK["End if"],
            BLOCK["Land"],
        )
        nodes = parse_program(sequence)
        self.assertEqual(validate_flight_safety(nodes), {False})
        drone = FakeDrone([120])
        result = execute_program(nodes, drone, lambda message: None, lambda: False)
        self.assertEqual(drone.actions, ["takeoff", "forward", "land"])
        self.assertFalse(result.airborne)

    def test_repeat_behaves_like_three_iteration_for_loop(self) -> None:
        sequence = (
            BLOCK["Take off"],
            BLOCK["Repeat 3 times"],
            BLOCK["Forward 30 cm"],
            BLOCK["End repeat"],
            BLOCK["Land"],
        )
        drone = FakeDrone()
        execute_program(
            parse_program(sequence), drone, lambda message: None, lambda: False
        )
        self.assertEqual(drone.actions.count("forward"), 3)

    def test_while_rechecks_condition_and_is_bounded(self) -> None:
        sequence = (
            BLOCK["Take off"],
            BLOCK["While path is clear"],
            BLOCK["Forward 30 cm"],
            BLOCK["End while"],
            BLOCK["Land"],
        )
        drone = FakeDrone([120, 110, 40])
        execute_program(
            parse_program(sequence), drone, lambda message: None, lambda: False
        )
        self.assertEqual(drone.actions, ["takeoff", "forward", "forward", "land"])

    def test_while_stops_after_five_true_checks(self) -> None:
        sequence = (
            BLOCK["Take off"],
            BLOCK["While path is clear"],
            BLOCK["Forward 30 cm"],
            BLOCK["End while"],
            BLOCK["Land"],
        )
        drone = FakeDrone([120] * 5)
        execute_program(
            parse_program(sequence), drone, lambda message: None, lambda: False
        )
        self.assertEqual(drone.actions.count("forward"), 5)

    def test_unsafe_conditional_flight_path_is_rejected(self) -> None:
        sequence = (
            BLOCK["If path is clear"],
            BLOCK["Take off"],
            BLOCK["End if"],
            BLOCK["Forward 30 cm"],
        )
        with self.assertRaises(BlockProgramError):
            validate_flight_safety(parse_program(sequence))

    def test_missing_end_marker_is_rejected(self) -> None:
        with self.assertRaisesRegex(BlockProgramError, "needs End repeat"):
            parse_program((BLOCK["Repeat 3 times"], BLOCK["Read battery"]))

    def test_nested_sequence_has_python_style_indentation(self) -> None:
        sequence = (
            BLOCK["If path is clear"],
            BLOCK["Repeat 3 times"],
            BLOCK["Read battery"],
            BLOCK["End repeat"],
            BLOCK["End if"],
        )
        self.assertEqual(sequence_indents(sequence), [0, 1, 2, 1, 0])

    def test_execution_result_survives_command_error_for_auto_landing(self) -> None:
        sequence = (BLOCK["Take off"], BLOCK["Forward 30 cm"])
        drone = FakeDrone()

        def broken_forward(*args: object) -> None:
            raise RuntimeError("motor error")

        drone.move_forward = broken_forward  # type: ignore[method-assign]
        result = ExecutionResult()
        with self.assertRaisesRegex(RuntimeError, "motor error"):
            execute_program(
                parse_program(sequence),
                drone,
                lambda message: None,
                lambda: False,
                result,
            )
        self.assertTrue(result.airborne)

    def test_trick_requires_takeoff(self) -> None:
        with self.assertRaisesRegex(BlockProgramError, "movement needs Take off"):
            validate_flight_safety(parse_program((BLOCK["Flip backward"],)))

    def test_backward_flip_runs_when_battery_is_high_enough(self) -> None:
        sequence = (
            BLOCK["Take off"],
            BLOCK["Flip backward"],
            BLOCK["Land"],
        )
        drone = FakeDrone(battery=80)
        execute_program(
            parse_program(sequence), drone, lambda message: None, lambda: False
        )
        self.assertEqual(
            drone.actions, ["takeoff", "flip-back", "hover", "land"]
        )

    def test_flip_rejects_low_battery_and_preserves_airborne_state(self) -> None:
        sequence = (BLOCK["Take off"], BLOCK["Flip backward"])
        drone = FakeDrone(battery=40)
        result = ExecutionResult()
        with self.assertRaisesRegex(RuntimeError, "at least 50% battery"):
            execute_program(
                parse_program(sequence),
                drone,
                lambda message: None,
                lambda: False,
                result,
            )
        self.assertTrue(result.airborne)

    def test_square_path_flies_four_sides(self) -> None:
        sequence = (
            BLOCK["Take off"],
            BLOCK["Square path"],
            BLOCK["Land"],
        )
        drone = FakeDrone()
        execute_program(
            parse_program(sequence), drone, lambda message: None, lambda: False
        )
        self.assertEqual(drone.actions.count("forward"), 4)
        self.assertEqual(drone.actions.count("right-90"), 4)


if __name__ == "__main__":
    unittest.main()
