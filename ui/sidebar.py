import tkinter as tk
from tkinter import ttk, messagebox
from config import COLOR_FRAME, COLOR_TEXT, YEAR_LIST 
from service import FastF1Service
import threading 
import datetime 

class Sidebar(tk.Frame):
    def __init__(self, master, svc: FastF1Service, main_tab, **kw):
        requested_width = kw.pop('width', 260) 
        super().__init__(master, width=requested_width, bg=COLOR_FRAME, **kw) 
        
        self.canvas = tk.Canvas(self, bg=COLOR_FRAME, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.internal_frame = tk.Frame(self.canvas, bg=COLOR_FRAME) 
        self.canvas_window = self.canvas.create_window((0, 0), window=self.internal_frame, anchor="nw", tags="self.internal_frame")

        self.internal_frame.bind("<Configure>", self._on_frame_configure)
        
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind("<Button-4>", self._on_mousewheel)
        self.canvas.bind("<Button-5>", self.canvas.yview_scroll, ("1", "units")) # Simplified Linux scroll

        self.svc = svc
        self.main_tab = main_tab 
        self.current_session = None

        # --- Populate the internal_frame with sidebar content ---
        tk.Label(self.internal_frame, text="開催年", bg=COLOR_FRAME, fg=COLOR_TEXT) \
          .pack(anchor="w", padx=10, pady=(10,0))
        year_frame = tk.Frame(self.internal_frame, bg=COLOR_FRAME)
        year_frame.pack(fill="x", padx=10)
        self.year_var = tk.IntVar(value=YEAR_LIST[-1] if YEAR_LIST else datetime.date.today().year) # Handle empty YEAR_LIST
        
        self.year_lb = tk.Listbox(year_frame, height=6, exportselection=False)
        for year_val in YEAR_LIST:
            self.year_lb.insert(tk.END, year_val)
        if YEAR_LIST: 
            self.year_lb.selection_set(tk.END) 
            self.year_lb.see(tk.END)

        self.year_lb.pack(side="left", fill="both", expand=True)
        self.year_lb.bind("<<ListboxSelect>>", self._on_year_select)

        tk.Label(self.internal_frame, text="グランプリ", bg=COLOR_FRAME, fg=COLOR_TEXT) \
          .pack(anchor="w", padx=10, pady=(10,0))
        gp_frame = tk.Frame(self.internal_frame, bg=COLOR_FRAME)
        gp_frame.pack(fill="x", padx=10)
        self.gp_var = tk.StringVar()
        self.gp_lb = tk.Listbox(gp_frame, height=8, exportselection=False)
        self.gp_lb.pack(side="left", fill="both", expand=True)
        self.gp_lb.bind("<<ListboxSelect>>", self._on_gp_select)

        tk.Label(self.internal_frame, text="セッション", bg=COLOR_FRAME, fg=COLOR_TEXT) \
          .pack(anchor="w", padx=10, pady=(10,0))
        self.ses_var = tk.StringVar()
        self.ses_cmb = ttk.Combobox(self.internal_frame,
                                    textvariable=self.ses_var,
                                    state="readonly",
                                    values=["FP1","FP2","FP3","Q","R"])
        self.ses_cmb.pack(fill="x", padx=10)
        self.ses_cmb.bind("<<ComboboxSelected>>", self._on_session_select)

        tk.Label(self.internal_frame, text="ドライバー (複数選択可)", bg=COLOR_FRAME, fg=COLOR_TEXT) \
          .pack(anchor="w", padx=10, pady=(10,0))
        drv_frame = tk.Frame(self.internal_frame, bg=COLOR_FRAME)
        drv_frame.pack(fill="x", padx=10)
        self.drv_lb = tk.Listbox(drv_frame, selectmode="multiple", height=6, exportselection=False)
        self.drv_lb.pack(side="left", fill="both", expand=True)

        buttons_config = [
            ("テレメトリ (単一)", self._cmd_show_single_telemetry),
            ("ラップ散布図 (単一)", self._cmd_show_single_scatter),
            ("ラップタイム比較 (複数)", self._cmd_show_laptime_comparison),
            ("速度比較 (複数)", self._cmd_show_speed_comparison),
            ("散布図比較 (複数)", self._cmd_show_scatter_comparison),
        ]
        for txt, cmd in buttons_config:
            ttk.Button(self.internal_frame, text=txt, command=cmd) \
               .pack(fill="x", padx=10, pady=3)

        self.progress_var = tk.DoubleVar(value=0)
        self.progress = ttk.Progressbar(self.internal_frame, mode='determinate', variable=self.progress_var, maximum=100)
        self.progress.pack(fill="x", padx=10, pady=10, anchor='s')

        self.internal_frame.update_idletasks()
        self._on_frame_configure() 
        self.after_idle(lambda: self.canvas.itemconfig(self.canvas_window, width=self.canvas.winfo_width()))


    def _on_frame_configure(self, event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        if self.canvas.winfo_width() > 1 : 
            self.canvas.itemconfig(self.canvas_window, width=self.canvas.winfo_width())

    def _on_mousewheel(self, event):
        # Linux scroll events (Button-4 and Button-5) are handled by direct binding now.
        # This handles Windows/macOS specific MouseWheel event.
        if hasattr(event, 'delta') and event.delta: # Check if delta attribute exists and is non-zero
             self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        # For direct Button-4/5 binding, the command itself handles scroll, so no explicit check for event.num here needed
        # unless this method is also bound to Button-4/5, which is slightly redundant with the new direct bind.

    def _start_loading_progress(self):
        self.progress.configure(mode='indeterminate')
        self.progress.start(10) 

    def _stop_loading_progress(self, success=True):
        self.progress.stop()
        self.progress.configure(mode='determinate')
        self.progress_var.set(100 if success else 0)

    def _on_year_select(self, event):
        sel = self.year_lb.curselection()
        if not sel: return
        year = int(self.year_lb.get(sel[0]))
        if self.year_var.get() == year and self.gp_lb.size() > 0: 
             return
        self.year_var.set(year)
        self.gp_lb.delete(0, tk.END) 
        self.drv_lb.delete(0, tk.END) 
        self.current_session = None   
        if self.main_tab: self.main_tab.show_overview() 

        self._start_loading_progress()
        threading.Thread(
            target=self._load_schedule_thread,
            args=(year,),
            daemon=True
        ).start()

    def _load_schedule_thread(self, year):
        fut = self.svc.get_event_schedule_async(year)
        def _done_callback(future):
            try:
                schedule_df = future.result() # Pandas DataFrame expected
                self.gp_lb.delete(0, tk.END)
                if not schedule_df.empty: # Check if DataFrame is not empty
                    # Assuming 'EventName' is a column in the DataFrame
                    for gp_event_name in schedule_df['EventName']:
                        self.gp_lb.insert(tk.END, gp_event_name)
                self._stop_loading_progress(success=True)
            except Exception as e:
                self._stop_loading_progress(success=False)
                messagebox.showerror("スケジュール取得エラー", f"エラー: {e}\nインターネット接続を確認するか、後で再試行してください。")
        
        fut.add_done_callback(lambda f: self.after(0, _done_callback, f))


    def _on_gp_select(self, event):
        sel = self.gp_lb.curselection()
        if not sel: return
        self.gp_var.set(self.gp_lb.get(sel[0]))

    def _on_session_select(self, event=None): 
        year = self.year_var.get()
        gp_name = self.gp_var.get()
        session_type = self.ses_var.get()

        if not (year and gp_name and session_type):
            messagebox.showinfo("選択不足", "年、グランプリ、セッションタイプをすべて選択してください。")
            return

        self._start_loading_progress()
        self.drv_lb.delete(0, tk.END) 
        self.current_session = None   
        if self.main_tab: self.main_tab.show_overview() 

        threading.Thread(
            target=self._load_session_thread,
            args=(year, gp_name, session_type),
            daemon=True
        ).start()

    def _load_session_thread(self, year, gp, ses):
        # Assuming FastF1Service is correctly typed and svc is an instance of it
        fut = self.svc.load_session_async(year, gp, ses)
        def _done_callback(future):
            try:
                session_obj = future.result() # Expecting a FastF1 Session object
                self.current_session = session_obj
                
                self.drv_lb.delete(0, tk.END)
                # Ensure session_obj is not None and has 'drivers' attribute
                if session_obj and hasattr(session_obj, 'drivers') and session_obj.drivers:
                    driver_abbreviations = []
                    for drv_num in session_obj.drivers: # drivers is typically a list of driver numbers/IDs
                        try:
                            driver_info = session_obj.get_driver(drv_num) # Method to get driver details
                            if driver_info is not None and 'Abbreviation' in driver_info:
                                driver_abbreviations.append(driver_info['Abbreviation'])
                        except Exception: 
                            pass # Log error or handle missing driver info
                    
                    driver_abbreviations.sort() 
                    for abbr in driver_abbreviations:
                        self.drv_lb.insert(tk.END, abbr)

                self._stop_loading_progress(success=True)
                if self.main_tab: self.main_tab.show_map(self.current_session) 
                messagebox.showinfo("ロード完了", f"{year} {gp} – {ses} を読み込みました。\nドライバーを選択して分析を開始してください。")

            except Exception as e:
                self._stop_loading_progress(success=False)
                self.current_session = None 
                messagebox.showerror("セッション取得エラー", f"エラー: {e}\nデータが存在しないか、ロードに失敗しました。")
        
        fut.add_done_callback(lambda f: self.after(0, _done_callback, f))

    def _get_selected_drivers(self):
        return [self.drv_lb.get(i) for i in self.drv_lb.curselection()]

    def _ensure_session_loaded(self):
        if not self.current_session:
            messagebox.showinfo("セッション未ロード", "先にセッションを読み込んでください。")
            return False
        return True

    def _cmd_show_single_telemetry(self):
        if not self._ensure_session_loaded(): return
        drivers = self._get_selected_drivers()
        if len(drivers) != 1:
            messagebox.showinfo("ドライバー選択", "テレメトリ表示にはドライバーを1名選択してください。")
            return
        if self.main_tab: self.main_tab.show_single_driver_telemetry(self.current_session, drivers)

    def _cmd_show_single_scatter(self):
        if not self._ensure_session_loaded(): return
        drivers = self._get_selected_drivers()
        if len(drivers) != 1:
            messagebox.showinfo("ドライバー選択", "ラップ散布図表示にはドライバーを1名選択してください。")
            return
        if self.main_tab: self.main_tab.show_single_driver_scatter(self.current_session, drivers)

    def _cmd_show_laptime_comparison(self):
        if not self._ensure_session_loaded(): return
        drivers = self._get_selected_drivers()
        if len(drivers) < 1: 
            messagebox.showinfo("ドライバー選択", "ラップタイム比較には少なくとも1名以上のドライバーを選択してください。")
            return
        if self.main_tab: self.main_tab.show_laptime_comparison(self.current_session, drivers)

    def _cmd_show_speed_comparison(self):
        if not self._ensure_session_loaded(): return
        drivers = self._get_selected_drivers()
        if len(drivers) < 1:
            messagebox.showinfo("ドライバー選択", "速度比較には少なくとも1名以上のドライバーを選択してください。")
            return
        if self.main_tab: self.main_tab.show_speed_comparison(self.current_session, drivers)

    def _cmd_show_scatter_comparison(self):
        if not self._ensure_session_loaded(): return
        drivers = self._get_selected_drivers()
        if len(drivers) < 1:
            messagebox.showinfo("ドライバー選択", "散布図比較には少なくとも1名以上のドライバーを選択してください (最大4名)。")
            return
        if len(drivers) > 4:
            messagebox.showinfo("ドライバー選択超過", "散布図比較では最大4名まで選択可能です。最初の4名が表示されます。")
            drivers = drivers[:4]
        if self.main_tab: self.main_tab.show_scatter_comparison(self.current_session, drivers)