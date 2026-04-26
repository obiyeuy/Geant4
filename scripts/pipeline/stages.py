#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pipeline stage implementations."""

from __future__ import annotations

import json
import os
import random
import re
import subprocess
import math
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

@dataclass
class PipelineConfig:
    raw_root: Path
    processed_root: Path
    experiments_root: Path
    blank_dir: Path

    batch_id: str
    num_samples: int
    sample_start_index: int
    ore_ratio: float
    seed: int
    matrix_material: str
    matrix_density: float
    target_material: str
    target_density: float
    target_grade_min: float
    target_grade_max: float

    geant_exec: Path
    simulation_root: Path
    master_macro: Path
    beam_on: int
    ore_mode: str
    geometry_guard: bool
    tess_max_retries: int
    label_threshold: float

    train_ratio: float
    val_ratio: float
    epochs: int
    batch_size: int
    lr: float
    num_workers: int
    balance_mode: str


@dataclass
class SampleMeta:
    sample_name: str
    class_id: int
    class_name: str
    matrix_material: str
    target_material: str
    mix_spec: str
    mix_density: float
    matrix_mass_fraction: float
    matrix_mass_percent: float
    target_mass_fraction: float
    target_mass_percent: float
    grade_value: float
    grade_type: str
    grade_basis: str
    lumps: int
    cuts: int
    scale: float


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _sample_material_setup(
    cfg: PipelineConfig, rng: random.Random
) -> tuple[str, str, float, float, float, float, str]:
    # 所有样本先随机品位，再由阈值派生 ore/waste 标签。
    target_mass_percent = rng.uniform(cfg.target_grade_min, cfg.target_grade_max)
    target_mass_fraction = target_mass_percent / 100.0
    matrix_mass_fraction = max(0.0, 1.0 - target_mass_fraction)
    mix = (
        f"{cfg.matrix_material}:{matrix_mass_fraction * 100.0:.6f},"
        f"{cfg.target_material}:{target_mass_fraction * 100.0:.6f}"
    )
    # 基于质量分数的比体积加权：
    # 1/rho_mix = sum_i(w_i / rho_i)
    # 统一用于 ore 与 waste（waste 时 target 分数为 0）。
    mix_density = 1.0 / (
        (matrix_mass_fraction / cfg.matrix_density) + (target_mass_fraction / cfg.target_density)
    )
    return (
        cfg.matrix_material,
        mix,
        mix_density,
        matrix_mass_fraction,
        target_mass_fraction,
        target_mass_percent,
        f"{cfg.target_material}_wt%",
    )


