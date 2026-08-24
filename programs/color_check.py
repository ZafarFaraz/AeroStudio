"""Program 6: report colours seen by the front and bottom colour sensors."""

NAME = "Color Check"
DESCRIPTION = "Shows the colours detected by both colour sensors. No flight."


def run(drone, log, should_stop) -> None:
    log(f"Front colour: {drone.get_front_color('name')}")
    log(f"Bottom colour: {drone.get_back_color('name')}")
