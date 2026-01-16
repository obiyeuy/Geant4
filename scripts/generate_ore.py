#!/usr/bin/env python3
"""
复杂矿石生成器 - 基于 pyg4ometry
实现不规则形状基体和浸染状颗粒的生成式建模
"""

import pyg4ometry.geant4 as pyg4g4
import pyg4ometry.gdml as pyg4gdml
import numpy as np
import argparse
import os
import sys


def check_point_in_ellipsoid(point, center, radii):
    """
    检查点是否在椭球内部
    椭球方程: (x-cx)^2/a^2 + (y-cy)^2/b^2 + (z-cz)^2/c^2 <= 1
    """
    dx, dy, dz = point[0] - center[0], point[1] - center[1], point[2] - center[2]
    a, b, c = radii[0], radii[1], radii[2]
    return (dx*dx)/(a*a) + (dy*dy)/(b*b) + (dz*dz)/(c*c) <= 1.0


def check_sphere_in_ellipsoid(sphere_center, sphere_radius, ellipsoid_center, ellipsoid_radii):
    """
    检查整个球体是否完全在椭球内部
    方法：检查球体上多个关键点，确保它们都在椭球内
    """
    dx = sphere_center[0] - ellipsoid_center[0]
    dy = sphere_center[1] - ellipsoid_center[1]
    dz = sphere_center[2] - ellipsoid_center[2]
    a, b, c = ellipsoid_radii[0], ellipsoid_radii[1], ellipsoid_radii[2]
    
    # 首先检查球体中心是否在椭球内
    center_value = (dx*dx)/(a*a) + (dy*dy)/(b*b) + (dz*dz)/(c*c)
    if center_value > 1.0:
        return False
    
    # 如果球体中心在椭球中心，检查最小半径是否足够
    if abs(dx) < 1e-10 and abs(dy) < 1e-10 and abs(dz) < 1e-10:
        min_radius = min(a, b, c)
        return sphere_radius < min_radius
    
    # 检查球体上多个关键点，确保它们都在椭球内
    # 1. 在从椭球中心到球体中心的方向上的最远点
    direction = np.array([dx, dy, dz])
    direction_norm = np.linalg.norm(direction)
    if direction_norm > 1e-10:
        direction_unit = direction / direction_norm
        farthest_point = np.array(sphere_center) + direction_unit * sphere_radius
        dfx = farthest_point[0] - ellipsoid_center[0]
        dfy = farthest_point[1] - ellipsoid_center[1]
        dfz = farthest_point[2] - ellipsoid_center[2]
        farthest_value = (dfx*dfx)/(a*a) + (dfy*dfy)/(b*b) + (dfz*dfz)/(c*c)
        if farthest_value > 1.0:
            return False
    
    # 2. 在各个坐标轴方向上的最远点（更保守的检查）
    # 检查 x, y, z 正负方向上的点
    test_points = [
        [sphere_center[0] + sphere_radius, sphere_center[1], sphere_center[2]],
        [sphere_center[0] - sphere_radius, sphere_center[1], sphere_center[2]],
        [sphere_center[0], sphere_center[1] + sphere_radius, sphere_center[2]],
        [sphere_center[0], sphere_center[1] - sphere_radius, sphere_center[2]],
        [sphere_center[0], sphere_center[1], sphere_center[2] + sphere_radius],
        [sphere_center[0], sphere_center[1], sphere_center[2] - sphere_radius],
    ]
    
    for point in test_points:
        px = point[0] - ellipsoid_center[0]
        py = point[1] - ellipsoid_center[1]
        pz = point[2] - ellipsoid_center[2]
        point_value = (px*px)/(a*a) + (py*py)/(b*b) + (pz*pz)/(c*c)
        if point_value > 1.0:
            return False
    
    # 所有关键点都在椭球内，返回 True
    return True


def check_overlap(point, radius, existing_particles, min_distance_factor=1.1):
    """
    检查新颗粒是否与已有颗粒重叠
    min_distance_factor: 最小距离因子，避免颗粒过于紧密
    """
    for existing_pos, existing_r in existing_particles:
        distance = np.linalg.norm(np.array(point) - np.array(existing_pos))
        min_distance = (radius + existing_r) * min_distance_factor
        if distance < min_distance:
            return True
    return False


