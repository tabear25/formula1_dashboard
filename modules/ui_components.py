import tkinter as tk
from tkinter import ttk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from modules.plotting_modules import plot_speed_telemetry

class Sidebar(tk.Frame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self._build()

    def _build(self):
        # Year selection
        ttk.Label(self, text="Year:").pack(anchor='w', pady=(10,0))
        self.year_cb = ttk.Combobox(self, values=[1950,1951,1952,1953,1954,1955,1956,1957,1958,1959,1960,1961,1962,1963,1964,1965,1966,1967,1968,1969,1970,1971,1972,1973,1974,1975,1976,1977,1978,1979,1980,1981,1982,1983,1984,1985,1986,1987,1988,1989,1990,1991,1992,1993,1994,1995,1996,1997,1998,1999,2000,2001,2002,2003,2004,2005,2006,2007,2008,2009,2010,2011,2012,2013,2014,2015,2016,2017,2018,2019,2020,2021,2022,2023,2024,2025], state='readonly')
        self.year_cb.current(3)
        self.year_cb.pack(fill='x')
        # GP selection
        ttk.Label(self, text="Grand Prix:").pack(anchor='w', pady=(10,0))
        self.gp_cb = ttk.Combobox(self, values=[], state='readonly')
        self.gp_cb.pack(fill='x')
        # Session selection
        ttk.Label(self, text="Session:").pack(anchor='w', pady=(10,0))
        self.ses_cb = ttk.Combobox(self, values=['FP1','FP2','FP3','Q','R'], state='readonly')
        self.ses_cb.current(3)
        self.ses_cb.pack(fill='x')
        # Driver selection
        ttk.Label(self, text="Driver:").pack(anchor='w', pady=(10,0))
        self.driver_cb = ttk.Combobox(self, values=[], state='readonly')
        self.driver_cb.pack(fill='x')
        # Load button / progress
        self.load_btn = ttk.Button(self, text="Load Session")
        self.load_btn.pack(fill='x', pady=(20,0))
        self.progress = ttk.Progressbar(self, mode='indeterminate')
        self.progress.pack(fill='x', pady=(10,0))

    def bind(self, data_service, main_tab):
        self.data_service = data_service
        self.main_tab = main_tab
        # Events
        self.year_cb.bind('<<ComboboxSelected>>', self._on_year)
        self.load_btn.config(command=self._on_load)
        # Trigger initial year load
        self._on_year()

    def _on_year(self, event=None):
        year = int(self.year_cb.get())
        df = self.data_service.get_schedule(year)
        gps = df['EventName'].tolist()
        self.gp_cb['values'] = gps
        if gps:
            self.gp_cb.current(0)

    def _on_load(self):
        year = int(self.year_cb.get())
        gp = self.gp_cb.get()
        ses = self.ses_cb.get()
        # start progress
        self.progress.start()
        # async load
        self.data_service.load_session(year, gp, ses, self._on_session_loaded)

    def _on_session_loaded(self, session):
        # stop progress
        self.progress.stop()
        # populate drivers
        drivers = sorted({d for d in session.drivers})
        self.driver_cb['values'] = drivers
        if drivers:
            self.driver_cb.current(0)
        # display initial plot
        driver = self.driver_cb.get()
        self.main_tab.display_telemetry(session, driver)
        # bind driver change
        self.driver_cb.bind('<<ComboboxSelected>>', lambda e: self.main_tab.display_telemetry(session, self.driver_cb.get()))

class MainTab(tk.Frame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self._build()

    def _build(self):
        self.notebook = ttk.Notebook(self)
        # Telemetry tab
        self.tab1 = ttk.Frame(self.notebook)
        self.notebook.add(self.tab1, text='Telemetry')
        # Placeholder tab
        self.tab2 = ttk.Frame(self.notebook)
        self.notebook.add(self.tab2, text='Laptimes')
        self.notebook.pack(fill='both', expand=True)

    def display_telemetry(self, session, driver):
        # Clear tab1
        for widget in self.tab1.winfo_children():
            widget.destroy()
        # Generate plot
        fig = plot_speed_telemetry(session, driver)
        # Embed in Tk
        canvas = FigureCanvasTkAgg(fig, master=self.tab1)
        canvas.draw()
        canvas.get_tk_widget().pack(fill='both', expand=True)