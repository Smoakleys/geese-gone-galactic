"""Email notifications for the GGG harness — a per-session digest of the changes Claude made.

The Owner (away for long autonomous stretches) wants to *receive* the harness improvements as
they land, without babysitting a console. Transport is plain SMTP with a Gmail **app password**
(the Claude Gmail integration can only draft, not send). Everything a secret touches lives in a
**gitignored** local config; with no config the module runs in a harmless console dry-run so the
test suite and offline use never need credentials.

Two things it produces:
* ``build_digest`` — gathers the harness-change commits since the last email (tracked by sha in a
  gitignored state file) into a concise, skimmable summary: a headline, the test-count rollup,
  one line per change, and the commit/PR references.
* ``send_email`` / ``send_digest`` / ``send_alert`` — deliver it (or print it, unconfigured).

CLI:
    python ops/notify.py digest        # build + send the session digest, then advance the marker
    python ops/notify.py iter "s" "b"  # send a per-iteration update email (Owner wants one each iteration)
    python ops/notify.py alert "text"  # send an immediate one-off alert (blocked run / STOP)
    python ops/notify.py test          # send a tiny "it works" email to verify setup
    python ops/notify.py preview       # print the digest without sending or advancing the marker
"""

from __future__ import annotations

import json
import re
import smtplib
import ssl
import subprocess
import sys
from dataclasses import dataclass
from email.message import EmailMessage
from pathlib import Path
from typing import Optional

_REPO = Path(__file__).resolve().parents[1]
CONFIG_PATH = _REPO / "ops" / "notify_config.local.json"   # gitignored; holds the app password
STATE_PATH = _REPO / "ops" / ".notify_state.json"          # gitignored; last-emailed commit sha
DEFAULT_TO = "bridgerhumphreys03@gmail.com"


@dataclass
class NotifyConfig:
    smtp_host: str
    smtp_port: int
    username: str
    app_password: str
    sender: str
    to: str

    @classmethod
    def load(cls) -> Optional["NotifyConfig"]:
        """Load the gitignored config, or None if it's absent/incomplete (→ dry-run)."""
        if not CONFIG_PATH.exists():
            return None
        try:
            d = json.loads(CONFIG_PATH.read_text())
        except (json.JSONDecodeError, OSError):
            return None
        if not d.get("app_password") or not d.get("username"):
            return None
        user = str(d["username"])
        return cls(
            smtp_host=str(d.get("smtp_host", "smtp.gmail.com")),
            smtp_port=int(d.get("smtp_port", 465)),
            username=user,
            app_password=str(d["app_password"]),
            sender=str(d.get("from", user)),
            to=str(d.get("to", DEFAULT_TO)),
        )


# -- delivery --------------------------------------------------------------------------


def send_email(subject: str, body: str, config: Optional[NotifyConfig] = None) -> bool:
    """Send one email. Returns True if actually sent; False (console dry-run) if unconfigured.

    Never raises on a missing config — an unconfigured harness must still run. A real SMTP error
    (bad password, no network) propagates so a genuine misconfiguration is loud, not silent.
    """
    config = config or NotifyConfig.load()
    if config is None:
        print("[notify] (dry-run — no ops/notify_config.local.json; not sent)")
        print(f"[notify] To: {DEFAULT_TO}\n[notify] Subject: {subject}\n{body}")
        return False

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = config.sender
    msg["To"] = config.to
    msg.set_content(body)

    if config.smtp_port == 465:
        with smtplib.SMTP_SSL(config.smtp_host, config.smtp_port,
                              context=ssl.create_default_context()) as s:
            s.login(config.username, config.app_password)
            s.send_message(msg)
    else:  # 587 / STARTTLS
        with smtplib.SMTP(config.smtp_host, config.smtp_port) as s:
            s.starttls(context=ssl.create_default_context())
            s.login(config.username, config.app_password)
            s.send_message(msg)
    print(f"[notify] sent -> {config.to}: {subject}")
    return True


def send_alert(text: str, config: Optional[NotifyConfig] = None) -> bool:
    """Immediate one-off alert (exceptional events: a blocked run, a STOP)."""
    return send_email(f"GGG harness ALERT: {text[:80]}", text, config)


