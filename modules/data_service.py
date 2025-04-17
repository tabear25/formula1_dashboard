import fastf1
import json
import os
import tempfile
from concurrent.futures import ThreadPoolExecutor

class DataService:
    def __init__(self, settings_path='settings.json'):
        # Load settings
        with open(settings_path, 'r') as f:
            cfg = json.load(f)
        # Determine cache directory (must be a valid string)
        cache_cfg = cfg.get('cache_dir')
        if cache_cfg:
            cache_dir = cache_cfg
        else:
            # default to OS temp directory under 'fastf1_cache'
            cache_dir = os.path.join(tempfile.gettempdir(), 'fastf1_cache')
        # Ensure cache directory exists
        os.makedirs(cache_dir, exist_ok=True)
        # Enable FastF1 cache
        fastf1.Cache.enable_cache(cache_dir)
        self.executor = ThreadPoolExecutor(max_workers=2)

    def get_schedule(self, year):
        # Returns a pandas DataFrame of the event schedule
        return fastf1.get_event_schedule(year)

    def load_session(self, year, gp, session, callback):
        # Asynchronous session loading
        def task():
            ses = fastf1.get_session(year, gp, session)
            ses.load()  # loads telemetry+weather
            callback(ses)
        self.executor.submit(task)