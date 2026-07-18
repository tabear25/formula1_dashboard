// リザルト表（レース / 予選 / プラクティスで列構成を切替）

import { state, toggleFocus } from "../state.js";
import { clearNode } from "../svg.js";
import { fmtLapTime, fmtRaceTime, fmtGap } from "../format.js";

export function renderResults(container) {
  clearNode(container);
  const { bundle, derived } = state;

  const panel = document.createElement("div");
  panel.className = "panel";
  container.appendChild(panel);

  const head = document.createElement("div");
  head.className = "panel-head";
  const typeLabel = bundle.meta.type === "race" ? "正式結果" : bundle.meta.type === "quali" ? "予選結果" : "セッション結果";
  head.innerHTML = `<div class="panel-title">${typeLabel}</div>
    <div class="panel-sub">行クリックでドライバーを選択（全チャート連動）。</div>`;
  panel.appendChild(head);

  const wrap = document.createElement("div");
  wrap.className = "data-table-wrap";
  panel.appendChild(wrap);

  if (bundle.meta.type === "race") wrap.appendChild(raceTable(bundle, derived));
  else if (bundle.meta.type === "quali") wrap.appendChild(qualiTable(bundle, derived));
  else wrap.appendChild(practiceTable(bundle, derived));
}

function makeTable(headers, numeric) {
  const table = document.createElement("table");
  table.className = "data-table";
  const thead = document.createElement("thead");
  const tr = document.createElement("tr");
  headers.forEach((h, i) => {
    const th = document.createElement("th");
    th.textContent = h;
    if (numeric.includes(i)) th.className = "num";
    tr.appendChild(th);
  });
  thead.appendChild(tr);
  table.appendChild(thead);
  return table;
}

function driverCell(d) {
  const td = document.createElement("td");
  const key = document.createElement("span");
  key.className = "team-key";
  key.style.background = d.color;
  td.appendChild(key);
  const strong = document.createElement("strong");
  strong.textContent = d.abbr;
  td.appendChild(strong);
  td.appendChild(document.createTextNode(`　${d.name ?? ""}`));
  return td;
}

function addRow(tbody, d, cells) {
  const tr = document.createElement("tr");
  tr.style.cursor = "pointer";
  for (const c of cells) tr.appendChild(c);
  tr.addEventListener("click", () => toggleFocus(d.abbr));
  if (state.focus.size > 0 && !state.focus.has(d.abbr)) tr.style.opacity = "0.45";
  tbody.appendChild(tr);
}

function td(textContent, cls) {
  const cell = document.createElement("td");
  if (textContent instanceof Node) cell.appendChild(textContent);
  else cell.textContent = textContent ?? "—";
  if (cls) cell.className = cls;
  return cell;
}

function raceTable(bundle, derived) {
  const table = makeTable(
    ["Pos", "ドライバー", "チーム", "Grid", "変動", "タイム / 結果", "FL", "Pts"],
    [0, 3, 7]);
  const tbody = document.createElement("tbody");
  const fl = derived.fastestLap;
  const winnerTime = bundle.drivers[0]?.time_s;

  for (const d of bundle.drivers) {
    const posText = d.classified && /^\d+$/.test(d.classified) ? d.classified : (d.classified ?? "—");
    const gridText = d.grid != null && d.grid >= 1 ? String(d.grid) : "PL";
    let deltaCell;
    if (d.grid != null && d.grid >= 1 && d.pos != null) {
      const diff = d.grid - d.pos;
      const span = document.createElement("span");
      if (diff > 0) { span.className = "delta-up"; span.textContent = `▲${diff}`; }
      else if (diff < 0) { span.className = "delta-down"; span.textContent = `▼${-diff}`; }
      else { span.className = "delta-zero"; span.textContent = "＝"; }
      deltaCell = td(span);
    } else {
      deltaCell = td("—");
    }
    let timeText;
    if (d.pos === 1 && d.time_s != null) timeText = fmtRaceTime(d.time_s);
    else if (d.status === "Finished" && d.time_s != null) timeText = fmtGap(d.time_s);
    else timeText = d.status ?? "—";

    let flCell = td("");
    if (fl && fl.abbr === d.abbr) {
      const span = document.createElement("span");
      span.className = "best-purple";
      span.textContent = `FL ${fmtLapTime(fl.t)} (L${fl.lap})`;
      flCell = td(span);
    }

    addRow(tbody, d, [
      td(posText, "num"), driverCell(d), td(d.team), td(gridText, "num"),
      deltaCell, td(timeText), flCell,
      td(d.points != null && d.points > 0 ? String(d.points) : "—", "num"),
    ]);
  }
  table.appendChild(tbody);
  return table;
}

function qualiTable(bundle, derived) {
  const table = makeTable(
    ["Pos", "ドライバー", "チーム", "Q1", "Q2", "Q3", "ポール差"],
    [0]);
  const tbody = document.createElement("tbody");
  const best = derived.qBest;
  const pole = bundle.drivers.find((d) => d.pos === 1);
  const poleQ3 = pole?.q3 ?? null;

  for (const d of bundle.drivers) {
    const segCell = (seg) => {
      if (d[seg] == null) return td("—", "num");
      const span = document.createElement("span");
      span.textContent = fmtLapTime(d[seg]);
      if (best[seg] != null && Math.abs(d[seg] - best[seg]) < 0.0005) span.className = "best-purple";
      return td(span, "num");
    };
    const gapText = d.q3 != null && poleQ3 != null && d.pos !== 1 ? fmtGap(d.q3 - poleQ3) : (d.pos === 1 ? "POLE" : "—");
    addRow(tbody, d, [
      td(d.pos != null ? String(d.pos) : "—", "num"), driverCell(d), td(d.team),
      segCell("q1"), segCell("q2"), segCell("q3"), td(gapText, "num"),
    ]);
  }
  table.appendChild(tbody);
  return table;
}

function practiceTable(bundle, derived) {
  const table = makeTable(
    ["Pos", "ドライバー", "チーム", "ベストラップ", "差", "周回数", "タイヤ"],
    [0, 4, 5]);
  const tbody = document.createElement("tbody");

  const rows = [];
  for (const d of bundle.drivers) {
    const laps = derived.lapsByDriver.get(d.abbr) ?? [];
    let bestRec = null;
    for (const rec of laps) {
      if (rec.t == null || rec.del) continue;
      if (!bestRec || rec.t < bestRec.t) bestRec = rec;
    }
    rows.push({ d, bestRec, count: laps.length });
  }
  rows.sort((a, b) => {
    if (a.bestRec == null) return 1;
    if (b.bestRec == null) return -1;
    return a.bestRec.t - b.bestRec.t;
  });
  const best = rows[0]?.bestRec?.t ?? null;

  rows.forEach(({ d, bestRec, count }, i) => {
    addRow(tbody, d, [
      td(String(i + 1), "num"), driverCell(d), td(d.team),
      td(bestRec ? fmtLapTime(bestRec.t) : "—", "num"),
      td(bestRec && best != null && i > 0 ? fmtGap(bestRec.t - best) : (i === 0 ? "—" : "—"), "num"),
      td(String(count), "num"),
      td(bestRec?.cmp ?? "—"),
    ]);
  });
  table.appendChild(tbody);
  return table;
}
