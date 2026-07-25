// サーバ API ラッパ

async function getJSON(url) {
  const res = await fetch(url);
  if (!res.ok) {
    let detail = `${res.status}`;
    try {
      const body = await res.json();
      if (body && body.error) detail = body.error;
    } catch { /* JSON でないエラー本文は無視 */ }
    const err = new Error(detail);
    err.status = res.status;
    throw err;
  }
  return res.json();
}

export const api = {
  years: () => getJSON("/api/years"),
  schedule: (year) => getJSON(`/api/schedule?year=${year}`),
  load: (year, round, session) =>
    getJSON(`/api/load?year=${year}&round=${round}&session=${session}`),
  status: (year, round, session) =>
    getJSON(`/api/status?year=${year}&round=${round}&session=${session}`),
  session: (year, round, session) =>
    getJSON(`/api/session?year=${year}&round=${round}&session=${session}`),
  telemetry: (year, round, session, drivers, lap = "fastest") =>
    getJSON(`/api/telemetry?year=${year}&round=${round}&session=${session}` +
            `&drivers=${drivers.join(",")}&lap=${lap}`),
  trackmap: (year, round, session) =>
    getJSON(`/api/trackmap?year=${year}&round=${round}&session=${session}`),
  replay: (year, round, session) =>
    getJSON(`/api/replay?year=${year}&round=${round}&session=${session}`),
};
