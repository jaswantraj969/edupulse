"""Mask local absolute paths and strip ANSI colour codes from command output (stdin -> stdout).

Used by scripts/gate.sh so that gate output can be committed to docs/process/REVIEW_PACKET.md
without leaking the developer's home directory or username.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _root_variants() -> list[str]:
    win = str(ROOT)  # e.g. C:\x\y on Windows, /x/y elsewhere
    fwd = win.replace("\\", "/")
    variants = {win, fwd, fwd.replace(" ", "%20")}
    if re.match(r"^[A-Za-z]:/", fwd):  # Git Bash form: /c/x/y
        variants.add("/" + fwd[0].lower() + fwd[2:])
    return sorted(variants, key=len, reverse=True)


PATTERNS = [re.compile(re.escape(v), re.IGNORECASE) for v in _root_variants()]
HOME = re.compile(
    r"(?:[A-Za-z]:[\\/]+Users|/[a-z]/Users|/home|/Users)[\\/]+[^\\/\s]+", re.IGNORECASE
)
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")


def sanitize(text: str) -> str:
    text = ANSI.sub("", text)
    for pattern in PATTERNS:
        text = pattern.sub("<repo>", text)
    return HOME.sub("<home>", text)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    for line in sys.stdin.buffer:
        sys.stdout.write(sanitize(line.decode("utf-8", errors="replace")))
