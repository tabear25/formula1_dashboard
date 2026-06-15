"""フレームワーク非依存のプロット生成コア。

Tkinter 版（`tabs/*.py`）と Streamlit 版（`streamlit_app.py`）の双方から呼ばれる。
各関数は `matplotlib.figure.Figure` を直接生成して返し、`pyplot` のグローバル状態や
`tkinter` には一切依存しない。配色は `config.py` の定数を流用する。

データが存在しない場合は `ChartDataError` を送出するので、呼び出し側
（Tkinter なら messagebox + Label、Streamlit なら st.warning）で表示を切り替える。
"""

import math
from collections import namedtuple

import numpy as np
import pandas as pd
import seaborn as sns
import fastf1
import fastf1.plotting
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.artist import setp

from config import COLOR_FRAME, COLOR_ACCENT, COLOR_HIGHLIGHT, COLOR_TEXT


class ChartDataError(Exception):
    """プロット／テーブル生成に必要なデータが存在しないときに送出する。"""
    pass


# --- 共通スタイル ------------------------------------------------------------

def _style_axes(ax, fig):
    """ダークテーマの共通軸スタイルを適用する。"""
    ax.grid(color="#333333")
    ax.set_facecolor(COLOR_FRAME)
    fig.patch.set_facecolor(COLOR_FRAME)
    ax.tick_params(colors=COLOR_TEXT, which="both")
    ax.xaxis.label.set_color(COLOR_TEXT)
    ax.yaxis.label.set_color(COLOR_TEXT)
    for spine in ax.spines.values():
        spine.set_edgecolor(COLOR_TEXT)


def _style_legend(leg):
    """凡例をダークテーマに合わせる。"""
    if not leg:
        return
    setp(leg.get_texts(), color=COLOR_TEXT)
    if leg.get_title() is not None:
        leg.get_title().set_color(COLOR_TEXT)
    frame = leg.get_frame()
    frame.set_facecolor(COLOR_FRAME)
    frame.set_edgecolor(COLOR_TEXT)


# --- サーキットマップ --------------------------------------------------------

def build_map_fig(session) -> Figure:
    """最速ラップの位置データからサーキットマップを描画する。"""
    lap = session.laps.pick_fastest()
    if lap is None or not hasattr(lap, "Driver"):
        raise ChartDataError("最速ラップが見つかりません。マップを表示できません。")

    try:
        pos = lap.get_pos_data()
    except Exception as e:
        raise ChartDataError(f"位置データ取得中にエラーが発生しました: {e}")
    if pos is None or pos.empty:
        raise ChartDataError("最速ラップの位置データが見つかりません。")

    cinfo = session.get_circuit_info()
    coords = pos.loc[:, ("X", "Y")].to_numpy()
    theta = cinfo.rotation / 180 * math.pi

    R = np.array([[math.cos(theta), -math.sin(theta)],
                  [math.sin(theta),  math.cos(theta)]])
    track = coords @ R

    fig = Figure(figsize=(6, 4), dpi=100, facecolor=COLOR_FRAME)
    ax = fig.add_subplot(111)
    ax.plot(track[:, 0], track[:, 1], color=COLOR_HIGHLIGHT, linewidth=2)

    offset0 = np.array([500, 0])

    def _rot(pt, ang):
        return pt @ np.array([[math.cos(ang), -math.sin(ang)],
                              [math.sin(ang),  math.cos(ang)]])

    for _, corner in cinfo.corners.iterrows():
        txt = f"{corner['Number']}{corner['Letter']}"
        ang_off = corner["Angle"] / 180 * math.pi
        off = _rot(offset0, ang_off)
        p_orig = np.array([corner["X"], corner["Y"]])
        text_pt = _rot(p_orig + off, theta)
        track_pt = _rot(p_orig, theta)
        ax.scatter(text_pt[0], text_pt[1], color="grey", s=100)
        ax.plot([track_pt[0], text_pt[0]], [track_pt[1], text_pt[1]], color="grey")
        ax.text(text_pt[0], text_pt[1], txt,
                va="center_baseline", ha="center", color="white", fontsize=6)

    ax.set_title(f"{session.event['Location']} {session.event.year}", color=COLOR_TEXT)
    ax.axis("equal")
    ax.axis("off")
    fig.patch.set_facecolor(COLOR_FRAME)
    fig.tight_layout()
    return fig


