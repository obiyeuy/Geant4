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


def _normalize_masked(arr: np.ndarray, mask: np.ndarray, low_q: float = 0.01, high_q: float = 0.99) -> np.ndarray:
    """Normalize by quantiles computed only on masked pixels."""
    if mask is None or mask.size == 0 or not np.any(mask):
        return normalize_map(arr, low_q=low_q, high_q=high_q)
    v = arr[mask]
    lo = float(np.quantile(v, low_q))
    hi = float(np.quantile(v, high_q))
    if hi <= lo:
        return np.zeros_like(arr, dtype=np.float32)
    return np.clip((arr - lo) / (hi - lo), 0.0, 1.0).astype(np.float32)


def _to_u8_masked(arr: np.ndarray, mask: np.ndarray) -> np.ndarray:
    norm = _normalize_masked(arr, mask)
    out = np.clip(norm * 255.0, 0, 255).astype(np.uint8)
    if mask is not None and mask.shape == out.shape:
        out = out.copy()
        out[~mask] = 0
    return out


def _save_mask_png(mask: np.ndarray, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray((mask.astype(np.uint8) * 255), mode="L").save(out_path)


def _save_mask_preview(mask: np.ndarray, out_path: Path, scale: int = 4) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.fromarray((mask.astype(np.uint8) * 255), mode="L")
    img = img.resize((img.width * scale, img.height * scale), resample=Image.Resampling.NEAREST)
    img.save(out_path)


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


def _otsu_threshold(u8: np.ndarray) -> int:
    """Otsu threshold for uint8 2D image."""
    hist = np.bincount(u8.reshape(-1), minlength=256).astype(np.float64)
    total = hist.sum()
    if total <= 0:
        return 128
    prob = hist / total
    omega = np.cumsum(prob)
    mu = np.cumsum(prob * np.arange(256))
    mu_t = mu[-1]
    denom = omega * (1.0 - omega)
    denom[denom <= 1e-12] = np.nan
    sigma_b2 = (mu_t * omega - mu) ** 2 / denom
    t = int(np.nanargmax(sigma_b2))
    return max(0, min(255, t))


def _largest_component(mask: np.ndarray) -> np.ndarray:
    """Keep only the largest connected component (8-connectivity if available)."""
    try:
        from scipy import ndimage as ndi  # type: ignore

        structure = np.ones((3, 3), dtype=np.uint8)
        labeled, n = ndi.label(mask.astype(np.uint8), structure=structure)
        if n <= 1:
            return mask
        sizes = np.bincount(labeled.reshape(-1))
        sizes[0] = 0
        keep = int(np.argmax(sizes))
        return labeled == keep
    except Exception:
        return mask


def _build_ore_mask_from_high(high: np.ndarray) -> np.ndarray:
    """Segment ore region using high-energy preview intensity (dark object on bright background)."""
    u8 = _to_u8(high)
    t = _otsu_threshold(u8)
    mask = u8 < t
    mask = _largest_component(mask)
    if float(mask.mean()) < 0.01:
        # fallback if Otsu fails (e.g., mostly background)
        mask = u8 < min(240, t + 30)
        mask = _largest_component(mask)
    return mask


def _median_denoise(arr: np.ndarray, size: int = 3) -> np.ndarray:
    try:
        from scipy import ndimage as ndi  # type: ignore

        return ndi.median_filter(arr, size=size)
    except Exception:
        return arr


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
    ore_mask = _build_ore_mask_from_high(high)

    images_dir = sample_dir / "images"
    _save_gray_png(low, images_dir / "low_energy.png")
    _save_gray_png(high, images_dir / "high_energy.png")
    _save_gray_png(r_map, images_dir / "r_map.png")
    _save_gray_preview(low, images_dir / "low_energy_vis_x4.png")
    _save_gray_preview(high, images_dir / "high_energy_vis_x4.png")
    _save_gray_preview(r_map, images_dir / "r_map_vis_x4.png")

    _save_mask_png(ore_mask, images_dir / "ore_mask.png")
    _save_mask_preview(ore_mask, images_dir / "ore_mask_vis_x4.png")

    # Masked R-map preview: normalize using only ore pixels, background forced to 0.
    r_u8_masked = _to_u8_masked(r_map, ore_mask)
    Image.fromarray(r_u8_masked, mode="L").save(images_dir / "r_map_masked.png")
    Image.fromarray(r_u8_masked, mode="L").resize(
        (r_u8_masked.shape[1] * 4, r_u8_masked.shape[0] * 4), resample=Image.Resampling.NEAREST
    ).save(images_dir / "r_map_masked_vis_x4.png")

    # Denoised R-map preview: median filter in attenuation domain before ratio.
    t_low = (low + BIX_OFFSET) / (flat_field.low[None, :] + BIX_OFFSET)
    t_high = (high + BIX_OFFSET) / (flat_field.high[None, :] + BIX_OFFSET)
    a_low = -np.log(np.clip(t_low, EPS, 1.0))
    a_high = -np.log(np.clip(t_high, EPS, 1.0))
    a_low_f = _median_denoise(a_low, size=3)
    a_high_f = _median_denoise(a_high, size=3)
    r_denoised = (np.abs(a_low_f) + 5e-2) / (np.abs(a_high_f) + 5e-2)
    r_u8_denoised = _to_u8_masked(r_denoised, ore_mask)
    Image.fromarray(r_u8_denoised, mode="L").save(images_dir / "r_map_denoised.png")
    Image.fromarray(r_u8_denoised, mode="L").resize(
        (r_u8_denoised.shape[1] * 4, r_u8_denoised.shape[0] * 4), resample=Image.Resampling.NEAREST
    ).save(images_dir / "r_map_denoised_vis_x4.png")

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

