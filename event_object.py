import fastf1
import pandas as pd

schedule = fastf1.get_event_schedule(2025)
print(schedule)  