# --- 単一ドライバー速度テレメトリ -------------------------------------------

def build_telemetry_fig(session, driver: str) -> Figure:
    """単一ドライバーの最速ラップの速度テレメトリを描画する。"""
    lap = session.laps.pick_drivers(driver).pick_fastest()
    if lap is None or not hasattr(lap, "Driver"):
        raise ChartDataError(f"ドライバー {driver} の最速ラップが見つかりません。")

    try:
        tel = lap.get_car_data().add_distance()
    except Exception as e:
        raise ChartDataError(f"ドライバー {driver} のテレメトリ取得中にエラー: {e}")
    if tel is None or tel.empty:
        raise ChartDataError(f"ドライバー {driver} のテレメトリデータが見つかりません。")

    fig = Figure(figsize=(6, 4), dpi=100, facecolor=COLOR_FRAME)
    ax = fig.add_subplot(111)
    ax.plot(tel["Distance"], tel["Speed"], color=COLOR_HIGHLIGHT, label=driver)
    ax.set_xlabel("Distance (m)", color=COLOR_TEXT)
    ax.set_ylabel("Speed (km/h)", color=COLOR_TEXT)
    ax.set_title(
        f"Fastest Lap Telemetry – {driver} – "
        f"{session.event['EventName']} {session.event.year}",
        color=COLOR_TEXT, fontsize=9,
    )
    _style_axes(ax, fig)
    _style_legend(ax.legend())
    fig.tight_layout()
    return fig


# --- 複数ドライバー速度比較 --------------------------------------------------

def build_speed_fig(session, drivers) -> Figure:
    """複数ドライバーの最速ラップ速度を重ねて比較する。"""
    fig = Figure(figsize=(6, 4), dpi=100, facecolor=COLOR_FRAME)
    ax = fig.add_subplot(111)

    at_least_one_plotted = False
    for drv in drivers:
        lap = session.laps.pick_drivers(drv).pick_fastest()
        if lap is None or not hasattr(lap, "Driver"):
            continue
        try:
            tel = lap.get_car_data().add_distance()
        except Exception:
            continue
        if tel is None or tel.empty:
            continue

        style = fastf1.plotting.get_driver_style(
            identifier=drv, style=["color", "linestyle"], session=session,
        )
        ax.plot(tel["Distance"], tel["Speed"], label=drv, **style)
        at_least_one_plotted = True

    if not at_least_one_plotted:
        raise ChartDataError("選択されたドライバーの有効なテレメトリデータが見つかりませんでした。")

    ax.set_xlabel("Distance (m)", color=COLOR_TEXT)
    ax.set_ylabel("Speed (km/h)", color=COLOR_TEXT)
    ax.set_title(
        f"Fastest Lap Speed Comparison – {session.event['EventName']} {session.event.year}",
        color=COLOR_TEXT, fontsize=9,
    )
    _style_axes(ax, fig)
    _style_legend(ax.legend())
    fig.tight_layout()
    return fig


# --- 複数ドライバーラップタイム比較（バイオリンプロット）---------------------

