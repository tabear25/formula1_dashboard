// セクター分析: ドライバー別のベストセクターと理論上ベストラップ（自己ベスト
// セクターの合計）。全体ベストのセクターは紫、自己ベストは緑で表示する。

import { state, toggleFocus } from "../state.js";
import { el, clearNode, linScale, tooltip } from "../svg.js";
import { fmtLapTime, fmtGap } from "../format.js";

let showDeleted = false;

export function renderSectors(container) {
  clearNode(container);
  const { bundle, derived } = state;

  const panel = document.createElement("div");
  panel.className = "panel";
  container.appendChild(panel);

  const head = document.createElement("div");
  head.className = "panel-head";
  head.innerHTML = `<div class="panel-title">セクター分析</div>
    <div class="panel-sub">各ドライバーのベストセクターと理論値（3セクター自己ベストの合計）。紫＝全体ベスト。行クリックで選択。</div>`;
  const controls = document.createElement("div");
  controls.className = "panel-controls";
  const btn = document.createElement("button");
  btn.className = `toggle-btn${showDeleted ? " on" : ""}`;
  btn.textContent = "削除ラップ含む";
  btn.addEventListener("click", () => { showDeleted = !showDeleted; renderSectors(container); });
  controls.appendChild(btn);
  head.appendChild(controls);
  panel.appendChild(head);

  // ドライバー別のセクター自己ベストと実ベストラップ
  const rows = [];
  for (const d of bundle.drivers) {
    const recs = (derived.lapsByDriver.get(d.abbr) ?? []).filter((r) => showDeleted || !r.del);
    let s1 = null, s2 = null, s3 = null, bestLap = null;
    let s1Lap = null, s2Lap = null, s3Lap = null;
    for (const r of recs) {
      if (r.s1 != null && (s1 == null || r.s1 < s1)) { s1 = r.s1; s1Lap = r.lap; }
      if (r.s2 != null && (s2 == null || r.s2 < s2)) { s2 = r.s2; s2Lap = r.lap; }
      if (r.s3 != null && (s3 == null || r.s3 < s3)) { s3 = r.s3; s3Lap = r.lap; }
      if (r.t != null && (bestLap == null || r.t < bestLap.t)) bestLap = r;
    }
    if (s1 == null && s2 == null && s3 == null) continue;
    const ideal = s1 != null && s2 != null && s3 != null ? s1 + s2 + s3 : null;
    rows.push({
      d, s1, s2, s3, s1Lap, s2Lap, s3Lap, bestLap, ideal,
      margin: ideal != null && bestLap ? bestLap.t - ideal : null,
    });
  }
  if (rows.length === 0) {
    panel.insertAdjacentHTML("beforeend", `<div class="empty-note">セクタータイムがありません。</div>`);
    return;
  }
  rows.sort((a, b) => {
    if (a.ideal == null) return 1;
    if (b.ideal == null) return -1;
    return a.ideal - b.ideal;
  });

  // 全体ベストセクター
  const best = {
    s1: Math.min(...rows.filter((r) => r.s1 != null).map((r) => r.s1)),
    s2: Math.min(...rows.filter((r) => r.s2 != null).map((r) => r.s2)),
    s3: Math.min(...rows.filter((r) => r.s3 != null).map((r) => r.s3)),
  };
  const superIdeal = best.s1 + best.s2 + best.s3;

  const note = document.createElement("div");
  note.className = "panel-sub";
  note.style.marginBottom = "6px";
  note.textContent = `究極の理論値（全ドライバーのベストセクター合計）: ${fmtLapTime(superIdeal)}`;
  panel.appendChild(note);

  // 表
  const wrap = document.createElement("div");
  wrap.className = "data-table-wrap";
  panel.appendChild(wrap);
  const table = document.createElement("table");
  table.className = "data-table";
  const thead = document.createElement("thead");
  thead.innerHTML = `<tr><th>#</th><th>ドライバー</th><th class="num">S1</th><th class="num">S2</th><th class="num">S3</th>
    <th class="num">理論値</th><th class="num">実ベスト</th><th class="num">未達</th></tr>`;
  table.appendChild(thead);
  const tbody = document.createElement("tbody");

  rows.forEach((r, i) => {
    const tr = document.createElement("tr");
    tr.style.cursor = "pointer";
    tr.addEventListener("click", () => toggleFocus(r.d.abbr));
    if (state.focus.size > 0 && !state.focus.has(r.d.abbr)) tr.style.opacity = "0.45";

    const tdRank = document.createElement("td");
    tdRank.className = "num";
    tdRank.textContent = String(i + 1);
    tr.appendChild(tdRank);

    const tdD = document.createElement("td");
    const key = document.createElement("span");
    key.className = "team-key";
    key.style.background = r.d.color;
    tdD.appendChild(key);
    const strong = document.createElement("strong");
    strong.textContent = r.d.abbr;
    tdD.appendChild(strong);
    tdD.appendChild(document.createTextNode(`　${r.d.name ?? ""}`));
    tr.appendChild(tdD);

    const secCell = (val, lap, bestVal) => {
      const td = document.createElement("td");
      td.className = "num";
      if (val == null) { td.textContent = "—"; return td; }
      const span = document.createElement("span");
      span.textContent = fmtLapTime(val);
      if (Math.abs(val - bestVal) < 0.0005) span.className = "best-purple";
      td.appendChild(span);
      if (lap != null) {
        const lapSpan = document.createElement("span");
        lapSpan.textContent = ` L${lap}`;
        lapSpan.style.color = "var(--ink-3)";
        lapSpan.style.fontSize = "11px";
        td.appendChild(lapSpan);
      }
      return td;
    };
    tr.appendChild(secCell(r.s1, r.s1Lap, best.s1));
    tr.appendChild(secCell(r.s2, r.s2Lap, best.s2));
    tr.appendChild(secCell(r.s3, r.s3Lap, best.s3));

    const tdIdeal = document.createElement("td");
    tdIdeal.className = "num";
    tdIdeal.textContent = r.ideal != null ? fmtLapTime(r.ideal) : "—";
    tdIdeal.style.fontWeight = "600";
    tr.appendChild(tdIdeal);

    const tdActual = document.createElement("td");
    tdActual.className = "num";
    tdActual.textContent = r.bestLap ? fmtLapTime(r.bestLap.t) : "—";
    tr.appendChild(tdActual);

    const tdMargin = document.createElement("td");
    tdMargin.className = "num";
    if (r.margin != null) {
      tdMargin.textContent = fmtGap(r.margin);
      tdMargin.style.color = r.margin < 0.15 ? "var(--good)" : (r.margin > 0.5 ? "var(--warn)" : "var(--ink-2)");
    } else {
      tdMargin.textContent = "—";
    }
    tr.appendChild(tdMargin);
    tbody.appendChild(tr);
  });
  table.appendChild(tbody);
  wrap.appendChild(table);

  // セクター差の可視化: 理論値トップとの差を積み上げバーで表示
  drawGapBars(panel, container, rows, best);
}

