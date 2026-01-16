# GDML 动态加载功能使用说明

本文档说明如何使用新增的 GDML 动态加载功能来生成复杂矿石几何并进行自动化数据生成。

## 功能概述

1. **C++ 端**：支持在运行时动态加载 GDML 文件来替换矿石几何
2. **Python 端**：使用 pyg4ometry 生成不规则含杂质矿石的 GDML 文件
3. **自动化管线**：串联 Python 生成和 Geant4 模拟，实现全自动数据生成

## 编译要求

### 依赖库

- **XercesC**：用于 GDML 解析
  ```bash
  # Ubuntu/Debian
  sudo apt-get install libxerces-c-dev
  
  # 或使用 conda
  conda install xerces-c
  ```

- **pyg4ometry**：Python 几何生成库
  ```bash
  pip install pyg4ometry
  # 或
  conda install -c conda-forge pyg4ometry
  ```

### 编译 Geant4 程序

```bash
cd simulation
mkdir -p build
cd build
cmake ..
make
```

确保 CMakeLists.txt 中已添加 XercesC 支持（已完成）。

## 使用方法

### 1. 生成单个矿石 GDML 文件

```bash
python scripts/generate_ore.py --output ore.gdml \
    --num-particles 1000 \
    --particle-radius 1.0 \
    --matrix-material CalciumPhosphate \
    --inclusion-material G4_Pb
```

参数说明：
- `--output`: 输出 GDML 文件路径
- `--num-particles`: 颗粒数量（默认 1000）
- `--particle-radius`: 颗粒半径，单位 mm（默认 1.0）
- `--matrix-material`: 基体材质（默认 CalciumPhosphate）
- `--inclusion-material`: 颗粒材质（默认 G4_Pb）
- `--num-ellipsoids`: 基体椭球数量（默认 3，当前实现中简化）

### 2. 在 Geant4 中加载 GDML

#### 方法 1：使用宏文件

创建宏文件 `load_ore.mac`：
```
/Xray/det/loadGDML /absolute/path/to/ore.gdml
/run/initialize
/run/beamOn 10000
```

运行：
```bash
./simulation/build/CZT load_ore.mac
```

#### 方法 2：在现有宏文件中添加

在 `simulation/master.mac` 开头添加：
```
/Xray/det/loadGDML /absolute/path/to/ore.gdml
```

### 3. 自动化数据生成管线

```bash
python scripts/run_pipeline.py \
    --base-dir data/raw \
    --batch-id 20240101 \
    --num-samples 10 \
    --start-id 1 \
    --material mixed \
    --executable ./simulation/build/CZT \
    --num-particles 1000 \
    --particle-radius 1.0
```

参数说明：
- `--base-dir`: 基础数据目录（默认 `data/raw`）
- `--batch-id`: 批次ID，默认使用当前日期
- `--num-samples`: 生成样本数量
- `--start-id`: 起始样本ID（默认 1）
- `--material`: 材质名称（用于文件夹命名）
- `--executable`: Geant4 可执行文件路径
- `--num-particles`: 矿石颗粒数量
- `--particle-radius`: 颗粒半径 (mm)

## 输出结构

运行管线后，数据将按以下结构组织：

```
data/raw/
└── batch_20240101/
    ├── sample_0001_mixed/
    │   ├── ore.gdml          # 矿石几何文件
    │   ├── scan.mac          # 临时宏文件
    │   ├── info.json         # 样本信息（品位、颗粒数等）
    │   ├── LowEnergy/        # 低能探测器数据
    │   │   └── *.bin
    │   └── HighEnergy/        # 高能探测器数据
    │       └── *.bin
    ├── sample_0002_mixed/
    │   └── ...
    └── ...
```

## 环境变量

- `G4_OUTPUT_DIR`: 设置 Geant4 输出目录（由 `scripts/run_pipeline.py` 自动设置）

## 注意事项

1. **路径问题**：GDML 文件路径必须使用**绝对路径**，避免因运行目录不同导致文件找不到。

2. **重叠检测**：Python 脚本会检查颗粒之间、颗粒与边界的重叠，但复杂情况下仍可能出现重叠。如果 Geant4 报错 `Overlap` 或 `Stuck Track`，请：
   - 减少颗粒数量
   - 增大颗粒间距（调整 `min_distance_factor`）
   - 减小颗粒半径

3. **性能权衡**：
   - GDML 文件大小建议控制在 50MB 以内（约 1-2 万个颗粒）
   - Geant4 解析 GDML 需要时间，建议每个 GDML 加载后运行至少 10^5 个粒子

4. **材质定义**：确保使用的材质名称在 Geant4 中已定义：
   - 预定义材质：`G4_Pb`, `G4_Fe`, `G4_SiO2` 等
   - 自定义材质：需要在 C++ 代码中定义（如 `CalciumPhosphate`）

5. **逻辑体积命名**：Python 生成的 GDML 中，矿石逻辑体积**必须**命名为 `"OreLog"`（与 C++ 约定一致）。

## 故障排除

### 问题：找不到 'OreLog' 逻辑体积

**原因**：GDML 文件中的逻辑体积名称不是 "OreLog"

**解决**：检查 `scripts/generate_ore.py` 中逻辑体积的命名，确保为 `"OreLog"`

### 问题：GDML 文件无法读取

**原因**：文件路径错误或文件不存在

**解决**：使用绝对路径，确保文件存在

### 问题：编译错误，找不到 XercesC

**原因**：XercesC 未安装或 CMake 找不到

**解决**：
```bash
# 安装 XercesC
sudo apt-get install libxerces-c-dev

# 或指定 XercesC 路径
cmake -DXercesC_ROOT=/path/to/xercesc ..
```

### 问题：Python 导入错误，找不到 pyg4ometry

**原因**：pyg4ometry 未安装

**解决**：
```bash
pip install pyg4ometry
# 或
conda install -c conda-forge pyg4ometry
```

## 示例工作流

完整的数据生成流程：

```bash
# 1. 编译 Geant4 程序
cd simulation/build
cmake ..
make

# 2. 生成单个样本测试
cd ../..
python scripts/generate_ore.py --output test_ore.gdml --num-particles 100

# 3. 测试加载
cd simulation/build
echo "/Xray/det/loadGDML $(pwd)/../../test_ore.gdml" > test.mac
echo "/run/initialize" >> test.mac
echo "/run/beamOn 1000" >> test.mac
./CZT test.mac

# 4. 运行自动化管线
cd ../..
python scripts/run_pipeline.py --num-samples 5 --num-particles 500
```

## 扩展功能

### 自定义材质

如需使用自定义材质，需要在 `simulation/src/DetectorConstruction.cc` 中定义材质，然后在 Python 脚本中使用相同的名称。

### 更复杂的几何形状

可以修改 `scripts/generate_ore.py` 中的 `generate_irregular_matrix` 函数，实现更复杂的基体形状（如多个椭球的布尔并集、三角网格等）。

### 并行生成

可以修改 `scripts/run_pipeline.py` 使用多进程并行生成多个样本，提高效率。





