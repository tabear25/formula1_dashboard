// PITWALL アプリ本体: セッション選択 → ロード → タブ描画のオーケストレーション

import { api } from "./api.js";
import { state, on, setBundle, setTab, toggleFocus, clearFocus } from "./state.js";
import { derive } from "./derive.js";
import { fmtLapTime, fmtRaceTime, fmtGap } from "./format.js";
import { el } from "./svg.js";
import { renderLapChart } from "./views/lapchart.js";
import { renderGaps } from "./views/gaps.js";
import { renderPace } from "./views/pace.js";
import { renderViolin } from "./views/violin.js";
import { renderStrategy } from "./views/strategy.js";
import { renderTelemetry } from "./views/telemetry.js";
import { renderTrack } from "./views/track.js";
import { renderResults } from "./views/results.js";
import { renderControl } from "./views/control.js";

const $ = (id) => document.getElementById(id);
const selYear = $("sel-year");
const selEvent = $("sel-event");
const selSession = $("sel-session");
const btnLoad = $("btn-load");
const loadStatus = $("load-status");
const sessionTitle = $("session-title");
const driverStrip = $("driver-strip");
const statRow = $("stat-row");
const tabNav = $("tab-nav");
const viewWrap = $("view-wrap");

const SESSION_LABEL = {
  FP1: "フリー走行1", FP2: "フリー走行2", FP3: "フリー走行3",
  Q: "予選", SQ: "スプリント予選", S: "スプリント", R: "決勝",
};

const TABS = [
  { id: "lapchart", label: "ラップチャート", raceOnly: true, render: renderLapChart },
  { id: "gaps", label: "ギャップ", raceOnly: true, render: renderGaps },
  { id: "pace", label: "ペース", raceOnly: false, render: renderPace },
  { id: "violin", label: "ラップ分布", raceOnly: false, render: renderViolin },
  { id: "strategy", label: "タイヤ戦略", raceOnly: false, render: renderStrategy },
  { id: "telemetry", label: "テレメトリ", raceOnly: false, render: renderTelemetry },
  { id: "track", label: "トラック", raceOnly: false, render: renderTrack },
  { id: "results", label: "リザルト", raceOnly: false, render: renderResults },
  { id: "control", label: "レースコントロール", raceOnly: false, render: renderControl },
];

let schedule = null;
let pollToken = 0;

// ------------------------------------------------------------- 起動フロー

async function boot() {
  try {
    const { years } = await api.years();
    for (const y of years) {
      const opt = document.createElement("option");
      opt.value = String(y);
      opt.textContent = `${y}年`;
      selYear.appendChild(opt);
    }
    const savedYear = localStorage.getItem("pitwall.year");
    if (savedYear && years.includes(Number(savedYear))) selYear.value = savedYear;
    await loadSchedule();
  } catch (err) {
    setStatus(`サーバに接続できません: ${err.message}`, "error");
  }
}

async function loadSchedule() {
  setStatus("スケジュール取得中…", "busy");
  selEvent.innerHTML = "";
  selSession.innerHTML = "";
  try {
    schedule = await api.schedule(Number(selYear.value));
  } catch (err) {
    setStatus(`スケジュール取得に失敗: ${err.message}`, "error");
    return;
  }
  setStatus("");
  const today = new Date().toISOString().slice(0, 10);
  let defaultIdx = 0;
  schedule.events.forEach((ev, i) => {
    const opt = document.createElement("option");
    opt.value = String(ev.round);
    opt.textContent = `R${ev.round} ${ev.name}${ev.date ? `（${ev.date.slice(5)}）` : ""}`;
    selEvent.appendChild(opt);
    if (ev.date && ev.date <= today) defaultIdx = i;
  });
  const savedRound = localStorage.getItem(`pitwall.round.${selYear.value}`);
  if (savedRound && schedule.events.some((e) => String(e.round) === savedRound)) {
    selEvent.value = savedRound;
  } else if (schedule.events[defaultIdx]) {
    selEvent.value = String(schedule.events[defaultIdx].round);
  }
  fillSessions();
}

function fillSessions() {
  selSession.innerHTML = "";
  const ev = currentEvent();
  if (!ev) return;
  for (const s of ev.sessions) {
    const opt = document.createElement("option");
    opt.value = s.code;
    opt.textContent = SESSION_LABEL[s.code] ?? s.name;
    selSession.appendChild(opt);
  }
  const saved = localStorage.getItem("pitwall.session");
  if (saved && ev.sessions.some((s) => s.code === saved)) selSession.value = saved;
  else if (ev.sessions.some((s) => s.code === "R")) selSession.value = "R";
}

