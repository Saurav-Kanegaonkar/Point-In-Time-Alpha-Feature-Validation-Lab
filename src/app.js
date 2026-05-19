const state = {
  surface: "cockpit",
  summary: null,
  queue: [],
  deciles: [],
  pit: [],
  stationarity: [],
  feed: [],
  memos: [],
  events: [],
  actions: [],
};

const paths = {
  summary: "analysis/outputs/summary.json",
  queue: "analysis/outputs/feature_validation_summary.csv",
  deciles: "analysis/outputs/decile_spreads.csv",
  pit: "analysis/outputs/point_in_time_checks.csv",
  stationarity: "analysis/outputs/stationarity_tests.csv",
  feed: "analysis/outputs/feed_health.csv",
  memos: "analysis/outputs/research_memos.csv",
  events: "data/source_events.csv",
  actions: "data/recommended_actions.csv",
};

function parseCsv(text) {
  const rows = [];
  const lines = text.trim().split(/\r?\n/);
  const headers = splitCsvLine(lines.shift());
  lines.forEach((line) => {
    const values = splitCsvLine(line);
    const row = {};
    headers.forEach((header, index) => {
      row[header] = values[index] ?? "";
    });
    rows.push(row);
  });
  return rows;
}

function splitCsvLine(line) {
  const values = [];
  let current = "";
  let quoted = false;
  for (let index = 0; index < line.length; index += 1) {
    const char = line[index];
    if (char === '"' && line[index + 1] === '"') {
      current += '"';
      index += 1;
    } else if (char === '"') {
      quoted = !quoted;
    } else if (char === "," && !quoted) {
      values.push(current);
      current = "";
    } else {
      current += char;
    }
  }
  values.push(current);
  return values;
}

function number(value) {
  return Number.parseFloat(value) || 0;
}

function pct(value) {
  return `${number(value).toFixed(1)}%`;
}

function bps(value) {
  return `${number(value).toFixed(1)} bps`;
}

function score(value) {
  return number(value).toFixed(1);
}

function decisionClass(decision) {
  return `tag ${decision.toLowerCase()}`;
}

function byFeature(rows) {
  return Object.fromEntries(rows.map((row) => [row.feature_id, row]));
}

function topBy(rows, key, count = 5) {
  return [...rows].sort((a, b) => number(b[key]) - number(a[key])).slice(0, count);
}

function renderMetrics() {
  const strip = document.querySelector("#metricStrip");
  const s = state.summary;
  const metrics = [
    ["Panel rows", s.panel_rows.toLocaleString(), `${s.feature_count} features`],
    ["Promote", s.promote_count, "pass research gate"],
    ["Quarantine", s.quarantine_count, "blocked from training"],
    ["Avg test IC", s.avg_test_ic.toFixed(4), "out-of-sample"],
  ];
  strip.innerHTML = metrics
    .map(
      ([label, value, note]) => `
        <article>
          <span>${label}</span>
          <strong>${value}</strong>
          <em>${note}</em>
        </article>
      `,
    )
    .join("");
  document.querySelector("#heroDecision").textContent = `${s.top_feature} leads the queue`;
  document.querySelector("#heroDetail").textContent = `${s.promote_count} features pass the promotion gate while ${s.quarantine_count} are blocked for leakage or feed-health risk.`;
}

function miniBar(value, max, className = "") {
  const width = Math.max(3, Math.min(100, (number(value) / max) * 100));
  return `<span class="bar ${className}"><i style="width:${width}%"></i></span>`;
}

