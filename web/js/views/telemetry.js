// テレメトリ比較: 最大2名の最速ラップ（または指定ラップ）を距離軸で比較。
// パネル: 速度 / Δタイム(B−A) / スロットル / ブレーキ / ギア + コーナー位置

import { state } from "../state.js";
import { api } from "../api.js";
import { el, clearNode, linScale, niceTicks, gridY, attachCrosshair, dashArray, tooltip } from "../svg.js";
import { fmtLapTime, fmtGap, compoundLetter } from "../format.js";

const M = { top: 30, bottom: 26, left: 74, right: 26 };
const GAP = 16;

let selA = null;
let selB = null;
let selLap = "fastest";
let lastSessionKey = null;
const cache = new Map();

export function renderTelemetry(container) {
  clearNode(container);
  const { bundle, sessionKey } = state;

  const keyStr = `${sessionKey.year}:${sessionKey.round}:${sessionKey.code}`;
  if (lastSessionKey !== keyStr) {
    lastSessionKey = keyStr;
    selA = null; selB = null; selLap = "fastest";
    cache.clear();
  }

  const drivers = bundle.drivers;
  const focusArr = [...state.focus];
  if (!selA) selA = focusArr[0] ?? drivers[0]?.abbr ?? null;
  if (!selB) selB = focusArr.find((a) => a !== selA) ?? drivers.find((d) => d.abbr !== selA)?.abbr ?? null;
  if (selA === selB) selB = null;

  const panel = document.createElement("div");
  panel.className = "panel";
  container.appendChild(panel);

  const head = document.createElement("div");
  head.className = "panel-head";
  head.innerHTML = `<div class="panel-title">テレメトリ比較</div>
    <div class="panel-sub">距離基準で2名を比較。Δタイムは「B − A」（＋はBが遅れ）。</div>`;
  const controls = document.createElement("div");
  controls.className = "panel-controls";

  const mkSelect = (labelText, value, allowNone, onChange) => {
    const label = document.createElement("span");
    label.className = "panel-sub";
    label.textContent = labelText;
    controls.appendChild(label);
    const sel = document.createElement("select");
    if (allowNone) {
      const opt = document.createElement("option");
      opt.value = ""; opt.textContent = "—";
      sel.appendChild(opt);
    }
    for (const d of drivers) {
      const opt = document.createElement("option");
      opt.value = d.abbr;
      opt.textContent = `${d.abbr} (${d.team})`;
      sel.appendChild(opt);
    }
    sel.value = value ?? "";
    sel.addEventListener("change", () => { onChange(sel.value || null); renderTelemetry(container); });
    controls.appendChild(sel);
  };
  mkSelect("A:", selA, false, (v) => { selA = v; if (selB === v) selB = null; });
  mkSelect("B:", selB, true, (v) => { selB = v === selA ? null : v; });

  const lapLabel = document.createElement("span");
  lapLabel.className = "panel-sub";
  lapLabel.textContent = "ラップ:";
  controls.appendChild(lapLabel);
  const lapSel = document.createElement("select");
  const optF = document.createElement("option");
  optF.value = "fastest"; optF.textContent = "最速ラップ";
  lapSel.appendChild(optF);
  const maxLap = state.derived.maxLap;
  for (let lap = 1; lap <= maxLap; lap++) {
    const opt = document.createElement("option");
    opt.value = String(lap); opt.textContent = `Lap ${lap}`;
    lapSel.appendChild(opt);
  }
  lapSel.value = selLap;
  lapSel.addEventListener("change", () => { selLap = lapSel.value; renderTelemetry(container); });
  controls.appendChild(lapSel);

  head.appendChild(controls);
  panel.appendChild(head);

  const host = document.createElement("div");
  host.className = "chart-host";
  panel.appendChild(host);

  if (!selA) {
    host.innerHTML = `<div class="empty-note">ドライバーを選択してください。</div>`;
    return;
  }

  const loading = document.createElement("div");
  loading.className = "empty-note";
  loading.textContent = "テレメトリを読み込み中…";
  host.appendChild(loading);

  const abbrs = selB ? [selA, selB] : [selA];
  const fetchKey = `${keyStr}|${abbrs.join(",")}|${selLap}`;

  const paint = (data, corners) => {
    if (!host.isConnected) return;
    clearNode(host);
    drawTelemetry(host, container, data, corners);
  };

  if (cache.has(fetchKey)) {
    paint(...cache.get(fetchKey));
    return;
  }
  Promise.all([
    api.telemetry(sessionKey.year, sessionKey.round, sessionKey.code, abbrs, selLap),
    api.trackmap(sessionKey.year, sessionKey.round, sessionKey.code).catch(() => null),
  ]).then(([data, tm]) => {
    const corners = tm && !tm.error ? tm.corners : [];
    cache.set(fetchKey, [data, corners]);
    if (cache.size > 8) cache.delete(cache.keys().next().value);
    paint(data, corners);
  }).catch((err) => {
    if (!host.isConnected) return;
    loading.textContent = `テレメトリの取得に失敗しました: ${err.message}`;
  });
}

