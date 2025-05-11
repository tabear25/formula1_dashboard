import tkinter as tk
from tkinter import messagebox
import seaborn as sns
import pandas as pd
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
from config import COLOR_FRAME, COLOR_TEXT
import fastf1
import fastf1.plotting

def init_scatter(notebook): # This will be for multi-driver scatter comparison
    frame = tk.Frame(notebook, bg=COLOR_FRAME)
    # Label text will be updated by the specific show function or removed if init is generic
    notebook.add(frame, text="📊 Scatter Compare")
    return frame

def init_single_scatter(notebook): # New init for single driver scatter
    frame = tk.Frame(notebook, bg=COLOR_FRAME)
    notebook.add(frame, text="📈 Lap Scatter (Single)")
    return frame

def _clear_frame_widgets(frame):
    for widget in frame.winfo_children():
        widget.destroy()

def show_scatter_compare(frame, session, drivers): # For multiple drivers
    _clear_frame_widgets(frame)
    tk.Label(frame, text="📊 ラップタイム散布図比較 (複数ドライバー)", fg=COLOR_TEXT, bg=COLOR_FRAME).pack()

    if not drivers:
        tk.Label(frame, text="比較するドライバーを選択してください (最大4名)。", fg=COLOR_TEXT, bg=COLOR_FRAME).pack(expand=True)
        return

    laps_df = session.laps.pick_quicklaps().reset_index()
    if laps_df.empty:
        messagebox.showinfo("データなし", "比較対象のクイックラップが見つかりません。")
        tk.Label(frame, text="クイックラップデータなし", fg=COLOR_TEXT, bg=COLOR_FRAME).pack(expand=True)
        return

    # Ensure we only plot for drivers present in laps_df
    drivers_in_data = [d for d in drivers if d in laps_df['Driver'].unique()]
    if not drivers_in_data:
        messagebox.showinfo("データなし", f"選択されたドライバー ({', '.join(drivers)}) のクイックラップデータが見つかりません。")
        tk.Label(frame, text="選択ドライバーのデータなし", fg=COLOR_TEXT, bg=COLOR_FRAME).pack(expand=True)
        return
    
    # Use a copy to avoid SettingWithCopyWarning
    plot_drivers = drivers_in_data[:4]
    laps_to_plot_df = laps_df[laps_df['Driver'].isin(plot_drivers)].copy()
    
    # Convert LapTime to seconds for plotting if not already
    if 'LapTime' in laps_to_plot_df.columns and pd.api.types.is_timedelta64_dtype(laps_to_plot_df['LapTime']):
        laps_to_plot_df['LapTime_s'] = laps_to_plot_df['LapTime'].dt.total_seconds()
        y_axis_col = 'LapTime_s'
        y_axis_label = "Lap Time (s)"
    else: # If LapTime is already in a plottable format (e.g. seconds)
        y_axis_col = 'LapTime' 
        y_axis_label = "Lap Time"


    fig, axes = plt.subplots(2, 2, figsize=(8,6), facecolor=COLOR_FRAME)
    plt.subplots_adjust(hspace=0.4, wspace=0.3)

    compound_mapping = fastf1.plotting.get_compound_mapping(session=session, weekend=False) # weekend=False might be needed for older data

    for i, drv in enumerate(plot_drivers):
        ax = axes.flatten()[i]
        df_driver = laps_to_plot_df[laps_to_plot_df['Driver'] == drv]
        
        if df_driver.empty:
            ax.text(0.5, 0.5, f"{drv}\nNo Data", horizontalalignment='center', verticalalignment='center', transform=ax.transAxes, color=COLOR_TEXT)
            ax.set_facecolor(COLOR_FRAME)
            ax.tick_params(colors=COLOR_TEXT, which='both')
            for spine in ax.spines.values():
                spine.set_edgecolor(COLOR_TEXT)
            ax.set_title(drv, color=COLOR_TEXT, fontsize=8)
            continue

        sns.scatterplot(data=df_driver, x="LapNumber", y=y_axis_col,
                        hue="Compound",
                        palette=compound_mapping,
                        s=40, linewidth=0, ax=ax, legend=(i==0)) # Show legend only for the first plot
        
        if i==0 and ax.get_legend() is not None:
            leg = ax.get_legend()
            plt.setp(leg.get_texts(), color=COLOR_TEXT) # Legend text color
            leg.get_title().set_color(COLOR_TEXT)      # Legend title color
            leg.get_frame().set_facecolor(COLOR_FRAME) # Legend background
            leg.get_frame().set_edgecolor(COLOR_TEXT)  # Legend border

        ax.invert_yaxis()
        ax.set_title(drv, color=COLOR_TEXT, fontsize=8)
        ax.set_facecolor(COLOR_FRAME)
        ax.set_xlabel("Lap #", color=COLOR_TEXT); ax.set_ylabel(y_axis_label, color=COLOR_TEXT)
        ax.tick_params(colors=COLOR_TEXT, which='both')
        for spine in ax.spines.values():
            spine.set_edgecolor(COLOR_TEXT)


    # Hide unused subplots
    for j in range(len(plot_drivers), 4):
        axes.flatten()[j].axis('off')

    fig.patch.set_facecolor(COLOR_FRAME)
    # fig.suptitle(f"Laptime Scatter Comparison - {session.event.year} {session.event['EventName']}", color=COLOR_TEXT) # Optional super title
    fig.tight_layout(rect=[0, 0, 1, 0.96]) # Adjust layout to make space for suptitle if used

    canvas = FigureCanvasTkAgg(fig, master=frame)
    canvas.draw()
    canvas.get_tk_widget().pack(expand=True, fill="both")

