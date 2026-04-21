#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Select a global beamOn from SNR report JSON files."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np


def main() -> None:
    p = argparse.ArgumentParser(description="Compute global beamOn using SNR reports.")
    p.add_argument("--report-batch-dir", type=Path, required=True, help="Folder containing *_snr.json files.")
    p.add_argument("--base-beam-on", type=int, required=True, help="beamOn used to generate these reports.")
    p.add_argument("--target-half-fwhm-over-mean", type=float, default=0.01)
    p.add_argument("--percentile", type=float, default=0.90, help="Use P90/P95 etc, range (0,1].")
    p.add_argument("--safety-factor", type=float, default=1.10)
    p.add_argument("--out-json", type=Path, default=None)
    args = p.parse_args()

    files = sorted(args.report_batch_dir.glob("*_snr.json"))
    if not files:
        raise FileNotFoundError(f"No *_snr.json under: {args.report_batch_dir}")

    target = float(args.target_half_fwhm_over_mean)
    factors: list[float] = []
    rows: list[dict] = []
    for fp in files:
        data = json.loads(fp.read_text(encoding="utf-8"))
        worst_ratio = max(float(data["low"]["half_fwhm_over_mean"]), float(data["high"]["half_fwhm_over_mean"]))
        factor = max((worst_ratio / max(target, 1e-12)) ** 2, 1.0)
        factors.append(factor)
        rows.append(
            {
                "file": str(fp),
                "sample_dir": data.get("sample_dir", ""),
                "worst_half_fwhm_over_mean": worst_ratio,
                "beam_factor_needed": factor,
            }
        )

    pctl_factor = float(np.quantile(np.asarray(factors, dtype=np.float64), args.percentile))
    recommended = int(math.ceil(args.base_beam_on * pctl_factor * args.safety_factor))
    result = {
        "report_batch_dir": str(args.report_batch_dir.resolve()),
        "num_samples": len(files),
        "base_beam_on": int(args.base_beam_on),
        "target_half_fwhm_over_mean": target,
        "percentile": float(args.percentile),
        "safety_factor": float(args.safety_factor),
        "beam_factor_percentile": pctl_factor,
        "recommended_global_beam_on": recommended,
        "samples": rows,
    }
    text = json.dumps(result, ensure_ascii=False, indent=2)
    print(text)
    if args.out_json is not None:
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        args.out_json.write_text(text + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

