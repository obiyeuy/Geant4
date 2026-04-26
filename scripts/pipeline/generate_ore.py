#!/usr/bin/env python3
"""
复杂棱角矿石生成器 - 基于 pyg4ometry
通过“并集 + 随机切割（Boolean Subtraction）”构造具有断裂面的碎石感矿石。
"""

import pyg4ometry.geant4 as pyg4g4
import pyg4ometry.gdml as pyg4gdml
import numpy as np
import argparse
import time
try:
    from scipy.spatial import ConvexHull
except Exception:
    ConvexHull = None


def _log(msg: str) -> None:
    print(f"[generate] {msg}")


def _log_debug(msg: str) -> None:
    print(f"[generate][tess-debug] {msg}")


def probe_triangularfacet_support():
    """
    检测当前环境是否具备 TriangularFacet 所需能力。
    返回:
      {
        "ok": bool,
        "has_scipy": bool,
        "has_tessellated_solid": bool,
        "has_triangular_facet": bool,
        "has_create_tessellated_solid": bool,
        "reason": str,
      }
    """
    has_scipy = ConvexHull is not None
    has_tessellated_solid = hasattr(pyg4g4.solid, "TessellatedSolid")
    has_triangular_facet = hasattr(pyg4g4.solid, "TriangularFacet")
    has_create_tess = hasattr(pyg4g4.solid, "createTessellatedSolid")

    if not has_scipy:
        reason = "缺少 scipy.spatial.ConvexHull"
    elif not has_tessellated_solid:
        reason = "pyg4ometry.geant4.solid 缺少 TessellatedSolid"
    elif not has_triangular_facet:
        reason = (
            "pyg4ometry.geant4.solid 缺少 TriangularFacet（通常表示未启用原生扩展或版本不兼容）"
        )
    else:
        reason = "TriangularFacet 可用"

    return {
        "ok": has_scipy and has_tessellated_solid and has_triangular_facet,
        "has_scipy": has_scipy,
        "has_tessellated_solid": has_tessellated_solid,
        "has_triangular_facet": has_triangular_facet,
        "has_create_tessellated_solid": has_create_tess,
        "reason": reason,
    }

def _make_rotation(reg, name, rx, ry, rz):
    """兼容性旋转定义"""
    if hasattr(pyg4g4, "d3"):
        return pyg4g4.d3.Rotation(name, rx, ry, rz)
    defines = getattr(pyg4gdml, "Defines", None)
    if defines is not None and hasattr(defines, "Rotation"):
        return defines.Rotation(name, rx, ry, rz, "rad", reg)
    return [rx, ry, rz]

def _make_position(reg, name, x, y, z):
    """兼容性位移定义"""
    if hasattr(pyg4g4, "d3"):
        return pyg4g4.d3.Position(name, x, y, z)
    defines = getattr(pyg4gdml, "Defines", None)
    if defines is not None and hasattr(defines, "Position"):
        return defines.Position(name, x, y, z, "mm", reg)
    return [x, y, z]

def _make_union(reg, name, obj1, obj2, rot, pos):
    """执行布尔并集操作"""
    try:
        return pyg4g4.solid.Union(name, obj1, obj2, [rot, pos], reg)
    except TypeError:
        return pyg4g4.solid.Union(name, obj1, obj2, rot, pos, reg)

def _make_subtraction(reg, name, obj1, obj2, rot, pos):
    """执行布尔减操作"""
    try:
        return pyg4g4.solid.Subtraction(name, obj1, obj2, [rot, pos], reg)
    except TypeError:
        return pyg4g4.solid.Subtraction(name, obj1, obj2, rot, pos, reg)

def _clip(value, low, high):
    return max(low, min(value, high))

