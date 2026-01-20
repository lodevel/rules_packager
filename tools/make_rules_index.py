#!/usr/bin/env python3
"""Generate rules_index.json with SHA-256 checksums for .md files in a rules version folder.

Writes to:
  src/rules_packager/rules/rules_index.json

Usage:
  python tools/make_rules_index.py            # auto-detect latest version
  python tools/make_rules_index.py 0.5.0      # explicitly choose version
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
RULES_ROOT = ROOT / "src" / "rules_packager" / "rules"


def _sha256(fp: pathlib.Path) -> str:
    h = hashlib.sha256()
    with open(fp, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _version_key(s: str):
    # Natural sort: 0.10.0 > 0.9.0
    return [int(x) if x.isdigit() else x for x in re.split(r"(\d+)", s)]


def _detect_latest_version() -> str:
    vers = [p.name for p in RULES_ROOT.iterdir() if p.is_dir()]
    if not vers:
        raise SystemExit(f"No rules versions found in: {RULES_ROOT}")
    return sorted(vers, key=_version_key)[-1]


def main() -> None:
    ver = sys.argv[1] if len(sys.argv) > 1 else _detect_latest_version()
    version_dir = RULES_ROOT / ver

    if not version_dir.exists():
        raise SystemExit(f"Error: Rules folder not found: {version_dir}")

    files = sorted(
        [p for p in version_dir.iterdir() if p.is_file() and p.suffix == ".md"],
        key=lambda p: p.name,
    )

    idx = {
        "driver_version": ver,
        "rules_version": ver,
        "files": [{"name": f.name, "sha256": _sha256(f)} for f in files],
    }

    out_path = RULES_ROOT / "rules_index.json"
    out_path.write_text(json.dumps(idx, indent=2), encoding="utf-8")
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
