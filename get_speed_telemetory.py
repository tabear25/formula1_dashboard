from matplotlib import pyplot as plt
import fastf1
import fastf1.plotting

fastf1.plotting.setup_mpl(misc_mpl_mods=False, color_scheme='fastf1')

session = fastf1.get_session(2025, 'Suzuka', 'Q')

session.load()
fast_max = session.laps.pick_drivers('LEC').pick_fastest()
lec_car_data = fast_max.get_car_data()
t = lec_car_data['Time']
vCar = lec_car_data['Speed']

# 表示の設定
fig, ax = plt.subplots()
ax.plot(t, vCar, label='Fast')
ax.set_xlabel('Time')
ax.set_ylabel('Speed [Km/h]')
ax.set_title('Speed Telemetry - VER - 2025 Suzuka')

# 表示させるコード
ax.legend()
plt.tight_layout()
plt.show()