def _parse_material_mix(mix_spec):
    """
    解析混合材质字符串:
    例: "CalciumPhosphate:70,G4_Si:30"
    返回: [(name, fraction), ...]，fraction 为 0~1 的质量分数。
    """
    if not mix_spec:
        return []

    pairs = []
    for item in mix_spec.split(","):
        token = item.strip()
        if not token:
            continue
        if ":" not in token:
            raise ValueError(f"无效混合项 '{token}'，应为 名称:百分比")
        name, pct = token.split(":", 1)
        name = name.strip()
        pct_value = float(pct.strip())
        if pct_value < 0:
            raise ValueError(f"混合项 '{token}' 百分比必须 >= 0")
        pairs.append((name, pct_value))

    if not pairs:
        raise ValueError("mix 为空，请提供至少一个材质项")

    total_pct = sum(p for _, p in pairs)
    if total_pct <= 0:
        raise ValueError("mix 百分比总和必须 > 0")
    # 允许 0% 组分，便于保持 ore/waste 的元数据结构一致。
    return [(name, pct / total_pct) for name, pct in pairs]

def _build_material(reg, material_name, cache):
    """按名称构建并缓存材质。"""
    if material_name in cache:
        return cache[material_name]

    if material_name == "CalciumPhosphate":
        el_ca = cache.get("__el_ca")
        el_p = cache.get("__el_p")
        el_o = cache.get("__el_o")
        if el_ca is None:
            el_ca = pyg4g4.ElementSimple("Ca", "Ca", 20, 40.078, reg)
            el_p = pyg4g4.ElementSimple("P", "P", 15, 30.974, reg)
            el_o = pyg4g4.ElementSimple("O", "O", 8, 15.999, reg)
            cache["__el_ca"] = el_ca
            cache["__el_p"] = el_p
            cache["__el_o"] = el_o

        mat = pyg4g4.MaterialCompound("CalciumPhosphate", 2.9, 3, reg)
        mat.add_element_natoms(el_ca, 3)
        mat.add_element_natoms(el_p, 2)
        mat.add_element_natoms(el_o, 8)
    elif material_name == "G4_PbS":
        el_pb = cache.get("__el_pb")
        el_s = cache.get("__el_s")
        if el_pb is None:
            el_pb = pyg4g4.ElementSimple("Pb", "Pb", 82, 207.2, reg)
            el_s = pyg4g4.ElementSimple("S", "S", 16, 32.06, reg)
            cache["__el_pb"] = el_pb
            cache["__el_s"] = el_s
        mat = pyg4g4.MaterialCompound("G4_PbS", 7.6, 2, reg)
        mat.add_element_natoms(el_pb, 1)
        mat.add_element_natoms(el_s, 1)
    else:
        mat = pyg4g4.MaterialPredefined(material_name, reg)

    cache[material_name] = mat
    return mat

