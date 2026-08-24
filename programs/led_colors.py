"""Program 3: cycle the drone LED through red, green, blue, then white."""

import time

NAME = "LED Colors"
DESCRIPTION = "Cycles red, green, blue, and white. The drone stays grounded."


def run(drone, log, should_stop) -> None:
    colors = (
        ("Red", 255, 0, 0),
        ("Green", 0, 255, 0),
        ("Blue", 0, 0, 255),
        ("White", 255, 255, 255),
    )
    for name, red, green, blue in colors:
        if should_stop():
            return
        log(name)
        drone.set_drone_LED(red, green, blue, 100)
        time.sleep(1)
