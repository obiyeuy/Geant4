#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据组合和可视化脚本
功能：
1. 读取所有位置的LowEnergy和HighEnergy数据
2. 组合成3D数组 [位置, 像素, 能量]
3. 生成多种可视化图像
"""

import numpy as np
import matplotlib.pyplot as plt
from PIL import Image
import glob
import os
from pathlib import Path

# 设置中文字体（如果需要显示中文）
plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial', 'SimHei']
plt.rcParams['axes.unicode_minus'] = False

# 配置参数
OUTPUT_DIR = "output"
LOW_ENERGY_DIR = os.path.join(OUTPUT_DIR, "LowEnergy")
HIGH_ENERGY_DIR = os.path.join(OUTPUT_DIR, "HighEnergy")
MYDATA_DIR = os.path.join(OUTPUT_DIR, "Mydata")

NUM_PIXELS = 128  # 像素数量

def load_scan_data():
    """
    加载所有扫描位置的数据
    
    返回:
        positions: 位置数组 (n_positions,)
        low_energy_data: 低能数据 (n_positions, 128)
        high_energy_data: 高能数据 (n_positions, 128)
    """
    print("正在加载数据...")
    
    # 找到所有LowEnergy文件，按数值排序（不是字符串排序）
    low_files = glob.glob(os.path.join(LOW_ENERGY_DIR, "*.txt"))
    # 按文件名中的数值排序
    low_files = sorted(low_files, key=lambda x: float(os.path.basename(x).replace(".txt", "")))
    
    if not low_files:
        print(f"错误: 在 {LOW_ENERGY_DIR} 中找不到数据文件")
        return None, None, None
    
    positions = []
    low_energy_data = []
    high_energy_data = []
    
    for low_file in low_files:
        # 从文件名提取位置（例如: "0.0.txt" -> 0.0）
        filename = os.path.basename(low_file)
        try:
            y_pos = float(filename.replace(".txt", ""))
        except ValueError:
            print(f"警告: 无法解析文件名 {filename}，跳过")
            continue
        
        # 读取低能数据
        try:
            # 读取文件内容，按制表符分割，过滤空字符串
            with open(low_file, 'r') as f:
                content = f.read().strip()
                values = [float(x) for x in content.split('\t') if x.strip()]
            
            if len(values) != NUM_PIXELS:
                print(f"警告: {filename} 数据点数不是 {NUM_PIXELS}，实际为 {len(values)}")
                continue
            
            low_data = np.array(values)
        except Exception as e:
            print(f"警告: 读取 {low_file} 失败: {e}")
            continue
        
        # 读取对应的高能数据
        high_file = os.path.join(HIGH_ENERGY_DIR, filename)
        if not os.path.exists(high_file):
            print(f"警告: 找不到对应的高能文件 {high_file}，跳过")
            continue
        
        try:
            # 读取文件内容，按制表符分割，过滤空字符串
            with open(high_file, 'r') as f:
                content = f.read().strip()
                values = [float(x) for x in content.split('\t') if x.strip()]
            
            if len(values) != NUM_PIXELS:
                print(f"警告: {high_file} 数据点数不是 {NUM_PIXELS}，实际为 {len(values)}")
                continue
            
            high_data = np.array(values)
        except Exception as e:
            print(f"警告: 读取 {high_file} 失败: {e}")
            continue
        
        positions.append(y_pos)
        low_energy_data.append(low_data)
        high_energy_data.append(high_data)
    
    if len(positions) == 0:
        print("错误: 没有成功加载任何数据")
        return None, None, None
    
    positions = np.array(positions)
    low_energy_data = np.array(low_energy_data)
    high_energy_data = np.array(high_energy_data)
    
    print(f"成功加载 {len(positions)} 个位置的数据")
    if len(positions) > 0:
        print(f"位置范围: {positions.min():.1f} 到 {positions.max():.1f} mm")
    
    return positions, low_energy_data, high_energy_data


# def create_heatmaps(positions, low_data, high_data):
#     """
#     创建2D热图：位置 vs 像素的能量分布
#     """
#     print("生成热图...")
    
#     fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    
#     # 低能热图
#     # 注意：low_data 形状是 [n_positions, n_pixels]
#     # 转置后是 [n_pixels, n_positions]，用于显示
#     # Y轴（行）= 像素编号，X轴（列）= Y位置
#     im1 = axes[0].imshow(low_data.T, aspect='auto', origin='lower',
#                         extent=[positions.min(), positions.max(), 0, NUM_PIXELS-1],
#                         cmap='viridis', interpolation='nearest')
#                         # cmap='viridis', interpolation='nearest')
#     axes[0].set_xlabel('Y Position (mm)', fontsize=12)
#     axes[0].set_ylabel('Pixel Number', fontsize=12)
#     axes[0].set_title('Low Energy (GGAG) - Energy Deposition', fontsize=14, fontweight='bold')
#     plt.colorbar(im1, ax=axes[0], label='Energy (keV)')
#     axes[0].grid(True, alpha=0.3)
    
