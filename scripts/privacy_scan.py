"""Scan the whole git history for things that must not be published.

Checks every commit (all refs): author/committer identities, commit messages (incl.
Co-Authored-By), every file version ever committed (e-mail addresses, local absolute paths,
secret-looking strings, extra terms), forbidden file names (.env, keys) and file sizes > 1 MB.

Usage::

    python scripts/privacy_scan.py [--term TEXT ...]

``--term`` adds machine-specific strings (e.g. the local username or a personal e-mail). They are
searched for but never printed, so the report can be committed.
Exit code 1 if anything is found.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAX_BYTES = 1024 * 1024

ALLOWED_EMAIL_DOMAINS = (
    "edupulse.example",  # synthetic demo data
    "users.noreply.github.com",  # commit identity
    "allowed.example",  # test fixtures
    "evil.example",
    "insecure.example",
    "example.com",
    "example.org",
)
EMAIL = re.compile(rb"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}")
PATHS = re.compile(
    rb"(?:[A-Za-z]:\\\\?Users\\\\?[^\\\s\"']+|/(?:Users|home)/[A-Za-z0-9._-]+/|/[a-z]/Users/)"
)
SECRETS = {
    "private key": re.compile(rb"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "AWS access key": re.compile(rb"AKIA[0-9A-Z]{16}"),
    "GitHub token": re.compile(rb"gh[pousr]_[A-Za-z0-9]{30,}"),
    "Slack token": re.compile(rb"xox[baprs]-[A-Za-z0-9-]{10,}"),
    "generic API key": re.compile(
        rb"(?i)(?:api[_-]?key|secret[_-]?key)\s*[:=]\s*['\"][A-Za-z0-9/+_-]{24,}['\"]"
    ),
}
FORBIDDEN_NAMES = re.compile(r"(^|/)(\.env(\..+)?|id_rsa|id_ed25519|.*\.pem|.*\.p12|.*\.key)$")
ALLOWED_ENV = {".env.example"}
# Placeholder/test values that are allowed to look like credentials.
ALLOWED_SNIPPETS = (b"ci-only-", b"test-secret-", b"change-me-local-only")


def git(*args: str, stdin: bytes | None = None) -> bytes:
    # Fixed executable and arguments built by this script only.
    return subprocess.run(  # noqa: S603
        ["git", *args],  # noqa: S607
        cwd=ROOT,
        check=True,
        capture_output=True,
        input=stdin,
    ).stdout


def email_allowed(address: bytes) -> bool:
    if b"@" not in address:
        return False
    domain = address.rsplit(b"@", 1)[1].decode(errors="replace").lower()
    return any(domain == d or domain.endswith("." + d) for d in ALLOWED_EMAIL_DOMAINS)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--term", action="append", default=[], help="extra string to search for")
    args = parser.parse_args()
    terms = [t.encode() for t in args.term if t]
    findings: dict[str, set[str]] = defaultdict(set)

    commits = git("rev-list", "--all").split()
    print(f"commits scanned: {len(commits)}")

    # 1. Identities and messages.
    log = git("log", "--all", "--format=%H%x00%an%x00%ae%x00%cn%x00%ce%x00%B%x01")
    for record in log.split(b"\x01"):
        if not record.strip():
            continue  # trailing separator
        commit, an, ae, cn, ce, body = (record.strip(b"\n").split(b"\x00") + [b""] * 6)[:6]
        short = commit[:8].decode()
        for address in (ae, ce):
            if not email_allowed(address):
                findings["identity e-mail not allowed"].add(short)
        if b"co-authored-by" in body.lower():
            findings["Co-Authored-By in commit message"].add(short)
        for term in terms:
            if term.lower() in (an + ae + cn + ce + body).lower():
                findings["runtime term in identity/message"].add(short)

    # 2. Every blob ever committed.
    objects = git("rev-list", "--objects", "--all").decode(errors="replace").splitlines()
    paths: dict[str, str] = {}
    for line in objects:
        sha, _, path = line.partition(" ")
        if path:
            paths.setdefault(sha, path)
    sizes = git(
        "cat-file",
        "--batch-check=%(objectname) %(objecttype) %(objectsize)",
        stdin="".join(f"{sha}\n" for sha in paths).encode(),
    )
    blobs: list[tuple[str, int, str]] = []
    for line in sizes.decode().splitlines():
        object_id, kind, object_size = line.split()
        if kind == "blob":
            blobs.append((object_id, int(object_size), paths[object_id]))
    print(f"file versions scanned: {len(blobs)}")

    for blob_id, size, path in blobs:
        name = path.replace("\\", "/")
        if FORBIDDEN_NAMES.search(name) and Path(name).name not in ALLOWED_ENV:
            findings["forbidden file name"].add(name)
        if size > MAX_BYTES:
            findings["file larger than 1 MB"].add(f"{name} ({size} bytes)")
        content = git("cat-file", "-p", blob_id)
        for address in set(EMAIL.findall(content)):
            if not email_allowed(address):
                findings["e-mail address in file"].add(
                    f"{name}: {address.decode(errors='replace')}"
                )
        if PATHS.search(content):
            findings["local absolute path in file"].add(name)
        for label, pattern in SECRETS.items():
            for match in pattern.finditer(content):
                if not any(s in match.group(0) for s in ALLOWED_SNIPPETS):
                    findings[f"possible secret ({label})"].add(name)
        for term in terms:
            if term.lower() in content.lower():
                findings["runtime term in file"].add(name)

    print(f"runtime terms checked: {len(terms)} (values not printed)")
    if not findings:
        print("RESULT: no findings")
        return 0
    for rule, items in sorted(findings.items()):
        print(f"FINDING [{rule}]")
        for item in sorted(items):
            print(f"  - {item}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
