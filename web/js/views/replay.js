// レースリプレイ: /api/replay の全車位置（共通0.5秒グリッド）をコース上で再生する。
//   - トラック上を全車がチームカラーのドットで走行（フォーカス車はラベル強調）
//   - 右側にタイミングタワー（周回・ギャップ・タイヤをラップデータから補間）
//   - シークバーに SC/VSC/赤旗帯と自動検出モーメント（オーバーテイク・ピット等）
//   - Space=再生/停止、←/→=±10秒（Shift=±60秒）
// 予選・プラクティスでも動作し、タワーは暫定ベストタイム順に切り替わる。

import { state, toggleFocus } from "../state.js";
import { api } from "../api.js";
import { el, clearNode } from "../svg.js";
import { fmtLapTime, fmtGap, compoundLetter } from "../format.js";
import { statusKind } from "../derive.js";

// セッションをまたいで持ち回るモジュール状態（タブ切替では消さない）
const R = {
  key: null,
  data: null,        // /api/replay 応答
  tm: null,          // /api/trackmap 応答
  error: null,
  loading: false,
  t: null,           // 現在のセッション時刻（秒）
  playing: false,
  speed: 10,
  labelAll: false,
  moments: null,
  bands: null,
  timing: null,
};

let keysInstalled = false;
let rafToken = 0;

export function renderReplay(container) {
  clearNode(container);
  const { bundle, sessionKey } = state;
  const keyStr = `${sessionKey.year}:${sessionKey.round}:${sessionKey.code}`;

  if (R.key !== keyStr) {
    Object.assign(R, {
      key: keyStr, data: null, tm: null, error: null, loading: false,
      t: null, playing: false, moments: null, bands: null, timing: null,
    });
  }

  const panel = document.createElement("div");
  panel.className = "panel";
  container.appendChild(panel);

  const head = document.createElement("div");
  head.className = "panel-head";
  head.innerHTML = `<div class="panel-title">レースリプレイ</div>
    <div class="panel-sub">全車の実位置データを再生。シークバーのマーカー＝検出イベント。Space＝再生/停止、←/→＝±10秒。</div>`;
  panel.appendChild(head);

  const host = document.createElement("div");
  host.className = "chart-host";
  panel.appendChild(host);

  if (R.error) {
    host.innerHTML = `<div class="empty-note">リプレイを表示できません。${R.error}</div>`;
    return;
  }
  if (!R.data || !R.tm) {
    const note = document.createElement("div");
    note.className = "empty-note";
    note.textContent = R.loading ? "位置データを読み込み中…（決勝で1〜2MB）" : "位置データを読み込み中…";
    host.appendChild(note);
    if (!R.loading) {
      R.loading = true;
      Promise.all([
        api.replay(sessionKey.year, sessionKey.round, sessionKey.code),
        api.trackmap(sessionKey.year, sessionKey.round, sessionKey.code),
      ]).then(([data, tm]) => {
        if (R.key !== keyStr) return;   // 取得中に別セッションへ切り替わった応答は捨てる
        R.loading = false;
        if (data.error) { R.error = data.error; }
        else if (!tm || tm.error) { R.error = tm?.error ?? "コース形状を取得できません"; }
        else {
          R.data = data;
          R.tm = tm;
          if (R.t == null) R.t = data.race_start != null ? data.race_start - 12 : data.t0;
        }
        if (container.isConnected && state.tab === "replay") renderReplay(container);
      }).catch((err) => {
        if (R.key !== keyStr) return;
        R.loading = false;
        R.error = err.message;
        if (container.isConnected && state.tab === "replay") renderReplay(container);
      });
    }
    return;
  }

  // 派生データ（バンドル単位で1回だけ計算）
  if (!R.timing) R.timing = buildTiming(bundle);
  if (!R.bands) R.bands = buildStatusBands(bundle, R.data);
  if (!R.moments) R.moments = detectMoments(bundle, state.derived);

  buildUI(host, container, bundle);
  installKeys();
}

// ---------------------------------------------------------------- UI 構築