#     # 高能热图
#     im2 = axes[1].imshow(high_data.T, aspect='auto', origin='lower',
#                         extent=[positions.min(), positions.max(), 0, NUM_PIXELS-1],
#                         cmap='plasma', interpolation='nearest')
#                         # cmap='viridis', interpolation='nearest')
#     axes[1].set_xlabel('Y Position (mm)', fontsize=12)
#     axes[1].set_ylabel('Pixel Number', fontsize=12)
#     axes[1].set_title('High Energy (GOS) - Energy Deposition', fontsize=14, fontweight='bold')
#     plt.colorbar(im2, ax=axes[1], label='Energy (keV)')
#     axes[1].grid(True, alpha=0.3)
    
#     plt.tight_layout()
#     output_file = os.path.join(OUTPUT_DIR, "scan_heatmap.png")
#     plt.savefig(output_file, dpi=300, bbox_inches='tight')
#     print(f"  保存到: {output_file}")
#     plt.close()


# def create_pixel_response_curves(positions, low_data, high_data, num_pixels_to_show=5):
#     """
#     创建像素响应曲线：显示几个代表性像素随位置变化的能量响应
#     """
#     print("生成像素响应曲线...")
    
#     # 选择几个代表性像素（均匀分布）
#     pixel_indices = np.linspace(0, NUM_PIXELS-1, num_pixels_to_show, dtype=int)
    
#     fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    
#     # 低能响应曲线
#     for idx, pixel in enumerate(pixel_indices):
#         axes[0].plot(positions, low_data[:, pixel], 
#                     marker='o', markersize=3, linewidth=1.5,
#                     label=f'Pixel {pixel}')
#     axes[0].set_xlabel('Y Position (mm)', fontsize=12)
#     axes[0].set_ylabel('Energy Deposition (keV)', fontsize=12)
#     axes[0].set_title('Low Energy (GGAG) - Pixel Response Curves', fontsize=14, fontweight='bold')
#     axes[0].legend(loc='best')
#     axes[0].grid(True, alpha=0.3)
    
#     # 高能响应曲线
#     for idx, pixel in enumerate(pixel_indices):
#         axes[1].plot(positions, high_data[:, pixel], 
#                     marker='s', markersize=3, linewidth=1.5,
#                     label=f'Pixel {pixel}')
#     axes[1].set_xlabel('Y Position (mm)', fontsize=12)
#     axes[1].set_ylabel('Energy Deposition (keV)', fontsize=12)
#     axes[1].set_title('High Energy (GOS) - Pixel Response Curves', fontsize=14, fontweight='bold')
#     axes[1].legend(loc='best')
#     axes[1].grid(True, alpha=0.3)
    
#     plt.tight_layout()
#     output_file = os.path.join(OUTPUT_DIR, "pixel_response_curves.png")
#     plt.savefig(output_file, dpi=300, bbox_inches='tight')
#     print(f"  保存到: {output_file}")
#     plt.close()


# def create_total_energy_plot(positions, low_data, high_data):
#     """
#     创建总能量随位置变化的曲线
#     """
#     print("生成总能量曲线...")
    
#     # 计算每个位置的总能量
#     low_total = np.sum(low_data, axis=1)
#     high_total = np.sum(high_data, axis=1)
#     combined_total = low_total + high_total
    
#     fig, ax = plt.subplots(figsize=(10, 6))
    
#     ax.plot(positions, low_total, 'b-o', markersize=4, linewidth=2, label='Low Energy (GGAG)')
#     ax.plot(positions, high_total, 'r-s', markersize=4, linewidth=2, label='High Energy (GOS)')
#     ax.plot(positions, combined_total, 'g-^', markersize=4, linewidth=2, label='Combined Total')
    
#     ax.set_xlabel('Y Position (mm)', fontsize=12)
#     ax.set_ylabel('Total Energy Deposition (keV)', fontsize=12)
#     ax.set_title('Total Energy Deposition vs Position', fontsize=14, fontweight='bold')
#     ax.legend(loc='best')
#     ax.grid(True, alpha=0.3)
    
#     plt.tight_layout()
#     output_file = os.path.join(OUTPUT_DIR, "total_energy_vs_position.png")
#     plt.savefig(output_file, dpi=300, bbox_inches='tight')
#     print(f"  保存到: {output_file}")
#     plt.close()


