#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Material thickness scan with configurable beamOn and parallel workers."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path

import numpy as np

# 扫描计划：材料 -> (起始厚度mm, 结束厚度mm, 步长mm)
MATERIAL_CONFIG = {
    "H2O": (10.0, 180.0, 10.0),
    "CHO": (10.0, 180.0, 10.0),
    "C": (5.0, 100.0, 5.0),
    "Al": (1.0, 50.0, 1.0),
    "Fe": (0.03, 5.0, 0.03),
    "Cu": (0.01, 3.0, 0.01),
    "Pb": (0.001, 1.0, 0.001),
    # "H2O": (10.0, 180.0, 10.0),
    # "CHO": (10.0, 180.0, 10.0),
    # "C": (5.0, 100.0, 5.0),
    # "Al": (1.0, 50.0, 1.0),
    # "Fe": (0.1, 5.0, 0.1),
    # "Cu": (0.1, 4.0, 0.05),
    # "Pb": (0.01, 0.5, 0.005),
}

DEFAULT_BEAM_ON = 10_000_000
NUM_PIXELS = 128
PIXEL_SLICE = slice(63, 64)
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
SIMULATION_DIR = PROJECT_ROOT / "simulation"
BUILD_DIR = PROJECT_ROOT / "build"
RUN_TIMEOUT_SEC = 3600


def _find_executable(executable_path: str | None) -> Path:
    if executable_path:
        exe = Path(executable_path).resolve()
        if not exe.exists():
            raise FileNotFoundError(f"指定的可执行文件不存在: {exe}")
        if not os.access(exe, os.X_OK):
            raise PermissionError(f"可执行文件不可执行: {exe}")
        return exe

    candidates: list[Path] = []
    for base in (BUILD_DIR, BUILD_DIR / "simulation", PROJECT_ROOT / "build", PROJECT_ROOT / "build" / "simulation"):
        for name in ("XRay", "CZT", "simulation"):
            candidates.append(base / name)
    for path in candidates:
        if path.exists() and os.access(path, os.X_OK):
            return path.resolve()
    raise FileNotFoundError("找不到Geant4可执行文件，请先编译或使用 --executable 指定路径")


def _build_thickness_list(start: float, end: float, step: float) -> list[float]:
    vals: list[float] = []
    idx = 0
    while True:
        v = round(start + idx * step, 6)
        if v > end + 1e-9:
            break
        vals.append(v)
        idx += 1
    if vals and abs(vals[-1] - end) > 1e-6:
        vals.append(round(end, 6))
    return vals


def _write_macro(material: str, thickness_mm: float, beam_on: int, macro_path: Path) -> None:
    macro_path.parent.mkdir(parents=True, exist_ok=True)
    macro = (
        "# 材料厚度扫描宏\n"
        f"# Material: {material}, Thickness: {thickness_mm:.6f} mm\n\n"
        "/control/verbose 0\n"
        "/run/verbose 0\n"
        f"/Xray/det/SetMaterialSlabMaterial {material}\n"
        f"/Xray/det/SetMaterialSlabThickness {thickness_mm:.6f} mm\n"
        "/run/initialize\n"
        f"/run/beamOn {beam_on}\n"
    )
    macro_path.write_text(macro, encoding="utf-8")


def _read_latest_mean(output_dir: Path) -> tuple[float | None, float | None]:
    low_dir = output_dir / "LowEnergy"
    high_dir = output_dir / "HighEnergy"
    if not low_dir.exists() or not high_dir.exists():
        return None, None
    low_files = sorted(low_dir.glob("*.bin"), key=lambda p: p.stat().st_mtime)
    high_files = sorted(high_dir.glob("*.bin"), key=lambda p: p.stat().st_mtime)
    if not low_files or not high_files:
        return None, None
    low_data = np.fromfile(low_files[-1], dtype=np.float64)
    high_data = np.fromfile(high_files[-1], dtype=np.float64)
    if low_data.size != NUM_PIXELS or high_data.size != NUM_PIXELS:
        return None, None
    return float(np.mean(low_data[PIXEL_SLICE])), float(np.mean(high_data[PIXEL_SLICE]))