function renderCockpit() {
  const rows = state.queue.slice(0, 10);
  return `
    <div class="surface-grid wide-left">
      <section class="panel">
        <div class="panel-head">
          <p class="eyebrow">Promotion queue</p>
          <h2>Research cockpit</h2>
        </div>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Feature</th>
                <th>Decision</th>
                <th>Score</th>
                <th>Test IC</th>
                <th>Spread</th>
                <th>Health</th>
              </tr>
            </thead>
            <tbody>
              ${rows
                .map(
                  (row) => `
                    <tr>
                      <td>
                        <strong>${row.feature_name}</strong>
                        <small>${row.vendor_family} | ${row.category}</small>
                      </td>
                      <td><span class="${decisionClass(row.decision)}">${row.decision}</span></td>
                      <td>${score(row.promotion_score)}${miniBar(row.promotion_score, 100)}</td>
                      <td>${number(row.test_ic).toFixed(4)}</td>
                      <td>${bps(row.long_short_spread_bps)}</td>
                      <td>${score(row.health_score)}</td>
                    </tr>
                  `,
                )
                .join("")}
            </tbody>
          </table>
        </div>
      </section>
      <aside class="panel stack">
        <p class="eyebrow">Decision rule</p>
        <h2>What gets promoted</h2>
        <p>Features need positive out-of-sample evidence, tolerable drift, clean availability timing, and a feed-health score high enough for production monitoring.</p>
        <div class="decision-list">
          ${["promote", "watch", "repair", "quarantine"]
            .map((decision) => {
              const count = state.queue.filter((row) => row.decision === decision).length;
              return `<div><span class="${decisionClass(decision)}">${decision}</span><strong>${count}</strong></div>`;
            })
            .join("")}
        </div>
      </aside>
    </div>
  `;
}

function renderValidation() {
  const pitMap = byFeature(state.pit);
  const statMap = byFeature(state.stationarity);
  const risky = state.queue
    .filter((row) => row.decision !== "promote")
    .slice(0, 8)
    .map((row) => ({ ...row, ...pitMap[row.feature_id], ...statMap[row.feature_id] }));
  const selected = state.queue[0];
  const deciles = state.deciles.filter((row) => row.feature_id === selected.feature_id);
  const maxSpread = Math.max(...deciles.map((row) => Math.abs(number(row.avg_forward_5d_return_bps))), 1);
  return `
    <div class="surface-grid">
      <section class="panel">
        <div class="panel-head">
          <p class="eyebrow">Cross-sectional test</p>
          <h2>Decile return shape</h2>
        </div>
        <p class="subtle">${selected.feature_name} should show monotonic separation if the feature carries useful information.</p>
        <div class="decile-chart">
          ${deciles
            .map(
              (row) => `
                <div>
                  <span>D${row.decile}</span>
                  ${miniBar(Math.abs(number(row.avg_forward_5d_return_bps)), maxSpread, number(row.avg_forward_5d_return_bps) >= 0 ? "good" : "bad")}
                  <strong>${bps(row.avg_forward_5d_return_bps)}</strong>
                </div>
              `,
            )
            .join("")}
        </div>
      </section>
      <section class="panel">
        <div class="panel-head">
          <p class="eyebrow">Leakage and drift</p>
          <h2>Validation exceptions</h2>
        </div>
        <div class="table-wrap compact">
          <table>
            <thead><tr><th>Feature</th><th>PIT fail</th><th>PSI</th><th>IC decay</th><th>Status</th></tr></thead>
            <tbody>
              ${risky
                .map(
                  (row) => `
                    <tr>
                      <td><strong>${row.feature_id}</strong><small>${row.feature_name}</small></td>
                      <td>${pct(row.late_rate)}</td>
                      <td>${number(row.stationarity_psi).toFixed(3)}</td>
                      <td>${number(row.degradation).toFixed(4)}</td>
                      <td><span class="${decisionClass(row.decision)}">${row.decision}</span></td>
                    </tr>
                  `,
                )
                .join("")}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  `;
}

