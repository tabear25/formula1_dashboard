// 予選分析（予選専用）:
//   1) Q1→Q2→Q3 のセグメントベストをつなぐスロープチャート（ノックアウト可視化）
//   2) トラック進化: セッション時間に対する全ラップと「その時点のベスト」の推移

import { state, toggleFocus } from "../state.js";
import { el, clearNode, linScale, niceTicks, gridY, dashArray, tooltip } from "../svg.js";
import { fmtLapTime, fmtGap, compoundLetter } from "../format.js";

const M = { top: 34, bottom: 30, left: 84, right: 96 };
const PLOT_H = 470;

let clampOutliers = true;

export function renderQuali(container) {
  clearNode(container);
  const { bundle } = state;

  drawSlope(container);
  drawEvolution(container);

  // 予選でQ1/Q2/Q3が全て無い（古いデータ等）場合のガードは drawSlope 内で行う
  void bundle;
}

// ------------------------------------------------------------ スロープチャート

function drawSlope(container) {
  const { bundle } = state;
  const panel = document.createElement("div");
  panel.className = "panel";
  container.appendChild(panel);

  const head = document.createElement("div");
  head.className = "panel-head";
  head.innerHTML = `<div class="panel-title">セグメント推移（Q1 → Q2 → Q3）</div>
    <div class="panel-sub">各セグメントのベストタイム。紫＝セグメント最速。ラベルクリックで選択。</div>`;
  const controls = document.createElement("div");
  controls.className = "panel-controls";
  const btn = document.createElement("button");
  btn.className = `toggle-btn${clampOutliers ? " on" : ""}`;
  btn.textContent = "外れ値カット";
  btn.addEventListener("click", () => { clampOutliers = !clampOutliers; rerender(container); });
  controls.appendChild(btn);
  head.appendChild(controls);
  panel.appendChild(head);

  const drivers = bundle.drivers.filter((d) => d.q1 != null || d.q2 != null || d.q3 != null);
  if (drivers.length === 0) {
    panel.insertAdjacentHTML("beforeend", `<div class="empty-note">セグメントタイム（Q1/Q2/Q3）がありません。</div>`);
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

  const segs = ["q1", "q2", "q3"];
  const segX = segs.map((_, i) => plot.x0 + ((plot.x1 - plot.x0) * i) / (segs.length - 1));

  const allT = [];
  for (const d of drivers) for (const s of segs) if (d[s] != null) allT.push(d[s]);
  allT.sort((a, b) => a - b);
  const vMin = allT[0];
  let vMax = allT[allT.length - 1];
  if (clampOutliers && allT.length > 10) {
    vMax = Math.min(vMax, vMin + Math.max(2.5, (allT[Math.floor(allT.length * 0.9)] - vMin) * 1.15));
  }
  const pad = (vMax - vMin) * 0.05 + 0.05;
  const y = linScale(vMin - pad, vMax + pad, plot.y0, plot.y1);   // 速い＝上

  const defs = el("defs", {}, svg);
  const clip = el("clipPath", { id: "quali-clip" }, defs);
  el("rect", { x: plot.x0 - 6, y: plot.y0 - 6, width: plot.x1 - plot.x0 + 12, height: plot.y1 - plot.y0 + 12 }, clip);

  // セグメント列ヘッダとベスト
  const best = {};
  for (const s of segs) {
    const vals = drivers.map((d) => d[s]).filter((v) => v != null);
    best[s] = vals.length ? Math.min(...vals) : null;
  }
  segs.forEach((s, i) => {
    el("line", { class: "gridline", x1: segX[i], x2: segX[i], y1: plot.y0, y2: plot.y1 }, svg);
    el("text", {
      class: "axis-label", x: segX[i], y: plot.y0 - 16, "text-anchor": "middle",
      "font-weight": 700, "font-size": 13, text: s.toUpperCase(),
    }, svg);
    if (best[s] != null) {
      el("text", {
        class: "axis-label", x: segX[i], y: plot.y0 - 4, "text-anchor": "middle",
        text: fmtLapTime(best[s]),
      }, svg);
    }
  });
  const gridG = el("g", {}, svg);
  gridY(gridG, y, niceTicks(y.domain[0], y.domain[1], 7), plot.x0, plot.x1,
    (v) => fmtLapTime(v).replace(/(\.\d)\d+$/, "$1"));

  const focus = state.focus;
  const hasFocus = focus.size > 0;

  const linesG = el("g", { fill: "none", "clip-path": "url(#quali-clip)" }, svg);
  const labelYs = [];
  for (const d of drivers) {
    const dim = hasFocus && !focus.has(d.abbr);
    const pts = [];
    segs.forEach((s, i) => { if (d[s] != null) pts.push({ i, v: d[s], seg: s }); });
    if (pts.length === 0) continue;
    const g = el("g", { opacity: dim ? 0.18 : 0.95 }, linesG);
    if (pts.length > 1) {
      const points = pts.map((p) => `${segX[p.i]},${y(p.v)}`).join(" ");
      el("polyline", {
        points, stroke: d.color, "stroke-width": 2,
        "stroke-dasharray": dashArray(d.dash), "stroke-linejoin": "round",
      }, g);
    }
    for (const p of pts) {
      const isBest = best[p.seg] != null && Math.abs(p.v - best[p.seg]) < 0.0005;
      const dot = el("circle", {
        cx: segX[p.i], cy: y(p.v), r: isBest ? 5 : 3.6,
        fill: isBest ? "var(--purple)" : d.color,
        stroke: "var(--surface-1)", "stroke-width": 1.6,
      }, g);
      dot.addEventListener("pointermove", (evt) => {
        const gapToBest = best[p.seg] != null ? p.v - best[p.seg] : null;
        tooltip.showRows(evt.clientX, evt.clientY, {
          title: `${d.abbr} — ${p.seg.toUpperCase()}`,
          rows: [
            { color: d.color, dash: d.dash, label: "タイム", value: fmtLapTime(p.v) },
            { label: "セグメント最速差", value: gapToBest != null && gapToBest > 0 ? fmtGap(gapToBest) : "最速" },
          ],
        });
      });
      dot.addEventListener("pointerleave", () => tooltip.hide());
      dot.style.cursor = "pointer";
      dot.addEventListener("click", () => toggleFocus(d.abbr));
    }
    // ラベルのアンカーは「表示域内にある最後のセグメント点」。全点が域外
    // （外れ値カットで隠れた）ドライバーはラベルも出さない。
    const visPts = pts.filter((p) => y(p.v) >= plot.y0 && y(p.v) <= plot.y1);
    if (visPts.length === 0) continue;
    const anchor = visPts[visPts.length - 1];
    labelYs.push({ d, x: segX[anchor.i], y: y(anchor.v), dim });
  }

  // ラベルの重なり解決。列（Q1脱落/Q2脱落/Q3）が違えば横に重ならないので、
  // 同じ列のラベル同士だけで押し下げを行う。
  const labelCols = new Map();
  for (const L of labelYs) {
    if (!labelCols.has(L.x)) labelCols.set(L.x, []);
    labelCols.get(L.x).push(L);
  }
  for (const colLabels of labelCols.values()) {
    colLabels.sort((a, b) => a.y - b.y);
    let prevY = -100;
    for (const L of colLabels) {
      const ly = Math.max(L.y, prevY + 11.5);
      prevY = ly;
      if (ly > plot.y1 + 10) continue;   // 押し下げの結果プロット外へ出たものは描かない
      const label = el("text", {
        class: `drv-label${L.dim ? " dim" : ""}`, x: L.x + 10, y: ly + 3.5, text: L.d.abbr,
      }, svg);
      el("line", {
        x1: L.x + 10 + L.d.abbr.length * 7 + 4, x2: L.x + 10 + L.d.abbr.length * 7 + 16,
        y1: ly, y2: ly, stroke: L.d.color, "stroke-width": 3,
        "stroke-dasharray": dashArray(L.d.dash), "stroke-linecap": "round",
        opacity: L.dim ? 0.25 : 1,
      }, svg);
      label.addEventListener("click", () => toggleFocus(L.d.abbr));
    }
  }
}

function rerender(container) {
  clearNode(container);
  renderQuali(container);
}

// ------------------------------------------------------------ トラック進化

function drawEvolution(container) {
  const { bundle, derived } = state;
  const panel = document.createElement("div");
  panel.className = "panel";
  container.appendChild(panel);
  const head = document.createElement("div");
  head.className = "panel-head";
  head.innerHTML = `<div class="panel-title">トラック進化</div>
    <div class="panel-sub">セッション時間に対する各ラップ（ドット色＝タイヤ）と、その時点までのベスト（白線）。路面改善やアタックの波が見える。</div>`;
  panel.appendChild(head);

  // クリーンラップのみ（削除ラップ除外、明らかなクールダウンは外れ値カットで隠れる）
  const recs = [];
  for (const rec of bundle.laps) {
    if (rec.t == null || rec.del || rec.st == null) continue;
    if (rec.pit_out || rec.pit_in) continue;
    recs.push(rec);
  }
  if (recs.length < 5) {
    panel.insertAdjacentHTML("beforeend", `<div class="empty-note">表示できるラップがありません。</div>`);
    return;
  }
  recs.sort((a, b) => a.st - b.st);

  const host = document.createElement("div");
  host.className = "chart-host";
  panel.appendChild(host);

  const EM = { top: 26, bottom: 30, left: 84, right: 26 };
  const width = Math.max(680, host.clientWidth || container.clientWidth || 900);
  const height = EM.top + EM.bottom + 380;
  const svg = el("svg", { viewBox: `0 0 ${width} ${height}`, width, height });
  host.appendChild(svg);
  const plot = { x0: EM.left, x1: width - EM.right, y0: EM.top, y1: height - EM.bottom };

  const t0 = recs[0].st;
  const minutes = (s) => (s - t0) / 60;
  const tMax = minutes(recs[recs.length - 1].st) || 1;
  const x = linScale(0, tMax * 1.02, plot.x0, plot.x1);

  const allT = recs.map((r) => r.t).sort((a, b) => a - b);
  const vMin = allT[0];
  let vMax = allT[allT.length - 1];
  if (clampOutliers && allT.length > 10) {
    vMax = Math.min(vMax, vMin + Math.max(3.5, (allT[Math.floor(allT.length * 0.75)] - vMin) * 1.6));
  }
  const pad = (vMax - vMin) * 0.06 + 0.05;
  const y = linScale(vMin - pad, vMax + pad, plot.y1, plot.y0);

  // セグメント区切り: サーバ付与の seg（split_qualifying_sessions 由来）を優先し、
  // 無ければ5分以上の空白から推定する
  const breaks = [];
  let segLabels = null;
  const hasSeg = recs.some((r) => r.seg != null);
  if (hasSeg) {
    for (let i = 1; i < recs.length; i++) {
      const a = recs[i - 1].seg, b = recs[i].seg;
      if (a != null && b != null && a !== b) {
        breaks.push((minutes(recs[i - 1].st) + minutes(recs[i].st)) / 2);
      }
    }
    const present = [...new Set(recs.map((r) => r.seg).filter((v) => v != null))].sort();
    if (present.length === breaks.length + 1) segLabels = present.map((s) => `Q${s}`);
  } else {
    for (let i = 1; i < recs.length; i++) {
      if (recs[i].st - recs[i - 1].st > 300) breaks.push((minutes(recs[i - 1].st) + minutes(recs[i].st)) / 2);
    }
    if (breaks.length === 2) segLabels = ["Q1", "Q2", "Q3"];
  }
  const bounds = [0, ...breaks, tMax];
  breaks.forEach((b) => {
    el("line", { x1: x(b), x2: x(b), y1: plot.y0, y2: plot.y1, stroke: "var(--baseline)", "stroke-width": 1.4, "stroke-dasharray": "3 4" }, svg);
  });
  if (segLabels) {
    for (let i = 0; i < segLabels.length; i++) {
      el("text", {
        class: "band-label", x: x((bounds[i] + bounds[i + 1]) / 2), y: plot.y0 - 6,
        "text-anchor": "middle", text: segLabels[i],
      }, svg);
    }
  }

  const gridG = el("g", {}, svg);
  gridY(gridG, y, niceTicks(y.domain[0], y.domain[1], 6), plot.x0, plot.x1,
    (v) => fmtLapTime(v).replace(/(\.\d)\d+$/, "$1"));
  for (const t of niceTicks(0, tMax, 8)) {
    el("text", { class: "axis-label", x: x(t), y: plot.y1 + 17, "text-anchor": "middle", text: `${Math.round(t)}分` }, gridG);
  }

  const hasFocus = state.focus.size > 0;

  // ドット
  for (const rec of recs) {
    if (rec.t > y.domain[1]) continue;
    const d = derived.driverMap.get(rec.drv);
    const dim = hasFocus && !state.focus.has(rec.drv);
    const dot = el("circle", {
      cx: x(minutes(rec.st)), cy: y(rec.t), r: 3,
      fill: bundle.compound_colors[rec.cmp] ?? "#8a8f9c",
      "fill-opacity": dim ? 0.15 : 0.8,
      stroke: dim ? "none" : "var(--surface-1)", "stroke-width": 1,
    }, svg);
    dot.style.cursor = "pointer";
    dot.addEventListener("pointermove", (evt) => {
      tooltip.showRows(evt.clientX, evt.clientY, {
        title: `${rec.drv} — Lap ${rec.lap}`,
        rows: [
          { color: d?.color, dash: d?.dash, label: "タイム", value: fmtLapTime(rec.t) },
          { label: "タイヤ", value: `${compoundLetter(rec.cmp)}${rec.life ?? ""}` },
          { label: "時刻", value: `開始+${Math.round(minutes(rec.st))}分` },
        ],
      });
    });
    dot.addEventListener("pointerleave", () => tooltip.hide());
    dot.addEventListener("click", () => toggleFocus(rec.drv));
  }

  // その時点までのベスト（ステップ線）。序盤の遅いラップが表示域外でも
  // 線が上へはみ出さないよう、ドメイン上限でクランプ + クリップする。
  const evoDefs = el("defs", {}, svg);
  const evoClip = el("clipPath", { id: "quali-evo-clip" }, evoDefs);
  el("rect", { x: plot.x0 - 4, y: plot.y0 - 4, width: plot.x1 - plot.x0 + 8, height: plot.y1 - plot.y0 + 8 }, evoClip);
  const clampT = (t) => Math.min(t, y.domain[1]);
  let bestSoFar = Infinity;
  let path = "";
  for (const rec of recs) {
    if (rec.t < bestSoFar) {
      const px = x(minutes(rec.st));
      if (path === "") path = `M${px},${y(clampT(rec.t))}`;
      else path += `L${px},${y(clampT(bestSoFar))}L${px},${y(clampT(rec.t))}`;
      bestSoFar = rec.t;
    }
  }
  path += `L${x(tMax)},${y(clampT(bestSoFar))}`;
  el("path", {
    d: path, stroke: "var(--ink)", "stroke-width": 1.8, fill: "none", opacity: 0.85,
    "clip-path": "url(#quali-evo-clip)",
  }, svg);
}
