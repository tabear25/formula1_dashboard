import tkinter as tk
from tkinter import ttk, messagebox
from config import COLOR_FRAME, COLOR_TEXT, YEAR_LIST
from service import FastF1Service
import threading
import datetime

class Sidebar(tk.Frame):
    def __init__(self, master, svc: FastF1Service, main_tab, **kw):
        kw.pop('width', None)
        super().__init__(master, bg=COLOR_FRAME, **kw)

        # ─── scrollable canvas ───
        self.canvas = tk.Canvas(self, bg=COLOR_FRAME, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.internal_frame = tk.Frame(self.canvas, bg=COLOR_FRAME)
        self.canvas_window = self.canvas.create_window(
            (0, 0), window=self.internal_frame, anchor="nw"
        )

        # resize handling
        self.internal_frame.bind("<Configure>", self._on_frame_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind("<Button-4>", lambda e: self.canvas.yview_scroll(-1, "units"))
        self.canvas.bind("<Button-5>", lambda e: self.canvas.yview_scroll(1, "units"))

        self.svc = svc
        self.main_tab = main_tab
        self.current_session = None

        # ─── Widgets ───
        tk.Label(self.internal_frame, text="開催年", bg=COLOR_FRAME, fg=COLOR_TEXT)\
            .pack(anchor="w", padx=10, pady=(10,0))
        self.year_lb = tk.Listbox(self.internal_frame, height=6, exportselection=False)
        for y in YEAR_LIST:
            self.year_lb.insert(tk.END, y)
        if YEAR_LIST:
            self.year_lb.selection_set(tk.END)
            self.year_lb.see(tk.END)
        self.year_lb.pack(fill="x", expand=True, padx=10, pady=2)
        self.year_lb.bind("<<ListboxSelect>>", self._on_year_select)

        tk.Label(self.internal_frame, text="グランプリ", bg=COLOR_FRAME, fg=COLOR_TEXT)\
            .pack(anchor="w", padx=10, pady=(10,0))
        self.gp_lb = tk.Listbox(self.internal_frame, height=8, exportselection=False)
        self.gp_lb.pack(fill="x", expand=True, padx=10, pady=2)
        self.gp_lb.bind("<<ListboxSelect>>", self._on_gp_select)

        tk.Label(self.internal_frame, text="セッション", bg=COLOR_FRAME, fg=COLOR_TEXT)\
            .pack(anchor="w", padx=10, pady=(10,0))
        self.ses_cmb = ttk.Combobox(
            self.internal_frame, state="readonly",
            values=["FP1","FP2","FP3","Q","R"],
            textvariable=tk.StringVar()
        )
        self.ses_cmb.pack(fill="x", expand=True, padx=10, pady=2)
        self.ses_cmb.bind("<<ComboboxSelected>>", self._on_session_select)

        tk.Label(self.internal_frame, text="ドライバー (複数選択可)", bg=COLOR_FRAME, fg=COLOR_TEXT)\
            .pack(anchor="w", padx=10, pady=(10,0))
        self.drv_lb = tk.Listbox(self.internal_frame, selectmode="multiple", height=6, exportselection=False)
        self.drv_lb.pack(fill="x", expand=True, padx=10, pady=2)

        for txt, cmd in [
            ("テレメトリ (単一)", self._cmd_show_single_telemetry),
            ("ラップ散布図 (単一)", self._cmd_show_single_scatter),
            ("ラップタイム比較 (複数)", self._cmd_show_laptime_comparison),
            ("速度比較 (複数)", self._cmd_show_speed_comparison),
            ("散布図比較 (複数)", self._cmd_show_scatter_comparison),
        ]:
            ttk.Button(self.internal_frame, text=txt, command=cmd)\
               .pack(fill="x", expand=True, padx=10, pady=2)

        self.progress_var = tk.DoubleVar(value=0)
        self.progress = ttk.Progressbar(
            self.internal_frame, mode='determinate',
            variable=self.progress_var, maximum=100
        )
        self.progress.pack(fill="x", expand=True, padx=10, pady=10)

        # initial layout
        self.internal_frame.update_idletasks()
        self._on_frame_configure()

    def _on_frame_configure(self, event=None):
        # canvas のスクロール領域を更新
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        # canvas の幅に合わせて内部ウィジェットの幅を調整
        new_width = event.width
        self.canvas.itemconfig(self.canvas_window, width=new_width)

    def _on_mousewheel(self, event):
        if hasattr(event, 'delta') and event.delta:
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            self.canvas.bind("<Button-4>", lambda e: self.canvas.yview_scroll(-1, "units"))
        self.canvas.bind("<Button-5>", lambda e: self.canvas.yview_scroll(1, "units"))


    def _on_frame_configure(self, event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        if self.canvas.winfo_width() > 1:
            self.canvas.itemconfig(self.canvas_window, width=self.canvas.winfo_width())

    def _on_mousewheel(self, event):
        if hasattr(event, 'delta') and event.delta:
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _on_year_select(self, event):
        sel = self.year_lb.curselection()
        if not sel:
            return
        year = int(self.year_lb.get(sel[0]))
        if self.year_var.get() == year and self.gp_lb.size() > 0:
            return
        self.year_var.set(year)
        self.gp_lb.delete(0, tk.END)
        self.drv_lb.delete(0, tk.END)
        self.current_session = None
        if self.main_tab:
            self.main_tab.show_overview()

        self._start_loading_progress()
        threading.Thread(target=self._load_schedule_thread, args=(year,), daemon=True).start()

    def _load_schedule_thread(self, year):
        fut = self.svc.get_event_schedule_async(year)
        def _done(fut):
            try:
                df = fut.result()
                self.gp_lb.delete(0, tk.END)
                if not df.empty:
                    for name in df['EventName']:
                        self.gp_lb.insert(tk.END, name)
                self._stop_loading_progress(True)
            except Exception as e:
                self._stop_loading_progress(False)
                messagebox.showerror("スケジュール取得エラー", str(e))
        fut.add_done_callback(lambda f: self.after(0, _done, f))

    def _on_gp_select(self, event):
        sel = self.gp_lb.curselection()
        if sel:
            self.gp_var.set(self.gp_lb.get(sel[0]))

    def _on_session_select(self, event=None):
        year = self.year_var.get()
        gp = self.gp_var.get()
        ses = self.ses_var.get()
        if not (year and gp and ses):
            messagebox.showinfo("選択不足", "年、グランプリ、セッションを全て選択してください。")
            return

        self._start_loading_progress()
        self.drv_lb.delete(0, tk.END)
        self.current_session = None
        if self.main_tab:
            self.main_tab.show_overview()
            self.main_tab.show_session_results_data(None)

        threading.Thread(
            target=self._load_session_thread,
            args=(year, gp, ses),
            daemon=True
        ).start()

    def _load_session_thread(self, year, gp, ses):
        fut = self.svc.load_session_async(year, gp, ses)
        def _done(fut):
            try:
                session = fut.result()
                self.current_session = session
                self.drv_lb.delete(0, tk.END)
                if session and hasattr(session, 'drivers'):
                    abbrs = []
                    for num in session.drivers:
                        info = session.get_driver(num)
                        if info and 'Abbreviation' in info:
                            abbrs.append(info['Abbreviation'])
                    for abbr in sorted(abbrs):
                        self.drv_lb.insert(tk.END, abbr)
                self._stop_loading_progress(True)
                if self.main_tab:
                    self.main_tab.show_map(session)
                    self.main_tab.show_session_results_data(session)
                messagebox.showinfo("ロード完了", f"{year} {gp} {ses} を読み込みました。")
            except Exception as e:
                self._stop_loading_progress(False)
                self.current_session = None
                if self.main_tab:
                    self.main_tab.show_session_results_data(None)
                messagebox.showerror("セッション取得エラー", str(e))
        fut.add_done_callback(lambda f: self.after(0, _done, f))

    def _start_loading_progress(self):
        self.progress.configure(mode='indeterminate')
        self.progress.start(10)

    def _stop_loading_progress(self, success=True):
        self.progress.stop()
        self.progress.configure(mode='determinate')
        self.progress_var.set(100 if success else 0)

    def _get_selected_drivers(self):
        return [self.drv_lb.get(i) for i in self.drv_lb.curselection()]

    def _ensure_session_loaded(self):
        if not self.current_session:
            messagebox.showinfo("セッション未ロード", "先にセッションを読み込んでください。")
            return False
        return True

    # --- コマンドメソッド ---
    def _cmd_show_single_telemetry(self):
        if not self._ensure_session_loaded(): return
        drivers = self._get_selected_drivers()
        if len(drivers) != 1:
            messagebox.showinfo("ドライバー選択", "1名選択してください。")
            return
        self.main_tab.show_single_driver_telemetry(self.current_session, drivers[0])

    def _cmd_show_single_scatter(self):
        if not self._ensure_session_loaded(): return
        drivers = self._get_selected_drivers()
        if len(drivers) != 1:
            messagebox.showinfo("ドライバー選択", "1名選択してください。")
            return
        self.main_tab.show_single_driver_scatter(self.current_session, drivers[0])

    def _cmd_show_laptime_comparison(self):
        if not self._ensure_session_loaded(): return
        drivers = self._get_selected_drivers()
        if not drivers:
            messagebox.showinfo("ドライバー選択", "少なくとも1名選択してください。")
            return
        self.main_tab.show_laptime_comparison(self.current_session, drivers)

    def _cmd_show_speed_comparison(self):
        if not self._ensure_session_loaded(): return
        drivers = self._get_selected_drivers()
        if not drivers:
            messagebox.showinfo("ドライバー選択", "少なくとも1名選択してください。")
            return
        self.main_tab.show_speed_comparison(self.current_session, drivers)

    def _cmd_show_scatter_comparison(self):
        if not self._ensure_session_loaded(): return
        drivers = self._get_selected_drivers()
        if not drivers:
            messagebox.showinfo("ドライバー選択", "少なくとも1名選択してください。")
            return
        if len(drivers) > 4:
            messagebox.showinfo("選択超過", "最大4名まで選択可能です。最初の4名を使用します。")
            drivers = drivers[:4]
        self.main_tab.show_scatter_comparison(self.current_session, drivers)