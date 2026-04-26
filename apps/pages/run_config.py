from __future__ import annotations

from datetime import datetime

import streamlit as st

from task_service import DEFAULT_STAGES


def _default_batch_id() -> str:
    return datetime.now().strftime("web_%Y%m%d_%H%M%S")


STAGE_LABELS = {
    "generate": "生成样本(generate)",
    "blank": "空场仿真(blank)",
    "simulate": "样本仿真(simulate)",
    "render": "图像渲染(render)",
    "snr": "信噪评估(snr)",
    "build": "构建数据集(build)",
    "train": "模型训练(train)",
}

ORE_MODE_LABELS = {
    "tessellated": "镶嵌网格(tessellated)",
    "csg": "布尔几何(csg)",
}

BALANCE_MODE_LABELS = {
    "none": "不平衡处理(none)",
    "class_weight": "类别权重(class_weight)",
    "sampler": "重采样(sampler)",
    "both": "类别权重+重采样(both)",
}


def render(task_service, project_root) -> None:
    st.subheader("任务配置")
    # Apply pending update for batch_id BEFORE widget instantiation.
    if "run_config_next_batch_id" in st.session_state:
        st.session_state["run_config_batch_id"] = st.session_state.pop("run_config_next_batch_id")
    if "run_config_batch_id" not in st.session_state:
        st.session_state["run_config_batch_id"] = _default_batch_id()
    if "run_config_auto_new_batch_id" not in st.session_state:
        st.session_state["run_config_auto_new_batch_id"] = False

    with st.form("run_form"):
        st.caption("修改参数后提交到任务队列")
        c1, c2 = st.columns(2)
        batch_id = c1.text_input("批次 ID(batch_id)", key="run_config_batch_id")
        auto_new_batch_id = c1.checkbox(
            "提交后自动生成新批次ID(auto_new_batch_id)",
            key="run_config_auto_new_batch_id",
        )
        num_samples = c1.number_input("样本数量(num_samples)", value=10, min_value=1, step=1)
        sample_start_index = c1.number_input("起始样本序号(sample_start_index)", value=1, min_value=0, step=1)
        beam_on = c1.number_input("粒子数(beam_on)", value=1_000_000, min_value=1, step=10_000)
        ore_ratio = c1.slider("矿石占比(ore_ratio)", min_value=0.0, max_value=1.0, value=0.5)
        seed = c1.number_input("随机种子(seed)", value=42, min_value=0, step=1)
        randomize_seed = c1.checkbox("使用随机种子(randomize_seed)", value=False)

        matrix_material = c2.text_input("基质材料(matrix_material)", value="G4_SILICON_DIOXIDE")
        matrix_density = c2.number_input("基质密度(matrix_density)", value=2.65, min_value=0.001, step=0.01)
        target_material = c2.text_input("目标材料(target_material)", value="G4_PbS")
        target_density = c2.number_input("目标密度(target_density)", value=7.6, min_value=0.001, step=0.01)
        target_grade_min = c2.number_input("目标品位下限(target_grade_min)", value=0.0, min_value=0.0, max_value=100.0, step=0.1)
        target_grade_max = c2.number_input("目标品位上限(target_grade_max)", value=20.0, min_value=0.0, max_value=100.0, step=0.1)
        label_threshold = c2.number_input("标签阈值(label_threshold)", value=5.0, min_value=0.0, max_value=100.0, step=0.1)

        stages = st.multiselect(
            "执行阶段(stages)",
            options=DEFAULT_STAGES,
            default=DEFAULT_STAGES,
            format_func=lambda x: STAGE_LABELS.get(x, x),
        )

        with st.expander("高级参数"):
            c3, c4 = st.columns(2)
            raw_root = c3.text_input("原始数据目录(raw_root)", value="data/raw")
            processed_root = c3.text_input("处理后数据目录(processed_root)", value="data/processed")
            experiments_root = c3.text_input("实验输出目录(experiments_root)", value="experiments")
            blank_dir = c3.text_input("空场目录(blank_dir)", value="data/raw/output_blank")
            geant_exec = c3.text_input("Geant 可执行路径(geant_exec，可选)", value="")
            simulation_root = c4.text_input("仿真目录(simulation_root)", value="simulation")
            master_macro = c4.text_input("主宏文件(master_macro)", value="simulation/master.mac")
            ore_mode = c4.selectbox(
                "矿体建模模式(ore_mode)",
                options=["tessellated", "csg"],
                index=0,
                format_func=lambda x: ORE_MODE_LABELS.get(x, x),
            )
            geometry_guard = c4.checkbox("几何保护重试(geometry_guard)", value=True)
            tess_max_retries = c4.number_input("最大重试次数(tess_max_retries)", value=3, min_value=1, step=1)
            train_ratio = c4.number_input("训练集比例(train_ratio)", value=0.7, min_value=0.0, max_value=1.0, step=0.01)
            val_ratio = c4.number_input("验证集比例(val_ratio)", value=0.15, min_value=0.0, max_value=1.0, step=0.01)
            epochs = c4.number_input("训练轮数(epochs)", value=30, min_value=1, step=1)
            batch_size = c4.number_input("批大小(batch_size)", value=16, min_value=1, step=1)
            lr = c4.number_input("学习率(lr)", value=0.001, min_value=0.0, step=0.0001, format="%.4f")
            num_workers = c4.number_input("数据加载线程数(num_workers)", value=0, min_value=0, step=1)
            balance_mode = c4.selectbox(
                "类别平衡策略(balance_mode)",
                options=["none", "class_weight", "sampler", "both"],
                index=3,
                format_func=lambda x: BALANCE_MODE_LABELS.get(x, x),
            )
            snr_report_dir = c4.text_input("SNR 报告目录(snr_report_dir)", value="experiments/snr_reports")

        submitted = st.form_submit_button("提交任务")
        if submitted:
            params = {
                "batch_id": batch_id,
                "num_samples": int(num_samples),
                "sample_start_index": int(sample_start_index),
                "ore_ratio": float(ore_ratio),
                "seed": int(seed),
                "randomize_seed": bool(randomize_seed),
                "matrix_material": matrix_material,
                "matrix_density": float(matrix_density),
                "target_material": target_material,
                "target_density": float(target_density),
                "target_grade_min": float(target_grade_min),
                "target_grade_max": float(target_grade_max),
                "label_threshold": float(label_threshold),
                "raw_root": raw_root,
                "processed_root": processed_root,
                "experiments_root": experiments_root,
                "blank_dir": blank_dir,
                "simulation_root": simulation_root,
                "master_macro": master_macro,
                "beam_on": int(beam_on),
                "ore_mode": ore_mode,
                "geometry_guard": bool(geometry_guard),
                "tess_max_retries": int(tess_max_retries),
                "train_ratio": float(train_ratio),
                "val_ratio": float(val_ratio),
                "epochs": int(epochs),
                "batch_size": int(batch_size),
                "lr": float(lr),
                "num_workers": int(num_workers),
                "balance_mode": balance_mode,
                "snr_report_dir": snr_report_dir,
            }
            if geant_exec.strip():
                params["geant_exec"] = geant_exec.strip()
            job_id = task_service.submit_pipeline_job(params, stages=stages or DEFAULT_STAGES)
            st.session_state["selected_batch_id"] = batch_id
            if auto_new_batch_id:
                # Defer changing the widget value to next rerun to avoid StreamlitAPIException.
                st.session_state["run_config_next_batch_id"] = _default_batch_id()
            st.success(f"任务已提交：任务ID={job_id}，批次ID={batch_id}")
            st.caption(f"项目根目录：{project_root}")