function buildUI(host, container, bundle) {
  const data = R.data, tm = R.tm;
  const derived = state.derived;

  // ---- レイアウト ----
  const layout = document.createElement("div");
  layout.className = "replay-layout";
  host.appendChild(layout);

  const mapWrap = document.createElement("div");
  mapWrap.className = "replay-map";
  layout.appendChild(mapWrap);

  const side = document.createElement("div");
  side.className = "replay-side";
  layout.appendChild(side);

  const towerEl = document.createElement("div");
  towerEl.className = "replay-tower";
  side.appendChild(towerEl);

  const logEl = document.createElement("div");
  logEl.className = "replay-log";
  side.appendChild(logEl);

  // ---- トラック SVG ----
  const width = Math.max(560, (mapWrap.clientWidth || container.clientWidth - 280 || 800));
  const height = 520;
  const pad = 46;
  const xs = tm.x, ys = tm.y;
  const minX = Math.min(...xs), maxX = Math.max(...xs);
  const minY = Math.min(...ys), maxY = Math.max(...ys);
  const k = Math.min((width - pad * 2) / (maxX - minX || 1), (height - pad * 2) / (maxY - minY || 1));
  const ox = (width - (maxX - minX) * k) / 2;
  const oy = (height - (maxY - minY) * k) / 2;
  const px = (x) => ox + (x - minX) * k;
  const py = (y) => oy + (maxY - y) * k;

  const svg = el("svg", { viewBox: `0 0 ${width} ${height}`, width, height });
  mapWrap.appendChild(svg);

  let outline = "";
  for (let i = 0; i < xs.length; i++) outline += (i ? "L" : "M") + `${px(xs[i]).toFixed(1)},${py(ys[i]).toFixed(1)}`;
  outline += "Z";
  el("path", { d: outline, stroke: "#060810", "stroke-width": 11, fill: "none", "stroke-linejoin": "round", "stroke-linecap": "round" }, svg);
  const trackPath = el("path", { d: outline, stroke: "var(--surface-3)", "stroke-width": 6.5, fill: "none", "stroke-linejoin": "round", "stroke-linecap": "round" }, svg);

  // スタートライン
  if (xs.length > 2) {
    const dx = px(xs[1]) - px(xs[0]);
    const dy = py(ys[1]) - py(ys[0]);
    const len = Math.hypot(dx, dy) || 1;
    el("line", {
      x1: px(xs[0]) + (dy / len) * 8, y1: py(ys[0]) - (dx / len) * 8,
      x2: px(xs[0]) - (dy / len) * 8, y2: py(ys[0]) + (dx / len) * 8,
      stroke: "var(--ink)", "stroke-width": 3,
    }, svg);
  }

  // 旗バッジ（SVG右上）
  const flagBadge = el("g", { visibility: "hidden" }, svg);
  const flagRect = el("rect", { x: width - 168, y: 14, width: 150, height: 30, rx: 6, fill: "var(--warn)" }, flagBadge);
  const flagText = el("text", {
    x: width - 93, y: 34, "text-anchor": "middle",
    "font-weight": 800, "font-size": 14, fill: "#0b0d12", text: "SAFETY CAR",
  }, flagBadge);

  // ---- 車ドット ----
  const carEls = new Map();
  const carsG = el("g", {}, svg);
  const carsSorted = [...data.cars].sort((a, b) => {
    const pa = derived.driverMap.get(a.abbr)?.pos ?? 99;
    const pb = derived.driverMap.get(b.abbr)?.pos ?? 99;
    return pb - pa;   // 上位を後に描いて前面へ
  });
  for (const car of carsSorted) {
    const d = derived.driverMap.get(car.abbr);
    const g = el("g", { visibility: "hidden", cursor: "pointer" }, carsG);
    el("circle", { r: 6, fill: d?.color ?? "#8a8f9c", stroke: "#0b0d12", "stroke-width": 1.6 }, g);
    if (d?.dash) {
      el("circle", { r: 2.1, fill: "#0b0d12", "pointer-events": "none" }, g);
    }
    const label = el("text", {
      class: "replay-car-label", x: 9, y: 4, text: car.abbr,
    }, g);
    g.addEventListener("click", () => toggleFocus(car.abbr));
    g.addEventListener("pointerenter", () => { label.setAttribute("visibility", "visible"); });
    g.addEventListener("pointerleave", () => { syncLabels(); });
    carEls.set(car.abbr, { g, label, car });
  }

  function syncLabels() {
    const hasFocus = state.focus.size > 0;
    for (const { label, car } of carEls.values()) {
      const show = R.labelAll || (hasFocus && state.focus.has(car.abbr));
      label.setAttribute("visibility", show ? "visible" : "hidden");
    }
  }
  syncLabels();

  // ---- コントロール行 ----
  const controls = document.createElement("div");
  controls.className = "replay-controls";
  host.appendChild(controls);

  const btnPlay = document.createElement("button");
  btnPlay.className = "replay-play";
  btnPlay.textContent = R.playing ? "⏸ 停止" : "▶ 再生";
  btnPlay.addEventListener("click", () => { setPlaying(!R.playing); });
  controls.appendChild(btnPlay);

  const btnStart = document.createElement("button");
  btnStart.className = "toggle-btn";
  btnStart.textContent = "スタートへ";
  btnStart.addEventListener("click", () => {
    seekTo(data.race_start != null ? data.race_start - 12 : data.t0);
  });
  controls.appendChild(btnStart);

  const speedWrap = document.createElement("span");
  speedWrap.className = "replay-speeds";
  for (const sp of [1, 5, 10, 30, 60]) {
    const b = document.createElement("button");
    b.className = `toggle-btn${R.speed === sp ? " on" : ""}`;
    b.textContent = `×${sp}`;
    b.addEventListener("click", () => {
      R.speed = sp;
      for (const c of speedWrap.children) c.classList.toggle("on", c === b);
    });
    speedWrap.appendChild(b);
  }
  controls.appendChild(speedWrap);

  const btnLabels = document.createElement("button");
  btnLabels.className = `toggle-btn${R.labelAll ? " on" : ""}`;
  btnLabels.textContent = "全車ラベル";
  btnLabels.addEventListener("click", () => {
    R.labelAll = !R.labelAll;
    btnLabels.classList.toggle("on", R.labelAll);
    syncLabels();
  });
  controls.appendChild(btnLabels);

  const timeLabel = document.createElement("span");
  timeLabel.className = "replay-time";
  controls.appendChild(timeLabel);

  // ---- シークバー ----
  const seek = document.createElement("div");
  seek.className = "replay-seek";
  host.appendChild(seek);

  const t0 = data.t0, tEnd = data.t0 + (data.n - 1) * data.dt;
  const frac = (t) => Math.max(0, Math.min(1, (t - t0) / (tEnd - t0)));

  for (const band of R.bands) {
    const div = document.createElement("div");
    div.className = "replay-seek-band";
    div.style.left = `${frac(band.from) * 100}%`;
    div.style.width = `${Math.max(0.15, (frac(band.to) - frac(band.from)) * 100)}%`;
    div.style.background = band.kind === "RED" ? "var(--red-band)"
      : band.kind === "VSC" ? "var(--vsc-band)" : "var(--sc-band)";
    seek.appendChild(div);
  }
  if (data.race_start != null) {
    const mark = document.createElement("div");
    mark.className = "replay-seek-start";
    mark.style.left = `${frac(data.race_start) * 100}%`;
    mark.title = "レーススタート";
    seek.appendChild(mark);
  }
  const fill = document.createElement("div");
  fill.className = "replay-seek-fill";
  seek.appendChild(fill);
  const knob = document.createElement("div");
  knob.className = "replay-seek-knob";
  seek.appendChild(knob);

  // モーメントマーカー
  for (const m of R.moments) {
    if (m.t == null || m.t < t0 || m.t > tEnd) continue;
    const dot = document.createElement("button");
    dot.className = `replay-moment kind-${m.kind}`;
    dot.style.left = `${frac(m.t) * 100}%`;
    dot.title = m.text;
    dot.addEventListener("click", (evt) => {
      evt.stopPropagation();
      seekTo(Math.max(t0, m.t - 6));
    });
    seek.appendChild(dot);
  }

  let scrubbing = false;
  const seekFromEvent = (evt) => {
    const rect = seek.getBoundingClientRect();
    const f = Math.max(0, Math.min(1, (evt.clientX - rect.left) / rect.width));
    seekTo(t0 + f * (tEnd - t0));
  };
  seek.addEventListener("pointerdown", (evt) => {
    // モーメントマーカー上ではスクラブを開始しない（マーカー自身の click に任せる）
    if (evt.target.closest(".replay-moment")) return;
    scrubbing = true;
    seek.setPointerCapture(evt.pointerId);
    seekFromEvent(evt);
  });
  seek.addEventListener("pointermove", (evt) => { if (scrubbing) seekFromEvent(evt); });
  seek.addEventListener("pointerup", () => { scrubbing = false; });

  // ---- ティッカー ----
  const ticker = document.createElement("div");
  ticker.className = "replay-ticker";
  host.appendChild(ticker);

  // ---- フレーム更新 ----
  if (R.t == null) R.t = data.race_start != null ? data.race_start - 12 : t0;

  const rcMsgs = (bundle.race_control ?? []).filter((m) => m.t != null);
  const statusEntries = (bundle.track_status ?? []).filter((s) => s.t != null);
  let lastTowerAt = 0;
  let lastTickerKey = null;

  function setPlaying(playing) {
    R.playing = playing;
    btnPlay.textContent = playing ? "⏸ 停止" : "▶ 再生";
    if (playing && R.t >= tEnd - 0.6) R.t = t0;
  }

  function seekTo(t) {
    R.t = Math.max(t0, Math.min(tEnd, t));
    lastTowerAt = 0;
    drawFrame(true);
  }

  function currentStatusKind(t) {
    let kind = null;
    for (const s of statusEntries) {
      if (s.t > t) break;
      kind = statusKind(s.s);
    }
    return kind;
  }

  function drawFrame(force) {
    const t = R.t;
    // 車位置
    const idxF = (t - t0) / data.dt;
    for (const { g, car } of carEls.values()) {
      if (idxF < car.i0 || idxF > car.i1) {
        g.setAttribute("visibility", "hidden");
        continue;
      }
      const local = idxF - car.i0;
      const j = Math.min(car.x.length - 2, Math.floor(local));
      const f = Math.max(0, Math.min(1, local - j));
      const cx = car.x[j] + (car.x[j + 1] - car.x[j]) * f;
      const cy = car.y[j] + (car.y[j + 1] - car.y[j]) * f;
      g.setAttribute("visibility", "visible");
      g.setAttribute("transform", `translate(${px(cx).toFixed(1)},${py(cy).toFixed(1)})`);
      const hasFocus = state.focus.size > 0;
      g.setAttribute("opacity", hasFocus && !state.focus.has(car.abbr) ? 0.4 : 1);
    }

    // 旗表示
    const kind = currentStatusKind(t);
    if (kind === "SC" || kind === "VSC" || kind === "RED") {
      flagBadge.setAttribute("visibility", "visible");
      const isRed = kind === "RED";
      flagRect.setAttribute("fill", isRed ? "var(--bad)" : "var(--warn)");
      flagText.textContent = kind === "SC" ? "SAFETY CAR" : kind === "VSC" ? "VIRTUAL SC" : "RED FLAG";
      flagText.setAttribute("fill", isRed ? "#fff" : "#0b0d12");
      trackPath.setAttribute("stroke", isRed ? "rgba(229,72,77,0.4)" : "rgba(243,192,75,0.35)");
    } else if (kind === "YEL") {
      flagBadge.setAttribute("visibility", "visible");
      flagRect.setAttribute("fill", "var(--warn)");
      flagText.textContent = "YELLOW";
      flagText.setAttribute("fill", "#0b0d12");
      trackPath.setAttribute("stroke", "var(--surface-3)");
    } else {
      flagBadge.setAttribute("visibility", "hidden");
      trackPath.setAttribute("stroke", "var(--surface-3)");
    }

    // シークバー・時刻
    const f = frac(t) * 100;
    fill.style.width = `${f}%`;
    knob.style.left = `${f}%`;
    const timing = R.timing.at(t);
    const rel = data.race_start != null ? t - data.race_start : t - t0;
    const sign = rel < 0 ? "-" : "";
    const a = Math.abs(rel);
    const clock = `${sign}${Math.floor(a / 3600)}:${String(Math.floor((a % 3600) / 60)).padStart(2, "0")}:${String(Math.floor(a % 60)).padStart(2, "0")}`;
    timeLabel.textContent = (timing.leaderLap != null
      ? `LAP ${Math.min(timing.leaderLap, state.derived.totalLaps)}/${state.derived.totalLaps}　` : "") + clock;

    // タワー（再生中のみ250msごと。停止中の再構築はクリック取りこぼしの原因になる）
    const now = performance.now();
    if (force || (R.playing && now - lastTowerAt > 250)) {
      lastTowerAt = now;
      renderTower(towerEl, timing, bundle);
      renderLog(logEl, t);
    }

    // ティッカー（直近8秒のレースコントロール）
    let msg = null;
    for (const m of rcMsgs) {
      if (m.t > t) break;
      if (t - m.t < 8) msg = m;
    }
    const key = msg ? `${msg.t}:${msg.msg}` : null;
    if (key !== lastTickerKey) {
      lastTickerKey = key;
      ticker.textContent = msg ? `📢 ${msg.lap != null ? `[L${msg.lap}] ` : ""}${msg.msg}` : "";
      ticker.classList.toggle("show", !!msg);
    }
  }

  // rAF ループ（このビューのDOMが生きている間だけ回す）
  const token = ++rafToken;
  let lastTs = null;
  function loop(ts) {
    if (token !== rafToken || !svg.isConnected) return;
    if (lastTs != null && R.playing) {
      // タブ非表示中は rAF が止まるため、復帰フレームの巨大なデルタはクランプする
      const dtMs = Math.min(ts - lastTs, 250);
      R.t = Math.min(tEnd, R.t + (dtMs / 1000) * R.speed);
      if (R.t >= tEnd) setPlaying(false);
    }
    lastTs = ts;
    drawFrame(false);
    requestAnimationFrame(loop);
  }
  requestAnimationFrame(loop);
  drawFrame(true);

  // ログクリックでシーク
  logEl.addEventListener("click", (evt) => {
    const row = evt.target.closest("[data-t]");
    if (!row) return;
    seekTo(Math.max(t0, Number(row.dataset.t) - 6));
  });

  // タワー行クリックでドライバー選択（委譲: 行が再構築されても効く）
  towerEl.addEventListener("click", (evt) => {
    const row = evt.target.closest(".replay-tower-row");
    if (row?.dataset.abbr) toggleFocus(row.dataset.abbr);
  });

  // モジュールから seek/play を触れるように保持（キーボード用）
  R._seekBy = (dt) => seekTo(R.t + dt);
  R._togglePlay = () => setPlaying(!R.playing);
}

