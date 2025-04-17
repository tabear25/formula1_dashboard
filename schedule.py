import fastf1
import pandas as pd
import logging

# 2025年のイベントスケジュールを取得
schedule = fastf1.get_event_schedule(2025)

# スケジュールのカラム情報を表示
print("取得されたカラム一覧:")
print(schedule.columns)

# 先頭5行を表示（中身の確認）
print("スケジュールのプレビュー:")
print(schedule.head())
