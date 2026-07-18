// バンドル(JSON)からチャート用の派生データを一括計算する

// TrackStatus 文字列（例 "124"）に含まれるコードで状態を判定
export function statusKind(tsString) {
  if (!tsString) return null;
  if (tsString.includes("5")) return "RED";
  if (tsString.includes("4")) return "SC";
  if (tsString.includes("6") || tsString.includes("7")) return "VSC";
  if (tsString.includes("2")) return "YEL";
  return null;
}

export function derive(bundle) {
  const drivers = bundle.drivers ?? [];
  const laps = bundle.laps ?? [];
  const isRace = bundle.meta.type === "race";

  const driverMap = new Map(drivers.map((d) => [d.abbr, d]));

  // ドライバー別ラップ（lap 昇順）
  const lapsByDriver = new Map();
  for (const rec of laps) {
    if (!lapsByDriver.has(rec.drv)) lapsByDriver.set(rec.drv, []);
    lapsByDriver.get(rec.drv).push(rec);
  }
  for (const arr of lapsByDriver.values()) arr.sort((a, b) => a.lap - b.lap);

  const lapIndex = new Map();
  for (const [abbr, arr] of lapsByDriver) {
    lapIndex.set(abbr, new Map(arr.map((r) => [r.lap, r])));
  }

  let maxLap = 0;
  for (const rec of laps) maxLap = Math.max(maxLap, rec.lap);
  const totalLaps = bundle.meta.total_laps ?? maxLap;

  // ラップごとの全ドライバー行 + 状態ユニオン
  const rowsPerLap = new Map(); // lap -> rec[]
  for (const rec of laps) {
    if (!rowsPerLap.has(rec.lap)) rowsPerLap.set(rec.lap, []);
    rowsPerLap.get(rec.lap).push(rec);
  }

  const statusPerLap = new Map(); // lap -> "RED"|"SC"|"VSC"|"YEL"|null
  for (const [lap, rows] of rowsPerLap) {
    let kind = null;
    const rank = { RED: 4, SC: 3, VSC: 2, YEL: 1 };
    for (const r of rows) {
      const k = statusKind(r.ts);
      if (k && (!kind || rank[k] > rank[kind])) kind = k;
    }
    statusPerLap.set(lap, kind);
  }

  // SC/VSC/赤旗の帯（連続区間へまとめる。黄旗のみは帯にしない）
  const bands = [];
  let current = null;
  for (let lap = 1; lap <= maxLap; lap++) {
    const kind = statusPerLap.get(lap);
    const bandKind = kind === "YEL" ? null : kind;
    if (bandKind && current && current.kind === bandKind && current.to === lap - 1) {
      current.to = lap;
    } else if (bandKind) {
      current = { from: lap, to: lap, kind: bandKind };
      bands.push(current);
    } else {
      current = null;
    }
  }

  // ラップごとの順位表（レースのみ意味を持つ）+ リーダー基準ギャップ
  const towerPerLap = new Map();
  if (isRace) {
    for (const [lap, rows] of rowsPerLap) {
      const valid = rows.filter((r) => r.pos != null);
      valid.sort((a, b) => a.pos - b.pos);
      const ets = rows.map((r) => r.et).filter((v) => v != null);
      const leaderEt = ets.length ? Math.min(...ets) : null;
      towerPerLap.set(lap, valid.map((r) => ({
        abbr: r.drv,
        pos: r.pos,
        gap: r.et != null && leaderEt != null ? r.et - leaderEt : null,
        cmp: r.cmp,
        life: r.life,
        pit: r.pit_in || r.pit_out,
      })));
    }
  }

  // スティント一覧
  const stints = new Map(); // abbr -> [{stint, cmp, from, to, fresh}]
  for (const [abbr, arr] of lapsByDriver) {
    const list = [];
    for (const rec of arr) {
      const last = list[list.length - 1];
      if (last && last.stint === rec.stint && last.cmp === rec.cmp) {
        last.to = rec.lap;
      } else {
        list.push({ stint: rec.stint, cmp: rec.cmp, from: rec.lap, to: rec.lap, fresh: rec.fresh });
      }
    }
    stints.set(abbr, list);
  }

  // ピットストップ（pit_in したラップ。次スティントのコンパウンドを添える）
  const pitStops = new Map(); // abbr -> [{lap, pos, nextCmp}]
  for (const [abbr, arr] of lapsByDriver) {
    const idx = lapIndex.get(abbr);
    const stops = [];
    for (const rec of arr) {
      if (!rec.pit_in) continue;
      const next = idx.get(rec.lap + 1);
      stops.push({ lap: rec.lap, pos: rec.pos, nextCmp: next?.cmp ?? null });
    }
    pitStops.set(abbr, stops);
  }

  // セッション最速ラップ（削除ラップ除外）
  let fastestLap = null;
  for (const rec of laps) {
    if (rec.t == null || rec.del) continue;
    if (!fastestLap || rec.t < fastestLap.t) {
      fastestLap = { abbr: rec.drv, lap: rec.lap, t: rec.t };
    }
  }

  // 完走判定と最終ラップ
  const lastLapOf = new Map();
  for (const [abbr, arr] of lapsByDriver) {
    lastLapOf.set(abbr, arr.length ? arr[arr.length - 1].lap : 0);
  }
  const finished = new Map();
  for (const d of drivers) {
    const cls = d.classified;
    finished.set(d.abbr, cls != null && /^\d+$/.test(cls));
  }

  // 首位交代回数 / SC・VSC ラップ数
  let leadChanges = 0;
  if (isRace) {
    let prevLeader = null;
    for (let lap = 1; lap <= maxLap; lap++) {
      const tower = towerPerLap.get(lap);
      const leader = tower && tower.length ? tower[0].abbr : null;
      if (leader && prevLeader && leader !== prevLeader) leadChanges++;
      if (leader) prevLeader = leader;
    }
  }
  const scLaps = [...statusPerLap.values()].filter((k) => k === "SC").length;
  const vscLaps = [...statusPerLap.values()].filter((k) => k === "VSC").length;

  // 勝者平均ペース基準の参照時刻（レースヒストリーチャート用）
  let historyRef = null;
  if (isRace && drivers.length > 0) {
    const winner = drivers[0];
    const wLaps = lapsByDriver.get(winner.abbr) ?? [];
    const wLast = wLaps[wLaps.length - 1];
    const wFirst = wLaps[0];
    if (wLast && wFirst && wLast.et != null && wFirst.st != null && wLast.lap > 0) {
      const avg = (wLast.et - wFirst.st) / wLast.lap;
      historyRef = { start: wFirst.st, avg };
    }
  }

  // 予選: セグメントベスト
  const qBest = { q1: null, q2: null, q3: null };
  for (const d of drivers) {
    for (const seg of ["q1", "q2", "q3"]) {
      if (d[seg] != null && (qBest[seg] == null || d[seg] < qBest[seg])) qBest[seg] = d[seg];
    }
  }

  return {
    isRace,
    driverMap,
    lapsByDriver,
    lapIndex,
    rowsPerLap,
    towerPerLap,
    statusPerLap,
    bands,
    stints,
    pitStops,
    fastestLap,
    lastLapOf,
    finished,
    leadChanges,
    scLaps,
    vscLaps,
    historyRef,
    qBest,
    maxLap,
    totalLaps,
  };
}
