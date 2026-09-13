"""Small, testable helpers for the CoDrone connection lifecycle."""

from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Any, Callable


class DroneConnectionError(RuntimeError):
    """Raised when the controller and drone are not both ready to use."""


def connect_ready_drone(
    drone_factory: Callable[[], Any],
    ready_flight_state: object,
) -> Any:
    """Create and pair a drone, closing partial connections on every failure."""
    drone: Any | None = None
    try:
        drone = drone_factory()
        if drone.pair() is False:
            raise DroneConnectionError("The controller rejected the connection.")
        if not drone.isOpen():
            raise DroneConnectionError("The controller serial port is not open.")
        if drone.get_flight_state() != ready_flight_state:
            raise DroneConnectionError("The drone is not paired with the controller.")
        return drone
    except (Exception, SystemExit) as error:
        if drone is not None:
            try:
                drone.close()
            except (Exception, SystemExit):
                pass
        if isinstance(error, DroneConnectionError):
            raise
        raise DroneConnectionError("Could not connect to the drone.") from error


@dataclass(frozen=True)
class EmergencyStopResult:
    """Outcome of a bounded emergency-stop attempt."""

    completed: bool
    error: BaseException | None = None


def send_emergency_stop(
    drone: Any,
    *,
    timeout: float = 1.0,
) -> EmergencyStopResult:
    """Send an emergency stop and wait briefly before callers close the port."""
    finished = threading.Event()
    errors: list[BaseException] = []

    def work() -> None:
        try:
            drone.emergency_stop()
        except (Exception, SystemExit) as error:
            errors.append(error)
        finally:
            finished.set()

    threading.Thread(target=work, daemon=True).start()
    completed = finished.wait(timeout)
    return EmergencyStopResult(completed, errors[0] if errors else None)
