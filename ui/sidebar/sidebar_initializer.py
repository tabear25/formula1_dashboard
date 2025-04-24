import tkinter as tk
from tkinter import ttk, messagebox, font as tkfont
from config import COLOR_FRAME, COLOR_TEXT, YEAR_LIST

class SidebarInitializer:
    """Sidebar のウィジェット生成・レイアウト定義"""

    def build_widgets(self):
        # フレーム背景
        self.configure(bg=COLOR_FRAME)

        # フォント設定
        font = tkfont.nametofont("TkDefaultFont")
        font.configure(size=10, weight="bold")

        # 年度ラベル＆リスト
        tk.Label(self, text="開催年", bg=COLOR_FRAME, fg=COLOR_TEXT) \
          .pack(anchor="w", padx=10, pady=5)
        self.year_var = tk.IntVar(value=YEAR_LIST[-1])
        self.year_lb = tk.Listbox(
            self,
            listvariable=tk.StringVar(value=YEAR_LIST),
            height=10
        )
        self.year_lb.pack(fill="x", padx=10)
        self.year_lb.bind("<<ListboxSelect>>", self.on_year)

        # GP選択
        tk.Label(self, text="グランプリ", bg=COLOR_FRAME, fg=COLOR_TEXT) \
          .pack(anchor="w", padx=10, pady=5)
        self.gp_var = tk.StringVar()
        self.gp_lb = tk.Listbox(self, listvariable=tk.StringVar(value=[]), height=12)
        self.gp_lb.pack(fill="x", padx=10)
        self.gp_lb.bind("<<ListboxSelect>>", self.on_gp)

        # セッション選択
        tk.Label(self, text="セッション", bg=COLOR_FRAME, fg=COLOR_TEXT) \
          .pack(anchor="w", padx=10, pady=5)
        self.ses_var = tk.StringVar()
        self.ses_cmb = ttk.Combobox(
            self,
            textvariable=self.ses_var,
            state="readonly",
            values=["FP1", "FP2", "FP3", "Q", "R"]
        )
        self.ses_cmb.pack(fill="x", padx=10)
        self.ses_cmb.bind("<<ComboboxSelected>>", self.on_ses)

        # ドライバー選択
        tk.Label(self, text="ドライバー (最大4)", bg=COLOR_FRAME, fg=COLOR_TEXT) \
          .pack(anchor="w", padx=10, pady=5)
        self.drv_lb = tk.Listbox(self, selectmode="multiple", height=8)
        self.drv_lb.pack(fill="x", padx=10)

        # ボタン群
        btns = [
            ("速度テレメトリ表示", self.show_speed),
            ("ラップタイム散布図", self.show_scatter),
            ("複数ドライバー比較", self.show_compare),
            ("速度テレメトリ比較", self.show_speed_compare),
            ("散布図比較", self.show_scatter_compare),
        ]
        for txt, cmd in btns:
            ttk.Button(self, text=txt, command=cmd) \
               .pack(fill="x", padx=10, pady=3)

        # プログレスバー
        self.progress = ttk.Progressbar(self, mode="indeterminate")
        self.progress.pack(fill="x", padx=10, pady=10)
        self.messagebox = messagebox.Message(
            master=self, title="メッセージ", icon="info",
            message="情報の読み込みが完了しました"
        )
