"""Program 4: take off, hover briefly, and land."""

NAME = "Takeoff + Hover"
DESCRIPTION = "Takes off, hovers for 3 seconds, then lands."


def run(drone, log, should_stop) -> None:
    takeoff_attempted = False
    try:
        log("Taking off...")
        takeoff_attempted = True
        drone.takeoff()
        if should_stop():
            return
        log("Hovering for 3 seconds...")
        drone.hover(3)
    finally:
        if takeoff_attempted and not should_stop():
            log("Landing...")
            drone.land()
