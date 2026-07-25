// トラックドミナンス: 最速ラップをミニセクターに分割し、区間ごとに最速の
// ドライバーのチームカラーでコースを塗る。データは既存 /api/telemetry を利用し、
// コース形状は /api/trackmap の幾何を使う（全員同じ線上に描くため）。

import { state } from "../state.js";
import { api } from "../api.js";
import { el, clearNode, tooltip } from "../svg.js";
import { fmtLapTime, fmtGap } from "../format.js";

const MAX_DRIVERS = 6;

let lastSessionKey = null;
let selAbbrs = null;      // ユーザーが明示選択した比較対象（null = focus/上位から自動）
const cache = new Map();  // fetchKey -> {data, tm}

export function renderDominance(container) {
  clearNode(container);
  const { bundle, sessionKey } = state;

  const keyStr = `${sessionKey.year}:${sessionKey.round}:${sessionKey.code}`;
  if (lastSessionKey !== keyStr) {
    lastSessionKey = keyStr;
    selAbbrs = null;
    cache.clear();
  }

  const panel = document.createElement("div");
  panel.className = "panel";
  container.appendChild(panel);

  // 比較対象: 明示選択 > focus(2名以上) > 上位3名
  const focusArr = [...state.focus];
  let abbrs;
  if (selAbbrs != null) {
    // ユーザーが明示選択を始めたら、2名未満でもその集合を尊重する（下のガードで案内表示）
    abbrs = selAbbrs.slice(0, MAX_DRIVERS);
  } else if (focusArr.length >= 2) {
    abbrs = focusArr.slice(0, MAX_DRIVERS);
  } else {
    abbrs = bundle.drivers.slice(0, 3).map((d) => d.abbr);
  }

  const head = document.createElement("div");
  head.className = "panel-head";
  head.innerHTML = `<div class="panel-title">トラックドミナンス</div>
    <div class="panel-sub">各ドライバーの最速ラップをミニセクターで比較し、区間最速の色で塗る。ホバーで区間タイム差。最大${MAX_DRIVERS}名。</div>`;

  const controls = document.createElement("div");
  controls.className = "panel-controls";
  for (const d of bundle.drivers) {
    const btn = document.createElement("button");
    btn.className = `toggle-btn${abbrs.includes(d.abbr) ? " on" : ""}`;
    btn.textContent = d.abbr;
    btn.style.borderBottom = `2px solid ${d.color}`;
    btn.addEventListener("click", () => {
      const cur = new Set(selAbbrs ?? abbrs);
      if (cur.has(d.abbr)) cur.delete(d.abbr);
      else if (cur.size < MAX_DRIVERS) cur.add(d.abbr);
      selAbbrs = [...cur];
      renderDominance(container);
    });
    controls.appendChild(btn);
  }
  head.appendChild(controls);
  panel.appendChild(head);

  const host = document.createElement("div");
  host.className = "chart-host";
  panel.appendChild(host);

  if (abbrs.length < 2) {
    host.innerHTML = `<div class="empty-note">2名以上を選択してください（上のボタン、またはドライバーチップから）。</div>`;
    return;
  }

  const loading = document.createElement("div");
  loading.className = "empty-note";
  loading.textContent = "テレメトリを読み込み中…";
  host.appendChild(loading);

  const fetchKey = `${keyStr}|${[...abbrs].sort().join(",")}`;
  const paint = ({ data, tm }) => {
    if (!host.isConnected) return;
    clearNode(host);
    drawDominance(host, container, data, tm, abbrs);
  };

  if (cache.has(fetchKey)) {
    paint(cache.get(fetchKey));
    return;
  }
  Promise.all([
    api.telemetry(sessionKey.year, sessionKey.round, sessionKey.code, abbrs, "fastest"),
    api.trackmap(sessionKey.year, sessionKey.round, sessionKey.code),
  ]).then(([data, tm]) => {
    cache.set(fetchKey, { data, tm });
    if (cache.size > 6) cache.delete(cache.keys().next().value);
    paint({ data, tm });
  }).catch((err) => {
    if (host.isConnected) loading.textContent = `取得に失敗しました: ${err.message}`;
  });
}

