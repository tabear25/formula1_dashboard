// ペースチャート: ラップタイム推移（ドット色 = タイヤコンパウンド）+ 表ビュー

import { state, visibleDrivers } from "../state.js";
import { el, clearNode, linScale, niceTicks, attachCrosshair, dashArray, lapTicks, gridY, tooltip } from "../svg.js";
import { fmtLapTime, compoundLetter } from "../format.js";
import { statusKind } from "../derive.js";

const M = { top: 28, bottom: 28, left: 84, right: 30 };
const PLOT_H = 430;

let excludePit = true;
let excludeSC = true;
let showDeleted = false;
let clampOutliers = true;
let tableMode = false;

export function renderPace(container) {
  clearNode(container);
  const { bundle, derived } = state;

  const panel = document.createElement("div");
  panel.className = "panel";
  container.appendChild(panel);

  const head = document.createElement("div");
  head.className = "panel-head";
  const title = document.createElement("div");
  title.className = "panel-title";
  title.textContent = "ペース（ラップタイム）";
  const sub = document.createElement("div");
  sub.className = "panel-sub";
  sub.textContent = state.focus.size > 0
    ? "選択中のドライバーを表示。ドットの色はタイヤ。"
    : "上位6名を表示（上のドライバーチップで自由に選択）。ドットの色はタイヤ。";
  head.appendChild(title);
  head.appendChild(sub);

  const controls = document.createElement("div");
  controls.className = "panel-controls";
  controls.appendChild(toggle("ピット周除外", excludePit, () => { excludePit = !excludePit; renderPace(container); }));
  controls.appendChild(toggle("SC周除外", excludeSC, () => { excludeSC = !excludeSC; renderPace(container); }));
  controls.appendChild(toggle("削除ラップ", showDeleted, () => { showDeleted = !showDeleted; renderPace(container); }));
  controls.appendChild(toggle("外れ値カット", clampOutliers, () => { clampOutliers = !clampOutliers; renderPace(container); }));
  controls.appendChild(toggle("表で見る", tableMode, () => { tableMode = !tableMode; renderPace(container); }));
  head.appendChild(controls);
  panel.appendChild(head);

  // コンパウンド凡例
  const legend = document.createElement("div");
  legend.className = "panel-sub";
  legend.style.marginBottom = "6px";
  const present = new Set();
  for (const rec of bundle.laps) if (rec.cmp) present.add(rec.cmp);
  for (const cmp of present) {
    const chip = document.createElement("span");
    chip.className = "tyre-chip";
    chip.style.background = bundle.compound_colors[cmp] ?? "#8a8f9c";
    chip.textContent = compoundLetter(cmp);
    chip.style.marginRight = "4px";
    legend.appendChild(chip);
    const name = document.createElement("span");
    name.textContent = `${cmp.toLowerCase()}　`;
    legend.appendChild(name);
  }
  panel.appendChild(legend);

  const shown = visibleDrivers(6);
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
    series.push({ abbr: d.abbr, color: d.color, dash: d.dash, recs, recAt: new Map(recs.map((r) => [r.lap, r])) });
    for (const r of recs) if (!r.del) allT.push(r.t);
  }

  if (series.length === 0) {
    panel.appendChild(emptyNote("表示できるラップがありません（フィルタを緩めてください）。"));
    return;
  }

  if (tableMode) {
    panel.appendChild(buildTable(series, derived));
    return;
  }

  const host = document.createElement("div");
  host.className = "chart-host";
  panel.appendChild(host);

  const maxLap = derived.maxLap;
  const width = Math.max(680, host.clientWidth || container.clientWidth || 900);
  const height = M.top + M.bottom + PLOT_H;
  const svg = el("svg", { viewBox: `0 0 ${width} ${height}`, width, height });
  host.appendChild(svg);
  const plot = { x0: M.left, x1: width - M.right, y0: M.top, y1: height - M.bottom };
  const x = linScale(0.6, maxLap + 0.3, plot.x0, plot.x1);

  allT.sort((a, b) => a - b);
  const q = (p) => allT[Math.min(allT.length - 1, Math.floor(p * allT.length))];
  const vMin = allT[0];
  let vMax = allT[allT.length - 1];
  if (clampOutliers && allT.length > 12) vMax = Math.min(vMax, q(0.9) + (q(0.9) - vMin) * 0.35 + 0.8);
  const pad = (vMax - vMin) * 0.06 + 0.05;
  // ラップタイムは大きい = 遅い = 上に伸びる標準の向き
  const y = linScale(vMin - pad, vMax + pad, plot.y1, plot.y0);

  const defs = el("defs", {}, svg);
  const clip = el("clipPath", { id: "pace-clip" }, defs);
  el("rect", { x: plot.x0 - 2, y: plot.y0 - 6, width: plot.x1 - plot.x0 + 8, height: plot.y1 - plot.y0 + 12 }, clip);

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
  gridY(gridG, y, niceTicks(vMin - pad, vMax + pad, 7), plot.x0, plot.x1, (v) => fmtLapTime(v).replace(/\.\d+$/, (m) => m.slice(0, 2)));
  for (const lap of lapTicks(maxLap, plot.x1 - plot.x0)) {
    el("text", { class: "axis-label", x: x(lap), y: plot.y1 + 17, "text-anchor": "middle", text: lap }, gridG);
  }
  el("text", { class: "axis-label", x: plot.x1 + 4, y: plot.y1 + 17, text: "Lap" }, gridG);

  const focusSize = state.focus.size;
  const linesG = el("g", { fill: "none", "clip-path": "url(#pace-clip)", "stroke-linejoin": "round", "stroke-linecap": "round" }, svg);
  const dotsG = el("g", { "clip-path": "url(#pace-clip)" }, svg);
  let hoverAbbr = null;
  const lineEls = new Map();

  for (const s of series) {
    // レースのみ線で結ぶ（予選・プラクティスはアウト/クールダウン混在のためドットのみ）
    let d = "";
    if (derived.isRace) {
      let prevLap = null;
      for (const rec of s.recs) {
        if (rec.del) { prevLap = null; continue; }
        const px = x(rec.lap), py = y(rec.t);
        d += (prevLap != null && rec.lap - prevLap <= 1 ? "L" : "M") + `${px},${py}`;
        prevLap = rec.lap;
      }
    }
    const path = el("path", {
      d, stroke: s.color, "stroke-width": 2, "stroke-dasharray": dashArray(s.dash),
    }, linesG);
    lineEls.set(s.abbr, path);

    for (const rec of s.recs) {
      const color = bundle.compound_colors[rec.cmp] ?? "#8a8f9c";
      if (rec.del) {
        const dot = el("rect", {
          x: x(rec.lap) - 3.2, y: y(rec.t) - 3.2, width: 6.4, height: 6.4,
          transform: `rotate(45 ${x(rec.lap)} ${y(rec.t)})`,
          fill: "none", stroke: color, "stroke-width": 1.6,
        }, dotsG);
        dot.dataset.abbr = s.abbr;
      } else {
        const dot = el("circle", {
          cx: x(rec.lap), cy: y(rec.t), r: 3.4,
          fill: color, stroke: "var(--surface-1)", "stroke-width": 1.6,
        }, dotsG);
        dot.dataset.abbr = s.abbr;
      }
    }
  }

  applyEmphasis();
  function applyEmphasis() {
    for (const s of series) {
      const line = lineEls.get(s.abbr);
      const active = hoverAbbr == null || s.abbr === hoverAbbr;
      line.setAttribute("opacity", active ? 0.95 : 0.18);
      line.setAttribute("stroke-width", hoverAbbr != null && active ? 3 : 2);
    }
    for (const dot of dotsG.children) {
      const active = hoverAbbr == null || dot.dataset.abbr === hoverAbbr;
      dot.setAttribute("opacity", active ? 1 : 0.15);
    }
  }

  attachCrosshair(svg, plot, {
    snap(px) {
      const lap = Math.max(1, Math.min(maxLap, Math.round(x.invert(px))));
      return { px: x(lap), lap };
    },
    onMove(snapped, clientX, clientY, localY) {
      const lap = snapped.lap;
      let nearest = null, bestDy = 16;
      for (const s of series) {
        const rec = s.recAt.get(lap);
        if (!rec) continue;
        const dy = Math.abs(y(rec.t) - localY);
        if (dy < bestDy) { bestDy = dy; nearest = s.abbr; }
      }
      if (nearest !== hoverAbbr) { hoverAbbr = nearest; applyEmphasis(); }

      const rows = [];
      for (const s of series) {
        const rec = s.recAt.get(lap);
        if (!rec) continue;
        const notes = [];
        if (rec.pit_in) notes.push("P-in");
        if (rec.pit_out) notes.push("P-out");
        if (rec.del) notes.push("DEL");
        if (rec.pb && !rec.del) notes.push("PB");
        rows.push({
          color: s.color, dash: s.dash, label: s.abbr,
          value: fmtLapTime(rec.t), _t: rec.t,
          extra: `${compoundLetter(rec.cmp)}${rec.life ?? ""}${notes.length ? " " + notes.join("/") : ""}`,
          valueColor: s.abbr === hoverAbbr ? "#ffffff" : undefined,
        });
      }
      rows.sort((a, b) => a._t - b._t);
      const kind = derived.statusPerLap.get(lap);
      tooltip.showRows(clientX, clientY, {
        title: `Lap ${lap}/${derived.totalLaps}${kind ? `　[${kind === "RED" ? "赤旗" : kind}]` : ""}`,
        rows,
      });
    },
    onLeave() { hoverAbbr = null; applyEmphasis(); },
  });
}