def generate_irregular_matrix(reg, name_base="matrix", num_ellipsoids=3):
    """
    生成不规则基体：使用多个椭球进行布尔并集操作
    简化实现：使用单个椭球，后续可以扩展为多个椭球的并集
    
    Returns:
        tuple: (ellipsoid_solid, radii) - 椭球实体和半径列表 [rx, ry, rz]
    """
    # 简化实现：使用单个椭球，参数随机化以模拟不规则
    # 实际应用中可以使用多个椭球的布尔并集
    
    # 椭球半径（不规则）
    radius_x = np.random.uniform(8, 12)  # mm
    radius_y = np.random.uniform(8, 12)
    radius_z = np.random.uniform(8, 12)
    
    # 创建椭球实体
    # Ellipsoid 参数: name, pxSemiAxis, pySemiAxis, pzSemiAxis, pzBottomCut, pzTopCut, registry
    # pzBottomCut 和 pzTopCut 用于切割椭球
    # 修正：pzBottomCut 设置为 -radius_z 以创建完整的椭球（之前是 0.0，导致只生成了半个椭球）
    ellipsoid = pyg4g4.solid.Ellipsoid(
        f"{name_base}_ellipsoid",
        radius_x,  # pxSemiAxis
        radius_y,  # pySemiAxis
        radius_z,  # pzSemiAxis
        -radius_z, # pzBottomCut (底部切割，-radius_z 表示保留下半部分) [修正处]
        radius_z,  # pzTopCut (顶部切割，radius_z 表示不切割)
        reg        # registry
    )
    
    return ellipsoid, [radius_x, radius_y, radius_z]


def generate_inclusions(reg, matrix_center, safe_radii, actual_radii,
                        num_particles=1000, particle_radius=1.0):
    """
    使用拒绝采样在基体内植入颗粒（浸染体）
    
    Args:
        reg: pyg4ometry registry
        matrix_center: 基体中心 [x, y, z]
        safe_radii: 安全采样半径（已考虑颗粒大小）[rx, ry, rz]
        actual_radii: 实际椭球半径（用于检查点是否在基体内）[rx, ry, rz]
        num_particles: 目标颗粒数量
        particle_radius: 颗粒半径 (mm)
    
    Returns:
        list: 颗粒位置和半径的列表 [(pos, radius), ...]
    """
    particles = []
    max_attempts = num_particles * 20  # 最大尝试次数
    attempts = 0
    
    # 计算包围盒（使用安全半径，确保颗粒中心在基体内）
    bbox_min = np.array(matrix_center) - np.array(safe_radii)
    bbox_max = np.array(matrix_center) + np.array(safe_radii)
    
    print(f"开始生成 {num_particles} 个颗粒...")
    print(f"采样范围: [{bbox_min}, {bbox_max}]")
    
    while len(particles) < num_particles and attempts < max_attempts:
        attempts += 1
        
        # 在包围盒内随机采样
        point = [
            np.random.uniform(bbox_min[0], bbox_max[0]),
            np.random.uniform(bbox_min[1], bbox_max[1]),
            np.random.uniform(bbox_min[2], bbox_max[2])
        ]
        
        # 使用严格的检查：确保整个球体都在椭球内
        if not check_sphere_in_ellipsoid(point, particle_radius, matrix_center, actual_radii):
            continue
        
        # 检查是否与已有颗粒重叠
        if check_overlap(point, particle_radius, particles):
            continue
        
        # 接受这个颗粒
        particles.append((point, particle_radius))
        
        if len(particles) % 100 == 0:
            print(f"已生成 {len(particles)}/{num_particles} 个颗粒...")
    
    print(f"颗粒生成完成：共 {len(particles)} 个颗粒（尝试次数: {attempts}）")
    
    return particles


