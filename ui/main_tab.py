import tkinter as tk
from tkinter import ttk
from tabs.overview import init_overview, show_overview
from tabs.map_tab import init_map, show_map
from tabs.compare_tab import init_compare, show_compare
from tabs.speed_tab import init_speed, show_speed_compare
from tabs.scatter_tab import init_scatter, show_scatter_compare
from tabs.telemetry_tab import init_telemetry, show_telemetry

class MainTab(ttk.Notebook):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.configure(style="MainNotebook.TNotebook")

        # 各タブの初期化
        self.overview_frame  = init_overview(self)
        self.map_frame       = init_map(self)
        self.compare_frame   = init_compare(self)
        self.speed_frame     = init_speed(self)
        self.scatter_frame   = init_scatter(self)
        self.telemetry_frame = init_telemetry(self)

    # tabs/*で定義された関数を呼び出すためのメソッド
    def show_overview(self, *args, **kwargs):
        return show_overview(self.overview_frame, *args, **kwargs)

    def show_map(self, session):
        return show_map(self.map_frame, session)

    def show_multi_driver_compare(self, session, drivers):
        return show_compare(self.compare_frame, session, drivers)

    def show_multi_driver_speed(self, session, drivers):
        return show_speed_compare(self.speed_frame, session, drivers)

    def show_multi_lap_scatter(self, session, drivers):
        return show_scatter_compare(self.scatter_frame, session, drivers)

    def show_telemetry(self, session, driver):
        return show_telemetry(self.telemetry_frame, session, driver)
