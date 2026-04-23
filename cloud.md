# Cloud Animations

Animations for every piece of data in the F1 Dashboard — implemented via `ui/animations.py`.

## Animation Types

### 1. CloudLoader — chart tabs
A row of five dots that bounce in a left-to-right sine wave, shown while each chart is being prepared.

- **Used in**: Map, Telemetry, LapTime Compare, Speed Compare, Scatter Compare, Lap Scatter
- **Frame interval**: 40 ms (≈25 fps)
- **Dot colour**: `COLOR_ACCENT` (#007ACC) on `COLOR_FRAME` (#3C3F41)

### 2. Typewriter Effect — Overview tab
Text is revealed one character at a time, giving a dynamic typing feel on startup and whenever the overview is reset.

- **Used in**: `tabs/overview.py` (`init_overview`, `show_overview`)
- **Speed**: 30 ms per character

### 3. Animated Row Insertion — Results tab
Each result row slides into the Treeview table one at a time with a short staggered delay.

- **Used in**: `tabs/results_tab.py` (`show_session_results`)
- **Delay**: 40 ms per row

### 4. Fade-In Label (`fade_in_label`)
Interpolates a label's foreground colour from the background colour to the target text colour.

- **Available for use** in any tab or widget
- **Default**: 400 ms, 20 steps

## Module Reference

```
ui/animations.py
```

| Symbol | Purpose |
|---|---|
| `CloudLoader` | Canvas widget — bouncing-dot animation |
| `show_chart_with_loader(frame, text, bg, fg, fn)` | Wrap any chart render with a CloudLoader |
| `typewriter_effect(label, text, delay, on_done)` | Character-by-character text reveal |
| `animate_treeview_rows(tree, rows, delay)` | Staggered row insertion |
| `fade_in_label(label, from_color, to_color, duration, steps)` | Colour-interpolation fade |

## How `show_chart_with_loader` Works

1. A `CloudLoader` is packed into the target frame and `.start()` is called.
2. `frame.after(80, ...)` is scheduled — the event loop runs and displays the animation.
3. After 80 ms the loader is destroyed and `render_fn()` is called on the main thread.
4. `render_fn()` adds the matplotlib canvas (and any title labels) directly to `frame`.

This gives visible loading feedback before the matplotlib render begins.

## Fixes Made

- `main.py`: Removed three redundant `'COLOR_HIGHLIGHT' in globals()` guards — `COLOR_HIGHLIGHT` is always imported.
- `scatter_tab.py`: Replaced `plt.subplots()` with `fig.subplots()` to avoid pyplot global state.
- All chart tabs: Title labels and error labels moved inside `_render()` so the frame is clean before the loader appears.
