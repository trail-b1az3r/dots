#!/usr/bin/env python3
"""Why apps closed: `halcyon crashes [--since 2d] [--json]`.

Apps opened from the shell (launcher, dock, search, revolver) are the shell's children, so they share the
halcyon-quickshell service's cgroup. Under systemd's defaults (KillMode=control-group, OOMPolicy=stop) a restart
of the shell, an update, or one of those apps being killed for memory, closes every one of them at once. That looks
like Vesktop, Spotify and media players "crashing after a while". Halcyon's unit now sets KillMode=process and
OOMPolicy=continue; this command shows whether that is in effect, and what actually closed recently:

  - app crashes systemd-coredump recorded (coredumpctl)
  - processes the kernel killed for memory
  - restarts and stops of the shell service, and which apps were in its cgroup
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

SHELL_UNIT = "halcyon-quickshell.service"
MEDIA_HINT = re.compile(r"vesktop|discord|electron|spotify|mpv|vlc|rhythmbox|amberol|strawberry|clementine|elisa|lollypop|"
                        r"audacious|cmus|tauon|celluloid|totem|haruna|youtube|chrom|firefox|zen", re.I)


def run(argv: list[str], timeout: float = 10) -> str:
    if not shutil.which(argv[0]):
        return ""
    try:
        out = subprocess.run(argv, capture_output=True, text=True, timeout=timeout, check=False, stdin=subprocess.DEVNULL)
    except (OSError, subprocess.SubprocessError):
        return ""
    return out.stdout


def unit_settings(unit: str = SHELL_UNIT) -> dict[str, str]:
    text = run(["systemctl", "--user", "show", unit, "-p", "KillMode,OOMPolicy,ControlGroup,NRestarts,ActiveState"])
    return dict(line.split("=", 1) for line in text.splitlines() if "=" in line)


def apps_in_cgroup(cgroup: str) -> list[str]:
    """Names of the processes in a cgroup other than the shell itself."""
    if not cgroup:
        return []
    procs = Path("/sys/fs/cgroup") / cgroup.lstrip("/") / "cgroup.procs"
    names = []
    try:
        pids = procs.read_text().split()
    except OSError:
        return []
    for pid in pids:
        try:
            name = Path(f"/proc/{pid}/comm").read_text().strip()
        except OSError:
            continue
        if name not in ("qs", "quickshell", ".quickshell-wra"):
            names.append(name)
    return sorted(set(names))


def parse_coredumps(text: str) -> list[dict]:
    """coredumpctl --json=short output -> [{time, exe, signal}]."""
    try:
        data = json.loads(text) if text.strip() else []
    except ValueError:
        return []
    out = []
    for row in data if isinstance(data, list) else []:
        exe = row.get("exe") or row.get("comm") or "?"
        out.append({"time": row.get("time"), "exe": exe, "signal": row.get("sig"), "pid": row.get("pid")})
    return out


OOM_RE = re.compile(r"Out of memory: Killed process (\d+) \(([^)]+)\)|oom-kill:.*task=([^,\s]+)")
SHELL_STOP_RE = re.compile(r"(Main process exited|Failed with result|Scheduled restart job|Stopping|Stopped|A process of this unit has been killed by the OOM killer)")


def parse_oom(lines: list[str]) -> list[str]:
    found = []
    for line in lines:
        m = OOM_RE.search(line)
        if m:
            found.append(m.group(2) or m.group(3))
    return found


def parse_shell_events(lines: list[str]) -> list[str]:
    return [line.strip() for line in lines if SHELL_STOP_RE.search(line)]


def verdict(settings: dict[str, str], cores: list[dict], ooms: list[str], shell_events: list[str], in_cgroup: list[str]) -> list[str]:
    """Plain sentences: what most likely closed the apps, and what to do."""
    notes = []
    if not settings.get("KillMode"):
        notes.append("Could not read the shell service (no systemctl --user here, or it is not installed).")
    risky = bool(settings.get("KillMode")) and (settings.get("KillMode") != "process" or settings.get("OOMPolicy", "stop") == "stop")
    media_in_shell = [n for n in in_cgroup if MEDIA_HINT.search(n)]
    if risky:
        notes.append("The shell service still uses systemd's defaults, so restarting the shell closes every app it opened. "
                     "Update Halcyon (update apply, or ./setup install), then log out and back in.")
    elif in_cgroup:
        notes.append("Apps opened from the shell share its cgroup, but the service no longer takes them down with it.")
    if media_in_shell and risky:
        notes.append("Opened from the shell right now: " + ", ".join(media_in_shell) + ".")
    restarts = [e for e in shell_events if "restart" in e.lower() or "Failed" in e or "OOM" in e]
    if restarts:
        notes.append(f"The shell stopped or restarted {len(restarts)} time(s) in this period; with the old settings each one closed the apps.")
    if ooms:
        notes.append("The kernel killed these for lack of memory: " + ", ".join(sorted(set(ooms))) + ". "
                     "Something is using too much memory; check with: systemd-cgtop or btop.")
    media_cores = [c for c in cores if MEDIA_HINT.search(str(c.get("exe")))]
    if media_cores:
        names = sorted({Path(str(c["exe"])).name for c in media_cores})
        notes.append("These crashed on their own (core dumps): " + ", ".join(names) + ". "
                     "`coredumpctl info <name>` shows the backtrace to report upstream.")
    if not notes:
        notes.append("Nothing recorded: no core dumps, memory kills or shell restarts in this period.")
    return notes


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="halcyon crashes", description=__doc__.splitlines()[0])
    parser.add_argument("--since", default="2d", help="how far back, as journalctl understands it (default 2d)")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    since = f"-{args.since}" if re.fullmatch(r"\d+[smhdw]", args.since) else args.since

    settings = unit_settings()
    cores = parse_coredumps(run(["coredumpctl", "list", "--no-pager", "--json=short", "--since", since]))
    oom_lines = run(["journalctl", "-k", "--no-pager", "-o", "cat", "--since", since, "-g", "Out of memory|oom-kill"]).splitlines()
    shell_lines = run(["journalctl", "--user", "-u", SHELL_UNIT, "--no-pager", "-o", "short", "--since", since]).splitlines()
    ooms = parse_oom(oom_lines)
    shell_events = parse_shell_events(shell_lines)
    in_cgroup = apps_in_cgroup(settings.get("ControlGroup", ""))
    notes = verdict(settings, cores, ooms, shell_events, in_cgroup)

    if args.json:
        print(json.dumps({"unit": settings, "coredumps": cores, "oom_killed": ooms, "shell_events": shell_events,
                          "apps_in_shell_cgroup": in_cgroup, "notes": notes}, indent=2))
        return 0

    print(f"Shell service: KillMode={settings.get('KillMode', '?')} OOMPolicy={settings.get('OOMPolicy', '?')} "
          f"restarts={settings.get('NRestarts', '?')}")
    if in_cgroup:
        print("Apps in the shell's cgroup: " + ", ".join(in_cgroup))
    if cores:
        print("\nCore dumps:")
        for c in cores[-15:]:
            print(f"  {c.get('exe')} (signal {c.get('signal')})")
    if ooms:
        print("\nKilled for memory: " + ", ".join(ooms))
    if shell_events:
        print("\nShell service events:")
        for e in shell_events[-10:]:
            print("  " + e)
    print()
    for note in notes:
        print("* " + note)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
