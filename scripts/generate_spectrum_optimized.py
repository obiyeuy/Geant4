#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
优化能谱生成脚本 - 用于改善Pb和H2O的分选效果

优化原理：
1. 在低能区（<50keV），光电效应占主导，Pb(Z=82)和H2O(Z_eff≈7.4)的衰减差异巨大（~15000倍）
2. 在高能区（>100keV），康普顿散射占主导，衰减差异变小（~11倍）
3. 当前160kVp能谱能量范围太宽，包含大量高能光子，导致分离度差

优化策略：
- 方案1：降低管电压（80-100kVp）- 增加低能成分，利用光电效应
- 方案2：增加过滤（硬化能谱）- 去除低能，保留中高能，增强差异
- 方案3：使用双能技术 - 两个不同的管电压
"""

import numpy as np
import spekpy
import matplotlib.pyplot as plt

def generate_optimized_spectrum_v1(filename="spectrum_optimized_v1.txt", kvp=100):
    """
    方案1：降低管电压 + 适度过滤
    优点：增加低能成分，利用光电效应差异
    适用：需要更好分离度，可接受较低穿透力
    """
    print(f"生成优化能谱方案1: {kvp}kVp (降低管电压)...")
    
    s = spekpy.Spek(kvp=kvp)
    # 适度过滤：保留更多低能成分
    s.filter('Al', 0.5)  # 减少Al过滤
    s.filter('Cu', 0.3)  # 减少Cu过滤
    
    energies, weights = s.get_spectrum()
    
    # 映射到1.0 keV步长
    target_energies = np.arange(int(min(energies)), kvp+1, 1.0)
    target_weights = np.interp(target_energies, energies, weights)
    
    # 过滤掉权重为 0 的部分
    mask = target_weights > 1e-10
    final_energies = target_energies[mask]
    final_weights = target_weights[mask]
    
    # 保存
    data = np.column_stack((final_energies, final_weights))
    np.savetxt(filename, data, fmt='%.2f  %.6e')
    print(f"成功！能谱已保存至: {filename}")
    print(f"  能量范围: {final_energies.min():.1f} - {final_energies.max():.1f} keV")
    print(f"  低能成分（<50keV）占比: {np.sum(final_weights[final_energies < 50]) / np.sum(final_weights) * 100:.1f}%")
    
    return final_energies, final_weights


def generate_optimized_spectrum_v2(filename="spectrum_optimized_v2.txt", kvp=140):
    """
    方案2：增加过滤（硬化能谱）
    优点：去除低能，保留中高能，增强Pb和H2O的差异
    适用：需要较高穿透力，同时改善分离度
    """
    print(f"生成优化能谱方案2: {kvp}kVp (增加过滤，硬化能谱)...")
    
    s = spekpy.Spek(kvp=kvp)
    # 增加过滤：去除低能，保留中高能
    s.filter('Al', 1.0)
    s.filter('Cu', 1.5)  # 增加Cu过滤（从0.5增加到1.5）
    # 可选：添加Sn或Cd过滤进一步硬化
    # s.filter('Sn', 0.2)
    
    energies, weights = s.get_spectrum()
    
    # 映射到1.0 keV步长
    target_energies = np.arange(int(min(energies)), kvp+1, 1.0)
    target_weights = np.interp(target_energies, energies, weights)
    
    # 过滤掉权重为 0 的部分
    mask = target_weights > 1e-10
    final_energies = target_energies[mask]
    final_weights = target_weights[mask]
    
    # 保存
    data = np.column_stack((final_energies, final_weights))
    np.savetxt(filename, data, fmt='%.2f  %.6e')
    print(f"成功！能谱已保存至: {filename}")
    print(f"  能量范围: {final_energies.min():.1f} - {final_energies.max():.1f} keV")
    print(f"  中高能成分（50-120keV）占比: {np.sum(final_weights[(final_energies >= 50) & (final_energies <= 120)]) / np.sum(final_weights) * 100:.1f}%")
    
    return final_energies, final_weights


def generate_optimized_spectrum_v3_low(filename="spectrum_low_energy.txt", kvp=80):
    """
    方案3a：双能技术 - 低能能谱
    用于低能探测器
    """
    print(f"生成双能低能谱: {kvp}kVp...")
    
    s = spekpy.Spek(kvp=kvp)
    # 最小过滤，保留低能成分
    s.filter('Al', 0.5)
    # 不添加Cu过滤，保留更多低能
    
    energies, weights = s.get_spectrum()
    
    target_energies = np.arange(int(min(energies)), kvp+1, 1.0)
    target_weights = np.interp(target_energies, energies, weights)
    
    mask = target_weights > 1e-10
    final_energies = target_energies[mask]
    final_weights = target_weights[mask]
    
    data = np.column_stack((final_energies, final_weights))
    np.savetxt(filename, data, fmt='%.2f  %.6e')
    print(f"成功！低能谱已保存至: {filename}")
    
    return final_energies, final_weights


def generate_optimized_spectrum_v3_high(filename="spectrum_high_energy.txt", kvp=140):
    """
    方案3b：双能技术 - 高能能谱
    用于高能探测器
    """
    print(f"生成双能高能谱: {kvp}kVp...")
    
    s = spekpy.Spek(kvp=kvp)
    # 厚过滤，去除低能
    s.filter('Al', 1.0)
    s.filter('Cu', 2.0)  # 厚Cu过滤
    
    energies, weights = s.get_spectrum()
    
    target_energies = np.arange(int(min(energies)), kvp+1, 1.0)
    target_weights = np.interp(target_energies, energies, weights)
    
    mask = target_weights > 1e-10
    final_energies = target_energies[mask]
    final_weights = target_weights[mask]
    
    data = np.column_stack((final_energies, final_weights))
    np.savetxt(filename, data, fmt='%.2f  %.6e')
    print(f"成功！高能谱已保存至: {filename}")
    
    return final_energies, final_weights


def compare_spectra():
    """
    对比不同能谱方案
    """
    print("\n" + "="*60)
    print("能谱优化方案对比")
    print("="*60)
    
    # 生成所有方案
    e1, w1 = generate_optimized_spectrum_v1("spectrum_v1_100kvp.txt", kvp=100)
    e2, w2 = generate_optimized_spectrum_v2("spectrum_v2_140kvp_hard.txt", kvp=140)
    e3_low, w3_low = generate_optimized_spectrum_v3_low("spectrum_v3_low_80kvp.txt", kvp=80)
    e3_high, w3_high = generate_optimized_spectrum_v3_high("spectrum_v3_high_140kvp.txt", kvp=140)
    
    # 绘制对比图
    plt.figure(figsize=(14, 8))
    
    plt.subplot(2, 1, 1)
    plt.plot(e1, w1/np.max(w1), label='方案1: 100kVp (低过滤)', linewidth=2, alpha=0.8)
    plt.plot(e2, w2/np.max(w2), label='方案2: 140kVp (高过滤)', linewidth=2, alpha=0.8)
    plt.plot(e3_low, w3_low/np.max(w3_low), label='方案3: 80kVp (低能)', linewidth=2, alpha=0.8, linestyle='--')
    plt.plot(e3_high, w3_high/np.max(w3_high), label='方案3: 140kVp (高能)', linewidth=2, alpha=0.8, linestyle='--')
    plt.xlabel('Photon Energy (keV)', fontsize=12)
    plt.ylabel('Normalized Fluence', fontsize=12)
    plt.title('能谱优化方案对比', fontsize=14, fontweight='bold')
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    # 标注关键能量区域
    plt.axvline(x=50, color='red', linestyle=':', alpha=0.5, label='50keV (光电/康普顿分界)')
    plt.axvline(x=100, color='orange', linestyle=':', alpha=0.5, label='100keV (高能区起点)')
    
    plt.subplot(2, 1, 2)
    # 计算各能量区间的权重占比
    energy_ranges = [
        ('<50keV\n(光电效应区)', 0, 50),
        ('50-100keV\n(混合区)', 50, 100),
        ('>100keV\n(康普顿区)', 100, 200)
    ]
    
    schemes = [
        ('方案1\n100kVp', w1, e1),
        ('方案2\n140kVp', w2, e2),
        ('方案3低\n80kVp', w3_low, e3_low),
        ('方案3高\n140kVp', w3_high, e3_high)
    ]
    
    x = np.arange(len(schemes))
    width = 0.25
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c']
    
    for i, (label, low, high) in enumerate(energy_ranges):
        values = []
        for name, weights, energies in schemes:
            mask = (energies >= low) & (energies < high)
            if np.any(mask):
                values.append(np.sum(weights[mask]) / np.sum(weights) * 100)
            else:
                values.append(0)
        plt.bar(x + i*width, values, width, label=label, color=colors[i], alpha=0.8)
    
    plt.xlabel('能谱方案', fontsize=12)
    plt.ylabel('能量占比 (%)', fontsize=12)
    plt.title('各能量区间的权重占比', fontsize=12, fontweight='bold')
    plt.xticks(x + width, [s[0] for s in schemes])
    plt.legend()
    plt.grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    plt.savefig("spectrum_comparison.png", dpi=300, bbox_inches='tight')
    print("\n对比图已保存至: spectrum_comparison.png")
    plt.show()


if __name__ == "__main__":
    print("="*60)
    print("能谱优化工具 - 改善Pb和H2O分选效果")
    print("="*60)
    print("\n推荐方案：")
    print("  方案1：100kVp + 低过滤 - 增加低能成分，利用光电效应")
    print("  方案2：140kVp + 高过滤 - 硬化能谱，去除低能噪声")
    print("  方案3：双能技术 - 80kVp(低能) + 140kVp(高能)")
    print("\n" + "="*60 + "\n")
    
    try:
        compare_spectra()
    except Exception as err:
        print(f"程序运行出错: {err}")
        import traceback
        traceback.print_exc()