def _run_one(
    material: str,
    thickness_mm: float,
    beam_on: int,
    output_root: str,
    executable: str,
) -> dict:
    out_dir = Path(output_root) / material / f"thickness_{thickness_mm:.6f}"
    out_dir.mkdir(parents=True, exist_ok=True)
    macro_path = out_dir / "run.mac"
    _write_macro(material, thickness_mm, beam_on, macro_path)

    env = os.environ.copy()
    env["G4_OUTPUT_DIR"] = str(out_dir.resolve())
    cmd = [executable, str(macro_path.resolve())]
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(SIMULATION_DIR),
            env=env,
            capture_output=True,
            text=True,
            timeout=RUN_TIMEOUT_SEC,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {
            "material": material,
            "thickness_mm": thickness_mm,
            "ok": False,
            "error": "timeout",
        }

    if proc.returncode != 0:
        return {
            "material": material,
            "thickness_mm": thickness_mm,
            "ok": False,
            "error": f"exit_code={proc.returncode}",
            "stderr_tail": "\n".join(proc.stderr.splitlines()[-5:]),
        }

    low_mean, high_mean = _read_latest_mean(out_dir)
    if low_mean is None or high_mean is None:
        return {
            "material": material,
            "thickness_mm": thickness_mm,
            "ok": False,
            "error": "output_missing_or_invalid",
        }
    return {
        "material": material,
        "thickness_mm": thickness_mm,
        "ok": True,
        "low_mean": low_mean,
        "high_mean": high_mean,
    }


def _serialize_results(all_results: dict[str, list[dict]], out_path: Path) -> None:
    payload = {}
    for material, items in all_results.items():
        sorted_items = sorted(items, key=lambda x: x["thickness_mm"])
        payload[material] = [[r["thickness_mm"], r["low_mean"], r["high_mean"]] for r in sorted_items]
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Material thickness scan")
    parser.add_argument("--materials", nargs="+", default=list(MATERIAL_CONFIG.keys()), help="materials to scan")
    parser.add_argument("--beam-on", type=int, default=DEFAULT_BEAM_ON, help="beamOn per thickness (default 10000000)")
    parser.add_argument("--output-dir", type=str, default="material_scan_output", help="output root")
    parser.add_argument("--executable", type=str, default=None, help="Geant4 executable path")
    parser.add_argument("--clean", action="store_true", help="delete output-dir before scanning")
    args = parser.parse_args()

    exe = _find_executable(args.executable)
    output_root = (PROJECT_ROOT / args.output_dir).resolve()
    if args.clean and output_root.exists():
        shutil.rmtree(output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    tasks: list[tuple[str, float]] = []
    for material in args.materials:
        if material not in MATERIAL_CONFIG:
            print(f"跳过未知材料: {material}")
            continue
        start, end, step = MATERIAL_CONFIG[material]
        for thickness in _build_thickness_list(start, end, step):
            tasks.append((material, thickness))

    if not tasks:
        raise SystemExit("没有有效扫描任务")

    print(f"总任务数: {len(tasks)} | beamOn: {args.beam_on} | 串行执行")
    all_ok: dict[str, list[dict]] = {m: [] for m in MATERIAL_CONFIG}
    failures: list[dict] = []
    done = 0
    total = len(tasks)
    for m, t in tasks:
        done += 1
        result = _run_one(m, t, args.beam_on, str(output_root), str(exe))
        if result["ok"]:
            all_ok[m].append(result)
            if done % 25 == 0 or done == total:
                print(f"[{done}/{total}] OK {m} {t:.6f} mm")
        else:
            failures.append(result)
            print(f"[{done}/{total}] FAIL {m} {t:.6f} mm -> {result.get('error', 'unknown')}")

    result_json = output_root / "scan_results.json"
    _serialize_results(all_ok, result_json)
    fail_json = output_root / "scan_failures.json"
    fail_json.write_text(json.dumps(failures, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\n结果写入: {result_json}")
    print(f"失败列表: {fail_json}")
    for material in MATERIAL_CONFIG:
        ok_n = len(all_ok.get(material, []))
        exp_n = len(_build_thickness_list(*MATERIAL_CONFIG[material]))
        print(f"  {material}: {ok_n}/{exp_n}")
    if failures:
        print(f"总失败数: {len(failures)}")
    else:
        print("全部任务成功")


if __name__ == "__main__":
    main()

