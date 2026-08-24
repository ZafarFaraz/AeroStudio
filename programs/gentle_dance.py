"""Program 12: combine small movements, turns, and coloured LEDs."""

NAME = "Gentle Dance"
DESCRIPTION = "Performs small side moves and turns while changing LED colours."


def run(drone, log, should_stop) -> None:
    airborne = False
    try:
        log("Taking off...")
        drone.takeoff()
        airborne = True
        moves = (
            ("Blue left", (0, 80, 255), drone.move_left),
            ("Pink right", (255, 20, 120), drone.move_right),
            ("Green left", (20, 255, 80), drone.move_left),
            ("Gold right", (255, 160, 0), drone.move_right),
        )
        for label, color, move in moves:
            if should_stop():
                return
            log(label)
            drone.set_drone_LED(*color, 100)
            move(25, "cm", 0.4)
            drone.turn_right(45)
    finally:
        if airborne and not should_stop():
            drone.set_drone_LED(255, 255, 255, 100)
            log("Landing...")
            drone.land()
