"""
PITWALL - F1 Web Dashboard server.

stdlib の http.server で web/ の静的ファイルと /api/* の JSON API を配信する。
データ源は FastF1（既存 Tkinter アプリと同じキャッシュ _fastf1_cache/ を共用）。
追加の pip 依存は無し（fastf1 / pandas は既存 requirements.txt の範囲）。

起動:  py server.py            (既定 http://127.0.0.1:8380 を自動で開く)
       py server.py --no-browser --port 8380
"""

import argparse
import gzip
import json
import logging
import math
import threading
import time
import traceback
import webbrowser
from collections import OrderedDict
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import numpy as np
import pandas as pd
import fastf1
import fastf1.plotting

from config import CACHE_DIR

BASE_DIR = Path(__file__).resolve().parent
WEB_DIR = BASE_DIR / "web"
DEFAULT_PORT = 8380

# ライブタイミング由来のラップ/テレメトリが揃うのは 2018 年以降
FIRST_YEAR = 2018

# ダークサーフェス（web/styles.css の --surface-1 と一致させること）
CHART_SURFACE = "#14171f"
MIN_MARK_CONTRAST = 3.0

SESSION_NAME_TO_CODE = {
    "Practice 1": "FP1",
    "Practice 2": "FP2",
    "Practice 3": "FP3",
    "Qualifying": "Q",
    "Sprint Qualifying": "SQ",
    "Sprint Shootout": "SQ",
    "Sprint": "S",
    "Race": "R",
}

COMPOUND_FALLBACK = {
    "SOFT": "#da291c",
    "MEDIUM": "#ffd12e",
    "HARD": "#f0f0ec",
    "INTERMEDIATE": "#43b02a",
    "WET": "#0067ad",
    "UNKNOWN": "#8a8f9c",
    "TEST_UNKNOWN": "#8a8f9c",
}


# ---------------------------------------------------------------------------
# 色ユーティリティ（チームカラーをダーク背景で読めるように明度だけ補正する）
# ---------------------------------------------------------------------------

def _hex_to_rgb(h):
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(ch * 2 for ch in h)
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _rgb_to_hex(rgb):
    return "#{:02x}{:02x}{:02x}".format(*(max(0, min(255, round(v))) for v in rgb))


def _srgb_to_linear(c):
    c = c / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _linear_to_srgb(c):
    c = max(0.0, min(1.0, c))
    return (12.92 * c if c <= 0.0031308 else 1.055 * (c ** (1 / 2.4)) - 0.055) * 255.0


def _relative_luminance(hex_color):
    r, g, b = (_srgb_to_linear(v) for v in _hex_to_rgb(hex_color))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(hex_a, hex_b):
    la, lb = _relative_luminance(hex_a), _relative_luminance(hex_b)
    lighter, darker = max(la, lb), min(la, lb)
    return (lighter + 0.05) / (darker + 0.05)


def _rgb_to_oklab(rgb):
    r, g, b = (_srgb_to_linear(v) for v in rgb)
    l = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b
    l, m, s = (v ** (1 / 3) if v > 0 else 0.0 for v in (l, m, s))
    return (
        0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s,
        1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s,
        0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s,
    )


def _oklab_to_rgb(lab):
    L, a, b = lab
    l = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3
    m = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3
    s = (L - 0.0894841775 * a - 1.2914855480 * b) ** 3
    r = +4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s
    g = -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s
    bb = -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s
    return tuple(_linear_to_srgb(v) for v in (r, g, bb))


def ensure_mark_contrast(hex_color, surface=CHART_SURFACE, min_ratio=MIN_MARK_CONTRAST):
    """色相を保ったまま OKLab の明度を上げ、サーフェス比 min_ratio 以上へスナップする。
    明度を上げた結果、彩度がフロア(0.10)を割って灰色化しないよう彩度も底上げする。"""
    try:
        if contrast_ratio(hex_color, surface) >= min_ratio:
            return hex_color.lower()
        L, a, b = _rgb_to_oklab(_hex_to_rgb(hex_color))
        chroma = math.hypot(a, b)
        if 0.0 < chroma < 0.10:
            scale = 0.11 / chroma
            a, b = a * scale, b * scale
        candidate = hex_color
        for _ in range(40):
            L = min(0.97, L + 0.015)
            candidate = _rgb_to_hex(_oklab_to_rgb((L, a, b)))
            if contrast_ratio(candidate, surface) >= min_ratio:
                return candidate
        return candidate
    except Exception:
        return hex_color


