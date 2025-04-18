import tkinter as tk
from tkinter import ttk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from modules.plotting_modules import *

class Sidebar(tk.Frame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self._build()

    def _build(self):
        ttk.Label(self, text="Year:").pack(anchor='w', pady=5)
        self.year_cb = ttk.Combobox(self, values=[2022,2023,2024,2025], state='readonly')
        self.year_cb.current(3)
        self.year_cb.pack(fill='x')

        ttk.Label(self, text="GP:").pack(anchor='w', pady=5)
        self.gp_cb = ttk.Combobox(self, values=[], state='readonly')
        self.gp_cb.pack(fill='x')

        ttk.Label(self, text="Session:").pack(anchor='w', pady=5)
        self.ses_cb = ttk.Combobox(self, values=['FP1','FP2','FP3','Q','R'], state='readonly')
        self.ses_cb.current(3)
        self.ses_cb.pack(fill='x')

        ttk.Label(self, text="Drivers:").pack(anchor='w', pady=5)
        self.drivers_lb = tk.Listbox(self, selectmode='multiple', height=4)
        self.drivers_lb.pack(fill='x')

        self.load_btn = ttk.Button(self, text="Load")
        self.load_btn.pack(fill='x', pady=10)
        self.load_btn.pack(fill='x', pady=10)

        self.progress = ttk.Progressbar(self, mode='indeterminate')
        self.progress.pack(fill='x')

    def bind(self, ds, mt):
        self.ds = ds
        self.mt = mt
        self.year_cb.bind('<<ComboboxSelected>>', self._on_year)
        self.load_btn.config(command=self._on_load)
        self._on_year()

    def _on_year(self, event=None):
        df = self.ds.get_schedule(int(self.year_cb.get()))
        gps = df['EventName'].tolist()
        self.gp_cb['values'] = gps
        self.gp_cb.current(0)

    def _on_load(self):
        self.progress.start()
        self.ds.load_session(int(self.year_cb.get()), self.gp_cb.get(), self.ses_cb.get(), self._loaded)

    def _loaded(self, ses):
        self.progress.stop()
        self.mt.session = ses
        self.drivers_lb.delete(0, 'end')
        for d in sorted(ses.drivers):
            self.drivers_lb.insert('end', d)
        self.mt.show_all(ses, [self.drivers_lb.get(i) for i in self.drivers_lb.curselection()] or [ses.drivers[0]])
        self.drivers_lb.bind('<<ListboxSelect>>', lambda e: self.mt.show_all(ses, [self.drivers_lb.get(i) for i in self.drivers_lb.curselection()]))

class MainTab(tk.Frame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self._build()

    def _build(self):
        self.notebook = ttk.Notebook(self)
        # 必要なタブを追加
        for name in ['Telemetry','SessionInfo','CircuitMap','LapComp','PosChange','Points','Heatmap','QualyBubble','Strategy','TeamPace']:
            frame = ttk.Frame(self.notebook)
            self.notebook.add(frame, text=name)
        self.notebook.pack(fill='both', expand=True)
