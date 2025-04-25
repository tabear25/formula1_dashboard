import tkinter as tk
import pandas as pd
import seaborn as sns
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import fastf1
import fastf1.plotting
import matplotlib.pyplot as plt
from config import COLOR_FRAME, COLOR_ACCENT, COLOR_HIGHLIGHT, COLOR_TEXT

def init_compare(notebook):
    frame = tk.Frame(notebook, bg=COLOR_FRAME)
    tk.Label(frame, text="👥 ドライバー比較", fg=COLOR_TEXT, bg=COLOR_FRAME).pack()
    notebook.add(frame, text="👥 Compare")
    return frame

def show_compare(frame, session, drivers):
    # 前回のキャンバスをクリア
    if hasattr(frame, '_compare_canvas'):
        frame._compare_canvas.get_tk_widget().destroy()

    laps_df = session.laps.pick_quicklaps().reset_index()
    df = laps_df[laps_df['Driver'].isin(drivers)].copy()
    df['LapTime_s'] = df['LapTime'].dt.total_seconds()

    fig = plt.Figure(figsize=(6,4), dpi=100, facecolor=COLOR_FRAME)
    ax = fig.add_subplot(111)
    sns.violinplot(data=df, x='Driver', y='LapTime_s',
                   inner='quartile', cut=0, ax=ax,
                   palette=[COLOR_ACCENT]*len(drivers))
    meds = df.groupby('Driver')['LapTime_s'].median()
    ax.plot(range(len(drivers)), meds.values,
            marker='o', linestyle='--',
            color=COLOR_HIGHLIGHT)

    ax.invert_yaxis()
    ax.set_xlabel("Driver"); ax.set_ylabel("LapTime (s)")
    ax.set_title(f"LapTime Comparison – {session.event['EventName']} {session.event.year}",
                 color=COLOR_TEXT, fontsize=9)
    ax.grid(color="#333333")
    ax.set_facecolor(COLOR_FRAME); fig.patch.set_facecolor(COLOR_FRAME)
    fig.tight_layout()

    canvas = FigureCanvasTkAgg(fig, master=frame)
    canvas.draw()
    canvas.get_tk_widget().pack(expand=True, fill="both")
    frame._compare_canvas = canvas