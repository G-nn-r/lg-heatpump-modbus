"""Tests for converting JSON snapshots into a CSV file."""

from __future__ import annotations

import csv
import importlib.util
import json
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "script" / "json_to_csv.py"


def _load() -> object:
    """Import the CSV conversion helper as a module."""
    spec = importlib.util.spec_from_file_location("lg_snapshot_csv", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_collect_rows_and_write_csv(tmp_path: Path) -> None:
    module = _load()
    snapshot_dir = tmp_path / "snapshots"
    snapshot_dir.mkdir()

    for index, timestamp in enumerate(["2024-01-01T00:00:00Z", "2024-01-01T00:05:00Z"]):
        payload = {
            "timestamp": timestamp,
            "model": "therma_v",
            "unit_id": 1,
            "elapsed_ms": 123.4 + index,
            "modbus_reads": 7,
            "failed": {"sensor_block": "timeout"} if index else {},
            "components": {
                "sensors": {"outdoor_temperature": -4.2 + index, "error_code": 42},
                "controls": {"dhw_target_temperature": 55.0},
            },
            "derived": {"compressor_speed": 3720 + index},
        }
        (snapshot_dir / f"snapshot-{index}.json").write_text(
            json.dumps(payload), encoding="utf-8"
        )

    rows = module.collect_rows(snapshot_dir)
    assert len(rows) == 2
    assert "components.sensors.outdoor_temperature" in rows[0]
    assert rows[0]["components.sensors.outdoor_temperature"] == -4.2
    assert rows[0]["derived.compressor_speed"] == 3720

    output = tmp_path / "out.csv"
    written = module.write_csv(rows, output)
    assert written == output
    with output.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        records = list(reader)
    assert len(records) == 2
    assert records[0]["model"] == "therma_v"
    assert records[0]["components.sensors.outdoor_temperature"] == "-4.2"
    assert records[1]["derived.compressor_speed"] == "3721"


def test_cli_writes_csv(tmp_path: Path) -> None:
    module = _load()
    snapshot_dir = tmp_path / "snapshots"
    snapshot_dir.mkdir()
    payload = {
        "timestamp": "2024-01-02T10:00:00Z",
        "model": "therma_v",
        "unit_id": 3,
        "components": {"sensors": {"outdoor_temperature": 10.1}},
        "derived": {"backup_heater_steps": 2},
    }
    (snapshot_dir / "one.json").write_text(json.dumps(payload), encoding="utf-8")

    output = tmp_path / "snapshot.csv"
    rc = module.main(["--input-dir", str(snapshot_dir), "--output", str(output)])

    assert rc == 0
    assert output.is_file()
    assert "components.sensors.outdoor_temperature" in output.read_text(encoding="utf-8")
