import tkinter as tk
from tkinter import messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from config import COLOR_FRAME, COLOR_ACCENT, COLOR_HIGHLIGHT, COLOR_TEXT
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

        lap = session.laps.pick_driver(driver_abbreviation).pick_fastest()

        if lap is None or not hasattr(lap, 'Driver'):
            messagebox.showerror("データエラー",
                                 f"ドライバー {driver_abbreviation} の最速ラップが見つかりません。")
            tk.Label(frame,
                     text=f"{driver_abbreviation}\n最速ラップデータなし",
                     fg=COLOR_TEXT, bg=COLOR_FRAME).pack(expand=True)
            return

        try:
            tel = lap.get_car_data().add_distance()
            if tel is None or tel.empty:
                messagebox.showerror("データエラー",
                                     f"ドライバー {driver_abbreviation} のテレメトリデータが見つかりません。")
                tk.Label(frame,
                         text=f"{driver_abbreviation}\nテレメトリデータなし",
                         fg=COLOR_TEXT, bg=COLOR_FRAME).pack(expand=True)
                return
        except Exception as e:
            messagebox.showerror("データエラー",
                                 f"ドライバー {driver_abbreviation} のテレメトリ取得中にエラー: {e}")
            tk.Label(frame,
                     text=f"{driver_abbreviation}\nテレメトリ取得エラー",
                     fg=COLOR_TEXT, bg=COLOR_FRAME).pack(expand=True)
            return

        fig = plt.Figure(figsize=(6, 4), dpi=100, facecolor=COLOR_FRAME)
        ax = fig.add_subplot(111)
        ax.plot(tel['Distance'], tel['Speed'], color=COLOR_HIGHLIGHT, label=driver_abbreviation)
        ax.set_xlabel("Distance (m)", color=COLOR_TEXT)
        ax.set_ylabel("Speed (km/h)", color=COLOR_TEXT)
        ax.set_title(
            f"Fastest Lap Telemetry – {driver_abbreviation} – "
            f"{session.event['EventName']} {session.event.year}",
            color=COLOR_TEXT, fontsize=9,
        )

        leg = ax.legend()
        if leg:
            plt.setp(leg.get_texts(), color=COLOR_TEXT)
            leg.get_frame().set_facecolor(COLOR_FRAME)
            leg.get_frame().set_edgecolor(COLOR_TEXT)

        ax.grid(color="#333333")
        ax.set_facecolor(COLOR_FRAME)
        ax.tick_params(colors=COLOR_TEXT, which='both')
        for spine in ax.spines.values():
            spine.set_edgecolor(COLOR_TEXT)

        fig.patch.set_facecolor(COLOR_FRAME)
        fig.tight_layout()

        canvas = FigureCanvasTkAgg(fig, master=frame)
        canvas.draw()
        canvas.get_tk_widget().pack(expand=True, fill="both")

    show_chart_with_loader(
        frame,
        f"{driver_abbreviation} のテレメトリを読み込み中...",
        COLOR_FRAME, COLOR_ACCENT, _render,
    )
