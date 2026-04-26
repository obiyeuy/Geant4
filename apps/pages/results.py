from __future__ import annotations

from pathlib import Path

import streamlit as st

from readers import flatten_splits, load_snr_reports, load_snr_summary, load_sorting_report


def _discover_batch_ids(project_root: Path) -> list[str]:
    out: set[str] = set()
    for p in (project_root / "data/raw").glob("batch_*"):
        if p.is_dir():
            out.add(p.name.replace("batch_", "", 1))
    for p in (project_root / "experiments/snr_reports").glob("batch_*"):
        if p.is_dir():
            out.add(p.name.replace("batch_", "", 1))
    for p in (project_root / "experiments/sorting_reports").glob("*"):
        if p.is_dir():
            out.add(p.name)
    return sorted(out)


def _rename_snr_rows(rows: list[dict]) -> list[dict]:
    out = []
    for r in rows:
        out.append(
            {
                "样本目录": r.get("sample_dir", ""),
                "样本名": r.get("sample_name", ""),
                "低能 SNR": r.get("low_snr", 0.0),
                "高能 SNR": r.get("high_snr", 0.0),
                "低能半高宽占比": r.get("low_half_fwhm_over_mean", 0.0),
                "高能半高宽占比": r.get("high_half_fwhm_over_mean", 0.0),
                "半高宽是否通过": r.get("pass_half_fwhm", False),
                "66%跨度是否通过": r.get("pass_half66", False),
                "估计补偿倍数": r.get("beam_factor_est", 0.0),
            }
        )
    return out


def _rename_split_rows(rows: list[dict]) -> list[dict]:
    return [
        {
            "数据集": r.get("split", ""),
            "样本数": r.get("n", 0),
            "准确率": r.get("accuracy", 0.0),
            "精确率": r.get("precision", 0.0),
            "召回率": r.get("recall", 0.0),
            "F1": r.get("f1", 0.0),
            "TP": r.get("tp", 0),
            "TN": r.get("tn", 0),
            "FP": r.get("fp", 0),
            "FN": r.get("fn", 0),
        }
        for r in rows
    ]


def render(project_root: Path) -> None:
    st.subheader("结果分析")
    default_batch_id = st.session_state.get("selected_batch_id", "PbS_1M")
    candidates = _discover_batch_ids(project_root)
    if candidates:
        idx = candidates.index(default_batch_id) if default_batch_id in candidates else 0
        batch_id = st.selectbox("批次 ID", options=candidates, index=idx, key="results_batch_select")
    else:
        st.info("未找到可选批次。")
        batch_id = default_batch_id
    st.session_state["selected_batch_id"] = batch_id

    snr_summary_path = project_root / "experiments/snr_reports" / f"batch_{batch_id}" / "summary.json"
    sorting_r_path = project_root / "experiments/sorting_reports" / batch_id / "r_threshold_report.json"
    sorting_simple_path = project_root / "experiments/sorting_reports" / batch_id / "simple_feature_threshold_report.json"

    st.markdown("#### SNR 汇总")
    summary = load_snr_summary(snr_summary_path)
    if summary:
        c1, c2, c3 = st.columns(3)
        total = int(summary.get("total", 0))
        pass_count = int(summary.get("pass_count", 0))
        c1.metric("总样本数", total)
        c2.metric("通过数", pass_count)
        c3.metric("通过率", f"{(pass_count / total * 100.0) if total else 0.0:.1f}%")
        snr_rows = load_snr_reports(snr_summary_path.parent)
        if snr_rows:
            st.dataframe(_rename_snr_rows(snr_rows), use_container_width=True, hide_index=True)
    else:
        st.info(f"未找到文件：{snr_summary_path}")

    st.markdown("#### 分选报告")
    rpt = load_sorting_report(sorting_r_path)
    if rpt:
        st.caption(f"方法：{rpt.get('method')} / 阈值：{rpt.get('r_threshold')}")
        st.dataframe(_rename_split_rows(flatten_splits(rpt)), use_container_width=True, hide_index=True)
    else:
        st.info(f"未找到文件：{sorting_r_path}")
    rpt2 = load_sorting_report(sorting_simple_path)
    if rpt2:
        st.caption(f"方法：{rpt2.get('method')}")
        st.dataframe(_rename_split_rows(flatten_splits(rpt2)), use_container_width=True, hide_index=True)

