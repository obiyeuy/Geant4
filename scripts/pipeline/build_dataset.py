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
    grade_value: float
    grade_type: str
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


def _load_grade_info(sample_dir: Path) -> tuple[float, str]:
    info_path = sample_dir / "info.json"
    grade_type = "unknown_wt%"
    grade_value = 0.0
    if info_path.exists():
        with info_path.open("r", encoding="utf-8") as f:
            info = json.load(f)
        if "grade_value" in info:
            grade_value = float(info["grade_value"])
        if "grade_type" in info:
            grade_type = str(info["grade_type"])
        elif "target_material" in info:
            # 兼容缺失 grade_type 的样本：沿用当前约定（按目标矿物质量百分比定义）
            grade_type = f"{info['target_material']}_wt%"
        # 兼容旧版样本元数据。
        elif "pbs_mass_percent" in info:
            grade_value = float(info["pbs_mass_percent"])
            grade_type = "PbS_wt%"
        elif "pb_mass_percent" in info:
            grade_value = float(info["pb_mass_percent"])
            grade_type = "Pb_wt%"
    return grade_value, grade_type


def _derive_binary_label(grade_value: float, label_threshold: float) -> int:
    return 1 if grade_value >= label_threshold else 0


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
    grade_value: float,
    grade_type: str,
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
        grade_value=grade_value,
        grade_type=grade_type,
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
    label_threshold: float,
) -> None:
    samples = _discover_samples(raw_dir)
    if not samples:
        raise RuntimeError(f"No sample folders found under: {raw_dir}")

    splits = _split_samples(samples, train_ratio=train_ratio, val_ratio=val_ratio, seed=seed)
    flat_field = compute_flat_field(blank_dir)

    records: list[SampleRecord] = []
    for split_name, split_samples in splits.items():
        for idx, sample_dir in enumerate(split_samples):
            grade_value, grade_type = _load_grade_info(sample_dir)
            class_id = _derive_binary_label(grade_value, label_threshold=label_threshold)
            record = _save_sample_features(
                sample_dir,
                out_dir,
                split_name,
                flat_field,
                class_id,
                grade_value,
                grade_type,
                idx,
            )
            records.append(record)

    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "raw_dir": str(raw_dir),
        "blank_dir": str(blank_dir),
        "num_samples": len(samples),
        "splits": {k: len(v) for k, v in splits.items()},
        "label_policy": {
            "task": "binary_classification",
            "rule": "class=1 if grade_value >= threshold else 0",
            "grade_type": "from_sample_info",
            "threshold": label_threshold,
        },
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
    parser.add_argument(
        "--label-threshold",
        type=float,
        default=0.5,
        help="Binary threshold in percent for class derivation",
    )
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
        label_threshold=args.label_threshold,
    )


if __name__ == "__main__":
    main()
