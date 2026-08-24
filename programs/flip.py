"""Program 9: take off, perform one backward flip, and land."""

NAME = "Backward Flip"
DESCRIPTION = "Takes off, performs one backward flip, then lands. Needs extra space."


def run(drone, log, should_stop) -> None:
    airborne = False
    try:
        log("Taking off...")
        drone.takeoff()
        airborne = True
        if should_stop():
            return
        log("Flipping backward...")
        drone.flip("back")
        if should_stop():
            return
        drone.hover(2)
    finally:
        if airborne and not should_stop():
            log("Landing...")
            drone.land()
