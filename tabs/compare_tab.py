import tkinter as tk
from tkinter import messagebox
import pandas as pd
import seaborn as sns
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import fastf1
import fastf1.plotting
import matplotlib.pyplot as plt
from config import COLOR_FRAME, COLOR_ACCENT, COLOR_HIGHLIGHT, COLOR_TEXT
from ui.animations import show_chart_with_loader


def init_compare(notebook):
    frame = tk.Frame(notebook, bg=COLOR_FRAME)
    tk.Label(frame, text="👥 ドライバーラップタイム比較", fg=COLOR_TEXT, bg=COLOR_FRAME).pack()
    notebook.add(frame, text="📊 LapTime Compare")
    return frame


def _clear_frame_widgets(frame):
    for widget in frame.winfo_children():
        widget.destroy()


def show_compare(frame, session, drivers):
    _clear_frame_widgets(frame)

    if not drivers:
        tk.Label(frame, text="比較するドライバーを選択してください。",
                 fg=COLOR_TEXT, bg=COLOR_FRAME).pack(expand=True)
        return

    def _render():
        laps_df = session.laps.pick_quicklaps().reset_index()

        if laps_df.empty:
            messagebox.showinfo("データなし", "比較対象のクイックラップが見つかりません。")
            tk.Label(frame, text="クイックラップデータなし", fg=COLOR_TEXT, bg=COLOR_FRAME).pack(expand=True)
            return

        df = laps_df[laps_df['Driver'].isin(drivers)].copy()

        if df.empty:
            messagebox.showinfo("データなし",
                                f"選択されたドライバー ({', '.join(drivers)}) のクイックラップが見つかりません。")
            tk.Label(frame, text="選択ドライバーのデータなし", fg=COLOR_TEXT, bg=COLOR_FRAME).pack(expand=True)
            return

        df['LapTime_s'] = df['LapTime'].dt.total_seconds()

        fig = plt.Figure(figsize=(6, 4), dpi=100, facecolor=COLOR_FRAME)
        ax = fig.add_subplot(111)

        palette = {drv: COLOR_ACCENT for drv in drivers}

        sns.violinplot(data=df, x='Driver', y='LapTime_s', hue='Driver',
                       inner='quartile', cut=0, ax=ax,
                       order=drivers, hue_order=drivers,
                       palette=palette, legend=False)

        medians_series = df.groupby('Driver')['LapTime_s'].median()
        valid_drivers = [d for d in drivers if d in medians_series and pd.notna(medians_series.get(d))]
        valid_medians = [medians_series.get(d) for d in valid_drivers]
        x_coords = [drivers.index(d) for d in valid_drivers]

        if x_coords:
            ax.plot(x_coords, valid_medians, marker='o', linestyle='--', color=COLOR_HIGHLIGHT)

        ax.invert_yaxis()
        ax.set_xlabel("Driver")
        ax.set_ylabel("LapTime (s)")
        ax.set_title(
            f"LapTime Comparison – {session.event['EventName']} {session.event.year}",
            color=COLOR_TEXT, fontsize=9,
        )
        ax.grid(color="#333333")
        ax.set_facecolor(COLOR_FRAME)
        fig.patch.set_facecolor(COLOR_FRAME)
        ax.tick_params(colors=COLOR_TEXT, which='both')
        ax.xaxis.label.set_color(COLOR_TEXT)
        ax.yaxis.label.set_color(COLOR_TEXT)
        for spine in ax.spines.values():
            spine.set_edgecolor(COLOR_TEXT)
        fig.tight_layout()

        canvas = FigureCanvasTkAgg(fig, master=frame)
        canvas.draw()
        canvas.get_tk_widget().pack(expand=True, fill="both")

    show_chart_with_loader(frame, "ラップタイム比較を読み込み中...", COLOR_FRAME, COLOR_ACCENT, _render)
