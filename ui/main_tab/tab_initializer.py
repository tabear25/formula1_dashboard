import tkinter as tk
from config import COLOR_FRAME, COLOR_TEXT

class TabInitializer:
    """各タブの初期化メソッド群"""

    def init_overview(self):
        frame = tk.Frame(self, bg=COLOR_FRAME)
        tk.Label(frame, text="📂 データを読み込んでください",
                 fg=COLOR_TEXT, bg=COLOR_FRAME).pack(expand=True)
        self.add(frame, text="🏁 Overview")
        self.overview_frame = frame

    def init_map(self):
        frame = tk.Frame(self, bg=COLOR_FRAME)
        tk.Label(frame, text="🌐 サーキットマップ",
                 fg=COLOR_TEXT, bg=COLOR_FRAME).pack()
        self.add(frame, text="🗺️ Map")
        self.map_frame = frame

    def init_compare(self):
        frame = tk.Frame(self, bg=COLOR_FRAME)
        tk.Label(frame, text="👥 ドライバー比較",
                 fg=COLOR_TEXT, bg=COLOR_FRAME).pack()
        self.add(frame, text="👥 Compare")
        self.compare_frame = frame

    def init_speed(self):
        frame = tk.Frame(self, bg=COLOR_FRAME)
        tk.Label(frame, text="🚥 速度テレメトリ比較",
                 fg=COLOR_TEXT, bg=COLOR_FRAME).pack()
        self.add(frame, text="🚥 Speed Compare")
        self.speed_frame = frame

    def init_scatter(self):
        frame = tk.Frame(self, bg=COLOR_FRAME)
        tk.Label(frame, text="📊 ラップタイム散布図比較",
                 fg=COLOR_TEXT, bg=COLOR_FRAME).pack()
        self.add(frame, text="📊 Scatter Compare")
        self.scatter_frame = frame
