// ラップ分布: ドライバーごとのラップタイム分布バイオリンプロット
// （Tkinter版 compare_tab のバイオリンプロットを Web に移植・拡張したもの。
//   カーネル密度推定は自前実装。ドットはタイヤコンパウンド色の実ラップ。）

import { state, visibleDrivers, toggleFocus } from "../state.js";
import { el, clearNode, linScale, niceTicks, gridY, dashArray, tooltip } from "../svg.js";
import { fmtLapTime, compoundLetter } from "../format.js";
import { statusKind } from "../derive.js";

const M = { top: 24, bottom: 34, left: 84, right: 20 };
const PLOT_H = 450;

let excludePit = true;
let excludeSC = true;
let showDeleted = false;
let clampOutliers = true;
let tableMode = false;

export function renderViolin(container) {
  clearNode(container);
  const { bundle, derived } = state;

  const panel = document.createElement("div");
  panel.className = "panel";
  container.appendChild(panel);

  const head = document.createElement("div");
  head.className = "panel-head";
  const title = document.createElement("div");
  title.className = "panel-title";
  title.textContent = "ラップ分布（バイオリンプロット）";
  const sub = document.createElement("div");
  sub.className = "panel-sub";
  sub.textContent = "ラップタイムの分布形状。幅＝そのタイムの頻度、横線＝中央値、ドット＝実ラップ（色はタイヤ）。";
  head.appendChild(title);
  head.appendChild(sub);

  const controls = document.createElement("div");
  controls.className = "panel-controls";
  controls.appendChild(toggle("ピット周除外", excludePit, () => { excludePit = !excludePit; renderViolin(container); }));
  controls.appendChild(toggle("SC周除外", excludeSC, () => { excludeSC = !excludeSC; renderViolin(container); }));
  controls.appendChild(toggle("削除ラップ", showDeleted, () => { showDeleted = !showDeleted; renderViolin(container); }));
  controls.appendChild(toggle("外れ値カット", clampOutliers, () => { clampOutliers = !clampOutliers; renderViolin(container); }));
  controls.appendChild(toggle("表で見る", tableMode, () => { tableMode = !tableMode; renderViolin(container); }));
  head.appendChild(controls);
  panel.appendChild(head);

  // 対象ドライバー（選択があれば選択のみ、無ければ全員）とフィルタ済みラップ
  const shown = visibleDrivers();
  const series = [];
  const allT = [];
  for (const d of shown) {
    const recs = (derived.lapsByDriver.get(d.abbr) ?? []).filter((rec) => {
      if (rec.t == null) return false;
      if (rec.del && !showDeleted) return false;
      if (excludePit && (rec.pit_in || rec.pit_out)) return false;
      if (excludeSC) {
        const kind = statusKind(rec.ts);
        if (kind === "SC" || kind === "VSC" || kind === "RED") return false;
      }
      return true;
    });
    if (recs.length === 0) continue;
    const times = recs.map((r) => r.t).sort((a, b) => a - b);
    series.push({
      abbr: d.abbr, color: d.color, dash: d.dash, recs, times,
      stats: computeStats(times),
    });
    allT.push(...times);
  }

  if (series.length === 0) {
    panel.appendChild(emptyNote("表示できるラップがありません（フィルタを緩めてください）。"));
    return;
  }

  if (tableMode) {
    panel.appendChild(buildStatsTable(series));
    return;
  }

  const host = document.createElement("div");
  host.className = "chart-host";
  panel.appendChild(host);

  const width = Math.max(680, host.clientWidth || container.clientWidth || 900);
  const height = M.top + M.bottom + PLOT_H;
  const svg = el("svg", { viewBox: `0 0 ${width} ${height}`, width, height });
  host.appendChild(svg);
  const plot = { x0: M.left, x1: width - M.right, y0: M.top, y1: height - M.bottom };

  // Y ドメイン（ペースタブと同じ流儀: 速い=下）
  allT.sort((a, b) => a - b);
  const q = (p) => allT[Math.min(allT.length - 1, Math.floor(p * allT.length))];
  const vMin = allT[0];
  let vMax = allT[allT.length - 1];
  if (clampOutliers && allT.length > 12) vMax = Math.min(vMax, q(0.9) + (q(0.9) - vMin) * 0.35 + 0.8);
  const pad = (vMax - vMin) * 0.06 + 0.05;
  const y = linScale(vMin - pad, vMax + pad, plot.y1, plot.y0);

  const gridG = el("g", {}, svg);
  gridY(gridG, y, niceTicks(vMin - pad, vMax + pad, 7), plot.x0, plot.x1, (v) => fmtLapTime(v).replace(/(\.\d)\d+$/, "$1"));

  const n = series.length;
  const slotW = (plot.x1 - plot.x0) / n;
  const halfW = Math.min(36, slotW * 0.42);

  const focusSize = state.focus.size;
  series.forEach((s, i) => {
    const cx = plot.x0 + slotW * (i + 0.5);
    const group = el("g", {}, svg);

    // KDE → バイオリン形状（各バイオリンは自身の最大密度で正規化 = seaborn scale="width"）
    const inDomain = s.times.filter((t) => t >= y.domain[0] && t <= y.domain[1]);
    if (inDomain.length >= 4) {
      const kde = computeKDE(inDomain, y.domain[0], y.domain[1], 64);
      const maxD = Math.max(...kde.density);
      if (maxD > 0) {
        // 裾の刈り込み（最大密度の1.5%未満は描かない）
        let lo = 0, hi = kde.grid.length - 1;
        while (lo < hi && kde.density[lo] < maxD * 0.015) lo++;
        while (hi > lo && kde.density[hi] < maxD * 0.015) hi--;
        const right = [], left = [];
        for (let k = lo; k <= hi; k++) {
          const w = (kde.density[k] / maxD) * halfW;
          const py = y(kde.grid[k]);
          right.push(`${(cx + w).toFixed(1)},${py.toFixed(1)}`);
          left.push(`${(cx - w).toFixed(1)},${py.toFixed(1)}`);
        }
        const path = `M${right.join("L")}L${left.reverse().join("L")}Z`;
        el("path", {
          d: path, fill: s.color, "fill-opacity": 0.2,
          stroke: s.color, "stroke-width": 1.6,
          "stroke-dasharray": dashArray(s.dash), "stroke-linejoin": "round",
        }, group);
      }
    }

    // 中央値ライン
    if (s.stats.median >= y.domain[0] && s.stats.median <= y.domain[1]) {
      el("line", {
        x1: cx - halfW * 0.75, x2: cx + halfW * 0.75,
        y1: y(s.stats.median), y2: y(s.stats.median),
        stroke: "var(--ink)", "stroke-width": 2, "stroke-linecap": "round",
      }, group);
    }

    // 実ラップのドット（決定的ジッター・タイヤ色）
    for (const rec of s.recs) {
      if (rec.t < y.domain[0] || rec.t > y.domain[1]) continue;
      const jitter = ((((rec.lap * 2654435761) >>> 0) % 1000) / 1000 - 0.5) * halfW * 1.1;
      const color = bundle.compound_colors[rec.cmp] ?? "#8a8f9c";
      if (rec.del) {
        el("rect", {
          x: cx + jitter - 2.4, y: y(rec.t) - 2.4, width: 4.8, height: 4.8,
          transform: `rotate(45 ${cx + jitter} ${y(rec.t)})`,
          fill: "none", stroke: color, "stroke-width": 1.3,
        }, group);
      } else {
        el("circle", {
          cx: cx + jitter, cy: y(rec.t), r: 2.3,
          fill: color, stroke: "var(--surface-1)", "stroke-width": 1.2,
        }, group);
      }
    }

    // X ラベル（略称 + 色キー）
    const label = el("text", {
      class: "drv-label", x: cx, y: plot.y1 + 18, "text-anchor": "middle", text: s.abbr,
    }, svg);
    el("line", {
      x1: cx - 8, x2: cx + 8, y1: plot.y1 + 25, y2: plot.y1 + 25,
      stroke: s.color, "stroke-width": 3, "stroke-dasharray": dashArray(s.dash), "stroke-linecap": "round",
    }, svg);
    label.addEventListener("click", () => toggleFocus(s.abbr));

    const dim = focusSize > 0 && !state.focus.has(s.abbr);
    if (dim) group.setAttribute("opacity", "0.25");

    // ホバー: バイオリン単位の統計ツールチップ
    const hit = el("rect", {
      x: cx - slotW / 2, y: plot.y0, width: slotW, height: plot.y1 - plot.y0,
      fill: "transparent",
    }, svg);
    hit.style.cursor = "pointer";
    hit.addEventListener("pointermove", (evt) => {
      group.setAttribute("opacity", "1");
      tooltip.showRows(evt.clientX, evt.clientY, {
        title: `${s.abbr} — ${s.times.length}ラップ`,
        rows: [
          { color: s.color, dash: s.dash, label: "ベスト", value: fmtLapTime(s.stats.min) },
          { label: "中央値", value: fmtLapTime(s.stats.median) },
          { label: "平均", value: fmtLapTime(s.stats.mean) },
          { label: "P25–P75", value: `${fmtLapTime(s.stats.p25)} – ${fmtLapTime(s.stats.p75)}` },
          { label: "ばらつき(σ)", value: `${s.stats.std.toFixed(3)}s` },
        ],
      });
    });
    hit.addEventListener("pointerleave", () => {
      if (dim) group.setAttribute("opacity", "0.25");
      tooltip.hide();
    });
    hit.addEventListener("click", () => toggleFocus(s.abbr));
  });
}

