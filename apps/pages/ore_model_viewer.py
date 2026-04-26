from __future__ import annotations

from pathlib import Path

import streamlit as st

from readers import list_samples, load_sample_info, load_tessellated_mesh, sample_image_paths

try:
    import plotly.graph_objects as go
except Exception:  # pragma: no cover
    go = None


def _discover_batch_ids(project_root: Path) -> list[str]:
    out: set[str] = set()
    for p in (project_root / "data/raw").glob("batch_*"):
        if p.is_dir():
            out.add(p.name.replace("batch_", "", 1))
    return sorted(out)


def _render_fallback_images(sample_dir: Path) -> None:
    images = sample_image_paths(sample_dir)
    if not images:
        st.info("当前样本没有可用渲染图。")
        return
    st.caption("当前环境不可用 3D 组件，已展示样本预览图。")
    cols = st.columns(2)
    for idx, (name, path) in enumerate(images.items()):
        cols[idx % 2].image(str(path), caption=name)


def render(project_root: Path) -> None:
    st.subheader("矿石模型查看")
    st.caption("从样本目录中的 ore.gdml 读取三角网格并交互显示")

    default_batch_id = st.session_state.get("selected_batch_id", "PbS_1M")
    candidates = _discover_batch_ids(project_root)
    if not candidates:
        st.info("未找到任何批次目录。")
        return

    idx = candidates.index(default_batch_id) if default_batch_id in candidates else 0
    batch_id = st.selectbox("批次 ID", options=candidates, index=idx, key="model_batch_select")
    st.session_state["selected_batch_id"] = batch_id

    batch_dir = project_root / "data/raw" / f"batch_{batch_id}"
    samples = list_samples(batch_dir)
    if not samples:
        st.info(f"未在目录中找到样本：{batch_dir}")
        return

    sample_names = [p.name for p in samples]
    selected_name = st.selectbox("选择样本", options=sample_names, key="model_sample_select")
    sample_dir = batch_dir / selected_name
    gdml_path = sample_dir / "ore.gdml"

    c1, c2, c3 = st.columns(3)
    info = load_sample_info(sample_dir)
    class_name = str(info.get("class_name", info.get("label", "-")))
    grade_value = info.get("grade_value", info.get("target_grade", info.get("target_mass_percent", 0.0)))
    try:
        grade_value_f = float(grade_value)
    except (TypeError, ValueError):
        grade_value_f = 0.0
    c1.metric("类别", class_name)
    c2.metric("目标品位(%)", f"{grade_value_f:.3f}")
    c3.metric("文件", "ore.gdml" if gdml_path.exists() else "缺失")

    if not gdml_path.exists():
        st.warning(f"缺少几何文件：{gdml_path}")
        _render_fallback_images(sample_dir)
        return

    mesh = load_tessellated_mesh(gdml_path)
    if mesh is None:
        st.warning("GDML 解析失败，无法读取三角网格。")
        _render_fallback_images(sample_dir)
        return

    vcount = len(mesh.vertices)
    fcount = len(mesh.faces)
    st.caption(f"实体: {mesh.solid_name} | 顶点数: {vcount} | 三角面数: {fcount}")
    # st.info("这里展示的是几何网格数据（矿石外形），不是探测器信号或仿真统计结果。")

    if go is None:
        st.warning("未安装 plotly，暂无法显示交互 3D。请安装依赖后重试。")
        _render_fallback_images(sample_dir)
        return

    x = [v[0] for v in mesh.vertices]
    y = [v[1] for v in mesh.vertices]
    z = [v[2] for v in mesh.vertices]
    i = [f[0] for f in mesh.faces]
    j = [f[1] for f in mesh.faces]
    k = [f[2] for f in mesh.faces]

    fig = go.Figure(
        data=[
            go.Mesh3d(
                x=x,
                y=y,
                z=z,
                i=i,
                j=j,
                k=k,
                color="#5A8DEE",
                opacity=0.72,
                flatshading=True,
                lighting={"ambient": 0.45, "diffuse": 0.75, "specular": 0.20},
            )
        ]
    )
    fig.update_layout(
        margin=dict(l=0, r=0, t=10, b=0),
        scene=dict(
            xaxis_title="X (mm)",
            yaxis_title="Y (mm)",
            zaxis_title="Z (mm)",
            aspectmode="data",
        ),
        height=640,
    )
    st.plotly_chart(fig, use_container_width=True)
