import pyg4ometry
import numpy as np
import random
import os
import subprocess
import json
import datetime
import shutil

# --- 全局配置 ---
G4_EXEC_PATH = "../build/CZT"  # 编译好的程序路径
NUM_SAMPLES = 50               # 生成多少个样本
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_ROOT = os.path.join(PROJECT_ROOT, "data", "raw")

# --- 1. 复杂几何生成函数 (Pyg4ometry) ---
def create_disseminated_ore(filename, base_mat_name, inc_mat_name, ore_size_mm, grade_percent):
    """
    生成浸染状矿石 GDML：在基体中随机撒入颗粒
    """
    # 注册表
    reg = pyg4ometry.geant4.Registry()
    
    # 定义材料 (直接引用 G4 NIST)
    mat_base = pyg4ometry.geant4.MaterialPredefined(base_mat_name)
    mat_inc  = pyg4ometry.geant4.MaterialPredefined(inc_mat_name)
    
    # 构建不规则基体 (两个椭球融合，模拟土豆形状)
    s1 = pyg4ometry.geant4.solid.Ellipsoid("s1", ore_size_mm, ore_size_mm*0.8, ore_size_mm*1.2, 0,0,0)
    s2 = pyg4ometry.geant4.solid.Ellipsoid("s2", ore_size_mm*0.9, ore_size_mm*1.1, ore_size_mm, 0,0,0)
    pos_union = pyg4ometry.geant4.d3.Position("pos_union", ore_size_mm*0.2, 0, 0)
    rot_union = pyg4ometry.geant4.d3.Rotation("rot_union", 0,0,0)
    solid_ore = pyg4ometry.geant4.solid.Union("solid_ore", s1, s2, rot_union, pos_union)
    
    # 创建逻辑体积 (必须命名为 OreLog，以便 C++ 读取)
    lv_ore = pyg4ometry.geant4.LogicalVolume(solid_ore, mat_base, "OreLog")
    
    # 植入颗粒 (Inclusions)
    inc_radius = 1.0 # 1mm 颗粒
    solid_inc = pyg4ometry.geant4.solid.Orb("solid_inc", inc_radius)
    lv_inc = pyg4ometry.geant4.LogicalVolume(solid_inc, mat_inc, "IncLog")
    
    # 计算需要多少颗粒
    vol_ore_est = (4/3) * np.pi * ore_size_mm**3
    vol_inc = (4/3) * np.pi * inc_radius**3
    n_particles = int((vol_ore_est * grade_percent) / vol_inc)
    n_particles = min(n_particles, 2000) # 限制上限防止过卡
    
    print(f"Generating Geometry: Size={ore_size_mm:.1f}mm, Inclusions={n_particles}")

    # 随机撒点
    for i in range(n_particles):
        # 简单拒绝采样：保证在球体内
        while True:
            x = random.uniform(-ore_size_mm, ore_size_mm)
            y = random.uniform(-ore_size_mm, ore_size_mm)
            z = random.uniform(-ore_size_mm, ore_size_mm)
            if (x**2 + y**2 + z**2) < (ore_size_mm * 0.8)**2:
                pos = pyg4ometry.geant4.d3.Position(f"p{i}", x, y, z)
                # 放置物理体积
                pyg4ometry.geant4.PhysicalVolume(rot_union, pos, lv_inc, f"pv_{i}", lv_ore)
                break

    # 导出 GDML
    w = pyg4ometry.gdml.Writer()
    w.addDetector(lv_ore)
    w.write(filename)

# --- 2. 批次运行控制 ---
def run_batch(sample_id):
    # 随机化参数
    target_type = random.choice(["Ore", "Waste"])
    
    if target_type == "Ore":
        base_mat = "G4_SILICON_DIOXIDE" # 脉石
        inc_mat = "G4_Fe"               # 铁矿颗粒
        grade = random.uniform(0.1, 0.3) # 10% - 30% 品位
    else:
        base_mat = "G4_SILICON_DIOXIDE"
        inc_mat = "G4_AIR"              # 只有气孔，或者是纯石头
        grade = 0.0

    size = random.uniform(20.0, 40.0)

    # 准备目录
    batch_date = datetime.datetime.now().strftime("%Y%m%d")
    sample_dir_name = f"batch_{batch_date}_sample_{sample_id:04d}_{target_type}"
    output_dir = os.path.join(DATA_ROOT, sample_dir_name)
    os.makedirs(output_dir, exist_ok=True)

    # 1. 生成 GDML
    gdml_path = os.path.join(output_dir, "ore.gdml")
    create_disseminated_ore(gdml_path, base_mat, inc_mat, size, grade)

    # 2. 生成宏文件 scan_row.mac
    work_dir = os.path.dirname(G4_EXEC_PATH)
    macro_path = os.path.join(work_dir, "scan_row.mac")
    
    with open(macro_path, "w") as f:
        f.write(f"/Xray/det/loadGDML {gdml_path}\n")
        f.write(f"/Xray/det/SetObjShift {{iRow}} mm\n") # iRow 由 master.mac 循环控制
        f.write(f"/run/beamOn 500000\n") # 50万粒子用于训练
    
    # 3. 运行 Geant4
    env = os.environ.copy()
    env["G4_OUTPUT_DIR"] = output_dir
    
    print(f"--> Simulating {sample_dir_name}...")
    try:
        subprocess.run(["./CZT", "master.mac"], cwd=work_dir, env=env, check=True)
    except subprocess.CalledProcessError:
        print("Simulation Failed!")
        return

    # 4. 保存标签信息 (Label)
    info = {
        "id": sample_id,
        "class": 1 if target_type == "Ore" else 0, # 1=矿, 0=废
        "grade": grade,
        "size_mm": size,
        "base_mat": base_mat,
        "inclusion_mat": inc_mat
    }
    with open(os.path.join(output_dir, "info.json"), "w") as f:
        json.dump(info, f, indent=4)

if __name__ == "__main__":
    print(">>> Starting Advanced Training Data Generation...")
    for i in range(NUM_SAMPLES):
        run_batch(i)
    print(">>> All Done.")