#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动生成的绘图脚本
绘制低能 vs 高能闪烁体均值的统计曲线
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

# 读取结果
results_file = Path(__file__).parent / "scan_results.json"
with open(results_file, 'r') as f:
    all_results = json.load(f)

# 创建图形
plt.figure(figsize=(10, 8))

# 绘制每种材料的曲线
for material, results in all_results.items():
    if not results:
        continue
    
    # 转换为numpy数组
    thicknesses = np.array([r[0] for r in results])
    low_means = np.array([r[1] for r in results])
    high_means = np.array([r[2] for r in results])
    
    # 按厚度排序
    sort_idx = np.argsort(thicknesses)
    thicknesses = thicknesses[sort_idx]
    low_means = low_means[sort_idx]
    high_means = high_means[sort_idx]
    
    # 获取颜色
    color = MATERIAL_COLORS.get(material, "#000000")
    
    # 分离0值和非0值数据点
    non_zero_mask = (low_means > 0) | (high_means > 0)
    zero_mask = ~non_zero_mask
    
    # 绘制非0值曲线（主要数据）
    if np.any(non_zero_mask):
        plt.plot(low_means[non_zero_mask], high_means[non_zero_mask], 
                'o-', label=material, color=color, linewidth=2, markersize=4)
    
    # 标记0值点（完全吸收）
    if np.any(zero_mask):
        # 在原点标记0值点
        # 注意：material是在循环中定义的变量，在生成的脚本中直接使用
        zero_label = material + " (完全吸收)" if not np.any(non_zero_mask) else None
        plt.plot(0, 0, 'x', color=color, markersize=8, markeredgewidth=2, 
                label=zero_label)
        if np.any(zero_mask):
            first_zero_thickness = thicknesses[zero_mask][0] if np.any(zero_mask) else 'N/A'
            print(f"{material}: {np.sum(zero_mask)} 个数据点显示完全吸收（厚度 >= {first_zero_thickness} mm）")

plt.xlabel('低能闪烁体均值 (keV)', fontsize=12)
plt.ylabel('高能闪烁体均值 (keV)', fontsize=12)
plt.title('材料厚度扫描统计曲线\n低能 vs 高能闪烁体响应', fontsize=14)
plt.legend(loc='best', fontsize=10)
plt.grid(True, alpha=0.3)
plt.tight_layout()

# 保存图形
output_file = Path(__file__).parent / "material_scan_curve.png"
plt.savefig(output_file, dpi=300, bbox_inches='tight')
print(f"图形已保存到: {output_file}")

plt.show()
