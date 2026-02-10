#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
优化后的绘图脚本：对数空间 (Log-space) R值分析
L = ln(E0_low / E_low)
H = ln(E0_high / E_high)
"""

import json
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from pathlib import Path


# 配置中文字体支持
def setup_chinese_font():
    """设置中文字体，优先使用系统中可用的中文字体"""
    # 常见的中文字体名称列表（按优先级排序）
    preferred_fonts = [
        'Noto Sans CJK SC',     # Noto字体简体中文
        'Noto Sans CJK TC',     # Noto字体繁体中文
        'Noto Sans CJK JP',     # Noto字体日文（也支持中文）
        'Noto Serif CJK SC',    # Noto Serif简体中文
        'Noto Serif CJK TC',    # Noto Serif繁体中文
        'Noto Serif CJK JP',    # Noto Serif日文（也支持中文）
        'WenQuanYi Micro Hei',  # 文泉驿微米黑
        'WenQuanYi Zen Hei',    # 文泉驿正黑
        'AR PL UKai CN',        # 文鼎PL中楷
        'AR PL UMing CN',       # 文鼎PL中明
        'SimHei',               # 黑体 (Windows)
        'Microsoft YaHei',      # 微软雅黑 (Windows)
        'Source Han Sans CN',   # 思源黑体
        'STHeiti',              # 华文黑体 (macOS)
        'STSong',               # 华文宋体 (macOS)
    ]
    
    # 获取系统中所有可用字体（包括字体文件路径）
    available_fonts = {}
    for font_info in fm.fontManager.ttflist:
        font_name = font_info.name
        font_path = font_info.fname
        available_fonts[font_name] = font_path
    
    # 查找第一个可用的中文字体
    found_font = None
    found_path = None
    
    for font in preferred_fonts:
        if font in available_fonts:
            found_font = font
            found_path = available_fonts[font]
            break
    
    # 如果没有找到预设字体，尝试查找包含CJK/中文关键词的字体
    if not found_font:
        for font_name, font_path in available_fonts.items():
            if any(keyword in font_name.lower() for keyword in ['cjk', 'chinese', 'han', 'hei', 'song', 'kai', 'uming', 'ukai', 'noto']):
                found_font = font_name
                found_path = font_path
                break
    
    if found_font and found_path:
        # 设置全局字体参数
        plt.rcParams['font.sans-serif'] = [found_font] + plt.rcParams['font.sans-serif']
        plt.rcParams['axes.unicode_minus'] = False
        print(f"✓ 使用中文字体: {found_font}")
    else:
        # 如果找不到中文字体，至少设置unicode_minus
        plt.rcParams['axes.unicode_minus'] = False
        print("⚠ 警告: 未找到中文字体，中文可能无法正常显示")
        print("   建议安装中文字体: sudo apt-get install fonts-noto-cjk")

# 设置中文字体
setup_chinese_font()

# 材料颜色映射
MATERIAL_COLORS = {'H2O': '#1f77b4', 'CHO': '#ff7f0e', 'C': '#2ca02c', 'Al': '#d62728', 'Fe': '#9467bd', 'Cu': '#8c564b', 'Pb': '#e377c2'}

# ================= 设置空载能量沉积 (E0) =================
# 注意：你需要根据你的 Geant4 模拟结果填写这两个值
# 如果没有准确值，可以取各材料最薄处(接近0mm)的最大值，或从模拟 log 中查找
E0_LOW = 14706042.77   # 示例：低能探测器空载均值 (keV)
E0_HIGH = 4322554.47  # 示例：高能探测器空载均值 (keV)       14706042.766425144 4322554.474395496
# =======================================================

# 读取结果
results_file = Path(__file__).parent / "scan_results.json"
with open(results_file, 'r') as f:
    all_results = json.load(f)

plt.figure(figsize=(10, 8))

for material, results in all_results.items():
    if not results: continue
    
    # 提取数据
    thicknesses = np.array([r[0] for r in results])
    low_means = np.array([r[1] for r in results])
    high_means = np.array([r[2] for r in results])
    
    # 排序
    sort_idx = np.argsort(thicknesses)
    low_means = low_means[sort_idx]
    high_means = high_means[sort_idx]

    # --- 对数转换逻辑 ---
    # 1. 过滤掉能量沉积为 0 或极小值的数据（防止 ln(0) 或噪声干扰）
    # 能量必须小于 E0 且大于一个基本噪声阈值
    mask = (low_means > 10.0) & (high_means > 10.0) & (low_means < E0_LOW) & (high_means < E0_HIGH)
    
    if np.any(mask):
        # L = ln(E0_low / E_low)
        L = np.log(E0_LOW / low_means[mask])
        # H = ln(E0_high / E_high)
        H = np.log(E0_HIGH / high_means[mask])
        
        color = MATERIAL_COLORS.get(material, "#000000")
        
        # 绘制曲线
        # 在对数空间，不同物质应该呈现为不同斜率的射线
        plt.plot(L, H, 'o-', label=material, color=color, linewidth=2, markersize=4)

        # 计算该物质的平均 R 值 (斜率) 用于参考
        r_val = np.mean(H / L)
        print(f"材料: {material:4s} | 平均 R 值 (H/L): {r_val:.4f}")

# 绘制理想等效线 (R=1.0)
max_val = 5 # 坐标轴范围
plt.plot([0, max_val], [0, max_val], '--', color='gray', alpha=0.5, label='R=1.0 (参考线)')

plt.xlabel(r'$L = \ln(E_{0,low} / E_{low})$ (低能衰减强度)', fontsize=12)
plt.ylabel(r'$H = \ln(E_{0,high} / E_{high})$ (高能衰减强度)', fontsize=12)
plt.title('双能对数域物质识别曲线 (R值分析)\n斜率越大代表原子序数 Z 越高', fontsize=14)
plt.legend(loc='upper left', fontsize=10)
plt.grid(True, alpha=0.3)
plt.axis('equal') # 保持比例一致，方便观察斜率差异
plt.tight_layout()

# 保存图形
output_file = Path(__file__).parent / "material_R_value_curve.png"
plt.savefig(output_file, dpi=300)
print(f"\n图形已保存到: {output_file}")
plt.show()