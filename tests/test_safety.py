"""Tests for the shared directional obstacle protection."""

from __future__ import annotations

import unittest

from safety import ObstacleDetected, SafeDrone, SafetySensorError


class FakeDrone:
    def __init__(self, distances: list[float]) -> None:
        self.distances = iter(distances)
        self.actions: list[str] = []

    def get_front_range(self, units: str) -> float:
        return next(self.distances)

    def hover(self, seconds: float) -> None:
        self.actions.append("brake")

    def move_forward(self, distance: float, units: str, speed: float) -> None:
        self.actions.append("forward")

    def move_backward(self, distance: float, units: str, speed: float) -> None:
        self.actions.append("backward")

    def move_left(self, distance: float, units: str, speed: float) -> None:
        self.actions.append("left")

    def move_right(self, distance: float, units: str, speed: float) -> None:
        self.actions.append("right")

    def turn_left(self, degrees: int) -> None:
        self.actions.append(f"turn-left-{degrees}")

    def turn_right(self, degrees: int) -> None:
        self.actions.append(f"turn-right-{degrees}")

    def flip(self, direction: str) -> None:
        self.actions.append(f"flip-{direction}")


class SafeDroneTests(unittest.TestCase):
    def test_forward_motion_runs_when_destination_and_buffer_are_clear(self) -> None:
        drone = FakeDrone([100])
        SafeDrone(drone, lambda message: None).move_forward(50)
        self.assertEqual(drone.actions, ["forward"])

    def test_forward_motion_brakes_before_an_obstacle(self) -> None:
        drone = FakeDrone([70])
        with self.assertRaisesRegex(ObstacleDetected, "70 cm away"):
            SafeDrone(drone, lambda message: None).move_forward(50)
        self.assertEqual(drone.actions, ["brake"])

    def test_left_motion_strafes_without_turning(self) -> None:
        drone = FakeDrone([])
        SafeDrone(drone, lambda message: None).move_left(30)
        self.assertEqual(drone.actions, ["left"])

    def test_backward_and_right_motion_do_not_turn_for_sensor_checks(self) -> None:
        drone = FakeDrone([])
        safe_drone = SafeDrone(drone, lambda message: None)
        safe_drone.move_backward(30)
        safe_drone.move_right(30)
        self.assertEqual(drone.actions, ["backward", "right"])

    def test_invalid_sensor_reading_fails_closed(self) -> None:
        drone = FakeDrone([0])
        with self.assertRaises(SafetySensorError):
            SafeDrone(drone, lambda message: None).move_forward(30)
        self.assertEqual(drone.actions, [])

    def test_backward_flip_does_not_rotate_for_a_sensor_check(self) -> None:
        drone = FakeDrone([])
        SafeDrone(drone, lambda message: None).flip("back")
        self.assertEqual(drone.actions, ["flip-back"])

    def test_forward_flip_checks_forward_clearance(self) -> None:
        drone = FakeDrone([80])
        with self.assertRaises(ObstacleDetected):
            SafeDrone(drone, lambda message: None).flip("front")
        self.assertEqual(drone.actions, ["brake"])


if __name__ == "__main__":
    unittest.main()
