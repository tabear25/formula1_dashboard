# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the Application

```bash
python main.py
```

Install dependencies first:
```bash
pip install -r requirements.txt
```

There are no automated tests. Verification is done by running the app and exercising the UI manually.

## Architecture

This is a **tkinter desktop app** that uses FastF1 to fetch and visualize F1 race data. The entry point is `main.py`, which creates `F1DashboardApp(tk.Tk)`.

### Layout

```
F1DashboardApp (tk.Tk)
└── ttk.PanedWindow (horizontal)
    ├── Sidebar (tk.Frame)          ← data selection controls + progress bar
    └── MainTab (ttk.Notebook)      ← 8 tab frames, one per visualization
```

### Data flow

1. **Sidebar** (`ui/sidebar.py`) handles all user selections (year → GP → session → drivers).
2. Session loading runs in a background thread via `FastF1Service.load_session_async()` (uses `ThreadPoolExecutor`).
3. When loading completes, the callback uses `self.after(0, ...)` to return to the main thread, then calls the appropriate `MainTab` method.
4. `MainTab` (`ui/main_tab.py`) delegates to per-tab functions defined in `tabs/`.

### Tab pattern

Each tab module in `tabs/` exposes two functions:
- `init_xxx(notebook)` – creates the frame, adds it to the notebook, returns the frame.
- `show_xxx(frame, session, ...)` – clears the frame, displays a `CloudLoader`, then renders the matplotlib figure via `show_chart_with_loader()` from `ui/animations.py`.

`MainTab` stores each frame as an attribute and provides a method (e.g. `show_map`, `show_single_driver_telemetry`) that selects the tab and calls the corresponding `show_xxx`.

### Threading rule

**All tkinter widget operations must happen on the main thread.** Background threads (FastF1 data loading) communicate back via `widget.after(0, callback)`. Never call `.pack()`, `.configure()`, or widget constructors from a worker thread.

### Animation system (`ui/animations.py`)

- `show_chart_with_loader(frame, text, bg, fg, render_fn)` — shows a `CloudLoader` for 80 ms then calls `render_fn()` on the main thread. All chart tabs use this wrapper.
- `CloudLoader` — canvas widget, 5-dot sine-wave bounce animation.
- `typewriter_effect(label, text, delay)` — used by the Overview tab.
- `animate_treeview_rows(tree, rows, delay)` — used by the Results tab.
- `fade_in_label(label, from_color, to_color)` — available for use in any tab.

### Key configuration (`config.py`)

All theme colours, window size, cache path, and `YEAR_LIST` live here. `YEAR_LIST` defaults to 2000–present. `MPL_STYLE = 'fastf1'` applies FastF1's matplotlib style globally at startup.

### FastF1 cache

Data is cached under `_fastf1_cache/` (gitignored). `CacheManager.cleanup_cache()` runs at startup to evict files older than `CACHE_EXPIRE_DAYS` and enforce `CACHE_SIZE_LIMIT_GB`. Requires an internet connection on first load for a given session.

---

_Last updated: 2026-04-25 11:22
