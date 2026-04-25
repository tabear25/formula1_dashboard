import math
import tkinter as tk


def _hex_to_rgb(color):
    c = color.lstrip('#')
    return (int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16))


def _rgb_to_hex(r, g, b):
    return f'#{int(r):02x}{int(g):02x}{int(b):02x}'


def _lerp_color(start, end, t):
    t = max(0.0, min(1.0, t))
    sr, sg, sb = _hex_to_rgb(start)
    er, eg, eb = _hex_to_rgb(end)
    return _rgb_to_hex(
        sr + (er - sr) * t,
        sg + (eg - sg) * t,
        sb + (eb - sb) * t,
    )


def fade_in_label(label, from_color, to_color, duration=400, steps=20):
    """Animate a label's text color from from_color to to_color."""
    delay = max(1, duration // steps)

    def _step(n):
        if n > steps:
            return
        try:
            label.configure(fg=_lerp_color(from_color, to_color, n / steps))
            label.after(delay, _step, n + 1)
        except tk.TclError:
            pass

    _step(0)


def typewriter_effect(label, text, delay=40, on_done=None):
    """Reveal text in label one character at a time."""
    def _type(n):
        if n > len(text):
            if on_done:
                on_done()
            return
        try:
            label.configure(text=text[:n])
            label.after(delay, _type, n + 1)
        except tk.TclError:
            pass

    _type(0)


def animate_treeview_rows(tree, rows_data, delay=40):
    """Insert rows into a Treeview one at a time with a delay between each."""
    def _insert(i):
        if i >= len(rows_data):
            return
        try:
            tree.insert("", "end", values=rows_data[i])
            tree.after(delay, _insert, i + 1)
        except tk.TclError:
            pass

    _insert(0)


class CloudLoader(tk.Canvas):
    """Sine-wave bouncing-dot cloud loading animation widget."""
    _DOT_COUNT = 5
    _DOT_R = 8
    _SPACING = 24
    _BOUNCE = 12
    _CYCLE = 40
    _FRAME_MS = 40

    def __init__(self, master, bg_color, dot_color, **kw):
        self._cw = self._DOT_COUNT * self._SPACING + self._DOT_R * 2
        self._ch = self._BOUNCE * 2 + self._DOT_R * 2 + 8
        super().__init__(master, width=self._cw, height=self._ch,
                         bg=bg_color, highlightthickness=0, **kw)
        self._dots = []
        self._tick = 0
        self._running = False
        self._job = None
        cy = self._ch // 2
        x0 = self._DOT_R + self._SPACING // 2
        for i in range(self._DOT_COUNT):
            x = x0 + i * self._SPACING
            r = self._DOT_R
            dot = self.create_oval(x - r, cy - r, x + r, cy + r,
                                   fill=dot_color, outline='')
            self._dots.append((dot, x, cy))

    def start(self):
        self._running = True
        self._tick = 0
        self._animate()

    def stop(self):
        self._running = False
        if self._job:
            try:
                self.after_cancel(self._job)
            except tk.TclError:
                pass
            self._job = None

    def _animate(self):
        if not self._running:
            return
        self._tick = (self._tick + 1) % self._CYCLE
        t = self._tick / self._CYCLE
        cy_base = self._ch // 2
        for i, (dot, x, _) in enumerate(self._dots):
            phase = (t + i / self._DOT_COUNT) % 1.0
            bounce = int(self._BOUNCE * (math.sin(phase * 2 * math.pi) * 0.5 + 0.5))
            r = self._DOT_R
            cy = cy_base - bounce
            self.coords(dot, x - r, cy - r, x + r, cy + r)
        self._job = self.after(self._FRAME_MS, self._animate)


def show_chart_with_loader(frame, loading_text, bg_color, dot_color, render_fn):
    """Display a CloudLoader animation, then call render_fn after a brief delay.

    render_fn() runs on the main thread and should add chart widgets directly to frame.
    The loader is destroyed before render_fn is called.
    """
    loader_wrap = tk.Frame(frame, bg=bg_color)
    loader_wrap.pack(expand=True)

    tk.Label(loader_wrap, text=loading_text, fg=dot_color, bg=bg_color,
             font=('TkDefaultFont', 10)).pack(pady=(0, 6))

    loader = CloudLoader(loader_wrap, bg_color=bg_color, dot_color=dot_color)
    loader.pack()
    loader.start()

    def _do_render():
        loader.stop()
        try:
            loader_wrap.destroy()
        except tk.TclError:
            pass
        render_fn()

    frame.after(80, _do_render)