def build_compare_fig(session, drivers) -> Figure:
    """複数ドライバーのクイックラップ分布をバイオリンプロットで比較する。"""
    laps_df = session.laps.pick_quicklaps().reset_index()
    if laps_df.empty:
        raise ChartDataError("比較対象のクイックラップが見つかりません。")

    df = laps_df[laps_df["Driver"].isin(drivers)].copy()
    if df.empty:
        raise ChartDataError(
            f"選択されたドライバー ({', '.join(drivers)}) のクイックラップが見つかりません。")

    df["LapTime_s"] = df["LapTime"].dt.total_seconds()

    fig = Figure(figsize=(6, 4), dpi=100, facecolor=COLOR_FRAME)
    ax = fig.add_subplot(111)

    palette = {drv: COLOR_ACCENT for drv in drivers}
    sns.violinplot(data=df, x="Driver", y="LapTime_s", hue="Driver",
                   inner="quartile", cut=0, ax=ax,
                   order=drivers, hue_order=drivers,
                   palette=palette, legend=False)

    medians_series = df.groupby("Driver")["LapTime_s"].median()
    valid_drivers = [d for d in drivers if d in medians_series and pd.notna(medians_series.get(d))]
    valid_medians = [medians_series.get(d) for d in valid_drivers]
    x_coords = [drivers.index(d) for d in valid_drivers]
    if x_coords:
        ax.plot(x_coords, valid_medians, marker="o", linestyle="--", color=COLOR_HIGHLIGHT)

    ax.invert_yaxis()
    ax.set_xlabel("Driver")
    ax.set_ylabel("LapTime (s)")
    ax.set_title(
        f"LapTime Comparison – {session.event['EventName']} {session.event.year}",
        color=COLOR_TEXT, fontsize=9,
    )
    _style_axes(ax, fig)
    fig.tight_layout()
    return fig


# --- 単一ドライバーラップ散布図 ---------------------------------------------

def build_scatter_single_fig(session, driver: str) -> Figure:
    """単一ドライバーのクイックラップをコンパウンド別に散布図表示する。"""
    laps_df = session.laps.pick_drivers(driver).pick_quicklaps().reset_index()
    if laps_df.empty:
        raise ChartDataError(f"ドライバー {driver} のクイックラップが見つかりません。")

    laps_to_plot = laps_df.copy()
    if pd.api.types.is_timedelta64_dtype(laps_to_plot.get("LapTime", pd.Series())):
        laps_to_plot["LapTime_s"] = laps_to_plot["LapTime"].dt.total_seconds()
        y_col, y_label = "LapTime_s", "Lap Time (s)"
    else:
        y_col, y_label = "LapTime", "Lap Time"

    fig = Figure(figsize=(7, 5), dpi=100, facecolor=COLOR_FRAME)
    ax = fig.add_subplot(111)

    compound_mapping = fastf1.plotting.get_compound_mapping(session)
    sns.scatterplot(data=laps_to_plot, x="LapNumber", y=y_col,
                    hue="Compound", palette=compound_mapping,
                    s=50, linewidth=0, ax=ax, legend="auto")
    _style_legend(ax.get_legend())

    ax.invert_yaxis()
    ax.set_title(
        f"{driver} - Lap Times - {session.event.year} {session.event['EventName']}",
        color=COLOR_TEXT, fontsize=10,
    )
    ax.set_xlabel("Lap Number", color=COLOR_TEXT)
    ax.set_ylabel(y_label, color=COLOR_TEXT)
    _style_axes(ax, fig)
    ax.grid(color="#444444", linestyle="--", linewidth=0.5)
    fig.tight_layout()
    return fig


# --- 複数ドライバーラップ散布図比較（2x2）-----------------------------------

_COMPOUND_ORDER = ["SOFT", "MEDIUM", "HARD", "INTERMEDIATE", "WET"]