function drawGapBars(panel, container, rows, best) {
  const withIdeal = rows.filter((r) => r.ideal != null);
  if (withIdeal.length < 2) return;

  const head = document.createElement("div");
  head.className = "panel-sub";
  head.style.margin = "14px 0 4px";
  head.textContent = "ベストセクターごとの全体ベストとの差（積み上げ。短いほど速い）";
  panel.appendChild(head);

  const host = document.createElement("div");
  host.className = "chart-host";
  panel.appendChild(host);

  const ML = 92, MR = 70, ROW = 20;
  const width = Math.max(680, host.clientWidth || container.clientWidth || 900);
  const height = withIdeal.length * ROW + 30;
  const svg = el("svg", { viewBox: `0 0 ${width} ${height}`, width, height });
  host.appendChild(svg);

  const maxGap = Math.max(...withIdeal.map((r) => (r.s1 - best.s1) + (r.s2 - best.s2) + (r.s3 - best.s3)), 0.001);
  const x = linScale(0, maxGap * 1.02, ML, width - MR);
  const SEC_COLORS = ["#3987e5", "#b18bf5", "#f3c04b"];

  withIdeal.forEach((r, i) => {
    const cy = 12 + i * ROW;
    const label = el("text", {
      class: "drv-label", x: ML - 10, y: cy + 4, "text-anchor": "end", text: r.d.abbr,
    }, svg);
    label.addEventListener("click", () => toggleFocus(r.d.abbr));
    el("line", {
      x1: ML - 34, x2: ML - 22, y1: cy, y2: cy,
      stroke: r.d.color, "stroke-width": 3, "stroke-linecap": "round",
    }, svg);

    let acc = 0;
    const gaps = [r.s1 - best.s1, r.s2 - best.s2, r.s3 - best.s3];
    gaps.forEach((g, s) => {
      if (g <= 0) return;
      const rect = el("rect", {
        x: x(acc), y: cy - 6, width: Math.max(1, x(acc + g) - x(acc)), height: 12,
        fill: SEC_COLORS[s], "fill-opacity": 0.85,
      }, svg);
      rect.addEventListener("pointermove", (evt) => {
        tooltip.showRows(evt.clientX, evt.clientY, {
          title: `${r.d.abbr} — S${s + 1}`,
          rows: [{ label: `S${s + 1}の差`, value: fmtGap(g) }],
        });
      });
      rect.addEventListener("pointerleave", () => tooltip.hide());
      acc += g;
    });
    el("text", {
      class: "axis-label", x: x(acc) + 6, y: cy + 3.5, text: fmtGap(acc),
    }, svg);
  });

  // 凡例
  const legY = height - 8;
  ["S1", "S2", "S3"].forEach((s, i) => {
    el("rect", { x: ML + i * 60, y: legY - 9, width: 10, height: 10, fill: SEC_COLORS[i], "fill-opacity": 0.85 }, svg);
    el("text", { class: "axis-label", x: ML + i * 60 + 15, y: legY, text: s }, svg);
  });
}
