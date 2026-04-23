import sys
import logging
import tkinter as tk
from tkinter import ttk
from config import APP_TITLE, COLOR_HIGHLIGHT, WINDOW_SIZE, COLOR_BG, COLOR_FRAME, COLOR_TEXT, COLOR_ACCENT, MPL_STYLE
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

        self.main_tab = MainTab(self.paned_window)
        self.sidebar = Sidebar(self.paned_window,
                               svc=self.service,
                               main_tab=self.main_tab,
                               width=260) 

        self.paned_window.add(self.sidebar, weight=0) 
        self.paned_window.add(self.main_tab, weight=1)

        style = ttk.Style(self)
        try:
            current_theme = style.theme_use() # Get current theme to base on it
            if 'clam' in style.theme_names(): style.theme_use('clam')
            elif 'alt' in style.theme_names(): style.theme_use('alt')
            # else keep current_theme
        except tk.TclError:
            style.theme_use(style.theme_names()[0]) # Fallback

        style.configure("TFrame", background=COLOR_FRAME)
        style.configure("TLabel", background=COLOR_FRAME, foreground=COLOR_TEXT)
        style.configure("TButton", background=COLOR_ACCENT, foreground=COLOR_TEXT) # Text color on button
        style.map("TButton", background=[('active', COLOR_HIGHLIGHT)])


        style.configure("TNotebook", background=COLOR_BG, borderwidth=0)
        style.configure("TNotebook.Tab", background=COLOR_FRAME, foreground=COLOR_TEXT, padding=[5, 2])
        style.map("TNotebook.Tab",
                  background=[("selected", COLOR_ACCENT), ("active", COLOR_FRAME)], # Highlight on active
                  foreground=[("selected", COLOR_BG if COLOR_BG != COLOR_TEXT else "white")]) # Ensure contrast


        style.configure("MainNotebook.TNotebook", background=COLOR_FRAME, borderwidth=0)
        style.configure("MainNotebook.TNotebook.Tab", background=COLOR_FRAME, foreground=COLOR_TEXT, padding=[10,5], font=('TkDefaultFont', 10, 'bold'))
        style.map("MainNotebook.TNotebook.Tab",
                  background=[("selected", COLOR_ACCENT), ("active", COLOR_HIGHLIGHT)],
                  foreground=[("selected", COLOR_BG if COLOR_BG != COLOR_TEXT else "white")])


        style.configure("TProgressbar", troughcolor=COLOR_FRAME, bordercolor=COLOR_BG, background=COLOR_ACCENT)
        
        style.configure("Sash", background=COLOR_ACCENT, borderwidth=2, relief=tk.RAISED)
        style.configure("Horizontal.Sash", background=COLOR_BG, borderwidth=0, lightcolor=COLOR_ACCENT, darkcolor=COLOR_ACCENT, gripcount=10)
        style.configure("Vertical.Sash", background=COLOR_BG, borderwidth=0, lightcolor=COLOR_ACCENT, darkcolor=COLOR_ACCENT, gripcount=10)

        # Style for ttk.Treeview
        style.configure("Treeview", 
                        background=COLOR_FRAME, 
                        foreground=COLOR_TEXT, 
                        fieldbackground=COLOR_FRAME, # Background of the data cells
                        rowheight=25) # Adjust row height if needed
        style.map("Treeview", 
                  background=[('selected', COLOR_ACCENT)],
                  foreground=[('selected', COLOR_BG if COLOR_BG != COLOR_TEXT else "white")])
        style.configure("Treeview.Heading", 
                        background=COLOR_ACCENT, 
                        foreground=COLOR_BG if COLOR_BG != COLOR_TEXT else "white", 
                        relief="flat", font=('TkDefaultFont', 10, 'bold'))
        style.map("Treeview.Heading",
                  background=[('active', COLOR_HIGHLIGHT)])


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