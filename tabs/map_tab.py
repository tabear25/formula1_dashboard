import math
import numpy as np
import tkinter as tk
import fastf1
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
from config import COLOR_FRAME, COLOR_HIGHLIGHT, COLOR_TEXT

def init_map(notebook):
    frame = tk.Frame(notebook, bg=COLOR_FRAME)
    tk.Label(frame, text="🌐 サーキットマップ",
             fg=COLOR_TEXT, bg=COLOR_FRAME).pack()
    notebook.add(frame, text="🗺️ Map")
    return frame

def show_map(frame, session):
    # 既存キャンバスがあれば破棄
    if hasattr(frame, '_map_canvas'):
        frame._map_canvas.get_tk_widget().destroy()

    # 最速ラップと位置データ取得
    lap = session.laps.pick_fastest()
    pos = lap.get_pos_data()
    cinfo = session.get_circuit_info()
    coords = pos.loc[:, ("X", "Y")].to_numpy()
    theta = cinfo.rotation / 180 * math.pi

    # 回転行列適用
    R = np.array([[math.cos(theta), -math.sin(theta)],
                  [math.sin(theta),  math.cos(theta)]])
    track = coords @ R

    # 描画
    fig = plt.Figure(figsize=(6,4), dpi=100, facecolor=COLOR_FRAME)
    ax = fig.add_subplot(111)
    ax.plot(track[:,0], track[:,1],
            color=COLOR_HIGHLIGHT, linewidth=2)

    # コーナー番号注記
    offset0 = np.array([500, 0])
    def _rot(pt, ang):
        return pt @ np.array([[math.cos(ang), -math.sin(ang)],
                              [math.sin(ang),  math.cos(ang)]])

    for _, corner in cinfo.corners.iterrows():
        txt    = f"{corner['Number']}{corner['Letter']}"
        ang_off= corner['Angle']/180*math.pi
        off    = _rot(offset0, ang_off)
        p_orig = np.array([corner['X'], corner['Y']])
        text_pt= _rot(p_orig + off, theta)
        track_pt=_rot(p_orig, theta)
        ax.scatter(text_pt[0], text_pt[1], color='grey', s=100)
        ax.plot([track_pt[0], text_pt[0]],
                [track_pt[1], text_pt[1]],
                color='grey')
        ax.text(text_pt[0], text_pt[1], txt,
                va='center_baseline', ha='center',
                color='white', fontsize=6)

    ax.set_title(f"{session.event['Location']} {session.event.year}",
                 color=COLOR_TEXT)
    ax.axis("equal"); ax.axis("off")
    fig.tight_layout()

    canvas = FigureCanvasTkAgg(fig, master=frame)
    canvas.draw()
    canvas.get_tk_widget().pack(expand=True, fill="both")
    frame._map_canvas = canvas
