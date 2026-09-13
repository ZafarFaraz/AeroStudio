"""Tests for controller connection and shutdown lifecycle helpers."""

from __future__ import annotations

import threading
import unittest

from drone_runtime import (
    DroneConnectionError,
    connect_ready_drone,
    send_emergency_stop,
)


class FakeDrone:
    def __init__(
        self,
        *,
        pair_result: bool = True,
        port_open: bool = True,
        flight_state: str = "ready",
        pair_error: BaseException | None = None,
    ) -> None:
        self.pair_result = pair_result
        self.port_open = port_open
        self.flight_state = flight_state
        self.pair_error = pair_error
        self.closed = False

    def pair(self) -> bool:
        if self.pair_error is not None:
            raise self.pair_error
        return self.pair_result

    def isOpen(self) -> bool:
        return self.port_open

    def get_flight_state(self) -> str:
        return self.flight_state

    def close(self) -> None:
        self.closed = True


class DroneRuntimeTests(unittest.TestCase):
    def test_ready_drone_is_returned_without_closing(self) -> None:
        drone = FakeDrone()
        self.assertIs(connect_ready_drone(lambda: drone, "ready"), drone)
        self.assertFalse(drone.closed)

    def test_sdk_system_exit_is_converted_and_partial_connection_is_closed(self) -> None:
        drone = FakeDrone(pair_error=SystemExit())
        with self.assertRaises(DroneConnectionError):
            connect_ready_drone(lambda: drone, "ready")
        self.assertTrue(drone.closed)

    def test_controller_without_ready_drone_is_rejected_and_closed(self) -> None:
        drone = FakeDrone(flight_state="none")
        with self.assertRaisesRegex(DroneConnectionError, "not paired"):
            connect_ready_drone(lambda: drone, "ready")
        self.assertTrue(drone.closed)

    def test_emergency_stop_completes_before_returning(self) -> None:
        stopped = threading.Event()

        class StoppableDrone:
            def emergency_stop(self) -> None:
                stopped.set()

        result = send_emergency_stop(StoppableDrone())
        self.assertTrue(result.completed)
        self.assertIsNone(result.error)
        self.assertTrue(stopped.is_set())

    def test_emergency_stop_timeout_is_bounded(self) -> None:
        release = threading.Event()

        class SlowDrone:
            def emergency_stop(self) -> None:
                release.wait(2)

        result = send_emergency_stop(SlowDrone(), timeout=0.01)
        release.set()
        self.assertFalse(result.completed)


if __name__ == "__main__":
    unittest.main()
