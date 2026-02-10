#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
材料厚度扫描脚本
对不同的材料按指定步长扫描厚度，并记录低能和高能闪烁体的响应
"""

import os
import sys
import subprocess
import numpy as np
import json
from pathlib import Path
from datetime import datetime

# 材料配置：材料名称 -> (步长(mm), 起始厚度(mm), 结束厚度(mm))
MATERIAL_CONFIG = {
    "H2O": (10.0, 10.0, 180.0),
    "CHO": (10.0, 10.0, 180.0),
    "C": (5.0, 5.0, 100.0),
    "Al": (1.0, 1.0, 50.0),
    "Fe": (0.1, 0.1, 5.0),
    "Cu": (0.1, 0.1, 3.0),
    "Pb": (0.005, 0.01, 0.5),
}

# 材料颜色映射（用于绘图）
MATERIAL_COLORS = {
    "H2O": "#1f77b4",      # 蓝色
    "CHO": "#ff7f0e",      # 橙色
    "C": "#2ca02c",        # 绿色
    "Al": "#d62728",       # 红色
    "Fe": "#9467bd",       # 紫色
    "Cu": "#8c564b",       # 棕色
    "Pb": "#e377c2",       # 粉色
}

# 获取项目根目录
SCRIPT_DIR = Path(__file__).parent.absolute()
PROJECT_ROOT = SCRIPT_DIR.parent
SIMULATION_DIR = PROJECT_ROOT / "simulation"
BUILD_DIR = PROJECT_ROOT / "build"

# 探测器像素数
NUM_PIXELS = 128


def generate_macro_file(material, thickness, output_dir, num_events=1000000):
    """
    生成Geant4宏文件
    
    Args:
        material: 材料名称
        thickness: 材料板厚度 (mm)
        output_dir: 输出目录
        num_events: 事件数
    
    Returns:
        str: 宏文件路径
    """
    macro_path = output_dir / f"scan_{material}_{thickness:.6f}mm.mac"
    
    # 设置输出目录环境变量
    output_dir_str = str(output_dir.absolute())
    
    with open(macro_path, 'w') as f:
        f.write("# Material thickness scan macro\n")
        f.write(f"# Material: {material}, Thickness: {thickness} mm\n\n")
        f.write("/control/verbose 2\n")  # 启用详细输出以便调试
        f.write("/run/verbose 2\n\n")
        
        # 设置ObjShift为厚度值（用于文件名）
        # 注意：RunAction使用ObjShift值作为输出文件名
        # f.write(f"/Xray/det/SetObjShift 0.0 mm\n\n")
        
        # 设置材料板材料和厚度（必须在initialize之前）
        f.write(f"/Xray/det/SetMaterialSlabMaterial {material}\n")
        f.write(f"/Xray/det/SetMaterialSlabThickness {thickness} mm\n\n")
        
        # 初始化（这会触发几何构建）
        f.write("/run/initialize\n\n")
        
        # 设置输出目录（通过环境变量）
        # 注意：Geant4会读取G4_OUTPUT_DIR环境变量
        f.write(f"# Output directory: {output_dir_str}\n")
        f.write(f"# This is set via environment variable G4_OUTPUT_DIR\n\n")
        
        # 运行模拟
        f.write(f"/run/beamOn {num_events}\n")
    
    return macro_path


def run_simulation(macro_path, output_dir, executable_path=None):
    """
    运行Geant4模拟
    
    Args:
        macro_path: 宏文件路径
        output_dir: 输出目录
        executable_path: 可执行文件路径（可选）
    
    Returns:
        bool: 是否成功
    """
    # 设置输出目录环境变量
    env = os.environ.copy()
    output_dir_abs = str(output_dir.absolute())
    env['G4_OUTPUT_DIR'] = output_dir_abs
    
    # 确保输出目录的父目录存在
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    
    print(f"  环境变量 G4_OUTPUT_DIR: {env['G4_OUTPUT_DIR']}")
    
    # 查找可执行文件
    if executable_path:
        executable = Path(executable_path)
        if not executable.exists():
            print(f"错误：指定的可执行文件不存在: {executable_path}")
            return False
        if not os.access(executable, os.X_OK):
            print(f"警告：可执行文件没有执行权限: {executable_path}")
    else:
        # 尝试多个可能的名称和路径
        executable = None
        possible_names = ["XRay", "CZT", "simulation"]
        possible_paths = [
            BUILD_DIR,
            BUILD_DIR / "simulation",
            PROJECT_ROOT / "build",
            PROJECT_ROOT / "build" / "simulation",
        ]
        
        for path in possible_paths:
            for name in possible_names:
                exe_path = path / name
                if exe_path.exists() and os.access(exe_path, os.X_OK):
                    executable = exe_path
                    break
            if executable:
                break
        
        if executable is None:
            print(f"错误：找不到Geant4可执行文件")
            print(f"已搜索以下路径:")
            for path in possible_paths:
                print(f"  {path}")
            print(f"请先编译Geant4项目，或使用 --executable 参数指定可执行文件路径")
            return False
    
    # 运行模拟
    try:
        # 使用绝对路径确保宏文件能被找到
        macro_path_abs = macro_path.absolute()
        cmd = [str(executable), str(macro_path_abs)]
        print(f"  运行命令: {' '.join(cmd)}")
        print(f"  宏文件: {macro_path_abs}")
        print(f"  工作目录: {SIMULATION_DIR}")
        print(f"  输出目录: {output_dir.absolute()}")
        
        # 确保宏文件存在
        if not macro_path_abs.exists():
            print(f"  错误：宏文件不存在: {macro_path_abs}")
            return False
        
        result = subprocess.run(
            cmd,
            cwd=str(SIMULATION_DIR),
            env=env,
            capture_output=True,
            text=True,
            timeout=3600  # 1小时超时
        )
        
        # 打印模拟输出以便调试（总是打印，帮助诊断问题）
        if result.stdout:
            lines = result.stdout.strip().split('\n')
            if len(lines) > 0:
                print(f"  模拟标准输出（最后10行）:")
                for line in lines[-10:]:
                    print(f"    {line}")
            # 检查输出中是否有错误信息
            if "error" in result.stdout.lower() or "Error" in result.stdout or "ERROR" in result.stdout:
                print(f"  警告：标准输出中包含错误信息")
                # 打印所有包含error的行
                for i, line in enumerate(lines):
                    if "error" in line.lower() or "Error" in line or "ERROR" in line:
                        print(f"    第{i+1}行: {line}")
        
        if result.stderr:
            stderr_lines = result.stderr.strip().split('\n')
            if len(stderr_lines) > 0:
                print(f"  模拟错误输出（最后10行）:")
                for line in stderr_lines[-10:]:
                    print(f"    {line}")
        
        if result.returncode != 0:
            print(f"  错误：模拟返回非零退出码: {result.returncode}")
            if result.stdout:
                print(f"  完整标准输出:")
                print(result.stdout)
            if result.stderr:
                print(f"  完整错误输出:")
                print(result.stderr)
            return False
        
        # 注意：不再检查输出内容来判断模拟是否运行
        # 因为文件是否生成是更可靠的判断标准
        # Geant4的输出格式可能因版本和配置而异
        
        # 等待一小段时间确保文件系统同步
        import time
        time.sleep(1.0)  # 增加等待时间
        
        # 检查输出文件是否生成
        low_energy_dir = output_dir / "LowEnergy"
        high_energy_dir = output_dir / "HighEnergy"
        
        # 检查输出目录是否存在
        if not output_dir.exists():
            print(f"  错误：输出目录根本不存在: {output_dir}")
            print(f"    环境变量G4_OUTPUT_DIR: {env.get('G4_OUTPUT_DIR', '未设置')}")
            print(f"    检查输出中是否包含'Output directory'信息...")
            # 检查输出中是否提到了输出目录
            if result.stdout and "Output directory" in result.stdout:
                print(f"    输出中包含'Output directory'信息")
                # 提取输出目录信息
                for line in result.stdout.split('\n'):
                    if "Output directory" in line:
                        print(f"      {line}")
            if result.stdout:
                print(f"  完整标准输出:")
                print(result.stdout)
            if result.stderr:
                print(f"  完整错误输出:")
                print(result.stderr)
            return False
        
        if not low_energy_dir.exists() or not high_energy_dir.exists():
            print(f"  警告：输出目录已创建，但LowEnergy或HighEnergy子目录不存在")
            print(f"    输出目录: {output_dir} (存在: {output_dir.exists()})")
            print(f"    LowEnergy目录: {low_energy_dir} (存在: {low_energy_dir.exists()})")
            print(f"    HighEnergy目录: {high_energy_dir} (存在: {high_energy_dir.exists()})")
            if output_dir.exists():
                print(f"    输出目录内容: {list(output_dir.iterdir())}")
            # 打印完整输出以便调试
            if result.stdout:
                print(f"  完整标准输出:")
                print(result.stdout)
            if result.stderr:
                print(f"  完整错误输出:")
                print(result.stderr)
            return False
        
        # 检查是否有文件生成
        low_files = list(low_energy_dir.glob("*.bin"))
        high_files = list(high_energy_dir.glob("*.bin"))
        if not low_files or not high_files:
            print(f"  警告：模拟完成但未生成数据文件")
            print(f"    LowEnergy文件数: {len(low_files)}")
            print(f"    HighEnergy文件数: {len(high_files)}")
            if result.stdout:
                # 打印最后几行输出以便调试
                lines = result.stdout.strip().split('\n')
                print(f"  模拟输出（最后10行）:")
                for line in lines[-10:]:
                    print(f"    {line}")
            return False
        
        print(f"  模拟成功，生成 {len(low_files)} 个低能文件和 {len(high_files)} 个高能文件")
        return True
    except subprocess.TimeoutExpired:
        print(f"错误：模拟超时")
        return False
    except Exception as e:
        print(f"错误：运行模拟时出错: {e}")
        return False


def read_detector_data(output_dir, thickness=None):
    """
    读取探测器数据并计算平均值
    
    Args:
        output_dir: 输出目录
        thickness: 厚度值（用于查找对应的文件名，可选）
    
    Returns:
        tuple: (低能均值, 高能均值) 或 (None, None) 如果失败
    """
    low_energy_dir = output_dir / "LowEnergy"
    high_energy_dir = output_dir / "HighEnergy"
    
    # 确保目录存在
    if not low_energy_dir.exists() or not high_energy_dir.exists():
        print(f"警告：输出目录不存在: {output_dir}")
        return None, None
    
    # 查找.bin文件
    low_files = list(low_energy_dir.glob("*.bin"))
    high_files = list(high_energy_dir.glob("*.bin"))
    
    if not low_files or not high_files:
        print(f"警告：在 {output_dir} 中找不到数据文件")
        print(f"  LowEnergy目录: {low_energy_dir} (找到 {len(low_files)} 个文件)")
        print(f"  HighEnergy目录: {high_energy_dir} (找到 {len(high_files)} 个文件)")
        if low_energy_dir.exists():
            print(f"  LowEnergy目录内容: {list(low_energy_dir.iterdir())}")
        if high_energy_dir.exists():
            print(f"  HighEnergy目录内容: {list(high_energy_dir.iterdir())}")
        return None, None
    
    # 如果指定了厚度，尝试查找对应文件
    # RunAction使用setprecision(1)，所以文件名格式是"10.0.bin"（一位小数）
    if thickness is not None:
        # 尝试多种格式匹配（因为可能有浮点误差）
        thickness_strs = [
            f"{thickness:.1f}",  # 标准格式：10.0
            f"{thickness:.6f}",  # 完整格式：10.000000
            f"{int(thickness)}",  # 整数格式：10
        ]
        
        low_file = None
        high_file = None
        
        for ts in thickness_strs:
            test_low = low_energy_dir / f"{ts}.bin"
            test_high = high_energy_dir / f"{ts}.bin"
            if test_low.exists() and test_high.exists():
                low_file = test_low
                high_file = test_high
                break
        
        # 如果精确匹配失败，查找最接近的文件
        if low_file is None or high_file is None:
            try:
                # 查找文件名数值最接近厚度的文件
                def find_closest(files, target):
                    best = None
                    best_diff = float('inf')
                    for f in files:
                        try:
                            val = float(f.stem)
                            diff = abs(val - target)
                            if diff < best_diff:
                                best_diff = diff
                                best = f
                        except ValueError:
                            continue
                    return best
                
                low_file = find_closest(low_files, thickness)
                high_file = find_closest(high_files, thickness)
                
                if low_file is None or high_file is None:
                    # 如果还是找不到，使用最新的文件
                    low_file = max(low_files, key=lambda p: p.stat().st_mtime)
                    high_file = max(high_files, key=lambda p: p.stat().st_mtime)
            except Exception:
                # 如果出错，使用最新的文件
                low_file = max(low_files, key=lambda p: p.stat().st_mtime)
                high_file = max(high_files, key=lambda p: p.stat().st_mtime)
    else:
        # 使用最新的文件
        low_file = max(low_files, key=lambda p: p.stat().st_mtime)
        high_file = max(high_files, key=lambda p: p.stat().st_mtime)
    
    try:
        # 读取二进制数据（G4double = float64）
        low_data = np.fromfile(low_file, dtype=np.float64)
        high_data = np.fromfile(high_file, dtype=np.float64)
        
        if low_data.size != NUM_PIXELS or high_data.size != NUM_PIXELS:
            print(f"警告：数据尺寸不匹配，期望 {NUM_PIXELS}，实际 {low_data.size}, {high_data.size}")
            return None, None
        
        # 计算平均值
        low_mean = np.mean(low_data[63:64])
        high_mean = np.mean(high_data[63:64])
        
        return low_mean, high_mean
    except Exception as e:
        print(f"错误：读取数据文件时出错: {e}")
        return None, None


def scan_material(material, step, start, end, base_output_dir, num_events=1000000, executable_path=None):
    """
    扫描单个材料的厚度范围
    
    Args:
        material: 材料名称
        step: 步长 (mm)
        start: 起始厚度 (mm)
        end: 结束厚度 (mm)
        base_output_dir: 基础输出目录
        num_events: 每个厚度的模拟事件数
        executable_path: 可执行文件路径（可选）
    
    Returns:
        list: [(厚度, 低能均值, 高能均值), ...]
    """
    print(f"\n{'='*60}")
    print(f"开始扫描材料: {material}")
    print(f"厚度范围: {start} - {end} mm, 步长: {step} mm")
    print(f"{'='*60}\n")
    
    results = []
    thicknesses = np.arange(start, end + step/2, step)  # 包含结束值
    
    for i, thickness in enumerate(thicknesses):
        thickness = round(thickness, 6)  # 避免浮点误差
        print(f"[{i+1}/{len(thicknesses)}] 扫描厚度: {thickness} mm")
        
        # 为每个厚度创建独立的输出目录
        output_dir = base_output_dir / material / f"thickness_{thickness:.6f}"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建宏文件
        macro_path = generate_macro_file(material, thickness, output_dir, num_events)
        
        # 运行模拟
        if not run_simulation(macro_path, output_dir, executable_path):
            print(f"警告：厚度 {thickness} mm 的模拟失败，跳过")
            continue
        
        # 读取数据（传入厚度值以便查找对应文件）
        low_mean, high_mean = read_detector_data(output_dir, thickness)
        
        if low_mean is not None and high_mean is not None:
            results.append((thickness, low_mean, high_mean))
            # 检查是否为0值（完全吸收）
            if low_mean == 0.0 and high_mean == 0.0:
                print(f"  低能均值: {low_mean:.6f} keV, 高能均值: {high_mean:.6f} keV (完全吸收)")
                print(f"  注意：材料厚度 {thickness} mm 导致X射线完全被吸收，这是正常的物理现象")
            elif low_mean == 0.0:
                print(f"  低能均值: {low_mean:.6f} keV, 高能均值: {high_mean:.6f} keV")
                print(f"  注意：低能探测器无响应（低能光子被完全吸收），但高能探测器仍有响应")
            else:
                print(f"  低能均值: {low_mean:.6f} keV, 高能均值: {high_mean:.6f} keV")
        else:
            print(f"  警告：无法读取数据")
    
    print(f"\n材料 {material} 扫描完成，共 {len(results)} 个有效数据点")
    
    # 统计0值数据点
    zero_count = sum(1 for r in results if r[1] == 0.0 and r[2] == 0.0)
    if zero_count > 0:
        print(f"  其中 {zero_count} 个数据点显示完全吸收（0值），这是正常的物理现象")
        print(f"  说明：当材料厚度足够大时，X射线会被完全吸收，无法到达探测器")
    
    # 找出最后一个非零数据点
    non_zero_results = [r for r in results if not (r[1] == 0.0 and r[2] == 0.0)]
    if non_zero_results and zero_count > 0:
        last_non_zero = non_zero_results[-1]
        print(f"  最后一个有响应的厚度: {last_non_zero[0]} mm")
        print(f"  建议：对于该材料，可考虑将扫描上限调整为 {last_non_zero[0] + step} mm")
    
    print()
    return results


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="材料厚度扫描脚本")
    parser.add_argument("--materials", nargs="+", default=list(MATERIAL_CONFIG.keys()),
                       help="要扫描的材料列表（默认：所有材料）")
    parser.add_argument("--num-events", type=int, default=1000000,
                       help="每个厚度的模拟事件数（默认：1000000）")
    parser.add_argument("--output-dir", type=str, default="material_scan_output",
                       help="输出目录（默认：material_scan_output）")
    parser.add_argument("--skip-simulation", action="store_true",
                       help="跳过模拟，仅分析已有数据")
    parser.add_argument("--executable", type=str, default=None,
                       help="Geant4可执行文件路径（默认：自动查找）")
    
    args = parser.parse_args()
    
    # 创建输出目录
    base_output_dir = Path(args.output_dir)
    base_output_dir.mkdir(parents=True, exist_ok=True)
    
    # 存储所有结果
    all_results = {}
    
    # 扫描每种材料
    for material in args.materials:
        if material not in MATERIAL_CONFIG:
            print(f"警告：未知材料 {material}，跳过")
            continue
        
        step, start, end = MATERIAL_CONFIG[material]
        
        if args.skip_simulation:
            # 仅分析已有数据
            print(f"分析已有数据: {material}")
            material_dir = base_output_dir / material
            if not material_dir.exists():
                print(f"警告：找不到 {material_dir}，跳过")
                continue
            
            results = []
            for thickness_dir in sorted(material_dir.glob("thickness_*")):
                try:
                    thickness = float(thickness_dir.name.split("_")[1])
                    low_mean, high_mean = read_detector_data(thickness_dir, thickness)
                    if low_mean is not None and high_mean is not None:
                        results.append((thickness, low_mean, high_mean))
                except Exception as e:
                    print(f"警告：处理 {thickness_dir} 时出错: {e}")
            
            all_results[material] = results
        else:
            # 运行扫描
            results = scan_material(material, step, start, end, base_output_dir, args.num_events, args.executable)
            all_results[material] = results
    
    # 保存结果到JSON文件
    results_file = base_output_dir / "scan_results.json"
    with open(results_file, 'w') as f:
        json.dump(all_results, f, indent=2)
    print(f"\n结果已保存到: {results_file}")
    
    # 生成绘图脚本
    plot_script = base_output_dir / "plot_results.py"
    # generate_plot_script(plot_script, all_results)
    print(f"绘图脚本已生成: {plot_script}")
    print(f"\n运行以下命令绘制结果:")
    print(f"  python {plot_script}")


# def generate_plot_script(plot_script_path, all_results):
#     """生成绘图脚本"""
#     script_content = f'''#!/usr/bin/env python3
# # -*- coding: utf-8 -*-
# """
# 自动生成的绘图脚本
# 绘制低能 vs 高能闪烁体均值的统计曲线
# """