def build_scatter_compare_fig(session, drivers) -> Figure:
    """最大4名のクイックラップ散布図を 2x2 で並べて比較する。"""
    laps_df = session.laps.pick_quicklaps().reset_index()
    if laps_df.empty:
        raise ChartDataError("比較対象のクイックラップが見つかりません。")

    drivers_in_data = [d for d in drivers if d in laps_df["Driver"].unique()]
    if not drivers_in_data:
        raise ChartDataError(
            f"選択されたドライバー ({', '.join(drivers)}) のクイックラップデータが見つかりません。")

    plot_drivers = drivers_in_data[:4]
    laps_to_plot = laps_df[laps_df["Driver"].isin(plot_drivers)].copy()

    if pd.api.types.is_timedelta64_dtype(laps_to_plot.get("LapTime", pd.Series())):
        laps_to_plot["LapTime_s"] = laps_to_plot["LapTime"].dt.total_seconds()
        y_col, y_label = "LapTime_s", "Lap Time (s)"
    else:
        y_col, y_label = "LapTime", "Lap Time"

    fig = Figure(figsize=(8, 6), facecolor=COLOR_FRAME)
    axes = fig.subplots(2, 2)
    fig.subplots_adjust(hspace=0.4, wspace=0.3)

    compound_mapping = fastf1.plotting.get_compound_mapping(session)

    for i, drv in enumerate(plot_drivers):
        ax = axes.flatten()[i]
        df_drv = laps_to_plot[laps_to_plot["Driver"] == drv]
        if df_drv.empty:
            ax.text(0.5, 0.5, f"{drv}\nNo Data",
                    ha="center", va="center", transform=ax.transAxes, color=COLOR_TEXT)
        else:
            sns.scatterplot(data=df_drv, x="LapNumber", y=y_col,
                            hue="Compound", palette=compound_mapping,
                            s=40, linewidth=0, ax=ax, legend=False)
            ax.invert_yaxis()
            ax.set_xlabel("Lap #", color=COLOR_TEXT)
            ax.set_ylabel(y_label, color=COLOR_TEXT)

        ax.set_title(drv, color=COLOR_TEXT, fontsize=8)
        ax.set_facecolor(COLOR_FRAME)
        ax.tick_params(colors=COLOR_TEXT, which="both")
        for spine in ax.spines.values():
            spine.set_edgecolor(COLOR_TEXT)

    for j in range(len(plot_drivers), 4):
        axes.flatten()[j].axis("off")

    # 各サブプロットに凡例を出すとドライバーごとに使用コンパウンドが異なり不完全に
    # なるため、全パネル共通の凡例を figure 単位で1つ表示する。
    compounds_present = sorted(
        (c for c in laps_to_plot["Compound"].dropna().unique()),
        key=lambda c: _COMPOUND_ORDER.index(c) if c in _COMPOUND_ORDER else len(_COMPOUND_ORDER),
    )
    if compounds_present:
        handles = [
            Line2D([0], [0], marker="o", linestyle="", markersize=7,
                   markerfacecolor=compound_mapping.get(c, COLOR_TEXT),
                   markeredgecolor="none", label=c)
            for c in compounds_present
        ]
        leg = fig.legend(handles=handles, title="Compound",
                         loc="upper center", ncol=len(handles), fontsize=8,
                         facecolor=COLOR_FRAME, edgecolor=COLOR_TEXT)
        setp(leg.get_texts(), color=COLOR_TEXT)
        leg.get_title().set_color(COLOR_TEXT)

    fig.patch.set_facecolor(COLOR_FRAME)
    fig.tight_layout(rect=[0, 0, 1, 0.92])
    return fig


# --- セッション結果テーブル --------------------------------------------------

def format_timedelta(td) -> str:
    """Pandas Timedelta を HH:MM:SS.mmm 形式の文字列に整形する。"""
    if pd.isna(td):
        return ""
    total_seconds = td.total_seconds()
    sign = "-" if total_seconds < 0 else ""
    total_seconds = abs(total_seconds)

    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    milliseconds = int(round((seconds - int(seconds)) * 1000))

    if milliseconds >= 1000:
        milliseconds -= 1000
        seconds += 1
        if seconds >= 60:
            seconds -= 60
            minutes += 1
            if minutes >= 60:
                minutes -= 60
                hours += 1

    if hours > 0:
        return f"{sign}{int(hours):01d}:{int(minutes):02d}:{int(seconds):02d}.{milliseconds:03d}"
    elif minutes > 0:
        return f"{sign}{int(minutes):01d}:{int(seconds):02d}.{milliseconds:03d}"
    else:
        return f"{sign}{float(seconds):06.3f}"


# columns: list[(header_text, width)] / rows: list[tuple[str, ...]]
ResultsTable = namedtuple("ResultsTable", ["columns", "rows"])


