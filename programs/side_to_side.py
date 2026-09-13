"""Program 6: fly left and right before landing near the start area."""

NAME = "Side to Side"
DESCRIPTION = "Takes off, moves left 40 cm, right 40 cm, and lands."


def run(drone, log, should_stop) -> None:
    takeoff_attempted = False
    try:
        log("Taking off...")
        takeoff_attempted = True
        drone.takeoff()
        if should_stop():
            return
        log("Moving left...")
        drone.move_left(40, "cm", 0.5)
        if should_stop():
            return
        log("Moving right...")
        drone.move_right(40, "cm", 0.5)
    finally:
        if takeoff_attempted and not should_stop():
            log("Landing...")
            drone.land()