def generate_tessellated_ore(
    reg,
    name="RuggedOreTess",
    n_points=18,
    scale=18.0,
    debug=False,
    allow_unsafe_create_tess=False,
):
    """
    ROOT 兼容优先的碎石形状：
    使用随机点云凸包 + TessellatedSolid，形成天然棱角断裂面。
    """
    n_points = int(_clip(n_points, 15, 20))
    scale = float(_clip(scale, 15.0, 20.0))

    if ConvexHull is None:
        return None

    has_triangular_facet = hasattr(pyg4g4.solid, "TriangularFacet")
    has_tessellated_solid = hasattr(pyg4g4.solid, "TessellatedSolid")
    has_create_tess = hasattr(pyg4g4.solid, "createTessellatedSolid")
    if not has_tessellated_solid:
        return None
    if not has_triangular_facet and not has_create_tess:
        if debug:
            _log_debug("both TriangularFacet and createTessellatedSolid unavailable")
        return None

    def _sample_well_spaced_points(target_n):
        """
        在椭球面附近采样并限制最小点间距，减少细长三角面和近退化面。
        """
        ax = np.random.uniform(0.75, 1.35)
        ay = np.random.uniform(0.65, 1.30)
        az = np.random.uniform(0.75, 1.40)
        # 强化点间距，尽量避免后续出现近重合顶点导致的退化三角面
        min_dist = max(0.35, scale * 0.10)
        out = []
        max_trials = target_n * 180
        for _ in range(max_trials):
            if len(out) >= target_n:
                break
            phi = np.random.uniform(0.0, 2.0 * np.pi)
            cos_theta = np.random.uniform(-1.0, 1.0)
            theta = np.arccos(cos_theta)
            # 让采样更贴近外壳，避免凸包顶点数过低导致“碎片化/过简”形状
            rr = scale * np.random.uniform(0.86, 1.0)
            p = np.array(
                [
                    rr * np.sin(theta) * np.cos(phi) * ax,
                    rr * np.sin(theta) * np.sin(phi) * ay,
                    rr * np.cos(theta) * az,
                ],
                dtype=np.float64,
            )
            if all(float(np.linalg.norm(p - q)) >= min_dist for q in out):
                out.append(p)
        # 顶点数必须精确匹配，避免凸包输入数量波动造成壳体质量不稳定
        if len(out) != target_n:
            return np.empty((0, 3), dtype=np.float64)
        return np.asarray(out, dtype=np.float64)

    # Geant4 导航对超瘦三角面较敏感；提高阈值可显著降低 stuck-track 警告
    min_edge = max(0.32, scale * 0.037)
    min_height = max(0.18, scale * 0.021)
    min_area = max(0.10, min_edge * min_edge * 0.38)
    min_angle_deg = 10.0

    def _oriented_triangle(points_local, centroid_local, i0, i1, i2):
        """统一三角面朝向：法向尽量朝外，避免渲染出现“中空/漏面”假象。"""
        p1 = points_local[int(i0)]
        p2 = points_local[int(i1)]
        p3 = points_local[int(i2)]
        normal = np.cross(p2 - p1, p3 - p1)
        face_center = (p1 + p2 + p3) / 3.0
        # 若法向指向几何中心，反转顶点顺序
        if float(np.dot(normal, face_center - centroid_local)) < 0.0:
            p2, p3 = p3, p2
        return p1, p2, p3

    def _is_degenerate_triangle(p1, p2, p3):
        e12 = float(np.linalg.norm(p1 - p2))
        e23 = float(np.linalg.norm(p2 - p3))
        e31 = float(np.linalg.norm(p3 - p1))
        if e12 < min_edge or e23 < min_edge or e31 < min_edge:
            return True
        area = float(np.linalg.norm(np.cross(p2 - p1, p3 - p1)) * 0.5)
        if area < min_area:
            return True
        longest = max(e12, e23, e31)
        # 三角形最小高，过滤“细长针状面”
        min_altitude = 2.0 * area / max(longest, 1e-9)
        if min_altitude < min_height:
            return True
        # 角度下限约束，直接剔除“针尖三角面”
        cos1 = (e12 * e12 + e31 * e31 - e23 * e23) / max(2.0 * e12 * e31, 1e-9)
        cos2 = (e12 * e12 + e23 * e23 - e31 * e31) / max(2.0 * e12 * e23, 1e-9)
        cos3 = (e23 * e23 + e31 * e31 - e12 * e12) / max(2.0 * e23 * e31, 1e-9)
        a1 = float(np.degrees(np.arccos(np.clip(cos1, -1.0, 1.0))))
        a2 = float(np.degrees(np.arccos(np.clip(cos2, -1.0, 1.0))))
        a3 = float(np.degrees(np.arccos(np.clip(cos3, -1.0, 1.0))))
        if min(a1, a2, a3) < min_angle_deg:
            return True
        # 归一化形状质量（1=等边，0=退化）
        quality = (4.0 * np.sqrt(3.0) * area) / max(e12 * e12 + e23 * e23 + e31 * e31, 1e-9)
        return quality < 0.045

    polygons = None
    reject_stats = {
        "sample_count_mismatch": 0,
        "qhull_failed": 0,
        "hull_vertex_mismatch": 0,
        "too_few_simplices": 0,
        "duplicate_indices": 0,
        "duplicate_vertex_position": 0,
        "degenerate_triangle": 0,
        "duplicate_facet": 0,
        "non_manifold_edge": 0,
        "open_shell": 0,
        "inconsistent_plane_side": 0,
        "non_positive_volume": 0,
    }
    # 不跳过坏面：一旦存在坏面就整块重采样，避免破坏闭合壳体
    for _ in range(40):
        points = _sample_well_spaced_points(n_points)
        # 不做 round，直接保留高精度浮点坐标，避免近点被压成同一点
        if points.shape[0] != n_points:
            reject_stats["sample_count_mismatch"] += 1
            continue
        try:
            hull = ConvexHull(points, qhull_options="QJ")
        except Exception:
            reject_stats["qhull_failed"] += 1
            continue
        # 要求所有采样点都成为凸包顶点，避免“内点过多 + 外壳点不足”导致形状开裂感
        if len(hull.vertices) != n_points:
            reject_stats["hull_vertex_mismatch"] += 1
            continue
        if hull.simplices.shape[0] < 14:
            reject_stats["too_few_simplices"] += 1
            continue
        centroid = np.mean(points, axis=0)

        trial = []
        facet_keys = set()
        edge_counts = {}
        valid = True
        for tri in hull.simplices:
            if len({int(tri[0]), int(tri[1]), int(tri[2])}) != 3:
                reject_stats["duplicate_indices"] += 1
                valid = False
                break
            p1, p2, p3 = _oriented_triangle(points, centroid, tri[0], tri[1], tri[2])
            # 坐标级保险：即使索引不重复，也拒绝近乎重合的三角顶点
            if (
                np.allclose(p1, p2, rtol=0.0, atol=1e-10)
                or np.allclose(p2, p3, rtol=0.0, atol=1e-10)
                or np.allclose(p3, p1, rtol=0.0, atol=1e-10)
            ):
                reject_stats["duplicate_vertex_position"] += 1
                valid = False
                break
            if _is_degenerate_triangle(p1, p2, p3):
                reject_stats["degenerate_triangle"] += 1
                valid = False
                break
            # 面级去重：去掉重复或反向重复三角面
            k1 = tuple(np.round(p1, 8).tolist())
            k2 = tuple(np.round(p2, 8).tolist())
            k3 = tuple(np.round(p3, 8).tolist())
            facet_key = tuple(sorted((k1, k2, k3)))
            if facet_key in facet_keys:
                reject_stats["duplicate_facet"] += 1
                valid = False
                break
            facet_keys.add(facet_key)
            trial.append((p1, p2, p3))
            edge_idx = (
                tuple(sorted((int(tri[0]), int(tri[1])))),
                tuple(sorted((int(tri[1]), int(tri[2])))),
                tuple(sorted((int(tri[2]), int(tri[0])))),
            )
            for e in edge_idx:
                edge_counts[e] = edge_counts.get(e, 0) + 1
                if edge_counts[e] > 2:
                    reject_stats["non_manifold_edge"] += 1
                    valid = False
                    break
            if not valid:
                break

        # 闭合流形检查：每条边必须且仅能属于两个三角面
        if valid:
            if any(c != 2 for c in edge_counts.values()):
                reject_stats["open_shell"] += 1
                valid = False

        # 半空间一致性检查：所有面法向应使中心处于内侧
        if valid:
            eps = max(1e-8, scale * 1e-7)
            for p1, p2, p3 in trial:
                n = np.cross(p2 - p1, p3 - p1)
                if float(np.dot(n, centroid - p1)) > eps:
                    reject_stats["inconsistent_plane_side"] += 1
                    valid = False
                    break

        # 体积必须为正，避免面片朝向整体翻转或异常穿插
        if valid:
            signed_volume = 0.0
            for p1, p2, p3 in trial:
                signed_volume += float(np.dot(p1, np.cross(p2, p3)))
            signed_volume /= 6.0
            if signed_volume <= max(1e-8, scale * scale * scale * 1e-7):
                reject_stats["non_positive_volume"] += 1
                valid = False

        if valid and trial:
            polygons = [[p1.tolist(), p2.tolist(), p3.tolist()] for p1, p2, p3 in trial]
            break

    if not polygons:
        if debug:
            _log_debug(f"failed to build tessellated solid: rejects={reject_stats}")
        return None
    if debug:
        _log_debug(f"build succeeded: facets={len(polygons)} rejects={reject_stats}")

    if has_triangular_facet:
        facets = [pyg4g4.solid.TriangularFacet(v1, v2, v3, True, reg) for v1, v2, v3 in polygons]
        try:
            return pyg4g4.solid.TessellatedSolid(name, facets, reg)
        except TypeError:
            tess = pyg4g4.solid.TessellatedSolid(name, reg)
            for facet in facets:
                tess.add_facet(facet)
            return tess

    # 关键修复：
    # createTessellatedSolid 期望的是“轮廓序列”而非独立三角面列表，
    # 对三角面列表使用它会二次拼接并可能制造退化面（P1==P2）。
    # 这里直接按 STL 三角面网格构造 TessellatedSolid，避免引入内穿/坏面。
    mesh_type = pyg4g4.solid.TessellatedSolid.MeshType.Stl
    stl_mesh = [[tri] for tri in polygons]
    return pyg4g4.solid.TessellatedSolid(name, stl_mesh, reg, meshtype=mesh_type)

