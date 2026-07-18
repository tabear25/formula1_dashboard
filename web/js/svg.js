// SVG チャート共通ヘルパ（スケール・軸・グリッド・ツールチップ・クロスヘア）

export const NS = "http://www.w3.org/2000/svg";

export function el(name, attrs = {}, parent = null) {
  const node = document.createElementNS(NS, name);
  for (const [k, v] of Object.entries(attrs)) {
    if (v == null) continue;
    if (k === "text") node.textContent = v;
    else node.setAttribute(k, v);
  }
  if (parent) parent.appendChild(node);
  return node;
}

export function clearNode(node) {
  while (node.firstChild) node.removeChild(node.firstChild);
}

export function linScale(d0, d1, r0, r1) {
  const dd = d1 - d0 || 1;
  const scale = (x) => r0 + ((x - d0) / dd) * (r1 - r0);
  scale.invert = (px) => d0 + ((px - r0) / ((r1 - r0) || 1)) * dd;
  scale.domain = [d0, d1];
  scale.range = [r0, r1];
  return scale;
}

export function niceTicks(min, max, count = 6) {
  if (!isFinite(min) || !isFinite(max) || min === max) return [min];
  const span = max - min;
  const step0 = Math.pow(10, Math.floor(Math.log10(span / count)));
  const err = (span / count) / step0;
  const step = step0 * (err >= 7.5 ? 10 : err >= 3.5 ? 5 : err >= 1.5 ? 2 : 1);
  const start = Math.ceil(min / step) * step;
  const ticks = [];
  for (let v = start; v <= max + step * 1e-9; v += step) {
    ticks.push(Math.abs(v) < step * 1e-9 ? 0 : +v.toFixed(10));
  }
  return ticks;
}

export function dashArray(dash) {
  return dash === 1 ? "7 4" : dash === 2 ? "2 3.5" : null;
}

// 水平グリッド + 左軸ラベル
export function gridY(g, scaleY, ticks, x0, x1, fmt = (v) => String(v)) {
  for (const t of ticks) {
    const y = scaleY(t);
    el("line", { class: "gridline", x1: x0, x2: x1, y1: y, y2: y }, g);
    el("text", { class: "axis-label", x: x0 - 8, y: y + 3.5, "text-anchor": "end", text: fmt(t) }, g);
  }
}

// 下軸（目盛りラベルのみ、グリッドは任意）
export function axisX(g, scaleX, ticks, y, { grid = null, fmt = (v) => String(v), y0 = 0, y1 = 0 } = {}) {
  for (const t of ticks) {
    const x = scaleX(t);
    if (grid) el("line", { class: "gridline", x1: x, x2: x, y1: y0, y2: y1 }, g);
    el("text", { class: "axis-label", x, y, "text-anchor": "middle", text: fmt(t) }, g);
  }
}

export function polylinePoints(xs, ys) {
  const parts = [];
  for (let i = 0; i < xs.length; i++) {
    if (xs[i] == null || ys[i] == null) continue;
    parts.push(`${xs[i]},${ys[i]}`);
  }
  return parts.join(" ");
}

// ---------------------------------------------------------------- tooltip

const tipEl = document.getElementById("viz-tooltip");

export const tooltip = {
  showRows(clientX, clientY, { title = null, rows = [] }) {
    clearNode(tipEl);
    if (title) {
      const t = document.createElement("div");
      t.className = "tt-title";
      t.textContent = title;
      tipEl.appendChild(t);
    }
    const table = document.createElement("table");
    for (const row of rows) {
      const tr = document.createElement("tr");
      if (row.dim) tr.className = "tt-dim";

      const tdKey = document.createElement("td");
      tdKey.className = "tt-key";
      if (row.color) {
        const key = document.createElement("span");
        key.className = "tt-line";
        key.style.borderTopColor = row.color;
        if (row.dash === 1) key.style.borderTopStyle = "dashed";
        else if (row.dash === 2) key.style.borderTopStyle = "dotted";
        tdKey.appendChild(key);
      }
      tr.appendChild(tdKey);

      const tdLabel = document.createElement("td");
      tdLabel.className = "tt-label";
      tdLabel.textContent = row.label ?? "";
      tr.appendChild(tdLabel);

      const tdValue = document.createElement("td");
      tdValue.className = "tt-value";
      tdValue.textContent = row.value ?? "";
      if (row.valueColor) tdValue.style.color = row.valueColor;
      tr.appendChild(tdValue);

      if (row.extra != null) {
        const tdExtra = document.createElement("td");
        tdExtra.className = "tt-label";
        tdExtra.textContent = row.extra;
        tr.appendChild(tdExtra);
      }
      table.appendChild(tr);
    }
    tipEl.appendChild(table);
    this._position(clientX, clientY);
  },

  _position(clientX, clientY) {
    tipEl.style.display = "block";
    const pad = 14;
    const rect = tipEl.getBoundingClientRect();
    let x = clientX + pad;
    let y = clientY + pad;
    if (x + rect.width > window.innerWidth - 8) x = clientX - rect.width - pad;
    if (y + rect.height > window.innerHeight - 8) y = clientY - rect.height - pad;
    tipEl.style.left = `${Math.max(4, x)}px`;
    tipEl.style.top = `${Math.max(4, y)}px`;
  },

  hide() {
    tipEl.style.display = "none";
  },
};

// --------------------------------------------------------------- crosshair
// svg 上の pointermove を拾い、プロット領域内なら X 位置をスナップして通知する。
// snap: (plotX) => {px, ...payload} | null

export function attachCrosshair(svg, plot, { snap, onMove, onLeave }) {
  const overlay = el("g", { "pointer-events": "none" }, svg);
  const line = el("line", {
    class: "crosshair", y1: plot.y0, y2: plot.y1, visibility: "hidden",
  }, overlay);

  function toLocal(evt) {
    const rect = svg.getBoundingClientRect();
    const scaleX = svg.viewBox.baseVal.width ? svg.viewBox.baseVal.width / rect.width : 1;
    const scaleY = svg.viewBox.baseVal.height ? svg.viewBox.baseVal.height / rect.height : 1;
    return { x: (evt.clientX - rect.left) * scaleX, y: (evt.clientY - rect.top) * scaleY };
  }

  function hide() {
    line.setAttribute("visibility", "hidden");
    tooltip.hide();
    if (onLeave) onLeave();
  }

  svg.addEventListener("pointermove", (evt) => {
    const { x, y } = toLocal(evt);
    if (x < plot.x0 - 4 || x > plot.x1 + 4 || y < plot.y0 - 4 || y > plot.y1 + 4) {
      hide();
      return;
    }
    const snapped = snap(Math.max(plot.x0, Math.min(plot.x1, x)));
    if (!snapped) { hide(); return; }
    line.setAttribute("x1", snapped.px);
    line.setAttribute("x2", snapped.px);
    line.setAttribute("visibility", "visible");
    onMove(snapped, evt.clientX, evt.clientY, y);
  });
  svg.addEventListener("pointerleave", hide);
  return { hide };
}

// 表示幅に応じたラップ目盛り間隔
export function lapTickStep(maxLap, plotWidth) {
  const perLap = plotWidth / Math.max(1, maxLap);
  if (perLap > 26) return 1;
  if (perLap > 13) return 2;
  if (perLap > 6) return 5;
  return 10;
}

export function lapTicks(maxLap, plotWidth) {
  const step = lapTickStep(maxLap, plotWidth);
  const ticks = [];
  for (let lap = step; lap <= maxLap; lap += step) ticks.push(lap);
  if (ticks[0] !== 1) ticks.unshift(1);
  return ticks;
}
