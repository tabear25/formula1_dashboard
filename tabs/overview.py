import tkinter as tk
from config import COLOR_FRAME, COLOR_TEXT

"""
起動画面の設定
"""

def init_overview(notebook):
    frame = tk.Frame(notebook, bg=COLOR_FRAME)
    tk.Label(frame,
             text="🏁 F1 ダッシュボードへようこそ！\n\n左のサイドバーから年、グランプリ、セッションを選択してデータを読み込んでください。",
             fg=COLOR_TEXT, bg=COLOR_FRAME, justify=tk.LEFT, font=('TkDefaultFont', 12)).pack(expand=True, padx=20, pady=20)
    notebook.add(frame, text="🏁 Overview")
    return frame

def show_overview(frame, message=None): 
    for widget in frame.winfo_children():
        widget.destroy()
    
    if message is None:
        message = "🏁 F1 ダッシュボードへようこそ！\n\n左のサイドバーから年、グランプリ、セッションを選択してデータを読み込んでください。"
        
    tk.Label(frame,
             text=message,
             fg=COLOR_TEXT, bg=COLOR_FRAME, justify=tk.LEFT, font=('TkDefaultFont', 12)).pack(expand=True, padx=20, pady=20)