def generate_angular_ore(
    reg,
    name_base="ore_matrix",
    num_lumps=10,
    num_cuts=18,
    base_scale=18.0,
):
    """
    生成具有明显棱角和断裂面的矿石。
    1) 先用多个旋转长方体并集形成不规则主体。
    2) 再用多个大长方体从不同方向做布尔减，制造断裂平面。
    """
    # 允许极简参数输入，同时保持几何稳定
    num_lumps = _clip(int(num_lumps), 1, 64)
    num_cuts = _clip(int(num_cuts), 0, 128)
    base_scale = float(_clip(base_scale, 6.0, 30.0))

    # 主体核心：略扁/略长，避免过于规则
    bx = base_scale * np.random.uniform(0.85, 1.25)
    by = base_scale * np.random.uniform(0.70, 1.20)
    bz = base_scale * np.random.uniform(0.80, 1.35)
    current_solid = pyg4g4.solid.Box(f"{name_base}_core", bx, by, bz, reg)

    # Step1: 添加凸起块，生成“岩块拼接”感
    for i in range(num_lumps - 1):
        px = bx * np.random.uniform(0.35, 0.95)
        py = by * np.random.uniform(0.35, 0.95)
        pz = bz * np.random.uniform(0.35, 0.95)
        lump = pyg4g4.solid.Box(f"{name_base}_lump_{i}", px, py, pz, reg)

        # 让凸起尽量分布在外层，形成更粗粝的轮廓
        ox = np.random.uniform(-1.0, 1.0) * bx * np.random.uniform(0.25, 0.75)
        oy = np.random.uniform(-1.0, 1.0) * by * np.random.uniform(0.25, 0.75)
        oz = np.random.uniform(-1.0, 1.0) * bz * np.random.uniform(0.25, 0.75)

        rot = _make_rotation(
            reg,
            f"{name_base}_lump_rot_{i}",
            np.random.uniform(0, 2 * np.pi),
            np.random.uniform(0, 2 * np.pi),
            np.random.uniform(0, 2 * np.pi),
        )
        pos = _make_position(reg, f"{name_base}_lump_pos_{i}", ox, oy, oz)
        current_solid = _make_union(reg, f"{name_base}_u_{i}", current_solid, lump, rot, pos)

    # Step2: 用大型切割块从不同方向切掉局部，形成“断裂平面”
    # 极简参数下至少执行少量稳定切割，避免结果过于规则但又不至于切穿主体
    effective_cuts = max(2, num_cuts)
    cut_size = max(bx, by, bz) * 2.2
    for j in range(effective_cuts):
        cutter = pyg4g4.solid.Box(
            f"{name_base}_cutter_{j}",
            cut_size,
            cut_size * np.random.uniform(0.65, 1.25),
            cut_size * np.random.uniform(0.65, 1.25),
            reg,
        )

        # 将切割体中心推到主体边缘附近，避免整体被削没
        axis = np.random.randint(0, 3)
        signs = np.array([np.random.choice([-1.0, 1.0]) for _ in range(3)])
        offsets = np.array(
            [
                np.random.uniform(0.35, 0.85) * bx,
                np.random.uniform(0.35, 0.85) * by,
                np.random.uniform(0.35, 0.85) * bz,
            ]
        ) * signs
        # 控制切割体更靠外层，降低切穿或“削空主体”的风险
        offsets[axis] = signs[axis] * np.random.uniform(0.78, 1.10) * [bx, by, bz][axis]

        rot = _make_rotation(
            reg,
            f"{name_base}_cut_rot_{j}",
            np.random.uniform(0, 2 * np.pi),
            np.random.uniform(0, 2 * np.pi),
            np.random.uniform(0, 2 * np.pi),
        )
        pos = _make_position(
            reg,
            f"{name_base}_cut_pos_{j}",
            float(offsets[0]),
            float(offsets[1]),
            float(offsets[2]),
        )
        current_solid = _make_subtraction(
            reg, f"{name_base}_s_{j}", current_solid, cutter, rot, pos
        )

    return current_solid


