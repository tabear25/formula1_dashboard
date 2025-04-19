# =============================
# ライブラリのインストール
# =============================
import os
import sys
import json
import math
import shutil
import logging
import fastf1
from datetime import datetime, timedelta
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, Future
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from tkinter import font as tkfont
import fastf1
import pandas as pd
import numpy as np
import matplotlib
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
import plotly.io as pio

# =============================
# 変数・定数定義
# =============================
APP_TITLE: str = "F1 Information Dashboard"
WINDOW_SIZE: str = "1400x900"

# カラーパレット
COLOR_BG: str = "#161E2F"
COLOR_FRAME: str = "#242F48"
COLOR_ACCENT: str = "#B51A2B"
COLOR_HIGHLIGHT: str = "#FFA586"
COLOR_TEXT: str = "#FFFFFF"

# FastF1 キャッシュ関連
CACHE_DIR: Path = Path(os.getenv("TEMP", ".")) / "fastf1_cache"
CACHE_SIZE_LIMIT_GB: int = 2
CACHE_EXPIRE_DAYS: int = 30

# デフォルト年リスト (リリース年を想定)
YEAR_LIST = list(range(1950, datetime.now().year + 1))

# スレッドプール (GUI ブロック回避用)
EXECUTOR = ThreadPoolExecutor(max_workers=4, thread_name_prefix="FastF1Worker")

# =============================
# 補助クラス / 関数
# =============================
class CacheManager:
    """FastF1 キャッシュディレクトリの管理ユーティリティ"""

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
        limit_bytes = CACHE_SIZE_LIMIT_GB * (1024 ** 3)
        if total_bytes > limit_bytes:
            # キャッシュ全削除用 (実装簡易化) 
            shutil.rmtree(CACHE_DIR, ignore_errors=True)
            os.makedirs(CACHE_DIR, exist_ok=True)


class FastF1Service:
    """FastF1 API ラッパー (サービス層)"""

    def __init__(self):
        CacheManager.ensure_cache_dir()

    # 非同期メソッド
    def get_event_schedule_async(self, year: int) -> Future:
        return EXECUTOR.submit(fastf1.get_event_schedule, year)

    def load_session_async(self, year: int, gp: str, session_name: str) -> Future:
        def _inner():
            session = fastf1.get_session(year, gp, session_name)
            session.load()  # telemetry=True by default
            return session
        return EXECUTOR.submit(_inner)


# ============================================================================
# GUI コンポーネント
# ============================================================================
class MainTab(ttk.Notebook):
    """メイン可視化エリア (Notebook)"""

    def __init__(self, master: tk.Misc, **kwargs):
        super().__init__(master, **kwargs)
        self.configure(style="MainNotebook.TNotebook")

        # Overview タブ ─ placeholder
        self.overview_frame = tk.Frame(self, bg=COLOR_FRAME)
        tk.Label(self.overview_frame, text="データを読み込んでください",
                 fg=COLOR_TEXT, bg=COLOR_FRAME).pack(expand=True)
        self.add(self.overview_frame, text="🏁 Overview")

        # Matplotlib Figure placeholder（動的更新用）
        self._fig = None
        self._canvas = None

    # ------------------------------------------------------------------
    # 可視化メソッド
    # ------------------------------------------------------------------
    def show_circuit_map(self, session):
        """サーキットマップを Overview タブに表示"""
        # 既存 Canvas を破棄
        if self._canvas:
            self._canvas.get_tk_widget().destroy()
            self._canvas = None
            self._fig = None

        # --- テレメトリからトラック座標を取得
        lap = session.laps.pick_fastest()
        pos = lap.get_pos_data()
        circuit_info = session.get_circuit_info()

        track = pos.loc[:, ("X", "Y")].to_numpy()
        rot = circuit_info.rotation / 180 * np.pi
        rot_mat = np.array([[np.cos(rot), np.sin(rot)], [-np.sin(rot), np.cos(rot)]])
        track_rot = (track @ rot_mat.T)

        # --- Figure 作成
        self._fig = plt.Figure(figsize=(6, 4), dpi=100, facecolor=COLOR_FRAME)
        ax = self._fig.add_subplot(111)
        ax.plot(track_rot[:, 0], track_rot[:, 1], color=COLOR_HIGHLIGHT, linewidth=2)
        ax.set_title(f"{session.event['Location']} {session.event.year}", color=COLOR_TEXT)
        ax.axis("equal")
        ax.axis("off")
        self._fig.tight_layout()
        # Dark-style 微調整
        ax.set_facecolor(COLOR_FRAME)
        self._fig.patch.set_facecolor(COLOR_FRAME)
        for spine in ax.spines.values():
            spine.set_visible(False)

        # --- Tkinter へ埋め込み
        self._canvas = FigureCanvasTkAgg(self._fig, master=self.overview_frame)
        self._canvas.draw()
        self._canvas.get_tk_widget().pack(expand=True, fill="both")


