"""Program 11: fly a short zigzag course using alternating turns."""

NAME = "Zigzag Flight"
DESCRIPTION = "Flies a gentle four-leg zigzag, then lands."


def run(drone, log, should_stop) -> None:
    takeoff_attempted = False
    try:
        log("Taking off...")
        takeoff_attempted = True
        drone.takeoff()
        turns = (45, -90, 90, -45)
        for leg, turn in enumerate(turns, start=1):
            if should_stop():
                return
            log(f"Zigzag leg {leg}...")
            drone.move_forward(35, "cm", 0.5)
            if turn > 0:
                drone.turn_right(turn)
            else:
                drone.turn_left(abs(turn))
    finally:
        if takeoff_attempted and not should_stop():
            log("Landing...")
            drone.land()
