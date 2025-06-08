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
from pathlib import Path

from config import CACHE_DIR as CACHE_DIR_STR, CACHE_SIZE_LIMIT_GB, CACHE_EXPIRE_DAYS

CACHE_DIR = Path(CACHE_DIR_STR)
EXECUTOR = ThreadPoolExecutor(max_workers=4, thread_name_prefix="FastF1Worker")

class CacheManager:
    @staticmethod
    def ensure_cache_dir() -> None:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        fastf1.Cache.enable_cache(str(CACHE_DIR))

    @staticmethod
    def cleanup_cache() -> None:
        if not CACHE_DIR.exists():
            return
        total_bytes = 0
        now = datetime.now()
        expired_files = []
        for item in CACHE_DIR.rglob('*'):
            if item.is_file():
                try:
                    stat = item.stat()
                    total_bytes += stat.st_size
                    if (now - datetime.fromtimestamp(stat.st_atime)).days > CACHE_EXPIRE_DAYS:
                        expired_files.append(item)
                except FileNotFoundError:
                    continue
        for fp in expired_files:
            try:
                current_size = fp.stat().st_size
                fp.unlink()
                total_bytes -= current_size
            except FileNotFoundError:
                continue
            except Exception:
                pass
        if total_bytes > CACHE_SIZE_LIMIT_GB * 1024**3:
            try:
                shutil.rmtree(CACHE_DIR, ignore_errors=True)
                CACHE_DIR.mkdir(parents=True, exist_ok=True)
            except Exception:
                pass

class FastF1Service:
    def __init__(self):
        CacheManager.ensure_cache_dir()

    def get_event_schedule_async(self, year: int):
        return EXECUTOR.submit(fastf1.get_event_schedule, year)

    def load_session_async(self, year: int, gp: str, ses: str):
        def _inner():
            s = fastf1.get_session(year, gp, ses)
            s.load(laps=True, telemetry=True, weather=True, messages=True)
            return s
        return EXECUTOR.submit(_inner)