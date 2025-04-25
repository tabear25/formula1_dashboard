import tkinter as tk
from config import COLOR_FRAME, COLOR_TEXT

def init_overview(notebook):
    frame = tk.Frame(notebook, bg=COLOR_FRAME)
    tk.Label(frame,
             text="📂 データを読み込んでください",
             fg=COLOR_TEXT, bg=COLOR_FRAME).pack(expand=True)
    notebook.add(frame, text="🏁 Overview")
    return frame

def show_overview(frame, *args, **kwargs):
    # 既存ウィジェットをクリアして再表示
    for widget in frame.winfo_children():
        widget.destroy()
    tk.Label(frame,
             text="📂 データを読み込んでください",
             fg=COLOR_TEXT, bg=COLOR_FRAME).pack(expand=True)