# ---------------------------------------------------------------------------
# JSON 変換ヘルパ
# ---------------------------------------------------------------------------

def td_s(value, ndigits=3):
    """Timedelta/NaT → 秒(float) / None"""
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(value, (pd.Timedelta, np.timedelta64)):
        return round(pd.Timedelta(value).total_seconds(), ndigits)
    if isinstance(value, (int, float)):
        return round(float(value), ndigits)
    return None


def num(value, ndigits=None):
    """numpy スカラー/NaN → Python の数値 / None"""
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        v = float(value)
        return round(v, ndigits) if ndigits is not None else v
    if isinstance(value, (int,)):
        return value
    return None


def text(value):
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    s = str(value)
    return s if s and s.lower() != "nan" else None


# ---------------------------------------------------------------------------
# セッションストア（バックグラウンドロード + LRU）
# ---------------------------------------------------------------------------

class SessionStore:
    MAX_SESSIONS = 2  # fastf1 セッションはテレメトリ込みでメモリを食うため控えめに

    def __init__(self):
        self._lock = threading.Lock()
        self._load_lock = threading.Lock()  # fastf1 のロードは同時に 1 件のみ
        self._entries = OrderedDict()       # key -> entry dict
        self._schedule_cache = {}

    @staticmethod
    def key(year, rnd, code):
        return f"{year}:{rnd}:{code}"

    def get_schedule(self, year):
        with self._lock:
            if year in self._schedule_cache:
                return self._schedule_cache[year]
        schedule = fastf1.get_event_schedule(year)
        events = []
        for _, row in schedule.iterrows():
            try:
                rnd = int(row["RoundNumber"])
            except (TypeError, ValueError):
                continue
            if rnd < 1:
                continue  # テスト走行は対象外
            sessions = []
            for i in range(1, 6):
                name = text(row.get(f"Session{i}"))
                if not name:
                    continue
                code = SESSION_NAME_TO_CODE.get(name)
                if not code:
                    continue
                date = row.get(f"Session{i}DateUtc")
                sessions.append({
                    "code": code,
                    "name": name,
                    "date_utc": None if pd.isna(date) else str(date),
                })
            events.append({
                "round": rnd,
                "name": text(row.get("EventName")),
                "official_name": text(row.get("OfficialEventName")),
                "location": text(row.get("Location")),
                "country": text(row.get("Country")),
                "date": None if pd.isna(row.get("EventDate")) else str(row.get("EventDate"))[:10],
                "format": text(row.get("EventFormat")),
                "f1_api_support": bool(row.get("F1ApiSupport", False)),
                "sessions": sessions,
            })
        payload = {"year": year, "events": events}
        with self._lock:
            self._schedule_cache[year] = payload
        return payload

    def status(self, year, rnd, code):
        entry = self._entries.get(self.key(year, rnd, code))
        if entry is None:
            return {"state": "not_loaded"}
        out = {"state": entry["state"], "elapsed": round(time.time() - entry["started"], 1)}
        if entry["state"] == "error":
            out["error"] = entry.get("error", "unknown error")
        return out

    def request_load(self, year, rnd, code):
        k = self.key(year, rnd, code)
        with self._lock:
            entry = self._entries.get(k)
            if entry is not None and entry["state"] in ("loading", "ready"):
                self._entries.move_to_end(k)
                return self.status(year, rnd, code)
            entry = {"state": "loading", "started": time.time()}
            self._entries[k] = entry
            self._entries.move_to_end(k)
        worker = threading.Thread(target=self._load, args=(k, year, rnd, code), daemon=True)
        worker.start()
        return {"state": "loading", "elapsed": 0.0}

    def entry(self, year, rnd, code):
        with self._lock:
            entry = self._entries.get(self.key(year, rnd, code))
            if entry is not None:
                self._entries.move_to_end(self.key(year, rnd, code))
            return entry

    def _evict_if_needed(self):
        with self._lock:
            ready_keys = [k for k, e in self._entries.items() if e["state"] == "ready"]
            while len(ready_keys) > self.MAX_SESSIONS:
                victim = ready_keys.pop(0)
                logging.info("Evicting cached session %s", victim)
                self._entries.pop(victim, None)

    def _load(self, k, year, rnd, code):
        entry = self._entries[k]
        with self._load_lock:
            try:
                logging.info("Loading session %s ...", k)
                ses = fastf1.get_session(year, rnd, code)
                ses.load(laps=True, telemetry=True, weather=True, messages=True)
                bundle = build_bundle(ses, year, rnd, code)
                raw = json.dumps(bundle, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
                entry["session"] = ses
                entry["bundle_gz"] = gzip.compress(raw, 6)
                entry["bundle_raw"] = raw
                entry["circuit"] = None
                entry["tel_cache"] = {}
                entry["state"] = "ready"
                entry["finished"] = time.time()
                logging.info("Session %s ready (%.1fs, %d KB json)",
                             k, entry["finished"] - entry["started"], len(raw) // 1024)
            except Exception as exc:
                logging.error("Session load failed for %s\n%s", k, traceback.format_exc())
                entry["state"] = "error"
                entry["error"] = f"{type(exc).__name__}: {exc}"
        self._evict_if_needed()


# ---------------------------------------------------------------------------
# バンドル生成（セッション → JSON 化可能な dict）
# ---------------------------------------------------------------------------

def _team_colors(ses, results):
    """TeamName -> ダーク背景向けに補正済み hex"""
    colors = {}
    teams = []
    if results is not None and len(results) > 0:
        teams = [t for t in results["TeamName"].dropna().unique().tolist()]
    for team in teams:
        raw = None
        try:
            raw = fastf1.plotting.get_team_color(team, session=ses, colormap="fastf1")
        except Exception:
            try:
                raw = fastf1.plotting.get_team_color(team, session=ses, colormap="official")
            except Exception:
                raw = None
        if raw is None:
            raw = "#8a8f9c"
        colors[team] = ensure_mark_contrast(raw)
    return colors


def _compound_colors(ses):
    try:
        mapping = fastf1.plotting.get_compound_mapping(session=ses)
        out = {}
        for k, v in mapping.items():
            out[str(k).upper()] = ensure_mark_contrast(v)
        for k, v in COMPOUND_FALLBACK.items():
            out.setdefault(k, ensure_mark_contrast(v))
        return out
    except Exception:
        return {k: ensure_mark_contrast(v) for k, v in COMPOUND_FALLBACK.items()}


def _build_drivers(ses, team_colors):
    results = ses.results
    drivers = []
    if results is None or len(results) == 0:
        # 結果が無いセッション: ラップからフォールバック
        laps = ses.laps
        if laps is None or len(laps) == 0:
            return []
        for abbr in laps["Driver"].dropna().unique().tolist():
            sub = laps[laps["Driver"] == abbr].iloc[0]
            team = text(sub.get("Team")) or ""
            drivers.append({
                "num": text(sub.get("DriverNumber")),
                "abbr": abbr,
                "name": abbr,
                "team": team,
                "color": team_colors.get(team, "#8a8f9c"),
                "dash": 0,
                "grid": None, "pos": None, "classified": None,
                "status": None, "points": None, "time_s": None,
                "q1": None, "q2": None, "q3": None,
            })
    else:
        for _, row in results.iterrows():
            team = text(row.get("TeamName")) or ""
            drivers.append({
                "num": text(row.get("DriverNumber")),
                "abbr": text(row.get("Abbreviation")),
                "name": text(row.get("FullName")) or text(row.get("BroadcastName")),
                "team": team,
                "color": team_colors.get(team, "#8a8f9c"),
                "dash": 0,
                "grid": num(row.get("GridPosition")),
                "pos": num(row.get("Position")),
                "classified": text(row.get("ClassifiedPosition")),
                "status": text(row.get("Status")),
                "points": num(row.get("Points")),
                "time_s": td_s(row.get("Time")),
                "q1": td_s(row.get("Q1")),
                "q2": td_s(row.get("Q2")),
                "q3": td_s(row.get("Q3")),
            })
        drivers.sort(key=lambda d: (d["pos"] is None, d["pos"] if d["pos"] is not None else 999))
    # チームメイトの二次符号化: 実線 / 破線 / 点線
    per_team = {}
    for d in drivers:
        idx = per_team.get(d["team"], 0)
        d["dash"] = min(idx, 2)
        per_team[d["team"]] = idx + 1
    return drivers


def _build_laps(ses):
    laps = ses.laps
    out = []
    if laps is None or len(laps) == 0:
        return out
    for row in laps.itertuples(index=False):
        lap_no = num(row.LapNumber)
        if lap_no is None:
            continue
        out.append({
            "drv": text(row.Driver),
            "lap": int(lap_no),
            "pos": num(row.Position),
            "t": td_s(row.LapTime),
            "s1": td_s(row.Sector1Time),
            "s2": td_s(row.Sector2Time),
            "s3": td_s(row.Sector3Time),
            "st": td_s(row.LapStartTime),
            "et": td_s(row.Time),
            "cmp": text(row.Compound),
            "life": num(row.TyreLife),
            "stint": num(row.Stint),
            "fresh": bool(row.FreshTyre) if row.FreshTyre is not None and not pd.isna(row.FreshTyre) else None,
            "pit_in": not pd.isna(row.PitInTime),
            "pit_out": not pd.isna(row.PitOutTime),
            "ts": text(row.TrackStatus),
            "del": bool(row.Deleted) if row.Deleted is not None and not pd.isna(row.Deleted) else False,
            "acc": bool(row.IsAccurate) if row.IsAccurate is not None and not pd.isna(row.IsAccurate) else False,
            "pb": bool(row.IsPersonalBest) if row.IsPersonalBest is not None and not pd.isna(row.IsPersonalBest) else False,
        })
    return out


def _build_track_status(ses):
    ts = ses.track_status
    out = []
    if ts is None or len(ts) == 0:
        return out
    for row in ts.itertuples(index=False):
        out.append({"t": td_s(row.Time), "s": text(row.Status), "msg": text(row.Message)})
    return out


def _build_race_control(ses):
    rcm = ses.race_control_messages
    out = []
    if rcm is None or len(rcm) == 0:
        return out
    # 日時 → セッション時間の変換オフセットをラップから推定
    t0 = None
    laps = ses.laps
    if laps is not None and len(laps) > 0:
        valid = laps.dropna(subset=["LapStartDate", "LapStartTime"])
        if len(valid) > 0:
            first = valid.iloc[0]
            t0 = first["LapStartDate"] - first["LapStartTime"]
    for row in rcm.itertuples(index=False):
        t_s = None
        clock = None
        if not pd.isna(row.Time):
            clock = str(row.Time)
            if t0 is not None:
                t_s = td_s(row.Time - t0)
        out.append({
            "t": t_s,
            "clock": clock,
            "lap": num(getattr(row, "Lap", None)),
            "cat": text(row.Category),
            "msg": text(row.Message),
            "flag": text(getattr(row, "Flag", None)),
            "scope": text(getattr(row, "Scope", None)),
            "sector": num(getattr(row, "Sector", None)),
            "rn": text(getattr(row, "RacingNumber", None)),
        })
    return out


def _build_weather(ses):
    wd = ses.weather_data
    out = []
    if wd is None or len(wd) == 0:
        return out
    for row in wd.itertuples(index=False):
        out.append({
            "t": td_s(row.Time, 1),
            "air": num(row.AirTemp, 1),
            "trk": num(row.TrackTemp, 1),
            "rain": bool(row.Rainfall),
            "hum": num(row.Humidity, 1),
            "ws": num(row.WindSpeed, 1),
            "wd": num(row.WindDirection),
        })
    return out


def _quali_segments(ses):
    """予選ラップの (Driver, LapNumber) -> セグメント番号 1/2/3。
    split_qualifying_sessions() が使えない場合は空 dict（クライアントは推定に劣化）。"""
    seg_map = {}
    try:
        parts = ses.laps.split_qualifying_sessions()
    except Exception:
        return seg_map
    if not parts:
        return seg_map
    for seg_no, part in enumerate(parts, start=1):
        if part is None or len(part) == 0:
            continue
        for row in part.itertuples(index=False):
            drv = text(row.Driver)
            lap_no = num(row.LapNumber)
            if drv is None or lap_no is None:
                continue
            seg_map[(drv, int(lap_no))] = seg_no
    return seg_map


def build_bundle(ses, year, rnd, code):
    results = ses.results
    team_colors = _team_colors(ses, results)
    session_type = "race" if code in ("R", "S") else ("quali" if code in ("Q", "SQ") else "practice")
    total_laps = None
    try:
        if ses.total_laps is not None:
            total_laps = int(ses.total_laps)
    except (TypeError, ValueError):
        total_laps = None
    laps_out = _build_laps(ses)
    if session_type == "quali":
        seg_map = _quali_segments(ses)
        if seg_map:
            for rec in laps_out:
                rec["seg"] = seg_map.get((rec["drv"], rec["lap"]))
    return {
        "meta": {
            "year": year,
            "round": rnd,
            "code": code,
            "type": session_type,
            "session_name": text(ses.name),
            "event_name": text(ses.event.get("EventName")),
            "official_name": text(ses.event.get("OfficialEventName")),
            "location": text(ses.event.get("Location")),
            "country": text(ses.event.get("Country")),
            "date_utc": str(ses.date) if ses.date is not None else None,
            "total_laps": total_laps,
        },
        "drivers": _build_drivers(ses, team_colors),
        "laps": laps_out,
        "track_status": _build_track_status(ses),
        "race_control": _build_race_control(ses),
        "weather": _build_weather(ses),
        "team_colors": team_colors,
        "compound_colors": _compound_colors(ses),
    }


# ---------------------------------------------------------------------------
# テレメトリ / トラックマップ
# ---------------------------------------------------------------------------

def _rotate_xy(x, y, angle_deg):
    rad = math.radians(angle_deg)
    cos_a, sin_a = math.cos(rad), math.sin(rad)
    # fastf1 のドキュメント例と同じ回転（時計回り）
    return x * cos_a + y * sin_a, -x * sin_a + y * cos_a


def _circuit_info(entry, ses):
    if entry.get("circuit") is None:
        try:
            ci = ses.get_circuit_info()
            entry["circuit"] = {"rotation": float(ci.rotation), "corners": ci.corners}
        except Exception:
            entry["circuit"] = {"rotation": 0.0, "corners": None}
    return entry["circuit"]


def _pick_lap(ses, abbr, lap_sel):
    laps = ses.laps.pick_drivers(abbr)
    if laps is None or len(laps) == 0:
        return None
    if lap_sel == "fastest":
        try:
            lap = laps.pick_fastest()
        except Exception:
            lap = None
        if lap is None or (hasattr(lap, "empty") and lap.empty):
            return None
        return lap
    try:
        lap_no = int(lap_sel)
    except (TypeError, ValueError):
        return None
    sub = laps[laps["LapNumber"] == lap_no]
    if len(sub) == 0:
        return None
    return sub.iloc[0]


def telemetry_payload(entry, ses, abbrs, lap_sel):
    circuit = _circuit_info(entry, ses)
    rotation = circuit["rotation"]
    out = []
    for abbr in abbrs:
        cache_key = f"{abbr}:{lap_sel}"
        cached = entry["tel_cache"].get(cache_key)
        if cached is not None:
            out.append(cached)
            continue
        lap = _pick_lap(ses, abbr, lap_sel)
        if lap is None:
            out.append({"abbr": abbr, "error": "lap not found"})
            continue
        try:
            tel = lap.get_telemetry()
        except Exception as exc:
            out.append({"abbr": abbr, "error": f"telemetry unavailable: {exc}"})
            continue
        if tel is None or len(tel) == 0:
            out.append({"abbr": abbr, "error": "telemetry empty"})
            continue
        x_rot, y_rot = _rotate_xy(tel["X"].to_numpy(), tel["Y"].to_numpy(), rotation)
        lap_time = td_s(lap["LapTime"])
        t_arr = (tel["Time"].dt.total_seconds()).round(3)
        payload = {
            "abbr": abbr,
            "lap": num(lap["LapNumber"]),
            "lap_time": lap_time,
            "compound": text(lap["Compound"]),
            "d": [round(float(v), 1) for v in tel["Distance"].to_numpy()],
            "v": [round(float(v), 1) for v in tel["Speed"].to_numpy()],
            "th": [round(float(v), 1) for v in tel["Throttle"].to_numpy()],
            "br": [1 if bool(v) else 0 for v in tel["Brake"].to_numpy()],
            "g": [int(v) for v in tel["nGear"].to_numpy()],
            "drs": [int(v) for v in tel["DRS"].to_numpy()],
            "t": [float(v) for v in t_arr.to_numpy()],
            "x": [round(float(v), 1) for v in x_rot],
            "y": [round(float(v), 1) for v in y_rot],
        }
        entry["tel_cache"][cache_key] = payload
        out.append(payload)
    return {"rotation": rotation, "laps": out}


def trackmap_payload(entry, ses):
    cached = entry["tel_cache"].get("__trackmap__")
    if cached is not None:
        return cached
    circuit = _circuit_info(entry, ses)
    rotation = circuit["rotation"]
    lap = None
    try:
        lap = ses.laps.pick_fastest()
    except Exception:
        lap = None
    if lap is None or (hasattr(lap, "empty") and lap.empty):
        return {"error": "no fastest lap available"}
    try:
        tel = lap.get_telemetry()
    except Exception as exc:
        return {"error": f"telemetry unavailable: {exc}"}
    x_rot, y_rot = _rotate_xy(tel["X"].to_numpy(), tel["Y"].to_numpy(), rotation)
    corners = []
    cdf = circuit["corners"]
    if cdf is not None and len(cdf) > 0:
        offset = 560.0  # コーナー番号ラベルをトラック外側に出すオフセット距離
        for row in cdf.itertuples(index=False):
            angle_rad = math.radians(float(row.Angle))
            off_x = offset * math.cos(angle_rad)
            off_y = offset * math.sin(angle_rad)
            px, py = _rotate_xy(float(row.X), float(row.Y), rotation)
            lx, ly = _rotate_xy(float(row.X) + off_x, float(row.Y) + off_y, rotation)
            corners.append({
                "n": int(row.Number),
                "letter": text(row.Letter) or "",
                "x": round(px, 1), "y": round(py, 1),
                "lx": round(lx, 1), "ly": round(ly, 1),
                "dist": round(float(row.Distance), 1),
            })
    payload = {
        "rotation": rotation,
        "abbr": text(lap["Driver"]),
        "lap_time": td_s(lap["LapTime"]),
        "x": [round(float(v), 1) for v in x_rot],
        "y": [round(float(v), 1) for v in y_rot],
        "v": [round(float(v), 1) for v in tel["Speed"].to_numpy()],
        "d": [round(float(v), 1) for v in tel["Distance"].to_numpy()],
        "corners": corners,
    }
    entry["tel_cache"]["__trackmap__"] = payload
    return payload


# ---------------------------------------------------------------------------
# リプレイ（全車位置の共通時間グリッド）
# ---------------------------------------------------------------------------

REPLAY_DT = 0.5          # 秒。実測でこの粒度なら決勝全体で gzip 後 1MB 台に収まる
REPLAY_PRE_START = 150.0  # レーススタート前に含める秒数（フォーメーションラップ）
REPLAY_POST_END = 60.0    # 最終ラップ通過後に含める秒数

def replay_payload(entry, ses):
    """全車の X,Y を共通時間グリッドへ線形補間したリプレイ用データ。
    成功時は (raw_json_bytes, gz_bytes) を tel_cache にキャッシュして返し、
    失敗時は {"error": ...} を返す。

    実測に基づく前提（2025 豪州GP決勝 / サウジ予選で検証済み）:
      - pos_data は全ドライバーが同一の SessionTime 軸を持つ（中央値 0.24s 間隔）
      - 欠損は NaN ではなく X==0 かつ Y==0 の行として現れる
      - リタイア車はその後も座標を送り続ける場合があるため laps の最終通過時刻で打ち切る
    """
    cached = entry["tel_cache"].get("__replay__")
    if cached is not None:
        return cached

    try:
        pos = ses.pos_data
    except Exception as exc:
        return {"error": f"position data unavailable: {exc}"}
    if not pos:
        return {"error": "position data unavailable"}

    circuit = _circuit_info(entry, ses)
    rotation = circuit["rotation"]

    # ドライバー番号 -> 略称
    num_to_abbr = {}
    results = ses.results
    if results is not None and len(results) > 0:
        for _, row in results.iterrows():
            n, a = text(row.get("DriverNumber")), text(row.get("Abbreviation"))
            if n and a:
                num_to_abbr[n] = a

    # ラップ由来の基準時刻（レーススタート・各車の最終ライン通過）
    laps = ses.laps
    race_start = None
    last_et = {}
    if laps is not None and len(laps) > 0:
        lap1 = laps[laps["LapNumber"] == 1]["LapStartTime"].dropna()
        if len(lap1) > 0:
            race_start = float(lap1.min().total_seconds())
        for abbr in laps["Driver"].dropna().unique().tolist():
            ets = laps[laps["Driver"] == abbr]["Time"].dropna()
            if len(ets) > 0:
                last_et[abbr] = float(ets.max().total_seconds())

    # 時間範囲: 位置データの実範囲と、スタート前150s〜最終通過+60s の共通部分
    sample_df = next(iter(pos.values()))
    pos_t = sample_df["SessionTime"].dt.total_seconds()
    pos_lo, pos_hi = float(pos_t.min()), float(pos_t.max())
    t_lo = pos_lo if race_start is None else max(pos_lo, race_start - REPLAY_PRE_START)
    t_hi = pos_hi if not last_et else min(pos_hi, max(last_et.values()) + REPLAY_POST_END)
    if t_hi - t_lo > 4 * 3600:
        t_hi = t_lo + 4 * 3600
    if t_hi <= t_lo:
        return {"error": "position data time range is empty"}
    grid = np.arange(t_lo, t_hi + 1e-9, REPLAY_DT)

    cars = []
    for num_str, df in pos.items():
        if df is None or len(df) == 0:
            continue
        abbr = num_to_abbr.get(str(num_str)) or str(num_str)
        t_arr = df["SessionTime"].dt.total_seconds().to_numpy()
        x_arr = df["X"].to_numpy(dtype=float)
        y_arr = df["Y"].to_numpy(dtype=float)
        valid = ~((x_arr == 0.0) & (y_arr == 0.0))
        if int(valid.sum()) < 5:
            continue
        t_v, x_v, y_v = t_arr[valid], x_arr[valid], y_arr[valid]
        cutoff = float(t_v[-1])
        if abbr in last_et:
            cutoff = min(cutoff, last_et[abbr] + REPLAY_POST_END)
        i0 = int(np.searchsorted(grid, float(t_v[0]), "left"))
        i1 = int(np.searchsorted(grid, cutoff, "right")) - 1
        if i1 - i0 < 4:
            continue
        sub = grid[i0:i1 + 1]
        x_i = np.interp(sub, t_v, x_v)
        y_i = np.interp(sub, t_v, y_v)
        x_r, y_r = _rotate_xy(x_i, y_i, rotation)
        cars.append({
            "abbr": abbr,
            "i0": i0, "i1": i1,
            "x": [int(round(v)) for v in x_r],
            "y": [int(round(v)) for v in y_r],
        })

    if not cars:
        return {"error": "no usable position data"}

    payload = {
        "t0": round(float(grid[0]), 3),
        "dt": REPLAY_DT,
        "n": int(len(grid)),
        "race_start": round(race_start, 3) if race_start is not None else None,
        "rotation": rotation,
        "cars": cars,
    }
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    result = (raw, gzip.compress(raw, 6))
    entry["tel_cache"]["__replay__"] = result
    logging.info("Replay payload built: %d cars, %d samples, %d KB (gz %d KB)",
                 len(cars), len(grid), len(raw) // 1024, len(result[1]) // 1024)
    return result


# ---------------------------------------------------------------------------
# HTTP ハンドラ
# ---------------------------------------------------------------------------

STORE = SessionStore()

MIME = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".ico": "image/x-icon",
    ".woff2": "font/woff2",
}


class Handler(BaseHTTPRequestHandler):
    server_version = "PitwallF1/1.0"

    def log_message(self, fmt, *args):
        logging.info("%s %s", self.address_string(), fmt % args)

    # --- 共通レスポンス ---

    def _send_bytes(self, data, content_type, status=200, gz=False, cache=False):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        if gz:
            self.send_header("Content-Encoding", "gzip")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "max-age=3600" if cache else "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _send_json(self, obj, status=200):
        raw = json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        if len(raw) > 8192 and "gzip" in (self.headers.get("Accept-Encoding") or ""):
            self._send_bytes(gzip.compress(raw, 6), "application/json; charset=utf-8", status, gz=True)
        else:
            self._send_bytes(raw, "application/json; charset=utf-8", status)

    def _send_error_json(self, message, status=400):
        self._send_json({"error": message}, status=status)

    # --- ルーティング ---

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = {k: v[0] for k, v in parse_qs(parsed.query).items()}
        try:
            if path.startswith("/api/"):
                self._handle_api(path, query)
            else:
                self._handle_static(path)
        except (ConnectionAbortedError, BrokenPipeError):
            pass
        except Exception as exc:
            logging.error("Request failed: %s\n%s", self.path, traceback.format_exc())
            try:
                self._send_error_json(f"{type(exc).__name__}: {exc}", status=500)
            except Exception:
                pass

    def _session_params(self, query):
        year = int(query.get("year", "0"))
        rnd = int(query.get("round", "0"))
        code = query.get("session", "R")
        if year < FIRST_YEAR or year > datetime.now().year:
            raise ValueError(f"year out of range: {year}")
        if rnd < 1:
            raise ValueError(f"round out of range: {rnd}")
        if code not in SESSION_NAME_TO_CODE.values():
            raise ValueError(f"unknown session code: {code}")
        return year, rnd, code

    def _handle_api(self, path, query):
        if path == "/api/health":
            self._send_json({"ok": True, "fastf1": fastf1.__version__})
            return

        if path == "/api/years":
            years = list(range(datetime.now().year, FIRST_YEAR - 1, -1))
            self._send_json({"years": years, "first_year": FIRST_YEAR})
            return

        if path == "/api/schedule":
            year = int(query.get("year", "0"))
            if year < FIRST_YEAR or year > datetime.now().year:
                self._send_error_json(f"year out of range: {year}")
                return
            self._send_json(STORE.get_schedule(year))
            return

        if path == "/api/load":
            year, rnd, code = self._session_params(query)
            self._send_json(STORE.request_load(year, rnd, code))
            return

        if path == "/api/status":
            year, rnd, code = self._session_params(query)
            self._send_json(STORE.status(year, rnd, code))
            return

        if path == "/api/session":
            year, rnd, code = self._session_params(query)
            entry = STORE.entry(year, rnd, code)
            if entry is None or entry["state"] != "ready":
                self._send_error_json("session not loaded", status=409)
                return
            if "gzip" in (self.headers.get("Accept-Encoding") or ""):
                self._send_bytes(entry["bundle_gz"], "application/json; charset=utf-8", gz=True)
            else:
                self._send_bytes(entry["bundle_raw"], "application/json; charset=utf-8")
            return

        if path == "/api/telemetry":
            year, rnd, code = self._session_params(query)
            entry = STORE.entry(year, rnd, code)
            if entry is None or entry["state"] != "ready":
                self._send_error_json("session not loaded", status=409)
                return
            abbrs = [a for a in (query.get("drivers", "").split(",")) if a][:6]
            if not abbrs:
                self._send_error_json("drivers parameter required")
                return
            lap_sel = query.get("lap", "fastest")
            self._send_json(telemetry_payload(entry, entry["session"], abbrs, lap_sel))
            return

        if path == "/api/trackmap":
            year, rnd, code = self._session_params(query)
            entry = STORE.entry(year, rnd, code)
            if entry is None or entry["state"] != "ready":
                self._send_error_json("session not loaded", status=409)
                return
            self._send_json(trackmap_payload(entry, entry["session"]))
            return

        if path == "/api/replay":
            year, rnd, code = self._session_params(query)
            entry = STORE.entry(year, rnd, code)
            if entry is None or entry["state"] != "ready":
                self._send_error_json("session not loaded", status=409)
                return
            result = replay_payload(entry, entry["session"])
            if isinstance(result, dict):
                self._send_json(result)
                return
            raw, gz = result
            if "gzip" in (self.headers.get("Accept-Encoding") or ""):
                self._send_bytes(gz, "application/json; charset=utf-8", gz=True)
            else:
                self._send_bytes(raw, "application/json; charset=utf-8")
            return

        self._send_error_json(f"unknown api path: {path}", status=404)

    def _handle_static(self, path):
        if path in ("/", ""):
            path = "/index.html"
        rel = path.lstrip("/")
        target = (WEB_DIR / rel).resolve()
        if not str(target).startswith(str(WEB_DIR.resolve())) or not target.is_file():
            self._send_error_json("not found", status=404)
            return
        content_type = MIME.get(target.suffix.lower(), "application/octet-stream")
        self._send_bytes(target.read_bytes(), content_type)


def main():
    parser = argparse.ArgumentParser(description="PITWALL - F1 web dashboard server")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO,
                        format="[%(asctime)s] %(levelname)s %(message)s")

    cache_path = Path(CACHE_DIR)
    cache_path.mkdir(parents=True, exist_ok=True)
    fastf1.Cache.enable_cache(str(cache_path))
    logging.info("FastF1 cache: %s", cache_path.resolve())

    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    url = f"http://127.0.0.1:{args.port}/"
    logging.info("PITWALL running at %s", url)
    if not args.no_browser:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logging.info("Shutting down.")
        server.shutdown()


if __name__ == "__main__":
    main()
