import tkinter as tk
from tkinter import messagebox
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from config import COLOR_FRAME, COLOR_ACCENT, COLOR_TEXT
from core.charts import build_scatter_compare_fig, build_scatter_single_fig, ChartDataError
from ui.animations import show_chart_with_loader


def init_scatter(notebook):
    frame = tk.Frame(notebook, bg=COLOR_FRAME)
    notebook.add(frame, text="📊 Scatter Compare")
    return frame


def init_single_scatter(notebook):
    frame = tk.Frame(notebook, bg=COLOR_FRAME)
    notebook.add(frame, text="📈 Lap Scatter (Single)")
    return frame


def _clear_frame_widgets(frame):
    for widget in frame.winfo_children():
        widget.destroy()


def show_scatter_compare(frame, session, drivers):
    _clear_frame_widgets(frame)

    if not drivers:
        tk.Label(frame, text="比較するドライバーを選択してください (最大4名)。",
                 fg=COLOR_TEXT, bg=COLOR_FRAME).pack(expand=True)
        return

    def _render():
        tk.Label(frame, text="📊 ラップタイム散布図比較 (複数ドライバー)",
                 fg=COLOR_TEXT, bg=COLOR_FRAME).pack()

        try:
            fig = build_scatter_compare_fig(session, drivers)
        except ChartDataError as e:
            messagebox.showinfo("データなし", str(e))
            tk.Label(frame, text=str(e), fg=COLOR_TEXT, bg=COLOR_FRAME).pack(expand=True)
            return

        canvas = FigureCanvasTkAgg(fig, master=frame)
        canvas.draw()
        canvas.get_tk_widget().pack(expand=True, fill="both")

    show_chart_with_loader(frame, "散布図比較を読み込み中...", COLOR_FRAME, COLOR_ACCENT, _render)


def show_single_driver_scatter(frame, session, driver_abbreviation):
    _clear_frame_widgets(frame)

    def _render():
        tk.Label(frame, text=f"📊 ラップタイム散布図 ({driver_abbreviation})",
                 fg=COLOR_TEXT, bg=COLOR_FRAME).pack()

        try:
            fig = build_scatter_single_fig(session, driver_abbreviation)
        except ChartDataError as e:
            messagebox.showinfo("データなし", str(e))
            tk.Label(frame, text=f"{driver_abbreviation}\n{e}",
                     fg=COLOR_TEXT, bg=COLOR_FRAME).pack(expand=True)
            return

        canvas = FigureCanvasTkAgg(fig, master=frame)
        canvas.draw()
        canvas.get_tk_widget().pack(expand=True, fill="both")

    show_chart_with_loader(
        frame,
        f"{driver_abbreviation} のラップ散布図を読み込み中...",
        COLOR_FRAME, COLOR_ACCENT, _render,
    )
