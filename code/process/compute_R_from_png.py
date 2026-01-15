import os

import numpy as np
from PIL import Image


EPS = 1e-6
bix_1_value = 1e-3


def load_png_as_float(path: str) -> np.ndarray:
    """Load 16-bit (or 8-bit) grayscale PNG as float64 numpy array."""
    img = Image.open(path)
    # Ensure single-channel
    img = img.convert("I")  # 32-bit signed integer pixels, preserves 16-bit range
    arr = np.array(img, dtype=np.float64)
    return arr


def save_float_as_16bit_png(arr: np.ndarray, path: str, vmin: float = None, vmax: float = None) -> None:
    """
    Save a float array to 16-bit PNG.

    If vmin/vmax are not given, use arr.min()/arr.max().
    Values outside [vmin, vmax] will be clipped.
    """
    if vmin is None:
        vmin = float(np.nanmin(arr))
    if vmax is None:
        vmax = float(np.nanmax(arr))

    if vmax <= vmin:
        vmax = vmin + 1.0

    arr_clip = np.clip(arr, vmin, vmax)
    norm = (arr_clip - vmin) / (vmax - vmin)  # 0~1
    arr_16 = (norm * 65535.0 + 0.5).astype(np.uint16)

    img = Image.fromarray(arr_16, mode="I;16")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.save(path)


def compute_flat_field_from_blank(blank_img: np.ndarray) -> np.ndarray:
    """
    根据空扫图像计算平场：
    - 输入：81 x 128 的二维矩阵 blank_img
    - 操作：对行方向求平均，得到 1 x 128 的向量
    - 再将该向量复制 81 行，得到 81 x 128 的平场矩阵
    """
    # 按行求平均（axis=0），得到一行
    mean_row = np.mean(blank_img, axis=0, dtype=np.float64)
    # 复制 81 行，形状匹配原图
    flat_field = np.tile(mean_row, (blank_img.shape[0], 1))
    return flat_field


def main():
    # 路径（使用绝对路径）
    root = "/home/yyb/workspace/XRay-all/XRay-detectionCode/code"
    out_dir = os.path.join(root, "build", "output")
    blank_dir = os.path.join(root, "build", "output_blank")

    # 原始高能 / 低能 16 位灰度图（含待分选矿石）
    high_path = os.path.join(out_dir, "high_energy_grayscale_16bit.png")
    low_path = os.path.join(out_dir, "low_energy_grayscale_16bit.png")

    # 空扫（平板）高能 / 低能 16 位灰度图
    high_blank_path = os.path.join(blank_dir, "high_energy_grayscale_16bit.png")
    low_blank_path = os.path.join(blank_dir, "low_energy_grayscale_16bit.png")

    # 读入图像为 float64
    high = load_png_as_float(high_path)
    low = load_png_as_float(low_path)
    high_blank_raw = load_png_as_float(high_blank_path)
    low_blank_raw = load_png_as_float(low_blank_path)

    # === 第一步：由空扫图像计算平场（81 行求平均后再填充） ===
    bh_blank = compute_flat_field_from_blank(high_blank_raw)
    bl_blank = compute_flat_field_from_blank(low_blank_raw)

    # 安全下界，避免 0 或负数
    High_safe = np.where(high <= 0, EPS, high)
    Low_safe = np.where(low <= 0, EPS, low)

    # === 第二步：计算透射率图（0~1），作为标准化高能 / 低能图 ===
    # T = I / I0；这里做一个 +10 的平移，与后续对数形式保持一致
    T_high = (High_safe + 10.0) / (bh_blank + 10.0)
    T_low = (Low_safe + 10.0) / (bl_blank + 10.0)

    # 将透射率裁剪到 [0, 1]，并保存为 16 位 PNG（类似医院 X 光）
    T_high_clipped = np.clip(T_high, 0.0, 1.0)
    T_low_clipped = np.clip(T_low, 0.0, 1.0)

    high_trans_path = os.path.join(out_dir, "high_energy_transmission_16bit.png")
    low_trans_path = os.path.join(out_dir, "low_energy_transmission_16bit.png")
    save_float_as_16bit_png(T_high_clipped, high_trans_path, vmin=0.0, vmax=1.0)
    save_float_as_16bit_png(T_low_clipped, low_trans_path, vmin=0.0, vmax=1.0)

    # === 第三步：计算对数衰减厚度 A = -ln(T)（与你给出的公式等价） ===
    # 你的原始公式：
    # log_h = np.log((bh_blank + 10) / (High_safe + 10))
    # log_l = np.log((bl_blank + 10) / (Low_safe  + 10))
    # 这里直接用透射率来计算：
    log_h = -np.log(np.clip(T_high, EPS, None))
    log_l = -np.log(np.clip(T_low, EPS, None))

    log_h_abs = np.abs(log_h)
    log_l_abs = np.abs(log_l)

    # === 第四步：计算 R 图像 ===
    # R = (log_l_abs + bix_1_value) / (log_h_abs + bix_1_value)
    R = (log_l_abs + bix_1_value) / (log_h_abs + bix_1_value)

    # 为了可视化，把 R 线性映射到 16 位灰度
    # 这里可以根据经验给一个合理的显示范围，比如 [0.5, 2.0]，你也可以根据实际数据再调整
    R_min_display = 0.5
    R_max_display = 2.0
    R_path = os.path.join(out_dir, "R_image_16bit.png")
    save_float_as_16bit_png(R, R_path, vmin=R_min_display, vmax=R_max_display)

    print("Saved:")
    print("  Low-energy transmission image :", low_trans_path)
    print("  High-energy transmission image:", high_trans_path)
    print("  R image                       :", R_path)


if __name__ == "__main__":
    main()


