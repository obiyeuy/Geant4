#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unified orchestrator for full ore sorting workflow."""

from __future__ import annotations

import argparse
import re
import sys
import time
from datetime import datetime
from pathlib import Path


THIS_FILE = Path(__file__).resolve()
SCRIPTS_DIR = THIS_FILE.parents[1]
PROJECT_ROOT = THIS_FILE.parents[2]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from pipeline.stages import (  # noqa: E402
    PipelineConfig,
    build_r_dataset,
    evaluate_snr_for_samples,
    generate_samples,
    render_samples_to_images,
    simulate_blank,
    simulate_samples,
    train_model,
)

SAMPLE_NAME_RE = re.compile(r"^sample_(\d+)_")


def _default_geant_exec(project_root: Path) -> Path:
    candidates = [
        project_root / "build" / "CZT",
        project_root / "simulation" / "build" / "CZT",
        project_root / "simulation" / "CZT",
    ]
    for c in candidates:
        if c.exists():
            return c
    return candidates[0]


def _beam_on_tokens(beam_on: int) -> list[str]:
    tokens = [str(beam_on)]
    if beam_on % 1_000_000 == 0:
        tokens.append(f"{beam_on // 1_000_000}m")
        tokens.append(f"{beam_on // 1_000_000}M")
    if beam_on % 10_000 == 0:
        tokens.append(f"{beam_on // 10_000}w")
        tokens.append(f"{beam_on // 10_000}W")
    if beam_on % 1_000 == 0:
        tokens.append(f"{beam_on // 1_000}k")
        tokens.append(f"{beam_on // 1_000}K")
    return list(dict.fromkeys(tokens))


def _batch_id_tokens(batch_id: str) -> list[str]:
    # 示例： "single_800w_20260421" -> ["800w", "800W"]
    found = re.findall(r"(\d+\s*[wWkKmM])", batch_id)
    out: list[str] = []
    for token in found:
        t = token.replace(" ", "")
        out.extend([t, t.lower(), t.upper()])
    return list(dict.fromkeys(out))


def _looks_like_blank_dir(path: Path) -> bool:
    return path.is_dir() and (path / "LowEnergy").exists() and (path / "HighEnergy").exists()


def _resolve_sample_start_index(raw_root: Path, batch_id: str, requested_start: int) -> int:
    if requested_start >= 1:
        return requested_start
    # requested_start <= 0 means auto-append from existing max index
    batch_dir = raw_root / f"batch_{batch_id}"
    if not batch_dir.exists():
        return 1
    max_idx = 0
    for p in batch_dir.glob("sample_*"):
        if not p.is_dir():
            continue
        m = SAMPLE_NAME_RE.match(p.name)
        if not m:
            continue
        max_idx = max(max_idx, int(m.group(1)))
    return max_idx + 1


