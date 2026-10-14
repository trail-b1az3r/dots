"""The QML widget tests in tests/qml, run with qmltestrunner against mocked shell modules (tests/qml/mock).

They drive the real revolver with mouse drags, and load every theme style of the drum and the plates. Skipped
where Qt's qmltestrunner (with QtQuick.Shapes and QtTest) is not installed.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import unittest
from pathlib import Path

QML = Path(__file__).resolve().parent / "qml"
RUNNER = shutil.which("qmltestrunner") or next((p for p in ("/usr/lib/qt6/bin/qmltestrunner", "/usr/lib/qt6/qmltestrunner")
                                               if os.path.exists(p)), None)


@unittest.skipUnless(RUNNER, "qmltestrunner is not installed")
class QmlWidgetTests(unittest.TestCase):
    def test_qml(self):
        for test in sorted(QML.glob("tst_*.qml")):
            env = dict(os.environ, QT_QPA_PLATFORM="offscreen")
            out = subprocess.run([RUNNER, "-import", str(QML / "mock"), "-input", str(test)],
                                 capture_output=True, text=True, env=env, timeout=300, cwd=QML)
            text = out.stdout + out.stderr
            self.assertEqual(out.returncode, 0, text[-4000:])
            self.assertRegex(text, r"Totals: \d+ passed, 0 failed")
            # A QML error that a test did not catch still fails the run.
            errors = [line for line in text.splitlines() if re.search(r"TypeError|ReferenceError|Cannot assign|is not a type", line)]
            self.assertEqual(errors, [], "\n".join(errors))


if __name__ == "__main__":
    unittest.main()
