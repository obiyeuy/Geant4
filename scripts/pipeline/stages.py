#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pipeline stage implementations."""

from __future__ import annotations

import json
import os
import random
import re
import subprocess
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
    ore_ratio: float
    seed: int

    geant_exec: Path
    simulation_root: Path
    master_macro: Path
    beam_on: int
    ore_mode: str
    geometry_guard: bool
    tess_max_retries: int

    train_ratio: float
    val_ratio: float
    epochs: int
    batch_size: int
    lr: float
    num_workers: int


@dataclass
class SampleMeta:
    sample_name: str
    class_id: int
    class_name: str
    matrix_material: str
    mix_spec: str
    mix_density: float
    lumps: int
    cuts: int
    scale: float


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _sample_material_setup(is_ore: bool, rng: random.Random) -> tuple[str, str, float]:
    if is_ore:
        ore_ratio_fe = rng.uniform(18.0, 42.0)
        mix = f"CalciumPhosphate:{100.0 - ore_ratio_fe:.2f},G4_Fe:{ore_ratio_fe:.2f}"
        return "CalciumPhosphate", mix, 3.2
    return "G4_Si", "", 2.5


def generate_samples(cfg: PipelineConfig) -> list[Path]:
    from generate_ore import create_rugged_ore_gdml

    rng = random.Random(cfg.seed)
    batch_dir = cfg.raw_root / f"batch_{cfg.batch_id}"
    _ensure_dir(batch_dir)

    generated: list[Path] = []
    for i in range(cfg.num_samples):
        is_ore = rng.random() < cfg.ore_ratio
        class_id = 1 if is_ore else 0
        class_name = "ore" if is_ore else "waste"
        sample_name = f"sample_{i+1:05d}_{class_name}"
        sample_dir = batch_dir / sample_name
        _ensure_dir(sample_dir)

        matrix_material, mix_spec, mix_density = _sample_material_setup(is_ore, rng)
        meta = SampleMeta(
            sample_name=sample_name,
            class_id=class_id,
            class_name=class_name,
            matrix_material=matrix_material,
            mix_spec=mix_spec,
            mix_density=mix_density,
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


def _write_scan_row(simulation_root: Path, beam_on: int = 500000) -> Path:
    scan_path = simulation_root / "scan_row.mac"
    content = [
        "/Xray/det/SetObjShift {iRow} mm",
        f"/run/beamOn {beam_on}",
        "",
    ]
    scan_path.write_text("\n".join(content), encoding="utf-8")
    return scan_path


def _write_launch_macro(simulation_root: Path, gdml_path: Path, master_macro: Path) -> Path:
    launch_path = simulation_root / "launch_sample.mac"
    content = [
        "/run/numberOfThreads 12",
        # Stable order: initialize geometry first, then replace placeholder object with GDML ore.
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

    _write_scan_row(cfg.simulation_root, beam_on=cfg.beam_on)
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


def _regenerate_ore_from_info(sample_dir: Path, mode: str) -> None:
    from generate_ore import create_rugged_ore_gdml

    info_path = sample_dir / "info.json"
    if not info_path.exists():
        raise FileNotFoundError(f"Missing info.json: {info_path}")
    info = json.loads(info_path.read_text(encoding="utf-8"))
    geom = info.get("geometry", {})
    gdml_path = sample_dir / "ore.gdml"
    create_rugged_ore_gdml(
        str(gdml_path),
        matrix_material=str(geom.get("matrix_material", "CalciumPhosphate")),
        mix_spec=str(geom.get("mix_spec", "")),
        mix_density=float(geom.get("mix_density", 2.9)),
        num_lumps=int(geom.get("lumps", 12)),
        num_cuts=int(geom.get("cuts", 18)),
        base_scale=float(geom.get("scale", 12.0)),
        mode=mode,
    )


def _run_single_simulation(cfg: PipelineConfig, sample_dir: Path) -> None:
    log_dir = sample_dir / "logs"
    _ensure_dir(log_dir)

    if not cfg.geometry_guard:
        _run_single_simulation_once(cfg, sample_dir, log_dir / "sim.log")
        return

    # 1) tessellated retries
    for attempt in range(1, cfg.tess_max_retries + 1):
        _regenerate_ore_from_info(sample_dir, mode="tessellated")
        log_path = log_dir / f"sim_tess_try{attempt}.log"
        _run_single_simulation_once(cfg, sample_dir, log_path)
        if not _log_has_geometry_failure(log_path):
            print(f"[simulate] geometry_guard: tessellated pass at try={attempt}")
            return
        print(f"[simulate] geometry_guard: tessellated failed at try={attempt}, retrying...")

    # 2) fallback to csg once
    print("[simulate] geometry_guard: fallback to csg")
    _regenerate_ore_from_info(sample_dir, mode="csg")
    fallback_log = log_dir / "sim_csg_fallback.log"
    _run_single_simulation_once(cfg, sample_dir, fallback_log)
    if _log_has_geometry_failure(fallback_log):
        raise RuntimeError(
            f"Geometry guard failed for {sample_dir.name}. "
            f"See logs under {log_dir}."
        )
    print("[simulate] geometry_guard: csg fallback pass")


def simulate_samples(cfg: PipelineConfig, samples: Iterable[Path]) -> None:
    total = 0
    for sample_dir in samples:
        total += 1
        print(f"[simulate] ({total}) {sample_dir.name}")
        _run_single_simulation(cfg, sample_dir)
    print(f"[simulate] finished {total} samples")


def _write_blank_gdml(blank_gdml_path: Path) -> None:
    # Keep OreLog name for compatibility with DetectorConstruction::LoadOreGDML.
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
    meta = {
        "timestamp": datetime.now().isoformat(),
        "batch_id": cfg.batch_id,
        "seed": cfg.seed,
        "beam_on": cfg.beam_on,
        "generator": "scripts/pipeline/stages.py::simulate_blank",
        "master_macro": str(cfg.master_macro),
        "scan_row_template": {
            "set_obj_shift": "/Xray/det/SetObjShift {iRow} mm",
            "beam_on": cfg.beam_on,
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