function currentEvent() {
  return schedule?.events.find((e) => String(e.round) === selEvent.value) ?? null;
}

selYear.addEventListener("change", () => {
  localStorage.setItem("pitwall.year", selYear.value);
  loadSchedule();
});
selEvent.addEventListener("change", () => {
  localStorage.setItem(`pitwall.round.${selYear.value}`, selEvent.value);
  fillSessions();
});
selSession.addEventListener("change", () => {
  localStorage.setItem("pitwall.session", selSession.value);
});

// ------------------------------------------------------------- ロード

btnLoad.addEventListener("click", startLoad);

async function startLoad() {
  const ev = currentEvent();
  if (!ev) return;
  const year = Number(selYear.value);
  const round = Number(selEvent.value);
  const code = selSession.value;
  const token = ++pollToken;

  btnLoad.disabled = true;
  markStale(true);
  setStatus("読み込み開始…", "busy");
  try {
    await api.load(year, round, code);
  } catch (err) {
    setStatus(`読み込み開始に失敗: ${err.message}`, "error");
    btnLoad.disabled = false;
    return;
  }

  const started = Date.now();
  const poll = async () => {
    if (token !== pollToken) return; // 新しいロードが始まった
    let st;
    try {
      st = await api.status(year, round, code);
    } catch (err) {
      setStatus(`状態確認に失敗: ${err.message}`, "error");
      btnLoad.disabled = false;
      return;
    }
    if (st.state === "ready") {
      setStatus("データ変換中…", "busy");
      try {
        const bundle = await api.session(year, round, code);
        if (token !== pollToken) return;
        onBundle({ year, round, code }, bundle);
        setStatus("");
      } catch (err) {
        setStatus(`セッション取得に失敗: ${err.message}`, "error");
      }
      btnLoad.disabled = false;
      return;
    }
    if (st.state === "error") {
      setStatus(`読み込みエラー: ${st.error ?? "不明"}`, "error");
      btnLoad.disabled = false;
      markStale(false);
      return;
    }
    const secs = Math.round((Date.now() - started) / 1000);
    setStatus(`データ取得中… ${secs}s（初回は数分かかることがあります）`, "busy");
    setTimeout(poll, 1200);
  };
  poll();
}

function setStatus(message, kind = "") {
  loadStatus.textContent = "";
  if (kind === "busy") {
    const spin = document.createElement("span");
    spin.className = "spinner";
    loadStatus.appendChild(spin);
  }
  const span = document.createElement("span");
  span.textContent = message;
  if (kind === "error") span.style.color = "var(--bad)";
  loadStatus.appendChild(span);
}

function markStale(stale) {
  for (const panel of viewWrap.querySelectorAll(".panel")) {
    panel.classList.toggle("stale", stale);
  }
}

// ------------------------------------------------------------- バンドル反映

function onBundle(sessionKey, bundle) {
  const derived = derive(bundle);
  setBundle(sessionKey, bundle, derived);
}

on("bundle", () => {
  $("boot-hero")?.remove();
  renderSessionTitle();
  renderStrip();
  renderStats();
  renderTabs();
  const isRace = state.bundle.meta.type === "race";
  const currentTab = TABS.find((t) => t.id === state.tab);
  if (!currentTab || (currentTab.raceOnly && !isRace)) {
    state.tab = isRace ? "lapchart" : "pace";
  }
  renderActiveView();
});

on("focus", () => {
  updateStripSelection();
  renderActiveView();
});

on("tab", () => {
  renderTabs();
  renderActiveView();
});

function renderSessionTitle() {
  const m = state.bundle.meta;
  sessionTitle.innerHTML = "";
  const l1 = document.createElement("div");
  l1.className = "line1";
  l1.textContent = `${m.year} ${m.event_name} — ${SESSION_LABEL[m.code] ?? m.session_name}`;
  const l2 = document.createElement("div");
  l2.className = "line2";
  l2.textContent = `${m.location}, ${m.country}${m.total_laps ? `　全${m.total_laps}周` : ""}`;
  sessionTitle.appendChild(l1);
  sessionTitle.appendChild(l2);
}

