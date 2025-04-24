import math
import numpy as np
import matplotlib.pyplot as plt
import fastf1
import fastf1.plotting
import seaborn as sns
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from config import COLOR_FRAME, COLOR_HIGHLIGHT, COLOR_TEXT, COLOR_ACCENT

class _DisplayMethods:
    """各タブの描画メソッド群"""
    def show_map(self, session):
        if getattr(self, "_map_canvas", None):
            self._map_canvas.get_tk_widget().destroy()
        lap    = session.laps.pick_fastest()
        pos    = lap.get_pos_data()
        cinfo  = session.get_circuit_info()
        coords = pos.loc[:, ("X", "Y")].to_numpy()
        θ      = cinfo.rotation / 180 * math.pi

        R = np.array([[math.cos(θ), -math.sin(θ)],
                      [math.sin(θ),  math.cos(θ)]])
        track = coords @ R

        fig = plt.Figure(figsize=(6,4), dpi=100,
                         facecolor=COLOR_FRAME)
        ax  = fig.add_subplot(111)
        ax.plot(track[:,0], track[:,1],
                color=COLOR_HIGHLIGHT, linewidth=2)

        # コーナー注記
        base_off = np.array([500, 0])
        def _rot(pt, ang):
            return pt @ np.array([
                [math.cos(ang), -math.sin(ang)],
                [math.sin(ang),  math.cos(ang)]
            ])

        for _, corner in cinfo.corners.iterrows():
            txt    = f"{corner['Number']}{corner['Letter']}"
            ang_off= corner['Angle']/180*math.pi
            off    = _rot(base_off, ang_off)
            p_orig = np.array([corner['X'], corner['Y']])
            t_pt   = _rot(p_orig + off, θ)
            c_pt   = _rot(p_orig, θ)
            ax.scatter(*t_pt, color='grey', s=100)
            ax.plot([c_pt[0], t_pt[0]], [c_pt[1], t_pt[1]],
                    color='grey')
            ax.text(*t_pt, txt,
                    va='center_baseline',
                    ha='center', color='white',
                    fontsize=6)

        ax.set_title(f"{session.event['Location']} {session.event.year}",
                     color=COLOR_TEXT)
        ax.axis("equal"); ax.axis("off")
        fig.tight_layout()

        self._map_canvas = FigureCanvasTkAgg(fig,
                                             master=self.map_frame)
        self._map_canvas.draw()
        self._map_canvas.get_tk_widget().pack(
            expand=True, fill="both")

    # 単独でのテレメトリデータを追加することのできるロジックを追加する
    """
    def show_telemetry(self, session, driver: list[str]):
        if getattr(self, "_telemetry_canvas", None):
            self._telemetry_canvas.get_tk_widget().destroy()
        laps_df = session.laps.pick_quicklaps().reset_index()
        df      = laps_df[laps_df['Driver'].isin(driver)].copy()
        df['LapTime_s'] = df['LapTime'].dt.total_seconds()

        fig = plt.Figure(figsize=(6,4), dpi=100,
                         facecolor=COLOR_FRAME)
        ax  = fig.add_subplot(111)
        sns.violinplot(data=df, x='Driver', y='LapTime_s',
                       inner='quartile', cut=0, ax=ax,
                       palette=[COLOR_ACCENT]*len(drivers))
        meds = df.groupby('Driver')['LapTime_s'].median()
        ax.plot(range(len(drivers)), meds.values,
                marker='o', linestyle='--',
                color=COLOR_HIGHLIGHT)

        ax.invert_yaxis()
        ax.set_xlabel("Driver"); ax.set_ylabel("LapTime (s)")
        ax.set_title(
            f"LapTime Comparison – {session.event['EventName']} {session.event.year}",
            color=COLOR_TEXT, fontsize=9
        )
        ax.grid(color="#333333")
        ax.set_facecolor(COLOR_FRAME)
        fig.patch.set_facecolor(COLOR_FRAME)
        fig.tight_layout()

        self._compare_canvas = FigureCanvasTkAgg(fig,
                                                 master=self.compare_frame)
        self._compare_canvas.draw()
        self._compare_canvas.get_tk_widget().pack(
            expand=True, fill="both")

    def show_multi_driver_speed(self, session, drivers: list[str]):
        if getattr(self, "_speed_canvas", None):
            self._speed_canvas.get_tk_widget().destroy()
        fastf1.plotting.setup_mpl(misc_mpl_mods=False,
                                  color_scheme='fastf1')

        fig = plt.Figure(figsize=(6,4), dpi=100,
                         facecolor=COLOR_FRAME)
        ax  = fig.add_subplot(111)
        for drv in drivers:
            lap = session.laps.pick_drivers(drv).pick_fastest()
            tel = lap.get_car_data().add_distance()
            style = fastf1.plotting.get_driver_style(
                identifier=drv,
                style=['color','linestyle'],
                session=session
            )
            ax.plot(tel['Distance'], tel['Speed'],
                    label=drv, **style)

        ax.set_xlabel("Distance (m)")
        ax.set_ylabel("Speed (km/h)")
        ax.set_title(
            f"Speed Comparison – {session.event['EventName']} {session.event.year}",
            color=COLOR_TEXT, fontsize=9
        )
        ax.legend(); ax.grid(color="#333333")
        ax.set_facecolor(COLOR_FRAME)
        fig.patch.set_facecolor(COLOR_FRAME)
        fig.tight_layout()

        self._speed_canvas = FigureCanvasTkAgg(fig,
                                               master=self.speed_frame)
        self._speed_canvas.draw()
        self._speed_canvas.get_tk_widget().pack(
            expand=True, fill="both")
    """

    def show_multi_driver_compare(self, session, drivers: list[str]):
        if getattr(self, "_compare_canvas", None):
            self._compare_canvas.get_tk_widget().destroy()
        laps_df = session.laps.pick_quicklaps().reset_index()
        df      = laps_df[laps_df['Driver'].isin(drivers)].copy()
        df['LapTime_s'] = df['LapTime'].dt.total_seconds()

        fig = plt.Figure(figsize=(6,4), dpi=100,
                         facecolor=COLOR_FRAME)
        ax  = fig.add_subplot(111)
        sns.violinplot(data=df, x='Driver', y='LapTime_s',
                       inner='quartile', cut=0, ax=ax,
                       palette=[COLOR_ACCENT]*len(drivers))
        meds = df.groupby('Driver')['LapTime_s'].median()
        ax.plot(range(len(drivers)), meds.values,
                marker='o', linestyle='--',
                color=COLOR_HIGHLIGHT)

        ax.invert_yaxis()
        ax.set_xlabel("Driver"); ax.set_ylabel("LapTime (s)")
        ax.set_title(
            f"LapTime Comparison – {session.event['EventName']} {session.event.year}",
            color=COLOR_TEXT, fontsize=9
        )
        ax.grid(color="#333333")
        ax.set_facecolor(COLOR_FRAME)
        fig.patch.set_facecolor(COLOR_FRAME)
        fig.tight_layout()

        self._compare_canvas = FigureCanvasTkAgg(fig,
                                                 master=self.compare_frame)
        self._compare_canvas.draw()
        self._compare_canvas.get_tk_widget().pack(
            expand=True, fill="both")

    def show_multi_driver_speed(self, session, drivers: list[str]):
        if getattr(self, "_speed_canvas", None):
            self._speed_canvas.get_tk_widget().destroy()
        fastf1.plotting.setup_mpl(misc_mpl_mods=False,
                                  color_scheme='fastf1')

        fig = plt.Figure(figsize=(6,4), dpi=100,
                         facecolor=COLOR_FRAME)
        ax  = fig.add_subplot(111)
        for drv in drivers:
            lap = session.laps.pick_drivers(drv).pick_fastest()
            tel = lap.get_car_data().add_distance()
            style = fastf1.plotting.get_driver_style(
                identifier=drv,
                style=['color','linestyle'],
                session=session
            )
            ax.plot(tel['Distance'], tel['Speed'],
                    label=drv, **style)

        ax.set_xlabel("Distance (m)")
        ax.set_ylabel("Speed (km/h)")
        ax.set_title(
            f"Speed Comparison – {session.event['EventName']} {session.event.year}",
            color=COLOR_TEXT, fontsize=9
        )
        ax.legend(); ax.grid(color="#333333")
        ax.set_facecolor(COLOR_FRAME)
        fig.patch.set_facecolor(COLOR_FRAME)
        fig.tight_layout()

        self._speed_canvas = FigureCanvasTkAgg(fig,
                                               master=self.speed_frame)
        self._speed_canvas.draw()
        self._speed_canvas.get_tk_widget().pack(
            expand=True, fill="both")

    def show_multi_lap_scatter(self, session, drivers: list[str]):
        if getattr(self, "_scatter_canvas", None):
            self._scatter_canvas.get_tk_widget().destroy()
        laps_df = session.laps.pick_quicklaps().reset_index()

        fig, axes = plt.subplots(2, 2, figsize=(8,6),
                                 facecolor=COLOR_FRAME)
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

        fig.patch.set_facecolor(COLOR_FRAME)
        for j in range(len(drivers), 4):
            axes.flatten()[j].axis('off')

        self._scatter_canvas = FigureCanvasTkAgg(fig,
                                                 master=self.scatter_frame)
        self._scatter_canvas.draw()
        self._scatter_canvas.get_tk_widget().pack(
            expand=True, fill="both")