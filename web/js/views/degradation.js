// タイヤデグラデーション: タイヤ使用周回数 × ラップタイムの散布図と
// コンパウンド別の線形フィット（劣化率 s/周）。レースでは燃料補正を選択可。

import { state, visibleDrivers } from "../state.js";
import { el, clearNode, linScale, niceTicks, gridY, tooltip } from "../svg.js";
import { fmtLapTime, compoundLetter } from "../format.js";
import { statusKind } from "../derive.js";

const M = { top: 28, bottom: 34, left: 84, right: 30 };
const PLOT_H = 430;

// 燃料搭載量によるラップタイム影響の近似値（1周ぶんの燃料 ≒ 0.06s）。
// 実測不能な近似であることを画面上にも明記する。
const FUEL_SECONDS_PER_LAP = 0.06;

let fuelCorrect = true;
let excludeSC = true;
let showDeleted = false;
let clampOutliers = true;
let tableMode = false;

export function renderDegradation(container) {
  clearNode(container);
  const { bundle, derived } = state;
  const isRace = derived.isRace;

  const panel = document.createElement("div");
  panel.className = "panel";
  container.appendChild(panel);

  const head = document.createElement("div");
  head.className = "panel-head";
  const title = document.createElement("div");
  title.className = "panel-title";
  title.textContent = "タイヤデグラデーション";
  const sub = document.createElement("div");
  sub.className = "panel-sub";
  sub.textContent = isRace && fuelCorrect
    ? `タイヤ使用周回数とラップタイムの関係。燃料補正あり（${FUEL_SECONDS_PER_LAP.toFixed(2)}s/周の近似で終盤重量に正規化）。線＝コンパウンド別フィット。`
    : "タイヤ使用周回数とラップタイムの関係。線＝コンパウンド別の線形フィット（傾き＝劣化率）。";
  head.appendChild(title);
  head.appendChild(sub);

  const controls = document.createElement("div");
  controls.className = "panel-controls";
  if (isRace) controls.appendChild(toggle("燃料補正", fuelCorrect, () => { fuelCorrect = !fuelCorrect; renderDegradation(container); }));
  controls.appendChild(toggle("SC周除外", excludeSC, () => { excludeSC = !excludeSC; renderDegradation(container); }));
  controls.appendChild(toggle("削除ラップ", showDeleted, () => { showDeleted = !showDeleted; renderDegradation(container); }));
  controls.appendChild(toggle("外れ値カット", clampOutliers, () => { clampOutliers = !clampOutliers; renderDegradation(container); }));
  controls.appendChild(toggle("表で見る", tableMode, () => { tableMode = !tableMode; renderDegradation(container); }));
  head.appendChild(controls);
  panel.appendChild(head);

  // 対象ラップの収集（クリーンラップのみ）
  const shown = visibleDrivers();
  const totalLaps = derived.totalLaps || derived.maxLap;
  const correct = (rec) => {
    if (!isRace || !fuelCorrect) return rec.t;
    return rec.t - FUEL_SECONDS_PER_LAP * (totalLaps - rec.lap);
  };
  let points = [];   // {abbr, color, lap, life, cmp, t, y}
  for (const d of shown) {
    for (const rec of derived.lapsByDriver.get(d.abbr) ?? []) {
      if (rec.t == null || rec.life == null || rec.cmp == null) continue;
      if (rec.pit_in || rec.pit_out) continue;
      if (rec.del && !showDeleted) continue;
      if (excludeSC) {
        const kind = statusKind(rec.ts);
        if (kind === "SC" || kind === "VSC" || kind === "RED") continue;
      }
      points.push({ abbr: d.abbr, color: d.color, lap: rec.lap, life: rec.life, cmp: rec.cmp, stint: rec.stint, t: rec.t, y: correct(rec) });
    }
  }

  // 外れ値カット: 表示だけでなくフィット・表も同じ集合で計算するため、ここで一度だけ除外する
  if (clampOutliers && points.length > 12) {
    const sorted = points.map((p) => p.y).sort((a, b) => a - b);
    const q92 = sorted[Math.min(sorted.length - 1, Math.floor(0.92 * sorted.length))];
    const cutoff = q92 + (q92 - sorted[0]) * 0.3 + 0.5;
    points = points.filter((p) => p.y <= cutoff);
  }

  if (points.length < 4) {
    panel.appendChild(emptyNote("表示できるラップがありません（フィルタを緩めるかドライバー選択を解除してください）。"));
    return;
  }

  // コンパウンド別グルーピングとフィット
  const byCmp = new Map();
  for (const p of points) {
    if (!byCmp.has(p.cmp)) byCmp.set(p.cmp, []);
    byCmp.get(p.cmp).push(p);
  }
  const fits = [];
  for (const [cmp, pts] of byCmp) {
    if (pts.length < 5) continue;
    const fit = linearFit(pts.map((p) => p.life), pts.map((p) => p.y));
    if (fit) fits.push({ cmp, ...fit, n: pts.length, minLife: Math.min(...pts.map((p) => p.life)), maxLife: Math.max(...pts.map((p) => p.life)) });
  }

  if (tableMode) {
    panel.appendChild(buildTable(fits, byCmp, bundle));
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

  const maxLife = Math.max(...points.map((p) => p.life));
  const x = linScale(0, maxLife + 1, plot.x0, plot.x1);

  // 外れ値は収集直後に除外済みなので、ドメインは残った点の実レンジでよい
  const allY = points.map((p) => p.y).sort((a, b) => a - b);
  const vMin = allY[0];
  const vMax = allY[allY.length - 1];
  const padV = (vMax - vMin) * 0.06 + 0.05;
  const y = linScale(vMin - padV, vMax + padV, plot.y1, plot.y0);

  const defs = el("defs", {}, svg);
  const clip = el("clipPath", { id: "deg-clip" }, defs);
  el("rect", { x: plot.x0 - 2, y: plot.y0 - 4, width: plot.x1 - plot.x0 + 8, height: plot.y1 - plot.y0 + 8 }, clip);

  const gridG = el("g", {}, svg);
  gridY(gridG, y, niceTicks(y.domain[0], y.domain[1], 7), plot.x0, plot.x1,
    (v) => fmtLapTime(v).replace(/(\.\d)\d+$/, "$1"));
  for (const t of niceTicks(0, maxLife + 1, 8)) {
    if (t < 0) continue;
    el("text", { class: "axis-label", x: x(t), y: plot.y1 + 17, "text-anchor": "middle", text: Math.round(t) }, gridG);
  }
  el("text", { class: "axis-label", x: plot.x1 + 4, y: plot.y1 + 17, text: "周目" }, gridG);
  el("text", { class: "axis-label", x: plot.x0, y: plot.y0 - 8, text: "タイヤ使用周回数（横軸）×ラップタイム（縦軸）" }, gridG);

  // ドット
  const dotsG = el("g", { "clip-path": "url(#deg-clip)" }, svg);
  for (const p of points) {
    const color = bundle.compound_colors[p.cmp] ?? "#8a8f9c";
    // 同一 life に複数ドットが重なるため決定的ジッター
    const jitter = ((((p.lap * 2654435761) >>> 0) % 1000) / 1000 - 0.5) * 5;
    const dot = el("circle", {
      cx: x(p.life) + jitter, cy: y(p.y), r: 3,
      fill: color, "fill-opacity": 0.75, stroke: "var(--surface-1)", "stroke-width": 1,
    }, dotsG);
    dot.addEventListener("pointermove", (evt) => {
      tooltip.showRows(evt.clientX, evt.clientY, {
        title: `${p.abbr} — Lap ${p.lap}`,
        rows: [
          { color: p.color, label: "実タイム", value: fmtLapTime(p.t) },
          ...(isRace && fuelCorrect ? [{ label: "補正後", value: fmtLapTime(p.y) }] : []),
          { label: "タイヤ", value: `${p.cmp} ${p.life}周目` },
        ],
      });
    });
    dot.addEventListener("pointerleave", () => tooltip.hide());
  }

  // フィット線 + 凡例
  const linesG = el("g", { fill: "none", "clip-path": "url(#deg-clip)" }, svg);
  const legend = document.createElement("div");
  legend.className = "panel-sub";
  legend.style.marginTop = "6px";
  for (const f of fits) {
    const color = bundle.compound_colors[f.cmp] ?? "#8a8f9c";
    const x0v = f.minLife, x1v = f.maxLife;
    el("line", {
      x1: x(x0v), y1: y(f.slope * x0v + f.intercept),
      x2: x(x1v), y2: y(f.slope * x1v + f.intercept),
      stroke: color, "stroke-width": 2.6, "stroke-dasharray": "8 5", opacity: 0.95,
    }, linesG);
    const chip = document.createElement("span");
    chip.className = "tyre-chip";
    chip.style.background = color;
    chip.textContent = compoundLetter(f.cmp);
    chip.style.marginRight = "4px";
    legend.appendChild(chip);
    const label = document.createElement("span");
    const slopeText = `${f.slope >= 0 ? "+" : ""}${f.slope.toFixed(3)}s/周`;
    label.textContent = `${f.cmp.toLowerCase()} ${slopeText}（${f.n}ラップ）　`;
    legend.appendChild(label);
  }
  panel.appendChild(legend);
}

// 最小二乗フィット
function linearFit(xs, ys) {
  const n = xs.length;
  if (n < 2) return null;
  const mx = xs.reduce((a, b) => a + b, 0) / n;
  const my = ys.reduce((a, b) => a + b, 0) / n;
  let sxx = 0, sxy = 0;
  for (let i = 0; i < n; i++) {
    sxx += (xs[i] - mx) ** 2;
    sxy += (xs[i] - mx) * (ys[i] - my);
  }
  if (sxx === 0) return null;
  const slope = sxy / sxx;
  return { slope, intercept: my - slope * mx };
}

function buildTable(fits, byCmp, bundle) {
  const wrap = document.createElement("div");
  wrap.className = "data-table-wrap";
  const table = document.createElement("table");
  table.className = "data-table";
  const thead = document.createElement("thead");
  thead.innerHTML = `<tr><th>コンパウンド</th><th class="num">ラップ数</th><th class="num">ベスト</th><th class="num">中央値</th><th class="num">劣化率</th></tr>`;
  table.appendChild(thead);
  const tbody = document.createElement("tbody");
  for (const [cmp, pts] of byCmp) {
    const times = pts.map((p) => p.y).sort((a, b) => a - b);
    const fit = fits.find((f) => f.cmp === cmp);
    const tr = document.createElement("tr");
    const tdC = document.createElement("td");
    const chip = document.createElement("span");
    chip.className = "tyre-chip";
    chip.style.background = bundle.compound_colors[cmp] ?? "#8a8f9c";
    chip.textContent = compoundLetter(cmp);
    chip.style.marginRight = "6px";
    tdC.appendChild(chip);
    tdC.appendChild(document.createTextNode(cmp.toLowerCase()));
    tr.appendChild(tdC);
    const cells = [
      String(times.length),
      fmtLapTime(times[0]),
      fmtLapTime(times[Math.floor(times.length / 2)]),
      fit ? `${fit.slope >= 0 ? "+" : ""}${fit.slope.toFixed(3)}s/周` : "—",
    ];
    for (const c of cells) {
      const td = document.createElement("td");
      td.className = "num";
      td.textContent = c;
      tr.appendChild(td);
    }
    tbody.appendChild(tr);
  }
  table.appendChild(tbody);
  wrap.appendChild(table);
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