# import json
# import numpy as np
# import matplotlib.pyplot as plt
# from pathlib import Path

# # 材料颜色映射
# MATERIAL_COLORS = {MATERIAL_COLORS}

# # 读取结果
# results_file = Path(__file__).parent / "scan_results.json"
# with open(results_file, 'r') as f:
#     all_results = json.load(f)

# # 创建图形
# plt.figure(figsize=(10, 8))

# # 绘制每种材料的曲线
# for material, results in all_results.items():
#     if not results:
#         continue
    
#     # 转换为numpy数组
#     thicknesses = np.array([r[0] for r in results])
#     low_means = np.array([r[1] for r in results])
#     high_means = np.array([r[2] for r in results])
    
#     # 按厚度排序
#     sort_idx = np.argsort(thicknesses)
#     thicknesses = thicknesses[sort_idx]
#     low_means = low_means[sort_idx]
#     high_means = high_means[sort_idx]
    
#     # 获取颜色
#     color = MATERIAL_COLORS.get(material, "#000000")
    
#     # 分离0值和非0值数据点
#     non_zero_mask = (low_means > 0) | (high_means > 0)
#     zero_mask = ~non_zero_mask
    
#     # 绘制非0值曲线（主要数据）
#     if np.any(non_zero_mask):
#         plt.plot(low_means[non_zero_mask], high_means[non_zero_mask], 
#                 'o-', label=material, color=color, linewidth=2, markersize=4)
    
