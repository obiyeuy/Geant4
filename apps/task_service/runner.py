from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable


STAGE_ORDER = ["generate", "blank", "simulate", "render", "snr", "build", "train"]


def _prettify_line(*, project_root: Path, current_stage: str, raw_line: str) -> str:
    """
    Normalize log lines to be readable:
    - Replace long absolute paths with relative ones.
    - Add stage tag for lines without a prefix (e.g. messages from geometry generator).
    - Ensure a single trailing newline.
    """
    line = raw_line.rstrip("\n")
    root_str = str(project_root)
    if root_str and root_str in line:
        line = line.replace(root_str, ".")

    # collapse extremely noisy "File ..." absolute paths from some libs
    # Replace current user's absolute project paths; keep other /home paths intact.
    line = line.replace("/home/yyb/workspace/XRay-all/XRay-detectionCode", ".")

    stripped = line.lstrip()
    has_stage_prefix = stripped.startswith("[") and "]" in stripped[:32]
    if not has_stage_prefix:
        stage_tag = current_stage if current_stage else "log"
        tag = f"[{stage_tag}]"
        line = f"{tag} {line}"
    return line + "\n"


@dataclass
class RunResult:
    exit_code: int
    stage: str
    error_message: str
    artifact_index_path: Path


def _args_from_params(project_root: Path, params: dict, stages: list[str]) -> list[str]:
    # Use unbuffered stdout so logs and progress update in real time.
    cmd = [sys.executable, "-u", str(project_root / "scripts/pipeline/run_full_pipeline.py")]
    cmd.extend(["--stages", *stages])

    mappings = [
        ("batch_id", "--batch-id"),
        ("num_samples", "--num-samples"),
        ("sample_start_index", "--sample-start-index"),
        ("ore_ratio", "--ore-ratio"),
        ("seed", "--seed"),
        ("matrix_material", "--matrix-material"),
        ("matrix_density", "--matrix-density"),
        ("target_material", "--target-material"),
        ("target_density", "--target-density"),
        ("target_grade_min", "--target-grade-min"),
        ("target_grade_max", "--target-grade-max"),
        ("raw_root", "--raw-root"),
        ("processed_root", "--processed-root"),
        ("experiments_root", "--experiments-root"),
        ("blank_dir", "--blank-dir"),
        ("geant_exec", "--geant-exec"),
        ("simulation_root", "--simulation-root"),
        ("master_macro", "--master-macro"),
        ("beam_on", "--beam-on"),
        ("ore_mode", "--ore-mode"),
        ("tess_max_retries", "--tess-max-retries"),
        ("label_threshold", "--label-threshold"),
        ("train_ratio", "--train-ratio"),
        ("val_ratio", "--val-ratio"),
        ("epochs", "--epochs"),
        ("batch_size", "--batch-size"),
        ("lr", "--lr"),
        ("num_workers", "--num-workers"),
        ("balance_mode", "--balance-mode"),
        ("snr_report_dir", "--snr-report-dir"),
    ]

    for key, flag in mappings:
        val = params.get(key)
        if val is None or val == "":
            continue
        cmd.extend([flag, str(val)])

    if params.get("randomize_seed"):
        cmd.append("--randomize-seed")
    if params.get("geometry_guard", True):
        cmd.append("--geometry-guard")
    else:
        cmd.append("--no-geometry-guard")
    return cmd