def generate_samples(cfg: PipelineConfig) -> list[Path]:
    from pipeline.generate_ore import create_rugged_ore_gdml

    rng = random.Random(cfg.seed)
    batch_dir = cfg.raw_root / f"batch_{cfg.batch_id}"
    _ensure_dir(batch_dir)

    if cfg.target_grade_min < 0 or cfg.target_grade_max > 100 or cfg.target_grade_min > cfg.target_grade_max:
        raise ValueError("target grade range must satisfy 0 <= min <= max <= 100")

    generated: list[Path] = []
    for i in range(cfg.num_samples):
        sample_index = cfg.sample_start_index + i
        (
            matrix_material,
            mix_spec,
            mix_density,
            matrix_mass_fraction,
            target_mass_fraction,
            target_mass_percent,
            grade_type,
        ) = _sample_material_setup(cfg, rng)
        # 生成阶段的类别直接按阈值定义：
        # ore: grade >= label_threshold, waste: grade < label_threshold
        # 这样 waste 样本会保留非零低品位，而不是全部 0。
        class_id = 1 if target_mass_percent >= cfg.label_threshold else 0
        class_name = "ore" if class_id == 1 else "waste"
        sample_name = f"sample_{sample_index:05d}_{class_name}"
        sample_dir = batch_dir / sample_name
        if sample_dir.exists():
            raise FileExistsError(
                f"Sample folder already exists: {sample_dir}. "
                "Please choose a larger --sample-start-index to append new samples."
            )
        _ensure_dir(sample_dir)
        meta = SampleMeta(
            sample_name=sample_name,
            class_id=class_id,
            class_name=class_name,
            matrix_material=matrix_material,
            target_material=cfg.target_material,
            mix_spec=mix_spec,
            mix_density=mix_density,
            matrix_mass_fraction=matrix_mass_fraction,
            matrix_mass_percent=matrix_mass_fraction * 100.0,
            target_mass_fraction=target_mass_fraction,
            target_mass_percent=target_mass_percent,
            grade_value=target_mass_percent,
            grade_type=grade_type,
            grade_basis="target_material_mass_percent",
            lumps=rng.randint(8, 16),
            cuts=rng.randint(12, 24),
            scale=rng.uniform(16.0, 22.0),
        )

        gdml_path = sample_dir / "ore.gdml"
        create_rugged_ore_gdml(
            str(gdml_path),
            matrix_material=meta.matrix_material,
            mix_spec=meta.mix_spec,
            mix_density=meta.mix_density,
            num_lumps=meta.lumps,
            num_cuts=meta.cuts,
            base_scale=meta.scale,
            mode=cfg.ore_mode,
        )

        info = {
            "timestamp": datetime.now().isoformat(),
            "class": meta.class_id,
            "class_name": meta.class_name,
            "target_material": meta.target_material,
            "target_mass_fraction": meta.target_mass_fraction,
            "target_mass_percent": meta.target_mass_percent,
            "grade_value": meta.grade_value,
            "grade_type": meta.grade_type,
            "grade_basis": meta.grade_basis,
            "generator": "scripts/pipeline/stages.py::generate_samples",
            "batch_id": cfg.batch_id,
            "seed": cfg.seed,
            "beam_on": cfg.beam_on,
            "master_macro": str(cfg.master_macro),
            "ore_mode": cfg.ore_mode,
            "geometry": asdict(meta),
        }
        with (sample_dir / "info.json").open("w", encoding="utf-8") as f:
            json.dump(info, f, ensure_ascii=False, indent=2)

        generated.append(sample_dir)

    print(f"[generate] batch={cfg.batch_id}, samples={len(generated)} -> {batch_dir}")
    return generated


def _infer_scan_steps(master_macro: Path) -> int:
    """
    Infer how many times scan_row.mac is executed by master macro.

    We treat cfg.beam_on as the particle count PER scan step.
    If master macro doesn't use /control/loop over scan_row.mac, fall back to 1.
    """
    try:
        text = master_macro.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return 1

    # 示例：
    # /control/loop scan_row.mac iRow -17.5 17.5 0.7
    m = re.search(
        r"^\s*/control/loop\s+scan_row\.mac\s+\S+\s+([-+]?\d*\.?\d+)\s+([-+]?\d*\.?\d+)\s+([-+]?\d*\.?\d+)\s*$",
        text,
        flags=re.MULTILINE,
    )
    if not m:
        return 1

    start = float(m.group(1))
    end = float(m.group(2))
    step = float(m.group(3))
    if step == 0.0:
        return 1

    span = abs(end - start)
    n = int(math.floor(span / abs(step) + 1e-12)) + 1
    return max(1, n)


def _write_scan_row(simulation_root: Path, *, beam_on_per_step: int) -> Path:
    scan_path = simulation_root / "scan_row.mac"
    content = [
        "/Xray/det/SetObjShift {iRow} mm",
        f"/run/beamOn {int(beam_on_per_step)}",
        "",
    ]
    scan_path.write_text("\n".join(content), encoding="utf-8")
    return scan_path


def _write_launch_macro(simulation_root: Path, gdml_path: Path, master_macro: Path) -> Path:
    launch_path = simulation_root / "launch_sample.mac"
    content = [
        "/run/numberOfThreads 12",
        # 稳定顺序：先初始化几何体，再用 GDML 矿石替换占位物体。
        "/run/initialize",
        f"/Xray/det/loadGDML {gdml_path}",
        f"/control/execute {master_macro}",
        "",
    ]
    launch_path.write_text("\n".join(content), encoding="utf-8")
    return launch_path


