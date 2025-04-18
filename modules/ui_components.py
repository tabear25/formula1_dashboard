import tkinter as tk
from tkinter import ttk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from tkhtmlview import HTMLLabel
from modules.plotting_modules import (
    plot_speed_telemetry, plot_session_info, plot_circuit_map, plot_laptime_comparison,
    plot_position_changes, plot_points_bar, plot_track_heatmap, plot_qualy_bubble,
    plot_tire_strategy, plot_team_pace
)

class Sidebar(tk.Frame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self._build()

    def _build(self):
        ttk.Label(self, text="Year:").pack(anchor='w', pady=5)
        self.year_cb = ttk.Combobox(self, values=[1950,1951,1952,1953,1954,1955,1956,1957,1958,1959,1960,1961,1962,1963,1964,1965,1966,1967,1968,1969,1970,1971,1972,1973,1974,1975,1976,1977,1978,1979,1980,1981,1982,1983,1984,1985,1986,1987,1988,1989,1990,1991,1992,1993,1994,1995,1996,1997,1998,1999,2000,2001,2002,2003,2004,2005,2006,2007,2008,2009,2010,2011,2012,2013,2014,2015,2016,2017,2018,2019,2020,2021,2022,2023,2024,2025], state='readonly')
        self.year_cb.current(3)
        self.year_cb.pack(fill='x')

        ttk.Label(self, text="GP:").pack(anchor='w', pady=5)
        self.gp_cb = ttk.Combobox(self, values=[], state='readonly')
        self.gp_cb.pack(fill='x')

        ttk.Label(self, text="Session:").pack(anchor='w', pady=5)
        self.ses_cb = ttk.Combobox(self, values=['FP1','FP2','FP3','Q','R'], state='readonly')
        self.ses_cb.current(4)
        self.ses_cb.pack(fill='x')

        ttk.Label(self, text="Drivers:").pack(anchor='w', pady=5)
        self.drivers_lb = tk.Listbox(self, selectmode='multiple', height=4)
        self.drivers_lb.pack(fill='x')

        self.load_btn = ttk.Button(self, text="Load")
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
        self.drivers_lb.bind('<<ListboxSelect>>', lambda e: self.mt.show_all(ses, [self.drivers_lb.get(i) for i in self.drivers_lb.curselection()]))
        # Display all tabs with default selection
        selected = [self.drivers_lb.get(i) for i in self.drivers_lb.curselection()] or [sorted(ses.drivers)[0]]
        self.mt.show_all(ses, selected)

class MainTab(tk.Frame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self._build()

    def _build(self):
        self.nb = ttk.Notebook(self)
        self.tabs = {}
        tab_names = ['Telemetry','SessionInfo','CircuitMap','LapComp','PosChange','Points','Heatmap','QualyBubble','Strategy','TeamPace']
        for name in tab_names:
            frame = ttk.Frame(self.nb)
            self.nb.add(frame, text=name)
            self.tabs[name] = frame
        self.nb.pack(fill='both', expand=True)

    def clear(self, tab):
        for widget in tab.winfo_children():
            widget.destroy()

    def embed_fig(self, fig, tab):
        self.clear(tab)
        canvas = FigureCanvasTkAgg(fig, master=tab)
        canvas.draw()
        canvas.get_tk_widget().pack(fill='both', expand=True)

    def show_all(self, ses, drivers):
        # Telemetry
        self.embed_fig(plot_speed_telemetry(ses, drivers[0]), self.tabs['Telemetry'])
        # Session Info
        self.embed_fig(plot_session_info(ses), self.tabs['SessionInfo'])
        # Circuit Map
        self.embed_fig(plot_circuit_map(ses), self.tabs['CircuitMap'])
        # Lap Time Comparison
        self.embed_fig(plot_laptime_comparison(ses, drivers[:4]), self.tabs['LapComp'])
        # Position Changes
        self.embed_fig(plot_position_changes(ses), self.tabs['PosChange'])
        # Points Bar
        self.embed_fig(plot_points_bar(ses), self.tabs['Points'])
        # Speed Heatmap
        self.embed_fig(plot_track_heatmap(ses), self.tabs['Heatmap'])
        # Qualy Bubble (interactive)
        self.clear(self.tabs['QualyBubble'])
        fig = plot_qualy_bubble(ses, drivers[:4])
        html = fig.to_html(include_plotlyjs='cdn')
        html_label = HTMLLabel(self.tabs['QualyBubble'], html=html)
        html_label.pack(fill='both', expand=True)
        # Team Pace
        self.embed_fig(plot_team_pace(ses), self.tabs['TeamPace'])
        self.embed_fig(plot_tire_strategy(ses), self.tabs['Strategy'])
        # Team Pace
        self.embed_fig(plot_team_pace(ses), self.tabs['TeamPace'])