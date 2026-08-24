"""Program 1: read the connected drone's battery level without flying."""

NAME = "Battery Check"
DESCRIPTION = "Shows the drone battery level. The drone does not take off."


def run(drone, log, should_stop) -> None:
    battery = drone.get_battery()
    log(f"Battery: {battery}%")
