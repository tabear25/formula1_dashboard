import tkinter as tk
import fastf1
import fastf1.plotting
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
from config import COLOR_FRAME, COLOR_TEXT

def init_speed(notebook):
    frame = tk.Frame(notebook, bg=COLOR_FRAME)
    tk.Label(frame, text="🚥 速度比較", fg=COLOR_TEXT, bg=COLOR_FRAME).pack()
    notebook.add(frame, text="🚥 Speed Compare")
    return frame

def show_speed_compare(frame, session, drivers):
    if hasattr(frame, '_speed_canvas'):
        frame._speed_canvas.get_tk_widget().destroy()

    fastf1.plotting.setup_mpl(misc_mpl_mods=False, color_scheme='fastf1')
    fig = plt.Figure(figsize=(6,4), dpi=100, facecolor=COLOR_FRAME)
    ax = fig.add_subplot(111)

    for drv in drivers:
        lap = session.laps.pick_drivers(drv).pick_fastest()
        tel = lap.get_car_data().add_distance()
        style = fastf1.plotting.get_driver_style(identifier=drv,
                                                 style=['color','linestyle'],
                                                 session=session)
        ax.plot(tel['Distance'], tel['Speed'], label=drv, **style)

    ax.set_xlabel("Distance (m)")
    ax.set_ylabel("Speed (km/h)")
    ax.set_title(f"Speed Comparison – {session.event['EventName']} {session.event.year}",
                 color=COLOR_TEXT, fontsize=9)
    ax.legend(); ax.grid(color="#333333")
    ax.set_facecolor(COLOR_FRAME); fig.patch.set_facecolor(COLOR_FRAME)
    fig.tight_layout()

    canvas = FigureCanvasTkAgg(fig, master=frame)
    canvas.draw()
    canvas.get_tk_widget().pack(expand=True, fill="both")
    frame._speed_canvas = canvas
