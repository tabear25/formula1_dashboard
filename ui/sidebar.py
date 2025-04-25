import tkinter as tk
from tkinter import ttk, messagebox
from tkinter import font as tkfont
from config import COLOR_FRAME, COLOR_TEXT, YEAR_LIST
from service import FastF1Service
from tqdm import tqdm
import threading

class Sidebar(tk.Frame):
    def __init__(self, master, svc: FastF1Service, main_tab, **kw):
        super().__init__(master, bg=COLOR_FRAME, **kw)
        self.svc = svc
        self.main_tab = main_tab
        self.current_session = None

        font = tkfont.nametofont("TkDefaultFont")
        font.configure(size=10, weight="bold")

        # 年度選択
        tk.Label(self, text="開催年", bg=COLOR_FRAME, fg=COLOR_TEXT) \
          .pack(anchor="w", padx=10, pady=(10,0))
        year_frame = tk.Frame(self, bg=COLOR_FRAME)
        year_frame.pack(fill="x", padx=10)
        self.year_var = tk.IntVar(value=YEAR_LIST[-1])
        self.year_lb = tk.Listbox(year_frame,
                                   listvariable=tk.StringVar(value=YEAR_LIST),
                                   height=10, yscrollcommand=lambda f, l: self.year_scroll.set(f, l))
        self.year_lb.pack(side="left", fill="both", expand=True)
        self.year_lb.bind("<<ListboxSelect>>", self._on_year)
        self.year_scroll = tk.Scrollbar(year_frame, orient="vertical",
                                        command=self.year_lb.yview)
        self.year_scroll.pack(side="right", fill="y")

        # GP選択
        tk.Label(self, text="グランプリ", bg=COLOR_FRAME, fg=COLOR_TEXT) \
          .pack(anchor="w", padx=10, pady=(10,0))
        gp_frame = tk.Frame(self, bg=COLOR_FRAME)
        gp_frame.pack(fill="x", padx=10)
        self.gp_var = tk.StringVar()
        self.gp_lb = tk.Listbox(gp_frame, listvariable=tk.StringVar(value=[]),
                                height=12, yscrollcommand=lambda f, l: self.gp_scroll.set(f, l))
        self.gp_lb.pack(side="left", fill="both", expand=True)
        self.gp_lb.bind("<<ListboxSelect>>", self._on_gp)
        self.gp_scroll = tk.Scrollbar(gp_frame, orient="vertical",
                                      command=self.gp_lb.yview)
        self.gp_scroll.pack(side="right", fill="y")

        # セッション選択
        tk.Label(self, text="セッション", bg=COLOR_FRAME, fg=COLOR_TEXT) \
          .pack(anchor="w", padx=10, pady=(10,0))
        self.ses_var = tk.StringVar()
        self.ses_cmb = ttk.Combobox(self,
                                    textvariable=self.ses_var,
                                    state="readonly",
                                    values=["FP1","FP2","FP3","Q","R"])
        self.ses_cmb.pack(fill="x", padx=10)
        self.ses_cmb.bind("<<ComboboxSelected>>", self._on_ses)

        # ドライバー選択
        tk.Label(self, text="ドライバー (最大4)", bg=COLOR_FRAME, fg=COLOR_TEXT) \
          .pack(anchor="w", padx=10, pady=(10,0))
        drv_frame = tk.Frame(self, bg=COLOR_FRAME)
        drv_frame.pack(fill="x", padx=10)
        self.drv_lb = tk.Listbox(drv_frame, selectmode="multiple", height=8,
                                 yscrollcommand=lambda f, l: self.drv_scroll.set(f, l))
        self.drv_lb.pack(side="left", fill="both", expand=True)
        self.drv_scroll = tk.Scrollbar(drv_frame, orient="vertical",
                                       command=self.drv_lb.yview)
        self.drv_scroll.pack(side="right", fill="y")

        # ボタン群
        btns = [
            ("速度テレメトリ表示", self._show_speed),
            ("ラップタイム散布図", self._show_scatter),
            ("複数ドライバー比較", self._show_compare),
            ("速度テレメトリ比較", self._show_speed_compare),
            ("散布図比較", self._show_scatter_compare),
            ("テレメトリ表示", self._show_telemetry),
        ]
        for txt, cmd in btns:
            ttk.Button(self, text=txt, command=cmd) \
               .pack(fill="x", padx=10, pady=3)

        # プログレスバー
        self.progress_var = tk.DoubleVar()
        self.progress = ttk.Progressbar(self,
                                        variable=self.progress_var,
                                        maximum=100)
        self.progress.pack(fill="x", padx=10, pady=10)

    def _on_year(self, e):
        sel = e.widget.curselection()
        if not sel: return
        year = int(e.widget.get(sel[0]))
        self.year_var.set(year)
        threading.Thread(
            target=self._load_schedule,
            args=(year,),
            daemon=True
        ).start()

    def _load_schedule(self, year):
        # 進捗シミュレーション
        for i in tqdm(range(80),
                      desc="スケジュール読み込み",
                      leave=False):
            self.progress_var.set(i + 1)
            self.update_idletasks()

        fut = self.svc.get_event_schedule_async(year)
        def _done(f):
            try:
                df = f.result()
                self.gp_lb.delete(0, tk.END)
                for gp in df['EventName']:
                    self.gp_lb.insert(tk.END, gp)
                self.progress_var.set(100)
            except Exception as e:
                messagebox.showerror("スケジュール取得エラー", str(e))
        fut.add_done_callback(lambda f: self.after(0, _done, f))

    def _on_gp(self, e):
        sel = e.widget.curselection()
        if not sel: return
        self.gp_var.set(e.widget.get(sel[0]))

    def _on_ses(self, _):
        year = self.year_var.get()
        gp   = self.gp_var.get()
        ses  = self.ses_var.get()
        if not (year and gp and ses):
            messagebox.showinfo("選択不足", "年、GP、セッションを選択してください")
            return
        threading.Thread(
            target=self._load_session,
            args=(year, gp, ses),
            daemon=True
        ).start()

    def _load_session(self, year, gp, ses):
        for i in tqdm(range(80),
                      desc="セッション読み込み",
                      leave=False):
            self.progress_var.set(i + 1)
            self.update_idletasks()

        fut = self.svc.load_session_async(year, gp, ses)
        def _done(f):
            try:
                sess = f.result()
                # ドライバー一覧更新
                self.drv_lb.delete(0, tk.END)
                for d in sess.drivers:
                    self.drv_lb.insert(tk.END,
                                       sess.get_driver(d)
                                           ['Abbreviation'])
                self.current_session = sess
                # Mapタブ更新
                self.main_tab.show_map(sess)
                messagebox.showinfo(
                    "ロード完了",
                    f"{gp} – {ses} を読み込みました"
                )
                self.progress_var.set(100)
            except Exception as e:
                messagebox.showerror(
                    "セッション取得エラー",
                    str(e)
                )
        fut.add_done_callback(lambda f: self.after(0, _done, f))

    def _selected_drivers(self):
        return [self.drv_lb.get(i)
                for i in self.drv_lb.curselection()]

    def _show_speed(self):
        if not self.current_session:
            messagebox.showinfo(
                "セッション未ロード",
                "先にセッションを読み込んでください"
            )
            return
        drvs = self._selected_drivers()
        if len(drvs) != 1:
            messagebox.showinfo(
                "ドライバー選択",
                "1名選択してください"
            )
            return
        self.main_tab.show_multi_driver_speed(
            self.current_session, drvs
        )

    def _show_scatter(self):
        if not self.current_session:
            messagebox.showinfo(
                "セッション未ロード",
                "先にセッションを読み込んでください"
            )
            return
        drvs = self._selected_drivers()
        if len(drvs) != 1:
            messagebox.showinfo(
                "ドライバー選択",
                "1名選択してください"
            )
            return
        self.main_tab.show_multi_lap_scatter(
            self.current_session, drvs
        )

    def _show_compare(self):
        if not self.current_session:
            messagebox.showinfo(
                "セッション未ロード",
                "先にセッションを読み込んでください"
            )
            return
        drvs = self._selected_drivers()
        self.main_tab.show_multi_driver_compare(
            self.current_session, drvs
        )

    def _show_speed_compare(self):
        if not self.current_session:
            messagebox.showinfo(
                "セッション未ロード",
                "先にセッションを読み込んでください"
            )
            return
        drvs = self._selected_drivers()
        self.main_tab.show_multi_driver_speed(
            self.current_session, drvs
        )

    def _show_scatter_compare(self):
        if not self.current_session:
            messagebox.showinfo(
                "セッション未ロード",
                "先にセッションを読み込んでください"
            )
            return
        drvs = self._selected_drivers()
        self.main_tab.show_multi_lap_scatter(
            self.current_session, drvs
        )

    def _show_telemetry(self):
        if not self.current_session:
            messagebox.showinfo(
                "セッション未ロード",
                "先にセッションを読み込んでください"
            )
            return
        drvs = self._selected_drivers()
        if len(drvs) != 1:
            messagebox.showinfo(
                "ドライバー選択",
                "1名選択してください"
            )
            return
        self.main_tab.show_telemetry(
            self.current_session, drvs
        )