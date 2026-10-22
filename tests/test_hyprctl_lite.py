"""hyprctl-lite's `install update` and `install full`, run against stand-in git, pacman, make, sudo, id and getent,
and a stand-in hyprland-plus binary in a scratch bin folder. Nothing is built or installed.
Run: python3 -m unittest discover -s tests"""

import os
import shutil
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "tools/hyprctl-lite/hyprctl-lite"
OLD = "1111111111111111111111111111111111111111"
NEW = "2222222222222222222222222222222222222222"

STUBS = {
    "id": 'echo "${FAKE_UID:-0}"',
    "getent": 'echo "me:x:1000:1000::$FAKE_HOME:/bin/bash"',
    # sudo -u USER CMD...: run CMD as is
    "sudo": 'shift 2; exec "$@"',
    "pacman": r'''echo "pacman $*" >> "$LOG"
case "$1 $2" in
  "-Q hyprland-plus") [ "${FAKE_AUR:-0}" = 1 ] && { echo "hyprland-plus 1-1"; exit 0; }; exit 1 ;;
  "-Q hyprland") exit 1 ;;
  "-Q hyprland-plus-local") exit 0 ;;
  "-T hyprland") exit 0 ;;
esac
exit 0''',
    # make -C REPO all leaves a stand-in build; make install can be made to stop part way (FAKE_INSTALL_FAIL).
    "make": r'''echo "make $*" >> "$LOG"
if [ "$3" = all ]; then
  mkdir -p "$2/build/hyprctl"
  printf '#!/bin/sh\necho "%s"\n' "${FAKE_BUILT:-hyprland-plus 0.56.2.p3 (Hyprland 0.56.2)}" > "$2/build/Hyprland"
  printf '#!/bin/sh\necho hyprctl\n' > "$2/build/hyprctl/hyprctl"
  chmod +x "$2/build/Hyprland" "$2/build/hyprctl/hyprctl"
fi
[ "$3" = install ] && [ "${FAKE_INSTALL_FAIL:-0}" = 1 ] && exit 2
exit 0''',
    "git": r'''echo "git $*" >> "$LOG"
args="$*"
case "$args" in
  *"rev-parse --short HEAD"*) echo "${FAKE_HEAD:0:7}" ;;
  *"rev-parse HEAD"*) echo "$FAKE_HEAD" ;;
  *"ls-remote"*) printf '%s\trefs/heads/halcyon-0.56.2\n' "$FAKE_HEAD" ;;
  *" log "*) echo "2222222 Drop at the top to fullscreen" ;;
  *"clone"*) mkdir -p "${@: -1}/.git" ;;
esac
exit 0''',
}


class HyprctlLiteTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.stubs = self.tmp / "stubs"
        self.bin = self.tmp / "usr-local-bin"
        self.home = self.tmp / "home"
        for d in (self.stubs, self.bin, self.home / "hyprland-plus/.git", self.home / "hyprland-plus/packaging/aur"):
            d.mkdir(parents=True)
        (self.home / "hyprland-plus/packaging/aur/PKGBUILD").write_text("depends=(aquamarine)\nmakedepends=(cmake)\n")
        for name, body in STUBS.items():
            self.executable(self.stubs / name, "#!/bin/bash\n" + body + "\n")
        self.script = self.tmp / "hyprctl-lite"
        shutil.copy(SCRIPT, self.script)
        self.log = self.tmp / "log"
        self.log.write_text("")

    def executable(self, path, text):
        path.write_text(text)
        path.chmod(path.stat().st_mode | stat.S_IEXEC)

    def install_plus(self, commit=OLD):
        self.executable(self.bin / "Hyprland", '#!/bin/sh\necho "hyprland-plus 0.56.2.p2 (Hyprland 0.56.2)"\n')
        note = self.home / ".local/state/halcyon/hyprland-plus-commit"
        note.parent.mkdir(parents=True, exist_ok=True)
        note.write_text(commit[:7] + "\n")

    def run_lite(self, *args, head=NEW, **extra):
        env = {"PATH": f"{self.stubs}:/usr/bin:/bin", "LOG": str(self.log), "FAKE_HOME": str(self.home),
               "FAKE_HEAD": head, "SUDO_USER": "me", "HOME": str(self.home), "HYPRCTL_LITE_BIN_DIR": str(self.bin)}
        env.update(extra)
        return subprocess.run(["bash", str(self.script), *args], capture_output=True, text=True, env=env, timeout=60)

    # --- the install itself ---

    def test_a_make_install_that_stops_part_way_still_installs_hyprland(self):
        # make install stops at the first file it can't copy, and Hyprland is among the last: /usr/local/bin was
        # left empty. The built binaries are copied in directly, and checked.
        result = self.run_lite("install", "full", FAKE_INSTALL_FAIL="1")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("make install stopped", result.stderr)
        self.assertTrue((self.bin / "Hyprland").is_file())
        self.assertTrue((self.bin / "hyprctl").is_file())
        self.assertEqual(os.readlink(self.bin / "hyprland"), "Hyprland")
        self.assertIn("hyprland-plus 0.56.2.p3", result.stdout)

    def test_an_install_that_is_not_hyprland_plus_fails_loudly(self):
        result = self.run_lite("install", "full", FAKE_BUILT="Hyprland 0.56.2")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("does not say it is hyprland-plus", result.stderr)
        self.assertTrue(self.script.exists(), "kept, so it can be run again")

    # --- update ---

    def test_update_when_up_to_date_builds_nothing_and_keeps_itself(self):
        self.install_plus(OLD)
        result = self.run_lite("install", "update", head=OLD)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("already up to date", result.stdout)
        self.assertNotIn("make ", self.log.read_text())
        self.assertNotIn("pacman -S", self.log.read_text())
        self.assertTrue(self.script.exists())

    def test_update_with_new_commits_lists_them_builds_installs_and_keeps_itself(self):
        self.install_plus(OLD)
        result = self.run_lite("install", "update", head=NEW)
        self.assertEqual(result.returncode, 0, result.stderr)
        log = self.log.read_text()
        self.assertIn("pull --ff-only origin halcyon-0.56.2", log)
        self.assertIn(f"log --oneline --no-decorate {OLD[:7]}..{NEW}", log)
        self.assertIn("Drop at the top to fullscreen", result.stdout)
        self.assertIn("all", [line.split()[-1] for line in log.splitlines() if line.startswith("make")])
        self.assertIn("install", [line.split()[-1] for line in log.splitlines() if line.startswith("make")])
        self.assertEqual((self.home / ".local/state/halcyon/hyprland-plus-commit").read_text().strip(), NEW[:7])
        self.assertTrue(self.script.exists(), "install update keeps hyprctl-lite for the next one")
        self.assertIn("stays installed", result.stdout)

    def test_force_rebuilds_an_up_to_date_install(self):
        self.install_plus(OLD)
        result = self.run_lite("install", "update", "--force", head=OLD)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("make -C", self.log.read_text())

    def test_update_without_hyprland_plus_says_to_install_it(self):
        result = self.run_lite("install", "update")
        self.assertEqual(result.returncode, 1)
        self.assertIn("sudo hyprctl-lite install full", result.stderr)
        self.assertNotIn("git ", self.log.read_text())

    def test_stock_hyprland_is_not_hyprland_plus(self):
        self.executable(self.bin / "Hyprland", '#!/bin/sh\necho "Hyprland 0.56.2 built from branch"\n')
        result = self.run_lite("install", "update")
        self.assertEqual(result.returncode, 1)
        self.assertIn("not installed", result.stderr)

    def test_update_leaves_an_aur_install_to_the_aur_helper(self):
        self.install_plus(OLD)
        result = self.run_lite("install", "update", FAKE_AUR="1")
        self.assertEqual(result.returncode, 1)
        self.assertIn("AUR", result.stderr)
        self.assertNotIn("make ", self.log.read_text())

    def test_update_needs_sudo(self):
        self.install_plus(OLD)
        result = self.run_lite("install", "update", FAKE_UID="1000")
        self.assertEqual(result.returncode, 1)
        self.assertIn("sudo hyprctl-lite install update", result.stderr)

    # --- check ---

    def test_check_says_whether_an_update_is_waiting_without_sudo(self):
        self.install_plus(OLD)
        waiting = self.run_lite("install", "update", "--check", head=NEW, FAKE_UID="1000")
        self.assertEqual(waiting.returncode, 10, waiting.stdout + waiting.stderr)
        self.assertIn("An update is waiting", waiting.stdout)
        current = self.run_lite("install", "update", "--check", head=OLD, FAKE_UID="1000")
        self.assertEqual(current.returncode, 0, current.stdout + current.stderr)
        self.assertNotIn("make ", self.log.read_text())
        self.assertNotIn("pull", self.log.read_text())

    def test_check_without_hyprland_plus(self):
        self.assertEqual(self.run_lite("install", "update", "--check").returncode, 1)

    # --- full, and what is not a command ---

    def test_full_still_installs_and_removes_itself(self):
        result = self.run_lite("install", "full")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("make -C", self.log.read_text())
        self.assertFalse(self.script.exists())

    def test_anything_else_is_refused(self):
        for args in ([], ["install"], ["install", "everything"], ["update"], ["install", "update", "--nope"],
                     ["install", "full", "--force"]):
            result = self.run_lite(*args)
            self.assertEqual(result.returncode, 1, args)
            self.assertIn("usage:", result.stderr)
        self.assertEqual(self.log.read_text(), "")


if __name__ == "__main__":
    unittest.main()
