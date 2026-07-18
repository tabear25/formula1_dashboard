// トラックマップ: セッション最速ラップの走行ラインを速度で塗る

import { state } from "../state.js";
import { api } from "../api.js";
import { el, clearNode, tooltip } from "../svg.js";
import { fmtLapTime } from "../format.js";

let lastSessionKey = null;
let cached = null;

// ダーク背景用の単一色相（青）ランプ: 遅い=濃 → 速い=淡
const RAMP = ["#0d366b", "#104281", "#184f95", "#1c5cab", "#256abf", "#2a78d6", "#3987e5", "#5598e7", "#6da7ec", "#86b6ef", "#9ec5f4", "#b7d3f6"];

function rampColor(t) {
  const idx = Math.max(0, Math.min(RAMP.length - 1, Math.floor(t * (RAMP.length - 1) + 0.5)));
  return RAMP[idx];
}

export function renderTrack(container) {
  clearNode(container);
  const { sessionKey } = state;
  const keyStr = `${sessionKey.year}:${sessionKey.round}:${sessionKey.code}`;

  const panel = document.createElement("div");
  panel.className = "panel";
  container.appendChild(panel);

  const head = document.createElement("div");
  head.className = "panel-head";
  head.innerHTML = `<div class="panel-title">トラックマップ</div>
    <div class="panel-sub" id="track-sub">セッション最速ラップの走行ライン。色 = 速度。</div>`;
  panel.appendChild(head);

  const host = document.createElement("div");
  host.className = "chart-host";
  panel.appendChild(host);

  const loading = document.createElement("div");
  loading.className = "empty-note";
  loading.textContent = "トラックデータを読み込み中…";
  host.appendChild(loading);

  const paint = (tm) => {
    if (!host.isConnected) return;
    clearNode(host);
    if (!tm || tm.error) {
      host.innerHTML = `<div class="empty-note">トラックマップを表示できません。${tm?.error ?? ""}</div>`;
      return;
    }
    const sub = head.querySelector("#track-sub");
    sub.textContent = `最速ラップ: ${tm.abbr} ${fmtLapTime(tm.lap_time)}　／　色 = 速度`;
    drawTrack(host, container, tm);
  };

  if (lastSessionKey === keyStr && cached) {
    paint(cached);
    return;
  }
  api.trackmap(sessionKey.year, sessionKey.round, sessionKey.code)
    .then((tm) => { lastSessionKey = keyStr; cached = tm; paint(tm); })
    .catch((err) => {
      if (host.isConnected) loading.textContent = `取得に失敗しました: ${err.message}`;
    });
}

