#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import numpy as np
import glob
import os

# --- 配置参数 ---
NUM_PIXELS = 128  # 探测器像素数
# 设定输入输出根目录
ROOT_DIR = "." 
SCAN_DIR = os.path.join(ROOT_DIR, "output")        # 矿石扫描数据
BLANK_DIR = os.path.join(ROOT_DIR, "output_blank")  # 空扫平场数据

def assemble_matrix(data_dir, label):
    """
    读取指定目录下所有 .bin 文件并拼装为矩阵
    """
    low_path = os.path.join(data_dir, "LowEnergy")
    high_path = os.path.join(data_dir, "HighEnergy")

    def read_folder(folder):
        files = glob.glob(os.path.join(folder, "*.bin"))
        # 按文件名中的位置数值排序（例如 -28.0.bin, -27.0.bin...）
        files = sorted(files, key=lambda x: float(os.path.basename(x).replace(".bin", "")))
        
        matrix = []
        for f in files:
            # Geant4 默认输出 float64
            data = np.fromfile(f, dtype=np.float64)
            if data.size == NUM_PIXELS:
                matrix.append(data)
            else:
                print(f"警告: 跳过文件 {f}，尺寸不符: {data.size}")
        return np.array(matrix)

    print(f"正在组装 {label} 数据...")
    low_matrix = read_folder(low_path)
    high_matrix = read_folder(high_path)

    # 存为 .npy 文件，保留原始物理精度
    os.makedirs("npy_data", exist_ok=True)
    np.save(f"npy_data/{label}_low.npy", low_matrix)
    np.save(f"npy_data/{label}_high.npy", high_matrix)
    print(f"成功保存 {label} 矩阵，形状: {low_matrix.shape}")

if __name__ == "__main__":
    # 组装正式扫描数据
    if os.path.exists(SCAN_DIR):
        assemble_matrix(SCAN_DIR, "ore")
    else:
        print(f"错误: 找不到目录 {SCAN_DIR}")

    # 组装空扫数据
    if os.path.exists(BLANK_DIR):
        assemble_matrix(BLANK_DIR, "blank")
    else:
        print(f"提示: 找不到目录 {BLANK_DIR}，请确保已跑完空扫模拟")