def create_rugged_ore_gdml(
    output_path,
    matrix_material="CalciumPhosphate",
    mix_spec=None,
    mix_density=2.9,
    num_lumps=10,
    num_cuts=18,
    base_scale=18.0,
    mode="tessellated",
    tess_debug=False,
    allow_unsafe_create_tess=False,
):
    """构建完整的 GDML 环境并写入文件"""
    # 关键：使用系统时间作为随机种子，确保每次生成的 GDML 都不一样
    np.random.seed(int(time.time() * 1000) % 2**32)
    
    reg = pyg4g4.Registry()
    tri_probe = probe_triangularfacet_support()
    
    # --- 材质定义 ---
    mat_cache = {}
    mix_items = _parse_material_mix(mix_spec)
    if mix_items:
        mix_density = float(mix_density)
        if mix_density <= 0:
            raise ValueError("mix_density 必须 > 0")
        non_zero_mix_items = [(name, frac) for name, frac in mix_items if frac > 0.0]
        mat = pyg4g4.MaterialCompound("OreMixture", mix_density, len(non_zero_mix_items), reg)
        for comp_name, comp_frac in non_zero_mix_items:
            component = _build_material(reg, comp_name, mat_cache)
            mat.add_material(component, comp_frac)
    else:
        mat = _build_material(reg, matrix_material, mat_cache)
    
    # --- 几何体构造 ---
    mode = (mode or "tessellated").lower()
    if mode == "tessellated":
        if tess_debug:
            _log_debug(
                "TriangularFacet probe: "
                f"ok={tri_probe['ok']} "
                f"scipy={tri_probe['has_scipy']} "
                f"tessellatedSolid={tri_probe['has_tessellated_solid']} "
                f"triangularFacet={tri_probe['has_triangular_facet']} "
                f"createTessellatedSolid={tri_probe['has_create_tessellated_solid']} "
                f"reason={tri_probe['reason']}"
            )
        ore_solid = generate_tessellated_ore(
            reg,
            name="RuggedOre_tess",
            n_points=max(12, min(18, 10 + num_lumps // 3 + num_cuts // 8)),
            scale=base_scale,
            debug=tess_debug,
            allow_unsafe_create_tess=allow_unsafe_create_tess,
        )
        if ore_solid is None:
            _log(
                "警告：当前环境不支持稳定 tessellated 构建，"
                f"原因：{tri_probe['reason']}。自动回退到 csg 模式。"
            )
            mode = "csg"

    if mode == "csg":
        ore_solid = generate_angular_ore(
            reg,
            "RuggedOre",
            num_lumps=num_lumps,
            num_cuts=num_cuts,
            base_scale=base_scale,
        )

    ore_lv = pyg4g4.LogicalVolume(ore_solid, mat, "OreLog", reg)
    
    # 世界体积 (World)
    world_s = pyg4g4.solid.Box("world", 1000, 1000, 1000, reg)
    # 使用显式定义材质，避免 ROOT 导入时 "G4_Galactic Not Yet Defined"
    elH = pyg4g4.ElementSimple("H", "H", 1, 1.008, reg)
    world_m = pyg4g4.MaterialCompound("Vacuum", 1e-25, 1, reg)
    world_m.add_element_natoms(elH, 1)
    world_lv = pyg4g4.LogicalVolume(world_s, world_m, "world", reg)
    
    # 放置矿石
    pyg4g4.PhysicalVolume([0,0,0], [0,0,0], ore_lv, "OrePV", world_lv, reg)
    reg.setWorld(world_lv.name)
    
    # 写入文件
    w = pyg4gdml.Writer()
    w.addDetector(reg)
    w.write(output_path)
    _log(
        "ore_gdml -> "
        f"{output_path} | mode={mode} | material={'mix' if mix_items else matrix_material} "
        f"| lumps={num_lumps} | cuts={num_cuts} | scale={base_scale}"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", "-o", default="ore.gdml")
    parser.add_argument(
        "--material",
        default="CalciumPhosphate",
        help="单材质模式名称（如 CalciumPhosphate 或 G4_Si）",
    )
    parser.add_argument(
        "--mix",
        default="",
        help="按百分比混合材质，如 'CalciumPhosphate:70,G4_Si:30'；设置后优先于 --material",
    )
    parser.add_argument(
        "--mix-density",
        type=float,
        default=2.9,
        help="混合材质总密度 g/cm3（仅 --mix 生效）",
    )
    parser.add_argument(
        "--lumps",
        type=int,
        default=0,
        help="并集凸起块数量（越大越粗糙）",
    )
    parser.add_argument(
        "--cuts",
        type=int,
        default=0,
        help="切割次数（越大断裂面越多）",
    )
    parser.add_argument(
        "--scale",
        type=float,
        default=18.0,
        help="矿石基础尺寸标度（mm）",
    )
    parser.add_argument(
        "--mode",
        choices=["tessellated", "csg"],
        default="tessellated",
        help="tessellated 对 ROOT 更稳定；csg 为并集+切割布尔体",
    )
    parser.add_argument(
        "--tess-debug",
        action="store_true",
        help="输出 tessellated 构建阶段的坏面/重采样统计",
    )
    parser.add_argument(
        "--allow-unsafe-create-tess",
        action="store_true",
        help="允许使用 createTessellatedSolid 回退（可能生成退化面，不推荐）",
    )
    parser.add_argument(
        "--probe-triangularfacet",
        action="store_true",
        help="仅检测 TriangularFacet 能力并退出（不生成 GDML）",
    )
    args = parser.parse_args()

    if args.probe_triangularfacet:
        probe = probe_triangularfacet_support()
        _log("triangularfacet-probe")
        _log(f"ok={probe['ok']}")
        _log(f"has_scipy={probe['has_scipy']}")
        _log(f"has_tessellated_solid={probe['has_tessellated_solid']}")
        _log(f"has_triangular_facet={probe['has_triangular_facet']}")
        _log(f"has_create_tessellated_solid={probe['has_create_tessellated_solid']}")
        _log(f"reason={probe['reason']}")
        raise SystemExit(0 if probe["ok"] else 2)

    create_rugged_ore_gdml(
        args.output,
        matrix_material=args.material,
        mix_spec=args.mix,
        mix_density=args.mix_density,
        num_lumps=args.lumps,
        num_cuts=args.cuts,
        base_scale=args.scale,
        mode=args.mode,
        tess_debug=args.tess_debug,
        allow_unsafe_create_tess=args.allow_unsafe_create_tess,
    )

if __name__ == "__main__":
    main()