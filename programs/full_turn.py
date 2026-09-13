"""Program 8: take off and rotate one complete turn in place."""

NAME = "360° Turn"
DESCRIPTION = "Takes off, turns right 360 degrees, and lands."


def run(drone, log, should_stop) -> None:
    takeoff_attempted = False
    try:
        log("Taking off...")
        takeoff_attempted = True
        drone.takeoff()
        if should_stop():
            return
        log("Turning 360 degrees...")
        drone.turn_right(360)
    finally:
        if takeoff_attempted and not should_stop():
            log("Landing...")
            drone.land()
