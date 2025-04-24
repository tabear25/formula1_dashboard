"""
FastF1 Service Module
This module provides a service for managing FastF1 cache and loading sessions asynchronously.
It includes a CacheManager for cache directory management and cleanup, and a FastF1Service for loading event schedules and sessions.
"""

import os
import shutil
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import fastf1

from config import CACHE_DIR, CACHE_SIZE_LIMIT_GB, CACHE_EXPIRE_DAYS

# スレッドプール
EXECUTOR = ThreadPoolExecutor(max_workers=4, thread_name_prefix="FastF1Worker")

class CacheManager:
    @staticmethod
    def ensure_cache_dir() -> None:
        os.makedirs(CACHE_DIR, exist_ok=True)
        fastf1.Cache.enable_cache(str(CACHE_DIR))

    @staticmethod
    def cleanup_cache() -> None:
        total_bytes = 0
        now = datetime.now()
        for root, _, files in os.walk(CACHE_DIR):
            for f in files:
                fp = os.path.join(root, f)
                try:
                    stat = os.stat(fp)
                except FileNotFoundError:
                    continue
                total_bytes += stat.st_size
                if (now - datetime.fromtimestamp(stat.st_atime)).days > CACHE_EXPIRE_DAYS:
                    os.remove(fp)
        if total_bytes > CACHE_SIZE_LIMIT_GB * 1024**3:
            shutil.rmtree(CACHE_DIR, ignore_errors=True)
            os.makedirs(CACHE_DIR, exist_ok=True)

class FastF1Service:
    def __init__(self):
        CacheManager.ensure_cache_dir()

    def get_event_schedule_async(self, year: int):
        return EXECUTOR.submit(fastf1.get_event_schedule, year)

    def load_session_async(self, year: int, gp: str, ses: str):
        def _inner():
            s = fastf1.get_session(year, gp, ses)
            s.load()
            return s
        return EXECUTOR.submit(_inner)
