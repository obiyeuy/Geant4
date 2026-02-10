# 材料厚度扫描功能说明

## 功能概述

此功能用于扫描不同材料的厚度，并记录低能和高能闪烁体的响应，最终绘制统计曲线。

## 支持的材料和扫描参数

| 材料 | 步长 (mm) | 厚度范围 (mm) |
|------|-----------|---------------|
| H2O (水) | 10 | 10 ~ 200 |
| CHO (亚克力) | 10 | 10 ~ 200 |
| C (石墨) | 5 | 5 ~ 100 |
| Al (铝) | 1 | 1 ~ 50 |
| Fe (铁) | 0.03 | 0.03 ~ 5 |
| Cu (铜) | 0.01 | 0.01 ~ 3 |
| Pb (铅) | 0.001 | 0.001 ~ 1 |

## 使用方法

### 1. 编译Geant4项目

首先确保Geant4项目已编译：

```bash
cd build
cmake ../simulation
make
```

### 2. 运行扫描脚本

基本用法（扫描所有材料）：

```bash
cd scripts
python material_thickness_scan.py
```

扫描指定材料：

```bash
python material_thickness_scan.py --materials H2O Al Cu
```

自定义参数：

```bash
python material_thickness_scan.py \
    --materials H2O Al \
    --num-events 50000 \
    --output-dir my_scan_output
```

### 3. 参数说明

- `--materials`: 要扫描的材料列表（默认：所有材料）
- `--num-events`: 每个厚度的模拟事件数（默认：10000）
- `--output-dir`: 输出目录（默认：material_scan_output）
- `--skip-simulation`: 跳过模拟，仅分析已有数据

### 4. 查看结果

扫描完成后，会生成以下文件：

- `scan_results.json`: 所有扫描结果的JSON文件
- `plot_results.py`: 自动生成的绘图脚本

运行绘图脚本：

```bash
cd material_scan_output  # 或你指定的输出目录
python plot_results.py
```

这将生成 `material_scan_curve.png` 图像文件，显示低能 vs 高能闪烁体均值的统计曲线。

## 输出数据格式

`scan_results.json` 文件格式：

```json
{
  "H2O": [
    [10.0, 低能均值, 高能均值],
    [20.0, 低能均值, 高能均值],
    ...
  ],
  "Al": [
    [1.0, 低能均值, 高能均值],
    [2.0, 低能均值, 高能均值],
    ...
  ],
  ...
}
```

## Geant4命令

在Geant4宏文件中，可以使用以下命令：

```
/Xray/det/SetMaterialSlabMaterial <材料名称>
/Xray/det/SetMaterialSlabThickness <厚度> mm
```

支持的材料名称：
- `H2O` 或 `Water`
- `CHO` 或 `PMMA` 或 `Acrylic`
- `C` 或 `Graphite`
- `Al` 或 `Aluminum`
- `Fe` 或 `Iron`
- `Cu` 或 `Copper`
- `Pb` 或 `Lead`

## 注意事项

1. 扫描所有材料可能需要较长时间，建议先用少量事件测试
2. 每个厚度的模拟结果保存在独立的子目录中
3. 如果模拟中断，可以使用 `--skip-simulation` 选项分析已有数据
4. 材料板位置在待测物体和探测器之间，距离探测器约一半距离





