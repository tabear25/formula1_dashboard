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
# --------------------------------------------------------
# キャッシュ管理 & サービス層
# --------------------------------------------------------
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

# --------------------------------------------------------
# メイン可視化エリア (Notebook)
# --------------------------------------------------------
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

        # Compare: LapTime Violin
        self.compare_frame = tk.Frame(self, bg=COLOR_FRAME)
        tk.Label(self.compare_frame, text="👥 ドライバー比較",
                 fg=COLOR_TEXT, bg=COLOR_FRAME).pack()
        self.add(self.compare_frame, text="👥 Compare")

        # Speed Compare タブ
        self.speed_frame = tk.Frame(self, bg=COLOR_FRAME)
        tk.Label(self.speed_frame, text="🚥 速度テレメトリ比較",
                 fg=COLOR_TEXT, bg=COLOR_FRAME).pack()
        self.add(self.speed_frame, text="🚥 Speed Compare")

        # Scatter Compare タブ
        self.scatter_frame = tk.Frame(self, bg=COLOR_FRAME)
        tk.Label(self.scatter_frame, text="📊 ラップタイム散布図比較",
                 fg=COLOR_TEXT, bg=COLOR_FRAME).pack()
        self.add(self.scatter_frame, text="📊 Scatter Compare")

        # Canvas／Figure 保存用
        self._map_canvas     = None
        self._compare_canvas = None
        self._speed_canvas   = None
        self._scatter_canvas = None

    # --------------------------------------------------------
    # Map 描画 + コーナー番号注記
    # --------------------------------------------------------
    def show_map(self, session):
        if self._map_canvas:
            self._map_canvas.get_tk_widget().destroy()

        lap = session.laps.pick_fastest()
        pos = lap.get_pos_data()
        cinfo = session.get_circuit_info()
        coords = pos.loc[:, ("X", "Y")].to_numpy()
        theta = cinfo.rotation / 180 * math.pi  # 回転角度 (ラジアン)

        # 標準の回転行列 R_std = [[cosθ, –sinθ], [sinθ, cosθ]]
        R_std = np.array([[math.cos(theta), -math.sin(theta)],
                        [math.sin(theta), math.cos(theta)]])
        track_rot = coords @ R_std  # 各点に標準回転行列を適用

        # Figure の準備
        fig = plt.Figure(figsize=(6,4), dpi=100, facecolor=COLOR_FRAME)
        ax = fig.add_subplot(111)
        ax.plot(track_rot[:, 0], track_rot[:, 1], color=COLOR_HIGHLIGHT, linewidth=2)

        # コーナー注記: x軸方向に500のみオフセット（y成分は0）
        offset0 = np.array([500, 0])

        # _rot関数：標準の回転 R_std を用いる
        def _rot(pt, ang):
            R = np.array([[math.cos(ang), -math.sin(ang)],
                        [math.sin(ang), math.cos(ang)]])
            return pt @ R

        for _, corner in cinfo.corners.iterrows():
            txt = f"{corner['Number']}{corner['Letter']}"
            off_ang = corner['Angle'] / 180 * math.pi
            off_vec = _rot(offset0, off_ang)
            pos_orig = np.array([corner['X'], corner['Y']])
            text_pt = _rot(pos_orig + off_vec, theta)  # コーナー座標＋オフセットを回転
            track_pt = _rot(pos_orig, theta)             # コーナー座標を回転
            ax.scatter(text_pt[0], text_pt[1], color='grey', s=100)
            ax.plot([track_pt[0], text_pt[0]], [track_pt[1], text_pt[1]], color='grey')
            ax.text(text_pt[0], text_pt[1], txt, va='center_baseline', ha='center', color='white', fontsize=6)

        ax.set_title(f"{session.event['Location']} {session.event.year}", color=COLOR_TEXT)
        ax.axis("equal")
        ax.axis("off")
        fig.tight_layout()

        self._map_canvas = FigureCanvasTkAgg(fig, master=self.map_frame)
        self._map_canvas.draw()
        self._map_canvas.get_tk_widget().pack(expand=True, fill="both")

    # --------------------------------------------------------
    # 複数ドライバー Violin 比較
    # --------------------------------------------------------
    def show_multi_driver_compare(self, session, drivers:list[str]):
        if self._compare_canvas:
            self._compare_canvas.get_tk_widget().destroy()

        laps_df = session.laps.pick_quicklaps().reset_index()
        df      = laps_df[laps_df['Driver'].isin(drivers)].copy()
        df['LapTime_s'] = df['LapTime'].dt.total_seconds()

        fig = plt.Figure(figsize=(6,4), dpi=100, facecolor=COLOR_FRAME)
        ax  = fig.add_subplot(111)
        sns.violinplot(data=df, x='Driver', y='LapTime_s',
                       inner='quartile', cut=0, ax=ax,
                       palette=[COLOR_ACCENT]*len(drivers))
        meds = df.groupby('Driver')['LapTime_s'].median()
        ax.plot(range(len(drivers)), meds.values,
                marker='o', color=COLOR_HIGHLIGHT, linestyle='--')

        ax.invert_yaxis()
        ax.set_xlabel("Driver"); ax.set_ylabel("LapTime (s)")
        ax.set_title(f"LapTime Comparison – {session.event['EventName']} {session.event.year}",
                     color=COLOR_TEXT, fontsize=9)
        ax.grid(color="#333333")
        ax.set_facecolor(COLOR_FRAME); fig.patch.set_facecolor(COLOR_FRAME)
        fig.tight_layout()

        self._compare_canvas = FigureCanvasTkAgg(fig, master=self.compare_frame)
        self._compare_canvas.draw()
        self._compare_canvas.get_tk_widget().pack(expand=True, fill="both")

    # --------------------------------------------------------
    # 複数ドライバー 速度テレメトリ比較
    # --------------------------------------------------------
    def show_multi_driver_speed(self, session, drivers:list[str]):
        if self._speed_canvas:
            self._speed_canvas.get_tk_widget().destroy()

        fastf1.plotting.setup_mpl(misc_mpl_mods=False, color_scheme='fastf1')

        fig = plt.Figure(figsize=(6,4), dpi=100, facecolor=COLOR_FRAME)
        ax  = fig.add_subplot(111)
        for drv in drivers:
            lap = session.laps.pick_drivers(drv).pick_fastest()
            tel = lap.get_car_data().add_distance()
            style = fastf1.plotting.get_driver_style(identifier=drv,
                                                     style=['color','linestyle'],
                                                     session=session)
            ax.plot(tel['Distance'], tel['Speed'], label=drv, **style)

        ax.set_xlabel("Distance (m)"); ax.set_ylabel("Speed (km/h)")
        ax.set_title(f"Speed Comparison – {session.event['EventName']} {session.event.year}",
                     color=COLOR_TEXT, fontsize=9)
        ax.legend(); ax.grid(color="#333333")
        ax.set_facecolor(COLOR_FRAME); fig.patch.set_facecolor(COLOR_FRAME)
        fig.tight_layout()

        self._speed_canvas = FigureCanvasTkAgg(fig, master=self.speed_frame)
        self._speed_canvas.draw()
        self._speed_canvas.get_tk_widget().pack(expand=True, fill="both")

    # --------------------------------------------------------
    # マルチ散布図 (2×2)
    # --------------------------------------------------------
    def show_multi_lap_scatter(self, session, drivers:list[str]):
        if self._scatter_canvas:
            self._scatter_canvas.get_tk_widget().destroy()

        laps_df = session.laps.pick_quicklaps().reset_index()
        fig, axes = plt.subplots(2,2, figsize=(8,6), facecolor=COLOR_FRAME)
        plt.subplots_adjust(hspace=0.4, wspace=0.3)
        for i, drv in enumerate(drivers[:4]):
            ax = axes.flatten()[i]
            df = laps_df[laps_df['Driver']==drv]
            sns.scatterplot(data=df, x="LapNumber", y="LapTime",
                            hue="Compound",
                            palette=fastf1.plotting.get_compound_mapping(session=session),
                            s=40, linewidth=0, ax=ax, legend=False)
            ax.invert_yaxis()
            ax.set_title(drv, color=COLOR_TEXT, fontsize=8)
            ax.set_facecolor(COLOR_FRAME)
            ax.set_xlabel("Lap #"); ax.set_ylabel("Lap Time")
            for sp in ax.spines.values(): sp.set_visible(False)

        fig.patch.set_facecolor(COLOR_FRAME)
        # 空プロットは消す
        for j in range(len(drivers),4):
            axes.flatten()[j].axis('off')

        self._scatter_canvas = FigureCanvasTkAgg(fig, master=self.scatter_frame)
        self._scatter_canvas.draw()
        self._scatter_canvas.get_tk_widget().pack(expand=True, fill="both")

