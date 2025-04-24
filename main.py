import sys
import logging
import tkinter as tk
from tkinter import ttk
from config import APP_TITLE, WINDOW_SIZE, COLOR_BG, COLOR_FRAME, COLOR_TEXT, COLOR_ACCENT
from service import FastF1Service, CacheManager
from ui.main_tab_caller import MainTab
from ui.sidebar_caller import Sidebar

class F1DashboardApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry(WINDOW_SIZE)
        self.configure(bg=COLOR_BG)
        self.minsize(1000, 600)

        self.service = FastF1Service()
        CacheManager.cleanup_cache()

        self.main_tab = MainTab(self)
        self.main_tab.pack(side="right", expand=True, fill="both")

        self.sidebar = Sidebar(self,
                               svc=self.service,
                               main_tab=self.main_tab,
                               width=260)
        self.sidebar.pack(side="left", fill="y")

        style = ttk.Style(self)
        style.theme_use(style.theme_names()[0])
        style.configure("TFrame",     background=COLOR_FRAME)
        style.configure("TLabel",     background=COLOR_FRAME,
                                     foreground=COLOR_TEXT)
        style.configure("TNotebook",  background=COLOR_FRAME,
                                     foreground=COLOR_TEXT)
        style.configure("MainNotebook.TNotebook",
                        background=COLOR_FRAME,
                        borderwidth=0)
        style.configure("TProgressbar",
                        troughcolor=COLOR_FRAME,
                        bordercolor=COLOR_BG,
                        background=COLOR_ACCENT)

def main():
    logging.basicConfig(level=logging.INFO,
                        format="[%(asctime)s] %(levelname)s %(message)s")
    app = F1DashboardApp()
    app.mainloop()

if __name__ == "__main__":
    if getattr(sys, "_f1_dashboard_started", False):
        sys.exit(0)
    sys._f1_dashboard_started = True
    main()
