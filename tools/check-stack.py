#!/usr/bin/env python3
"""Check that design/STACK.md agrees with what Cargo resolved.

Purpose: every crate row of design/STACK.md names the version that Cargo.lock holds. A crate that
no workspace member uses yet is not in Cargo.lock; its row must then equal the exact `=` pin in
the root Cargo.toml `[workspace.dependencies]`. Every workspace dependency must have a row.
Rows that are not crates (rustc, Inter, Bitwig Studio, ...) are skipped by name.

Usage: python3 tools/check-stack.py
Exit: 0 when everything agrees; 1 printing one line per mismatch.
"""

import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NOT_CRATES = {
    "rustc", "cargo", "rustfmt", "clippy", "Inter", "clap-validator", "Bitwig Studio", "git",
    "python3", "macOS",
}


def stack_rows(text):
    """(name, version) of each row of the first table whose header starts with | Name | Version |."""
    rows, in_table = [], False
    for line in text.splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if line.startswith("| Name | Version |"):
            in_table = True
        elif in_table and line.startswith("|---"):
            continue
        elif in_table and line.startswith("|"):
            rows.append((cells[0], cells[1]))
        elif in_table:
            break
    return rows


def main():
    rows = stack_rows((ROOT / "design" / "STACK.md").read_text(encoding="utf-8"))
    lock = tomllib.loads((ROOT / "Cargo.lock").read_text(encoding="utf-8"))
    manifest = tomllib.loads((ROOT / "Cargo.toml").read_text(encoding="utf-8"))

    locked = {}
    for package in lock.get("package", []):
        locked.setdefault(package["name"], set()).add(package["version"])
    pins = {}
    for name, spec in manifest.get("workspace", {}).get("dependencies", {}).items():
        version = spec if isinstance(spec, str) else spec.get("version", "")
        pins[name] = version

    mismatches = []
    crate_rows = {name: version for name, version in rows if name not in NOT_CRATES}
    if not crate_rows:
        mismatches.append("design/STACK.md: no crate rows found in the | Name | Version | table")
    for name, version in crate_rows.items():
        if name in locked:
            if version not in locked[name]:
                found = ", ".join(sorted(locked[name]))
                mismatches.append(f"{name}: design/STACK.md says {version}, Cargo.lock has {found}")
        elif name in pins:
            if pins[name] != f"={version}":
                mismatches.append(
                    f"{name}: design/STACK.md says {version}, Cargo.toml pins {pins[name]!r}"
                )
        else:
            mismatches.append(f"{name}: design/STACK.md says {version}, but it is neither in "
                              "Cargo.lock nor in [workspace.dependencies]")
    # A pin that differs from its row shows up above: an `=` pin decides the locked version.
    for name, pin in pins.items():
        if name not in crate_rows:
            mismatches.append(f"{name}: pinned {pin!r} in Cargo.toml but has no design/STACK.md row")

    for line in mismatches:
        print(line)
    return 1 if mismatches else 0


if __name__ == "__main__":
    sys.exit(main())