def send_digest(config: Optional[NotifyConfig] = None, *, advance: bool = True) -> bool:
    """Build the session digest and send it, advancing the last-emailed marker on success."""
    subject, body, head = build_digest()
    sent = send_email(subject, body, config)
    if advance:
        _write_state(head)  # advance even in dry-run so a later real run doesn't double-report
    return sent


# -- digest construction ---------------------------------------------------------------


def build_digest(repo_root: Path = _REPO) -> tuple[str, str, str]:
    """Return ``(subject, body, head_sha)`` summarizing changes since the last emailed commit."""
    head = _git(repo_root, "rev-parse", "HEAD")
    last = _read_state()
    rng = f"{last}..HEAD" if last else "-15"  # first run: last 15 commits
    log = _git(repo_root, "log", rng, "--no-merges", "--pretty=%h%x1f%s")
    changes = [line.split("\x1f", 1) for line in log.splitlines() if "\x1f" in line]

    tests = _current_test_count(repo_root)
    n = len(changes)
    headline = f"GGG harness: {n} change{'s' if n != 1 else ''}"
    if tests:
        headline += f", {tests} tests green"

    lines = [headline, "", f"Repo: {_repo_slug(repo_root)}  |  HEAD {head[:9]}"]
    if tests:
        lines.append(f"Test suite: {tests} passing")
    lines.append("")
    if changes:
        lines.append(f"Changes since last email ({n}):")
        for sha, subj in changes:
            lines.append(f"  - {subj}  [{sha}]")
    else:
        lines.append("No new harness changes since the last email.")
    lines += ["", "— sent by the GGG harness notifier (ops/notify.py)"]
    return headline, "\n".join(lines), head


def _current_test_count(repo_root: Path) -> Optional[str]:
    """Best-effort: read the '→ NNN passed' line docs/AUTOPILOT.md keeps current each increment."""
    doc = repo_root / "docs" / "AUTOPILOT.md"
    if not doc.exists():
        return None
    m = re.search(r"→\s*(\d+)\s+passed", doc.read_text(encoding="utf-8", errors="ignore"))
    return m.group(1) if m else None


def _repo_slug(repo_root: Path) -> str:
    try:
        url = _git(repo_root, "config", "--get", "remote.origin.url")
    except Exception:
        return repo_root.name
    m = re.search(r"[:/]([^/]+/[^/]+?)(?:\.git)?$", url)
    return m.group(1) if m else url or repo_root.name


# -- state + git helpers ---------------------------------------------------------------


def _read_state() -> Optional[str]:
    if not STATE_PATH.exists():
        return None
    try:
        return json.loads(STATE_PATH.read_text()).get("last_sha")
    except (json.JSONDecodeError, OSError):
        return None


def _write_state(sha: str) -> None:
    STATE_PATH.write_text(json.dumps({"last_sha": sha}, indent=2))


def _git(repo_root: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=repo_root, check=True,
                          capture_output=True, text=True).stdout.strip()


def main(argv: Optional[list[str]] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    cmd = argv[0] if argv else "preview"
    if cmd == "digest":
        send_digest()
    elif cmd == "preview":
        subject, body, _ = build_digest()
        print(body)
    elif cmd == "alert":
        send_alert(argv[1] if len(argv) > 1 else "(no message)")
    elif cmd == "iter":
        # Per-iteration update: a short email after each increment (Owner wants one every iteration).
        msg = argv[1] if len(argv) > 1 else "(iteration update)"
        body = argv[2] if len(argv) > 2 else msg
        try:
            head = _git(_REPO, "log", "-1", "--pretty=%h %s")
        except Exception:
            head = "?"
        full = f"{body}\n\nHEAD: {head}\nRepo: {_repo_slug(_REPO)}\n\n— GGG harness (per-iteration update)"
        send_email(f"GGG iteration: {msg[:70]}", full)
    elif cmd == "test":
        send_email("GGG harness: notifier test",
                   "If you're reading this in your inbox, SMTP delivery works.")
    else:
        print(f"unknown command {cmd!r}; use digest|iter|preview|alert|test")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
