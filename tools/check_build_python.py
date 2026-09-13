"""Check whether the running Python can build AeroStudio with PyInstaller."""

from __future__ import annotations

import sys
from collections.abc import Sequence


def is_supported_version(version: Sequence[int]) -> bool:
    """Accept Python 3.10.1 through 3.14.x, excluding unsupported 3.10.0."""
    major_minor = tuple(version[:2])
    major_minor_patch = tuple(version[:3])
    return (3, 10) <= major_minor <= (3, 14) and major_minor_patch != (3, 10, 0)


if __name__ == "__main__":
    raise SystemExit(0 if is_supported_version(sys.version_info) else 1)
