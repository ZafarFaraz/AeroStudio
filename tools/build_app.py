"""Build a native AeroStudio bundle for the current operating system."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    build_environment = os.environ.copy()
    build_environment["PYINSTALLER_CONFIG_DIR"] = str(
        ROOT / "build" / "pyinstaller-cache"
    )
    subprocess.run(
        [sys.executable, str(ROOT / "tools" / "generate_program_icons.py")],
        cwd=ROOT,
        check=True,
    )
    subprocess.run(
        [sys.executable, str(ROOT / "tools" / "generate_build_icons.py")],
        cwd=ROOT,
        check=True,
    )
    subprocess.run(
        [
            sys.executable,
            "-m",
            "PyInstaller",
            "--clean",
            "--noconfirm",
            str(ROOT / "packaging" / "AeroStudio.spec"),
        ],
        cwd=ROOT,
        env=build_environment,
        check=True,
    )
    print(f"Build complete. Open {ROOT / 'dist'}")


if __name__ == "__main__":
    main()
