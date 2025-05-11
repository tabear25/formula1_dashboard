from datetime import datetime

# --- Application Wide ---
APP_TITLE = "F1 Data Dashboard"
WINDOW_SIZE = "1366x865" 

"""
2000年から現在までのF1データを取得するためのリスト。
開始年度を変更したい場合は、YEAR_LISTの範囲を変更してください。
"""
YEAR_LIST = list(range(2000, datetime.now().year + 1))


# --- Theming Colors ---
COLOR_BG = "#2B2B2B"        # Main background color of the application window
COLOR_FRAME = "#3C3F41"     # Background color for frames, sidebar, unselected notebook tabs
COLOR_TEXT = "#BBBBBB"      # Default text color for labels, etc.
COLOR_ACCENT = "#007ACC"    # Accent color for selected tabs, buttons, progress bar (e.g., a bright blue)
COLOR_HIGHLIGHT = "#FF5722" # Highlight color for specific plot elements (e.g., fastest lap line on map, a distinct orange/red)

# --- Matplotlib Style for FastF1 Plots ---
MPL_STYLE = 'fastf1'

# --- Cache Settings (used by service.py) ---
CACHE_DIR = "_fastf1_cache"
CACHE_SIZE_LIMIT_GB = 2
CACHE_EXPIRE_DAYS = 30

# --- Logging ---
LOG_LEVEL = "INFO"