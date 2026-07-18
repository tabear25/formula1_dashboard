// レースコントロール: 天候の推移 + 競技メッセージのフィード

import { state } from "../state.js";
import { el, clearNode, linScale, niceTicks, gridY, attachCrosshair, tooltip } from "../svg.js";

let filter = "all";

export function renderControl(container) {
  clearNode(container);
  const { bundle } = state;

  // ---- 天候パネル ----
  const wPanel = document.createElement("div");
  wPanel.className = "panel";
  container.appendChild(wPanel);
  const wHead = document.createElement("div");
  wHead.className = "panel-head";
  wHead.innerHTML = `<div class="panel-title">天候</div>
    <div class="panel-sub">気温・路面温度の推移。青の帯 = 降雨。</div>`;
  wPanel.appendChild(wHead);

  const weather = bundle.weather ?? [];
  if (weather.length > 1) {
    drawWeather(wPanel, container, weather);
  } else {
    wPanel.insertAdjacentHTML("beforeend", `<div class="empty-note">天候データがありません。</div>`);
  }

  // ---- レースコントロールメッセージ ----
  const panel = document.createElement("div");
  panel.className = "panel";
  container.appendChild(panel);
  const head = document.createElement("div");
  head.className = "panel-head";
  head.innerHTML = `<div class="panel-title">レースコントロール</div>
    <div class="panel-sub">競技団からの通達（旗・SC・調査・ペナルティ等）。</div>`;
  const controls = document.createElement("div");
  controls.className = "panel-controls";
  const filters = [
    ["all", "すべて"], ["flag", "旗"], ["sc", "SC/VSC"],
    ["penalty", "ペナルティ/調査"], ["drs", "DRS"], ["other", "その他"],
  ];
  for (const [key, label] of filters) {
    const btn = document.createElement("button");
    btn.className = `toggle-btn${filter === key ? " on" : ""}`;
    btn.textContent = label;
    btn.addEventListener("click", () => { filter = key; renderControl(container); });
    controls.appendChild(btn);
  }
  head.appendChild(controls);
  panel.appendChild(head);

  const msgs = (bundle.race_control ?? []).filter((m) => matches(m, filter));
  if (msgs.length === 0) {
    panel.insertAdjacentHTML("beforeend", `<div class="empty-note">該当するメッセージはありません。</div>`);
    return;
  }

  const wrap = document.createElement("div");
  wrap.className = "data-table-wrap";
  panel.appendChild(wrap);
  const table = document.createElement("table");
  table.className = "data-table";
  const thead = document.createElement("thead");
  thead.innerHTML = `<tr><th>Lap</th><th>時刻(UTC)</th><th>種別</th><th>内容</th></tr>`;
  table.appendChild(thead);
  const tbody = document.createElement("tbody");
  for (const m of msgs) {
    const tr = document.createElement("tr");
    const tdLap = document.createElement("td");
    tdLap.className = "num";
    tdLap.textContent = m.lap != null ? String(m.lap) : "—";
    tr.appendChild(tdLap);
    const tdTime = document.createElement("td");
    tdTime.textContent = m.clock ? m.clock.split(" ")[1] ?? m.clock : "—";
    tr.appendChild(tdTime);
    const tdKind = document.createElement("td");
    tdKind.appendChild(kindChip(m));
    tr.appendChild(tdKind);
    const tdMsg = document.createElement("td");
    tdMsg.textContent = m.msg ?? "";
    tdMsg.style.whiteSpace = "normal";
    tr.appendChild(tdMsg);
    tbody.appendChild(tr);
  }
  table.appendChild(tbody);
  wrap.appendChild(table);
}

function matches(m, key) {
  const msg = (m.msg ?? "").toUpperCase();
  switch (key) {
    case "all": return true;
    case "flag": return m.cat === "Flag";
    case "sc": return m.cat === "SafetyCar" || msg.includes("SAFETY CAR") || msg.includes("VIRTUAL");
    case "penalty": return msg.includes("PENALTY") || msg.includes("INVESTIGAT") || msg.includes("DELETED") || msg.includes("NOTED") || msg.includes("REPRIMAND");
    case "drs": return m.cat === "Drs" || msg.includes("DRS");
    case "other": return m.cat !== "Flag" && m.cat !== "SafetyCar" && m.cat !== "Drs"
      && !msg.includes("PENALTY") && !msg.includes("INVESTIGAT") && !msg.includes("DELETED");
    default: return true;
  }
}

