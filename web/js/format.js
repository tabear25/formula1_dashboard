// 時間・数値の表示フォーマッタ

export function fmtLapTime(seconds) {
  if (seconds == null || !isFinite(seconds)) return "—";
  const sign = seconds < 0 ? "-" : "";
  const abs = Math.abs(seconds);
  const m = Math.floor(abs / 60);
  const s = abs - m * 60;
  const sStr = s.toFixed(3).padStart(6, "0");
  return `${sign}${m}:${sStr}`;
}

export function fmtRaceTime(seconds) {
  if (seconds == null || !isFinite(seconds)) return "—";
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds - h * 3600) / 60);
  const s = seconds - h * 3600 - m * 60;
  if (h > 0) return `${h}:${String(m).padStart(2, "0")}:${s.toFixed(3).padStart(6, "0")}`;
  return fmtLapTime(seconds);
}

export function fmtGap(seconds, digits = 3) {
  if (seconds == null || !isFinite(seconds)) return "—";
  if (Math.abs(seconds) < 0.0005) return "±0.000";
  const sign = seconds > 0 ? "+" : "-";
  return `${sign}${Math.abs(seconds).toFixed(digits)}`;
}

export function fmtSecs(seconds, digits = 1) {
  if (seconds == null || !isFinite(seconds)) return "—";
  return seconds.toFixed(digits);
}

// コンパウンド名 → 1文字表記
export function compoundLetter(name) {
  if (!name) return "?";
  const map = {
    SOFT: "S", MEDIUM: "M", HARD: "H",
    INTERMEDIATE: "I", WET: "W",
    HYPERSOFT: "HS", ULTRASOFT: "US", SUPERSOFT: "SS", SUPERHARD: "SH",
    UNKNOWN: "?", TEST_UNKNOWN: "?",
  };
  return map[name] ?? name[0];
}

export function ordinalPos(pos) {
  return pos == null ? "—" : `P${pos}`;
}
