import tkinter as tk
from modules.ui_components import Sidebar, MainTab
from modules.data_service import DataService

class DashboardApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('F1 Dashboard')
        self.geometry('1280x800')
        ds = DataService()
        sb = Sidebar(self, width=200, bg='#161E2F')
        sb.pack(side='left', fill='y')
        mt = MainTab(self, bg='#242F48')
        mt.pack(side='right', fill='both', expand=True)
        sb.bind(ds, mt)

if __name__ == '__main__':
    DashboardApp().mainloop()