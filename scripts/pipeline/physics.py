#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Physics feature extraction utilities for dual-energy data."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Tuple

import numpy as np


EPS = 1e-6
BIX_OFFSET = 10.0
R_SMOOTH = 5e-2
NUM_PIXELS = 128


@dataclass
class FlatField:
    low: np.ndarray
    high: np.ndarray


def _sorted_bin_files(folder: Path) -> list[Path]:
    files = list(folder.glob("*.bin"))
    return sorted(files, key=lambda p: float(p.stem))


def read_energy_matrix(sample_dir: Path) -> Tuple[np.ndarray, np.ndarray]:
    """
    Load LowEnergy / HighEnergy .bin files into 2D arrays.

    Returns:
        low, high with shape [n_positions, 128].
    """
    low_dir = sample_dir / "LowEnergy"
    high_dir = sample_dir / "HighEnergy"
    if not low_dir.exists() or not high_dir.exists():
        raise FileNotFoundError(f"Missing energy folders in sample: {sample_dir}")

    low_files = _sorted_bin_files(low_dir)
    if not low_files:
        raise FileNotFoundError(f"No LowEnergy .bin files under: {low_dir}")

    rows_low = []
    rows_high = []
    for low_file in low_files:
        high_file = high_dir / low_file.name
        if not high_file.exists():
            continue
        low = np.fromfile(low_file, dtype=np.float64)
        high = np.fromfile(high_file, dtype=np.float64)
        if low.size != NUM_PIXELS or high.size != NUM_PIXELS:
            continue
        rows_low.append(low)
        rows_high.append(high)

    if not rows_low:
        raise RuntimeError(f"No valid matched rows in sample: {sample_dir}")
    return np.asarray(rows_low, dtype=np.float32), np.asarray(rows_high, dtype=np.float32)


def compute_flat_field(blank_dir: Path) -> FlatField:
    """Build flat field vector from blank scan folder."""
    low, high = read_energy_matrix(blank_dir)
    return FlatField(
        low=np.mean(low, axis=0).astype(np.float32),
        high=np.mean(high, axis=0).astype(np.float32),
    )


def compute_physics_maps(
    low_ore: np.ndarray,
    high_ore: np.ndarray,
    flat_field: FlatField,
) -> dict[str, np.ndarray]:
    """Compute transmission, attenuation and R map."""
    t_low = (low_ore + BIX_OFFSET) / (flat_field.low[None, :] + BIX_OFFSET)
    t_high = (high_ore + BIX_OFFSET) / (flat_field.high[None, :] + BIX_OFFSET)

    a_low = -np.log(np.clip(t_low, EPS, 1.0))
    a_high = -np.log(np.clip(t_high, EPS, 1.0))
    r_map = (np.abs(a_low) + R_SMOOTH) / (np.abs(a_high) + R_SMOOTH)

    return {
        "t_low": t_low.astype(np.float32),
        "t_high": t_high.astype(np.float32),
        "a_low": a_low.astype(np.float32),
        "a_high": a_high.astype(np.float32),
        "r_map": r_map.astype(np.float32),
    }


def normalize_map(arr: np.ndarray, low_q: float = 0.01, high_q: float = 0.99) -> np.ndarray:
    """Robust normalize a map to [0, 1] by quantiles."""
    lo = float(np.quantile(arr, low_q))
    hi = float(np.quantile(arr, high_q))
    if hi <= lo:
        return np.zeros_like(arr, dtype=np.float32)
    return np.clip((arr - lo) / (hi - lo), 0.0, 1.0).astype(np.float32)
