from __future__ import annotations

import json

import streamlit as st


def render(task_service) -> None:
    st.subheader("总览")
    jobs = task_service.list_jobs(limit=30)
    if not jobs:
        st.info("当前还没有任务，请先在“任务配置”页面提交。")
        return

    queued = sum(1 for j in jobs if j.status == "queued")
    running = sum(1 for j in jobs if j.status == "running")
    success = sum(1 for j in jobs if j.status == "success")
    failed = sum(1 for j in jobs if j.status == "failed")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("排队中", queued)
    c2.metric("运行中", running)
    c3.metric("成功", success)
    c4.metric("失败", failed)

    rows = []
    for j in jobs:
        batch_id = ""
        try:
            batch_id = json.loads(j.params_json).get("batch_id", "")
        except Exception:
            batch_id = ""
        rows.append(
            {
                "任务ID": j.job_id,
                "批次ID": batch_id,
                "状态": j.status,
                "任务类型": j.task_type,
                "当前阶段": j.current_stage,
                "进度": round(j.progress, 3),
                "创建时间": j.created_at,
                "更新时间": j.updated_at,
            }
        )
    st.dataframe(rows, use_container_width=True, hide_index=True)
