"""The Halcyon updater (halcyon/update) against a real git "upstream" in a temporary folder, from each way an install
can be: a clone on main, on another branch, a detached checkout, one with no upstream set, one with local edits, and a
release archive (no git at all). notify-send is a stand-in that logs what it was asked to show.
Run: python3 -m unittest discover -s tests"""

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UPDATE = ROOT / "dots/.config/hypr/hyprland/halcyon/update"

NOTIFY = """#!/bin/sh
# Logs each notification as one JSON line; answers "apply" to an "Update now" action when ANSWER_APPLY is set.
python3 - "$@" <<'EOF' >> "$NOTIFY_LOG"
import json, sys
print(json.dumps(sys.argv[1:]))
EOF
case "$*" in *--wait*) [ -n "${ANSWER_APPLY:-}" ] && echo apply ;; esac
exit 0
"""


def git(cwd, *args, check=True):
    done = subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True, check=False,
                          env={**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t",
                               "GIT_COMMITTER_EMAIL": "t@t", "GIT_CONFIG_GLOBAL": "/dev/null"})
    if check and done.returncode != 0:
        raise AssertionError(f"git {' '.join(args)}: {done.stderr}")
    return done.stdout.strip()


@unittest.skipUnless(shutil.which("git") and shutil.which("bash"), "needs git and bash")
class UpdaterTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.home = self.tmp / "home"
        self.state = self.home / ".local/state/halcyon"
        self.state.mkdir(parents=True)
        self.bin = self.tmp / "bin"
        self.bin.mkdir()
        (self.bin / "notify-send").write_text(NOTIFY)
        (self.bin / "notify-send").chmod(0o755)
        for name in ("systemctl", "hyprctl", "pgrep"):   # nothing to reload in a test
            (self.bin / name).write_text("#!/bin/sh\nexit 1\n")
            (self.bin / name).chmod(0o755)
        self.notify_log = self.tmp / "notify.log"

        # The upstream: a work tree we commit to, pushed to a bare repository the installs clone.
        self.upstream = self.tmp / "upstream.git"
        git(self.tmp, "init", "-q", "--bare", "-b", "main", str(self.upstream))
        self.work = self.tmp / "work"
        git(self.tmp, "clone", "-q", str(self.upstream), str(self.work))
        git(self.work, "checkout", "-q", "-b", "main")
        self.commit({"dots/.config/halcyon-test/a.txt": "one\n", "README.md": "hi\n"}, "first")
        self.first = git(self.work, "rev-parse", "HEAD")

    # --- helpers --------------------------------------------------------------------------------------------------

    def commit(self, files, message):
        for rel, text in files.items():
            path = self.work / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
        git(self.work, "add", "-A")
        git(self.work, "commit", "-q", "-m", message)
        git(self.work, "push", "-q", "origin", "HEAD:main")

    def clone(self, name="halcyon"):
        repo = self.tmp / name
        git(self.tmp, "clone", "-q", str(self.upstream), str(repo))
        (self.state / "repo").write_text(f"{repo}\n")
        # As ./setup install leaves it: the files are in $HOME too.
        dest = self.home / ".config/halcyon-test/a.txt"
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(repo / "dots/.config/halcyon-test/a.txt", dest)
        return repo

    def run_update(self, *args, answer_apply=False):
        env = {**os.environ, "HOME": str(self.home), "XDG_STATE_HOME": str(self.home / ".local/state"),
               "PATH": f"{self.bin}:{os.environ['PATH']}", "NOTIFY_LOG": str(self.notify_log),
               "HALCYON_REMOTE": str(self.upstream), "GIT_CONFIG_GLOBAL": "/dev/null",
               "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
        if answer_apply:
            env["ANSWER_APPLY"] = "1"
        return subprocess.run(["bash", str(UPDATE), *args], capture_output=True, text=True, env=env, timeout=60)

    def notifications(self):
        if not self.notify_log.exists():
            return []
        return [json.loads(line) for line in self.notify_log.read_text().splitlines()]

    def titles(self):
        """Each notification's title: the first argument that isn't an option or an option's value."""
        titles = []
        for argv in self.notifications():
            rest = list(argv)
            while rest and rest[0].startswith("-"):
                option = rest.pop(0)
                if option in ("-a", "-i", "-A", "-u", "-t", "-c", "-h") and rest:
                    rest.pop(0)
            titles.append(rest[0] if rest else "")
        return titles

    def home_file(self):
        return (self.home / ".config/halcyon-test/a.txt").read_text()

    def waiting(self):
        path = self.state / "update-available"
        return path.read_text().strip() if path.exists() else None

    # --- check ----------------------------------------------------------------------------------------------------

    def test_on_main_a_new_commit_is_announced_once(self):
        self.clone()
        self.commit({"dots/.config/halcyon-test/a.txt": "two\n"}, "Two")
        self.assertEqual(self.run_update("check").returncode, 0)
        self.assertEqual(self.waiting(), "1")
        self.assertEqual(self.titles(), ["Halcyon update available"])
        self.run_update("check")
        self.assertEqual(len(self.notifications()), 1, "the same commits are announced once")

    def test_another_branch_still_hears_about_main(self):
        repo = self.clone()
        git(repo, "checkout", "-q", "-b", "trying-something")
        self.commit({"dots/.config/halcyon-test/a.txt": "two\n"}, "Two")
        self.run_update("check")
        self.assertEqual(self.waiting(), "1")
        self.assertEqual(self.titles(), ["Halcyon update available"])

    def test_a_detached_checkout_and_no_upstream_still_hear_about_main(self):
        repo2 = self.clone("halcyon2")
        git(repo2, "branch", "-q", "--unset-upstream")
        repo = self.clone()
        git(repo, "checkout", "-q", "--detach")
        self.commit({"dots/.config/halcyon-test/a.txt": "two\n"}, "Two")
        self.run_update("check")
        self.assertEqual(self.waiting(), "1")
        (self.state / "repo").write_text(f"{repo2}\n")
        (self.state / "update-seen").unlink(missing_ok=True)
        (self.state / "update-available").unlink(missing_ok=True)
        done = self.run_update("check")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(self.waiting(), "1")

    def test_up_to_date_says_nothing(self):
        self.clone()
        self.run_update("check")
        self.assertIsNone(self.waiting())
        self.assertEqual(self.notifications(), [])

    def test_update_now_on_the_notification_applies_it(self):
        self.clone()
        self.commit({"dots/.config/halcyon-test/a.txt": "two\n"}, "Two")
        self.run_update("check", answer_apply=True)
        self.assertEqual(self.home_file(), "two\n")
        self.assertIn("Halcyon updated", self.titles())

    # --- apply ----------------------------------------------------------------------------------------------------

    def test_apply_copies_the_changed_files(self):
        self.clone()
        self.commit({"dots/.config/halcyon-test/a.txt": "two\n", "dots/.config/halcyon-test/new.txt": "new\n"}, "Two")
        done = self.run_update("apply")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(self.home_file(), "two\n")
        self.assertEqual((self.home / ".config/halcyon-test/new.txt").read_text(), "new\n")
        self.assertIsNone(self.waiting())

    def test_apply_from_another_branch_goes_back_to_main(self):
        repo = self.clone()
        git(repo, "checkout", "-q", "-b", "trying-something")
        self.commit({"dots/.config/halcyon-test/a.txt": "two\n"}, "Two")
        done = self.run_update("apply")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(git(repo, "branch", "--show-current"), "main")
        self.assertEqual(self.home_file(), "two\n")

    def test_apply_keeps_local_edits_in_the_repository(self):
        repo = self.clone()
        (repo / "README.md").write_text("my notes\n")
        self.commit({"dots/.config/halcyon-test/a.txt": "two\n"}, "Two")
        done = self.run_update("apply")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(self.home_file(), "two\n")
        self.assertEqual((repo / "README.md").read_text(), "my notes\n")

    def test_a_failure_is_shown_not_just_printed(self):
        repo = self.clone()
        # main has a commit upstream doesn't, and upstream moved on: no fast-forward.
        (repo / "README.md").write_text("mine\n")
        git(repo, "commit", "-q", "-am", "mine")
        self.commit({"dots/.config/halcyon-test/a.txt": "two\n"}, "Two")
        done = self.run_update("apply")
        self.assertNotEqual(done.returncode, 0)
        self.assertIn("Halcyon update failed", self.titles())
        self.assertTrue((self.state / "update-error").read_text().strip())

    def test_a_release_archive_install_updates_too(self):
        # An archive is the tree without .git: what was released, here the first commit.
        archive = self.tmp / "halcyon-1.0.0"
        git(self.tmp, "clone", "-q", str(self.upstream), str(archive))
        shutil.rmtree(archive / ".git")
        (self.state / "repo").write_text(f"{archive}\n")
        dest = self.home / ".config/halcyon-test/a.txt"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text("one\n")
        self.commit({"dots/.config/halcyon-test/a.txt": "two\n"}, "Two")

        done = self.run_update("check")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(self.titles(), ["Halcyon update available"])
        done = self.run_update("apply")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(self.home_file(), "two\n")
        self.assertEqual(git(archive, "branch", "--show-current"), "main", "it is a clone from now on")
        self.commit({"dots/.config/halcyon-test/a.txt": "three\n"}, "Three")
        self.assertEqual(self.run_update("apply").returncode, 0)
        self.assertEqual(self.home_file(), "three\n")

    def test_status_only_reports(self):
        done = self.run_update("status")   # nothing recorded yet
        self.assertNotEqual(done.returncode, 0)
        self.assertIn("No repository is recorded", done.stderr)
        self.assertEqual(self.notifications(), [])
        self.assertFalse((self.state / "update-error").exists())

    def test_status_says_where_it_stands(self):
        self.clone()
        self.commit({"dots/.config/halcyon-test/a.txt": "two\n"}, "Two")
        self.run_update("check")
        out = self.run_update("status").stdout
        self.assertIn("updates waiting: 1", out)
        self.assertIn("branch", out)


class TimerTest(unittest.TestCase):
    def test_the_timer_can_run_it(self):
        # It was committed without its executable bit, so the timer's ExecStart failed with "Permission denied" and
        # no check ever ran. It is executable now, and run through bash anyway, for copies installed before.
        mode = subprocess.run(["git", "-C", str(ROOT), "ls-files", "-s", str(UPDATE)], capture_output=True,
                              text=True, check=False).stdout.split(" ")[0]
        if mode:
            self.assertEqual(mode, "100755")
        unit = (ROOT / "dots/.config/systemd/user/halcyon-update.service").read_text()
        self.assertIn("ExecStart=/bin/bash %h/.config/hypr/hyprland/halcyon/update check", unit)

    def test_checks_hourly_and_login_turns_the_timer_on(self):
        timer = (ROOT / "dots/.config/systemd/user/halcyon-update.timer").read_text()
        self.assertIn("OnUnitActiveSec=1h", timer)
        init = (ROOT / "dots/.config/hypr/hyprland/halcyon/init.lua").read_text()
        self.assertIn("enable --now halcyon-update.timer", init)


if __name__ == "__main__":
    unittest.main()