function drawTelemetry(host, container, data, corners) {
  const { bundle } = state;
  const laps = (data.laps ?? []).filter((L) => !L.error && L.d && L.d.length > 1);
  const errors = (data.laps ?? []).filter((L) => L.error);
  if (laps.length === 0) {
    const msgs = errors.map((e) => `${e.abbr}: ${e.error}`).join(" / ");
    host.innerHTML = `<div class="empty-note">テレメトリを表示できません。${msgs}</div>`;
    return;
  }

  const meta = laps.map((L) => {
    const d = state.derived.driverMap.get(L.abbr);
    return { ...L, color: d?.color ?? "#8a8f9c", dash: d?.dash ?? 0 };
  });
  const A = meta[0];
  const B = meta.length > 1 ? meta[1] : null;

  // ラップ情報の小さなサマリ
  const info = document.createElement("div");
  info.className = "panel-sub";
  info.style.marginBottom = "6px";
  info.textContent = meta.map((L) =>
    `${L.abbr}: Lap ${L.lap} ${fmtLapTime(L.lap_time)} (${compoundLetter(L.compound)})`).join("　／　") +
    (errors.length ? `　／　取得不可 → ${errors.map((e) => e.abbr).join(", ")}` : "");
  host.appendChild(info);

  const maxD = Math.max(...meta.map((L) => L.d[L.d.length - 1]));
  const width = Math.max(680, host.clientWidth || container.clientWidth || 900);

  // Δタイム系列（Bあり時のみ）
  let delta = null;
  if (B) {
    const interpB = makeInterp(B.d, B.t);
    delta = A.d.map((dist, i) => {
      const tb = interpB(dist);
      return tb == null ? null : tb - A.t[i];
    });
  }

  const panels = [];
  panels.push({ key: "v", label: "速度 km/h", h: 200, series: meta.map((L) => ({ ...L, ys: L.v })) });
  if (delta) panels.push({ key: "delta", label: `Δ ${B.abbr}−${A.abbr} (s)`, h: 100, series: null });
  panels.push({ key: "th", label: "スロットル %", h: 84, series: meta.map((L) => ({ ...L, ys: L.th })), domain: [0, 102] });
  panels.push({ key: "br", label: "ブレーキ", h: 46, series: meta.map((L) => ({ ...L, ys: L.br.map((v) => v * 100) })), domain: [0, 110], noTicks: true });
  panels.push({ key: "g", label: "ギア", h: 84, series: meta.map((L) => ({ ...L, ys: L.g })), domain: [1, 8.4], step: true });

  let height = M.top + M.bottom;
  for (const p of panels) height += p.h + GAP;

  const svg = el("svg", { viewBox: `0 0 ${width} ${height}`, width, height });
  host.appendChild(svg);
  const x = linScale(0, maxD, M.left, width - M.right);
  const fullPlot = { x0: M.left, x1: width - M.right, y0: M.top, y1: height - M.bottom };

  // コーナー位置の縦ライン + 番号
  const cornersG = el("g", {}, svg);
  for (const c of corners ?? []) {
    if (c.dist == null || c.dist > maxD) continue;
    const px = x(c.dist);
    el("line", { class: "gridline", x1: px, x2: px, y1: M.top - 4, y2: height - M.bottom, opacity: 0.7 }, cornersG);
    el("text", {
      class: "axis-label", x: px, y: M.top - 10, "text-anchor": "middle",
      "font-size": 9.5, text: `${c.n}${c.letter ?? ""}`,
    }, cornersG);
  }

  let yTop = M.top;
  const panelScales = [];
  for (const p of panels) {
    const py0 = yTop, py1 = yTop + p.h;
    yTop = py1 + GAP;
    let vals;
    if (p.key === "delta") {
      vals = delta.filter((v) => v != null);
    } else {
      vals = p.series.flatMap((s) => s.ys).filter((v) => v != null);
    }
    let d0, d1;
    if (p.domain) { [d0, d1] = p.domain; }
    else {
      d0 = Math.min(...vals); d1 = Math.max(...vals);
      const pad = (d1 - d0) * 0.08 || 1;
      d0 -= pad; d1 += pad;
      if (p.key === "delta") { const m = Math.max(Math.abs(d0), Math.abs(d1), 0.05); d0 = -m; d1 = m; }
    }
    const y = linScale(d0, d1, py1, py0);
    panelScales.push({ p, y, py0, py1 });

    // パネル枠 + グリッド + ラベル
    el("line", { class: "baseline", x1: M.left, x2: width - M.right, y1: py1, y2: py1 }, svg);
    if (!p.noTicks) {
      const ticks = p.key === "g" ? [2, 4, 6, 8] : niceTicks(d0, d1, p.h > 150 ? 5 : 3);
      gridY(el("g", {}, svg), y, ticks, M.left, width - M.right,
        (v) => p.key === "delta" ? fmtGap(v, 2) : String(Math.round(v)));
    }
    el("text", {
      class: "axis-label", x: M.left, y: py0 - 5, "font-weight": 600, text: p.label,
    }, svg);

    const linesG = el("g", { fill: "none", "stroke-linejoin": "round", "stroke-linecap": "round" }, svg);
    if (p.key === "delta") {
      el("line", { x1: M.left, x2: width - M.right, y1: y(0), y2: y(0), stroke: "var(--baseline)", "stroke-width": 1.4 }, svg);
      let dPath = "";
      let started = false;
      for (let i = 0; i < A.d.length; i++) {
        if (delta[i] == null) { started = false; continue; }
        dPath += (started ? "L" : "M") + `${x(A.d[i])},${y(delta[i])}`;
        started = true;
      }
      el("path", { d: dPath, stroke: "var(--ink-2)", "stroke-width": 2, fill: "none" }, linesG);
    } else {
      for (const s of p.series) {
        let dPath = "";
        for (let i = 0; i < s.d.length; i++) {
          const val = s.ys[i];
          if (val == null) continue;
          const px = x(s.d[i]);
          const py = p.step && i > 0 ? y(val) : y(val);
          dPath += (dPath ? "L" : "M") + `${px},${py}`;
        }
        el("path", {
          d: dPath, stroke: s.color, "stroke-width": p.key === "v" ? 2.2 : 1.8,
          "stroke-dasharray": dashArray(s.dash),
          opacity: 0.95,
        }, linesG);
      }
    }
  }

  // 距離軸
  const xt = niceTicks(0, maxD, 8);
  for (const t of xt) {
    el("text", { class: "axis-label", x: x(t), y: height - M.bottom + 18, "text-anchor": "middle", text: `${Math.round(t)}m` }, svg);
  }

  // クロスヘア（A のサンプル位置にスナップ）
  const interpolators = meta.map((L) => ({
    abbr: L.abbr, color: L.color, dash: L.dash,
    v: makeInterp(L.d, L.v), th: makeInterp(L.d, L.th),
    br: makeInterp(L.d, L.br), g: makeInterp(L.d, L.g),
  }));
  attachCrosshair(svg, fullPlot, {
    snap(px) {
      const dist = Math.max(0, Math.min(maxD, x.invert(px)));
      return { px: x(dist), dist };
    },
    onMove(snapped, clientX, clientY) {
      const dist = snapped.dist;
      const rows = [];
      for (const it of interpolators) {
        const v = it.v(dist);
        const g = it.g(dist);
        const th = it.th(dist);
        const br = it.br(dist);
        rows.push({
          color: it.color, dash: it.dash, label: it.abbr,
          value: v != null ? `${Math.round(v)} km/h` : "—",
          extra: `G${g != null ? Math.round(g) : "—"}  Thr${th != null ? Math.round(th) : "—"}%${br != null && br > 0.5 ? " BRK" : ""}`,
        });
      }
      if (delta) {
        const iB = makeInterp(A.d, delta);
        const dv = iB(dist);
        rows.push({ label: `Δ ${B.abbr}−${A.abbr}`, value: dv != null ? fmtGap(dv, 3) : "—" });
      }
      const corner = nearestCorner(corners, dist);
      tooltip.showRows(clientX, clientY, {
        title: `${Math.round(dist)} m${corner ? `　(T${corner.n}${corner.letter ?? ""} 付近)` : ""}`,
        rows,
      });
    },
  });
}

function nearestCorner(corners, dist) {
  if (!corners || corners.length === 0) return null;
  let best = null, bestD = 120;
  for (const c of corners) {
    const dd = Math.abs(c.dist - dist);
    if (dd < bestD) { bestD = dd; best = c; }
  }
  return best;
}

// 単調増加 xs に対する線形補間
function makeInterp(xs, ys) {
  return (x) => {
    if (x <= xs[0]) return ys[0];
    if (x >= xs[xs.length - 1]) return ys[ys.length - 1];
    let lo = 0, hi = xs.length - 1;
    while (hi - lo > 1) {
      const mid = (lo + hi) >> 1;
      if (xs[mid] <= x) lo = mid; else hi = mid;
    }
    const span = xs[hi] - xs[lo];
    if (span <= 0) return ys[lo];
    const f = (x - xs[lo]) / span;
    const a = ys[lo], b = ys[hi];
    if (a == null || b == null) return a ?? b;
    return a + (b - a) * f;
  };
}
