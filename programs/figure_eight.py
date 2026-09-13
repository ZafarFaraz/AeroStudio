"""Program 16: trace two connected loops in opposite directions."""

NAME = "Figure Eight"
DESCRIPTION = "Traces two small opposite loops to form a figure eight."


def run(drone, log, should_stop) -> None:
    takeoff_attempted = False
    try:
        log("Taking off...")
        takeoff_attempted = True
        drone.takeoff()
        for loop_name, turn in (("Right loop", drone.turn_right), ("Left loop", drone.turn_left)):
            log(loop_name)
            for _ in range(4):
                if should_stop():
                    return
                drone.move_forward(35, "cm", 0.45)
                turn(90)
    finally:
        if takeoff_attempted and not should_stop():
            log("Landing...")
            drone.land()
