import matplotlib.pyplot as plt
import pandas as pd
from timple.timedelta import strftimedelta

import fastf1
import fastf1.plotting
from fastf1.core import Laps

# GUI 用ライブラリ
import tkinter as tk
from tkinter import ttk

# Matplotlib のタイムデルタ表示サポートを有効化
fastf1.plotting.setup_mpl(mpl_timedelta_support=True, misc_mpl_mods=False, color_scheme=None)

# セッションの取得とデータロード（例：2025年 Japanese Grand Prix の予選）
session = fastf1.get_session(2025, 'Japanese Grand Prix', 'Q')
session.load()

# 結果データフレームの表示
print(session.results.columns)
print(session.results.head())
