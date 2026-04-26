from __future__ import annotations

import json
from pathlib import Path


def list_samples(batch_dir: Path) -> list[Path]:
    if not batch_dir.exists():
        return []
    return [p for p in sorted(batch_dir.glob("sample_*")) if p.is_dir()]


def load_sample_info(sample_dir: Path) -> dict:
    info_path = sample_dir / "info.json"
    if not info_path.exists():
        return {}
    return json.loads(info_path.read_text(encoding="utf-8"))


def sample_image_paths(sample_dir: Path) -> dict[str, Path]:
    img_dir = sample_dir / "images"
    out: dict[str, Path] = {}
    for name in ("low_energy.png", "high_energy.png", "r_map.png", "preview_rgb.png"):
        p = img_dir / name
        if p.exists():
            out[name] = p
    return out
