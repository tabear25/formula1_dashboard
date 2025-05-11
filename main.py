import sys
import logging
import tkinter as tk
from tkinter import ttk
from config import APP_TITLE, WINDOW_SIZE, COLOR_BG, COLOR_FRAME, COLOR_TEXT, COLOR_ACCENT, MPL_STYLE
from service import FastF1Service, CacheManager
from ui.main_tab import MainTab
from ui.sidebar import Sidebar
import fastf1.plotting

class F1DashboardApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry(WINDOW_SIZE)
        self.configure(bg=COLOR_BG)
        self.minsize(800, 600)

        if MPL_STYLE:
            try:
                fastf1.plotting.setup_mpl(mpl_timedelta_support=True, color_scheme=MPL_STYLE, misc_mpl_mods=False)
                logging.info(f"Applied Matplotlib style: {MPL_STYLE}")
            except Exception as e:
                logging.warning(f"Could not apply Matplotlib style '{MPL_STYLE}': {e}")

        self.service = FastF1Service()
        CacheManager.cleanup_cache()

        self.paned_window = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        self.paned_window.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 1. MainTab を先にインスタンス化 (親は PanedWindow)
        self.main_tab = MainTab(self.paned_window)
        
        # 2. Sidebar をインスタンス化 (親は PanedWindow)
        self.sidebar = Sidebar(self.paned_window,
                               svc=self.service,
                               main_tab=self.main_tab, # main_tab をコンストラクタに渡す
                               width=260) 

        # 3. PanedWindow にウィジェットを追加 (ここが正しい場所で、一度だけのはず)
        self.paned_window.add(self.sidebar, weight=0) 
        self.paned_window.add(self.main_tab, weight=1)

        # ↓↓↓ この下に、以前の重複した .add() や .main_tab の再設定がないことを確認してください ↓↓↓

        # Global ttk widget styling
        style = ttk.Style(self)
        try:
            if 'clam' in style.theme_names(): style.theme_use('clam')
            elif 'alt' in style.theme_names(): style.theme_use('alt')
            else: style.theme_use(style.theme_names()[0])
        except tk.TclError:
            style.theme_use(style.theme_names()[0])

        style.configure("TFrame", background=COLOR_FRAME)
        style.configure("TLabel", background=COLOR_FRAME, foreground=COLOR_TEXT)
        style.configure("TButton", background=COLOR_ACCENT, foreground=COLOR_BG)
        
        style.configure("TNotebook", background=COLOR_BG, borderwidth=0)
        style.configure("TNotebook.Tab", background=COLOR_FRAME, foreground=COLOR_TEXT, padding=[5, 2])
        style.map("TNotebook.Tab",
                  background=[("selected", COLOR_ACCENT), ("active", COLOR_ACCENT)], # COLOR_HIGHLIGHT から COLOR_ACCENT へ変更
                  foreground=[("selected", COLOR_BG)])

        style.configure("MainNotebook.TNotebook", background=COLOR_FRAME, borderwidth=0)
        style.configure("MainNotebook.TNotebook.Tab", background=COLOR_BG, foreground=COLOR_TEXT, padding=[10,5], font=('TkDefaultFont', 10, 'bold'))
        style.map("MainNotebook.TNotebook.Tab",
                  background=[("selected", COLOR_ACCENT), ("active", COLOR_FRAME)],
                  foreground=[("selected", COLOR_BG),("active", COLOR_ACCENT)])

        style.configure("TProgressbar", troughcolor=COLOR_FRAME, bordercolor=COLOR_BG, background=COLOR_ACCENT)
        
        style.configure(" Sash", background=COLOR_ACCENT, borderwidth=2, relief=tk.RAISED)
        style.configure("Horizontal. Sash", background=COLOR_BG, borderwidth=0, lightcolor=COLOR_ACCENT, darkcolor=COLOR_ACCENT, gripcount=10)
        style.configure("Vertical. Sash", background=COLOR_BG, borderwidth=0, lightcolor=COLOR_ACCENT, darkcolor=COLOR_ACCENT, gripcount=10)


def main():
    logging.basicConfig(level=logging.INFO,
                        format="[%(asctime)s] %(levelname)s %(filename)s:%(lineno)d %(message)s")
    
    try:
        app = F1DashboardApp()
        app.mainloop()
    except Exception as e:
        logging.critical("Application failed to start or encountered a critical error during runtime.", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    if getattr(sys, "_f1_dashboard_started", False):
        logging.warning("F1 Dashboard already started or flag not cleared. Exiting.")
        sys.exit(0)
    sys._f1_dashboard_started = True
    main()