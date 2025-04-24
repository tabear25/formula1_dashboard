import tkinter as tk
from tkinter import ttk
from service import FastF1Service
from ui.sidebar.sidebar_initializer import SidebarInitializer
from ui.sidebar.sidebar_actions import SidebarActions

class Sidebar(tk.Frame, SidebarInitializer, SidebarActions):
    def __init__(self, master, svc: FastF1Service, main_tab, **kw):
        super().__init__(master, **kw)
        self.svc             = svc
        self.main_tab        = main_tab
        self.current_session = None

        # ウィジェット生成
        self.build_widgets()