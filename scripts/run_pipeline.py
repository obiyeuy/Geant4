#!/usr/bin/env python3
"""
自动化数据生成管线
负责调度整个模拟流程：生成矿石 -> Geant4 模拟 -> 保存标签
"""

import os
import sys
import json
import subprocess
import argparse
from datetime import datetime
from pathlib import Path

# 添加当前脚本目录到路径，以便导入 generate_ore
script_dir = Path(__file__).parent.absolute()
sys.path.insert(0, str(script_dir))
import generate_ore


def create_sample_directory(base_dir, batch_id, sample_id, material):
    """
    创建样本文件夹
    
    Args:
        base_dir: 基础数据目录
        batch_id: 批次ID（如日期）
        sample_id: 样本ID
        material: 材质名称
    
    Returns:
        str: 样本文件夹的绝对路径
    """
    sample_dir = Path(base_dir) / f"batch_{batch_id}" / f"sample_{sample_id:04d}_{material}"
    sample_dir.mkdir(parents=True, exist_ok=True)
    return str(sample_dir.absolute())


def generate_macro_file(sample_dir, gdml_path, base_macro="master.mac"):
    """
    生成临时宏文件，包含 GDML 加载命令
    
    Args:
        sample_dir: 样本文件夹路径
        gdml_path: GDML 文件绝对路径
        base_macro: 基础宏文件名（在 simulation 目录中）
    
    Returns:
        str: 生成的宏文件路径
    """
    # 读取基础宏文件（从项目根目录的 simulation 目录）
    project_root = script_dir.parent
    simulation_dir = project_root / "simulation"
    base_macro_path = simulation_dir / base_macro
    
    if not base_macro_path.exists():
        raise FileNotFoundError(f"基础宏文件不存在: {base_macro_path}")
    
    # 读取基础宏内容
    with open(base_macro_path, 'r') as f:
        macro_content = f.read()
    
    # 在宏文件开头添加 GDML 加载命令
    gdml_load_cmd = f"/Xray/det/loadGDML {gdml_path}\n"
    macro_content = gdml_load_cmd + macro_content
    
    # 写入临时宏文件
    temp_macro_path = Path(sample_dir) / "scan.mac"
    with open(temp_macro_path, 'w') as f:
        f.write(macro_content)
    
    return str(temp_macro_path.absolute())


def run_geant4_simulation(executable_path, macro_path, output_dir):
    """
    运行 Geant4 模拟
    
    Args:
        executable_path: Geant4 可执行文件路径
        macro_path: 宏文件路径
        output_dir: 输出目录（设置到环境变量）
    
    Returns:
        bool: 是否成功
    """
    # 设置环境变量
    env = os.environ.copy()
    env["G4_OUTPUT_DIR"] = output_dir
    
    # 构建命令
    cmd = [executable_path, macro_path]
    
    print(f"运行 Geant4 模拟...")
    print(f"  可执行文件: {executable_path}")
    print(f"  宏文件: {macro_path}")
    print(f"  输出目录: {output_dir}")
    
    try:
        # 运行模拟（可能需要较长时间）
        result = subprocess.run(
            cmd,
            env=env,
            cwd=os.path.dirname(executable_path),
            check=True,
            capture_output=True,
            text=True
        )
        
        print("模拟完成！")
        if result.stdout:
            print("标准输出:")
            print(result.stdout[-500:])  # 只打印最后500字符
        
        return True
    except subprocess.CalledProcessError as e:
        print(f"模拟失败: {e}")
        if e.stdout:
            print("标准输出:")
            print(e.stdout)
        if e.stderr:
            print("错误输出:")
            print(e.stderr)
        return False


def save_sample_info(sample_dir, ore_info, additional_info=None):
    """
    保存样本信息到 info.json
    
    Args:
        sample_dir: 样本文件夹路径
        ore_info: 矿石生成信息（来自 generate_ore）
        additional_info: 额外信息字典
    """
    info = {
        "timestamp": datetime.now().isoformat(),
        "ore_info": ore_info,
    }
    
    if additional_info:
        info.update(additional_info)
    
    info_path = Path(sample_dir) / "info.json"
    with open(info_path, 'w') as f:
        json.dump(info, f, indent=2)
    
    print(f"样本信息已保存: {info_path}")


