import warnings
import matplotlib.pyplot as plt
import fastf1.plotting

# Suppress FastF1 FutureWarning about MPL defaults
warnings.filterwarnings('ignore', category=FutureWarning, module='fastf1.plotting')

# Set up FastF1 dark theme for matplotlib
fastf1.plotting.setup_mpl(mpl_timedelta_support=True, misc_mpl_mods=False, color_scheme='fastf1')


def plot_speed_telemetry(session, driver):
    # Plot fastest lap speed telemetry for a driver
    laps = session.laps.pick_drivers(driver).pick_fastest()
    data = laps.get_car_data()
    fig, ax = plt.subplots(figsize=(6,4))
    ax.plot(data['Time'], data['Speed'], label=driver)
    ax.set_title(f"Speed Telemetry: {driver}")
    ax.set_xlabel('Time')
    ax.set_ylabel('Speed (km/h)')
    ax.legend()
    plt.tight_layout()
    return fig
import matplotlib.pyplot as plt
import fastf1.plotting

# Set up FastF1 dark theme for matplotlib and suppress future warnings
fastf1.plotting.setup_mpl(mpl_timedelta_support=True, misc_mpl_mods=False, color_scheme='fastf1')


def plot_speed_telemetry(session, driver):
    # Plot fastest lap speed telemetry for a driver
    laps = session.laps.pick_drivers(driver).pick_fastest()
    data = laps.get_car_data()
    fig, ax = plt.subplots(figsize=(6,4))
    ax.plot(data['Time'], data['Speed'], label=driver)
    ax.set_title(f"Speed Telemetry: {driver}")
    ax.set_xlabel('Time')
    ax.set_ylabel('Speed (km/h)')
    ax.legend()
    plt.tight_layout()
    return fig
import matplotlib.pyplot as plt
import fastf1.plotting

# Set up FastF1 dark theme for matplotlib
fastf1.plotting.setup_mpl(mpl_timedelta_support=True, color_scheme='fastf1')


def plot_speed_telemetry(session, driver):
    # Plot fastest lap speed telemetry for a driver
    laps = session.laps.pick_drivers(driver).pick_fastest()
    data = laps.get_car_data()
    fig, ax = plt.subplots(figsize=(6,4))
    ax.plot(data['Time'], data['Speed'], label=driver)
    ax.set_title(f"Speed Telemetry: {driver}")
    ax.set_xlabel('Time')
    ax.set_ylabel('Speed (km/h)')
    ax.legend()
    plt.tight_layout()
    return fig