def build_results_table(session) -> ResultsTable:
    """セッション結果を整形済みのテーブル（列メタ + 行データ）にして返す。

    Treeview（デスクトップ）にも DataFrame（Streamlit）にも流用できるよう、
    表示用に文字列整形済みの行と、列ヘッダー・推奨幅のメタ情報を返す。
    """
    try:
        has_results = (
            hasattr(session, "results")
            and session.results is not None
            and not session.results.empty
        )
    except Exception as e:
        raise ChartDataError(f"結果データの確認中にエラー: {type(e).__name__}: {e}")

    if not has_results:
        raise ChartDataError(
            "このセッションの結果データはありません。\n"
            "(または、このセッションタイプには結果がありません)")

    results_df = session.results.copy()
    session_type_name = session.name

    # id: (Header Text, Default Width, Data Type Hint)
    columns_config = {
        "Position": ("Pos", 40, "int"),
        "Abbreviation": ("Driver", 70, "str"),
        "TeamName": ("Team", 130, "str"),
        "Time": ("Time/Gap", 100, "timedelta"),
        "Status": ("Status", 100, "str"),
        "Laps": ("Laps", 40, "int"),
        "GridPosition": ("Grid", 40, "int"),
        "Points": ("Pts", 40, "float"),
    }

    if session_type_name == "Qualifying":
        columns_config.update({
            "Q1": ("Q1", 80, "timedelta"),
            "Q2": ("Q2", 80, "timedelta"),
            "Q3": ("Q3", 80, "timedelta"),
        })
        columns_config.pop("Time", None)
        columns_config.pop("Status", None)
        columns_config.pop("FastestLapTime", None)
    elif session_type_name in ["Race", "Sprint Race", "Sprint"]:
        columns_config.update({
            "FastestLapTime": ("Fastest Lap", 90, "timedelta"),
        })
    else:  # Practice
        columns_config.pop("GridPosition", None)
        columns_config.pop("Points", None)
        columns_config.pop("Status", None)
        if "Time" in results_df.columns:
            columns_config["Time"] = ("Best Lap", 90, "timedelta")
        elif "FastestLapTime" in results_df.columns:
            columns_config["FastestLapTime"] = ("Best Lap", 90, "timedelta")
            results_df.rename(columns={"FastestLapTime": "Time"}, inplace=True)
        columns_config.pop("FastestLapTime", None)

    # FullName を Abbreviation の直後に挿入。無ければ get_driver で補完。
    if "FullName" not in results_df.columns and "DriverNumber" in results_df.columns:
        full_names = []
        for driver_number in results_df["DriverNumber"]:
            try:
                driver_info = session.get_driver(driver_number)
                if driver_info is not None and "FullName" in driver_info:
                    full_names.append(driver_info["FullName"])
                else:
                    full_names.append("")
            except Exception:
                full_names.append("")
        results_df["FullName"] = full_names

    if "FullName" in results_df.columns:
        temp_cols = list(columns_config.items())
        try:
            abbr_index = [i for i, (k, v) in enumerate(temp_cols) if k == "Abbreviation"][0]
            temp_cols.insert(abbr_index + 1, ("FullName", ("Full Name", 150, "str")))
            columns_config = dict(temp_cols)
        except IndexError:
            columns_config["FullName"] = ("Full Name", 150, "str")

    col_ids = [cid for cid in columns_config.keys() if cid in results_df.columns]
    if not col_ids:
        raise ChartDataError("表示できる結果の列が見つかりませんでした。")

    rows = []
    for _, row in results_df.iterrows():
        values = []
        for cid in col_ids:
            val = row.get(cid)
            _, _, data_type = columns_config[cid]
            if pd.isna(val):
                values.append("")
            elif data_type == "timedelta":
                values.append(format_timedelta(val))
            elif data_type == "int":
                try:
                    values.append(str(int(float(str(val)))))
                except ValueError:
                    values.append(str(val))
            elif data_type == "float":
                try:
                    values.append(f"{float(str(val)):.1f}")
                except ValueError:
                    values.append(str(val))
            else:
                values.append(str(val))
        rows.append(tuple(values))

    columns = [(columns_config[cid][0], columns_config[cid][1]) for cid in col_ids]
    return ResultsTable(columns=columns, rows=rows)
