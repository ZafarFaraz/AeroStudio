"""Create native Windows and macOS icon containers from the master PNG."""

from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "assets" / "codrone_studio_icon.png"
OUTPUT = ROOT / "packaging"


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    source = Image.open(SOURCE).convert("RGBA")
    square = source.resize((1024, 1024), Image.Resampling.LANCZOS)
    square.save(
        OUTPUT / "codrone_studio.ico",
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )
    square.save(OUTPUT / "codrone_studio.icns")
    print(f"Generated native build icons in {OUTPUT}")


if __name__ == "__main__":
    main()
