"""Pre-push secret scanner. Zero dependencies, stdlib only.

Scans exactly what a `git push` would ship — the git-tracked files (`git ls-files`) —
so anything under .gitignore (`.venv/`, scratchpad, local settings) is skipped for free.

Found secrets are REDACTED in the output (prefix + length only), never printed in full,
so running this in a shared terminal cannot itself leak a key.

Exit codes:
  0  clean — safe to push
  1  potential secret(s) found — review before pushing

Usage:
  python scripts/check_secrets.py
  python scripts/check_secrets.py && git push      # gate a push on a clean scan
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

# --- high-confidence provider key formats (matching one of these fails the scan) -------------
KEY_PATTERNS: dict[str, re.Pattern[str]] = {
    "Anthropic API key": re.compile(r"sk-ant-[A-Za-z0-9_\-]{24,}"),
    "OpenAI project key": re.compile(r"sk-proj-[A-Za-z0-9_\-]{20,}"),
    "OpenAI key": re.compile(r"sk-[A-Za-z0-9]{32,}"),
    "Google API key": re.compile(r"AIza[0-9A-Za-z_\-]{35}"),
    "AWS access key id": re.compile(r"AKIA[0-9A-Z]{16}"),
    "GitHub token": re.compile(r"gh[pousr]_[A-Za-z0-9]{36,}"),
    "GitHub fine-grained PAT": re.compile(r"github_pat_[A-Za-z0-9_]{22,}"),
    "Slack token": re.compile(r"xox[baprs]-[A-Za-z0-9\-]{10,}"),
    "Google OAuth secret": re.compile(r"GOCSPX-[A-Za-z0-9_\-]{20,}"),
    "Private key block": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY-----"),
}

# Generic "NAME = <literal>" secrets — lower confidence, still surfaced.
GENERIC = re.compile(
    r"""(?i)\b(api[_-]?key|secret|token|passwd|password|access[_-]?key)\b\s*[:=]\s*"""
    r"""['"]([^'"]{12,})['"]"""
)

# A match containing any of these is a placeholder/example, not a real leak.
PLACEHOLDER = re.compile(
    r"(\.\.\.|xxx+|your[-_ ]|example|placeholder|replace|dummy|fake|redacted|<|>|\$\{|%\()",
    re.IGNORECASE,
)

# Filenames that should never be committed at all. `.env.example`/`.sample`/`.template`/
# `.dist` are safe templates (placeholders only) and are explicitly allowed.
BAD_NAMES = re.compile(
    r"(^|/)(\.env(\.(?!(example|sample|template|dist)$)[^/]+)?|.*\.pem|.*\.pfx"
    r"|id_rsa|id_ed25519)$"
)

# Skip obviously-binary or huge blobs.
SKIP_SUFFIX = {".png", ".jpg", ".jpeg", ".gif", ".ico", ".pdf", ".zip", ".gz",
               ".whl", ".so", ".pyd", ".bin", ".pt", ".safetensors", ".onnx"}
MAX_BYTES = 2_000_000


def redact(s: str) -> str:
    """Show enough to locate the leak, never enough to reuse it."""
    s = s.strip()
    if len(s) <= 8:
        return "*" * len(s)
    return f"{s[:6]}...({len(s)} chars)"


def tracked_files() -> list[Path]:
    out = subprocess.run(
        ["git", "ls-files"], capture_output=True, text=True, check=True
    ).stdout
    return [Path(line) for line in out.splitlines() if line.strip()]


def scan_file(path: Path) -> list[tuple[int, str, str]]:
    """Return (line_no, finding_label, redacted_value) for one file."""
    findings: list[tuple[int, str, str]] = []
    if BAD_NAMES.search(path.as_posix()):
        findings.append((0, "committed secret file", path.name))
    if path.suffix.lower() in SKIP_SUFFIX:
        return findings
    try:
        if path.stat().st_size > MAX_BYTES:
            return findings
        text = path.read_text(encoding="utf-8", errors="strict")
    except (OSError, UnicodeDecodeError):
        return findings  # unreadable / binary → nothing to scan

    for lineno, line in enumerate(text.splitlines(), start=1):
        for label, pat in KEY_PATTERNS.items():
            for m in pat.finditer(line):
                hit = m.group(0)
                if PLACEHOLDER.search(hit):
                    continue
                findings.append((lineno, label, redact(hit)))
        for m in GENERIC.finditer(line):
            value = m.group(2)
            if PLACEHOLDER.search(value) or PLACEHOLDER.search(m.group(0)):
                continue
            if "/" in value or value.startswith(("http", "path")):
                continue  # looks like a path/url, not a credential
            findings.append((lineno, f"generic {m.group(1).lower()}", redact(value)))
    return findings


def main() -> int:
    try:
        files = tracked_files()
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("ERROR: not a git repo (or git not found).", file=sys.stderr)
        return 1

    all_findings: list[tuple[str, int, str, str]] = []
    for f in files:
        for lineno, label, value in scan_file(f):
            all_findings.append((f.as_posix(), lineno, label, value))

    print(f"Scanned {len(files)} git-tracked files.")
    if not all_findings:
        print("OK - no exposed secrets found. Safe to push.")
        return 0

    print(f"\nFAIL - {len(all_findings)} potential secret(s), REVIEW before pushing:\n")
    for path, lineno, label, value in all_findings:
        loc = f"{path}:{lineno}" if lineno else path
        print(f"  [{label}] {loc}  ->  {value}")
    print("\nIf any is real: remove it, rotate the key, and scrub git history "
          "(git rm --cached / filter-repo) before pushing.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