# def create_position_slices(positions, low_data, high_data, num_slices=5):
#     """
#     创建几个代表性位置的像素能量分布图
#     """
#     print("生成位置切片图...")
    
#     # 选择几个代表性位置
#     position_indices = np.linspace(0, len(positions)-1, num_slices, dtype=int)
    
#     fig, axes = plt.subplots(2, num_slices, figsize=(4*num_slices, 8))
    
#     for col, pos_idx in enumerate(position_indices):
#         y_pos = positions[pos_idx]
        
#         # 低能数据
#         axes[0, col].bar(range(NUM_PIXELS), low_data[pos_idx, :], 
#                         color='blue', alpha=0.7, width=0.8)
#         axes[0, col].set_xlabel('Pixel Number', fontsize=10)
#         axes[0, col].set_ylabel('Energy (keV)', fontsize=10)
#         axes[0, col].set_title(f'Low Energy\nY = {y_pos:.1f} mm', fontsize=11)
#         axes[0, col].grid(True, alpha=0.3, axis='y')
        
#         # 高能数据
#         axes[1, col].bar(range(NUM_PIXELS), high_data[pos_idx, :], 
#                         color='red', alpha=0.7, width=0.8)
#         axes[1, col].set_xlabel('Pixel Number', fontsize=10)
#         axes[1, col].set_ylabel('Energy (keV)', fontsize=10)
#         axes[1, col].set_title(f'High Energy\nY = {y_pos:.1f} mm', fontsize=11)
#         axes[1, col].grid(True, alpha=0.3, axis='y')
    
#     plt.tight_layout()
#     output_file = os.path.join(OUTPUT_DIR, "position_slices.png")
#     plt.savefig(output_file, dpi=300, bbox_inches='tight')
#     print(f"  保存到: {output_file}")
#     plt.close()


def create_grayscale_images(positions, low_data, high_data):
    """
    创建灰度图像（0-255范围）：将能量数据归一化并保存为灰度图像
    """
    print("生成灰度图像...")
    
    def normalize_to_255(data):
        """
        将数据归一化到0-255范围
        """
        data_min = data.min()
        data_max = data.max()
        
        if data_max == data_min:
            # 如果所有值都相同，返回全零或全255
            return np.zeros_like(data, dtype=np.uint8)
        
        # 线性归一化到0-255
        normalized = ((data - data_min) / (data_max - data_min) * 255).astype(np.uint8)
        return normalized
    
    # 归一化低能数据
    low_gray = normalize_to_255(low_data.T)  # 转置以匹配图像显示方向
    high_gray = normalize_to_255(high_data.T)  # 转置以匹配图像显示方向
    
    # 保存为PNG灰度图像
    low_output = os.path.join(OUTPUT_DIR, "low_energy_grayscale.png")
    high_output = os.path.join(OUTPUT_DIR, "high_energy_grayscale.png")
    # combined_output = os.path.join(OUTPUT_DIR, "combined_energy_grayscale.png")
    
    # 保存低能灰度图像
    Image.fromarray(low_gray, mode='L').save(low_output)
    print(f"  低能灰度图像保存到: {low_output}")
    print(f"    数据范围: {low_data.min():.2f} - {low_data.max():.2f} keV")
    print(f"    图像尺寸: {low_gray.shape[1]} x {low_gray.shape[0]} (位置 x 像素)")
    
    # 保存高能灰度图像
    Image.fromarray(high_gray, mode='L').save(high_output)
    print(f"  高能灰度图像保存到: {high_output}")
    print(f"    数据范围: {high_data.min():.2f} - {high_data.max():.2f} keV")
    print(f"    图像尺寸: {high_gray.shape[1]} x {high_gray.shape[0]} (位置 x 像素)")
    
    # 保存组合能量灰度图像（低能+高能）
    # combined_data = low_data + high_data
    # combined_gray = normalize_to_255(combined_data.T)
    # Image.fromarray(combined_gray, mode='L').save(combined_output)
    # print(f"  组合能量灰度图像保存到: {combined_output}")
    # print(f"    数据范围: {combined_data.min():.2f} - {combined_data.max():.2f} keV")
    # print(f"    图像尺寸: {combined_gray.shape[1]} x {combined_gray.shape[0]} (位置 x 像素)")
    
    # 同时使用matplotlib生成带坐标轴的灰度图像（用于可视化）
    fig, axes = plt.subplots(1, 3, figsize=(18, 6))
    
    # 低能灰度图
    im1 = axes[0].imshow(low_gray, aspect='auto', origin='lower',
                        extent=[positions.min(), positions.max(), 0, NUM_PIXELS-1],
                        cmap='gray', interpolation='nearest')
    axes[0].set_xlabel('Y Position (mm)', fontsize=12)
    axes[0].set_ylabel('Pixel Number', fontsize=12)
    axes[0].set_title('Low Energy (GGAG) - Grayscale', fontsize=14, fontweight='bold')
    plt.colorbar(im1, ax=axes[0], label='Normalized Intensity (0-255)')
    axes[0].grid(True, alpha=0.3)
    
    # 高能灰度图
    im2 = axes[1].imshow(high_gray, aspect='auto', origin='lower',
                        extent=[positions.min(), positions.max(), 0, NUM_PIXELS-1],
                        cmap='gray', interpolation='nearest')
    axes[1].set_xlabel('Y Position (mm)', fontsize=12)
    axes[1].set_ylabel('Pixel Number', fontsize=12)
    axes[1].set_title('High Energy (GOS) - Grayscale', fontsize=14, fontweight='bold')
    plt.colorbar(im2, ax=axes[1], label='Normalized Intensity (0-255)')
    axes[1].grid(True, alpha=0.3)
    
    # 组合能量灰度图
    # im3 = axes[2].imshow(combined_gray, aspect='auto', origin='lower',
    #                      extent=[positions.min(), positions.max(), 0, NUM_PIXELS-1],
    #                      cmap='gray', interpolation='nearest')
    # axes[2].set_xlabel('Y Position (mm)', fontsize=12)
    # axes[2].set_ylabel('Pixel Number', fontsize=12)
    # axes[2].set_title('Combined Energy - Grayscale', fontsize=14, fontweight='bold')
    # plt.colorbar(im3, ax=axes[2], label='Normalized Intensity (0-255)')
    # axes[2].grid(True, alpha=0.3)
    
    # plt.tight_layout()
    # grayscale_plot_file = os.path.join(OUTPUT_DIR, "grayscale_images.png")
    # plt.savefig(grayscale_plot_file, dpi=300, bbox_inches='tight')
    # print(f"  灰度图像可视化保存到: {grayscale_plot_file}")
    plt.close()