#     # 标记0值点（完全吸收）
#     if np.any(zero_mask):
#         # 在原点标记0值点
#         # 注意：material是在循环中定义的变量，在生成的脚本中直接使用
#         zero_label = material + " (完全吸收)" if not np.any(non_zero_mask) else None
#         plt.plot(0, 0, 'x', color=color, markersize=8, markeredgewidth=2, 
#                 label=zero_label)
#         if np.any(zero_mask):
#             first_zero_thickness = thicknesses[zero_mask][0] if np.any(zero_mask) else 'N/A'
#             print(f"{{material}}: {{np.sum(zero_mask)}} 个数据点显示完全吸收（厚度 >= {{first_zero_thickness}} mm）")

# plt.xlabel('低能闪烁体均值 (keV)', fontsize=12)
# plt.ylabel('高能闪烁体均值 (keV)', fontsize=12)
# plt.title('材料厚度扫描统计曲线\\n低能 vs 高能闪烁体响应', fontsize=14)
# plt.legend(loc='best', fontsize=10)
# plt.grid(True, alpha=0.3)
# plt.tight_layout()

# # 保存图形
# output_file = Path(__file__).parent / "material_scan_curve.png"
# plt.savefig(output_file, dpi=300, bbox_inches='tight')
# print(f"图形已保存到: {{output_file}}")

# plt.show()
# '''
    
#     with open(plot_script_path, 'w') as f:
#         f.write(script_content)
    
#     # 设置可执行权限
#     os.chmod(plot_script_path, 0o755)


if __name__ == "__main__":
    main()

