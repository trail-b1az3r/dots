#!/usr/bin/env python3
"""halcyon.UwU-agent (UwU: universal web user [auth]): Halcyon's Wi-Fi, password and web password keeper.

    halcyon uwu                     whether the agent is running, and what the vault holds
    halcyon uwu agent               run the agent (halcyon-uwu-agent.service does, at login)
    halcyon uwu wifi [list]         the Wi-Fi networks it knows a password for
    halcyon uwu wifi add SSID       keep a Wi-Fi password (typed, or on stdin)
    halcyon uwu wifi remove SSID
    halcyon uwu web [list]          sites and user names (never the passwords)
    halcyon uwu web add SITE USER   keep a web password (typed, or on stdin)
    halcyon uwu web get SITE [USER] copy that password; the clipboard is cleared again after 45 seconds
    halcyon uwu web pick            choose one from a menu and copy it (Super + Alt + P)
    halcyon uwu web remove SITE [USER]

The agent is NetworkManager's secret agent, the job plasma-nm's agent did: when NetworkManager needs a Wi-Fi
password (a new network, a changed password, a network that forgot it), it asks the agent. The agent answers from
the vault when it can, and otherwise asks you in a password prompt (fuzzel, or zenity), then keeps what you typed.

Everything is kept in one vault, ~/.local/state/halcyon/uwu/vault.enc: AES-256 (openssl, PBKDF2), with its key in
the keyring (secret-tool), or, without a keyring, in a file only you can read. Passwords never go on a command line.
"""


import asyncio
import getpass
import hashlib
import json
import os
import secrets
import shutil
import subprocess
import sys
import time
from pathlib import Path

STATE = Path(os.environ.get("XDG_STATE_HOME") or Path.home() / ".local/state") / "halcyon/uwu"
VAULT = STATE / "vault.enc"
KEY_FILE = STATE / "vault.key"           # only when there is no keyring
KEYRING_ATTRS = ["application", "halcyon", "purpose", "uwu-vault"]
AGENT_ID = "halcyon.uwu-agent"
CLEAR_AFTER = 45


def run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, check=False, **kwargs)


def notify(title: str, body: str) -> None:
    if shutil.which("notify-send"):
        run(["notify-send", "-a", "Halcyon", "-i", "dialog-password", title, body])


# ── The vault ─────────────────────────────────────────────────────────────────