// ---------------------------------------------------------------- タワー

function renderTower(towerEl, timing, bundle) {
  const { derived } = state;
  const rows = timing.rows;
  clearNode(towerEl);
  const title = document.createElement("div");
  title.className = "replay-tower-head";
  title.textContent = timing.mode === "race" ? "タイミングタワー" : "暫定ベスト順";
  towerEl.appendChild(title);
  const hasFocus = state.focus.size > 0;
  rows.forEach((r, i) => {
    const d = derived.driverMap.get(r.abbr);
    const row = document.createElement("div");
    row.className = "replay-tower-row";
    row.dataset.abbr = r.abbr;   // クリックは towerEl 側の委譲リスナーで処理（行の再構築に耐える）
    if (r.out) row.classList.add("out");
    if (hasFocus && !state.focus.has(r.abbr)) row.style.opacity = "0.4";

    const pos = document.createElement("span");
    pos.className = "pos";
    pos.textContent = String(i + 1);
    row.appendChild(pos);

    const key = document.createElement("span");
    key.className = "key";
    key.style.background = d?.color ?? "#8a8f9c";
    row.appendChild(key);

    const abbr = document.createElement("span");
    abbr.className = "abbr";
    abbr.textContent = r.abbr;
    row.appendChild(abbr);

    const gap = document.createElement("span");
    gap.className = "gap";
    gap.textContent = r.out ? "OUT" : r.gapText;
    row.appendChild(gap);

    if (r.cmp) {
      const tyre = document.createElement("span");
      tyre.className = "tyre";
      tyre.style.background = bundle.compound_colors[r.cmp] ?? "#8a8f9c";
      tyre.textContent = compoundLetter(r.cmp);
      row.appendChild(tyre);
      if (r.life != null) {
        const life = document.createElement("span");
        life.className = "life";
        life.textContent = String(r.life);
        row.appendChild(life);
      }
    }
    if (r.pit) {
      const pit = document.createElement("span");
      pit.className = "pitflag";
      pit.textContent = "PIT";
      row.appendChild(pit);
    }
    towerEl.appendChild(row);
  });
}