function kindChip(m) {
  const chip = document.createElement("span");
  chip.className = "flag-chip";
  const msg = (m.msg ?? "").toUpperCase();
  if (m.cat === "Flag") {
    const flag = (m.flag ?? "").toUpperCase();
    chip.textContent = m.flag ?? "FLAG";
    if (flag.includes("GREEN") || flag === "CLEAR") chip.classList.add("f-green");
    else if (flag.includes("YELLOW")) chip.classList.add("f-yellow");
    else if (flag.includes("RED")) chip.classList.add("f-red");
    else if (flag.includes("BLUE")) chip.classList.add("f-blue");
    else if (flag.includes("CHEQUERED")) chip.classList.add("f-cheq");
  } else if (m.cat === "SafetyCar" || msg.includes("SAFETY CAR") || msg.includes("VIRTUAL")) {
    chip.textContent = msg.includes("VIRTUAL") ? "VSC" : "SC";
    chip.classList.add("f-sc");
  } else if (msg.includes("PENALTY")) {
    chip.textContent = "PENALTY";
    chip.classList.add("f-red");
  } else if (msg.includes("INVESTIGAT") || msg.includes("NOTED")) {
    chip.textContent = "調査";
    chip.classList.add("f-yellow");
  } else if (m.cat === "Drs") {
    chip.textContent = "DRS";
  } else {
    chip.textContent = m.cat ?? "INFO";
  }
  return chip;
}

const WM = { top: 24, bottom: 26, left: 56, right: 70 };

function drawWeather(panel, container, weather) {
  const host = document.createElement("div");
  host.className = "chart-host";
  panel.appendChild(host);

  const width = Math.max(680, host.clientWidth || container.clientWidth || 900);
  const height = 200;
  const svg = el("svg", { viewBox: `0 0 ${width} ${height}`, width, height });
  host.appendChild(svg);
  const plot = { x0: WM.left, x1: width - WM.right, y0: WM.top, y1: height - WM.bottom };

  const t0 = weather[0].t ?? 0;
  const times = weather.map((w) => ((w.t ?? 0) - t0) / 60);
  const tMax = times[times.length - 1] || 1;
  const x = linScale(0, tMax, plot.x0, plot.x1);

  const temps = weather.flatMap((w) => [w.air, w.trk]).filter((v) => v != null);
  const vMin = Math.min(...temps), vMax = Math.max(...temps);
  const pad = (vMax - vMin) * 0.15 + 0.5;
  const y = linScale(vMin - pad, vMax + pad, plot.y1, plot.y0);

  // 降雨帯
  let rainStart = null;
  for (let i = 0; i <= weather.length; i++) {
    const raining = i < weather.length && weather[i].rain;
    if (raining && rainStart == null) rainStart = times[i];
    if (!raining && rainStart != null) {
      const end = times[Math.min(i, times.length - 1)];
      el("rect", {
        x: x(rainStart), y: plot.y0, width: Math.max(2, x(end) - x(rainStart)), height: plot.y1 - plot.y0,
        fill: "rgba(77,159,255,0.12)",
      }, svg);
      rainStart = null;
    }
  }

  const gridG = el("g", {}, svg);
  gridY(gridG, y, niceTicks(vMin - pad, vMax + pad, 5), plot.x0, plot.x1, (v) => `${Math.round(v)}°C`);
  for (const t of niceTicks(0, tMax, 7)) {
    el("text", { class: "axis-label", x: x(t), y: plot.y1 + 17, "text-anchor": "middle", text: `${Math.round(t)}分` }, gridG);
  }

  const seriesDef = [
    { key: "trk", label: "路面温度", color: "#d95926" },
    { key: "air", label: "気温", color: "#3987e5" },
  ];
  for (const s of seriesDef) {
    let d = "";
    for (let i = 0; i < weather.length; i++) {
      const v = weather[i][s.key];
      if (v == null) continue;
      d += (d ? "L" : "M") + `${x(times[i]).toFixed(1)},${y(v).toFixed(1)}`;
    }
    el("path", { d, stroke: s.color, "stroke-width": 2, fill: "none", "stroke-linejoin": "round" }, svg);
    // 直接ラベル（線の右端）
    const lastVal = [...weather].reverse().find((w) => w[s.key] != null)?.[s.key];
    if (lastVal != null) {
      el("text", {
        class: "axis-label", x: plot.x1 + 8, y: y(lastVal) + 3.5, "font-weight": 600, text: s.label,
      }, svg);
    }
  }

  attachCrosshair(svg, plot, {
    snap(px) {
      const t = x.invert(px);
      let best = 0, bestD = Infinity;
      for (let i = 0; i < times.length; i++) {
        const dd = Math.abs(times[i] - t);
        if (dd < bestD) { bestD = dd; best = i; }
      }
      return { px: x(times[best]), i: best };
    },
    onMove(snapped, clientX, clientY) {
      const w = weather[snapped.i];
      tooltip.showRows(clientX, clientY, {
        title: `開始から ${Math.round(times[snapped.i])} 分`,
        rows: [
          { color: "#d95926", label: "路面温度", value: w.trk != null ? `${w.trk}°C` : "—" },
          { color: "#3987e5", label: "気温", value: w.air != null ? `${w.air}°C` : "—" },
          { label: "湿度", value: w.hum != null ? `${w.hum}%` : "—" },
          { label: "風速", value: w.ws != null ? `${w.ws} m/s` : "—" },
          { label: "降雨", value: w.rain ? "あり" : "なし" },
        ],
      });
    },
  });
}
