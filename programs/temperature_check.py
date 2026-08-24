"""Program 4: read the drone's internal temperature while grounded."""

NAME = "Temperature Check"
DESCRIPTION = "Shows the drone temperature in Celsius without taking off."


def run(drone, log, should_stop) -> None:
    temperature = drone.get_drone_temperature("C")
    log(f"Drone temperature: {temperature}°C")
