import tkinter as tk
from tkinter import ttk
from tabs.overview import init_overview, show_overview
from tabs.map_tab import init_map, show_map
from tabs.compare_tab import init_compare, show_compare
from tabs.speed_tab import init_speed, show_speed_compare
from tabs.scatter_tab import init_scatter, show_scatter_compare, init_single_scatter, show_single_driver_scatter # Added single scatter imports
from tabs.telemetry_tab import init_telemetry, show_telemetry

class MainTab(ttk.Notebook):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.configure(style="MainNotebook.TNotebook")

        self.overview_frame          = init_overview(self)
        self.map_frame               = init_map(self)
        
        # 各関数名の再定義
        self.single_telemetry_frame  = init_telemetry(self) 
        self.single_scatter_frame    = init_single_scatter(self) 
        self.laptime_compare_frame   = init_compare(self)
        self.speed_compare_frame     = init_speed(self) 
        self.scatter_compare_frame   = init_scatter(self)


    # tabs/*で定義された関数を呼び出すためのメソッド
    def show_overview(self, *args, **kwargs):
        self.select(self.overview_frame) # Select tab before showing content
        return show_overview(self.overview_frame, *args, **kwargs)

    def show_map(self, session):
        self.select(self.map_frame)
        return show_map(self.map_frame, session)

    # Single Driver Views
    def show_single_driver_telemetry(self, session, driver_list_one_elem):
        self.select(self.single_telemetry_frame)
        return show_telemetry(self.single_telemetry_frame, session, driver_list_one_elem)

    def show_single_driver_scatter(self, session, driver_list_one_elem):
        self.select(self.single_scatter_frame)
        return show_single_driver_scatter(self.single_scatter_frame, session, driver_list_one_elem[0])

    # Multi-Driver Comparison Views
    def show_laptime_comparison(self, session, drivers): # Formerly show_multi_driver_compare
        self.select(self.laptime_compare_frame)
        return show_compare(self.laptime_compare_frame, session, drivers)

    def show_speed_comparison(self, session, drivers): # Formerly show_multi_driver_speed
        self.select(self.speed_compare_frame)
        return show_speed_compare(self.speed_compare_frame, session, drivers)

    def show_scatter_comparison(self, session, drivers): # Formerly show_multi_lap_scatter
        self.select(self.scatter_compare_frame)
        return show_scatter_compare(self.scatter_compare_frame, session, drivers)