import tkinter as tk
from tkinter import messagebox
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from config import COLOR_FRAME, COLOR_ACCENT, COLOR_TEXT
from core.charts import build_map_fig, ChartDataError
from ui.animations import show_chart_with_loader


def init_map(notebook):
    frame = tk.Frame(notebook, bg=COLOR_FRAME)
    tk.Label(frame, text="🌐 サーキットマップ",
             fg=COLOR_TEXT, bg=COLOR_FRAME).pack()
    notebook.add(frame, text="🗺️ Map")
    return frame


def _clear_frame_widgets(frame):
    for widget in frame.winfo_children():
        widget.destroy()


def show_map(frame, session):
    _clear_frame_widgets(frame)

    def _render():
        try:
            fig = build_map_fig(session)
        except ChartDataError as e:
            messagebox.showerror("データエラー", str(e))
            tk.Label(frame, text=str(e), fg=COLOR_TEXT, bg=COLOR_FRAME).pack(expand=True)
            return

        canvas = FigureCanvasTkAgg(fig, master=frame)
        canvas.draw()
        canvas.get_tk_widget().pack(expand=True, fill="both")

    show_chart_with_loader(frame, "サーキットマップを読み込み中...", COLOR_FRAME, COLOR_ACCENT, _render)
