from __future__ import annotations

import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from importlib import import_module
from io import StringIO
from pathlib import Path
from types import ModuleType
from unittest.mock import Mock, patch

from tools.check_build_python import is_supported_version


fake_app_module = ModuleType("app")
fake_app_module.AeroStudioApp = Mock()  # type: ignore[attr-defined]
with patch.dict("sys.modules", {"app": fake_app_module}):
    main = import_module("main")


class StartupSmokeTests(unittest.TestCase):
    def test_smoke_test_initializes_updates_and_destroys_root(self) -> None:
        application = Mock()
        with tempfile.TemporaryDirectory() as temporary_directory:
            report_path = Path(temporary_directory) / "smoke.log"
            with patch.object(main, "AeroStudioApp", return_value=application):
                with redirect_stdout(StringIO()):
                    status = main.run_startup_smoke_test(report_path)

            self.assertEqual(status, 0)
            application.root.withdraw.assert_called_once_with()
            application.root.update_idletasks.assert_called_once_with()
            application.root.update.assert_called_once_with()
            application.root.destroy.assert_called_once_with()
            self.assertEqual(
                report_path.read_text(encoding="utf-8"),
                "AeroStudio startup smoke test passed.\n",
            )

    def test_smoke_test_reports_startup_exception(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            report_path = Path(temporary_directory) / "smoke.log"
            with patch.object(main, "AeroStudioApp", side_effect=RuntimeError("bad cursor")):
                with redirect_stderr(StringIO()):
                    status = main.run_startup_smoke_test(report_path)

            self.assertEqual(status, 1)
            report = report_path.read_text(encoding="utf-8")
            self.assertIn("AeroStudio startup smoke test failed", report)
            self.assertIn("RuntimeError: bad cursor", report)


class BuildPythonVersionTests(unittest.TestCase):
    def test_rejects_only_python_3100_at_supported_lower_boundary(self) -> None:
        self.assertFalse(is_supported_version((3, 10, 0)))
        self.assertTrue(is_supported_version((3, 10, 1)))
        self.assertTrue(is_supported_version((3, 10, 14)))

    def test_accepts_supported_versions_and_rejects_outside_range(self) -> None:
        self.assertTrue(is_supported_version((3, 12, 8)))
        self.assertTrue(is_supported_version((3, 14, 0)))
        self.assertFalse(is_supported_version((3, 9, 20)))
        self.assertFalse(is_supported_version((3, 15, 0)))


if __name__ == "__main__":
    unittest.main()