function renderMonitor() {
  const worstFeeds = topBy(state.feed, "high_severity_events", 6);
  const latestEvents = [...state.events].reverse().slice(0, 8);
  return `
    <div class="surface-grid wide-right">
      <section class="panel">
        <div class="panel-head">
          <p class="eyebrow">Production monitor</p>
          <h2>Vendor feed health</h2>
        </div>
        <div class="feed-grid">
          ${worstFeeds
            .map(
              (row) => `
                <article>
                  <div>
                    <strong>${row.feature_id}</strong>
                    <span>${row.vendor_family}</span>
                  </div>
                  <b>${score(row.health_score)}</b>
                  <p>Latency ${number(row.avg_latency_days).toFixed(1)} days | Missing ${pct(row.missing_rate)} | Restated ${pct(row.restatement_rate)}</p>
                </article>
              `,
            )
            .join("")}
        </div>
      </section>
      <aside class="panel">
        <div class="panel-head">
          <p class="eyebrow">Root-cause queue</p>
          <h2>Latest incidents</h2>
        </div>
        <div class="event-list">
          ${latestEvents
            .map(
              (event) => `
                <article>
                  <span class="severity ${event.severity}">${event.severity}</span>
                  <strong>${event.feature_id} | ${event.event_type.replaceAll("_", " ")}</strong>
                  <p>${event.root_cause}</p>
                </article>
              `,
            )
            .join("")}
        </div>
      </aside>
    </div>
  `;
}

function renderMemo() {
  const actionMap = state.actions.reduce((acc, action) => {
    acc[action.feature_id] = acc[action.feature_id] || [];
    acc[action.feature_id].push(action);
    return acc;
  }, {});
  const memoRows = state.memos
    .filter((memo) => ["promote", "repair", "quarantine"].includes(memo.decision))
    .slice(0, 6);
  return `
    <div class="memo-grid">
      ${memoRows
        .map((memo) => {
          const action = (actionMap[memo.feature_id] || [])[0];
          return `
            <article class="panel memo-card">
              <div class="memo-top">
                <p class="eyebrow">${memo.feature_id}</p>
                <span class="${decisionClass(memo.decision)}">${memo.decision}</span>
              </div>
              <h2>${memo.feature_name}</h2>
              <p>${memo.thesis}</p>
              <dl>
                <div><dt>Evidence</dt><dd>${memo.evidence}</dd></div>
                <div><dt>Next step</dt><dd>${memo.next_step}</dd></div>
                <div><dt>Action owner</dt><dd>${action ? `${action.owner}, ${action.effort_hours} hours` : "Research review"}</dd></div>
              </dl>
            </article>
          `;
        })
        .join("")}
    </div>
  `;
}

function renderSurface() {
  const surface = document.querySelector("#surface");
  const renderers = {
    cockpit: renderCockpit,
    validation: renderValidation,
    monitor: renderMonitor,
    memo: renderMemo,
  };
  surface.innerHTML = renderers[state.surface]();
}

async function loadData() {
  const [summary, queue, deciles, pit, stationarity, feed, memos, events, actions] = await Promise.all([
    fetch(paths.summary).then((response) => response.json()),
    fetch(paths.queue).then((response) => response.text()).then(parseCsv),
    fetch(paths.deciles).then((response) => response.text()).then(parseCsv),
    fetch(paths.pit).then((response) => response.text()).then(parseCsv),
    fetch(paths.stationarity).then((response) => response.text()).then(parseCsv),
    fetch(paths.feed).then((response) => response.text()).then(parseCsv),
    fetch(paths.memos).then((response) => response.text()).then(parseCsv),
    fetch(paths.events).then((response) => response.text()).then(parseCsv),
    fetch(paths.actions).then((response) => response.text()).then(parseCsv),
  ]);
  Object.assign(state, { summary, queue, deciles, pit, stationarity, feed, memos, events, actions });
  renderMetrics();
  renderSurface();
}

document.querySelectorAll(".surface-tabs button").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelectorAll(".surface-tabs button").forEach((item) => item.classList.remove("active"));
    button.classList.add("active");
    state.surface = button.dataset.surface;
    renderSurface();
  });
});

loadData().catch((error) => {
  document.querySelector("#surface").innerHTML = `<section class="panel"><h2>Data failed to load</h2><p>${error.message}</p></section>`;
});
