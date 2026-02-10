import numpy as np
import spekpy
import matplotlib.pyplot as plt

def generate_safe_spectrum(filename="spectrum.txt"):
    print("正在调用 SpekPy 生成 160kVp 能谱 (最兼容模式)...")
    
    # 1. 初始化 (160kVp, 默认钨靶)
    s = spekpy.Spek(kvp=160) 
    
    # 2. 添加过滤 (1.0mm Al 固有 + 0.5mm Cu 外部)
    s.filter('Al', 1.0)
    s.filter('Cu', 1.5)
    
    # 3. 获取数据 (不传参数，避开 dk 或 ener_step 错误)
    # 这将返回 SpekPy 默认分辨率的能谱 (通常是 0.5 keV)
    energies, weights = s.get_spectrum()
    
    # 4. 数据处理：确保从 1keV 开始，步长为 1.0
    # 我们使用 np.interp 将原始数据映射到你想要的 1.0 keV 步长上
    target_energies = np.arange(int(min(energies)), 161, 1.0)
    target_weights = np.interp(target_energies, energies, weights)
    
    # 5. 过滤掉权重为 0 的部分
    mask = target_weights > 1e-10 # 剔除极小值
    final_energies = target_energies[mask]
    final_weights = target_weights[mask]
    
    # 6. 保存 TXT
    data = np.column_stack((final_energies, final_weights))
    np.savetxt(filename, data, fmt='%.2f  %.6e')
    print(f"成功！能谱数据已保存至: {filename} (步长: 1.0 keV)")
    
    return final_energies, final_weights

def plot_spectrum(energies, weights):
    plt.figure(figsize=(10, 6))
    
    # 绘制能谱主曲线
    plt.plot(energies, weights, label='160kVp (1mm Al + 0.5mm Cu)', color='#1f77b4', linewidth=2)
    plt.fill_between(energies, weights, color='#1f77b4', alpha=0.1)
    
    # 标注钨的特征辐射峰 (W K-shell peaks)
    plt.annotate('K-alpha', xy=(59.3, max(weights)*0.8), xytext=(40, max(weights)*0.9),
                 arrowprops=dict(facecolor='black', shrink=0.05, width=1))
    plt.annotate('K-beta', xy=(67.2, max(weights)*0.4), xytext=(80, max(weights)*0.5),
                 arrowprops=dict(facecolor='black', shrink=0.05, width=1))

    plt.title("X-ray Spectrum for Geant4 Simulation (160 kVp)", fontsize=14)
    plt.xlabel("Photon Energy (keV)", fontsize=12)
    plt.ylabel("Photon Fluence (relative)", fontsize=12)
    plt.grid(True, which='both', linestyle=':', alpha=0.7)
    plt.legend()
    
    # 保存图片
    plt.savefig("spectrum_plot.png", dpi=300)
    print("能谱对比图已保存为: spectrum_plot.png")
    plt.show()

if __name__ == "__main__":
    try:
        e, w = generate_safe_spectrum()
        plot_spectrum(e, w)
    except Exception as err:
        print(f"程序运行出错: {err}")