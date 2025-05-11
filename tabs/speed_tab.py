import tkinter as tk
from tkinter import messagebox
import fastf1
import fastf1.plotting
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
from config import COLOR_FRAME, COLOR_TEXT

def init_speed(notebook):
    frame = tk.Frame(notebook, bg=COLOR_FRAME)
    # Label text will be updated by the specific show function or removed if init is generic
    notebook.add(frame, text="🏎️ Speed Compare") # Changed tab text
    return frame

def _clear_frame_widgets(frame):
    for widget in frame.winfo_children():
        widget.destroy()

def show_speed_compare(frame, session, drivers):
    _clear_frame_widgets(frame)
    tk.Label(frame, text="🚥 複数ドライバー速度比較", fg=COLOR_TEXT, bg=COLOR_FRAME).pack()

    if not drivers:
        tk.Label(frame, text="比較するドライバーを選択してください。", fg=COLOR_TEXT, bg=COLOR_FRAME).pack(expand=True)
        return

    # fastf1.plotting.setup_mpl(misc_mpl_mods=False, color_scheme='fastf1') # Moved to main or apply selectively
    # Applying FastF1 styles can be good, but ensure it's what's desired globally or apply locally.
    # For now, we rely on get_driver_style which should work fine.

    fig = plt.Figure(figsize=(6,4), dpi=100, facecolor=COLOR_FRAME)
    ax = fig.add_subplot(111)
    
    at_least_one_driver_plotted = False
    for drv in drivers:
        lap = session.laps.pick_driver(drv).pick_fastest()
        if lap is None or not hasattr(lap, 'Driver'):
            print(f"ドライバー {drv} の最速ラップが見つかりません。スキップします。") # Log or show in UI status
            continue
        
        try:
            tel = lap.get_car_data().add_distance()
            if tel is None or tel.empty:
                print(f"ドライバー {drv} のテレメトリデータが見つかりません。スキップします。")
                continue
        except Exception as e:
            print(f"ドライバー {drv} のテレメトリ取得エラー: {e}")
            continue

        style = fastf1.plotting.get_driver_style(identifier=drv,
                                                 style=['color','linestyle'], # Removed 'marker' as it's not used by default in line plot
                                                 session=session)
        ax.plot(tel['Distance'], tel['Speed'], label=drv, **style)
        at_least_one_driver_plotted = True

    if not at_least_one_driver_plotted:
        messagebox.showinfo("データなし", "選択されたドライバーの有効なテレメトリデータが見つかりませんでした。")
        tk.Label(frame, text="有効なテレメトリデータなし", fg=COLOR_TEXT, bg=COLOR_FRAME).pack(expand=True)
        plt.close(fig)
        return

    ax.set_xlabel("Distance (m)", color=COLOR_TEXT)
    ax.set_ylabel("Speed (km/h)", color=COLOR_TEXT)
    ax.set_title(f"Fastest Lap Speed Comparison – {session.event['EventName']} {session.event.year}",
                 color=COLOR_TEXT, fontsize=9)
    
    leg = ax.legend()
    if leg:
        plt.setp(leg.get_texts(), color=COLOR_TEXT)
        leg.get_frame().set_facecolor(COLOR_FRAME)
        leg.get_frame().set_edgecolor(COLOR_TEXT)

    ax.grid(color="#333333")
    ax.set_facecolor(COLOR_FRAME); fig.patch.set_facecolor(COLOR_FRAME)
    ax.tick_params(colors=COLOR_TEXT, which='both')
    for spine in ax.spines.values():
        spine.set_edgecolor(COLOR_TEXT)
    fig.tight_layout()

    canvas = FigureCanvasTkAgg(fig, master=frame)
    canvas.draw()
    canvas.get_tk_widget().pack(expand=True, fill="both")