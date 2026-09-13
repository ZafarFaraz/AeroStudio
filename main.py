"""Launch AeroStudio or verify that its packaged UI can start."""

from __future__ import annotations

import argparse
import sys
import traceback
from pathlib import Path
from typing import Sequence

from app import AeroStudioApp


def run_startup_smoke_test(report_path: Path | None = None) -> int:
    """Initialize and render the UI once, then exit without using hardware."""
    try:
        application = AeroStudioApp()
        application.root.withdraw()
        application.root.update_idletasks()
        application.root.update()
        application.root.destroy()
    except Exception:
        status = 1
        report = "AeroStudio startup smoke test failed:\n" + traceback.format_exc()
    else:
        status = 0
        report = "AeroStudio startup smoke test passed.\n"

    if report_path is not None:
        try:
            report_path.write_text(report, encoding="utf-8")
        except OSError:
            return 2
    stream = sys.stderr if status else sys.stdout
    if stream is not None:
        print(report, end="", file=stream)
    return status


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Launch AeroStudio.")
    parser.add_argument(
        "--startup-smoke-test",
        action="store_true",
        help="initialize the UI once and exit without connecting to a drone",
    )
    parser.add_argument(
        "--startup-smoke-report",
        type=Path,
        help="write the startup smoke-test result to this file",
    )
    arguments = parser.parse_args(argv)

    if arguments.startup_smoke_report is not None and not arguments.startup_smoke_test:
        parser.error("--startup-smoke-report requires --startup-smoke-test")
    if arguments.startup_smoke_test:
        return run_startup_smoke_test(arguments.startup_smoke_report)

    AeroStudioApp().run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