def process_single_sample(base_dir, batch_id, sample_id, material,
                          executable_path, ore_params):
    """
    处理单个样本的完整流程
    
    Args:
        base_dir: 基础数据目录
        batch_id: 批次ID
        sample_id: 样本ID
        material: 材质名称
        executable_path: Geant4 可执行文件路径
        ore_params: 矿石生成参数字典
    
    Returns:
        bool: 是否成功
    """
    print(f"\n{'='*60}")
    print(f"处理样本: batch_{batch_id} / sample_{sample_id:04d}_{material}")
    print(f"{'='*60}")
    
    # 1. 创建样本文件夹
    sample_dir = create_sample_directory(base_dir, batch_id, sample_id, material)
    print(f"样本目录: {sample_dir}")
    
    # 2. 生成矿石 GDML
    gdml_path = os.path.join(sample_dir, "ore.gdml")
    print(f"\n步骤 1: 生成矿石几何...")
    try:
        ore_info = generate_ore.create_ore_with_inclusions(
            gdml_path,
            ore_params.get("matrix_material", "CalciumPhosphate"),
            ore_params.get("inclusion_material", "G4_Pb"),
            ore_params.get("num_ellipsoids", 3),
            ore_params.get("num_particles", 1000),
            ore_params.get("particle_radius", 1.0)
        )
    except Exception as e:
        print(f"矿石生成失败: {e}")
        return False
    
    # 3. 生成临时宏文件
    print(f"\n步骤 2: 生成宏文件...")
    try:
        macro_path = generate_macro_file(sample_dir, os.path.abspath(gdml_path))
        print(f"宏文件: {macro_path}")
    except Exception as e:
        print(f"宏文件生成失败: {e}")
        return False
    
    # 4. 运行 Geant4 模拟
    print(f"\n步骤 3: 运行 Geant4 模拟...")
    success = run_geant4_simulation(executable_path, macro_path, sample_dir)
    if not success:
        return False
    
    # 5. 保存样本信息
    print(f"\n步骤 4: 保存样本信息...")
    save_sample_info(sample_dir, ore_info, {
        "batch_id": batch_id,
        "sample_id": sample_id,
        "material": material
    })
    
    print(f"\n样本处理完成！")
    return True


def main():
    parser = argparse.ArgumentParser(description="自动化数据生成管线")
    parser.add_argument("--base-dir", type=str, default="data/raw",
                       help="基础数据目录")
    parser.add_argument("--batch-id", type=str, default=None,
                       help="批次ID（默认使用当前日期）")
    parser.add_argument("--num-samples", type=int, default=10,
                       help="生成样本数量")
    parser.add_argument("--start-id", type=int, default=1,
                       help="起始样本ID")
    parser.add_argument("--material", type=str, default="mixed",
                       help="材质名称")
    parser.add_argument("--executable", type=str, default=None,
                       help="Geant4 可执行文件路径（默认: ../simulation/build/CZT）")
    parser.add_argument("--num-particles", type=int, default=1000,
                       help="矿石颗粒数量")
    parser.add_argument("--particle-radius", type=float, default=1.0,
                       help="颗粒半径 (mm)")
    parser.add_argument("--num-ellipsoids", type=int, default=3,
                       help="基体椭球数量")
    
    args = parser.parse_args()
    
    # 设置默认批次ID
    if args.batch_id is None:
        args.batch_id = datetime.now().strftime("%Y%m%d")
    
    # 设置默认可执行文件路径（相对于 scripts 目录）
    if args.executable is None:
        project_root = script_dir.parent
        args.executable = str(project_root / "simulation" / "build" / "CZT")
        # 如果 build 目录不存在，尝试其他可能的位置
        if not os.path.exists(args.executable):
            args.executable = str(project_root / "simulation" / "CZT")
    
    if not os.path.exists(args.executable):
        print(f"错误: Geant4 可执行文件不存在: {args.executable}")
        print("请先编译 Geant4 程序，或使用 --executable 指定路径")
        return 1
    
    # 矿石生成参数
    ore_params = {
        "num_particles": args.num_particles,
        "particle_radius": args.particle_radius,
        "num_ellipsoids": args.num_ellipsoids,
    }
    
    print(f"数据生成管线配置:")
    print(f"  基础目录: {args.base_dir}")
    print(f"  批次ID: {args.batch_id}")
    print(f"  样本数量: {args.num_samples}")
    print(f"  起始ID: {args.start_id}")
    print(f"  材质: {args.material}")
    print(f"  可执行文件: {args.executable}")
    print(f"  矿石参数: {ore_params}")
    
    # 处理每个样本
    success_count = 0
    for i in range(args.num_samples):
        sample_id = args.start_id + i
        success = process_single_sample(
            args.base_dir,
            args.batch_id,
            sample_id,
            args.material,
            args.executable,
            ore_params
        )
        if success:
            success_count += 1
    
    print(f"\n{'='*60}")
    print(f"批次处理完成！")
    print(f"  成功: {success_count}/{args.num_samples}")
    print(f"  失败: {args.num_samples - success_count}/{args.num_samples}")
    print(f"{'='*60}")
    
    return 0 if success_count == args.num_samples else 1


if __name__ == "__main__":
    sys.exit(main())