// ガウスカーネル密度推定（バンド幅は Silverman 則、下限 0.05s）
function computeKDE(sortedTimes, lo, hi, gridN) {
  const n = sortedTimes.length;
  const mean = sortedTimes.reduce((a, b) => a + b, 0) / n;
  const std = Math.sqrt(sortedTimes.reduce((a, b) => a + (b - mean) ** 2, 0) / n) || 0.05;
  const iqr = quantileSorted(sortedTimes, 0.75) - quantileSorted(sortedTimes, 0.25);
  const sigma = Math.min(std, iqr > 0 ? iqr / 1.34 : std) || std;
  const bw = Math.max(0.05, 0.9 * sigma * Math.pow(n, -0.2));
  const grid = [];
  const density = [];
  for (let k = 0; k < gridN; k++) {
    const gy = lo + ((hi - lo) * k) / (gridN - 1);
    let sum = 0;
    for (const t of sortedTimes) {
      const z = (gy - t) / bw;
      if (Math.abs(z) < 4) sum += Math.exp(-0.5 * z * z);
    }
    grid.push(gy);
    density.push(sum / (n * bw));
  }
  return { grid, density };
}

function quantileSorted(sorted, p) {
  const idx = (sorted.length - 1) * p;
  const lo = Math.floor(idx), hi = Math.ceil(idx);
  return sorted[lo] + (sorted[hi] - sorted[lo]) * (idx - lo);
}

