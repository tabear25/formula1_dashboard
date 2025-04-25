import tkinter as tk
import matplotlib.pyplot as plt
import numpy as np
import fastf1
from fastf1 import plotting
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from config import COLOR_FRAME, COLOR_HIGHLIGHT, COLOR_TEXT

def init_telemetry(notebook):
    frame = tk.Frame(notebook, bg=COLOR_FRAME)
    tk.Label(frame, text="📈 速度テレメトリ", fg=COLOR_TEXT, bg=COLOR_FRAME).pack()
    notebook.add(frame, text="📈 Telemetry")
    return frame

def show_telemetry(frame, session, driver):
    # 前回のキャンバスをクリア
    if hasattr(frame, "_telemetry_canvas"):
        frame._telemetry_canvas.get_tk_widget().destroy()

    # テレメトリデータ取得
    lap = session.laps.pick_drivers(driver[0]).pick_fastest()
    tel = lap.get_car_data().add_distance()

    # プロット
    fig = plt.Figure(figsize=(6, 4), dpi=100, facecolor=COLOR_FRAME)
    ax  = fig.add_subplot(111)
    ax.plot(tel['Distance'], tel['Speed'], color=COLOR_HIGHLIGHT)
    ax.set_xlabel("Distance (m)")
    ax.set_ylabel("Speed (km/h)")
    ax.set_title(
        f"Telemetry – {driver[0]} – {session.event['EventName']} {session.event.year}",
        color=COLOR_TEXT, fontsize=9
    )
    ax.grid(color="#333333")
    ax.set_facecolor(COLOR_FRAME)
    fig.patch.set_facecolor(COLOR_FRAME)
    fig.tight_layout()

    # キャンバス表示
    canvas = FigureCanvasTkAgg(fig, master=frame)
    canvas.draw()
    canvas.get_tk_widget().pack(expand=True, fill="both")

    # 再描画のために保持
    frame._telemetry_canvas = canvas