function renderLog(logEl, t) {
  // 現在時刻までの直近イベントを新しい順に表示
  const upto = R.moments.filter((m) => m.t != null && m.t <= t);
  const shown = upto.slice(-30).reverse();
  const key = shown.length ? `${shown.length}:${shown[0].t}` : "0";
  if (logEl.dataset.key === key) return;
  logEl.dataset.key = key;
  clearNode(logEl);
  const title = document.createElement("div");
  title.className = "replay-tower-head";
  title.textContent = "イベントログ";
  logEl.appendChild(title);
  if (shown.length === 0) {
    const div = document.createElement("div");
    div.className = "replay-log-row";
    div.textContent = "（まだイベントはありません）";
    logEl.appendChild(div);
    return;
  }
  for (const m of shown) {
    const div = document.createElement("div");
    div.className = `replay-log-row kind-${m.kind}`;
    div.dataset.t = String(m.t);
    div.textContent = m.text;
    logEl.appendChild(div);
  }
}

// ---------------------------------------------------------------- 時刻→順位

// laps の st/et から時刻 T の順位列を組み立てるインデックス
function buildTiming(bundle) {
  const { derived } = state;
  const isRace = derived.isRace;
  const perDriver = [];
  for (const d of bundle.drivers) {
    const laps = derived.lapsByDriver.get(d.abbr) ?? [];
    const valid = laps.filter((r) => r.st != null && r.et != null);
    perDriver.push({ abbr: d.abbr, laps: valid, allLaps: laps, grid: d.grid });
  }

  const etOf = (pd, lap) => {
    const rec = pd.laps.find((r) => r.lap === lap);
    return rec ? rec.et : null;
  };

  function at(t) {
    if (!isRace) return atSessionBest(t);
    const standings = [];
    let leaderLap = null;
    for (const pd of perDriver) {
      if (pd.laps.length === 0) continue;
      let completed = 0;
      let current = null;
      for (const rec of pd.laps) {
        if (rec.et <= t) completed = rec.lap;
        else if (rec.st <= t) { current = rec; break; }
      }
      const started = pd.laps[0].st <= t;
      const lastRec = pd.laps[pd.laps.length - 1];
      const out = t > lastRec.et + 45 && !(derived.finished.get(pd.abbr) ?? false);
      // スタート前（completed=0）は最終ラップでなくスタートスティントのタイヤを見せる
      const rec = current ?? pd.laps.find((r) => r.lap === completed)
        ?? (completed === 0 ? pd.laps[0] : lastRec);
      standings.push({
        abbr: pd.abbr, started, out, completed,
        hasCurrent: !!current,
        // 現在の周に入った時刻。周回数が同じなら先に入った方が前（ライン通過ベース）
        curSt: current ? current.st : (lastRec.et ?? Infinity),
        grid: pd.grid,
        cmp: rec?.cmp, life: rec?.life,
        pit: !!(current && current.et > current.st
          && ((current.pit_in && (t - current.st) / (current.et - current.st) > 0.75)
            || (current.pit_out && (t - current.st) / (current.et - current.st) < 0.3))),
      });
    }
    // ライン通過ベースの安定ソート: 周回数 → 現在周への到達時刻。
    // （周回内の時間割合は、ピットで現在ラップが長い車の順位を歪めるため使わない）
    standings.sort((a, b) => {
      if (a.out !== b.out) return a.out ? 1 : -1;
      if (a.started !== b.started) return a.started ? -1 : 1;
      if (!a.started) return (a.grid ?? 99) - (b.grid ?? 99);
      if (b.completed !== a.completed) return b.completed - a.completed;
      return a.curSt - b.curSt;
    });
    const leader = standings.find((s) => !s.out && s.started);
    if (leader) leaderLap = Math.max(1, leader.completed + (leader.hasCurrent ? 1 : 0));
    const leaderPd = leader ? perDriver.find((p) => p.abbr === leader.abbr) : null;
    const rows = standings.map((s, i) => {
      let gapText = "—";
      if (s.out) gapText = "OUT";
      else if (!s.started) gapText = "GRID";
      else if (i === 0) gapText = "Leader";
      else if (leader && s.completed >= 1) {
        const lapDiff = leader.completed - s.completed;
        if (lapDiff >= 1) {
          gapText = `+${lapDiff} LAP`;
        } else {
          const myEt = etOf(perDriver.find((p) => p.abbr === s.abbr), s.completed);
          const leaderEt = leaderPd ? etOf(leaderPd, s.completed) : null;
          gapText = myEt != null && leaderEt != null ? fmtGap(myEt - leaderEt, 1) : "—";
        }
      }
      return { ...s, gapText };
    });
    return { mode: "race", rows, leaderLap };
  }

  function atSessionBest(t) {
    const rows = [];
    for (const pd of perDriver) {
      let best = null;
      let lastRec = null;
      for (const rec of pd.allLaps) {
        if (rec.et == null || rec.et > t) continue;
        lastRec = rec;
        if (rec.t != null && !rec.del && (best == null || rec.t < best)) best = rec.t;
      }
      if (lastRec == null) continue;
      rows.push({ abbr: pd.abbr, best, cmp: lastRec.cmp, life: lastRec.life, pit: false, out: false });
    }
    rows.sort((a, b) => {
      if (a.best == null) return 1;
      if (b.best == null) return -1;
      return a.best - b.best;
    });
    const top = rows[0]?.best ?? null;
    return {
      mode: "session",
      leaderLap: null,
      rows: rows.map((r, i) => ({
        ...r,
        gapText: r.best == null ? "—" : (i === 0 ? fmtLapTime(r.best) : fmtGap(r.best - top)),
      })),
    };
  }

  return { at };
}

