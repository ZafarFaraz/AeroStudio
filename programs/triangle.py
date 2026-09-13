"""Program 10: fly an equilateral triangle and return near the start."""

NAME = "Fly a Triangle"
DESCRIPTION = "Flies three 50 cm sides with 120° right turns, then lands."


def run(drone, log, should_stop) -> None:
    takeoff_attempted = False
    try:
        log("Taking off...")
        takeoff_attempted = True
        drone.takeoff()
        for side in range(1, 4):
            if should_stop():
                return
            log(f"Triangle side {side}...")
            drone.move_forward(50, "cm", 0.5)
            if should_stop():
                return
            drone.turn_right(120)
    finally:
        if takeoff_attempted and not should_stop():
            log("Landing...")
            drone.land()
