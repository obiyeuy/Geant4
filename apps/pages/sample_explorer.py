from __future__ import annotations

from pathlib import Path

import streamlit as st

from readers import list_samples, load_sample_info, sample_image_paths


def _discover_batch_ids(project_root: Path) -> list[str]:
    out: set[str] = set()
    for p in (project_root / "data/raw").glob("batch_*"):
        if p.is_dir():
            out.add(p.name.replace("batch_", "", 1))
    return sorted(out)


def render(project_root: Path) -> None:
    st.subheader("样本浏览")
    default_batch_id = st.session_state.get("selected_batch_id", "PbS_1M")
    candidates = _discover_batch_ids(project_root)
    if candidates:
        idx = candidates.index(default_batch_id) if default_batch_id in candidates else 0
        batch_id = st.selectbox("批次 ID", options=candidates, index=idx, key="sample_batch_select")
    else:
        st.info("未找到可选批次。")
        batch_id = default_batch_id
    st.session_state["selected_batch_id"] = batch_id
    batch_dir = project_root / "data/raw" / f"batch_{batch_id}"
    samples = list_samples(batch_dir)
    if not samples:
        st.info(f"未在目录中找到样本：{batch_dir}")
        return
    sample_names = [p.name for p in samples]
    selected_name = st.selectbox("选择样本", options=sample_names, key="sample_name_select")
    sample_dir = batch_dir / selected_name

    info = load_sample_info(sample_dir)
    if info:
        st.json(info)
    else:
        st.warning(f"缺少 info.json：{sample_dir}")

    images = sample_image_paths(sample_dir)
    if not images:
        st.info("images 目录下未找到渲染图片。")
        return
    cols = st.columns(2)
    idx = 0
    for name, path in images.items():
        cols[idx % 2].image(str(path), caption=name)
        idx += 1
