# 统一全流程管线

该目录是项目唯一推荐入口，覆盖：

1. 样本几何生成（GDML）
2. Geant4 仿真输出（LowEnergy/HighEnergy）
3. 仿真数据组装图像（写回 raw 样本目录）
4. R值物理特征数据集构建
5. EfficientNet 训练

---

## 推荐目录结构

```text
XRay-detectionCode/
├── data/
│   ├── raw/                              # 原始样本输出
│   │   └── batch_<batch_id>/sample_xxxxx_ore|waste/
│   │       ├── ore.gdml
│   │       ├── LowEnergy/*.bin
│   │       ├── HighEnergy/*.bin
│   │       ├── images/
│   │       │   ├── low_energy.png
│   │       │   ├── high_energy.png
│   │       │   ├── r_map.png
│   │       │   └── preview_rgb.png
│   │       └── info.json
│   └── processed/
│       └── r_value_dataset/              # 构建后的训练数据
├── experiments/
│   └── efficientnet_rvalue_<batch_id>/   # 训练结果
└── scripts/
    └── pipeline/                         # 统一编排入口 + R值构建/训练实现
```

---

## 一键全流程

在项目根目录运行：

```bash
python3 scripts/pipeline/run_full_pipeline.py
```

默认执行阶段顺序：

- `generate`
- `blank`（同批次白板仿真：不放矿石，仅保留系统默认配置）
- `simulate`
- `render`
- `snr`
- `build`
- `train`

---

## 分阶段执行

仅生成+白板+仿真：

```bash
python3 scripts/pipeline/run_full_pipeline.py --stages generate blank simulate
```

仅对已仿真数据组装图像：

```bash
python3 scripts/pipeline/run_full_pipeline.py --stages render --batch-id <batch_id>
```

仅从已有原始数据构建并训练：

```bash
python3 scripts/pipeline/run_full_pipeline.py --stages build train --batch-id <batch_id>
```

---

## 常用参数

- `--batch-id`：批次名（默认时间戳）
- `--num-samples`：样本数
- `--ore-ratio`：矿石样本占比（0~1）
- `--seed`：固定随机种子（默认可复现实验）
- `--randomize-seed`：使用时间种子（每次运行不同）
- `--geant-exec`：Geant4可执行文件路径
- `--blank-dir`：空扫平场目录（用于R值计算；若同批次存在 `data/raw/batch_<batch_id>/blank` 会优先使用；否则按 `--beam-on` 自动匹配）
- `--epochs --batch-size --lr`：训练参数

