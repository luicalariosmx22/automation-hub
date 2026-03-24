"""Scan repository for environment variable usage.

This helper walks all ``.py`` files collecting the names passed to
``os.getenv`` so we can build a canonical inventory of tokens/variables in
use.  It prints a simple table and optionally writes a JSON report with the
list of files per variable.  This is the foundation for homogenizing config
management across the Automation Hub platform.

Usage:

    python scripts/env_inventory.py
    python scripts/env_inventory.py --json reports/env_usage.json

"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Dict, List

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_PATTERN = re.compile(r"os\.getenv\(\s*['\"]([A-Za-z0-9_]+)['\"]")


def scan_files() -> Dict[str, List[str]]:
    """Return mapping env_var -> sorted list of files referencing it."""

    mapping: Dict[str, set[str]] = {}
    for path in PROJECT_ROOT.rglob("*.py"):
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            continue

        for match in ENV_PATTERN.finditer(text):
            env_var = match.group(1)
            rel = path.relative_to(PROJECT_ROOT).as_posix()
            mapping.setdefault(env_var, set()).add(rel)

    return {key: sorted(files) for key, files in mapping.items()}


def print_table(mapping: Dict[str, List[str]]) -> None:
    """Print textual table sorted by variable name."""

    header = f"{'ENV_VAR':30} | #FILES"
    sep = "-" * len(header)
    print(header)
    print(sep)
    for key in sorted(mapping):
        print(f"{key:30} | {len(mapping[key])}")


def write_json(mapping: Dict[str, List[str]], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    data = {key: {"count": len(files), "files": files} for key, files in mapping.items()}
    output.write_text(json.dumps(data, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Inventory os.getenv usage")
    parser.add_argument("--json", dest="json_path", help="Optional JSON output path")
    args = parser.parse_args()

    mapping = scan_files()
    print_table(mapping)

    if args.json_path:
        write_json(mapping, Path(args.json_path))
        print(f"\nJSON report written to {args.json_path}")


if __name__ == "__main__":
    main()
