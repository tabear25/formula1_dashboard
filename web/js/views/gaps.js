// ギャップチャート（レースプログレス）:
//   リーダー基準 = 各周回終了時点の首位との差
//   勝者平均基準 = 優勝者の平均ラップで走る仮想レースカーとの差（レースヒストリーチャート）

import { state, toggleFocus } from "../state.js";
import { el, clearNode, linScale, niceTicks, attachCrosshair, dashArray, lapTicks, gridY, tooltip } from "../svg.js";
import { fmtGap, compoundLetter } from "../format.js";

const M = { top: 30, bottom: 28, left: 74, right: 70 };
const PLOT_H = 460;

let mode = "leader";   // "leader" | "avg"
let clampOutliers = true;

export function renderGaps(container) {
  clearNode(container);
  const { bundle, derived } = state;

  const panel = document.createElement("div");
  panel.className = "panel";
  container.appendChild(panel);

  const head = document.createElement("div");
  head.className = "panel-head";
  const title = document.createElement("div");
  title.className = "panel-title";
  title.textContent = "ギャップ推移";
  const sub = document.createElement("div");
  sub.className = "panel-sub";
  sub.textContent = mode === "leader"
    ? "各周回終了時点でのリーダーとの差（下ほど遅れ）。"
    : "優勝者の平均ペースを基準にした差。水平＝優勝者と同ペース、右肩上がり＝それより速い。";
  head.appendChild(title);
  head.appendChild(sub);

  const controls = document.createElement("div");
  controls.className = "panel-controls";
  controls.appendChild(makeToggle("リーダー基準", mode === "leader", () => { mode = "leader"; renderGaps(container); }));
  controls.appendChild(makeToggle("勝者平均基準", mode === "avg", () => { mode = "avg"; renderGaps(container); }));
  controls.appendChild(makeToggle("外れ値カット", clampOutliers, () => { clampOutliers = !clampOutliers; renderGaps(container); }));
  head.appendChild(controls);
  panel.appendChild(head);

  const host = document.createElement("div");
  host.className = "chart-host";
  panel.appendChild(host);

  const drivers = bundle.drivers;
  const maxLap = derived.maxLap;
  const width = Math.max(680, host.clientWidth || container.clientWidth || 900);
  const height = M.top + M.bottom + PLOT_H;

  const svg = el("svg", { viewBox: `0 0 ${width} ${height}`, width, height });
  host.appendChild(svg);
  const plot = { x0: M.left, x1: width - M.right, y0: M.top, y1: height - M.bottom };
  const x = linScale(0.6, maxLap + 0.3, plot.x0, plot.x1);

  // ギャップ辞書 abbr -> lap -> gap(リーダー基準)
  const gapAt = new Map();
  for (const [lap, tower] of derived.towerPerLap) {
    for (const t of tower) {
      if (!gapAt.has(t.abbr)) gapAt.set(t.abbr, new Map());
      gapAt.get(t.abbr).set(lap, t.gap);
    }
  }

  // 系列値の計算
  const series = [];
  const allVals = [];
  for (const d of drivers) {
    const lapsArr = derived.lapsByDriver.get(d.abbr) ?? [];
    const pts = [];
    for (const rec of lapsArr) {
      let val = null;
      if (mode === "leader") {
        val = gapAt.get(d.abbr)?.get(rec.lap) ?? null;
      } else if (derived.historyRef && rec.et != null) {
        val = rec.et - (derived.historyRef.start + derived.historyRef.avg * rec.lap);
      }
      if (val == null) continue;
      pts.push({ lap: rec.lap, val, cmp: rec.cmp, pit: rec.pit_in });
      allVals.push(val);
    }
    if (pts.length === 0) continue;
    series.push({
      abbr: d.abbr, color: d.color, dash: d.dash, pts,
      valAt: new Map(pts.map((p) => [p.lap, p.val])),
      finished: derived.finished.get(d.abbr) ?? false,
    });
  }

  if (series.length === 0) {
    host.innerHTML = `<div class="empty-note">ギャップを計算できるデータがありません。</div>`;
    return;
  }

  allVals.sort((a, b) => a - b);
  const q = (p) => allVals[Math.min(allVals.length - 1, Math.floor(p * allVals.length))];
  let vMin = allVals[0];
  let vMax = allVals[allVals.length - 1];
  if (clampOutliers && allVals.length > 20) {
    vMax = Math.min(vMax, q(0.92) * 1.1 + 5);
  }
  const pad = (vMax - vMin) * 0.03;
  const y = linScale(vMin - pad, vMax + pad, plot.y0, plot.y1);

  // クリップ（カットした系列がはみ出さないように）
  const defs = el("defs", {}, svg);
  const clip = el("clipPath", { id: "gaps-clip" }, defs);
  el("rect", { x: plot.x0 - 2, y: plot.y0 - 2, width: plot.x1 - plot.x0 + 4, height: plot.y1 - plot.y0 + 4 }, clip);

  // 帯 + グリッド
  for (const band of derived.bands) {
    const bx0 = x(Math.max(0.6, band.from - 0.5));
    const bx1 = x(band.to + 0.5);
    const fill = band.kind === "RED" ? "var(--red-band)" : band.kind === "VSC" ? "var(--vsc-band)" : "var(--sc-band)";
    el("rect", { x: bx0, y: plot.y0, width: bx1 - bx0, height: plot.y1 - plot.y0, fill }, svg);
    if (bx1 - bx0 >= 18) {
      el("text", {
        class: `band-label${band.kind === "RED" ? " red" : ""}`,
        x: (bx0 + bx1) / 2, y: plot.y0 - 6, "text-anchor": "middle",
        text: band.kind === "RED" ? "赤旗" : band.kind,
      }, svg);
    }
  }
  const gridG = el("g", {}, svg);
  gridY(gridG, y, niceTicks(y.domain[0], y.domain[1], 7), plot.x0, plot.x1,
    (v) => `${v > 0 ? "+" : ""}${Math.round(v)}s`);
  for (const lap of lapTicks(maxLap, plot.x1 - plot.x0)) {
    el("text", { class: "axis-label", x: x(lap), y: plot.y1 + 17, "text-anchor": "middle", text: lap }, gridG);
  }
  el("text", { class: "axis-label", x: plot.x1 + 6, y: plot.y1 + 17, text: "Lap" }, gridG);

  const focus = state.focus;
  const hasFocus = focus.size > 0;
  let hoverAbbr = null;

  const linesG = el("g", { fill: "none", "clip-path": "url(#gaps-clip)", "stroke-linejoin": "round", "stroke-linecap": "round" }, svg);
  const lineEls = new Map();
  for (const s of series) {
    const points = s.pts.map((p) => `${x(p.lap)},${y(p.val)}`).join(" ");
    const line = el("polyline", {
      points, stroke: s.color, "stroke-width": 2, "stroke-dasharray": dashArray(s.dash),
    }, linesG);
    lineEls.set(s.abbr, line);
    const lastPt = s.pts[s.pts.length - 1];
    if (!s.finished && lastPt.val <= y.domain[1]) {
      const cx = x(lastPt.lap), cy = y(lastPt.val);
      el("path", {
        d: `M${cx - 4},${cy - 4}L${cx + 4},${cy + 4}M${cx - 4},${cy + 4}L${cx + 4},${cy - 4}`,
        stroke: "var(--bad)", "stroke-width": 2,
      }, linesG);
    }
  }

  // ピットドット
  const pitsG = el("g", { "clip-path": "url(#gaps-clip)" }, svg);
  for (const s of series) {
    const idx = derived.lapIndex.get(s.abbr);
    for (const p of s.pts) {
      if (!p.pit) continue;
      const next = idx?.get(p.lap + 1);
      const color = next?.cmp ? (bundle.compound_colors[next.cmp] ?? "#8a8f9c") : "#8a8f9c";
      const dot = el("circle", {
        cx: x(p.lap), cy: y(p.val), r: 4,
        fill: color, stroke: "var(--surface-1)", "stroke-width": 2,
      }, pitsG);
      dot.dataset.abbr = s.abbr;
    }
  }

  // 右端ラベル（クリップ内に収まる系列のみ）
  const labelsG = el("g", {}, svg);
  const labelCandidates = series
    .map((s) => ({ s, lastPt: s.pts[s.pts.length - 1] }))
    .filter(({ lastPt }) => lastPt.val <= y.domain[1] && lastPt.val >= y.domain[0]);
  const ys = resolveCollisions(labelCandidates.map(({ lastPt }) => y(lastPt.val)), 11.5);
  labelCandidates.forEach(({ s }, i) => {
    const label = el("text", {
      class: "drv-label", x: plot.x1 + 8, y: ys[i] + 3.5, text: s.abbr,
    }, labelsG);
    el("line", {
      x1: plot.x1 + 8 + s.abbr.length * 7 + 4, x2: plot.x1 + 8 + s.abbr.length * 7 + 16,
      y1: ys[i], y2: ys[i], stroke: s.color, "stroke-width": 3,
      "stroke-dasharray": dashArray(s.dash), "stroke-linecap": "round",
    }, labelsG);
    label.addEventListener("click", () => toggleFocus(s.abbr));
    label.classList.toggle("dim", hasFocus && !focus.has(s.abbr));
  });

  applyEmphasis();
  function applyEmphasis() {
    for (const s of series) {
      const line = lineEls.get(s.abbr);
      let op = 0.92, w = 2;
      if (hoverAbbr) { op = s.abbr === hoverAbbr ? 1 : 0.13; w = s.abbr === hoverAbbr ? 3.2 : 2; }
      else if (hasFocus) { op = focus.has(s.abbr) ? 1 : 0.13; w = focus.has(s.abbr) ? 3 : 2; }
      line.setAttribute("opacity", op);
      line.setAttribute("stroke-width", w);
    }
    for (const dot of pitsG.querySelectorAll("circle")) {
      const abbr = dot.dataset.abbr;
      let op = 1;
      if (hoverAbbr) op = abbr === hoverAbbr ? 1 : 0.12;
      else if (hasFocus) op = focus.has(abbr) ? 1 : 0.12;
      dot.setAttribute("opacity", op);
    }
  }

  attachCrosshair(svg, plot, {
    snap(px) {
      const lap = Math.max(1, Math.min(maxLap, Math.round(x.invert(px))));
      return { px: x(lap), lap };
    },
    onMove(snapped, clientX, clientY, localY) {
      const lap = snapped.lap;
      let nearest = null, bestDy = 15;
      for (const s of series) {
        const val = s.valAt.get(lap);
        if (val == null) continue;
        const dy = Math.abs(y(val) - localY);
        if (dy < bestDy) { bestDy = dy; nearest = s.abbr; }
      }
      if (nearest !== hoverAbbr) { hoverAbbr = nearest; applyEmphasis(); }

      const tower = derived.towerPerLap.get(lap) ?? [];
      const kind = derived.statusPerLap.get(lap);
      const rows = tower.map((t) => {
        const d = derived.driverMap.get(t.abbr);
        return {
          color: d?.color, dash: d?.dash,
          label: `P${t.pos} ${t.abbr}`,
          value: t.pos === 1 ? "Leader" : fmtGap(t.gap, 1),
          extra: `${compoundLetter(t.cmp)}${t.life ?? ""}${t.pit ? " ●PIT" : ""}`,
          valueColor: t.abbr === hoverAbbr ? "#ffffff" : undefined,
        };
      });
      tooltip.showRows(clientX, clientY, {
        title: `Lap ${lap}/${derived.totalLaps}${kind ? `　[${kind === "RED" ? "赤旗" : kind}]` : ""}`,
        rows,
      });
    },
    onLeave() { hoverAbbr = null; applyEmphasis(); },
  });

  svg.addEventListener("click", (evt) => {
    const rect = svg.getBoundingClientRect();
    const sx = svg.viewBox.baseVal.width / rect.width;
    const lx = (evt.clientX - rect.left) * sx;
    const lyv = (evt.clientY - rect.top) * (svg.viewBox.baseVal.height / rect.height);
    if (lx < plot.x0 || lx > plot.x1 || lyv < plot.y0 || lyv > plot.y1) return;
    const lap = Math.max(1, Math.min(maxLap, Math.round(x.invert(lx))));
    let nearest = null, bestDy = 14;
    for (const s of series) {
      const val = s.valAt.get(lap);
      if (val == null) continue;
      const dy = Math.abs(y(val) - lyv);
      if (dy < bestDy) { bestDy = dy; nearest = s.abbr; }
    }
    if (nearest) toggleFocus(nearest);
  });
}

function makeToggle(label, on, onClick) {
  const btn = document.createElement("button");
  btn.className = `toggle-btn${on ? " on" : ""}`;
  btn.textContent = label;
  btn.addEventListener("click", onClick);
  return btn;
}

function resolveCollisions(ys, minGap) {
  const idx = ys.map((v, i) => ({ v, i })).sort((a, b) => a.v - b.v);
  for (let k = 1; k < idx.length; k++) {
    if (idx[k].v - idx[k - 1].v < minGap) idx[k].v = idx[k - 1].v + minGap;
  }
  const out = new Array(ys.length);
  for (const { v, i } of idx) out[i] = v;
  return out;
}
