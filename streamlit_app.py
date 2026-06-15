"""F1 Data Dashboard – Streamlit Web 版エントリポイント。

デスクトップ（Tkinter）版の `main.py` と同等の分析を、ブラウザから利用できる
Web アプリとして提供する。プロット生成は `core/charts.py`、データ取得は
`core/data.py` を共有する（単一の真実のソース）。

ローカル実行:
    streamlit run streamlit_app.py
"""

import matplotlib
matplotlib.use("Agg")  # ヘッドレス描画（GUI バックエンドを使わない）

import fastf1.plotting
import pandas as pd
import streamlit as st

from config import APP_TITLE, MPL_STYLE, YEAR_LIST
from core.charts import (
    ChartDataError,
    build_compare_fig,
    build_map_fig,
    build_results_table,
    build_scatter_compare_fig,
    build_scatter_single_fig,
    build_speed_fig,
    build_telemetry_fig,
)
from core.data import driver_abbreviations, get_event_names, load_session

SESSION_TYPES = ["FP1", "FP2", "FP3", "Q", "R"]


@st.cache_resource(show_spinner=False)
def _setup_mpl():
    """FastF1 の matplotlib スタイルを一度だけ適用する。"""
    if MPL_STYLE:
        try:
            fastf1.plotting.setup_mpl(mpl_timedelta_support=True, color_scheme=MPL_STYLE)
        except Exception:
            pass
    return True


def _show_fig(builder, *args):
    """Figure ビルダーを実行し、結果を描画する。データ無しは警告表示。

    `use_container_width=True` で図を列幅に追従させ、画面幅（PC/タブレット/スマホ）に
    応じて自動でスケールさせる（レスポンシブ）。
    """
    try:
        fig = builder(*args)
    except ChartDataError as e:
        st.warning(str(e))
        return
    except Exception as e:  # noqa: BLE001 - 予期せぬ描画エラーも UI に出す
        st.error(f"描画中にエラーが発生しました: {e}")
        return
    st.pyplot(fig, use_container_width=True)