def _resolve_blank_dir(
    *,
    project_root: Path,
    raw_root: Path,
    blank_arg: Path,
    batch_id: str,
    beam_on: int,
) -> tuple[Path, list[Path]]:
    requested = blank_arg if blank_arg.is_absolute() else (project_root / blank_arg)
    raw_batch_dir = raw_root / f"batch_{batch_id}"
    batch_blank = raw_batch_dir / "blank"
    if _looks_like_blank_dir(batch_blank):
        return batch_blank.resolve(), [batch_blank.resolve()]
    if _looks_like_blank_dir(requested):
        return requested.resolve(), [requested.resolve()]

    tokens = _beam_on_tokens(beam_on) + _batch_id_tokens(batch_id)
    tokens = list(dict.fromkeys(tokens))

    candidates: list[Path] = []
    if requested.exists():
        candidates.append(requested)
    candidates.extend(
        [
            raw_root / "output_blank",
            raw_batch_dir / "output_blank",
            raw_batch_dir / "blank",
        ]
    )
    for token in tokens:
        candidates.extend(
            [
                raw_root / f"output_blank_{token}",
                raw_root / f"blank_{token}",
                raw_root / f"batch_blank_{token}",
                raw_root / f"batch_blank_single_{token}",
                raw_batch_dir / f"output_blank_{token}",
                raw_batch_dir / f"blank_{token}",
            ]
        )

    # 同时扫描已有 raw 目录中与 beam-on 标记匹配的空文件夹。
    matched_token_dirs: list[Path] = []
    for d in raw_root.iterdir():
        if not d.is_dir():
            continue
        name = d.name.lower()
        if "blank" not in name:
            continue
        if any(re.search(rf"(^|[_-]){re.escape(t.lower())}([_-]|$)", name) for t in tokens):
            matched_token_dirs.append(d)
        elif "batch" in batch_id and batch_id.lower() in name:
            matched_token_dirs.append(d)
    candidates.extend(sorted(matched_token_dirs))

    uniq: list[Path] = []
    seen: set[Path] = set()
    for c in candidates:
        rc = c.resolve()
        if rc in seen:
            continue
        seen.add(rc)
        uniq.append(rc)

    for c in uniq:
        if _looks_like_blank_dir(c):
            return c, uniq
    return requested.resolve(), uniq


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run full pipeline: generate -> blank -> simulate -> render -> snr -> build -> train")
    parser.add_argument(
        "--stages",
        nargs="+",
        default=["generate", "blank", "simulate", "render", "snr", "build", "train"],
        choices=["generate", "blank", "simulate", "render", "snr", "build", "train"],
        help="Stages to run in order",
    )

    parser.add_argument("--batch-id", type=str, default=datetime.now().strftime("%Y%m%d_%H%M%S"))
    parser.add_argument("--num-samples", type=int, default=30)
    parser.add_argument(
        "--sample-start-index",
        type=int,
        default=1,
        help="Start index for generated sample numbering. Use 0 to auto-append after existing max.",
    )
    parser.add_argument("--ore-ratio", type=float, default=0.5)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--matrix-material", type=str, default="G4_SILICON_DIOXIDE")
    parser.add_argument("--matrix-density", type=float, default=2.65, help="g/cm3")
    parser.add_argument("--target-material", type=str, default="G4_PbS")
    parser.add_argument("--target-density", type=float, default=7.6, help="g/cm3")
    parser.add_argument("--target-grade-min", type=float, default=0.0, help="target mineral wt%% min")
    parser.add_argument("--target-grade-max", type=float, default=20.0, help="target mineral wt%% max")
    parser.add_argument(
        "--randomize-seed",
        action="store_true",
        help="Use time-based seed for this run; otherwise --seed is used for deterministic replay.",
    )

    parser.add_argument("--raw-root", type=Path, default=Path("data/raw"))
    parser.add_argument("--processed-root", type=Path, default=Path("data/processed"))
    parser.add_argument("--experiments-root", type=Path, default=Path("experiments"))
    parser.add_argument("--blank-dir", type=Path, default=Path("data/raw/output_blank"))

    parser.add_argument("--geant-exec", type=Path, default=None)
    parser.add_argument("--simulation-root", type=Path, default=Path("simulation"))
    parser.add_argument("--master-macro", type=Path, default=Path("simulation/master.mac"))
    parser.add_argument("--beam-on", type=int, default=500000)
    parser.add_argument("--ore-mode", type=str, default="tessellated", choices=["tessellated", "csg"])
    parser.add_argument("--geometry-guard", action="store_true", default=True)
    parser.add_argument("--no-geometry-guard", action="store_false", dest="geometry_guard")
    parser.add_argument("--tess-max-retries", type=int, default=3)

    parser.add_argument("--train-ratio", type=float, default=0.7)
    parser.add_argument("--val-ratio", type=float, default=0.15)
    parser.add_argument(
        "--label-threshold",
        type=float,
        default=0.5,
        help="Binary threshold in percent for class derivation during build",
    )
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--num-workers", type=int, default=0)
    parser.add_argument(
        "--balance-mode",
        type=str,
        default="both",
        choices=["none", "class_weight", "sampler", "both"],
        help="Class balancing mode used when training EfficientNet.",
    )
    parser.add_argument("--snr-report-dir", type=Path, default=Path("experiments/snr_reports"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    geant_exec = args.geant_exec if args.geant_exec else _default_geant_exec(PROJECT_ROOT)
    resolved_seed = int(time.time_ns() % (2**32)) if args.randomize_seed else int(args.seed)
    resolved_sample_start = _resolve_sample_start_index(
        raw_root=(PROJECT_ROOT / args.raw_root).resolve(),
        batch_id=args.batch_id,
        requested_start=int(args.sample_start_index),
    )

    cfg = PipelineConfig(
        raw_root=(PROJECT_ROOT / args.raw_root).resolve(),
        processed_root=(PROJECT_ROOT / args.processed_root).resolve(),
        experiments_root=(PROJECT_ROOT / args.experiments_root).resolve(),
        blank_dir=Path(),
        batch_id=args.batch_id,
        num_samples=args.num_samples,
        sample_start_index=resolved_sample_start,
        ore_ratio=args.ore_ratio,
        seed=resolved_seed,
        matrix_material=args.matrix_material,
        matrix_density=args.matrix_density,
        target_material=args.target_material,
        target_density=args.target_density,
        target_grade_min=args.target_grade_min,
        target_grade_max=args.target_grade_max,
        geant_exec=(PROJECT_ROOT / geant_exec).resolve() if not geant_exec.is_absolute() else geant_exec,
        simulation_root=(PROJECT_ROOT / args.simulation_root).resolve(),
        master_macro=(PROJECT_ROOT / args.master_macro).resolve(),
        beam_on=args.beam_on,
        ore_mode=args.ore_mode,
        geometry_guard=args.geometry_guard,
        tess_max_retries=args.tess_max_retries,
        label_threshold=args.label_threshold,
        train_ratio=args.train_ratio,
        val_ratio=args.val_ratio,
        epochs=args.epochs,
        batch_size=args.batch_size,
        lr=args.lr,
        num_workers=args.num_workers,
        balance_mode=args.balance_mode,
    )

    if not cfg.geant_exec.exists() and ("simulate" in args.stages or "blank" in args.stages):
        raise FileNotFoundError(f"Geant executable not found: {cfg.geant_exec}")
    if not cfg.master_macro.exists() and ("simulate" in args.stages or "blank" in args.stages):
        raise FileNotFoundError(f"master macro not found: {cfg.master_macro}")
    if "blank" in args.stages:
        cfg.blank_dir = simulate_blank(cfg)

    blank_dir, tried_blank_dirs = _resolve_blank_dir(
        project_root=PROJECT_ROOT,
        raw_root=cfg.raw_root,
        blank_arg=args.blank_dir,
        batch_id=args.batch_id,
        beam_on=args.beam_on,
    )
    cfg.blank_dir = blank_dir
    if not cfg.blank_dir.exists() and ("render" in args.stages or "build" in args.stages):
        tried_text = "\n".join(f"- {p}" for p in tried_blank_dirs)
        raise FileNotFoundError(
            "Blank directory not found. "
            f"Requested: {cfg.blank_dir}\n"
            f"beam_on={cfg.beam_on}, batch_id={cfg.batch_id}\n"
            "Tried candidates:\n"
            f"{tried_text}"
        )
    if "render" in args.stages or "build" in args.stages:
        print(f"[pipeline] using blank_dir={cfg.blank_dir}")
    print(f"[pipeline] using seed={cfg.seed} (randomized={args.randomize_seed})")
    if "generate" in args.stages:
        print(f"[pipeline] generate sample_start_index={cfg.sample_start_index}")

    samples = []
    if "generate" in args.stages:
        samples = generate_samples(cfg)
    if "simulate" in args.stages:
        if not samples:
            samples = sorted((cfg.raw_root / f"batch_{cfg.batch_id}").glob("sample_*"))
        simulate_samples(cfg, samples)
    if "render" in args.stages:
        if not samples:
            samples = sorted((cfg.raw_root / f"batch_{cfg.batch_id}").glob("sample_*"))
        render_samples_to_images(cfg, samples)
    if "snr" in args.stages:
        if not samples:
            samples = sorted((cfg.raw_root / f"batch_{cfg.batch_id}").glob("sample_*"))
        snr_dir = (PROJECT_ROOT / args.snr_report_dir / f"batch_{cfg.batch_id}").resolve()
        evaluate_snr_for_samples(cfg, samples, snr_dir)

    dataset_root = cfg.processed_root / "r_value_dataset"
    if "build" in args.stages:
        dataset_root = build_r_dataset(cfg)

    if "train" in args.stages:
        train_out = train_model(cfg, dataset_root=dataset_root)
        print(f"[train] outputs -> {train_out}")

    print("[pipeline] completed")


if __name__ == "__main__":
    main()