function drawTrack(host, container, tm) {
  const xs = tm.x, ys = tm.y, vs = tm.v, ds = tm.d;
  const width = Math.max(680, host.clientWidth || container.clientWidth || 900);
  const height = 560;
  const pad = 60;

  const minX = Math.min(...xs), maxX = Math.max(...xs);
  const minY = Math.min(...ys), maxY = Math.max(...ys);
  const k = Math.min((width - pad * 2) / (maxX - minX || 1), (height - pad * 2) / (maxY - minY || 1));
  const ox = (width - (maxX - minX) * k) / 2;
  const oy = (height - (maxY - minY) * k) / 2;
  const px = (x) => ox + (x - minX) * k;
  const py = (y) => oy + (maxY - y) * k;   // データ座標は上が正 → SVG は反転

  const svg = el("svg", { viewBox: `0 0 ${width} ${height}`, width, height });
  host.appendChild(svg);

  const vMin = Math.min(...vs), vMax = Math.max(...vs);
  const norm = (v) => (v - vMin) / ((vMax - vMin) || 1);

  // 下地（走行ラインの縁取り）
  let outline = "";
  for (let i = 0; i < xs.length; i++) outline += (i ? "L" : "M") + `${px(xs[i]).toFixed(1)},${py(ys[i]).toFixed(1)}`;
  outline += "Z";
  el("path", { d: outline, stroke: "#060810", "stroke-width": 9, fill: "none", "stroke-linejoin": "round", "stroke-linecap": "round" }, svg);

  // 速度セグメント
  const segs = el("g", { fill: "none", "stroke-linecap": "round" }, svg);
  for (let i = 1; i < xs.length; i++) {
    el("line", {
      x1: px(xs[i - 1]), y1: py(ys[i - 1]), x2: px(xs[i]), y2: py(ys[i]),
      stroke: rampColor(norm((vs[i] + vs[i - 1]) / 2)), "stroke-width": 5,
    }, segs);
  }

  // スタート/フィニッシュ
  if (xs.length > 2) {
    const dx = px(xs[1]) - px(xs[0]);
    const dy = py(ys[1]) - py(ys[0]);
    const len = Math.hypot(dx, dy) || 1;
    const nx = -dy / len, ny = dx / len;
    el("line", {
      x1: px(xs[0]) - nx * 9, y1: py(ys[0]) - ny * 9,
      x2: px(xs[0]) + nx * 9, y2: py(ys[0]) + ny * 9,
      stroke: "var(--ink)", "stroke-width": 3,
    }, svg);
    el("text", {
      class: "axis-label", x: px(xs[0]) + nx * 16 - 8, y: py(ys[0]) + ny * 16 + 4,
      "font-weight": 700, text: "S/F",
    }, svg);
  }

  // コーナー番号
  for (const c of tm.corners ?? []) {
    el("circle", { cx: px(c.x), cy: py(c.y), r: 2.4, fill: "var(--ink-3)" }, svg);
    el("text", {
      class: "axis-label", x: px(c.lx), y: py(c.ly) + 3.5, "text-anchor": "middle",
      "font-size": 10.5, "font-weight": 600, text: `${c.n}${c.letter ?? ""}`,
    }, svg);
  }

  // 速度凡例（グラデーションバー）
  const defs = el("defs", {}, svg);
  const grad = el("linearGradient", { id: "speed-grad", x1: 0, y1: 0, x2: 1, y2: 0 }, defs);
  RAMP.forEach((color, i) => {
    el("stop", { offset: `${(i / (RAMP.length - 1)) * 100}%`, "stop-color": color }, grad);
  });
  const legendX = 24, legendY = height - 34, legendW = 180;
  el("rect", { x: legendX, y: legendY, width: legendW, height: 8, rx: 4, fill: "url(#speed-grad)" }, svg);
  el("text", { class: "axis-label", x: legendX, y: legendY - 6, text: `${Math.round(vMin)} km/h` }, svg);
  el("text", { class: "axis-label", x: legendX + legendW, y: legendY - 6, "text-anchor": "end", text: `${Math.round(vMax)} km/h` }, svg);

  // ホバー: 最寄り点のスピード表示
  const marker = el("circle", { r: 6, fill: "none", stroke: "#fff", "stroke-width": 2, visibility: "hidden" }, svg);
  svg.addEventListener("pointermove", (evt) => {
    const rect = svg.getBoundingClientRect();
    const sx = svg.viewBox.baseVal.width / rect.width;
    const mx = (evt.clientX - rect.left) * sx;
    const my = (evt.clientY - rect.top) * (svg.viewBox.baseVal.height / rect.height);
    let best = -1, bestD = 30 * 30;
    for (let i = 0; i < xs.length; i += 2) {
      const dd = (px(xs[i]) - mx) ** 2 + (py(ys[i]) - my) ** 2;
      if (dd < bestD) { bestD = dd; best = i; }
    }
    if (best < 0) {
      marker.setAttribute("visibility", "hidden");
      tooltip.hide();
      return;
    }
    marker.setAttribute("cx", px(xs[best]));
    marker.setAttribute("cy", py(ys[best]));
    marker.setAttribute("visibility", "visible");
    let corner = null, cd = 150;
    for (const c of tm.corners ?? []) {
      const dd = Math.abs(c.dist - ds[best]);
      if (dd < cd) { cd = dd; corner = c; }
    }
    tooltip.showRows(evt.clientX, evt.clientY, {
      title: corner ? `T${corner.n}${corner.letter ?? ""} 付近` : "走行ライン",
      rows: [
        { label: "速度", value: `${Math.round(vs[best])} km/h` },
        { label: "距離", value: `${Math.round(ds[best])} m` },
      ],
    });
  });
  svg.addEventListener("pointerleave", () => {
    marker.setAttribute("visibility", "hidden");
    tooltip.hide();
  });
}
