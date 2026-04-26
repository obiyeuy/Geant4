from __future__ import annotations

import json
from pathlib import Path


def load_sorting_report(report_path: Path) -> dict:
    if not report_path.exists():
        return {}
    return json.loads(report_path.read_text(encoding="utf-8"))


def flatten_splits(report: dict) -> list[dict]:
    rows: list[dict] = []
    for split in ("train", "val", "test"):
        block = report.get(split)
        if not isinstance(block, dict):
            continue
        rows.append(
            {
                "split": split,
                "n": int(block.get("n", 0)),
                "accuracy": float(block.get("accuracy", 0.0)),
                "precision": float(block.get("precision", 0.0)),
                "recall": float(block.get("recall", 0.0)),
                "f1": float(block.get("f1", 0.0)),
                "tp": int(block.get("tp", 0)),
                "tn": int(block.get("tn", 0)),
                "fp": int(block.get("fp", 0)),
                "fn": int(block.get("fn", 0)),
            }
        )
    return rows