function renderStrip() {
  driverStrip.hidden = false;
  driverStrip.innerHTML = "";
  for (const d of state.bundle.drivers) {
    const chip = document.createElement("button");
    chip.className = "driver-chip";
    chip.dataset.abbr = d.abbr;
    chip.dataset.dash = String(d.dash);
    chip.title = `${d.name ?? d.abbr}（${d.team}）`;
    const key = document.createElement("span");
    key.className = "key";
    key.style.borderTopColor = d.color;
    chip.appendChild(key);
    const pos = document.createElement("span");
    pos.className = "pos";
    pos.textContent = d.classified && /^\d+$/.test(d.classified) ? `P${d.classified}`
      : (d.pos != null ? `P${d.pos}` : "—");
    chip.appendChild(pos);
    chip.appendChild(document.createTextNode(d.abbr));
    chip.addEventListener("click", () => toggleFocus(d.abbr));
    driverStrip.appendChild(chip);
  }
  const clear = document.createElement("button");
  clear.className = "strip-clear";
  clear.textContent = "選択解除";
  clear.addEventListener("click", clearFocus);
  driverStrip.appendChild(clear);
  const note = document.createElement("span");
  note.className = "strip-note";
  note.textContent = "クリックで選択 — 全タブ連動";
  driverStrip.appendChild(note);
  updateStripSelection();
}

function updateStripSelection() {
  const hasFocus = state.focus.size > 0;
  for (const chip of driverStrip.querySelectorAll(".driver-chip")) {
    chip.classList.toggle("selected", state.focus.has(chip.dataset.abbr));
    chip.style.opacity = hasFocus && !state.focus.has(chip.dataset.abbr) ? "0.55" : "1";
  }
}

function renderStats() {
  const { bundle, derived } = state;
  statRow.hidden = false;
  statRow.innerHTML = "";
  const tiles = [];

  if (derived.isRace) {
    const winner = bundle.drivers[0];
    if (winner) {
      tiles.push({
        label: "優勝",
        value: winner.abbr,
        sub: winner.time_s != null ? fmtRaceTime(winner.time_s) : (winner.status ?? ""),
        color: winner.color,
      });
    }
    if (derived.fastestLap) {
      const d = derived.driverMap.get(derived.fastestLap.abbr);
      tiles.push({
        label: "ファステストラップ",
        value: fmtLapTime(derived.fastestLap.t),
        sub: `${derived.fastestLap.abbr} / L${derived.fastestLap.lap}`,
        color: d?.color, valueClass: "best-purple",
      });
    }
    const scBands = derived.bands.filter((b) => b.kind === "SC").length;
    const vscBands = derived.bands.filter((b) => b.kind === "VSC").length;
    const redBands = derived.bands.filter((b) => b.kind === "RED").length;
    tiles.push({
      label: "SC / VSC / 赤旗",
      value: `${scBands} / ${vscBands} / ${redBands}`,
      sub: derived.scLaps + derived.vscLaps > 0 ? `計${derived.scLaps + derived.vscLaps}周` : "クリーンレース",
    });
    tiles.push({
      label: "首位交代",
      value: `${derived.leadChanges}回`,
      sub: `全${derived.totalLaps}周`,
    });
  } else if (bundle.meta.type === "quali") {
    const pole = bundle.drivers[0];
    if (pole) {
      tiles.push({
        label: "ポールポジション", value: pole.abbr,
        sub: pole.q3 != null ? fmtLapTime(pole.q3) : "", color: pole.color,
      });
      const second = bundle.drivers[1];
      if (second?.q3 != null && pole.q3 != null) {
        tiles.push({ label: "2番手との差", value: fmtGap(second.q3 - pole.q3), sub: second.abbr });
      }
    }
  } else if (derived.fastestLap) {
    const d = derived.driverMap.get(derived.fastestLap.abbr);
    tiles.push({
      label: "ベストタイム", value: fmtLapTime(derived.fastestLap.t),
      sub: derived.fastestLap.abbr, color: d?.color,
    });
  }

  const weather = bundle.weather ?? [];
  if (weather.length > 0) {
    const airs = weather.map((w) => w.air).filter((v) => v != null);
    const trks = weather.map((w) => w.trk).filter((v) => v != null);
    const rained = weather.some((w) => w.rain);
    if (airs.length && trks.length) {
      tiles.push({
        label: "気温 / 路面",
        value: `${Math.round(airs.reduce((a, b) => a + b) / airs.length)}° / ${Math.round(trks.reduce((a, b) => a + b) / trks.length)}°`,
        sub: rained ? "雨あり" : "ドライ",
      });
    }
  }

  for (const t of tiles) {
    const tile = document.createElement("div");
    tile.className = "stat-tile";
    const label = document.createElement("div");
    label.className = "label";
    label.textContent = t.label;
    tile.appendChild(label);
    const value = document.createElement("div");
    value.className = "value";
    if (t.color) {
      const chipEl = document.createElement("span");
      chipEl.className = "chip";
      chipEl.style.background = t.color;
      value.appendChild(chipEl);
    }
    const main = document.createElement("span");
    main.textContent = t.value;
    if (t.valueClass) main.className = t.valueClass;
    value.appendChild(main);
    if (t.sub) {
      const sub = document.createElement("span");
      sub.className = "sub";
      sub.textContent = t.sub;
      value.appendChild(sub);
    }
    tile.appendChild(value);
    statRow.appendChild(tile);
  }

  addCircuitTile();
}