def create_16bit_grayscale_images(positions, low_data, high_data):
    """
    创建16位灰度图像（0-65535范围）：将能量数据归一化并保存为16位灰度图像
    """
    print("生成16位灰度图像...")
    
    def normalize_to_65535(data):
        """
        将数据归一化到0-65535范围（16位）
        """
        data_min = data.min()
        data_max = data.max()
        
        if data_max == data_min:
            # 如果所有值都相同，返回全零
            return np.zeros_like(data, dtype=np.uint16)
        
        # 线性归一化到0-65535
        normalized = ((data - data_min) / (data_max - data_min) * 65535).astype(np.uint16)
        return normalized
    
    # 归一化低能数据
    low_gray_16bit = normalize_to_65535(low_data.T)  # 转置以匹配图像显示方向
    high_gray_16bit = normalize_to_65535(high_data.T)  # 转置以匹配图像显示方向
    
    # 保存为16位PNG灰度图像
    low_output_16bit = os.path.join(OUTPUT_DIR, "low_energy_grayscale_16bit.png")
    high_output_16bit = os.path.join(OUTPUT_DIR, "high_energy_grayscale_16bit.png")
    combined_output_16bit = os.path.join(OUTPUT_DIR, "combined_energy_grayscale_16bit.png")
    
    # 保存低能16位灰度图像
    # 使用mode='I;16'表示16位整数灰度图像
    Image.fromarray(low_gray_16bit, mode='I;16').save(low_output_16bit)
    print(f"  低能16位灰度图像保存到: {low_output_16bit}")
    print(f"    数据范围: {low_data.min():.2f} - {low_data.max():.2f} keV")
    print(f"    图像尺寸: {low_gray_16bit.shape[1]} x {low_gray_16bit.shape[0]} (位置 x 像素)")
    print(f"    灰度值范围: 0 - 65535 (16位)")
    
    # 保存高能16位灰度图像
    Image.fromarray(high_gray_16bit, mode='I;16').save(high_output_16bit)
    print(f"  高能16位灰度图像保存到: {high_output_16bit}")
    print(f"    数据范围: {high_data.min():.2f} - {high_data.max():.2f} keV")
    print(f"    图像尺寸: {high_gray_16bit.shape[1]} x {high_gray_16bit.shape[0]} (位置 x 像素)")
    print(f"    灰度值范围: 0 - 65535 (16位)")
    
    # 保存组合能量16位灰度图像（低能+高能）
    # combined_data = low_data + high_data
    # combined_gray_16bit = normalize_to_65535(combined_data.T)
    # Image.fromarray(combined_gray_16bit, mode='I;16').save(combined_output_16bit)
    # print(f"  组合能量16位灰度图像保存到: {combined_output_16bit}")
    # print(f"    数据范围: {combined_data.min():.2f} - {combined_data.max():.2f} keV")
    # print(f"    图像尺寸: {combined_gray_16bit.shape[1]} x {combined_gray_16bit.shape[0]} (位置 x 像素)")
    # print(f"    灰度值范围: 0 - 65535 (16位)")