function drawDominance(host, container, data, tm, abbrs) {
  const { derived } = state;
  if (!tm || tm.error || !tm.x || tm.x.length < 3) {
    host.innerHTML = `<div class="empty-note">コース形状を取得できません。${tm?.error ?? ""}</div>`;
    return;
  }
  // コース全長の95%以上をカバーするテレメトリだけを比較対象にする。
  // 途中で切れたラップを許すと commonLen が縮み、残り区間が単色に塗り潰されてしまう。
  const trackLenAll = tm.d[tm.d.length - 1];
  const covered = (L) => !L.error && L.d && L.d.length > 1 && L.d[L.d.length - 1] >= trackLenAll * 0.95;
  const laps = (data.laps ?? []).filter(covered);
  const errors = [
    ...(data.laps ?? []).filter((L) => L.error),
    ...(data.laps ?? []).filter((L) => !L.error && !covered(L))
      .map((L) => ({ abbr: L.abbr, error: "テレメトリが途中で欠損" })),
  ];
  if (laps.length < 2) {
    const msgs = errors.map((e) => `${e.abbr}: ${e.error}`).join(" / ");
    host.innerHTML = `<div class="empty-note">比較できるテレメトリが2名分ありません。${msgs}</div>`;
    return;
  }

  const meta = laps.map((L) => {
    const d = derived.driverMap.get(L.abbr);
    return { ...L, color: d?.color ?? "#8a8f9c" };
  });

  // ミニセクター境界: コース全長から決定（約170m刻み、20〜40区間）
  const commonLen = Math.min(trackLenAll, ...meta.map((L) => L.d[L.d.length - 1]));
  const nSec = Math.max(20, Math.min(40, Math.round(commonLen / 170)));
  const secLen = commonLen / nSec;

  // 各ドライバーの区間タイム: t(d) の線形補間で境界時刻を求め差分
  const secTimes = meta.map((L) => {
    const interpT = makeInterp(L.d, L.t);
    const times = [];
    for (let s = 0; s < nSec; s++) {
      const t0 = interpT(s * secLen);
      const t1 = interpT((s + 1) * secLen);
      times.push(t0 != null && t1 != null ? t1 - t0 : null);
    }
    return times;
  });

  // 区間ごとの勝者
  const winners = [];   // index into meta
  for (let s = 0; s < nSec; s++) {
    let best = -1, bestT = Infinity;
    for (let i = 0; i < meta.length; i++) {
      const t = secTimes[i][s];
      if (t != null && t < bestT) { bestT = t; best = i; }
    }
    winners.push(best);
  }

  // サマリ行: 各ドライバーの獲得区間数とラップタイム
  const info = document.createElement("div");
  info.className = "panel-sub";
  info.style.marginBottom = "6px";
  info.textContent = meta.map((L, i) => {
    const won = winners.filter((w) => w === i).length;
    return `${L.abbr}: ${won}区間 / Lap ${L.lap} ${fmtLapTime(L.lap_time)}`;
  }).join("　／　") + (errors.length ? `　／　取得不可 → ${errors.map((e) => e.abbr).join(", ")}` : "");
  host.appendChild(info);

  // 描画（track.js と同じ座標系）
  const xs = tm.x, ys = tm.y, ds = tm.d;
  const width = Math.max(680, host.clientWidth || container.clientWidth || 900);
  const height = 560;
  const pad = 60;
  const minX = Math.min(...xs), maxX = Math.max(...xs);
  const minY = Math.min(...ys), maxY = Math.max(...ys);
  const k = Math.min((width - pad * 2) / (maxX - minX || 1), (height - pad * 2) / (maxY - minY || 1));
  const ox = (width - (maxX - minX) * k) / 2;
  const oy = (height - (maxY - minY) * k) / 2;
  const px = (x) => ox + (x - minX) * k;
  const py = (y) => oy + (maxY - y) * k;

  const svg = el("svg", { viewBox: `0 0 ${width} ${height}`, width, height });
  host.appendChild(svg);

  // 縁取り
  let outline = "";
  for (let i = 0; i < xs.length; i++) outline += (i ? "L" : "M") + `${px(xs[i]).toFixed(1)},${py(ys[i]).toFixed(1)}`;
  outline += "Z";
  el("path", { d: outline, stroke: "#060810", "stroke-width": 9, fill: "none", "stroke-linejoin": "round", "stroke-linecap": "round" }, svg);

  // 勝者色で塗る（コース幾何の各セグメントを距離で区間に割り当て）
  const segsG = el("g", { fill: "none", "stroke-linecap": "round" }, svg);
  for (let i = 1; i < xs.length; i++) {
    const dMid = (ds[i - 1] + ds[i]) / 2;
    const s = Math.min(nSec - 1, Math.floor(dMid / secLen));
    const w = winners[s];
    el("line", {
      x1: px(xs[i - 1]), y1: py(ys[i - 1]), x2: px(xs[i]), y2: py(ys[i]),
      stroke: w >= 0 ? meta[w].color : "var(--ink-3)", "stroke-width": 5,
    }, segsG);
  }

  // コーナー番号
  for (const c of tm.corners ?? []) {
    el("circle", { cx: px(c.x), cy: py(c.y), r: 2.4, fill: "var(--ink-3)" }, svg);
    el("text", {
      class: "axis-label", x: px(c.lx), y: py(c.ly) + 3.5, "text-anchor": "middle",
      "font-size": 10.5, "font-weight": 600, text: `${c.n}${c.letter ?? ""}`,
    }, svg);
  }

  // 凡例（色 = ドライバー）
  const legend = el("g", {}, svg);
  meta.forEach((L, i) => {
    const lx = 24, ly = 28 + i * 20;
    el("line", { x1: lx, x2: lx + 18, y1: ly, y2: ly, stroke: L.color, "stroke-width": 4, "stroke-linecap": "round" }, legend);
    el("text", { class: "axis-label", x: lx + 26, y: ly + 3.5, "font-weight": 600, text: `${L.abbr}（${winners.filter((w) => w === i).length}）` }, legend);
  });

  // ホバー: 最寄り区間の全員のタイムと差
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
    const s = Math.min(nSec - 1, Math.floor(ds[best] / secLen));
    const times = meta.map((L, i) => ({ L, i, t: secTimes[i][s] }))
      .filter((r) => r.t != null)
      .sort((a, b) => a.t - b.t);
    const bestT = times[0]?.t ?? null;
    tooltip.showRows(evt.clientX, evt.clientY, {
      title: `ミニセクター ${s + 1}/${nSec}（${Math.round(s * secLen)}–${Math.round((s + 1) * secLen)}m）`,
      rows: times.map((r, rank) => ({
        color: r.L.color, label: r.L.abbr,
        value: `${r.t.toFixed(3)}s`,
        extra: rank === 0 ? "最速" : fmtGap(r.t - bestT),
        valueColor: rank === 0 ? "#ffffff" : undefined,
      })),
    });
  });
  svg.addEventListener("pointerleave", () => {
    marker.setAttribute("visibility", "hidden");
    tooltip.hide();
  });
}

// 単調増加 xs に対する線形補間。丸め・始点オフセット由来の数mは端点値へ
// クランプし、それを超える範囲外（欠損区間）は null を返す。
function makeInterp(xs, ys) {
  const EPS = 5; // m
  return (x) => {
    if (x < xs[0] - EPS || x > xs[xs.length - 1] + EPS) return null;
    if (x <= xs[0]) return ys[0];
    if (x >= xs[xs.length - 1]) return ys[ys.length - 1];
    let lo = 0, hi = xs.length - 1;
    while (hi - lo > 1) {
      const mid = (lo + hi) >> 1;
      if (xs[mid] <= x) lo = mid; else hi = mid;
    }
    const span = xs[hi] - xs[lo];
    if (span <= 0) return ys[lo];
    return ys[lo] + (ys[hi] - ys[lo]) * ((x - xs[lo]) / span);
  };
}
