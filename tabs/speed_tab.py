import tkinter as tk
from tkinter import messagebox
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from config import COLOR_FRAME, COLOR_ACCENT, COLOR_TEXT
from core.charts import build_speed_fig, ChartDataError
from ui.animations import show_chart_with_loader


def init_speed(notebook):
    frame = tk.Frame(notebook, bg=COLOR_FRAME)
    notebook.add(frame, text="🏎️ Speed Compare")
    return frame


def _clear_frame_widgets(frame):
    for widget in frame.winfo_children():
        widget.destroy()


def show_speed_compare(frame, session, drivers):
    _clear_frame_widgets(frame)

    if not drivers:
        tk.Label(frame, text="比較するドライバーを選択してください。",
                 fg=COLOR_TEXT, bg=COLOR_FRAME).pack(expand=True)
        return

    def _render():
        tk.Label(frame, text="🚥 複数ドライバー速度比較", fg=COLOR_TEXT, bg=COLOR_FRAME).pack()

        try:
            fig = build_speed_fig(session, drivers)
        except ChartDataError as e:
            messagebox.showinfo("データなし", str(e))
            tk.Label(frame, text=str(e), fg=COLOR_TEXT, bg=COLOR_FRAME).pack(expand=True)
            return

        canvas = FigureCanvasTkAgg(fig, master=frame)
        canvas.draw()
        canvas.get_tk_widget().pack(expand=True, fill="both")

    show_chart_with_loader(frame, "速度比較を読み込み中...", COLOR_FRAME, COLOR_ACCENT, _render)
