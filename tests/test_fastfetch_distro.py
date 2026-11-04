"""On Nexora, Halcyon's installer keeps the distribution's fastfetch (its logo and colours in /etc/xdg/fastfetch):
~/.config/fastfetch would take its place. Run: python3 -m unittest discover -s tests"""

import os
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FILES = (ROOT / "sdata/subcmd-install/3.files.sh").read_text()
BLOCK = re.search(r"\nif \[\[ -z \"\$\{HALCYON_FASTFETCH_LOGO_OVERRIDE.*?\nfi\n", FILES, re.S).group(0)


def decide(os_id: str, preset: str | None = None) -> str:
    with tempfile.TemporaryDirectory() as tmp:
        release = Path(tmp, "os-release")
        release.write_text(f'NAME="X"\nID="{os_id}"\nID_LIKE="endeavouros arch"\n')
        env = {"PATH": os.environ["PATH"], "OS_RELEASE_FILE": str(release)}
        if preset is not None:
            env["HALCYON_FASTFETCH_LOGO_OVERRIDE"] = preset
        script = BLOCK + 'echo "${HALCYON_FASTFETCH_LOGO_OVERRIDE:-unset}"\n'
        return subprocess.run(["bash", "-c", script], env=env, capture_output=True, text=True, check=True).stdout.strip()


class FastfetchOnNexoraTest(unittest.TestCase):
    def test_nexora_keeps_its_fastfetch(self):
        self.assertEqual(decide("nexora"), "0")

    def test_elsewhere_halcyons_is_installed(self):
        self.assertEqual(decide("arch"), "unset")       # 3.files-legacy.sh and -exp.yaml treat unset as 1

    def test_the_variable_still_wins(self):
        self.assertEqual(decide("nexora", "1"), "1")

    def test_both_installers_honour_it(self):
        legacy = (ROOT / "sdata/subcmd-install/3.files-legacy.sh").read_text()
        self.assertIn('"${HALCYON_FASTFETCH_LOGO_OVERRIDE:-1}" == "0"', legacy)
        exp = (ROOT / "sdata/subcmd-install/3.files-exp.yaml").read_text()
        self.assertRegex(exp, r'name: "HALCYON_FASTFETCH_LOGO_OVERRIDE"\s+value: "1"')


if __name__ == "__main__":
    unittest.main()
