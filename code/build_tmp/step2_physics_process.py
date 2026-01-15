#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import numpy as np
import os
from PIL import Image

# --- 算法常量 ---
EPS = 1e-6          # 防止 log(0)
BIX_OFFSET = 10.0   # 信号平滑偏移 (keV)，用于稳定厚重区域噪声
R_SMOOTH = 1e-2     # R值平滑因子，用于稳定背景区域
# 假设参数
N_blank = 1e7  # 平板模拟粒子数
N_ore = 1e6    # 物料模拟粒子数
scale_factor = N_blank / N_ore  # 补偿倍数，这里是 10


def save_16bit_png(arr, path, vmin, vmax):
    """将物理数据映射到 16位 灰度图保存"""
    arr_clip = np.clip((arr - vmin) / (vmax - vmin), 0, 1)
    arr_16 = (arr_clip * 65535).astype(np.uint16)
    img = Image.fromarray(arr_16, mode="I;16")
    img.save(path)

def main():
    # 1. 加载组装好的原始矩阵
    try:
        low_ore = np.load("npy_data/ore_low.npy")
        high_ore = np.load("npy_data/ore_high.npy")
        low_blank = np.load("npy_data/blank_low.npy")
        high_blank = np.load("npy_data/blank_high.npy")
    except FileNotFoundError:
        print("错误: 找不到 .npy 矩阵文件，请先运行脚本 1")
        return

    # 2. 计算黄金平场线 (利用 81 行空扫数据求平均，降低统计涨落)
    # axis=0 对行求平均，得到 128 维向量
    low_flat_vector = np.mean(low_blank, axis=0)
    high_flat_vector = np.mean(high_blank, axis=0)

    # 3. 计算透射率 T (归一化)
    # 利用 NumPy 广播机制，矩阵的每一行都会除以平均向量
    # t_low = (low_ore + BIX_OFFSET) / (low_flat_vector + BIX_OFFSET)
    # t_high = (high_ore + BIX_OFFSET) / (high_flat_vector + BIX_OFFSET)
    # 修正透射率计算公式
    # 将物料信号乘以倍数，使其与平板信号在同一“入射量级”下对比
    t_low = ((low_ore * scale_factor) + BIX_OFFSET) / (low_flat_vector + BIX_OFFSET)
    t_high = ((high_ore * scale_factor) + BIX_OFFSET) / (high_flat_vector + BIX_OFFSET)
    # 4. 计算衰减 A = -ln(T)
    # np.clip 保证了 T 在有效范围内，避免数学错误
    a_low = -np.log(np.clip(t_low, EPS, 1.0))
    a_high = -np.log(np.clip(t_high, EPS, 1.0))

    # 5. 计算 R 值图像 (R = A_low / A_high)
    # 结果反映了材质的有效原子序数
    r_map = (np.abs(a_low) + R_SMOOTH) / (np.abs(a_high) + R_SMOOTH)

    # 6. 保存结果图像
    os.makedirs("results", exist_ok=True)
    
    # 保存低能、高能透视投影
    save_16bit_png(t_low, "results/low_energy_transmission.png", vmin=0, vmax=1)
    save_16bit_png(t_high, "results/high_energy_transmission.png", vmin=0, vmax=1)
    
    # 保存 R 值材质图（看材质）
    # R 值通常在 0.5 - 2.5 之间，可以根据你的矿石种类微调 vmin/vmax
    # save_16bit_png(r_map, "results/r_value_map.png", vmin=0.5, vmax=2.5)
    save_16bit_png(r_map, "results/r_value_map.png", vmin=0.5, vmax=2.0)

    print("=" * 50)
    print("物理处理完成！")
    print(f"低能平均透过率: {np.mean(t_low):.4f}")
    print(f"R 值图保存路径: results/r_value_map.png")
    print("=" * 50)

if __name__ == "__main__":
    main()