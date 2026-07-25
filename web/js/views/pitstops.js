// ピット分析（レース専用）: 各ピットストップのタイムロス推定と、
// 前後で入れ替わったアンダーカット/オーバーカットの検出。
// タイムロス = (イン+アウトラップ) − 2×クリーンラップ中央値 の近似。

import { state, toggleFocus } from "../state.js";
import { clearNode } from "../svg.js";
import { fmtGap, fmtSecs, compoundLetter } from "../format.js";
import { statusKind } from "../derive.js";

export function renderPitstops(container) {
  clearNode(container);
  const { bundle, derived } = state;

  // ドライバー別のクリーンラップ中央値（ロス推定の基準）
  const medianClean = new Map();
  for (const [abbr, recs] of derived.lapsByDriver) {
    const clean = recs.filter((r) => r.t != null && !r.pit_in && !r.pit_out && !r.del && !statusKind(r.ts))
      .map((r) => r.t).sort((a, b) => a - b);
    if (clean.length >= 3) medianClean.set(abbr, clean[Math.floor(clean.length / 2)]);
  }

  // ---- ストップ一覧 ----
  const stops = [];
  for (const d of bundle.drivers) {
    const idx = derived.lapIndex.get(d.abbr);
    if (!idx) continue;
    for (const stop of derived.pitStops.get(d.abbr) ?? []) {
      const inLap = idx.get(stop.lap);
      const outLap = idx.get(stop.lap + 1);
      const median = medianClean.get(d.abbr);
      let loss = null;
      if (inLap?.t != null && outLap?.t != null && median != null) {
        loss = inLap.t + outLap.t - 2 * median;
      }
      const scNow = inLap ? statusKind(inLap.ts) : null;
      const posBefore = idx.get(stop.lap - 1)?.pos ?? inLap?.pos ?? null;
      const posAfter = idx.get(stop.lap + 2)?.pos ?? outLap?.pos ?? null;
      stops.push({
        d, lap: stop.lap, fromCmp: inLap?.cmp ?? null, toCmp: stop.nextCmp,
        loss, sc: scNow === "SC" || scNow === "VSC",
        posBefore, posAfter,
      });
    }
  }
  stops.sort((a, b) => a.lap - b.lap);

  const panel = document.createElement("div");
  panel.className = "panel";
  container.appendChild(panel);
  const head = document.createElement("div");
  head.className = "panel-head";
  head.innerHTML = `<div class="panel-title">ピットストップ</div>
    <div class="panel-sub">タイムロス＝（イン＋アウトラップ）−（クリーンラップ中央値×2）の近似値。SC中のストップは割安になる。行クリックで選択。</div>`;
  panel.appendChild(head);

  if (stops.length === 0) {
    panel.insertAdjacentHTML("beforeend", `<div class="empty-note">ピットストップがありません。</div>`);
  } else {
    const wrap = document.createElement("div");
    wrap.className = "data-table-wrap";
    panel.appendChild(wrap);
    const table = document.createElement("table");
    table.className = "data-table";
    const thead = document.createElement("thead");
    thead.innerHTML = `<tr><th class="num">Lap</th><th>ドライバー</th><th>タイヤ交換</th>
      <th class="num">推定ロス</th><th>状況</th><th class="num">順位変動</th></tr>`;
    table.appendChild(thead);
    const tbody = document.createElement("tbody");
    const cmpChip = (cmp) => {
      if (!cmp) return "?";
      return compoundLetter(cmp);
    };
    for (const s of stops) {
      const tr = document.createElement("tr");
      tr.style.cursor = "pointer";
      tr.addEventListener("click", () => toggleFocus(s.d.abbr));
      if (state.focus.size > 0 && !state.focus.has(s.d.abbr)) tr.style.opacity = "0.45";

      const tdLap = document.createElement("td");
      tdLap.className = "num";
      tdLap.textContent = String(s.lap);
      tr.appendChild(tdLap);

      const tdD = document.createElement("td");
      const key = document.createElement("span");
      key.className = "team-key";
      key.style.background = s.d.color;
      tdD.appendChild(key);
      tdD.appendChild(document.createTextNode(s.d.abbr));
      tr.appendChild(tdD);

      const tdTyre = document.createElement("td");
      const mkChip = (cmp) => {
        const chip = document.createElement("span");
        chip.className = "tyre-chip";
        chip.style.background = bundle.compound_colors[cmp] ?? "#8a8f9c";
        chip.textContent = cmpChip(cmp);
        return chip;
      };
      if (s.fromCmp) tdTyre.appendChild(mkChip(s.fromCmp));
      tdTyre.appendChild(document.createTextNode(" → "));
      if (s.toCmp) tdTyre.appendChild(mkChip(s.toCmp));
      else tdTyre.appendChild(document.createTextNode("—"));
      tr.appendChild(tdTyre);

      const tdLoss = document.createElement("td");
      tdLoss.className = "num";
      tdLoss.textContent = s.loss != null ? `${fmtSecs(s.loss, 1)}s` : "—";
      tr.appendChild(tdLoss);

      const tdSc = document.createElement("td");
      if (s.sc) {
        const chip = document.createElement("span");
        chip.className = "flag-chip f-sc";
        chip.textContent = "SC/VSC中";
        tdSc.appendChild(chip);
      } else {
        tdSc.textContent = "—";
      }
      tr.appendChild(tdSc);

      const tdPos = document.createElement("td");
      tdPos.className = "num";
      if (s.posBefore != null && s.posAfter != null) {
        const diff = s.posBefore - s.posAfter;
        const span = document.createElement("span");
        span.textContent = `P${s.posBefore}→P${s.posAfter}`;
        if (diff > 0) span.className = "delta-up";
        else if (diff < 0) span.className = "delta-down";
        tdPos.appendChild(span);
      } else {
        tdPos.textContent = "—";
      }
      tr.appendChild(tdPos);
      tbody.appendChild(tr);
    }
    table.appendChild(tbody);
    wrap.appendChild(table);
  }

  // ---- アンダーカット/オーバーカット検出 ----
  const duels = detectUndercuts(bundle, derived);
  const uPanel = document.createElement("div");
  uPanel.className = "panel";
  container.appendChild(uPanel);
  const uHead = document.createElement("div");
  uHead.className = "panel-head";
  uHead.innerHTML = `<div class="panel-title">アンダーカット / オーバーカット</div>
    <div class="panel-sub">近接していた2台が異なるラップでピットした局面の、前後3周でのタイム差の変動（＋＝先にピットした側が得）。</div>`;
  uPanel.appendChild(uHead);

  if (duels.length === 0) {
    uPanel.insertAdjacentHTML("beforeend", `<div class="empty-note">検出できる局面がありません（近接した状態でのピット差し合いが無かったか、データ不足です）。</div>`);
    return;
  }
  const uWrap = document.createElement("div");
  uWrap.className = "data-table-wrap";
  uPanel.appendChild(uWrap);
  const uTable = document.createElement("table");
  uTable.className = "data-table";
  const uThead = document.createElement("thead");
  uThead.innerHTML = `<tr><th>先にピット</th><th class="num">Lap</th><th>相手（後にピット）</th><th class="num">Lap</th>
    <th class="num">前ギャップ</th><th class="num">後ギャップ</th><th class="num">獲得</th><th>結果</th></tr>`;
  uTable.appendChild(uThead);
  const uTbody = document.createElement("tbody");
  for (const u of duels) {
    const tr = document.createElement("tr");
    const mkDriver = (d) => {
      const td = document.createElement("td");
      const key = document.createElement("span");
      key.className = "team-key";
      key.style.background = d.color;
      td.appendChild(key);
      td.appendChild(document.createTextNode(d.abbr));
      td.style.cursor = "pointer";
      td.addEventListener("click", () => toggleFocus(d.abbr));
      return td;
    };
    tr.appendChild(mkDriver(u.first));
    const tdL1 = document.createElement("td");
    tdL1.className = "num";
    tdL1.textContent = String(u.firstLap);
    tr.appendChild(tdL1);
    tr.appendChild(mkDriver(u.second));
    const tdL2 = document.createElement("td");
    tdL2.className = "num";
    tdL2.textContent = String(u.secondLap);
    tr.appendChild(tdL2);
    const tdG0 = document.createElement("td");
    tdG0.className = "num";
    tdG0.textContent = fmtGap(u.gapBefore, 1);
    tr.appendChild(tdG0);
    const tdG1 = document.createElement("td");
    tdG1.className = "num";
    tdG1.textContent = fmtGap(u.gapAfter, 1);
    tr.appendChild(tdG1);
    const tdSwing = document.createElement("td");
    tdSwing.className = "num";
    const span = document.createElement("span");
    span.textContent = fmtGap(u.swing, 1);
    span.className = u.swing > 0 ? "delta-up" : (u.swing < 0 ? "delta-down" : "delta-zero");
    tdSwing.appendChild(span);
    tr.appendChild(tdSwing);
    const tdRes = document.createElement("td");
    tdRes.textContent = u.overtook ? `${u.first.abbr} が前へ（アンダーカット成立）`
      : (u.swing < 0 ? `${u.second.abbr} が引っ張って得（オーバーカット）` : "順位変わらず");
    tr.appendChild(tdRes);
    uTbody.appendChild(tr);
  }
  uTable.appendChild(uTbody);
  uWrap.appendChild(uTable);
}