def show_single_driver_scatter(frame, session, driver_abbreviation):
    _clear_frame_widgets(frame)
    tk.Label(frame, text=f"📊 ラップタイム散布図 ({driver_abbreviation})", fg=COLOR_TEXT, bg=COLOR_FRAME).pack()

    laps_df = session.laps.pick_driver(driver_abbreviation).pick_quicklaps().reset_index()

    if laps_df.empty:
        messagebox.showinfo("データなし", f"ドライバー {driver_abbreviation} のクイックラップが見つかりません。")
        tk.Label(frame, text=f"{driver_abbreviation}\nクイックラップデータなし", fg=COLOR_TEXT, bg=COLOR_FRAME).pack(expand=True)
        return

    # Use a copy to avoid SettingWithCopyWarning
    laps_to_plot_df = laps_df.copy()
    if 'LapTime' in laps_to_plot_df.columns and pd.api.types.is_timedelta64_dtype(laps_to_plot_df['LapTime']):
        laps_to_plot_df['LapTime_s'] = laps_to_plot_df['LapTime'].dt.total_seconds()
        y_axis_col = 'LapTime_s'
        y_axis_label = "Lap Time (s)"
    else:
        y_axis_col = 'LapTime'
        y_axis_label = "Lap Time"

    fig = plt.Figure(figsize=(7,5), dpi=100, facecolor=COLOR_FRAME)
    ax = fig.add_subplot(111)
    
    compound_mapping = fastf1.plotting.get_compound_mapping(session=session, weekend=False)

    sns.scatterplot(data=laps_to_plot_df, x="LapNumber", y=y_axis_col,
                    hue="Compound",
                    palette=compound_mapping,
                    s=50, linewidth=0, ax=ax, legend="auto")
    
    if ax.get_legend() is not None:
        leg = ax.get_legend()
        plt.setp(leg.get_texts(), color=COLOR_TEXT)
        leg.get_title().set_color(COLOR_TEXT)
        leg.get_frame().set_facecolor(COLOR_FRAME)
        leg.get_frame().set_edgecolor(COLOR_TEXT)


    ax.invert_yaxis()
    ax.set_title(f"{driver_abbreviation} - Lap Times - {session.event.year} {session.event['EventName']}", color=COLOR_TEXT, fontsize=10)
    ax.set_facecolor(COLOR_FRAME)
    ax.set_xlabel("Lap Number", color=COLOR_TEXT); ax.set_ylabel(y_axis_label, color=COLOR_TEXT)
    ax.grid(color="#444444", linestyle='--', linewidth=0.5)
    ax.tick_params(colors=COLOR_TEXT, which='both')
    for spine in ax.spines.values():
        spine.set_edgecolor(COLOR_TEXT)

    fig.tight_layout()
    canvas = FigureCanvasTkAgg(fig, master=frame)
    canvas.draw()
    canvas.get_tk_widget().pack(expand=True, fill="both")