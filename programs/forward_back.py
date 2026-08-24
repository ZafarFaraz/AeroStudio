"""Program 5: fly forward and then return backward to the start area."""

NAME = "Forward + Back"
DESCRIPTION = "Takes off, flies forward 50 cm, returns 50 cm, and lands."


def run(drone, log, should_stop) -> None:
    airborne = False
    try:
        log("Taking off...")
        drone.takeoff()
        airborne = True
        if should_stop():
            return
        log("Moving forward...")
        drone.move_forward(50, "cm", 0.5)
        if should_stop():
            return
        log("Moving back...")
        drone.move_backward(50, "cm", 0.5)
    finally:
        if airborne and not should_stop():
            log("Landing...")
            drone.land()
