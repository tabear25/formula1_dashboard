import os
import sys
import json
import math
import shutil
import logging
from datetime import datetime, timedelta
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, Future
import fastf1
import pandas as pd
import numpy as np
import matplotlib
import tkinter as tk
from tkinter import ttk, messagebox
from tkinter import font as tkfont
import seaborn as sns
import fastf1.plotting
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
import plotly.io as pio
# ---------------------------------------------------------------
APP_TITLE   = "F1 Information Dashboard"
WINDOW_SIZE = "1400x900"

COLOR_BG        = "#161E2F"
COLOR_FRAME     = "#242F48"
COLOR_FRAME_2   = "#384358"
COLOR_ACCENT    = "#B51A2B"
COLOR_ACCENT_2  = "#591A2E"
COLOR_HIGHLIGHT = "#FFA586"
COLOR_TEXT      = "#FFFFFF"

CACHE_DIR           = Path(os.getenv("TEMP", ".")) / "fastf1_cache"
CACHE_SIZE_LIMIT_GB = 2
CACHE_EXPIRE_DAYS   = 30

YEAR_LIST = list(range(1950, datetime.now().year + 1))
EXECUTOR  = ThreadPoolExecutor(max_workers=4, thread_name_prefix="FastF1Worker")
# ================================================================
class CacheManager:
    @staticmethod
    def ensure_cache_dir() -> None:
        os.makedirs(CACHE_DIR, exist_ok=True)
        fastf1.Cache.enable_cache(str(CACHE_DIR))

    @staticmethod
    def cleanup_cache() -> None:
        total_bytes = 0
        now = datetime.now()
        for root, _, files in os.walk(CACHE_DIR):
            for f in files:
                fp = Path(root) / f
                try:
                    stat = fp.stat()
                except FileNotFoundError:
                    continue
                total_bytes += stat.st_size
                if (now - datetime.fromtimestamp(stat.st_atime)).days > CACHE_EXPIRE_DAYS:
                    fp.unlink(missing_ok=True)
        if total_bytes > CACHE_SIZE_LIMIT_GB * 1024**3:
            shutil.rmtree(CACHE_DIR, ignore_errors=True)
            os.makedirs(CACHE_DIR, exist_ok=True)

class FastF1Service:
    def __init__(self):
        CacheManager.ensure_cache_dir()

    def get_event_schedule_async(self, year:int) -> Future:
        return EXECUTOR.submit(fastf1.get_event_schedule, year)

    def load_session_async(self, year:int, gp:str, ses:str) -> Future:
        def _inner():
            s = fastf1.get_session(year, gp, ses)
            s.load()
            return s
        return EXECUTOR.submit(_inner)

