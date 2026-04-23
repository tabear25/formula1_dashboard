import tkinter as tk
from config import COLOR_FRAME, COLOR_TEXT
from ui.animations import typewriter_effect


def init_overview(notebook):
    frame = tk.Frame(notebook, bg=COLOR_FRAME)
    text = (
        "🏁 F1 ダッシュボードへようこそ！\n\n"
        "左のサイドバーから年、グランプリ、セッションを選択してデータを読み込んでください。"
    )
    label = tk.Label(frame, text="", fg=COLOR_TEXT, bg=COLOR_FRAME,
                     justify=tk.LEFT, font=('TkDefaultFont', 12))
    label.pack(expand=True, padx=20, pady=20)
    notebook.add(frame, text="🏁 Overview")
    frame.after(300, lambda: typewriter_effect(label, text, delay=30))
    return frame


def show_overview(frame, message=None):
    for widget in frame.winfo_children():
        widget.destroy()

    if message is None:
        message = (
            "🏁 F1 ダッシュボードへようこそ！\n\n"
            "左のサイドバーから年、グランプリ、セッションを選択してデータを読み込んでください。"
        )

    label = tk.Label(frame, text="", fg=COLOR_TEXT, bg=COLOR_FRAME,
                     justify=tk.LEFT, font=('TkDefaultFont', 12))
    label.pack(expand=True, padx=20, pady=20)
    typewriter_effect(label, message, delay=30)