def vault_key() -> str | None:
    """The vault's key: in the keyring if there is one, else a file only you can read. None if it can't be had."""
    if shutil.which("secret-tool"):
        found = run(["secret-tool", "lookup", *KEYRING_ATTRS]).stdout.strip()
        if found:
            return found
        if VAULT.exists() and not KEY_FILE.exists():
            return None     # the keyring is locked: a new key would lose the vault
        if not KEY_FILE.exists():
            key = secrets.token_hex(32)
            stored = subprocess.run(["secret-tool", "store", "--label=Halcyon UwU vault", *KEYRING_ATTRS],
                                    input=key, text=True, capture_output=True, check=False)
            if stored.returncode == 0:
                return key
    if KEY_FILE.is_file():
        return KEY_FILE.read_text(encoding="utf-8").strip()
    if VAULT.exists():
        return None
    key = secrets.token_hex(32)
    STATE.mkdir(parents=True, exist_ok=True)
    fd = os.open(KEY_FILE, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(key)
    return key


def openssl(args: list[str], data: bytes, key: str) -> subprocess.CompletedProcess:
    """openssl with the key on a pipe, so it never appears in a command line or a file."""
    read_fd, write_fd = os.pipe()
    try:
        os.write(write_fd, key.encode())
        os.close(write_fd)
        return subprocess.run(["openssl", "enc", "-aes-256-cbc", "-pbkdf2", "-iter", "200000", "-md", "sha256",
                               "-pass", f"fd:{read_fd}", *args], input=data, capture_output=True,
                              pass_fds=(read_fd,), check=False)
    finally:
        os.close(read_fd)


class VaultError(RuntimeError):
    pass


def load() -> dict:
    key = vault_key()
    if key is None:
        raise VaultError("the vault's key is in the keyring, and the keyring is locked")
    if not VAULT.exists():
        return {"wifi": {}, "web": {}}
    result = openssl(["-d"], VAULT.read_bytes(), key)
    if result.returncode != 0:
        raise VaultError("the vault could not be opened (wrong key?)")
    data = json.loads(result.stdout.decode())
    data.setdefault("wifi", {})
    data.setdefault("web", {})
    return data


def save(data: dict) -> None:
    key = vault_key()
    if key is None:
        raise VaultError("the vault's key is in the keyring, and the keyring is locked")
    result = openssl([], json.dumps(data).encode(), key)
    if result.returncode != 0:
        raise VaultError("the vault could not be written")
    STATE.mkdir(parents=True, exist_ok=True)
    tmp = VAULT.with_suffix(".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "wb") as handle:
        handle.write(result.stdout)
    os.replace(tmp, VAULT)


# ── Asking for a password ─────────────────────────────────────────────────────

def ask(prompt: str) -> str | None:
    """A password prompt on screen: fuzzel, else zenity. None if cancelled or there is no way to ask."""
    if shutil.which("fuzzel"):
        done = run(["fuzzel", "--dmenu", "--password", "--lines", "0", "--prompt", prompt], input="")
        return done.stdout.rstrip("\n") if done.returncode == 0 and done.stdout.strip() else None
    if shutil.which("zenity"):
        done = run(["zenity", "--password", "--title", prompt])
        return done.stdout.rstrip("\n") if done.returncode == 0 and done.stdout.strip() else None
    return None


def read_secret(prompt: str) -> str:
    """For the CLI: typed with no echo, or one line on stdin."""
    if sys.stdin.isatty():
        return getpass.getpass(prompt)
    return sys.stdin.readline().rstrip("\n")


# ── The clipboard ─────────────────────────────────────────────────────────────

def copy(secret: str) -> bool:
    """Copy, then clear the clipboard after CLEAR_AFTER seconds, if it still holds this (by hash, not by value)."""
    if not shutil.which("wl-copy"):
        return False
    subprocess.run(["wl-copy"], input=secret, text=True, check=False)
    digest = hashlib.sha256(secret.encode()).hexdigest()
    subprocess.Popen([sys.executable, __file__, "_clear", digest], stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL, start_new_session=True)
    return True


def clear_later(digest: str) -> int:
    time.sleep(CLEAR_AFTER)
    held = run(["wl-paste", "--no-newline"]).stdout
    if hashlib.sha256(held.encode()).hexdigest() == digest:
        run(["wl-copy", "--clear"])
    return 0


# ── NetworkManager's secret agent ─────────────────────────────────────────────

ALLOW_INTERACTION = 0x1
REQUEST_NEW = 0x2


def ssid_of(connection: dict) -> str:
    wireless = connection.get("802-11-wireless") or {}
    raw = wireless.get("ssid")
    raw = getattr(raw, "value", raw)
    if isinstance(raw, (bytes, bytearray)):
        return raw.decode(errors="replace")
    if isinstance(raw, list):
        return bytes(raw).decode(errors="replace")
    conn = connection.get("connection") or {}
    return str(getattr(conn.get("id"), "value", conn.get("id")) or "")


def secret_field(connection: dict, setting: str) -> str | None:
    """Which secret NetworkManager wants, for the settings this agent answers; None for the others (VPNs...)."""
    if setting == "802-11-wireless-security":
        security = connection.get(setting) or {}
        mgmt = getattr(security.get("key-mgmt"), "value", security.get("key-mgmt")) or "wpa-psk"
        return "wep-key0" if mgmt == "none" else "psk"
    if setting == "802-1x":
        return "password"
    return None


def answer(connection: dict, setting: str, flags: int, vault: dict, prompt=ask) -> tuple[str, str] | None:
    """(field, secret) to give NetworkManager, or None. Kept when the vault has it, unless NetworkManager says the
    one it had was wrong (REQUEST_NEW); otherwise asked for, if NetworkManager allows asking."""
    field = secret_field(connection, setting)
    if field is None:
        return None
    ssid = ssid_of(connection)
    kept = vault.get("wifi", {}).get(ssid)
    if kept and not flags & REQUEST_NEW:
        return field, kept
    if not flags & ALLOW_INTERACTION:
        return None
    typed = prompt(f"Wi-Fi password for {ssid}: " if not kept else f"{ssid}: that password failed. Password: ")
    if not typed:
        return None
    vault.setdefault("wifi", {})[ssid] = typed
    return field, typed


def agent() -> int:
    try:
        from dbus_next import BusType, Variant
        from dbus_next.aio import MessageBus
        from dbus_next.errors import DBusError
        from dbus_next.service import ServiceInterface, method
    except ImportError:
        print("halcyon uwu agent: needs python-dbus-next (sudo pacman -S python-dbus-next)", file=sys.stderr)
        return 1

    class SecretAgent(ServiceInterface):
        def __init__(self):
            super().__init__("org.freedesktop.NetworkManager.SecretAgent")

        @method()
        async def GetSecrets(self, connection: "a{sa{sv}}", connection_path: "o", setting_name: "s",  # noqa: F821
                             hints: "as", flags: "u") -> "a{sa{sv}}":  # noqa: F821
            loop = asyncio.get_running_loop()
            try:
                vault = await loop.run_in_executor(None, load)
            except VaultError as error:
                notify("Wi-Fi password", f"The UwU vault can't be opened: {error}.")
                vault = {"wifi": {}, "web": {}}
            got = await loop.run_in_executor(None, answer, connection, setting_name, flags, vault)
            if got is None:
                raise DBusError("org.freedesktop.NetworkManager.SecretAgent.NoSecrets", "no password for this network")
            try:
                await loop.run_in_executor(None, save, vault)
            except VaultError:
                pass
            field, secret = got
            return {setting_name: {field: Variant("s", secret)}}

        @method()
        def CancelGetSecrets(self, connection_path: "o", setting_name: "s"):  # noqa: F821
            return

        @method()
        def SaveSecrets(self, connection: "a{sa{sv}}", connection_path: "o"):  # noqa: F821
            return

        @method()
        def DeleteSecrets(self, connection: "a{sa{sv}}", connection_path: "o"):  # noqa: F821
            ssid = ssid_of(connection)
            try:
                vault = load()
                if vault["wifi"].pop(ssid, None) is not None:
                    save(vault)
            except VaultError:
                pass

    async def serve() -> None:
        # NetworkManager is on the system bus; tests point it at a private session bus with a stand-in.
        bus_type = BusType.SESSION if os.environ.get("HALCYON_UWU_BUS") == "session" else BusType.SYSTEM
        bus = await MessageBus(bus_type=bus_type).connect()
        bus.export("/org/freedesktop/NetworkManager/SecretAgent", SecretAgent())
        intro = await bus.introspect("org.freedesktop.NetworkManager", "/org/freedesktop/NetworkManager/AgentManager")
        proxy = bus.get_proxy_object("org.freedesktop.NetworkManager", "/org/freedesktop/NetworkManager/AgentManager",
                                     intro)
        manager = proxy.get_interface("org.freedesktop.NetworkManager.AgentManager")
        await manager.call_register_with_capabilities(AGENT_ID, 0)
        print(f"{AGENT_ID}: answering NetworkManager's password requests", file=sys.stderr)
        await bus.wait_for_disconnect()

    asyncio.run(serve())
    return 0


def agent_running() -> bool:
    return run(["systemctl", "--user", "is-active", "--quiet", "halcyon-uwu-agent.service"]).returncode == 0


# ── The CLI ───────────────────────────────────────────────────────────────────

def cmd_wifi(args: list[str]) -> int:
    vault = load()
    if not args or args[0] == "list":
        for ssid in sorted(vault["wifi"]):
            print(ssid)
        return 0
    if args[0] == "add" and len(args) == 2:
        secret = read_secret(f"Password for {args[1]}: ")
        if not secret:
            return 1
        vault["wifi"][args[1]] = secret
        save(vault)
        print(f"kept the password for {args[1]}")
        return 0
    if args[0] == "remove" and len(args) == 2:
        if vault["wifi"].pop(args[1], None) is None:
            print(f"no password kept for {args[1]}", file=sys.stderr)
            return 1
        save(vault)
        return 0
    print("usage: halcyon uwu wifi [list | add SSID | remove SSID]", file=sys.stderr)
    return 2


def find_login(vault: dict, site: str, user: str | None) -> dict | None:
    logins = vault["web"].get(site) or []
    if user is None:
        return logins[0] if len(logins) == 1 else None
    return next((entry for entry in logins if entry["user"] == user), None)


def cmd_web(args: list[str]) -> int:
    vault = load()
    if not args or args[0] == "list":
        for site in sorted(vault["web"]):
            for entry in vault["web"][site]:
                print(f"{site}  {entry['user']}")
        return 0
    if args[0] == "add" and len(args) == 3:
        site, user = args[1], args[2]
        secret = read_secret(f"Password for {user} at {site}: ")
        if not secret:
            return 1
        logins = [e for e in vault["web"].get(site, []) if e["user"] != user]
        logins.append({"user": user, "password": secret})
        vault["web"][site] = logins
        save(vault)
        print(f"kept {user} at {site}")
        return 0
    if args[0] == "get" and len(args) in (2, 3):
        entry = find_login(vault, args[1], args[2] if len(args) == 3 else None)
        if not entry:
            print(f"no single login kept for {args[1]}; name the user", file=sys.stderr)
            return 1
        if not copy(entry["password"]):
            print("halcyon uwu: wl-copy is not installed", file=sys.stderr)
            return 1
        print(f"copied the password for {entry['user']} at {args[1]}; cleared in {CLEAR_AFTER} s")
        return 0
    if args[0] == "pick":
        choices = [f"{site}  {e['user']}" for site in sorted(vault["web"]) for e in vault["web"][site]]
        if not choices:
            notify("Passwords", "No web passwords kept yet: halcyon uwu web add SITE USER")
            return 1
        picked = run(["fuzzel", "--dmenu", "--prompt", "Password for: "], input="\n".join(choices)).stdout.strip()
        if not picked:
            return 1
        site, _, user = picked.partition("  ")
        entry = find_login(vault, site, user)
        if entry and copy(entry["password"]):
            notify("Password copied", f"{user} at {site}. The clipboard is cleared in {CLEAR_AFTER} seconds.")
            return 0
        return 1
    if args[0] == "remove" and len(args) in (2, 3):
        if len(args) == 2:
            removed = vault["web"].pop(args[1], None) is not None
        else:
            before = vault["web"].get(args[1], [])
            vault["web"][args[1]] = [e for e in before if e["user"] != args[2]]
            removed = len(vault["web"][args[1]]) != len(before)
            if not vault["web"][args[1]]:
                vault["web"].pop(args[1])
        if not removed:
            print("nothing to remove", file=sys.stderr)
            return 1
        save(vault)
        return 0
    print("usage: halcyon uwu web [list | add SITE USER | get SITE [USER] | pick | remove SITE [USER]]", file=sys.stderr)
    return 2


def cmd_status() -> int:
    print(f"agent  {'running' if agent_running() else 'not running (systemctl --user start halcyon-uwu-agent)'}")
    try:
        vault = load()
    except VaultError as error:
        print(f"vault  {error}")
        return 1
    print(f"vault  {len(vault['wifi'])} Wi-Fi password(s), "
          f"{sum(len(v) for v in vault['web'].values())} web login(s), in {VAULT}")
    return 0


def main(argv: list[str]) -> int:
    command, rest = (argv[0], argv[1:]) if argv else ("status", [])
    try:
        if command == "agent":
            return agent()
        if command == "_clear" and rest:
            return clear_later(rest[0])
        if command == "wifi":
            return cmd_wifi(rest)
        if command == "web":
            return cmd_web(rest)
        if command == "status":
            return cmd_status()
    except VaultError as error:
        print(f"halcyon uwu: {error}", file=sys.stderr)
        return 1
    print("usage: halcyon uwu [status | agent | wifi ... | web ...]", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
