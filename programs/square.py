"""Program 7: trace a 50 cm square using four forward moves and turns."""

NAME = "Fly a Square"
DESCRIPTION = "Flies four 50 cm sides with right turns, then lands."


def run(drone, log, should_stop) -> None:
    takeoff_attempted = False
    try:
        log("Taking off...")
        takeoff_attempted = True
        drone.takeoff()
        for side in range(1, 5):
            if should_stop():
                return
            log(f"Square side {side}...")
            drone.move_forward(50, "cm", 0.5)
            if should_stop():
                return
            drone.turn_right(90)
    finally:
        if takeoff_attempted and not should_stop():
            log("Landing...")
            drone.land()