def run_pipeline_job(
    project_root: Path,
    params: dict,
    stages: list[str],
    log_path: Path,
    artifact_index_path: Path,
    on_stage_update: Callable[[str, float], None],
) -> RunResult:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_index_path.parent.mkdir(parents=True, exist_ok=True)
    command = _args_from_params(project_root, params, stages)
    current_stage = ""
    err = ""

    with log_path.open("w", encoding="utf-8") as logf:
        logf.write("$ " + " ".join(command) + "\n")
        logf.flush()
        env = dict(os.environ)
        env["PYTHONUNBUFFERED"] = "1"
        proc = subprocess.Popen(
            command,
            cwd=str(project_root),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        assert proc.stdout is not None
        total_samples = int(params.get("num_samples") or 0) or None
        per_sample_re = re.compile(r"^\[(simulate|render)\]\s+\((\d+)\)")
        snr_re = re.compile(r"^\[snr\]\s+sample_")
        snr_seen = 0
        for line in proc.stdout:
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            s = line.strip()

            # Infer stage for pipeline lines like: "[pipeline] generate sample_start_index=1"
            if s.startswith("[pipeline] generate"):
                current_stage = "generate"
            elif s.startswith("[pipeline] using blank_dir="):
                # blank stage finished, next typically generate/simulate etc; keep as blank for readability
                if "blank" in stages:
                    current_stage = "blank"
            elif s.startswith("[build]"):
                current_stage = "build"
            elif s.startswith("[train]"):
                current_stage = "train"

            # Lines from generator often have no prefix; treat them as generate stage.
            if "生成" in s and "矿石模型" in s:
                current_stage = current_stage or "generate"

            pretty = _prettify_line(project_root=project_root, current_stage=current_stage, raw_line=line)
            logf.write(f"[{ts}] {pretty}")
            logf.flush()

            # Stage-level progress.
            for idx, stage in enumerate(STAGE_ORDER):
                if s.startswith(f"[{stage}]"):
                    current_stage = stage
                    on_stage_update(stage, float(idx / len(STAGE_ORDER)))
                    break
            # Within-stage progress (simulate/render) based on per-sample counter.
            m = per_sample_re.match(s)
            if m and total_samples:
                stage = m.group(1)
                done = int(m.group(2))
                idx = STAGE_ORDER.index(stage) if stage in STAGE_ORDER else 0
                base = idx / len(STAGE_ORDER)
                frac = min(max(done / max(total_samples, 1), 0.0), 1.0)
                on_stage_update(stage, min(base + frac / len(STAGE_ORDER), 0.999))
                current_stage = stage
                continue
            # Within-stage progress (snr) lines don't carry explicit counter; approximate with count seen.
            if snr_re.match(s) and total_samples:
                stage = "snr"
                idx = STAGE_ORDER.index(stage)
                base = idx / len(STAGE_ORDER)
                snr_seen += 1
                frac = min(max(snr_seen / max(total_samples, 1), 0.0), 1.0)
                on_stage_update(stage, min(base + frac / len(STAGE_ORDER), 0.999))
                current_stage = stage
        exit_code = int(proc.wait())
        if exit_code != 0:
            err = f"Process exited with code {exit_code}"

    artifacts = _collect_artifacts(project_root, params)
    artifact_index_path.write_text(json.dumps(artifacts, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return RunResult(
        exit_code=exit_code,
        stage=current_stage,
        error_message=err,
        artifact_index_path=artifact_index_path,
    )


def _collect_artifacts(project_root: Path, params: dict) -> dict:
    batch_id = str(params.get("batch_id", ""))
    raw_root = Path(str(params.get("raw_root", "data/raw")))
    experiments_root = Path(str(params.get("experiments_root", "experiments")))
    snr_dir = Path(str(params.get("snr_report_dir", "experiments/snr_reports")))
    artifacts = {
        "batch_dir": str((project_root / raw_root / f"batch_{batch_id}").resolve()),
        "snr_summary": str((project_root / snr_dir / f"batch_{batch_id}" / "summary.json").resolve()),
        "sorting_r_threshold": str(
            (project_root / experiments_root / "sorting_reports" / batch_id / "r_threshold_report.json").resolve()
        ),
        "sorting_simple_feature": str(
            (project_root / experiments_root / "sorting_reports" / batch_id / "simple_feature_threshold_report.json").resolve()
        ),
    }
    return artifacts
