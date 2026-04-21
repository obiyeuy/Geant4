#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build train/val/test dataset with physics features and R map."""

from __future__ import annotations

import argparse
import json
import random
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

try:
    from .physics import FlatField, compute_flat_field, compute_physics_maps, normalize_map, read_energy_matrix
except ImportError:
    from physics import FlatField, compute_flat_field, compute_physics_maps, normalize_map, read_energy_matrix


@dataclass
class SampleRecord:
    sample_id: str
    source_dir: str
    class_id: int
    split: str
    tensor_path: str
    t_low_path: str
    t_high_path: str
    r_map_path: str


def _discover_samples(raw_dir: Path) -> list[Path]:
    out: list[Path] = []
    for p in raw_dir.rglob("*"):
        if not p.is_dir():
            continue
        if not p.name.startswith("sample_"):
            continue
        if (p / "LowEnergy").exists() and (p / "HighEnergy").exists():
            out.append(p)
    return sorted(out)


def _infer_label(sample_dir: Path) -> int:
    info_path = sample_dir / "info.json"
    if info_path.exists():
        with info_path.open("r", encoding="utf-8") as f:
            info = json.load(f)
        if "class" in info:
            return int(info["class"])
        if "label" in info:
            return int(info["label"])
    name = sample_dir.name.lower()
    if "ore" in name:
        return 1
    if "waste" in name:
        return 0
    raise ValueError(f"Cannot infer class for sample: {sample_dir}")


def _split_samples(samples: list[Path], train_ratio: float, val_ratio: float, seed: int) -> dict[str, list[Path]]:
    shuffled = samples[:]
    random.Random(seed).shuffle(shuffled)
    n = len(shuffled)
    n_train = int(n * train_ratio)
    n_val = int(n * val_ratio)
    train = shuffled[:n_train]
    val = shuffled[n_train : n_train + n_val]
    test = shuffled[n_train + n_val :]
    return {"train": train, "val": val, "test": test}


def _save_sample_features(
    sample_dir: Path,
    out_root: Path,
    split: str,
    flat_field: FlatField,
    class_id: int,
    index: int,
) -> SampleRecord:
    low, high = read_energy_matrix(sample_dir)
    maps = compute_physics_maps(low, high, flat_field)

    # 训练输入采用 3 通道：T_low, T_high, R
    c0 = normalize_map(maps["t_low"])
    c1 = normalize_map(maps["t_high"])
    c2 = normalize_map(maps["r_map"])
    tensor = np.stack([c0, c1, c2], axis=0).astype(np.float32)  # [3, H, W]

    sample_id = f"{split}_{index:05d}"
    sample_out = out_root / split / f"class_{class_id}" / sample_id
    sample_out.mkdir(parents=True, exist_ok=True)

    tensor_path = sample_out / "input.npy"
    np.save(tensor_path, tensor)
    t_low_path = sample_out / "t_low.npy"
    t_high_path = sample_out / "t_high.npy"
    r_map_path = sample_out / "r_map.npy"
    np.save(t_low_path, maps["t_low"])
    np.save(t_high_path, maps["t_high"])
    np.save(r_map_path, maps["r_map"])

    return SampleRecord(
        sample_id=sample_id,
        source_dir=str(sample_dir),
        class_id=class_id,
        split=split,
        tensor_path=str(tensor_path),
        t_low_path=str(t_low_path),
        t_high_path=str(t_high_path),
        r_map_path=str(r_map_path),
    )


def build_dataset(
    raw_dir: Path,
    blank_dir: Path,
    out_dir: Path,
    train_ratio: float,
    val_ratio: float,
    seed: int,
) -> None:
    samples = _discover_samples(raw_dir)
    if not samples:
        raise RuntimeError(f"No sample folders found under: {raw_dir}")

    splits = _split_samples(samples, train_ratio=train_ratio, val_ratio=val_ratio, seed=seed)
    flat_field = compute_flat_field(blank_dir)

    records: list[SampleRecord] = []
    for split_name, split_samples in splits.items():
        for idx, sample_dir in enumerate(split_samples):
            class_id = _infer_label(sample_dir)
            record = _save_sample_features(sample_dir, out_dir, split_name, flat_field, class_id, idx)
            records.append(record)

    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "raw_dir": str(raw_dir),
        "blank_dir": str(blank_dir),
        "num_samples": len(samples),
        "splits": {k: len(v) for k, v in splits.items()},
        "records": [asdict(r) for r in records],
    }
    with (out_dir / "manifest.json").open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    print("Dataset build completed.")
    print(f"Output: {out_dir}")
    print(f"Split counts: {manifest['splits']}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build R-value dataset for training")
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw"), help="Raw sample root")
    parser.add_argument(
        "--blank-dir",
        type=Path,
        default=Path("data/raw/output_blank"),
        help="Blank scan folder containing LowEnergy/HighEnergy",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("data/processed/r_value_dataset"),
        help="Output dataset root",
    )
    parser.add_argument("--train-ratio", type=float, default=0.7)
    parser.add_argument("--val-ratio", type=float, default=0.15)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    build_dataset(
        raw_dir=args.raw_dir,
        blank_dir=args.blank_dir,
        out_dir=args.out_dir,
        train_ratio=args.train_ratio,
        val_ratio=args.val_ratio,
        seed=args.seed,
    )


if __name__ == "__main__":
    main()
