#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Evaluate Gaussian noise and SNR criteria on blank-like columns."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from scipy.stats import norm

from pipeline.physics import compute_flat_field, read_energy_matrix


def _pick_blank_columns(low: np.ndarray, high: np.ndarray, ff_low: np.ndarray, ff_high: np.ndarray) -> np.ndarray:
    t_low = low / np.clip(ff_low[None, :], 1e-9, None)
    t_high = high / np.clip(ff_high[None, :], 1e-9, None)
    med_t = np.median((t_low + t_high) * 0.5, axis=0)
    q = np.quantile(med_t, 0.75)
    cols = np.where(med_t >= q)[0]
    if cols.size < 16:
        cols = np.argsort(med_t)[-16:]
    return cols


def _channel_metrics(x: np.ndarray, full_scale: float) -> dict[str, float]:
    mu = float(np.mean(x))
    sigma = float(np.std(x, ddof=1))
    fwhm = 2.354820045 * sigma
    half_fwhm = 0.5 * fwhm
    half_66 = 0.9541652531461944 * sigma
    snr = mu / max(sigma, 1e-12)

    z = (x - mu) / max(sigma, 1e-12)
    cov = {}
    for p in (0.33, 0.66, 0.99):
        z_req = norm.ppf((1.0 + p) / 2.0)
        cov[str(int(p * 100))] = float(np.mean(np.abs(z) <= z_req))

    return {
        "mu": mu,
        "sigma": sigma,
        "snr": snr,
        "half_fwhm": half_fwhm,
        "half_fwhm_over_mean": half_fwhm / max(mu, 1e-12),
        "half_66": half_66,
        "half_66_over_full_scale": half_66 / max(full_scale, 1e-12),
        "cov33": cov["33"],
        "cov66": cov["66"],
        "cov99": cov["99"],
    }


def evaluate(sample_dir: Path, blank_dir: Path, full_scale: float, target_ratio: float) -> dict:
    low, high = read_energy_matrix(sample_dir)
    ff = compute_flat_field(blank_dir)

    cols = _pick_blank_columns(low, high, ff.low, ff.high)
    t_low = low / np.clip(ff.low[None, :], 1e-9, None)
    t_high = high / np.clip(ff.high[None, :], 1e-9, None)
    x_low = t_low[:, cols].reshape(-1)
    x_high = t_high[:, cols].reshape(-1)

    low_m = _channel_metrics(x_low, full_scale=full_scale)
    high_m = _channel_metrics(x_high, full_scale=full_scale)
    worst_half_fwhm_ratio = max(low_m["half_fwhm_over_mean"], high_m["half_fwhm_over_mean"])
    worst_half66_fs = max(low_m["half_66_over_full_scale"], high_m["half_66_over_full_scale"])

    scale = (worst_half_fwhm_ratio / max(target_ratio, 1e-12)) ** 2
    estimated_beam_factor = float(max(scale, 1.0))

    return {
        "sample_dir": str(sample_dir),
        "blank_columns": cols.tolist(),
        "criteria": {
            "target_half_fwhm_over_mean": target_ratio,
            "target_half66_over_full_scale": 0.01,
            "gaussian_central_targets": {"33": 0.33, "66": 0.66, "99": 0.99},
        },
        "low": low_m,
        "high": high_m,
        "pass": {
            "half_fwhm_over_mean": worst_half_fwhm_ratio <= target_ratio,
            "half66_over_full_scale": worst_half66_fs <= 0.01,
        },
        "estimated_beam_factor_to_meet_half_fwhm": estimated_beam_factor,
    }


def main() -> None:
    p = argparse.ArgumentParser(description="Evaluate blank-column Gaussian/SNR criteria.")
    p.add_argument("--sample-dir", type=Path, required=True)
    p.add_argument("--blank-dir", type=Path, required=True)
    p.add_argument("--full-scale", type=float, default=1.0, help="Gray full scale in transmission domain.")
    p.add_argument("--target-half-fwhm-over-mean", type=float, default=0.01)
    p.add_argument("--out-json", type=Path, default=None)
    args = p.parse_args()

    report = evaluate(
        sample_dir=args.sample_dir.resolve(),
        blank_dir=args.blank_dir.resolve(),
        full_scale=float(args.full_scale),
        target_ratio=float(args.target_half_fwhm_over_mean),
    )
    text = json.dumps(report, ensure_ascii=False, indent=2)
    print(text)
    if args.out_json is not None:
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        args.out_json.write_text(text + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

