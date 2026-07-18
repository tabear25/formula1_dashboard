// タイヤ戦略: ドライバーごとのスティントを水平バーで表示

import { state, toggleFocus } from "../state.js";
import { el, clearNode, linScale, lapTicks, tooltip } from "../svg.js";
import { fmtLapTime, compoundLetter } from "../format.js";

const M = { top: 26, bottom: 26, left: 92, right: 56 };
const ROW_H = 26;
const BAR_H = 16;

export function renderStrategy(container) {
  clearNode(container);
  const { bundle, derived } = state;

  const panel = document.createElement("div");
  panel.className = "panel";
  container.appendChild(panel);

  const head = document.createElement("div");
  head.className = "panel-head";
  head.innerHTML = `<div class="panel-title">タイヤ戦略</div>
    <div class="panel-sub">スティントごとのコンパウンドと長さ。斜線＝中古タイヤ。ホバーで詳細（スティント平均ペースを含む）。</div>`;
  panel.appendChild(head);

  const host = document.createElement("div");
  host.className = "chart-host";
  panel.appendChild(host);

  const drivers = bundle.drivers.filter((d) => (derived.lapsByDriver.get(d.abbr) ?? []).length > 0);
  const n = drivers.length;
  if (n === 0) {
    host.innerHTML = `<div class="empty-note">ラップデータがありません。</div>`;
    return;
  }
  const maxLap = Math.max(derived.maxLap, derived.totalLaps ?? 0);
  const width = Math.max(680, host.clientWidth || container.clientWidth || 900);
  const height = M.top + M.bottom + n * ROW_H;
  const svg = el("svg", { viewBox: `0 0 ${width} ${height}`, width, height });
  host.appendChild(svg);
  const plot = { x0: M.left, x1: width - M.right, y0: M.top, y1: height - M.bottom };
  const x = linScale(0, maxLap, plot.x0, plot.x1);

  // 中古タイヤ用ハッチ
  const defs = el("defs", {}, svg);
  const pattern = el("pattern", {
    id: "used-hatch", width: 6, height: 6, patternUnits: "userSpaceOnUse",
    patternTransform: "rotate(45)",
  }, defs);
  el("rect", { width: 6, height: 6, fill: "transparent" }, pattern);
  el("line", { x1: 0, y1: 0, x2: 0, y2: 6, stroke: "rgba(11,13,18,0.5)", "stroke-width": 2.5 }, pattern);

  // SC/VSC帯（バー背面）
  for (const band of derived.bands) {
    const bx0 = x(Math.max(0, band.from - 1));
    const bx1 = x(band.to);
    const fill = band.kind === "RED" ? "var(--red-band)" : band.kind === "VSC" ? "var(--vsc-band)" : "var(--sc-band)";
    el("rect", { x: bx0, y: plot.y0 - 4, width: bx1 - bx0, height: plot.y1 - plot.y0 + 8, fill }, svg);
  }

  // 目盛り
  const gridG = el("g", {}, svg);
  for (const lap of lapTicks(maxLap, plot.x1 - plot.x0)) {
    el("line", { class: "gridline", x1: x(lap), x2: x(lap), y1: plot.y0 - 4, y2: plot.y1 + 4 }, gridG);
    el("text", { class: "axis-label", x: x(lap), y: plot.y1 + 18, "text-anchor": "middle", text: lap }, gridG);
  }
  el("text", { class: "axis-label", x: plot.x1 + 6, y: plot.y1 + 18, text: "Lap" }, gridG);

  const focus = state.focus;
  const hasFocus = focus.size > 0;

  drivers.forEach((d, i) => {
    const rowY = M.top + i * ROW_H + (ROW_H - BAR_H) / 2;
    const centerY = rowY + BAR_H / 2;
    const dim = hasFocus && !focus.has(d.abbr);

    // 左ラベル
    const label = el("text", {
      class: `drv-label${dim ? " dim" : ""}`, x: plot.x0 - 10, y: centerY + 3.5, "text-anchor": "end",
    }, svg);
    el("tspan", { class: "pos-part", text: `${d.classified && /^\d+$/.test(d.classified) ? "P" + d.classified : (d.classified ?? "—")} ` }, label);
    el("tspan", { text: d.abbr }, label);
    label.addEventListener("click", () => toggleFocus(d.abbr));
    const keyX = plot.x0 - 10 - ((String(d.classified ?? "—").length + 2 + d.abbr.length) * 6.4) - 18;
    el("line", {
      x1: keyX, x2: keyX + 12, y1: centerY, y2: centerY,
      stroke: d.color, "stroke-width": 3, "stroke-linecap": "round",
      opacity: dim ? 0.25 : 1,
    }, svg);

    const stints = derived.stints.get(d.abbr) ?? [];
    const lapsArr = derived.lapsByDriver.get(d.abbr) ?? [];
    const group = el("g", { opacity: dim ? 0.22 : 1 }, svg);

    for (const stint of stints) {
      const sx = x(stint.from - 1) + 1;
      const sw = Math.max(2, x(stint.to) - x(stint.from - 1) - 2); // 2px サーフェスギャップ
      const color = bundle.compound_colors[stint.cmp] ?? "#8a8f9c";
      const rect = el("rect", {
        x: sx, y: rowY, width: sw, height: BAR_H, rx: 4, fill: color,
      }, group);
      if (stint.fresh === false) {
        el("rect", { x: sx, y: rowY, width: sw, height: BAR_H, rx: 4, fill: "url(#used-hatch)", "pointer-events": "none" }, group);
      }
      const stintLaps = stint.to - stint.from + 1;
      const labelText = `${compoundLetter(stint.cmp)} ${stintLaps}`;
      if (sw >= labelText.length * 7 + 12) {
        el("text", {
          x: sx + sw / 2, y: centerY + 3.5, "text-anchor": "middle",
          fill: pickInk(color), "font-weight": 700, "font-size": 10.5,
          "pointer-events": "none", text: labelText,
        }, group);
      }
      // ホバー: スティント詳細
      const valid = lapsArr.filter((r) => r.lap >= stint.from && r.lap <= stint.to && r.t != null && !r.pit_in && !r.pit_out && r.acc);
      const avg = valid.length ? valid.reduce((sum, r) => sum + r.t, 0) / valid.length : null;
      const best = valid.length ? Math.min(...valid.map((r) => r.t)) : null;
      rect.addEventListener("pointermove", (evt) => {
        tooltip.showRows(evt.clientX, evt.clientY, {
          title: `${d.abbr} — スティント${stint.stint ?? "?"}`,
          rows: [
            { label: "タイヤ", value: `${stint.cmp ?? "?"}${stint.fresh === false ? "（中古）" : ""}` },
            { label: "区間", value: `Lap ${stint.from}–${stint.to}（${stintLaps}周）` },
            { label: "平均", value: avg != null ? fmtLapTime(avg) : "—", extra: "クリーンラップのみ" },
            { label: "ベスト", value: best != null ? fmtLapTime(best) : "—" },
          ],
        });
      });
      rect.addEventListener("pointerleave", () => tooltip.hide());
      rect.addEventListener("click", () => toggleFocus(d.abbr));
    }

    // 右: ストップ回数
    const stops = (derived.pitStops.get(d.abbr) ?? []).length;
    el("text", {
      class: "axis-label", x: plot.x1 + 10, y: centerY + 3.5,
      text: stops > 0 ? `${stops}stop` : "—", opacity: dim ? 0.3 : 1,
    }, svg);
  });
}

// コンパウンド色に応じてラベルの墨色を選ぶ（明るい地色 → 濃い文字）
function pickInk(hexColor) {
  const h = hexColor.replace("#", "");
  const r = parseInt(h.slice(0, 2), 16), g = parseInt(h.slice(2, 4), 16), b = parseInt(h.slice(4, 6), 16);
  const lum = 0.2126 * r + 0.7152 * g + 0.0722 * b;
  return lum > 140 ? "#0b0d12" : "#f5f7fb";
}
