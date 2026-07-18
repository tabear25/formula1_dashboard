// ラップチャート: 周回ごとの順位推移。
// davidor/formula1-lap-charts (Chris Pudney のD3チャート) のオマージュを
// チームカラー・SC/VSC帯・タイヤ・タイミングタワー tooltip で現代化したもの。

import { state, toggleFocus } from "../state.js";
import { el, clearNode, linScale, attachCrosshair, dashArray, lapTicks, tooltip } from "../svg.js";
import { fmtGap, compoundLetter } from "../format.js";

const M = { top: 30, bottom: 26, left: 92, right: 92 };
const ROW_H = 24;

export function renderLapChart(container) {
  clearNode(container);
  const { bundle, derived } = state;
  const panel = document.createElement("div");
  panel.className = "panel";
  container.appendChild(panel);

  const head = document.createElement("div");
  head.className = "panel-head";
  head.innerHTML = `<div class="panel-title">ラップチャート</div>
    <div class="panel-sub">周回ごとの順位。左＝グリッド順 / 右＝最終結果。ドット＝ピットストップ（色は次のタイヤ）。クリックでドライバーを選択。</div>`;
  panel.appendChild(head);

  const host = document.createElement("div");
  host.className = "chart-host";
  panel.appendChild(host);

  const drivers = bundle.drivers;
  const n = drivers.length;
  const maxLap = derived.maxLap;
  const width = Math.max(680, host.clientWidth || container.clientWidth || 900);
  const height = M.top + M.bottom + n * ROW_H;

  const svg = el("svg", { viewBox: `0 0 ${width} ${height}`, width, height });
  host.appendChild(svg);

  const x = linScale(0, maxLap + 0.3, M.left, width - M.right);
  const y = linScale(1, n, M.top + ROW_H / 2, height - M.bottom - ROW_H / 2);

  const plot = { x0: M.left, x1: width - M.right, y0: M.top, y1: height - M.bottom };

  // --- SC/VSC/赤旗の帯 ---
  const bandsG = el("g", {}, svg);
  for (const band of derived.bands) {
    const bx0 = x(Math.max(0.5, band.from - 0.5));
    const bx1 = x(band.to + 0.5);
    const cls = band.kind === "RED" ? "var(--red-band)"
      : band.kind === "VSC" ? "var(--vsc-band)" : "var(--sc-band)";
    el("rect", { x: bx0, y: plot.y0, width: bx1 - bx0, height: plot.y1 - plot.y0, fill: cls }, bandsG);
    if (bx1 - bx0 >= 18) {
      el("text", {
        class: `band-label${band.kind === "RED" ? " red" : ""}`,
        x: (bx0 + bx1) / 2, y: plot.y0 - 6, "text-anchor": "middle",
        text: band.kind === "RED" ? "赤旗" : band.kind,
      }, bandsG);
    }
  }

  // --- ラップ目盛り ---
  const ticksG = el("g", {}, svg);
  for (const lap of lapTicks(maxLap, plot.x1 - plot.x0)) {
    const px = x(lap);
    el("line", { class: "gridline", x1: px, x2: px, y1: plot.y0, y2: plot.y1 }, ticksG);
    el("text", { class: "axis-label", x: px, y: plot.y1 + 16, "text-anchor": "middle", text: lap }, ticksG);
  }
  el("text", { class: "axis-label", x: plot.x1 + 6, y: plot.y1 + 16, text: "Lap" }, ticksG);

  // --- 系列データ ---
  const series = [];
  for (const d of drivers) {
    const lapsArr = derived.lapsByDriver.get(d.abbr) ?? [];
    const pts = [];
    const gridPos = d.grid != null && d.grid >= 1 ? d.grid : n; // 0/不明はピットレーンスタート扱い
    pts.push({ lap: 0, pos: gridPos });
    for (const rec of lapsArr) {
      if (rec.pos != null) pts.push({ lap: rec.lap, pos: rec.pos });
    }
    if (pts.length <= 1 && lapsArr.length === 0) continue;
    series.push({
      abbr: d.abbr, color: d.color, dash: d.dash,
      pts,
      posAt: new Map(pts.map((p) => [p.lap, p.pos])),
      last: pts[pts.length - 1],
      finished: derived.finished.get(d.abbr) ?? false,
    });
  }

  const focus = state.focus;
  const hasFocus = focus.size > 0;
  let hoverAbbr = null;

  const linesG = el("g", { fill: "none", "stroke-linejoin": "round", "stroke-linecap": "round" }, svg);
  const lineEls = new Map();
  for (const s of series) {
    const points = s.pts.map((p) => `${x(p.lap)},${y(p.pos)}`).join(" ");
    const line = el("polyline", {
      points, stroke: s.color, "stroke-width": 2,
      "stroke-dasharray": dashArray(s.dash),
    }, linesG);
    lineEls.set(s.abbr, line);
    if (!s.finished && s.pts.length > 1) {
      const lastPt = s.pts[s.pts.length - 1];
      const cx = x(lastPt.lap), cy = y(lastPt.pos);
      el("path", {
        d: `M${cx - 4},${cy - 4}L${cx + 4},${cy + 4}M${cx - 4},${cy + 4}L${cx + 4},${cy - 4}`,
        stroke: "var(--bad)", "stroke-width": 2,
      }, linesG);
    }
  }

  // --- ピットストップ ---
  const pitsG = el("g", {}, svg);
  for (const s of series) {
    const stops = derived.pitStops.get(s.abbr) ?? [];
    for (const stop of stops) {
      if (stop.pos == null) continue;
      const color = stop.nextCmp ? (bundle.compound_colors[stop.nextCmp] ?? "#8a8f9c") : "#8a8f9c";
      const dot = el("circle", {
        cx: x(stop.lap), cy: y(stop.pos), r: 4.5,
        fill: color, stroke: "var(--surface-1)", "stroke-width": 2,
      }, pitsG);
      dot.dataset.abbr = s.abbr;
    }
  }

  // --- 両側のドライバーラベル ---
  const labelsG = el("g", {}, svg);
  const leftUsed = [];
  for (const s of series) {
    const gridPos = s.posAt.get(0);
    let ly = y(gridPos);
    while (leftUsed.some((v) => Math.abs(v - ly) < 11)) ly += 11;
    leftUsed.push(ly);
    drawDriverLabel(labelsG, s, plot.x0 - 10, ly, "end", `P${gridPos}`);
  }
  // 右は最終結果順（リタイアも分類順で下に並ぶ）
  const rightYs = resolveCollisions(
    drivers.map((d, i) => {
      const s = series.find((sr) => sr.abbr === d.abbr);
      return s ? y(s.last.pos) : y(i + 1);
    }), 12);
  drivers.forEach((d, i) => {
    const s = series.find((sr) => sr.abbr === d.abbr);
    if (!s) return;
    const posLabel = d.classified && /^\d+$/.test(d.classified) ? `P${d.classified}` : (d.classified ?? "—");
    drawDriverLabel(labelsG, s, plot.x1 + 10, rightYs[i], "start", posLabel);
  });

  function drawDriverLabel(g, s, lx, ly, anchor, posText) {
    const label = el("text", {
      class: "drv-label", x: lx, y: ly + 3.5, "text-anchor": anchor,
    }, g);
    const posSpan = el("tspan", { class: "pos-part", text: `${posText} ` }, label);
    el("tspan", { text: s.abbr }, label);
    // 色キー（テキストはデータ色を着ない: 隣の短いラインが識別を担う）
    const keyW = 12;
    const keyX = anchor === "end" ? lx - measure(posText, s.abbr) - keyW - 6 : lx + measure(posText, s.abbr) + 6;
    const key = el("line", {
      x1: keyX, x2: keyX + keyW, y1: ly, y2: ly,
      stroke: s.color, "stroke-width": 3,
      "stroke-dasharray": dashArray(s.dash), "stroke-linecap": "round",
    }, g);
    label.dataset.abbr = s.abbr;
    key.dataset.abbr = s.abbr;
    label.addEventListener("click", () => toggleFocus(s.abbr));
    label.classList.toggle("dim", hasFocus && !focus.has(s.abbr));
    posSpan.dataset.abbr = s.abbr;
  }

  function measure(posText, abbr) {
    return (posText.length + 1 + abbr.length) * 6.4;
  }

  applyEmphasis();

  function applyEmphasis() {
    for (const s of series) {
      const line = lineEls.get(s.abbr);
      let op = 0.92, w = 2;
      if (hoverAbbr) {
        op = s.abbr === hoverAbbr ? 1 : 0.15;
        w = s.abbr === hoverAbbr ? 3.2 : 2;
      } else if (hasFocus) {
        op = focus.has(s.abbr) ? 1 : 0.15;
        w = focus.has(s.abbr) ? 3 : 2;
      }
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

  // --- クロスヘア + タイミングタワー tooltip ---
  attachCrosshair(svg, plot, {
    snap(px) {
      const lap = Math.round(x.invert(px));
      const clamped = Math.max(0, Math.min(maxLap, lap));
      return { px: x(clamped), lap: clamped };
    },
    onMove(snapped, clientX, clientY, localY) {
      const lap = snapped.lap;
      // 近傍ドライバーの検出（ハイライト用）
      let nearest = null, bestDy = 15;
      for (const s of series) {
        const pos = s.posAt.get(lap) ?? nearestPos(s, lap);
        if (pos == null) continue;
        const dy = Math.abs(y(pos) - localY);
        if (dy < bestDy) { bestDy = dy; nearest = s.abbr; }
      }
      if (nearest !== hoverAbbr) { hoverAbbr = nearest; applyEmphasis(); }

      const kind = derived.statusPerLap.get(lap);
      const rows = [];
      if (lap === 0) {
        for (const d of drivers) {
          const s = series.find((sr) => sr.abbr === d.abbr);
          if (!s) continue;
          rows.push({
            color: d.color, dash: d.dash,
            label: `P${s.posAt.get(0)} ${d.abbr}`,
            value: d.grid != null && d.grid >= 1 ? "GRID" : "PIT",
            dim: hasFocus && !focus.has(d.abbr),
          });
        }
        rows.sort((a, b) => parseInt(a.label.slice(1)) - parseInt(b.label.slice(1)));
      } else {
        const tower = derived.towerPerLap.get(lap) ?? [];
        for (const t of tower) {
          const d = derived.driverMap.get(t.abbr);
          rows.push({
            color: d?.color, dash: d?.dash,
            label: `P${t.pos} ${t.abbr}`,
            value: t.pos === 1 ? "Leader" : fmtGap(t.gap, 1),
            extra: `${compoundLetter(t.cmp)}${t.life ?? ""}${t.pit ? " ●PIT" : ""}`,
            valueColor: t.abbr === hoverAbbr ? "#ffffff" : undefined,
            dim: hoverAbbr ? t.abbr !== hoverAbbr && false : false,
          });
        }
      }
      tooltip.showRows(clientX, clientY, {
        title: lap === 0 ? "スタートグリッド" : `Lap ${lap}/${derived.totalLaps}${kind ? `　[${kind === "RED" ? "赤旗" : kind}]` : ""}`,
        rows,
      });
    },
    onLeave() {
      hoverAbbr = null;
      applyEmphasis();
    },
  });

  function nearestPos(s, lap) {
    // その周のデータが無い場合は直前の周の順位を使う（リタイア後は null）
    if (lap > s.last.lap) return null;
    for (let l = lap; l >= 0; l--) {
      const pos = s.posAt.get(l);
      if (pos != null) return pos;
    }
    return null;
  }

  // クリックで選択トグル
  svg.addEventListener("click", (evt) => {
    const rect = svg.getBoundingClientRect();
    const sx = svg.viewBox.baseVal.width / rect.width;
    const lx = (evt.clientX - rect.left) * sx;
    const lyv = (evt.clientY - rect.top) * (svg.viewBox.baseVal.height / rect.height);
    if (lx < plot.x0 || lx > plot.x1 || lyv < plot.y0 || lyv > plot.y1) return;
    const lap = Math.max(0, Math.min(maxLap, Math.round(x.invert(lx))));
    let nearest = null, bestDy = 14;
    for (const s of series) {
      const pos = s.posAt.get(lap) ?? nearestPos(s, lap);
      if (pos == null) continue;
      const dy = Math.abs(y(pos) - lyv);
      if (dy < bestDy) { bestDy = dy; nearest = s.abbr; }
    }
    if (nearest) toggleFocus(nearest);
  });
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
