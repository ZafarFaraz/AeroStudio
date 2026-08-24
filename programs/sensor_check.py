"""Program 2: display a few easy-to-understand distance sensor readings."""

NAME = "Sensor Check"
DESCRIPTION = "Reads height and front distance sensors without taking off."


def run(drone, log, should_stop) -> None:
    height = drone.get_height("cm")
    front = drone.get_front_range("cm")
    log(f"Height: {height} cm")
    log(f"Front distance: {front} cm")
