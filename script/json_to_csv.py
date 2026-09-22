#!/usr/bin/env python3

"""Convert dumped JSON snapshots into a single CSV file."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any


def _flatten(value: Any, prefix: str = "") -> dict[str, Any]:
    """Flatten nested mappings into a single dictionary of dot-qualified keys."""
    if not isinstance(value, dict):
        return {prefix: value} if prefix else {}

    flattened: dict[str, Any] = {}
    for key, child in value.items():
        path = f"{prefix}.{key}" if prefix else str(key)
        if isinstance(child, dict):
            flattened.update(_flatten(child, path))
        elif isinstance(child, list):
            flattened[path] = json.dumps(child, sort_keys=True)
        else:
            flattened[path] = child
    return flattened


def _csv_value(value: Any) -> Any:
    """Convert complex CSV values to textual form for writing."""
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, sort_keys=True)
    return value


def _read_snapshot(path: Path) -> dict[str, Any]:
    """Read a JSON snapshot from disk."""
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"Snapshot {path} does not contain a JSON object")
    return payload


def collect_rows(input_dir: str | Path) -> list[dict[str, Any]]:
    """Collect all snapshot objects from JSON files in a directory."""
    directory = Path(input_dir)
    files = sorted(path for path in directory.rglob("*.json") if path.is_file())
    if not files:
        raise FileNotFoundError(f"No JSON snapshot files found in {directory}")

    rows: list[dict[str, Any]] = []
    for path in files:
        rows.append(_flatten(_read_snapshot(path)))
    return rows


def write_csv(rows: list[dict[str, Any]], output_path: str | Path) -> Path:
    """Write flattened snapshots to a CSV file."""
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)

    fieldnames: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for name in row:
            if name not in seen:
                seen.add(name)
                fieldnames.append(name)

    with target.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: _csv_value(row.get(key, "")) for key in fieldnames})

    return target


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments for the snapshot conversion script."""
    parser = argparse.ArgumentParser(
        description="Read all JSON snapshots in a directory and combine them in one CSV."
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        required=True,
        help="Directory containing JSON snapshot files.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="CSV file to write.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Run the CSV conversion script."""
    args = _parse_args(argv)
    try:
        rows = collect_rows(args.input_dir)
        target = write_csv(rows, args.output)
    except (FileNotFoundError, ValueError, OSError) as err:
        print(f"Error: {err}", file=sys.stderr)
        return 1

    print(f"Wrote {len(rows)} snapshot rows to {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
