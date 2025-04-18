import warnings
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import fastf1
import fastf1.plotting
from matplotlib.collections import LineCollection
import plotly.express as px
from fastf1.ergast import Ergast

warnings.filterwarnings('ignore', category=FutureWarning, module='fastf1.plotting')
fastf1.plotting.setup_mpl(mpl_timedelta_support=True, misc_mpl_mods=False, color_scheme='fastf1')

# 1. Speed Telemetry
def plot_speed_telemetry(session, driver):
    lap = session.laps.pick_drivers(driver).pick_fastest()
    data = lap.get_car_data()
    fig, ax = plt.subplots(figsize=(6,4))
    ax.plot(data['Time'], data['Speed'], label=driver)
    ax.set_title(f"Speed Telemetry: {driver}")
    ax.set_xlabel('Time')
    ax.set_ylabel('Speed (km/h)')
    ax.legend(); plt.tight_layout()
    return fig

# 2. Session Info Table
def plot_session_info(session):
    df = session.results[['Position','Driver','Team','LapTime','Time']] if hasattr(session, 'results') else pd.DataFrame()
    fig, ax = plt.subplots(figsize=(6,4))
    ax.axis('off')
    tbl = ax.table(cellText=df.values, colLabels=df.columns, loc='center')
    tbl.auto_set_font_size(False); tbl.set_fontsize(8)
    ax.set_title('Session Results')
    return fig

# 3. Circuit Map
def plot_circuit_map(session):
    lap = session.laps.pick_fastest()
    pos = lap.get_pos_data()[['X','Y']].to_numpy()
    rot = session.get_circuit_info().rotation/180*np.pi
    def rotate(xy, angle): return xy.dot(np.array([[np.cos(angle), np.sin(angle)],[-np.sin(angle), np.cos(angle)]]))
    track = rotate(pos, rot)
    fig, ax = plt.subplots(figsize=(6,4))
    ax.plot(track[:,0], track[:,1], color='white')
    ax.axis('equal'); ax.axis('off')
    ax.set_title('Circuit Map')
    return fig

# 4. Lap Time Comparison (Box + Line)
def plot_laptime_comparison(session, drivers):
    laps = session.laps.pick_quicklaps().reset_index()
    fig, ax = plt.subplots(figsize=(6,4))
    for d in drivers:
        dlap = laps[laps['Driver']==d]
        ax.plot(dlap['LapNumber'], dlap['LapTime'].dt.total_seconds(), label=d)
    ax.set_title('Lap Time Comparison'); ax.legend(); plt.tight_layout()
    return fig

# 5. Position Changes
def plot_position_changes(session):
    fig, ax = plt.subplots(figsize=(6,4))
    for drv in session.drivers:
        dlap = session.laps.pick_drivers(drv)
        ax.plot(dlap['LapNumber'], dlap['Position'], label=drv)
    ax.invert_yaxis(); ax.set_title('Position Changes'); ax.set_xlabel('Lap'); ax.set_ylabel('Position')
    ax.legend(bbox_to_anchor=(1,1)); plt.tight_layout()
    return fig

# 6. Points Bar Chart
def plot_points_bar(session):
    erg = Ergast()
    races = erg.get_race_schedule(session.event.year)
    results = []
    for i,_ in races['round'].items():
        tmp = erg.get_race_results(session.event.year, i+1).content[0][['driverCode','points']]
        tmp['round']=i+1; results.append(tmp)
    df = pd.concat(results)
    pts = df.groupby('driverCode')['points'].sum().sort_values()
    fig, ax = plt.subplots(figsize=(6,4))
    pts.plot.barh(ax=ax); ax.set_title('Total Points'); plt.tight_layout()
    return fig

# 7. Track Heatmap (Speed)
def plot_track_heatmap(session):
    lap = session.laps.pick_fastest()
    tel = lap.get_telemetry()
    pts = np.vstack([tel['X'],tel['Y'],tel['Speed']]).T
    fig, ax = plt.subplots(figsize=(6,4))
    sc = ax.scatter(pts[:,0], pts[:,1], c=pts[:,2], s=2)
    plt.colorbar(sc, ax=ax); ax.axis('off'); ax.set_title('Speed Heatmap')
    return fig

# 8. Qualifying Bubble Chart
def plot_qualy_bubble(session, drivers):
    laps = session.laps.pick_quicklaps().reset_index()
    df = laps[laps['Driver'].isin(drivers)]
    fig = px.scatter(df, x='LapNumber', y='LapTime', size='LapTime', color='Driver', title='Qualy Bubble')
    return fig

# 9. Tire Strategy Gantt (Race)
def plot_tire_strategy(session):
    st = session.laps[['Driver','Stint','Compound','LapNumber']].groupby(['Driver','Stint','Compound']).count().reset_index()
    fig, ax = plt.subplots(figsize=(6,4))
    for i,drv in enumerate(st['Driver'].unique()):
        sub = st[st['Driver']==drv]
        start=0
        for _,r in sub.iterrows():
            ax.barh(drv, r['LapNumber'], left=start)
            start+=r['LapNumber']
    ax.invert_yaxis(); ax.set_title('Tire Strategy'); plt.tight_layout()
    return fig

# 10. Team Pace Comparison
def plot_team_pace(session):
    laps = session.laps.pick_quicklaps()
    laps['lt_s']=laps['LapTime'].dt.total_seconds()
    med = laps.groupby('Team')['lt_s'].median().sort_values()
    fig, ax = plt.subplots(figsize=(6,4))
    med.plot.bar(ax=ax); ax.set_title('Team Pace (Median Lap Time)'); plt.tight_layout()
    return fig