// 近接ペアのピット差し合い検出。
// 条件: AがLapLでピット、BはL+1〜L+5でピット、L-1時点の|ギャップ|<25s。
// swing = (etB−etA) の変化（両者のピットが完了した後の周で評価）。
function detectUndercuts(bundle, derived) {
  const etAt = (abbr, lap) => derived.lapIndex.get(abbr)?.get(lap)?.et ?? null;
  const posAt = (abbr, lap) => derived.lapIndex.get(abbr)?.get(lap)?.pos ?? null;
  const recAt = (abbr, lap) => derived.lapIndex.get(abbr)?.get(lap);
  const out = [];
  for (const a of bundle.drivers) {
    const stopsA = derived.pitStops.get(a.abbr) ?? [];
    for (const stopA of stopsA) {
      for (const b of bundle.drivers) {
        if (a.abbr === b.abbr) continue;
        const stopsB = derived.pitStops.get(b.abbr) ?? [];
        const stopB = stopsB.find((s) => s.lap > stopA.lap && s.lap <= stopA.lap + 5);
        if (!stopB) continue;
        const evalLap = stopB.lap + 2;
        // 計測窓を汚す追加ピットがある局面は捨てる:
        //   - B が stopA 直前5周以内にもピットしている（双方向の重複行・2連続ストップ）
        //   - A・B のどちらかが (stopA.lap, evalLap] に stopB 以外のピットを持つ
        //   - before 計測ラップ（stopA.lap-1）が A・B どちらかのイン/アウトラップ
        if (stopsB.some((s) => s.lap >= stopA.lap - 5 && s.lap <= stopA.lap)) continue;
        if (stopsA.some((s) => s.lap > stopA.lap && s.lap <= evalLap)) continue;
        if (stopsB.some((s) => s.lap !== stopB.lap && s.lap > stopA.lap && s.lap <= evalLap)) continue;
        const aBefore = recAt(a.abbr, stopA.lap - 1);
        const bBefore = recAt(b.abbr, stopA.lap - 1);
        if (!aBefore || !bBefore || aBefore.pit_in || aBefore.pit_out || bBefore.pit_in || bBefore.pit_out) continue;
        const before0 = etAt(a.abbr, stopA.lap - 1);
        const before1 = etAt(b.abbr, stopA.lap - 1);
        const after0 = etAt(a.abbr, evalLap);
        const after1 = etAt(b.abbr, evalLap);
        if (before0 == null || before1 == null || after0 == null || after1 == null) continue;
        const gapBefore = before1 - before0;   // ＋ = Bが後ろ
        if (Math.abs(gapBefore) > 25) continue;
        const gapAfter = after1 - after0;
        const swing = gapAfter - gapBefore;    // ＋ = Aが得
        if (Math.abs(swing) < 1.0) continue;
        const posBefore0 = posAt(a.abbr, stopA.lap - 1);
        const posAfterEval = posAt(a.abbr, evalLap);
        const posBefore1 = posAt(b.abbr, stopA.lap - 1);
        const posAfter1 = posAt(b.abbr, evalLap);
        const overtook = posBefore0 != null && posBefore1 != null && posAfterEval != null && posAfter1 != null
          && posBefore0 > posBefore1 && posAfterEval < posAfter1;
        out.push({
          first: a, second: b, firstLap: stopA.lap, secondLap: stopB.lap,
          gapBefore, gapAfter, swing, overtook,
        });
      }
    }
  }
  out.sort((x, y) => Math.abs(y.swing) - Math.abs(x.swing));
  return out.slice(0, 14);
}