// ---------------------------------------------------------------- 帯とモーメント

// track_status（時刻ベース）から SC/VSC/赤旗の時間帯を作る
function buildStatusBands(bundle, data) {
  const entries = (bundle.track_status ?? []).filter((s) => s.t != null);
  const tEnd = data.t0 + (data.n - 1) * data.dt;
  const bands = [];
  let current = null;
  for (const s of entries) {
    const kind = statusKind(s.s);
    const bandKind = kind === "YEL" ? null : kind;
    if (current && bandKind !== current.kind) {
      current.to = s.t;
      current = null;
    }
    if (bandKind && !current) {
      current = { from: s.t, to: tEnd, kind: bandKind };
      bands.push(current);
    }
  }
  return bands;
}

// バンドルから注目イベントを検出してシークバー・ログに出す
function detectMoments(bundle, derived) {
  const moments = [];
  const isRace = derived.isRace;
  const etOf = (abbr, lap) => derived.lapIndex.get(abbr)?.get(lap)?.et ?? null;

  // 旗イベント（時刻ベース）
  let prevKind = null;
  for (const s of bundle.track_status ?? []) {
    if (s.t == null) continue;
    const kind = statusKind(s.s);
    if (kind !== prevKind) {
      if (kind === "SC") moments.push({ t: s.t, kind: "flag", text: "セーフティカー出動" });
      else if (kind === "VSC") moments.push({ t: s.t, kind: "flag", text: "バーチャルセーフティカー" });
      else if (kind === "RED") moments.push({ t: s.t, kind: "red", text: "赤旗" });
      else if (prevKind === "SC" || prevKind === "VSC" || prevKind === "RED") {
        moments.push({ t: s.t, kind: "green", text: "リスタート（グリーン）" });
      }
      prevKind = kind;
    }
  }

  if (isRace) {
    // オーバーテイク（周回境界の順位入替。ピット・SC絡みは除外）
    for (let lap = 2; lap <= derived.maxLap; lap++) {
      const cur = derived.towerPerLap.get(lap) ?? [];
      const prev = derived.towerPerLap.get(lap - 1) ?? [];
      const prevPos = new Map(prev.map((r) => [r.abbr, r.pos]));
      if (derived.statusPerLap.get(lap) || derived.statusPerLap.get(lap - 1)) continue;
      for (const r of cur) {
        const p0 = prevPos.get(r.abbr);
        if (p0 == null || r.pos >= p0) continue;
        const idx = derived.lapIndex.get(r.abbr);
        const rec = idx?.get(lap), recPrev = idx?.get(lap - 1);
        if (rec?.pit_in || rec?.pit_out || recPrev?.pit_in || recPrev?.pit_out) continue;
        // 実際にコース上で抜いた相手を特定する: 前の周では自分より前にいて、
        // この周も走行中（ピット非関与）なのに自分より後ろになった車。
        // 該当車がいなければ、第三者のリタイア・ピットによる繰り上がりなので記録しない。
        const passed = cur
          .filter((o) => {
            const op = prevPos.get(o.abbr);
            if (op == null || op >= p0 || o.pos <= r.pos) return false;
            const oIdx = derived.lapIndex.get(o.abbr);
            return !(oIdx?.get(lap)?.pit_in || oIdx?.get(lap)?.pit_out || oIdx?.get(lap - 1)?.pit_in);
          })
          .sort((a, b) => a.pos - b.pos)[0];
        if (!passed) continue;
        moments.push({
          t: etOf(r.abbr, lap), kind: "overtake",
          text: `L${lap} ${r.abbr} が P${p0}→P${r.pos}（${passed.abbr} を攻略）`,
        });
      }
    }

    // ピットストップ
    for (const d of bundle.drivers) {
      for (const stop of derived.pitStops.get(d.abbr) ?? []) {
        const t = etOf(d.abbr, stop.lap);
        moments.push({
          t, kind: "pit",
          text: `L${stop.lap} ${d.abbr} ピットイン${stop.nextCmp ? `（→${compoundLetter(stop.nextCmp)}）` : ""}`,
        });
      }
    }

    // ファステストラップ更新
    const flRecs = bundle.laps
      .filter((r) => r.t != null && !r.del && r.et != null && r.lap > 1)
      .sort((a, b) => a.et - b.et);
    let best = Infinity;
    for (const r of flRecs) {
      if (r.t < best) {
        best = r.t;
        moments.push({ t: r.et, kind: "fastest", text: `L${r.lap} ${r.drv} ファステスト ${fmtLapTime(r.t)}` });
      }
    }

    // リタイア
    for (const d of bundle.drivers) {
      if (derived.finished.get(d.abbr)) continue;
      const laps = derived.lapsByDriver.get(d.abbr) ?? [];
      const last = [...laps].reverse().find((r) => r.et != null);
      if (last) moments.push({ t: last.et + 5, kind: "retire", text: `${d.abbr} リタイア（L${last.lap}）` });
    }
  }

  // 降雨の開始・終了
  let raining = null;
  for (const w of bundle.weather ?? []) {
    if (w.t == null) continue;
    if (raining == null) { raining = w.rain; continue; }
    if (w.rain !== raining) {
      moments.push({ t: w.t, kind: "rain", text: w.rain ? "降雨開始" : "雨が上がる" });
      raining = w.rain;
    }
  }

  moments.sort((a, b) => (a.t ?? 0) - (b.t ?? 0));
  return moments;
}

// ---------------------------------------------------------------- キーボード

function installKeys() {
  if (keysInstalled) return;
  keysInstalled = true;
  document.addEventListener("keydown", (evt) => {
    if (state.tab !== "replay" || !R.data) return;
    const tag = evt.target?.tagName;
    if (tag === "INPUT" || tag === "SELECT" || tag === "TEXTAREA") return;
    if (evt.key === " ") {
      R._togglePlay?.();
      evt.preventDefault();
    } else if (evt.key === "ArrowLeft") {
      R._seekBy?.(evt.shiftKey ? -60 : -10);
      evt.preventDefault();
    } else if (evt.key === "ArrowRight") {
      R._seekBy?.(evt.shiftKey ? 60 : 10);
      evt.preventDefault();
    }
  });
}
