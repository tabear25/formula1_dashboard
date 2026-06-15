import tkinter as tk
from tkinter import messagebox
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from config import COLOR_FRAME, COLOR_ACCENT, COLOR_TEXT
from core.charts import build_telemetry_fig, ChartDataError
from ui.animations import show_chart_with_loader


def init_telemetry(notebook):
    frame = tk.Frame(notebook, bg=COLOR_FRAME)
    notebook.add(frame, text="📈 Telemetry (Single)")
    return frame


def _clear_frame_widgets(frame):
    for widget in frame.winfo_children():
        widget.destroy()


def show_telemetry(frame, session, driver_list_one_elem):
    _clear_frame_widgets(frame)

    if not driver_list_one_elem or not driver_list_one_elem[0]:
        tk.Label(frame, text="表示するドライバーを選択してください。",
                 fg=COLOR_TEXT, bg=COLOR_FRAME).pack(expand=True)
        return

    driver_abbreviation = driver_list_one_elem[0]

    def _render():
        tk.Label(frame,
                 text=f"📈 {driver_abbreviation} 速度テレメトリ (最速ラップ)",
                 fg=COLOR_TEXT, bg=COLOR_FRAME).pack()

        try:
            fig = build_telemetry_fig(session, driver_abbreviation)
        except ChartDataError as e:
            messagebox.showerror("データエラー", str(e))
            tk.Label(frame, text=f"{driver_abbreviation}\n{e}",
                     fg=COLOR_TEXT, bg=COLOR_FRAME).pack(expand=True)
            return

        canvas = FigureCanvasTkAgg(fig, master=frame)
        canvas.draw()
        canvas.get_tk_widget().pack(expand=True, fill="both")

    show_chart_with_loader(
        frame,
        f"{driver_abbreviation} のテレメトリを読み込み中...",
        COLOR_FRAME, COLOR_ACCENT, _render,
    )
