"""Program 5: report the drone's current tilt and heading angles."""

NAME = "Orientation Check"
DESCRIPTION = "Reads the X, Y, and Z angles while the drone stays grounded."


def run(drone, log, should_stop) -> None:
    log(f"X angle: {drone.get_x_angle()}°")
    log(f"Y angle: {drone.get_y_angle()}°")
    log(f"Z angle: {drone.get_z_angle()}°")
