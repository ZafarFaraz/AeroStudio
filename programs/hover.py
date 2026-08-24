"""Program 4: take off, hover briefly, and land."""

NAME = "Takeoff + Hover"
DESCRIPTION = "Takes off, hovers for 3 seconds, then lands."


def run(drone, log, should_stop) -> None:
    airborne = False
    try:
        log("Taking off...")
        drone.takeoff()
        airborne = True
        if should_stop():
            return
        log("Hovering for 3 seconds...")
        drone.hover(3)
    finally:
        if airborne and not should_stop():
            log("Landing...")
            drone.land()
