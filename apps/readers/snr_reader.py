from __future__ import annotations

import json
from pathlib import Path


def load_snr_summary(summary_path: Path) -> dict:
    if not summary_path.exists():
        return {}
    return json.loads(summary_path.read_text(encoding="utf-8"))


def load_snr_reports(snr_batch_dir: Path) -> list[dict]:
    if not snr_batch_dir.exists():
        return []
    rows: list[dict] = []
    for p in sorted(snr_batch_dir.glob("*_snr.json")):
        data = json.loads(p.read_text(encoding="utf-8"))
        low = data.get("low", {})
        high = data.get("high", {})
        passes = data.get("pass", {})
        rows.append(
            {
                "sample_dir": data.get("sample_dir", ""),
                "sample_name": Path(data.get("sample_dir", "")).name,
                "low_snr": float(low.get("snr", 0.0)),
                "high_snr": float(high.get("snr", 0.0)),
                "low_half_fwhm_over_mean": float(low.get("half_fwhm_over_mean", 0.0)),
                "high_half_fwhm_over_mean": float(high.get("half_fwhm_over_mean", 0.0)),
                "pass_half_fwhm": bool(passes.get("half_fwhm_over_mean", False)),
                "pass_half66": bool(passes.get("half66_over_full_scale", False)),
                "beam_factor_est": float(data.get("estimated_beam_factor_to_meet_half_fwhm", 0.0)),
            }
        )
    return rows