def _inject_responsive_css():
    """画面幅に応じてレイアウトを最適化するレスポンシブ CSS を注入する。

    Streamlit は既定でも幅に追従するが、スマホ／タブレットでの可読性を上げるため
    余白・見出しサイズ・タブの折り返し等を CSS のメディアクエリで調整する。
    """
    st.markdown(
        """
        <style>
        /* 見出しはビューポート幅に応じて滑らかにスケール（clamp でレスポンシブ） */
        h1 { font-size: clamp(1.4rem, 4vw, 2.2rem) !important; }
        h2 { font-size: clamp(1.15rem, 3vw, 1.6rem) !important; }
        h3 { font-size: clamp(1.0rem, 2.6vw, 1.3rem) !important; }

        /* タブが多くてもスマホで折り返さず横スクロールで全件アクセスできるように */
        .stTabs [data-baseweb="tab-list"] {
            overflow-x: auto;
            flex-wrap: nowrap;
            scrollbar-width: thin;
        }
        .stTabs [data-baseweb="tab"] { white-space: nowrap; }

        /* タブレット以下: 本文余白を詰めて描画領域を最大化 */
        @media (max-width: 1024px) {
            .block-container { padding-left: 2rem; padding-right: 2rem; }
        }

        /* スマホ: さらに余白を詰め、タブ文字を縮小して片手操作に最適化 */
        @media (max-width: 640px) {
            .block-container {
                padding-top: 2.5rem;
                padding-left: 0.8rem;
                padding-right: 0.8rem;
            }
            .stTabs [data-baseweb="tab"] { font-size: 0.8rem; padding: 0 0.5rem; }
            /* 画像（matplotlib 図）は常にコンテナ幅にフィット */
            div[data-testid="stImage"] img { width: 100% !important; height: auto !important; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def main():
    st.set_page_config(page_title=APP_TITLE, page_icon="🏁", layout="wide",
                       initial_sidebar_state="auto")
    _inject_responsive_css()
    _setup_mpl()

    st.title("🏁 F1 Data Dashboard")

    # --- サイドバー: データ選択 ---------------------------------------------
    with st.sidebar:
        st.header("データ選択")
        default_year_index = len(YEAR_LIST) - 1 if YEAR_LIST else 0
        year = st.selectbox("開催年", YEAR_LIST, index=default_year_index)

        try:
            gp_names = get_event_names(int(year))
        except Exception as e:  # noqa: BLE001
            st.error(f"スケジュール取得に失敗しました: {e}")
            gp_names = []

        gp = st.selectbox("グランプリ", gp_names) if gp_names else None
        ses = st.selectbox("セッション", SESSION_TYPES, index=len(SESSION_TYPES) - 1)

        if st.button("セッションを読み込む", type="primary", use_container_width=True,
                     disabled=not gp):
            st.session_state["target"] = (int(year), gp, ses)

    target = st.session_state.get("target")
    if not target:
        st.info("サイドバーで 開催年・グランプリ・セッション を選び、"
                "「セッションを読み込む」を押してください。")
        _render_overview()
        return

    t_year, t_gp, t_ses = target
    try:
        with st.spinner(f"{t_year} {t_gp} – {t_ses} を読み込み中..."
                        "（初回はデータDLのため時間がかかります）"):
            session = load_session(t_year, t_gp, t_ses)
    except Exception as e:  # noqa: BLE001
        st.error(f"セッションの読み込みに失敗しました: {e}\n"
                 "年・グランプリ・セッションの組み合わせやネットワークを確認してください。")
        return

    drivers = driver_abbreviations(session)
    selected = st.sidebar.multiselect("ドライバー（複数選択可）", drivers)
    st.sidebar.caption("テレメトリ／ラップ散布図（単一）は先頭の1名を使用します。")

    st.caption(f"読み込み済み: **{t_year} {t_gp} – {t_ses}**")

    # --- 分析タブ ------------------------------------------------------------
    tabs = st.tabs([
        "🏁 Overview", "🗺️ Map", "📊 Results",
        "📈 Telemetry (Single)", "📈 Lap Scatter (Single)",
        "📊 LapTime Compare", "🏎️ Speed Compare", "📊 Scatter Compare",
    ])

    with tabs[0]:
        _render_overview()

    with tabs[1]:
        _show_fig(build_map_fig, session)

    with tabs[2]:
        try:
            table = build_results_table(session)
            df = pd.DataFrame(table.rows, columns=[h for h, _ in table.columns])
            st.dataframe(df, use_container_width=True, hide_index=True)
        except ChartDataError as e:
            st.warning(str(e))
        except Exception as e:  # noqa: BLE001
            st.error(f"結果表示中にエラーが発生しました: {e}")

    with tabs[3]:
        if not selected:
            st.info("サイドバーでドライバーを1名以上選択してください。")
        else:
            _show_fig(build_telemetry_fig, session, selected[0])

    with tabs[4]:
        if not selected:
            st.info("サイドバーでドライバーを1名以上選択してください。")
        else:
            _show_fig(build_scatter_single_fig, session, selected[0])

    with tabs[5]:
        if not selected:
            st.info("サイドバーで比較するドライバーを選択してください。")
        else:
            _show_fig(build_compare_fig, session, selected)

    with tabs[6]:
        if not selected:
            st.info("サイドバーで比較するドライバーを選択してください。")
        else:
            _show_fig(build_speed_fig, session, selected)

    with tabs[7]:
        if not selected:
            st.info("サイドバーで比較するドライバーを選択してください（最大4名）。")
        else:
            if len(selected) > 4:
                st.caption("散布図比較は最大4名まで。先頭の4名を表示します。")
            _show_fig(build_scatter_compare_fig, session, selected)


def _render_overview():
    st.subheader("F1 Data Dashboard")
    st.markdown(
        """
        FastF1 の過去グランプリのセッションデータ（ラップタイム・テレメトリ・順位など）を
        可視化・分析する Web ダッシュボードです。

        **使い方**
        1. サイドバーで **開催年 → グランプリ → セッション** を選択し、「セッションを読み込む」を押す。
        2. 読み込み後、サイドバーに表示される **ドライバー** を選択する。
        3. 上部の各タブ（Map / Results / Telemetry / 各種比較）で分析結果を確認する。

        ※ 初回のデータ読み込みはダウンロードのため時間がかかります（2回目以降はキャッシュで高速）。
        """
    )


if __name__ == "__main__":
    main()
