import tkinter as tk
from tkinter import messagebox
import seaborn as sns
import pandas as pd
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from config import COLOR_FRAME, COLOR_ACCENT, COLOR_TEXT
import fastf1
import fastf1.plotting
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

        laps_df = session.laps.pick_quicklaps().reset_index()
        if laps_df.empty:
            messagebox.showinfo("データなし", "比較対象のクイックラップが見つかりません。")
            tk.Label(frame, text="クイックラップデータなし", fg=COLOR_TEXT, bg=COLOR_FRAME).pack(expand=True)
            return

        drivers_in_data = [d for d in drivers if d in laps_df['Driver'].unique()]
        if not drivers_in_data:
            messagebox.showinfo("データなし",
                                f"選択されたドライバー ({', '.join(drivers)}) のクイックラップデータが見つかりません。")
            tk.Label(frame, text="選択ドライバーのデータなし", fg=COLOR_TEXT, bg=COLOR_FRAME).pack(expand=True)
            return

        plot_drivers = drivers_in_data[:4]
        laps_to_plot = laps_df[laps_df['Driver'].isin(plot_drivers)].copy()

        if pd.api.types.is_timedelta64_dtype(laps_to_plot.get('LapTime', pd.Series())):
            laps_to_plot['LapTime_s'] = laps_to_plot['LapTime'].dt.total_seconds()
            y_col, y_label = 'LapTime_s', "Lap Time (s)"
        else:
            y_col, y_label = 'LapTime', "Lap Time"

        fig = plt.Figure(figsize=(8, 6), facecolor=COLOR_FRAME)
        axes = fig.subplots(2, 2)
        fig.subplots_adjust(hspace=0.4, wspace=0.3)

        compound_mapping = fastf1.plotting.get_compound_mapping(session)

        for i, drv in enumerate(plot_drivers):
            ax = axes.flatten()[i]
            df_drv = laps_to_plot[laps_to_plot['Driver'] == drv]

            if df_drv.empty:
                ax.text(0.5, 0.5, f"{drv}\nNo Data",
                        ha='center', va='center', transform=ax.transAxes, color=COLOR_TEXT)
            else:
                sns.scatterplot(data=df_drv, x="LapNumber", y=y_col,
                                hue="Compound", palette=compound_mapping,
                                s=40, linewidth=0, ax=ax, legend=False)

                ax.invert_yaxis()
                ax.set_xlabel("Lap #", color=COLOR_TEXT)
                ax.set_ylabel(y_label, color=COLOR_TEXT)

            ax.set_title(drv, color=COLOR_TEXT, fontsize=8)
            ax.set_facecolor(COLOR_FRAME)
            ax.tick_params(colors=COLOR_TEXT, which='both')
            for spine in ax.spines.values():
                spine.set_edgecolor(COLOR_TEXT)

        for j in range(len(plot_drivers), 4):
            axes.flatten()[j].axis('off')

        # 各サブプロットに凡例を出すとドライバーごとに使用コンパウンドが
        # 異なり不完全になるため、全パネル共通の凡例を figure 単位で1つ表示する。
        compound_order = ['SOFT', 'MEDIUM', 'HARD', 'INTERMEDIATE', 'WET']
        compounds_present = sorted(
            (c for c in laps_to_plot['Compound'].dropna().unique()),
            key=lambda c: compound_order.index(c) if c in compound_order else len(compound_order),
        )
        if compounds_present:
            handles = [
                Line2D([0], [0], marker='o', linestyle='', markersize=7,
                       markerfacecolor=compound_mapping.get(c, COLOR_TEXT),
                       markeredgecolor='none', label=c)
                for c in compounds_present
            ]
            leg = fig.legend(handles=handles, title="Compound",
                             loc='upper center', ncol=len(handles), fontsize=8,
                             facecolor=COLOR_FRAME, edgecolor=COLOR_TEXT)
            plt.setp(leg.get_texts(), color=COLOR_TEXT)
            leg.get_title().set_color(COLOR_TEXT)

        fig.patch.set_facecolor(COLOR_FRAME)
        fig.tight_layout(rect=[0, 0, 1, 0.92])

        canvas = FigureCanvasTkAgg(fig, master=frame)
        canvas.draw()
        canvas.get_tk_widget().pack(expand=True, fill="both")

    show_chart_with_loader(frame, "散布図比較を読み込み中...", COLOR_FRAME, COLOR_ACCENT, _render)


def show_single_driver_scatter(frame, session, driver_abbreviation):
    _clear_frame_widgets(frame)

    def _render():
        tk.Label(frame, text=f"📊 ラップタイム散布図 ({driver_abbreviation})",
                 fg=COLOR_TEXT, bg=COLOR_FRAME).pack()

        laps_df = session.laps.pick_drivers(driver_abbreviation).pick_quicklaps().reset_index()

        if laps_df.empty:
            messagebox.showinfo("データなし",
                                f"ドライバー {driver_abbreviation} のクイックラップが見つかりません。")
            tk.Label(frame, text=f"{driver_abbreviation}\nクイックラップデータなし",
                     fg=COLOR_TEXT, bg=COLOR_FRAME).pack(expand=True)
            return

        laps_to_plot = laps_df.copy()
        if pd.api.types.is_timedelta64_dtype(laps_to_plot.get('LapTime', pd.Series())):
            laps_to_plot['LapTime_s'] = laps_to_plot['LapTime'].dt.total_seconds()
            y_col, y_label = 'LapTime_s', "Lap Time (s)"
        else:
            y_col, y_label = 'LapTime', "Lap Time"

        fig = plt.Figure(figsize=(7, 5), dpi=100, facecolor=COLOR_FRAME)
        ax = fig.add_subplot(111)

        compound_mapping = fastf1.plotting.get_compound_mapping(session)

        sns.scatterplot(data=laps_to_plot, x="LapNumber", y=y_col,
                        hue="Compound", palette=compound_mapping,
                        s=50, linewidth=0, ax=ax, legend="auto")

        if ax.get_legend() is not None:
            leg = ax.get_legend()
            plt.setp(leg.get_texts(), color=COLOR_TEXT)
            leg.get_title().set_color(COLOR_TEXT)
            leg.get_frame().set_facecolor(COLOR_FRAME)
            leg.get_frame().set_edgecolor(COLOR_TEXT)

        ax.invert_yaxis()
        ax.set_title(
            f"{driver_abbreviation} - Lap Times - {session.event.year} {session.event['EventName']}",
            color=COLOR_TEXT, fontsize=10,
        )
        ax.set_facecolor(COLOR_FRAME)
        ax.set_xlabel("Lap Number", color=COLOR_TEXT)
        ax.set_ylabel(y_label, color=COLOR_TEXT)
        ax.grid(color="#444444", linestyle='--', linewidth=0.5)
        ax.tick_params(colors=COLOR_TEXT, which='both')
        for spine in ax.spines.values():
            spine.set_edgecolor(COLOR_TEXT)

        fig.tight_layout()
        canvas = FigureCanvasTkAgg(fig, master=frame)
        canvas.draw()
        canvas.get_tk_widget().pack(expand=True, fill="both")

    show_chart_with_loader(
        frame,
        f"{driver_abbreviation} のラップ散布図を読み込み中...",
        COLOR_FRAME, COLOR_ACCENT, _render,
    )
