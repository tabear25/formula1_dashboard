import math
import numpy as np
import tkinter as tk
from tkinter import messagebox
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

def _clear_frame_widgets(frame):
    for widget in frame.winfo_children():
        widget.destroy()

def show_map(frame, session):
    _clear_frame_widgets(frame) # Clear previous content, including error messages

    # 最速ラップと位置データ取得
    lap = session.laps.pick_fastest()
    
    if lap is None or not hasattr(lap, 'Driver'): # Check if lap is a valid Lap object
        messagebox.showerror("データエラー", "最速ラップが見つかりません。マップを表示できません。")
        tk.Label(frame, text="最速ラップデータなし", fg=COLOR_TEXT, bg=COLOR_FRAME).pack(expand=True)
        return

    try:
        pos = lap.get_pos_data()
        if pos is None or pos.empty:
            messagebox.showerror("データエラー", "最速ラップの位置データが見つかりません。マップを表示できません。")
            tk.Label(frame, text="位置データなし", fg=COLOR_TEXT, bg=COLOR_FRAME).pack(expand=True)
            return
    except Exception as e:
        messagebox.showerror("データエラー", f"位置データ取得中にエラーが発生しました: {e}")
        tk.Label(frame, text="位置データ取得エラー", fg=COLOR_TEXT, bg=COLOR_FRAME).pack(expand=True)
        return

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