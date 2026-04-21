#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render simulated dual-energy matrices into preview images."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image

from pipeline.physics import BIX_OFFSET, EPS, FlatField, compute_flat_field, normalize_map, read_energy_matrix


def _to_u8(arr: np.ndarray) -> np.ndarray:
    norm = normalize_map(arr)
    return np.clip(norm * 255.0, 0, 255).astype(np.uint8)


def _save_gray_png(arr: np.ndarray, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(_to_u8(arr), mode="L").save(out_path)


def _save_gray_preview(arr: np.ndarray, out_path: Path, scale: int = 4) -> None:
    """Save a nearest-neighbor upscaled preview for visual inspection."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.fromarray(_to_u8(arr), mode="L")
    img = img.resize((img.width * scale, img.height * scale), resample=Image.Resampling.NEAREST)
    img.save(out_path)


def _compute_r_map(low: np.ndarray, high: np.ndarray, flat_field: FlatField) -> np.ndarray:
    t_low = (low + BIX_OFFSET) / (flat_field.low[None, :] + BIX_OFFSET)
    t_high = (high + BIX_OFFSET) / (flat_field.high[None, :] + BIX_OFFSET)
    a_low = -np.log(np.clip(t_low, EPS, 1.0))
    a_high = -np.log(np.clip(t_high, EPS, 1.0))
    return (np.abs(a_low) + 5e-2) / (np.abs(a_high) + 5e-2)


def render_sample_images(sample_dir: Path, flat_field: FlatField) -> Path:
    """
    Render low/high/R maps as PNG images under raw sample folder.

    Output folder:
      <sample_dir>/images/
        - low_energy.png
        - high_energy.png
        - r_map.png
        - preview_rgb.png   (R=low, G=high, B=r)
    """
    low, high = read_energy_matrix(sample_dir)
    r_map = _compute_r_map(low, high, flat_field)

    images_dir = sample_dir / "images"
    _save_gray_png(low, images_dir / "low_energy.png")
    _save_gray_png(high, images_dir / "high_energy.png")
    _save_gray_png(r_map, images_dir / "r_map.png")
    _save_gray_preview(low, images_dir / "low_energy_vis_x4.png")
    _save_gray_preview(high, images_dir / "high_energy_vis_x4.png")
    _save_gray_preview(r_map, images_dir / "r_map_vis_x4.png")

    rgb = np.stack([_to_u8(low), _to_u8(high), _to_u8(r_map)], axis=-1)
    Image.fromarray(rgb, mode="RGB").save(images_dir / "preview_rgb.png")
    return images_dir


def render_batch_images(raw_root: Path, blank_dir: Path) -> tuple[int, int]:
    """Render all discovered samples under raw_root. Returns (ok, failed)."""
    flat_field = compute_flat_field(blank_dir)
    ok = 0
    failed = 0
    for sample_dir in sorted(raw_root.rglob("sample_*")):
        if not sample_dir.is_dir():
            continue
        try:
            render_sample_images(sample_dir, flat_field)
            ok += 1
        except Exception:
            failed += 1
    return ok, failed