# ================================================================
class MainTab(ttk.Notebook):
    def __init__(self, master:tk.Misc, **kw):
        super().__init__(master, **kw)
        self.configure(style="MainNotebook.TNotebook")

        # Overview タブ
        self.overview_frame = tk.Frame(self, bg=COLOR_FRAME)
        tk.Label(self.overview_frame, text="📂 データを読み込んでください",
                 fg=COLOR_TEXT, bg=COLOR_FRAME).pack(expand=True)
        self.add(self.overview_frame, text="🏁 Overview")

        # Map タブ
        self.map_frame = tk.Frame(self, bg=COLOR_FRAME)
        tk.Label(self.map_frame, text="🌐 サーキットマップ",
                 fg=COLOR_TEXT, bg=COLOR_FRAME).pack()
        self.add(self.map_frame, text="🗺️ Map")

        # Compare タブ
        self.compare_frame = tk.Frame(self, bg=COLOR_FRAME)
        tk.Label(self.compare_frame, text="👥 ドライバー比較",
                 fg=COLOR_TEXT, bg=COLOR_FRAME).pack()
        self.add(self.compare_frame, text="👥 Compare")

        # Canvas／Figure保持用
        self._map_fig     = None
        self._map_canvas  = None
        self._compare_fig    = None
        self._compare_canvas = None

    # ------------ Map 描画 ------------
    def show_map(self, session):
        """Map タブにサーキットマップを表示"""
        # 前の表示クリア
        if self._map_canvas:
            self._map_canvas.get_tk_widget().destroy()
        # テレメトリから座標取得
        lap = session.laps.pick_fastest()
        pos = lap.get_pos_data()
        c_info = session.get_circuit_info()
        track = pos.loc[:,("X","Y")].to_numpy()
        theta = c_info.rotation/180 * math.pi
        rot = np.array([[math.cos(theta), math.sin(theta)],
                        [-math.sin(theta), math.cos(theta)]])
        track_rot = track @ rot.T

        # Figure 作成
        self._map_fig = plt.Figure(figsize=(6,4), dpi=100, facecolor=COLOR_FRAME)
        ax = self._map_fig.add_subplot(111)
        ax.plot(track_rot[:,0], track_rot[:,1],
                color=COLOR_HIGHLIGHT, linewidth=2)
        ax.set_title(f"{session.event['Location']} {session.event.year}",
                     color=COLOR_TEXT)
        ax.axis("equal"); ax.axis("off")
        self._map_fig.tight_layout()

        # 埋め込み
        self._map_canvas = FigureCanvasTkAgg(self._map_fig, master=self.map_frame)
        self._map_canvas.draw()
        self._map_canvas.get_tk_widget().pack(expand=True, fill="both")

    # ------------ 速度テレメトリ描画 ------------
    def show_driver_speed(self, session, driver: str):
        """最速ラップのテレメトリを表示"""
        if hasattr(self, '_overview_canvas') and self._overview_canvas:
            self._overview_canvas.get_tk_widget().destroy()
        fastf1.plotting.setup_mpl(misc_mpl_mods=False, color_scheme='fastf1')
        lap = session.laps.pick_drivers(driver).pick_fastest()
        cdat = lap.get_car_data()
        t = cdat['Time']; v = cdat['Speed']
        self._overview_fig = plt.Figure(figsize=(6,4), dpi=100, facecolor=COLOR_FRAME)
        ax = self._overview_fig.add_subplot(111)
        ax.plot(t, v, label=driver, color=COLOR_HIGHLIGHT)
        ax.set_xlabel("Time"); ax.set_ylabel("Speed [km/h]")
        ax.set_title(f"Speed Telemetry - {driver}", color=COLOR_TEXT)
        ax.grid(True); ax.legend()
        ax.set_facecolor(COLOR_FRAME); self._overview_fig.patch.set_facecolor(COLOR_FRAME)
        for sp in ax.spines.values(): sp.set_visible(False)
        self._overview_fig.tight_layout()
        self._overview_canvas = FigureCanvasTkAgg(self._overview_fig, master=self.overview_frame)
        self._overview_canvas.draw()
        self._overview_canvas.get_tk_widget().pack(expand=True, fill="both")

    # ------------ ラップタイム散布図描画 ------------
    def show_lap_time_scatter(self, session, driver: str):
        """ラップタイム散布図を表示"""
        if session.name.lower() != "race":
            messagebox.showinfo("未対応", "ラップタイム散布図は決勝セッション (R) でのみ利用できます。")
            return
        if hasattr(self, '_overview_canvas') and self._overview_canvas:
            self._overview_canvas.get_tk_widget().destroy()
        fastf1.plotting.setup_mpl(mpl_timedelta_support=True, misc_mpl_mods=False, color_scheme='fastf1')
        laps_df = session.laps.pick_quicklaps().reset_index()
        drv_laps = laps_df[laps_df['Driver'] == driver]
        self._overview_fig = plt.Figure(figsize=(6,4), dpi=100, facecolor=COLOR_FRAME)
        ax = self._overview_fig.add_subplot(111)
        sns.scatterplot(data=drv_laps, x="LapNumber", y="LapTime",
                        hue="Compound",
                        palette=fastf1.plotting.get_compound_mapping(session=session),
                        s=60, linewidth=0, ax=ax, legend=False)
        ax.invert_yaxis()
        ax.set_xlabel("Lap #"); ax.set_ylabel("Lap Time")
        ax.set_title(f"Tyre LapTime – {driver}", color=COLOR_TEXT)
        ax.grid(True); ax.set_facecolor(COLOR_FRAME)
        for sp in ax.spines.values(): sp.set_visible(False)
        self._overview_fig.tight_layout()
        self._overview_canvas = FigureCanvasTkAgg(self._overview_fig, master=self.overview_frame)
        self._overview_canvas.draw()
        self._overview_canvas.get_tk_widget().pack(expand=True, fill="both")

    # ------------ Compare 描画 ------------
    def show_multi_driver_compare(self, session, drivers:list[str]):
        """Compare タブに複数ドライバーのラップタイム比較 (Violin + メディアン)"""
        # 2〜4名チェック
        if not (2 <= len(drivers) <= 4):
            messagebox.showinfo("ドライバー選択",
                                "2～4名のドライバーを選択してください。")
            return

        # 前の表示クリア
        if self._compare_canvas:
            self._compare_canvas.get_tk_widget().destroy()

        # ラップタイム取得
        laps_df = session.laps.pick_quicklaps().reset_index()
        all_laps = laps_df[laps_df['Driver'].isin(drivers)].copy()
        all_laps['LapTime_s'] = all_laps['LapTime'].dt.total_seconds()
        # 秒単位に変換
        all_laps['LapTime_s'] = all_laps['LapTime'].dt.total_seconds()

        # Figure 作成
        self._compare_fig = plt.Figure(figsize=(6,4), dpi=100, facecolor=COLOR_FRAME)
        ax = self._compare_fig.add_subplot(111)

        # Violin プロット
        sns.violinplot(data=all_laps, x='Driver', y='LapTime_s',
                       inner='quartile', cut=0, ax=ax,
                       palette=[COLOR_ACCENT]*len(drivers))
        # メディアンライン
        meds = all_laps.groupby('Driver')['LapTime_s'].median()
        positions = list(range(len(drivers)))
        ax.plot(positions, meds.values, marker='o',
                color=COLOR_HIGHLIGHT, linestyle='--')

        # 軸調整
        ax.invert_yaxis()  # ラップタイムは小さいほど良いので反転
        ax.set_xlabel("Driver"); ax.set_ylabel("LapTime (s)")
        ax.set_title(f"LapTime Comparison – {session.event['EventName']} {session.event.year}",
                     color=COLOR_TEXT, fontsize=9)
        ax.grid(color="#333333")
        ax.set_facecolor(COLOR_FRAME)
        self._compare_fig.patch.set_facecolor(COLOR_FRAME)

        # 埋め込み
        self._compare_canvas = FigureCanvasTkAgg(self._compare_fig, master=self.compare_frame)
        self._compare_canvas.draw()
        self._compare_canvas.get_tk_widget().pack(expand=True, fill="both")