class Sidebar(tk.Frame):
    """年・GP・セッション・ドライバー選択用サイドバー"""

    def __init__(self, master: tk.Misc, svc: FastF1Service, main_tab: MainTab, **kwargs):
        super().__init__(master, bg=COLOR_FRAME, **kwargs)
        self.svc = svc
        self.main_tab = main_tab

        default_font = tkfont.nametofont("TkDefaultFont")
        default_font.configure(size=10, weight="bold")

        # —— 年度選択 ————————————————————————————————————————————
        tk.Label(self, text="開催年", bg=COLOR_FRAME, fg=COLOR_TEXT).pack(anchor="w", padx=10, pady=5)
        self.year_var = tk.IntVar(value=datetime.now().year)
        self.year_listbox = tk.Listbox(self, listvariable=tk.StringVar(value=YEAR_LIST), height=10)
        self.year_listbox.pack(fill="x", padx=10)
        self.year_listbox.bind("<<ListboxSelect>>", self._on_year_select)

        # —— GP 選択 —————————————————————————————————————————————
        tk.Label(self, text="グランプリ", bg=COLOR_FRAME, fg=COLOR_TEXT).pack(anchor="w", padx=10, pady=5)
        self.gp_var = tk.StringVar()
        self.gp_listbox = tk.Listbox(self, listvariable=tk.StringVar(value=[]), height=12)
        self.gp_listbox.pack(fill="x", padx=10)
        self.gp_listbox.bind("<<ListboxSelect>>", self._on_gp_select)

        # —— セッション選択 ——————————————————————————————————————
        tk.Label(self, text="セッション", bg=COLOR_FRAME, fg=COLOR_TEXT).pack(anchor="w", padx=10, pady=5)
        self.session_var = tk.StringVar()
        self.session_cmb = ttk.Combobox(self, textvariable=self.session_var, state="readonly",
                                        values=["FP1", "FP2", "FP3", "Q", "R"])
        self.session_cmb.pack(fill="x", padx=10)
        self.session_cmb.bind("<<ComboboxSelected>>", self._on_session_select)

        # —— ドライバー選択 ——————————————————————————————————————
        tk.Label(self, text="ドライバー (最大4)", bg=COLOR_FRAME, fg=COLOR_TEXT).pack(anchor="w", padx=10, pady=5)
        self.driver_listbox = tk.Listbox(self, selectmode="multiple", height=8)
        self.driver_listbox.pack(fill="x", padx=10)

        # —— プログレスバー —————————————————————————————————————
        self.progress = ttk.Progressbar(self, mode="indeterminate")
        self.progress.pack(fill="x", padx=10, pady=10)

    # ------------------------------------------------------------------
    # イベントハンドラ
    # ------------------------------------------------------------------
    def _on_year_select(self, event):
        sel = event.widget.curselection()
        if not sel:
            return
        year = int(event.widget.get(sel[0]))
        self.year_var.set(year)
        self._load_schedule(year)

    def _on_gp_select(self, event):
        sel = event.widget.curselection()
        if not sel:
            return
        self.gp_var.set(event.widget.get(sel[0]))

    def _on_session_select(self, _):
        if not self.year_var.get() or not self.gp_var.get():
            messagebox.showinfo("選択不足", "年とグランプリを先に選択してください。")
            return
        self._load_session(self.year_var.get(), self.gp_var.get(), self.session_var.get())

    # ------------------------------------------------------------------
    # データロード処理
    # ------------------------------------------------------------------
    def _load_schedule(self, year: int):
        self.progress.start(8)
        fut = self.svc.get_event_schedule_async(year)

        def _done(f: Future):
            self.progress.stop()
            try:
                df: pd.DataFrame = f.result()
            except Exception as e:
                logging.exception(e)
                messagebox.showerror("スケジュール取得失敗", str(e))
                return
            self.gp_listbox.delete(0, tk.END)
            for name in df["EventName"].tolist():
                self.gp_listbox.insert(tk.END, name)
        fut.add_done_callback(lambda f: self.after(0, _done, f))

    def _load_session(self, year: int, gp: str, session_name: str):
        self.progress.start(8)
        fut = self.svc.load_session_async(year, gp, session_name)

        def _done(f: Future):
            self.progress.stop()
            try:
                session = f.result()
            except Exception as e:
                logging.exception(e)
                messagebox.showerror("セッション読込失敗", str(e))
                return
            # ドライバー一覧更新
            drivers = session.drivers
            abbs = [session.get_driver(d)["Abbreviation"] for d in drivers]
            self.driver_listbox.delete(0, tk.END)
            for abb in abbs:
                self.driver_listbox.insert(tk.END, abb)
            # Overview タブを更新
            self.main_tab.show_circuit_map(session)
            messagebox.showinfo("ロード完了", f"{gp} – {session_name} を読み込みました")
        fut.add_done_callback(lambda f: self.after(0, _done, f))

# ============================================================================
# メインアプリケーション
# ============================================================================
class F1DashboardApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry(WINDOW_SIZE)
        self.configure(bg=COLOR_BG)
        self.minsize(1000, 600)

        self.service = FastF1Service()
        CacheManager.cleanup_cache()

        # サイドバー & メインタブ
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
                        background=COLOR_ACCENT, lightcolor=COLOR_ACCENT, darkcolor=COLOR_ACCENT)

# ============================================================================
# エントリポイント
# ============================================================================

def main() -> None:
    logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s %(message)s")
    app = F1DashboardApp()
    app.mainloop()

if __name__ == "__main__":
    if getattr(sys, "_f1_dashboard_started", False):
        print("既にアプリケーションが起動しています。多重起動はできません。")
        sys.exit(0)
    sys._f1_dashboard_started = True  # type: ignore[attr-defined]
    main()