def create_ore_with_inclusions(output_path, matrix_material="CalciumPhosphate",
                               inclusion_material="G4_Pb", num_ellipsoids=3,
                               num_particles=1000, particle_radius=1.0):
    """
    创建包含浸染体的复杂矿石模型
    
    Args:
        output_path: 输出 GDML 文件路径
        matrix_material: 基体材质名称
        inclusion_material: 颗粒材质名称
        num_ellipsoids: 基体椭球数量（当前实现中未使用，保留用于未来扩展）
        num_particles: 颗粒数量
        particle_radius: 颗粒半径 (mm)
    
    Returns:
        dict: 包含矿石信息的字典（品位、颗粒数量等）
    """
    # 创建注册表
    reg = pyg4g4.Registry()
    
    # 创建基体（不规则形状）
    print("生成不规则基体...")
    matrix_solid, matrix_radii = generate_irregular_matrix(reg, "matrix", num_ellipsoids)
    
    # 基体中心（用于采样）
    matrix_center = [0, 0, 0]  # 假设基体中心在原点
    # 使用实际椭球半径，并缩小采样范围以确保颗粒在基体内部
    # 考虑颗粒半径，采样范围应该比椭球半径小一些
    max_particle_radius = particle_radius
    safe_radii = [max(0, r - max_particle_radius * 1.5) for r in matrix_radii]
    print(f"椭球半径: {matrix_radii} mm")
    print(f"安全采样半径（考虑颗粒大小）: {safe_radii} mm")
    
    # 生成浸染体位置（传入安全半径和实际半径）
    particles = generate_inclusions(
        reg, matrix_center, safe_radii, matrix_radii,
        num_particles, particle_radius
    )
    actual_num_particles = len(particles)
    
    # 创建基体材质
    # 如果材质是自定义的（如 CalciumPhosphate），需要手动创建
    if matrix_material == "CalciumPhosphate":
        # 创建自定义材质：Ca3(PO4)2，密度 2.9 g/cm³
        # 首先创建或获取元素
        # ElementSimple 参数: name, symbol, Z (原子序数), A (原子量), registry
        elCa = pyg4g4.ElementSimple("Ca", "Ca", 20, 40.078, reg)  # 钙，Z=20, A=40.078
        elP = pyg4g4.ElementSimple("P", "P", 15, 30.974, reg)     # 磷，Z=15, A=30.974
        elO = pyg4g4.ElementSimple("O", "O", 8, 15.999, reg)     # 氧，Z=8, A=15.999
        
        # 创建材质：Ca3(PO4)2 = 3*Ca + 2*P + 8*O
        # 密度：2.9 g/cm³，使用原子数方式（与 C++ 代码一致）
        matrix_mat = pyg4g4.MaterialCompound(
            "CalciumPhosphate",
            2.9,  # 密度 g/cm³
            3,    # 元素数量
            reg
        )
        # 使用原子数方式添加元素（与 C++ 的 AddElement(el, natoms) 对应）
        # C++: AddElement(elCa, 3); AddElement(elP, 2); AddElement(elO, 8);
        matrix_mat.add_element_natoms(elCa, 3)
        matrix_mat.add_element_natoms(elP, 2)
        matrix_mat.add_element_natoms(elO, 8)
    else:
        # 使用 NIST 预定义材质
        try:
            matrix_mat = pyg4g4.MaterialPredefined(matrix_material, reg)
        except ValueError as e:
            print(f"错误: {e}")
            print(f"提示: '{matrix_material}' 不是 NIST 预定义材质。")
            print("请使用 NIST 材质（如 G4_Fe, G4_Si, G4_Ca 等）或使用 'CalciumPhosphate'")
            raise
    
    # 创建基体逻辑体积（先使用基体实体）
    matrix_lv = pyg4g4.LogicalVolume(
        matrix_solid,
        matrix_mat,
        "OreLog",  # 强制命名为 OreLog（与 C++ 约定一致）
        reg
    )
    
    # 创建颗粒材质
    inclusion_mat = pyg4g4.MaterialPredefined(inclusion_material, reg)
    
    # 将颗粒作为子体积添加到基体中
    # 注意：对于大量颗粒，这种方法可能性能较差，但更简单可靠
    for i, (pos, radius) in enumerate(particles):
        # 创建颗粒实体
        # Sphere 参数: name, pRMin, pRMax, pSPhi, pDPhi, pSTheta, pDTheta, registry
        # 完整球体: RMin=0, RMax=radius, SPhi=0, DPhi=2*pi, STheta=0, DTheta=pi
        sphere_solid = pyg4g4.solid.Sphere(
            f"inclusion_{i}",
            0.0,           # pRMin (内半径，0 表示实心球)
            radius,       # pRMax (外半径)
            0.0,          # pSPhi (起始方位角)
            2.0 * np.pi,  # pDPhi (方位角范围)
            0.0,          # pSTheta (起始极角)
            np.pi,        # pDTheta (极角范围)
            reg           # registry
        )
        
        # 创建颗粒逻辑体积
        sphere_lv = pyg4g4.LogicalVolume(
            sphere_solid,
            inclusion_mat,
            f"inclusion_lv_{i}",
            reg
        )
        
        # 将颗粒放置到基体中
        pyg4g4.PhysicalVolume(
            [0, 0, 0],  # rotation
            pos,  # position (mm)
            sphere_lv,
            f"inclusion_pv_{i}",
            matrix_lv,  # parent volume
            reg
        )
    
    # 创建世界体积（必需）
    # Box 参数: name, pX, pY, pZ, registry
    world_solid = pyg4g4.solid.Box("world", 1000, 1000, 1000, reg)
    world_mat = pyg4g4.MaterialPredefined("G4_Galactic", reg)
    world_lv = pyg4g4.LogicalVolume(world_solid, world_mat, "world", reg)
    
    # 将矿石放置到世界中
    pyg4g4.PhysicalVolume(
        [0, 0, 0],  # rotation
        [0, 0, 0],  # position
        matrix_lv,
        "OrePV",
        world_lv,
        reg
    )
    
    # 设置世界体积
    reg.setWorld(world_lv.name)
    
    # 写入 GDML 文件
    print(f"写入 GDML 文件: {output_path}")
    w = pyg4gdml.Writer()
    w.addDetector(reg)
    w.write(output_path)
    
    # 计算品位（简化：基于颗粒体积占比）
    particle_volume = (4.0/3.0) * np.pi * (particle_radius ** 3) * actual_num_particles
    matrix_volume_approx = (4.0/3.0) * np.pi * matrix_radii[0] * matrix_radii[1] * matrix_radii[2]
    grade = particle_volume / (particle_volume + matrix_volume_approx) if (particle_volume + matrix_volume_approx) > 0 else 0.0
    
    info = {
        "num_particles": actual_num_particles,
        "particle_radius_mm": particle_radius,
        "matrix_material": matrix_material,
        "inclusion_material": inclusion_material,
        "grade": grade,
        "gdml_file": output_path
    }
    
    print(f"矿石生成完成！")
    print(f"  颗粒数量: {actual_num_particles}")
    print(f"  估算品位: {grade:.4f}")
    
    return info


def main():
    parser = argparse.ArgumentParser(description="生成复杂矿石 GDML 文件")
    parser.add_argument("--output", "-o", type=str, default="ore.gdml",
                       help="输出 GDML 文件路径")
    parser.add_argument("--matrix-material", type=str, default="CalciumPhosphate",
                       help="基体材质名称")
    parser.add_argument("--inclusion-material", type=str, default="G4_Pb",
                       help="颗粒材质名称")
    parser.add_argument("--num-ellipsoids", type=int, default=3,
                       help="基体椭球数量")
    parser.add_argument("--num-particles", type=int, default=1000,
                       help="颗粒数量")
    parser.add_argument("--particle-radius", type=float, default=1.0,
                       help="颗粒半径 (mm)")
    
    args = parser.parse_args()
    
    # 确保输出目录存在
    output_dir = os.path.dirname(os.path.abspath(args.output))
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # 生成矿石
    info = create_ore_with_inclusions(
        os.path.abspath(args.output),
        args.matrix_material,
        args.inclusion_material,
        args.num_ellipsoids,
        args.num_particles,
        args.particle_radius
    )
    
    print(f"\n矿石信息:")
    for key, value in info.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    main()