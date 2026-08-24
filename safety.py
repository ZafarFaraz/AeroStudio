"""Shared obstacle protection for every dashboard-controlled flight."""

from __future__ import annotations

from typing import Any, Callable


Log = Callable[[str], None]

SAFETY_BUFFER_CM = 35.0
MIN_CLEARANCE_CM = 55.0
FLIP_CLEARANCE_CM = 120.0


class ObstacleDetected(RuntimeError):
    """Raised after the drone has braked because its flight path is blocked."""

    def __init__(self, distance_cm: float, required_cm: float) -> None:
        self.distance_cm = distance_cm
        self.required_cm = required_cm
        super().__init__(
            f"Obstacle detected {distance_cm:.0f} cm away. "
            "The drone braked and the flight was stopped."
        )


class SafetySensorError(RuntimeError):
    """Raised when a safe path cannot be confirmed."""


def _to_centimetres(distance: float, units: str) -> float:
    conversions = {
        "cm": 1.0,
        "m": 100.0,
        "in": 2.54,
        "ft": 30.48,
    }
    try:
        return float(distance) * conversions[units]
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError(f"Unsupported distance: {distance!r} {units}") from error


class SafeDrone:
    """Proxy a CoDrone while protecting motion its front sensor can observe.

    Left, right, and backward commands retain their exact movement semantics.
    The drone is never rotated behind a student's back just to take a reading.
    """

    def __init__(self, drone: Any, log: Log) -> None:
        self._drone = drone
        self._log = log

    def __getattr__(self, name: str) -> Any:
        return getattr(self._drone, name)

    def _front_distance(self) -> float:
        try:
            distance = float(self._drone.get_front_range("cm"))
        except Exception as error:
            raise SafetySensorError(
                "The front safety sensor could not be read, so the drone did not move."
            ) from error
        if distance <= 0:
            raise SafetySensorError(
                "The front safety sensor did not return a usable distance, "
                "so the drone did not move."
            )
        return distance

    def _brake(self) -> None:
        try:
            self._drone.hover(0.5)
        except Exception:
            # The caller still raises and attempts a safety landing.
            pass

    def _check_path(self, travel_cm: float) -> None:
        required = max(MIN_CLEARANCE_CM, travel_cm + SAFETY_BUFFER_CM)
        distance = self._front_distance()
        self._log(f"Safety check: {distance:.0f} cm clear ahead")
        if distance <= required:
            self._brake()
            raise ObstacleDetected(distance, required)

    def move_forward(self, distance: float, units: str = "cm", speed: float = 0.5) -> Any:
        self._check_path(_to_centimetres(distance, units))
        return self._drone.move_forward(distance, units, speed)

    def move_backward(self, distance: float, units: str = "cm", speed: float = 0.5) -> Any:
        return self._drone.move_backward(distance, units, speed)

    def move_left(self, distance: float, units: str = "cm", speed: float = 0.5) -> Any:
        return self._drone.move_left(distance, units, speed)

    def move_right(self, distance: float, units: str = "cm", speed: float = 0.5) -> Any:
        return self._drone.move_right(distance, units, speed)

    def flip(self, direction: str = "back") -> Any:
        if direction == "front":
            self._check_path(FLIP_CLEARANCE_CM - SAFETY_BUFFER_CM)
        return self._drone.flip(direction)


def protect(drone: Any, log: Log) -> SafeDrone:
    """Return a safety proxy, avoiding accidental proxy nesting."""
    if isinstance(drone, SafeDrone):
        return drone
    return SafeDrone(drone, log)
