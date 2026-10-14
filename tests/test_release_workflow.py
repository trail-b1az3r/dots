"""The stable release workflow's "work out the tag" step, run as written against throwaway git repositories.

A run by hand used to check out the tag it was given, which fails when nobody has pushed that tag yet. Run:
python3 -m unittest discover -s tests"""

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = ROOT / ".github/workflows/stable.yml"

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None


def step_script(name):
    data = yaml.safe_load(WORKFLOW.read_text())
    for step in data["jobs"]["release"]["steps"]:
        if step.get("name") == name:
            return step["run"]
    raise KeyError(name)


@unittest.skipUnless(yaml and shutil.which("git") and shutil.which("bash"), "needs PyYAML, git and bash")
class StableReleaseStepTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.repo = Path(tmp.name)
        self.env_file = self.repo.parent / f"{self.repo.name}.env"
        self.addCleanup(lambda: self.env_file.unlink(missing_ok=True))
        self.git("init", "-q", "-b", "main")
        self.commit("1.0.0")

    def git(self, *args):
        env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t",
               "GIT_COMMITTER_EMAIL": "t@t"}
        return subprocess.run(["git", *args], cwd=self.repo, env=env, check=True, capture_output=True,
                              text=True).stdout.strip()

    def commit(self, version):
        (self.repo / "VERSION").write_text(version + "\n")
        self.git("add", "VERSION")
        self.git("commit", "-q", "-m", f"version {version}")

    def run_step(self, event, ref_name, version_input=""):
        self.env_file.write_text("")
        env = {**os.environ, "EVENT": event, "REF_NAME": ref_name, "VERSION_INPUT": version_input,
               "GITHUB_ENV": str(self.env_file)}
        done = subprocess.run(["bash", "-e", "-c", step_script("Work out the tag and version")], cwd=self.repo,
                              env=env, capture_output=True, text=True)
        values = dict(line.split("=", 1) for line in self.env_file.read_text().splitlines() if "=" in line)
        return done, values

    def test_by_hand_without_a_tag_makes_one_from_the_branch(self):
        done, values = self.run_step("workflow_dispatch", "main")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual((values["TAG"], values["VERSION"], values["CREATE_TAG"]), ("v1.0.0", "1.0.0", "true"))
        self.assertEqual(values["SHA"], self.git("rev-parse", "HEAD"))

    def test_by_hand_with_the_version_typed_with_or_without_v(self):
        for typed in ("1.0.0", "v1.0.0", " 1.0.0 "):
            done, values = self.run_step("workflow_dispatch", "main", typed)
            self.assertEqual(done.returncode, 0, typed + done.stdout + done.stderr)
            self.assertEqual(values["TAG"], "v1.0.0")

    def test_by_hand_with_a_version_that_is_not_in_the_file_says_how_to_fix_it(self):
        done, values = self.run_step("workflow_dispatch", "main", "2.0.0")
        self.assertNotEqual(done.returncode, 0)
        self.assertIn("Change VERSION to 2.0.0", done.stdout + done.stderr)
        self.assertNotIn("TAG", values)

    def test_by_hand_with_an_existing_tag_releases_what_it_points_at(self):
        self.git("tag", "v1.0.0")
        tagged = self.git("rev-parse", "HEAD")
        self.commit("1.1.0-dev")
        done, values = self.run_step("workflow_dispatch", "main", "1.0.0")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual((values["SHA"], values["CREATE_TAG"]), (tagged, "false"))

    def test_a_pushed_tag_must_match_version(self):
        done, values = self.run_step("push", "v1.0.0")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual(values["CREATE_TAG"], "false")
        done, _ = self.run_step("push", "v9.9.9")
        self.assertNotEqual(done.returncode, 0)

    def test_publish_makes_the_tag_only_when_asked(self):
        script = step_script("Publish the release")
        self.assertIn('--target "$SHA"', script)
        self.assertIn("--verify-tag", script)
        data = yaml.safe_load(WORKFLOW.read_text())
        checkout = data["jobs"]["release"]["steps"][0]
        self.assertNotIn("ref", checkout.get("with", {}), "checking out a tag that may not exist fails the run")


if __name__ == "__main__":
    unittest.main()