# def save_combined_data(positions, low_data, high_data):
#     """
#     保存组合后的数据为NumPy格式
#     """
#     print("保存组合数据...")
    
#     output_file = os.path.join(OUTPUT_DIR, "combined_data.npz")
#     np.savez(output_file,
#              positions=positions,
#              low_energy=low_data,
#              high_energy=high_data,
#              num_pixels=NUM_PIXELS)
#     print(f"  保存到: {output_file}")
    
#     # 同时保存为文本格式（CSV）
#     csv_file = os.path.join(OUTPUT_DIR, "combined_data_summary.txt")
#     with open(csv_file, 'w') as f:
#         f.write("# Combined Scan Data Summary\n")
#         f.write(f"# Number of positions: {len(positions)}\n")
#         f.write(f"# Number of pixels: {NUM_PIXELS}\n")
#         f.write(f"# Position range: {positions.min():.1f} to {positions.max():.1f} mm\n")
#         f.write("#\n")
#         f.write("# Format: Position(mm) | LowEnergy_Total(keV) | HighEnergy_Total(keV) | Combined_Total(keV)\n")
#         f.write("#\n")
        
#         for i, pos in enumerate(positions):
#             low_total = np.sum(low_data[i, :])
#             high_total = np.sum(high_data[i, :])
#             combined_total = low_total + high_total
#             f.write(f"{pos:.1f}\t{low_total:.2f}\t{high_total:.2f}\t{combined_total:.2f}\n")
    
#     print(f"  摘要保存到: {csv_file}")


def main():
    """
    主函数
    """
    print("=" * 60)
    print("数据组合和可视化工具")
    print("=" * 60)
    print()
    
    # 检查输出目录是否存在
    if not os.path.exists(OUTPUT_DIR):
        print(f"错误: 输出目录 {OUTPUT_DIR} 不存在")
        print("请先运行扫描脚本: bash scan_step.sh")
        return
    
    # 加载数据
    positions, low_data, high_data = load_scan_data()
    
    if positions is None:
        print("数据加载失败，退出")
        return
    
    print()
    print("=" * 60)
    print("开始生成可视化图像...")
    print("=" * 60)
    print()
    
    # 生成各种可视化
    # create_heatmaps(positions, low_data, high_data)
    # create_pixel_response_curves(positions, low_data, high_data)
    # create_total_energy_plot(positions, low_data, high_data)
    # create_position_slices(positions, low_data, high_data)
    create_grayscale_images(positions, low_data, high_data)
    create_16bit_grayscale_images(positions, low_data, high_data)
    
    # 保存组合数据
    # save_combined_data(positions, low_data, high_data)
    
    print()
    print("=" * 60)
    print("完成！所有结果保存在:", OUTPUT_DIR)
    print("=" * 60)
    # print()
    # print("生成的文件:")
    # print("  - scan_heatmap.png: 2D热图（位置 vs 像素）")
    # print("  - pixel_response_curves.png: 像素响应曲线")
    # print("  - total_energy_vs_position.png: 总能量随位置变化")
    # print("  - position_slices.png: 代表性位置的像素分布")
    # print("  - low_energy_grayscale.png: 低能灰度图像（8位，0-255）")
    # print("  - high_energy_grayscale.png: 高能灰度图像（8位，0-255）")
    # print("  - combined_energy_grayscale.png: 组合能量灰度图像（8位，0-255）")
    # print("  - grayscale_images.png: 灰度图像可视化（带坐标轴）")
    # print("  - low_energy_grayscale_16bit.png: 低能灰度图像（16位，0-65535）")
    # print("  - high_energy_grayscale_16bit.png: 高能灰度图像（16位，0-65535）")
    # print("  - combined_energy_grayscale_16bit.png: 组合能量灰度图像（16位，0-65535）")
    # print("  - combined_data.npz: 组合数据（NumPy格式）")
    # print("  - combined_data_summary.txt: 数据摘要")


if __name__ == "__main__":
    main()