function buildTable(series, derived) {
  const wrap = document.createElement("div");
  wrap.className = "data-table-wrap";
  const table = document.createElement("table");
  table.className = "data-table";
  const thead = document.createElement("thead");
  const headRow = document.createElement("tr");
  for (const h of ["Lap", "ドライバー", "タイム", "S1", "S2", "S3", "タイヤ", "周回数", "Pos", "備考"]) {
    const th = document.createElement("th");
    th.textContent = h;
    if (["タイム", "S1", "S2", "S3", "周回数", "Pos"].includes(h)) th.className = "num";
    headRow.appendChild(th);
  }
  thead.appendChild(headRow);
  table.appendChild(thead);

  const rows = [];
  for (const s of series) for (const rec of s.recs) rows.push({ s, rec });
  rows.sort((a, b) => a.rec.lap - b.rec.lap || (a.rec.pos ?? 99) - (b.rec.pos ?? 99));

  const tbody = document.createElement("tbody");
  const cap = 800;
  for (const { s, rec } of rows.slice(0, cap)) {
    const tr = document.createElement("tr");
    const notes = [];
    if (rec.pit_in) notes.push("P-in");
    if (rec.pit_out) notes.push("P-out");
    if (rec.del) notes.push("削除");
    if (rec.pb && !rec.del) notes.push("PB");
    const kind = statusKind(rec.ts);
    if (kind) notes.push(kind);
    const cells = [
      rec.lap, null, fmtLapTime(rec.t), fmtLapTime(rec.s1), fmtLapTime(rec.s2), fmtLapTime(rec.s3),
      `${compoundLetter(rec.cmp)}`, rec.life ?? "—", rec.pos ?? "—", notes.join(" / ") || "—",
    ];
    cells.forEach((v, i) => {
      const td = document.createElement("td");
      if (i === 1) {
        const key = document.createElement("span");
        key.className = "team-key";
        key.style.background = s.color;
        td.appendChild(key);
        td.appendChild(document.createTextNode(s.abbr));
      } else {
        td.textContent = String(v);
        if ([2, 3, 4, 5, 7, 8].includes(i)) td.className = "num";
      }
      tr.appendChild(td);
    });
    tbody.appendChild(tr);
  }
  table.appendChild(tbody);
  wrap.appendChild(table);
  if (rows.length > cap) {
    const note = document.createElement("div");
    note.className = "panel-sub";
    note.textContent = `表示上限 ${cap} 行（全 ${rows.length} 行）。ドライバーを絞ると全行表示できます。`;
    wrap.appendChild(note);
  }
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
