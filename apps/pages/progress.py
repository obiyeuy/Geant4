from __future__ import annotations

import json
import time

import streamlit as st
import streamlit.components.v1 as components


def render(task_service) -> None:
    st.subheader("任务进度")
    jobs = task_service.list_jobs(limit=100)
    if not jobs:
        st.info("当前没有任务。")
        return

    options: list[str] = []
    label_to_job_id: dict[str, str] = {}
    for j in jobs:
        bid = ""
        try:
            bid = json.loads(j.params_json).get("batch_id", "")
        except Exception:
            bid = ""
        label = f"{bid} | {j.job_id}" if bid else j.job_id
        options.append(label)
        label_to_job_id[label] = j.job_id

    selected_label = st.selectbox("选择任务（批次ID | 任务ID）", options=options, key="progress_task_select")
    job = task_service.get_job(label_to_job_id.get(selected_label, ""))
    if job is None:
        st.warning("任务不存在")
        return
    batch_id = ""
    try:
        batch_id = json.loads(job.params_json).get("batch_id", "")
    except Exception:
        batch_id = ""

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("状态", job.status)
    c2.metric("当前阶段", job.current_stage or "-")
    c3.metric("进度", f"{job.progress*100:.1f}%")
    c4.metric("批次ID", batch_id or "-")
    st.progress(min(max(float(job.progress), 0.0), 1.0))

    if job.error_message:
        st.error(job.error_message)

    auto_refresh = st.checkbox("自动刷新（3秒）", value=True)
    tail = task_service.read_log_tail(job.job_id, max_chars=12000)
    # Use a scrollable HTML block and always scroll to bottom after refresh.
    escaped = (
        tail.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
    components.html(
        f"""
        <div style="font-size:12px; line-height:1.35; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace;">
          <div style="margin: 0 0 6px 0; color: #666;">日志</div>
          <div id="logbox" style="height: 360px; overflow-y: auto; white-space: pre-wrap; border: 1px solid #e6e6e6; padding: 10px; border-radius: 6px; background: #fafafa;">{escaped}</div>
        </div>
        <script>
          const el = document.getElementById("logbox");
          if (el) {{ el.scrollTop = el.scrollHeight; }}
        </script>
        """,
        height=420,
    )

    if st.button("取消任务"):
        ok = task_service.cancel_job(job.job_id)
        if ok:
            st.warning("任务已取消。")
            st.rerun()
        st.info("当前状态无法取消任务。")

    if auto_refresh and job.status in ("queued", "running"):
        time.sleep(3)
        st.rerun()