# --------------------------------------------------------
# サイドバー
# --------------------------------------------------------
class Sidebar(tk.Frame):
    def __init__(self, master, svc:FastF1Service, main_tab:MainTab, **kw):
        super().__init__(master, bg=COLOR_FRAME, **kw)
        self.svc             = svc
        self.main_tab        = main_tab
        self.current_session = None

        font = tkfont.nametofont("TkDefaultFont")
        font.configure(size=10, weight="bold")

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

        # ボタン
        for txt, cmd in [
            ("速度テレメトリ表示", self._show_speed),
            ("ラップタイム散布図", self._show_scatter),
            ("複数ドライバー比較", self._show_compare),
            ("速度テレメトリ比較", self._show_speed_compare),
            ("散布図比較", self._show_scatter_compare),
        ]:
            btn = ttk.Button(self, text=txt, command=cmd)
            btn.pack(fill="x", padx=10, pady=3)

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

    def _on_ses(self, _):
        # 年度選択チェック
        year = self.year_var.get()
        if not year:
            messagebox.showinfo("選択が不足しています", "先に開催年を選択してください")
            return
        
        # GP選択チェック
        gp = self.gp_var.get()
        if not gp:
            messagebox.showinfo("選択が不足しています", "先にグランプリを選択してください")
            return
        
        # セッション選択チェック
        ses = self.ses_var.get()
        if not ses:
            messagebox.showinfo("選択が不足しています", "先にセッションを選択してください")
            return
        
        self._load_session(year, gp, ses)

    # 選択ドライバー一覧
    def _selected_drivers(self):
        sel = self.drv_lb.curselection()
        return [self.drv_lb.get(i) for i in sel]
    
    # 単一選択ドライバー
    def _selected_driver(self):
        sel = self.drv_lb.curselection()
        return [self.drv_lb.get(i) for i in sel]

    # 単一表示
    def _show_speed(self):
        if not self.current_session:
            messagebox.showinfo("セッション未ロード", "先にセッションを読み込んでください")
            return
        drvs = self._selected_drivers()
        if len(drvs) != 1:
            messagebox.showinfo("ドライバー選択", "1名だけ選択してください")
            return
        self.main_tab.show_multi_driver_speed(self.current_session, drvs)

    # 散布図単一表示
    def _show_scatter(self):
        if not self.current_session:
            messagebox.showinfo("セッション未ロード", "先にセッションを読み込んでください")
            return
        drvs = self._selected_drivers()
        if len(drvs) != 1:
            messagebox.showinfo("ドライバー選択", "1名だけ選択してください")
            return
        self.main_tab.show_multi_lap_scatter(self.current_session, drvs)

    # 複数Violin
    def _show_compare(self):
        drvs = self._selected_drivers()
        if not self.current_session:
            messagebox.showinfo("選択エラー","セッション読み込み後に実行してください")
            return
        self.main_tab.show_multi_driver_compare(self.current_session, drvs)

    # 複数Speed
    def _show_speed_compare(self):
        drvs = self._selected_drivers()
        if not self.current_session:
            messagebox.showinfo("選択エラー","セッション読み込み後に実行してください")
            return
        self.main_tab.show_multi_driver_speed(self.current_session, drvs)

    # 複数Scatter
    def _show_scatter_compare(self):
        drvs = self._selected_drivers()
        if not self.current_session:
            messagebox.showinfo("選択エラー","セッション読み込み後に実行してください")
            return
        self.main_tab.show_multi_lap_scatter(self.current_session, drvs)

    def _load_schedule(self, year:int):
        self.progress.start(8)
        fut = self.svc.get_event_schedule_async(year)
        def _done(f):
            self.progress.stop()
            try: df = f.result()
            except Exception as e:
                messagebox.showerror("失敗", str(e)); return
            self.gp_lb.delete(0,tk.END)
            for gp in df['EventName']: self.gp_lb.insert(tk.END, gp)
        fut.add_done_callback(lambda f: self.after(0,_done,f))

    def _load_session(self, year:int, gp:str, ses:str):
        self.progress.start(8)
        fut = self.svc.load_session_async(year,gp,ses)
        def _done(f):
            self.progress.stop()
            try: sess = f.result()
            except Exception as e:
                messagebox.showerror("失敗", str(e)); return
            # ドライバー一覧
            self.drv_lb.delete(0,tk.END)
            for d in sess.drivers:
                self.drv_lb.insert(tk.END, sess.get_driver(d)['Abbreviation'])
            self.current_session = sess
            # Map タブ更新
            self.main_tab.show_map(sess)
            messagebox.showinfo("ロード完了", f"{gp} – {ses} を読み込みました")
        fut.add_done_callback(lambda f: self.after(0,_done,f))