function computeStats(sortedTimes) {
  const n = sortedTimes.length;
  const mean = sortedTimes.reduce((a, b) => a + b, 0) / n;
  const std = Math.sqrt(sortedTimes.reduce((a, b) => a + (b - mean) ** 2, 0) / n);
  return {
    n,
    min: sortedTimes[0],
    median: quantileSorted(sortedTimes, 0.5),
    mean,
    p25: quantileSorted(sortedTimes, 0.25),
    p75: quantileSorted(sortedTimes, 0.75),
    std,
  };
}

function buildStatsTable(series) {
  const wrap = document.createElement("div");
  wrap.className = "data-table-wrap";
  const table = document.createElement("table");
  table.className = "data-table";
  const thead = document.createElement("thead");
  const headRow = document.createElement("tr");
  for (const h of ["ドライバー", "ラップ数", "ベスト", "中央値", "平均", "P25", "P75", "σ"]) {
    const th = document.createElement("th");
    th.textContent = h;
    if (h !== "ドライバー") th.className = "num";
    headRow.appendChild(th);
  }
  thead.appendChild(headRow);
  table.appendChild(thead);
  const tbody = document.createElement("tbody");
  const best = Math.min(...series.map((s) => s.stats.median));
  for (const s of series) {
    const tr = document.createElement("tr");
    tr.style.cursor = "pointer";
    tr.addEventListener("click", () => toggleFocus(s.abbr));
    const tdD = document.createElement("td");
    const key = document.createElement("span");
    key.className = "team-key";
    key.style.background = s.color;
    tdD.appendChild(key);
    tdD.appendChild(document.createTextNode(s.abbr));
    tr.appendChild(tdD);
    const cells = [
      String(s.stats.n), fmtLapTime(s.stats.min), fmtLapTime(s.stats.median),
      fmtLapTime(s.stats.mean), fmtLapTime(s.stats.p25), fmtLapTime(s.stats.p75),
      `${s.stats.std.toFixed(3)}s`,
    ];
    cells.forEach((v, i) => {
      const td = document.createElement("td");
      td.className = "num";
      if (i === 2 && Math.abs(s.stats.median - best) < 0.0005) td.classList.add("best-purple");
      td.textContent = v;
      tr.appendChild(td);
    });
    if (state.focus.size > 0 && !state.focus.has(s.abbr)) tr.style.opacity = "0.45";
    tbody.appendChild(tr);
  }
  table.appendChild(tbody);
  wrap.appendChild(table);
  const note = document.createElement("div");
  note.className = "panel-sub";
  note.textContent = "中央値が最速のドライバーを紫で表示。行クリックで選択。";
  wrap.appendChild(note);
  return wrap;
}

function toggle(label, on, onClick) {
  const btn = document.createElement("button");
  btn.className = `toggle-btn${on ? " on" : ""}`;
  btn.textContent = label;
  btn.addEventListener("click", onClick);
  return btn;
}

function emptyNote(text) {
  const div = document.createElement("div");
  div.className = "empty-note";
  div.textContent = text;
  return div;
}
