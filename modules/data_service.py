import fastf1
import json
import os
import tempfile
from concurrent.futures import ThreadPoolExecutor

class DataService:
    def __init__(self, settings_path='settings.json'):
        with open(settings_path, 'r') as f:
            cfg = json.load(f)
        cache_cfg = cfg.get('cache_dir')
        cache_dir = cache_cfg if cache_cfg else os.path.join(tempfile.gettempdir(), 'fastf1_cache')
        os.makedirs(cache_dir, exist_ok=True)
        fastf1.Cache.enable_cache(cache_dir)
        self.executor = ThreadPoolExecutor(max_workers=2)

    def get_schedule(self, year):
        return fastf1.get_event_schedule(year)

    def load_session(self, year, gp, session_name, callback):
        def task():
            ses = fastf1.get_session(year, gp, session_name)
            ses.load()
            callback(ses)
        self.executor.submit(task)