def _run_simulation_once_with_gdml(cfg: PipelineConfig, gdml_path: Path, output_dir: Path, log_path: Path) -> None:
    if not gdml_path.exists():
        raise FileNotFoundError(f"Missing GDML: {gdml_path}")

    _ensure_dir(output_dir)
    _ensure_dir(log_path.parent)

    beam_on_per_step = max(1, int(cfg.beam_on))
    _write_scan_row(cfg.simulation_root, beam_on_per_step=beam_on_per_step)
    launch_macro = _write_launch_macro(cfg.simulation_root, gdml_path, cfg.master_macro)

    env = dict(**os.environ)
    env["G4_OUTPUT_DIR"] = str(output_dir)

    cmd = [str(cfg.geant_exec), str(launch_macro)]
    with log_path.open("w", encoding="utf-8") as f:
        subprocess.run(cmd, cwd=str(cfg.simulation_root), env=env, stdout=f, stderr=subprocess.STDOUT, check=True)


def _run_single_simulation_once(cfg: PipelineConfig, sample_dir: Path, log_path: Path) -> None:
    gdml_path = sample_dir / "ore.gdml"
    _run_simulation_once_with_gdml(cfg, gdml_path=gdml_path, output_dir=sample_dir, log_path=log_path)


def _log_has_geometry_failure(log_path: Path) -> bool:
    if not log_path.exists():
        return True
    text = log_path.read_text(encoding="utf-8", errors="ignore")
    patterns = [
        r"GeomNav1002",
        r"GeomNav0003",
        r"GeomSolids1001",
        r"GeomSolids1002",
        r"Event Must Be Aborted",
        r"Track \*abandoned\* due to excessive number of Zero steps",
    ]
    return any(re.search(p, text) for p in patterns)


def _run_single_simulation(cfg: PipelineConfig, sample_dir: Path) -> None:
    log_dir = sample_dir / "logs"
    _ensure_dir(log_dir)

    if not cfg.geometry_guard:
        _run_single_simulation_once(cfg, sample_dir, log_dir / "sim.log")
        return

    # geometry_guard 仅负责“重跑同一份 GDML”进行稳定性确认，
    # 不在 simulate 阶段重建或改写几何（几何只由 generate 阶段产出）。
    for attempt in range(1, cfg.tess_max_retries + 1):
        log_path = log_dir / f"sim_tess_try{attempt}.log"
        _run_single_simulation_once(cfg, sample_dir, log_path)
        if not _log_has_geometry_failure(log_path):
            print(f"[simulate] geometry_guard: tessellated pass at try={attempt}")
            return
        print(f"[simulate] geometry_guard: tessellated failed at try={attempt}, retrying...")

    raise RuntimeError(
        f"Geometry guard failed for {sample_dir.name}. "
        "simulate stage does not regenerate geometry; "
        "please rerun generate for this sample and then simulate again. "
        f"See logs under {log_dir}."
    )


def simulate_samples(cfg: PipelineConfig, samples: Iterable[Path]) -> None:
    total = 0
    for sample_dir in samples:
        total += 1
        print(f"[simulate] ({total}) {sample_dir.name}")
        _run_single_simulation(cfg, sample_dir)
    print(f"[simulate] finished {total} samples")


def _write_blank_gdml(blank_gdml_path: Path) -> None:
    # 保留 OreLog 名称以兼容 DetectorConstruction::LoadOreGDML。
    text = """<?xml version="1.0" ?>
<gdml xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="http://cern.ch/service-spi/app/releases/GDML/schema/gdml.xsd">
  <materials>
    <element name="H" formula="H" Z="1">
      <atom value="1.008"/>
    </element>
    <material name="Vacuum">
      <D value="1e-25"/>
      <composite ref="H" n="1"/>
    </material>
  </materials>
  <solids>
    <box name="BlankSolid" x="0.01" y="0.01" z="0.01" lunit="mm"/>
    <box name="world" x="1000" y="1000" z="1000" lunit="mm"/>
  </solids>
  <structure>
    <volume name="OreLog">
      <materialref ref="Vacuum"/>
      <solidref ref="BlankSolid"/>
    </volume>
    <volume name="world">
      <materialref ref="Vacuum"/>
      <solidref ref="world"/>
      <physvol name="OrePV">
        <volumeref ref="OreLog"/>
      </physvol>
    </volume>
  </structure>
  <setup name="Default" version="1.0">
    <world ref="world"/>
  </setup>
</gdml>
"""
    blank_gdml_path.write_text(text, encoding="utf-8")


