"""Program 18: fly a square with a different LED colour on each side."""

NAME = "Rainbow Square"
DESCRIPTION = "Flies a colourful square, changing LED colour on every side."


def run(drone, log, should_stop) -> None:
    takeoff_attempted = False
    colors = (
        ("Red", 255, 0, 0),
        ("Green", 0, 255, 0),
        ("Blue", 0, 80, 255),
        ("Purple", 170, 0, 255),
    )
    try:
        log("Taking off...")
        takeoff_attempted = True
        drone.takeoff()
        for side, (name, red, green, blue) in enumerate(colors, start=1):
            if should_stop():
                return
            log(f"Side {side}: {name}")
            drone.set_drone_LED(red, green, blue, 100)
            drone.move_forward(45, "cm", 0.45)
            drone.turn_right(90)
    finally:
        if takeoff_attempted and not should_stop():
            try:
                drone.set_drone_LED(255, 255, 255, 100)
            finally:
                log("Landing...")
                drone.land()
