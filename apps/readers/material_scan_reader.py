from __future__ import annotations

import json
from pathlib import Path


def load_material_scan(scan_path: Path) -> list[dict]:
    if not scan_path.exists():
        return []
    payload = json.loads(scan_path.read_text(encoding="utf-8"))
    rows: list[dict] = []
    for material, items in payload.items():
        for triple in items:
            if len(triple) != 3:
                continue
            thickness, low_mean, high_mean = triple
            ratio = (float(low_mean) / float(high_mean)) if float(high_mean) != 0.0 else 0.0
            rows.append(
                {
                    "material": material,
                    "thickness_mm": float(thickness),
                    "low_mean": float(low_mean),
                    "high_mean": float(high_mean),
                    "ratio_lh": ratio,
                }
            )
    return rows
