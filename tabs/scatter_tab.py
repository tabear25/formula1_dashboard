import tkinter as tk
import seaborn as sns
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
from config import COLOR_FRAME, COLOR_TEXT
import fastf1
import fastf1.plotting

def init_scatter(notebook):
    frame = tk.Frame(notebook, bg=COLOR_FRAME)
    tk.Label(frame, text="📊 ラップタイム散布図比較", fg=COLOR_TEXT, bg=COLOR_FRAME).pack()
    notebook.add(frame, text="📊 Scatter Compare")
    return frame

def show_scatter_compare(frame, session, drivers):
    if hasattr(frame, '_scatter_canvas'):
        frame._scatter_canvas.get_tk_widget().destroy()

    laps_df = session.laps.pick_quicklaps().reset_index()
    fig, axes = plt.subplots(2, 2, figsize=(8,6), facecolor=COLOR_FRAME)
    plt.subplots_adjust(hspace=0.4, wspace=0.3)

    for i, drv in enumerate(drivers[:4]):
        ax = axes.flatten()[i]
        df = laps_df[laps_df['Driver']==drv]
        sns.scatterplot(data=df, x="LapNumber", y="LapTime",
                        hue="Compound",
                        palette=fastf1.plotting.get_compound_mapping(session=session),
                        s=40, linewidth=0, ax=ax, legend=False)
        ax.invert_yaxis()
        ax.set_title(drv, color=COLOR_TEXT, fontsize=8)
        ax.set_facecolor(COLOR_FRAME)
        ax.set_xlabel("Lap #"); ax.set_ylabel("Lap Time")
        for spine in ax.spines.values():
            spine.set_visible(False)

    # 空プロットを非表示
    for j in range(len(drivers), 4):
        axes.flatten()[j].axis('off')

    fig.patch.set_facecolor(COLOR_FRAME)
    canvas = FigureCanvasTkAgg(fig, master=frame)
    canvas.draw()
    canvas.get_tk_widget().pack(expand=True, fill="both")
    frame._scatter_canvas = canvas