# ================================================================
class Sidebar(tk.Frame):
    def __init__(self, master:tk.Misc,
                 svc:FastF1Service, main_tab:MainTab, **kw):
        super().__init__(master, bg=COLOR_FRAME, **kw)
        self.svc           = svc
        self.main_tab      = main_tab
        self.current_session = None

        default_font = tkfont.nametofont("TkDefaultFont")
        default_font.configure(size=10, weight="bold")

        # 年度選択
        tk.Label(self, text="開催年", bg=COLOR_FRAME, fg=COLOR_TEXT)\
            .pack(anchor="w", padx=10, pady=5)
        self.year_var = tk.IntVar(value=datetime.now().year)
        self.year_lb  = tk.Listbox(self, listvariable=tk.StringVar(value=YEAR_LIST), height=10)
        self.year_lb.pack(fill="x", padx=10)
        self.year_lb.bind("<<ListboxSelect>>", self._on_year)

        # GP選択
        tk.Label(self, text="グランプリ", bg=COLOR_FRAME, fg=COLOR_TEXT)\
            .pack(anchor="w", padx=10, pady=5)
        self.gp_var = tk.StringVar()
        self.gp_lb  = tk.Listbox(self, listvariable=tk.StringVar(value=[]), height=12)
        self.gp_lb.pack(fill="x", padx=10)
        self.gp_lb.bind("<<ListboxSelect>>", self._on_gp)

        # セッション選択
        tk.Label(self, text="セッション", bg=COLOR_FRAME, fg=COLOR_TEXT)\
            .pack(anchor="w", padx=10, pady=5)
        self.ses_var = tk.StringVar()
        self.ses_cmb = ttk.Combobox(self, textvariable=self.ses_var,
                                    state="readonly",
                                    values=["FP1","FP2","FP3","Q","R"])
        self.ses_cmb.pack(fill="x", padx=10)
        self.ses_cmb.bind("<<ComboboxSelected>>", self._on_ses)

        # ドライバー選択
        tk.Label(self, text="ドライバー (最大4)", bg=COLOR_FRAME, fg=COLOR_TEXT)\
            .pack(anchor="w", padx=10, pady=5)
        self.drv_lb = tk.Listbox(self, selectmode="multiple", height=8)
        self.drv_lb.pack(fill="x", padx=10)

        # 各種ボタン
        self.btn_speed   = ttk.Button(self, text="速度テレメトリ表示", command=self._show_speed)
        self.btn_speed.pack(fill="x", padx=10, pady=(15,3))
        self.btn_scatter = ttk.Button(self, text="ラップタイム散布図", command=self._show_scatter)
        self.btn_scatter.pack(fill="x", padx=10, pady=3)
        self.btn_compare = ttk.Button(self, text="複数ドライバー比較", command=self._show_compare)
        self.btn_compare.pack(fill="x", padx=10, pady=3)

        # プログレスバー
        self.progress = ttk.Progressbar(self, mode="indeterminate")
        self.progress.pack(fill="x", padx=10, pady=10)

    # 年度
    def _on_year(self, e):
        sel = e.widget.curselection(); self.current_session=None
        if not sel: return
        year = int(e.widget.get(sel[0])); self.year_var.set(year)
        self._load_schedule(year)

    # GP
    def _on_gp(self, e):
        sel = e.widget.curselection(); self.current_session=None
        if not sel: return
        self.gp_var.set(e.widget.get(sel[0]))

    # セッション
    def _on_ses(self, _):
        if not (self.year_var.get() and self.gp_var.get()):
            messagebox.showinfo("選択不足", "年とグランプリを先に選択してください。")
            return
        self._load_session(self.year_var.get(),
                           self.gp_var.get(), self.ses_var.get())

    # 選択ドライバー一覧
    def _selected_driver(self):
        sel = self.drv_lb.curselection()
        return [self.drv_lb.get(i) for i in sel]

    # 速度テレメトリ
    def _show_speed(self):
        if not self.current_session:
            messagebox.showinfo("セッション未ロード", "先にセッションを読み込んでください")
            return
        drvs = self._selected_driver()
        if len(drvs)!=1:
            messagebox.showinfo("ドライバー選択", "1名だけ選択してください")
            return
        self.main_tab.show_driver_speed(self.current_session, drvs[0])

    # 散布図
    def _show_scatter(self):
        if not self.current_session:
            messagebox.showinfo("セッション未ロード", "先にセッションを読み込んでください")
            return
        drvs = self._selected_driver()
        if len(drvs)!=1:
            messagebox.showinfo("ドライバー選択", "1名だけ選択してください")
            return
        self.main_tab.show_lap_time_scatter(self.current_session, drvs[0])

    # 複数比較
    def _show_compare(self):
        if not self.current_session:
            messagebox.showinfo("セッション未ロード", "先にセッションを読み込んでください")
            return
        drvs = self._selected_driver()
        self.main_tab.show_multi_driver_compare(self.current_session, drvs)

    # スケジュール取得
    def _load_schedule(self, year:int):
        self.progress.start(8)
        fut = self.svc.get_event_schedule_async(year)
        def _done(f:Future):
            self.progress.stop()
            try:
                df = f.result()
            except Exception as e:
                logging.exception(e)
                messagebox.showerror("失敗", str(e))
                return
            self.gp_lb.delete(0, tk.END)
            for n in df["EventName"]:
                self.gp_lb.insert(tk.END, n)
        fut.add_done_callback(lambda f: self.after(0, _done, f))

    # セッション取得 & Map タブ更新
    def _load_session(self, year:int, gp:str, ses:str):
        self.progress.start(8)
        fut = self.svc.load_session_async(year, gp, ses)
        def _done(f:Future):
            self.progress.stop()
            try:
                sesobj = f.result()
            except Exception as e:
                logging.exception(e)
                messagebox.showerror("失敗", str(e))
                return
            # ドライバー一覧更新
            abbs = [sesobj.get_driver(d)["Abbreviation"] for d in sesobj.drivers]
            self.drv_lb.delete(0, tk.END)
            for a in abbs: self.drv_lb.insert(tk.END, a)
            self.current_session = sesobj
            # Map タブに描画
            self.main_tab.show_map(sesobj)
            messagebox.showinfo("ロード完了", f"{gp} – {ses} を読み込みました")
        fut.add_done_callback(lambda f: self.after(0, _done, f))

