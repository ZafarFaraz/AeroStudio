"""Generate the small, consistent PNG pictograms used by program cards."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Callable

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "assets" / "program_icons"
SCALE = 3
SIZE = 64
CYAN = "#8cf2ff"
TEAL = "#35d2e8"
WHITE = "#f5f8f9"
MUTED = "#79aeb8"
RED = "#ff6961"
YELLOW = "#ffd60a"
GREEN = "#30d158"
PURPLE = "#b99cff"


def p(value: float) -> int:
    return round(value * SCALE)


def points(values: list[tuple[float, float]]) -> list[tuple[int, int]]:
    return [(p(x), p(y)) for x, y in values]


def line(draw: ImageDraw.ImageDraw, values: list[tuple[float, float]], fill: str = CYAN,
         width: float = 3) -> None:
    draw.line(points(values), fill=fill, width=p(width), joint="curve")


def drone(draw: ImageDraw.ImageDraw, x: float = 32, y: float = 28) -> None:
    line(draw, [(x - 13, y - 8), (x + 13, y + 8)], MUTED, 2)
    line(draw, [(x + 13, y - 8), (x - 13, y + 8)], MUTED, 2)
    draw.rounded_rectangle((p(x - 8), p(y - 5), p(x + 8), p(y + 5)), p(3), fill=CYAN)
    for rotor_x, rotor_y in ((x - 15, y - 10), (x + 15, y - 10),
                             (x - 15, y + 10), (x + 15, y + 10)):
        draw.ellipse((p(rotor_x - 5), p(rotor_y - 3), p(rotor_x + 5), p(rotor_y + 3)),
                     outline=CYAN, width=p(2))


def arrow(draw: ImageDraw.ImageDraw, start: tuple[float, float], end: tuple[float, float],
          fill: str = CYAN) -> None:
    line(draw, [start, end], fill, 3)
    angle = math.atan2(end[1] - start[1], end[0] - start[0])
    for delta in (2.55, -2.55):
        tip = (end[0] + math.cos(angle + delta) * 8,
               end[1] + math.sin(angle + delta) * 8)
        line(draw, [tip, end], fill, 3)


def path_icon(draw: ImageDraw.ImageDraw, shape: list[tuple[float, float]],
              colors: list[str] | None = None) -> None:
    for index in range(len(shape) - 1):
        line(draw, [shape[index], shape[index + 1]],
             colors[index % len(colors)] if colors else CYAN, 4)
    draw.ellipse((p(shape[0][0] - 3), p(shape[0][1] - 3),
                  p(shape[0][0] + 3), p(shape[0][1] + 3)), fill=WHITE)


def battery(draw: ImageDraw.ImageDraw) -> None:
    draw.rounded_rectangle((p(12), p(21), p(50), p(43)), p(4), outline=CYAN, width=p(3))
    draw.rectangle((p(50), p(27), p(55), p(37)), fill=CYAN)
    for x in (17, 26, 35):
        draw.rounded_rectangle((p(x), p(26), p(x + 6), p(38)), p(2), fill=GREEN)


def sensor(draw: ImageDraw.ImageDraw) -> None:
    drone(draw, 25, 32)
    for radius in (8, 14, 20):
        draw.arc((p(29), p(32 - radius), p(29 + radius * 2), p(32 + radius)),
                 -55, 55, fill=CYAN, width=p(2))


def lights(draw: ImageDraw.ImageDraw) -> None:
    drone(draw, 32, 25)
    for x, color in zip((14, 26, 38, 50), (RED, GREEN, "#64a8ff", WHITE)):
        draw.ellipse((p(x - 4), p(46), p(x + 4), p(54)), fill=color)


def temperature(draw: ImageDraw.ImageDraw) -> None:
    draw.rounded_rectangle((p(27), p(10), p(37), p(45)), p(5), outline=CYAN, width=p(3))
    draw.ellipse((p(21), p(39), p(43), p(61)), fill=CYAN)
    draw.rectangle((p(30), p(21), p(34), p(48)), fill=RED)
    draw.ellipse((p(27), p(45), p(37), p(55)), fill=RED)


def orientation(draw: ImageDraw.ImageDraw) -> None:
    center = (28, 38)
    arrow(draw, center, (28, 12), GREEN)
    arrow(draw, center, (52, 45), RED)
    arrow(draw, center, (10, 52), "#64a8ff")
    draw.ellipse((p(24), p(34), p(32), p(42)), fill=WHITE)


def colors(draw: ImageDraw.ImageDraw) -> None:
    draw.ellipse((p(10), p(10), p(54), p(54)), outline=CYAN, width=p(3))
    for xy, color in (((21, 21), RED), ((41, 21), YELLOW), ((21, 41), GREEN), ((41, 41), "#64a8ff")):
        x, y = xy
        draw.ellipse((p(x - 7), p(y - 7), p(x + 7), p(y + 7)), fill=color)


def hover(draw: ImageDraw.ImageDraw) -> None:
    drone(draw, 32, 25)
    for y in (43, 51):
        line(draw, [(18, y), (46, y)], MUTED, 2)


def forward_back(draw: ImageDraw.ImageDraw) -> None:
    drone(draw, 32, 32)
    arrow(draw, (18, 53), (48, 53), GREEN)
    arrow(draw, (46, 11), (16, 11), PURPLE)


def side_to_side(draw: ImageDraw.ImageDraw) -> None:
    drone(draw, 32, 32)
    arrow(draw, (26, 53), (8, 53), PURPLE)
    arrow(draw, (38, 53), (56, 53), GREEN)


def triangle(draw: ImageDraw.ImageDraw) -> None:
    path_icon(draw, [(12, 51), (32, 12), (53, 51), (12, 51)])


def zigzag(draw: ImageDraw.ImageDraw) -> None:
    path_icon(draw, [(9, 50), (22, 17), (33, 48), (45, 16), (56, 42)])


def dance(draw: ImageDraw.ImageDraw) -> None:
    drone(draw, 26, 36)
    line(draw, [(45, 13), (45, 40)], PURPLE, 3)
    line(draw, [(45, 13), (56, 17)], PURPLE, 3)
    draw.ellipse((p(36), p(36), p(47), p(47)), fill=PURPLE)
    draw.ellipse((p(49), p(14), p(58), p(23)), fill=YELLOW)


def square(draw: ImageDraw.ImageDraw) -> None:
    path_icon(draw, [(13, 13), (51, 13), (51, 51), (13, 51), (13, 13)])


def turn(draw: ImageDraw.ImageDraw) -> None:
    draw.arc((p(10), p(10), p(54), p(54)), 35, 330, fill=CYAN, width=p(4))
    draw.polygon(points([(50, 10), (56, 25), (40, 21)]), fill=CYAN)
    drone(draw, 32, 33)


def flip(draw: ImageDraw.ImageDraw) -> None:
    draw.arc((p(18), p(7), p(46), p(57)), 75, 315, fill=PURPLE, width=p(4))
    draw.polygon(points([(43, 48), (52, 54), (49, 39)]), fill=PURPLE)
    drone(draw, 32, 31)


def figure_eight(draw: ImageDraw.ImageDraw) -> None:
    draw.arc((p(7), p(18), p(34), p(48)), 45, 315, fill=CYAN, width=p(4))
    draw.arc((p(30), p(18), p(57), p(48)), 225, 495, fill=PURPLE, width=p(4))
    draw.ellipse((p(29), p(29), p(35), p(35)), fill=WHITE)


def obstacle(draw: ImageDraw.ImageDraw) -> None:
    drone(draw, 20, 32)
    for radius in (10, 17):
        draw.arc((p(21), p(32 - radius), p(21 + radius * 2), p(32 + radius)),
                 -50, 50, fill=YELLOW, width=p(2))
    draw.rounded_rectangle((p(49), p(18), p(58), p(48)), p(2), fill=RED)


def rainbow_square(draw: ImageDraw.ImageDraw) -> None:
    path_icon(
        draw,
        [(13, 13), (51, 13), (51, 51), (13, 51), (13, 13)],
        [RED, YELLOW, GREEN, "#64a8ff"],
    )


DRAWERS: dict[str, Callable[[ImageDraw.ImageDraw], None]] = {
    "battery_check": battery,
    "sensor_check": sensor,
    "led_colors": lights,
    "temperature_check": temperature,
    "orientation_check": orientation,
    "color_check": colors,
    "hover": hover,
    "forward_back": forward_back,
    "side_to_side": side_to_side,
    "triangle": triangle,
    "zigzag": zigzag,
    "gentle_dance": dance,
    "square": square,
    "full_turn": turn,
    "flip": flip,
    "figure_eight": figure_eight,
    "obstacle_scout": obstacle,
    "rainbow_square": rainbow_square,
}


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for name, draw_icon in DRAWERS.items():
        image = Image.new("RGBA", (SIZE * SCALE, SIZE * SCALE), (0, 0, 0, 0))
        canvas = ImageDraw.Draw(image)
        canvas.rounded_rectangle(
            (p(1), p(1), p(SIZE - 1), p(SIZE - 1)),
            p(14),
            fill="#214b56",
            outline="#3f7984",
            width=p(1),
        )
        draw_icon(canvas)
        image.resize((SIZE, SIZE), Image.Resampling.LANCZOS).save(OUTPUT / f"{name}.png")
    print(f"Generated {len(DRAWERS)} program icons in {OUTPUT}")


if __name__ == "__main__":
    main()
