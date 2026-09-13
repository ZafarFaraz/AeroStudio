"""Safety cleanup tests shared by every ready-made flight program."""

from __future__ import annotations

import unittest

from programs import ADVANCED_PROGRAMS, SIMPLE_PROGRAMS


class IncompleteTakeoffDrone:
    """Simulate lift beginning just before takeoff telemetry fails."""

    def __init__(self) -> None:
        self.land_calls = 0

    def takeoff(self) -> None:
        raise RuntimeError("telemetry lost after lift")

    def land(self) -> None:
        self.land_calls += 1

    def set_drone_LED(self, *args: object) -> None:
        pass


class ProgramSafetyTests(unittest.TestCase):
    def test_every_flight_program_lands_after_incomplete_takeoff(self) -> None:
        for program in SIMPLE_PROGRAMS + ADVANCED_PROGRAMS:
            with self.subTest(program=program.name):
                drone = IncompleteTakeoffDrone()
                with self.assertRaisesRegex(RuntimeError, "telemetry lost"):
                    program.run(drone, lambda message: None, lambda: False)
                self.assertEqual(drone.land_calls, 1)


if __name__ == "__main__":
    unittest.main()