// ヘッダー統計行のミニサーキットマップ（データは /api/trackmap を再利用）
let miniMapCache = { key: null, data: null };

function addCircuitTile() {
  const { bundle, sessionKey } = state;
  const tile = document.createElement("div");
  tile.className = "stat-tile";
  const label = document.createElement("div");
  label.className = "label";
  label.textContent = "サーキット";
  tile.appendChild(label);
  const value = document.createElement("div");
  value.className = "value";
  const holder = document.createElement("span");
  holder.className = "sub";
  holder.textContent = "読み込み中…";
  value.appendChild(holder);
  tile.appendChild(value);
  statRow.appendChild(tile);

  const keyStr = `${sessionKey.year}:${sessionKey.round}:${sessionKey.code}`;
  const draw = (tm) => {
    if (!tile.isConnected) return;
    if (!tm || tm.error || !tm.x || tm.x.length < 3) { tile.remove(); return; }
    value.innerHTML = "";
    const w = 132, h = 52, padPx = 4;
    const minX = Math.min(...tm.x), maxX = Math.max(...tm.x);
    const minY = Math.min(...tm.y), maxY = Math.max(...tm.y);
    const k = Math.min((w - padPx * 2) / (maxX - minX || 1), (h - padPx * 2) / (maxY - minY || 1));
    const ox = (w - (maxX - minX) * k) / 2;
    const oy = (h - (maxY - minY) * k) / 2;
    const svg = el("svg", { viewBox: `0 0 ${w} ${h}`, width: w, height: h });
    let d = "";
    for (let i = 0; i < tm.x.length; i += 3) {
      d += (d ? "L" : "M") +
        `${(ox + (tm.x[i] - minX) * k).toFixed(1)},${(oy + (maxY - tm.y[i]) * k).toFixed(1)}`;
    }
    d += "Z";
    el("path", { d, stroke: "var(--ink-2)", "stroke-width": 2, fill: "none", "stroke-linejoin": "round", "stroke-linecap": "round" }, svg);
    value.appendChild(svg);
    const sub = document.createElement("span");
    sub.className = "sub";
    sub.textContent = bundle.meta.location ?? "";
    value.appendChild(sub);
  };

  if (miniMapCache.key === keyStr) { draw(miniMapCache.data); return; }
  api.trackmap(sessionKey.year, sessionKey.round, sessionKey.code)
    .then((tm) => { miniMapCache = { key: keyStr, data: tm }; draw(tm); })
    .catch(() => { if (tile.isConnected) tile.remove(); });
}

function renderTabs() {
  tabNav.hidden = false;
  tabNav.innerHTML = "";
  const isRace = state.bundle?.meta.type === "race";
  for (const tab of TABS) {
    if (tab.raceOnly && !isRace) continue;
    const btn = document.createElement("button");
    btn.className = `tab-btn${state.tab === tab.id ? " active" : ""}`;
    btn.textContent = tab.label;
    btn.addEventListener("click", () => setTab(tab.id));
    tabNav.appendChild(btn);
  }
}

function renderActiveView() {
  if (!state.bundle) return;
  const tab = TABS.find((t) => t.id === state.tab) ?? TABS[0];
  viewWrap.innerHTML = "";
  try {
    tab.render(viewWrap);
  } catch (err) {
    console.error(err);
    const div = document.createElement("div");
    div.className = "empty-note";
    div.textContent = `描画エラー: ${err.message}`;
    viewWrap.appendChild(div);
  }
}

// リサイズで再描画（デバウンス）
let resizeTimer = null;
new ResizeObserver(() => {
  if (!state.bundle) return;
  clearTimeout(resizeTimer);
  resizeTimer = setTimeout(renderActiveView, 180);
}).observe(viewWrap);

boot();
