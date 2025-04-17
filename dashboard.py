# dashboard.py
import tkinter as tk
from modules.ui_components import Sidebar, MainTab
from modules.data_service import DataService

class DashboardApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("F1 Information Dashboard")
        self.geometry("1280x800")
        # Initialize services
        ds = DataService()
        # UI components
        self.sidebar = Sidebar(self)
        self.sidebar.pack(side='left', fill='y')
        self.main_tab = MainTab(self)
        self.main_tab.pack(side='right', fill='both', expand=True)
        # Bind
        self.sidebar.bind(ds, self.main_tab)

if __name__ == '__main__':
    app = DashboardApp()
    app.mainloop()
