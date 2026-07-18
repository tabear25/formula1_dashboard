// アプリ全体の状態ストア（軽量 pub/sub）

const listeners = new Map(); // event -> Set<fn>

export const state = {
  sessionKey: null,      // {year, round, code}
  bundle: null,          // /api/session の応答
  derived: null,         // derive.js の派生データ
  focus: new Set(),      // 選択中ドライバー略称。空 = 全員
  tab: "lapchart",
};

export function on(event, fn) {
  if (!listeners.has(event)) listeners.set(event, new Set());
  listeners.get(event).add(fn);
  return () => listeners.get(event).delete(fn);
}

export function emit(event, payload) {
  const set = listeners.get(event);
  if (!set) return;
  for (const fn of [...set]) {
    try { fn(payload); } catch (e) { console.error(`listener error for ${event}`, e); }
  }
}

export function setBundle(sessionKey, bundle, derived) {
  state.sessionKey = sessionKey;
  state.bundle = bundle;
  state.derived = derived;
  state.focus = new Set();
  emit("bundle", bundle);
}

export function toggleFocus(abbr) {
  if (state.focus.has(abbr)) state.focus.delete(abbr);
  else state.focus.add(abbr);
  emit("focus", state.focus);
}

export function clearFocus() {
  state.focus.clear();
  emit("focus", state.focus);
}

export function setTab(tab) {
  state.tab = tab;
  emit("tab", tab);
}

// 表示対象ドライバーの決定則:
//   focus が空 → 全員(またはデフォルト上位 n)、focus あり → その順序(リザルト順)
export function visibleDrivers(defaultTopN = null) {
  const drivers = state.bundle?.drivers ?? [];
  if (state.focus.size > 0) {
    return drivers.filter((d) => state.focus.has(d.abbr));
  }
  if (defaultTopN != null) return drivers.slice(0, defaultTopN);
  return drivers;
}