# ================================================================
class F1DashboardApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry(WINDOW_SIZE)
        self.configure(bg=COLOR_BG)
        self.minsize(1000, 600)

        self.service = FastF1Service()
        CacheManager.cleanup_cache()

        # 左: Sidebar、右: MainTab
        self.main_tab = MainTab(self)
        self.main_tab.pack(side="right", expand=True, fill="both")

        self.sidebar = Sidebar(self, svc=self.service, main_tab=self.main_tab, width=260)
        self.sidebar.pack(side="left", fill="y")

        self._setup_style()

    def _setup_style(self):
        style = ttk.Style(self)
        style.theme_use(style.theme_names()[0])
        style.configure("TFrame", background=COLOR_FRAME)
        style.configure("TLabel", background=COLOR_FRAME, foreground=COLOR_TEXT)
        style.configure("TNotebook", background=COLOR_FRAME, foreground=COLOR_TEXT)
        style.configure("MainNotebook.TNotebook", background=COLOR_FRAME, borderwidth=0)
        style.configure("TProgressbar", troughcolor=COLOR_FRAME, bordercolor=COLOR_BG,
                        background=COLOR_ACCENT)

# ================================================================
def main():
    logging.basicConfig(level=logging.INFO,
                        format="[%(asctime)s] %(levelname)s %(message)s")
    app = F1DashboardApp()
    app.mainloop()

if __name__ == "__main__":
    if getattr(sys, "_f1_dashboard_started", False):
        print("既にアプリケーションが起動しています。")
        sys.exit(0)
    sys._f1_dashboard_started = True  # type: ignore[attr-defined]
    main()