import tkinter as tk
from tkinter import ttk
from ui.main_tab.tab_initializer import TabInitializer
from ui.main_tab.display_methods import _DisplayMethods

class MainTab(ttk.Notebook, TabInitializer, _DisplayMethods):
    def __init__(self, master: tk.Misc, **kw):
        super().__init__(master, **kw)
        self.configure(style="MainNotebook.TNotebook")

        # ─── タブ生成／初期化 ───
        self.init_overview()
        self.init_telemetry()
        self.init_map()
        self.init_compare()
        self.init_speed()
        self.init_scatter()

        # Canvas プロパティ（描画更新時に参照）
        self._map_canvas     = None
        self._compare_canvas = None
        self._speed_canvas   = None
        self._scatter_canvas = None
        self._telemetry_canvas = None