def simulate_blank(cfg: PipelineConfig) -> Path:
    batch_dir = cfg.raw_root / f"batch_{cfg.batch_id}"
    blank_dir = batch_dir / "blank"
    log_dir = blank_dir / "logs"
    _ensure_dir(log_dir)
    blank_gdml = blank_dir / "blank.gdml"
    _write_blank_gdml(blank_gdml)

    _run_simulation_once_with_gdml(
        cfg,
        gdml_path=blank_gdml,
        output_dir=blank_dir,
        log_path=log_dir / "sim_blank.log",
    )
    steps = _infer_scan_steps(cfg.master_macro)
    beam_on_per_step = max(1, int(cfg.beam_on))
    meta = {
        "timestamp": datetime.now().isoformat(),
        "batch_id": cfg.batch_id,
        "seed": cfg.seed,
        "beam_on": cfg.beam_on,
        "generator": "scripts/pipeline/stages.py::simulate_blank",
        "master_macro": str(cfg.master_macro),
        "scan_row_template": {
            "set_obj_shift": "/Xray/det/SetObjShift {iRow} mm",
            "beam_on_total": beam_on_per_step * steps,
            "beam_on_per_step": beam_on_per_step,
            "scan_steps": steps,
        },
        "gdml": str(blank_gdml),
    }
    (blank_dir / "info.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[blank] generated -> {blank_dir}")
    return blank_dir


def render_samples_to_images(cfg: PipelineConfig, samples: Iterable[Path]) -> None:
    from pipeline.render_images import render_sample_images
    from pipeline.physics import compute_flat_field

    flat_field = compute_flat_field(cfg.blank_dir)
    total = 0
    for sample_dir in samples:
        total += 1
        out_dir = render_sample_images(sample_dir=sample_dir, flat_field=flat_field)
        print(f"[render] ({total}) {sample_dir.name} -> {out_dir}")
    print(f"[render] finished {total} samples")


def build_r_dataset(cfg: PipelineConfig) -> Path:
    from pipeline.build_dataset import build_dataset

    out_dir = cfg.processed_root / "r_value_dataset"
    batch_raw_dir = cfg.raw_root / f"batch_{cfg.batch_id}"
    build_dataset(
        raw_dir=batch_raw_dir,
        blank_dir=cfg.blank_dir,
        out_dir=out_dir,
        train_ratio=cfg.train_ratio,
        val_ratio=cfg.val_ratio,
        seed=cfg.seed,
        label_threshold=cfg.label_threshold,
    )
    return out_dir


def train_model(cfg: PipelineConfig, dataset_root: Path) -> Path:
    from pipeline.train_efficientnet import train

    out_dir = cfg.experiments_root / f"efficientnet_rvalue_{cfg.batch_id}"
    train(
        dataset_root=dataset_root,
        out_dir=out_dir,
        epochs=cfg.epochs,
        batch_size=cfg.batch_size,
        lr=cfg.lr,
        num_workers=cfg.num_workers,
        balance_mode=cfg.balance_mode,
    )
    return out_dir


def evaluate_snr_for_samples(cfg: PipelineConfig, samples: Iterable[Path], out_dir: Path) -> Path:
    from pipeline.evaluate_snr import evaluate

    _ensure_dir(out_dir)
    reports: list[dict] = []
    for sample_dir in samples:
        report = evaluate(
            sample_dir=sample_dir,
            blank_dir=cfg.blank_dir,
            full_scale=1.0,
            target_ratio=0.01,
        )
        reports.append(report)
        out_file = out_dir / f"{sample_dir.name}_snr.json"
        out_file.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        status = "PASS" if all(report["pass"].values()) else "FAIL"
        print(f"[snr] {sample_dir.name}: {status} -> {out_file}")

    summary = {
        "batch_id": cfg.batch_id,
        "total": len(reports),
        "pass_count": sum(1 for r in reports if all(r["pass"].values())),
        "reports": [f"{r['sample_dir']}" for r in reports],
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[snr] summary -> {out_dir / 'summary.json'}")
    return out_dir

