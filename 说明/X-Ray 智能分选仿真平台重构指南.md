
# X-Ray 智能分选仿真平台重构指南

## 1. 项目背景与目标

本项目旨在基于 Geant4 模拟双能 X 射线透射（DE-XRT）分选过程，用于训练深度学习分选模型。 **核心痛点**：当前模拟的矿石形状单一（方块/球体）、材质均匀，导致训练出的模型在真实工业场景（复杂形状、浸染状混合矿）下泛化能力差。 **升级目标**：

1. **复杂几何**：支持自动化生成不规则形状、内部包含随机颗粒（浸染状）的复杂矿石模型。
2. **数据闭环**：实现“Python 生成参数 -> Geant4 模拟 -> 自动标注 Label”的全自动数据生产线。
3. **工程解耦**：将随机控制逻辑上移至 Python，C++ 层只负责通用执行，通过 GDML 和 环境变量解耦。

------

## 2. 架构设计 (Architecture)

### 2.1 核心工作流

代码段

```
graph TD
    A[Python控制中心 (generate_data.py)] -->|1.生成| B(复杂几何 .gdml)
    A -->|2.生成| C(控制宏 .mac)
    A -->|3.设置| D{环境变量 G4_OUTPUT_DIR}
    B --> E[Geant4 C++ 引擎]
    C --> E
    D --> E
    E -->|4.输出| F[二进制数据 .bin]
    A -->|5.输出| G[标签信息 info.json]
    F & G --> H[样本文件夹 batch_xxx/sample_001]
```

### 2.2 关键技术栈

- **几何生成**：`pyg4ometry` (Python库，用于构建布尔运算几何和拒绝采样植入)。
- **几何交换**：`GDML` (Geant4 标注几何描述语言)。
- **进程通信**：`Environment Variables` (传递输出路径)。

------

## 3. C++ 端重构规范 (底层执行层)

### 3.1 依赖库升级 (`CMakeLists.txt`)

**必须** 显式链接 `XercesC` 以支持 GDML 解析。

- 操作：在 `target_link_libraries` 中添加 `${XERCESC_LIBRARIES}`。
- 操作：添加 `find_package(XercesC REQUIRED)` 和 `include_directories(${XERCESC_INCLUDE_DIRS})`。

### 3.2 动态几何加载 (`DetectorConstruction`)

移除硬编码的几何构建逻辑，改为动态读取 GDML。

- **头文件 (.hh)**：
  - 引入 `<G4GDMLParser.hh>`。
  - 新增成员 `G4GDMLParser fParser;`。
  - 新增接口 `void LoadOreGDML(G4String filename);`。
  - 确保 `fLogicOre` 和 `fPhysOre` 为成员变量以便动态替换。
- **源文件 (.cc)**：
  - 在 `Construct()` 中，初始化一个空的占位体积（或空气盒），避免空指针。
  - 实现 `LoadOreGDML(filename)`：
    1. 调用 `fParser.Read(filename, false)`。
    2. 通过 `fParser.GetVolume("OreLog")` 获取逻辑体积（约定名称为 `OreLog`）。
    3. 更新 `fPhysOre` 的逻辑体积指针 (`fPhysOre->SetLogicalVolume(...)`)。
    4. 调用 `G4RunManager::GetRunManager()->GeometryHasBeenModified()` 通知内核。

### 3.3 宏命令接口 (`DetectorMessenger`)

注册新命令以供 Python 调用。

- 命令路径：`/Xray/det/loadGDML [filename]`。
- 作用：调用 `LoadOreGDML` 函数。

### 3.4 动态输出路径 (`RunAction`)

数据不应死板地存放在 `output` 文件夹。

- 逻辑：优先读取环境变量 `G4_OUTPUT_DIR`。

- 代码片段：

  C++

  ```
  const char* env_p = std::getenv("G4_OUTPUT_DIR");
  G4String outputBase = (env_p != nullptr) ? G4String(env_p) : "output";
  // 随后基于 outputBase 创建 LowEnergy/HighEnergy 子目录
  ```

------

## 4. Python 端开发规范 (顶层控制层)

### 4.1 复杂矿石生成器 (`generate_ore.py`)

利用 `pyg4ometry` 实现生成式建模。

- **基体生成 (Matrix)**：
  - 使用 2-3 个 `Ellipsoid` 进行 `Union` (布尔并集) 操作，模拟不规则“土豆”形状。
- **浸染体植入 (Inclusions)**：
  - 定义微小颗粒（如 1mm 半径的球）。
  - 使用**拒绝采样 (Rejection Sampling)**：在基体包围盒内随机撒点，判断点是否在基体内部（`x^2/a^2 + ... < 1`），且不与其他颗粒重叠。
  - 循环植入 500-2000 个颗粒。
- **导出规范**：
  - 逻辑体积名称强制设为 `"OreLog"`（与 C++ 约定一致）。
  - 文件保存为 `.gdml`。

### 4.2 批次管理与运行 (`run_pipeline.py`)

负责调度整个模拟流程。

- **目录结构**： `data/raw/batch_{date}/sample_{id}_{material}/`
- **执行步骤**：
  1. 创建样本文件夹。
  2. 调用生成器生成 `ore.gdml` 到该文件夹。
  3. 生成临时宏文件 `scan.mac`，写入 `/Xray/det/loadGDML .../ore.gdml`。
  4. 设置 `os.environ["G4_OUTPUT_DIR"]` 为样本文件夹路径。
  5. 调用 `subprocess.run(["./CZT", "master.mac"])`。
  6. 写入 `info.json`：记录品位、基体材质、颗粒数量（作为 Ground Truth）。

------

## 5. 复现注意事项 (Checklist)

1. **重叠检测**：在 Python 生成颗粒时，务必检查颗粒之间、颗粒与边界是否重叠，否则 Geant4 会报错 `Stuck Track` 或 `Overlap`。
2. **路径问题**：C++ 读取 GDML 和 Python 设置环境变量时，**必须使用绝对路径** (`os.path.abspath`)，避免因运行目录不同导致文件找不到。
3. **性能权衡**：
   - GDML 文件大小建议控制在 50MB 以内（约 1-2 万个颗粒）。
   - Geant4 解析 GDML 需要时间，建议每个 GDML 加载后运行至少 10^5 个粒子，均摊 IO 开销。
4. **环境配置**：
   - 确保 Conda 环境中安装了 `pyg4ometry`。
   - 确保编译 Geant4 程序时没有 CMake 报错。