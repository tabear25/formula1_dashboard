"""FastF1 データ取得の Web（Streamlit）向けアダプタ。

`service.py` の `CacheManager` を再利用しつつ、Streamlit のキャッシュ機構で
スケジュール／セッションを保持し、5〜30 秒の再取得を回避する。

キャッシュディレクトリは環境変数 `FASTF1_CACHE` を優先し、未設定なら
一時ディレクトリ配下（クラウドの書き込み可能パス）を使う。
"""

import os
import tempfile
from pathlib import Path

import fastf1
import streamlit as st


def _resolve_cache_dir() -> Path:
    env = os.environ.get("FASTF1_CACHE")
    cache_dir = Path(env) if env else Path(tempfile.gettempdir()) / "f1_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


@st.cache_resource(show_spinner=False)
def init_cache() -> str:
    """FastF1 のディスクキャッシュを有効化する（プロセスで一度だけ）。"""
    cache_dir = _resolve_cache_dir()
    fastf1.Cache.enable_cache(str(cache_dir))
    return str(cache_dir)


@st.cache_data(show_spinner=False, ttl=60 * 60)
def get_event_names(year: int):
    """指定年の開催グランプリ名（EventName）一覧を返す。"""
    init_cache()
    schedule = fastf1.get_event_schedule(year)
    if schedule is None or schedule.empty:
        return []
    return list(schedule["EventName"])


@st.cache_resource(show_spinner=False)
def load_session(year: int, gp: str, ses: str):
    """ラップ・テレメトリ・天候・メッセージ込みでロード済みの Session を返す。

    `st.cache_resource` で保持するため、同じ (year, gp, ses) の再選択時は
    即座に返り、ネットワーク／キャッシュ I/O を繰り返さない。
    """
    init_cache()
    session = fastf1.get_session(year, gp, ses)
    session.load(laps=True, telemetry=True, weather=True, messages=True)
    return session


def driver_abbreviations(session) -> list:
    """セッション参加ドライバーの略称（昇順）を返す。"""
    abbrs = []
    if session is not None and getattr(session, "drivers", None):
        for drv_num in session.drivers:
            try:
                info = session.get_driver(drv_num)
                if info is not None and "Abbreviation" in info:
                    abbrs.append(info["Abbreviation"])
            except Exception:
                pass
    return sorted(abbrs)
