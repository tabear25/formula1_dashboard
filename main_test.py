import matplotlib.pyplot as plt
import numpy as np
from matplotlib import colormaps
from matplotlib.collections import LineCollection

import fastf1


# セッション情報の取得（2025年・鈴鹿・予選）

session = fastf1.get_session(2025, "Suzuka", "Q")
session.load()

# 角田の最速ラップを取得
lap = session.laps.pick_drivers("TSU").pick_fastest()
print(lap)
tel = lap.get_telemetry()

# データの前処理

x = np.array(tel['X'].values)
y = np.array(tel['Y'].values)

points = np.array([x, y]).T.reshape(-1, 1, 2)
segments = np.concatenate([points[:-1], points[1:]], axis=1)
gear = tel['nGear'].to_numpy().astype(float)

# カラーマップの設定

cmap = colormaps['Paired']
lc_comp = LineCollection(segments, norm=plt.Normalize(1, cmap.N+1), cmap=cmap)
lc_comp.set_array(gear)
lc_comp.set_linewidth(4)

# プロットの生成

plt.gca().add_collection(lc_comp)
plt.axis('equal')
plt.tick_params(labelleft=False, left=False, labelbottom=False, bottom=False)
lap_time = str(lap['LapTime'])[10:19]

title = plt.suptitle(
    f"Fastest Lap Gear Shift Visualization\n"
    f"{lap['Driver']} - {lap_time} - {session.event['EventName']} {session.event.year} {session.name}"
)

# カラーバーの生成

cbar = plt.colorbar(mappable=lc_comp, label="Gear",
                    boundaries=np.arange(1, 10))
cbar.set_ticks(np.arange(1.5, 9.5))
cbar.set_ticklabels(np.arange(1, 9))

# プロットの表示
plt.show()