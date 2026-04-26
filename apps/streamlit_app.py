from __future__ import annotations

from pathlib import Path

import streamlit as st

from pages import overview, progress, results, run_config, sample_explorer
from task_service import TaskService


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@st.cache_resource
def get_task_service() -> TaskService:
    return TaskService(PROJECT_ROOT)


def main() -> None:
    st.set_page_config(page_title="XRay 仿真看板", layout="wide")
    st.markdown(
        """
        <style>
            /* 保留顶部工具栏，否则侧边栏收起后无法找到展开入口 */
            [data-testid="stToolbar"] {display: block;}
            /* 隐藏右上角无关英文状态元素 */
            [data-testid="stStatusWidget"] {display: none;}
            #MainMenu {visibility: hidden;}
            /* 强制显示侧边栏展开按钮（收起后也可见） */
            [data-testid="stSidebarCollapsedControl"] {
                display: flex !important;
                position: fixed !important;
                left: 0.75rem;
                top: 0.75rem;
                z-index: 1000;
                opacity: 1 !important;
            }
            /* 左侧导航菜单美化（简洁版） */
            [data-testid="stSidebar"] {
                border-right: 1px solid rgba(120, 120, 120, 0.18);
            }
            [data-testid="stSidebar"] .stRadio > div[role="radiogroup"] {
                gap: 0.28rem;
            }
            [data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label {
                border: 1px solid transparent;
                border-radius: 8px;
                padding: 0.38rem 0.62rem;
                background: transparent;
                transition: all 120ms ease;
                width: 100%;
            }
            [data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label:hover {
                background: rgba(120, 120, 120, 0.10);
                border-color: rgba(120, 120, 120, 0.18);
            }
            [data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label[data-selected="true"] {
                background: rgba(255, 75, 75, 0.10);
                border-color: rgba(255, 75, 75, 0.30);
                box-shadow: inset 3px 0 0 rgba(255, 75, 75, 0.90);
            }
            [data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label > div:first-child {
                display: none;
            }
            [data-testid="stSidebar"] .stRadio > label {
                font-size: 0.86rem;
                font-weight: 600;
                margin-bottom: 0.20rem;
                color: rgba(60, 60, 60, 0.95);
            }
            [data-testid="stSidebar"] .stRadio p {
                font-size: 1.04rem;
                font-weight: 600;
                margin: 0;
                line-height: 1.25;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.title("XRay 仿真看板")
    st.caption("查看仿真进度、分选结果，并支持参数化提交任务")

    task_service = get_task_service()

    st.sidebar.markdown("### 导航菜单")
    page = st.sidebar.radio(
        "页面",
        options=["总览", "任务配置", "任务进度", "结果分析", "样本浏览"],
    )

    if page == "总览":
        overview.render(task_service)
    elif page == "任务配置":
        run_config.render(task_service, PROJECT_ROOT)
    elif page == "任务进度":
        progress.render(task_service)
    elif page == "结果分析":
        results.render(PROJECT_ROOT)
    elif page == "样本浏览":
        sample_explorer.render(PROJECT_ROOT)


if __name__ == "__main__":
    main()
