"""Program 17: make one flight decision using the front distance sensor."""

NAME = "Obstacle Scout"
DESCRIPTION = "Checks ahead, approaches open space or backs away from an obstacle."


def run(drone, log, should_stop) -> None:
    airborne = False
    try:
        log("Taking off...")
        drone.takeoff()
        airborne = True
        if should_stop():
            return
        distance = drone.get_front_range("cm")
        log(f"Front distance: {distance} cm")
        if distance > 100:
            log("Path is clear. Moving forward...")
            drone.move_forward(40, "cm", 0.35)
        else:
            log("Obstacle nearby. Moving backward...")
            drone.move_backward(30, "cm", 0.35)
        if not should_stop():
            drone.turn_right(180)
    finally:
        if airborne and not should_stop():
            log("Landing...")
            drone.land()