# --------------------------------------------------------
# メインアプリ
# --------------------------------------------------------
class F1DashboardApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry(WINDOW_SIZE)
        self.configure(bg=COLOR_BG); self.minsize(1000,600)

        self.service = FastF1Service()
        CacheManager.cleanup_cache()

        self.main_tab = MainTab(self)
        self.main_tab.pack(side="right", expand=True, fill="both")

        self.sidebar = Sidebar(self, svc=self.service, main_tab=self.main_tab, width=260)
        self.sidebar.pack(side="left", fill="y")

        style = ttk.Style(self)
        style.theme_use(style.theme_names()[0])
        style.configure("TFrame", background=COLOR_FRAME)
        style.configure("TLabel", background=COLOR_FRAME, foreground=COLOR_TEXT)
        style.configure("TNotebook", background=COLOR_FRAME, foreground=COLOR_TEXT)
        style.configure("MainNotebook.TNotebook", background=COLOR_FRAME, borderwidth=0)
        style.configure("TProgressbar", troughcolor=COLOR_FRAME, bordercolor=COLOR_BG,
                        background=COLOR_ACCENT)

def main():
    logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s %(message)s")
    app = F1DashboardApp()
    app.mainloop()

if __name__=="__main__":
    if getattr(sys,"_f1_dashboard_started",False):
        sys.exit(0)
    sys._f1_dashboard_started = True
    main()