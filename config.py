import os
from pathlib import Path
from datetime import datetime

"""
このモジュールはアプリケーションの設定を管理しています。
YEAR_LIST=システムで取り扱う年度を定義します。
F1が始まった1950年からリストするようにしています。
"""

# ─────────────────────────────────────────────────
# アプリケーション設定
# ─────────────────────────────────────────────────
APP_TITLE   = "F1 Information Dashboard"
WINDOW_SIZE = "1400x900"

# ─────────────────────────────────────────────────
# カラー定義
# ─────────────────────────────────────────────────
COLOR_BG        = "#161E2F"
COLOR_FRAME     = "#242F48"
COLOR_FRAME_2   = "#384358"
COLOR_ACCENT    = "#B51A2B"
COLOR_ACCENT_2  = "#591A2E"
COLOR_HIGHLIGHT = "#FFA586"
COLOR_TEXT      = "#FFFFFF"

# ─────────────────────────────────────────────────
# キャッシュとデータ設定
# ─────────────────────────────────────────────────
CACHE_DIR           = Path(os.getenv("TEMP", ".")) / "fastf1_cache"
CACHE_SIZE_LIMIT_GB = 2
CACHE_EXPIRE_DAYS   = 30

# ─────────────────────────────────────────────────
# 年リスト（1950〜今年）
# ─────────────────────────────────────────────────
YEAR_LIST = list(range(1950, datetime.now().year + 1))
