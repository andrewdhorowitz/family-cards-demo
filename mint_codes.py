#!/usr/bin/env python3
"""Mint Family Cards access codes (Phase 2).

Generates random tokens, stores ONLY their SHA-256 hashes + expiries in
codes.json (repo root, next to this script), and writes the plain links
to an output file the caller points OUTSIDE the repo (default
./codes-plain.txt). Tokens are never printed to stdout — only scopes
and expiries are.

Usage:
    python3 mint_codes.py --out /path/outside/repo/codes.txt \
        --entry "emma|emma|14d" \
        --entry "owner — permanent|owner|365d" \
        --entry "quick test|emma|1h"

Each --entry is "label|scope|duration" where duration is like 14d, 1h,
or 30m. Without --merge, minting REPLACES codes.json with the fresh
batch (pushing that codes.json is what rotates codes: replaced or
expired entries stop working). --base sets the link prefix
(default https://example.pages.dev).
"""

import argparse
import hashlib
import json
import re
import secrets
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

DURATION_RE = re.compile(r"^(\d+(?:\.\d+)?)([dhm])$")


def parse_duration(text):
    m = DURATION_RE.match(text.strip())
    if not m:
        raise ValueError(f"bad duration {text!r} (use e.g. 14d, 1h, 30m)")
    value, unit = float(m.group(1)), m.group(2)
    if unit == "d":
        return timedelta(days=value)
    if unit == "h":
        return timedelta(hours=value)
    return timedelta(minutes=value)


def iso_z(dt):
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Mint Family Cards access codes")
    ap.add_argument("--entry", action="append", default=[],
                    help='"label|scope|duration" — repeatable')
    ap.add_argument("--out", default="./codes-plain.txt",
                    help="plain-links output file (point it OUTSIDE the repo)")
    ap.add_argument("--codes", default=str(Path(__file__).with_name("codes.json")),
                    help="codes.json path (default: next to this script)")
    ap.add_argument("--base", default="https://example.pages.dev",
                    help="link base URL")
    ap.add_argument("--merge", action="store_true",
                    help="merge into existing codes.json instead of replacing it")
    args = ap.parse_args(argv)

    if not args.entry:
        ap.error("at least one --entry is required")

    now = datetime.now(timezone.utc)
    entries, lines = [], []
    for raw in args.entry:
        parts = raw.split("|")
        if len(parts) != 3:
            ap.error(f"--entry must be 'label|scope|duration', got {raw!r}")
        label, scope, duration = (p.strip() for p in parts)
        expires = now + parse_duration(duration)
        token = secrets.token_urlsafe(24)  # >=128-bit
        entries.append({
            "scope": scope,
            "sha256": hashlib.sha256(token.encode()).hexdigest(),
            "expires": iso_z(expires),
        })
        lines.append(
            f"{label} | scope={scope} | expires={iso_z(expires)} | "
            f"{args.base}/?c={token}"
        )

    codes_path = Path(args.codes)
    if args.merge and codes_path.exists():
        existing = json.loads(codes_path.read_text())
        entries = existing + entries
    codes_path.write_text(json.dumps(entries, indent=2) + "\n")

    out_path = Path(args.out)
    out_path.write_text("\n".join(lines) + "\n")

    for e in entries:
        print(f"scope={e['scope']} expires={e['expires']}")
    print(f"codes.json: {codes_path} ({len(entries)} entries, hashes only)")
    print(f"plain links: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
