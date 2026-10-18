/* Company OS console shell v2: role switcher, plug-in pages (contract C8), Home, Approvals, Runs. Rules: ../DESIGN.md */
(() => {
"use strict";
const $ = (s, r = document) => r.querySelector(s);
function h(tag, attrs, ...kids) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v == null || v === false) continue;
    if (k.startsWith("on")) el.addEventListener(k.slice(2), v); else el.setAttribute(k, v === true ? "" : v);
  }
  const add = (c) => { if (Array.isArray(c)) c.forEach(add); else if (c != null && c !== false) el.append(c instanceof Node ? c : document.createTextNode(String(c))); };
  kids.forEach(add);
  return el;
}
const ICONS = {
  home: '<path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><path d="M9 22V12h6v10"/>',
  check: '<path d="M20 6L9 17l-5-5"/>', x: '<path d="M18 6L6 18M6 6l12 12"/>', pulse: '<path d="M22 12h-4l-3 9L9 3l-3 9H2"/>',
  pause: '<rect x="6" y="4" width="4" height="16" rx="1"/><rect x="14" y="4" width="4" height="16" rx="1"/>',
  flag: '<path d="M4 22V4"/><path d="M4 4h13l-2 4 2 4H4"/>', chevron: '<path d="M9 18l6-6-6-6"/>', menu: '<path d="M3 6h18M3 12h18M3 18h18"/>',
  settings: '<path d="M4 21v-7M4 10V3M12 21v-9M12 8V3M20 21v-5M20 12V3M1 14h6M9 8h6M17 16h6"/>', alert: '<circle cx="12" cy="12" r="10"/><path d="M12 8v4M12 16h.01"/>',
  coin: '<path d="M6 3h12M6 8h12M6 13l8.5 8M6 13h3M9 13c6.667 0 6.667-10 0-10"/>', calendar: '<rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/>',
  book: '<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>',
  list: '<path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01"/>', play: '<path d="M6 4l14 8-14 8z"/>',
  bot: '<rect x="4" y="8" width="16" height="12" rx="3"/><path d="M12 8V4M9 14h.01M15 14h.01"/>', users: '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/>',
  moon: '<path d="M21 12.8A9 9 0 1 1 11.2 3 7 7 0 0 0 21 12.8z"/>', minus: '<path d="M5 12h14"/>',
};
function icon(name) {
  const t = document.createElement("template");
  t.innerHTML = `<svg class="i" viewBox="0 0 24 24" aria-hidden="true" focusable="false">${ICONS[name] || ICONS.bot}</svg>`;
  return t.content.firstChild;
}
const FAMILY = { brain: "brain", review: "brain", meeting_prep: "meeting_prep", deals: "meeting_prep", live: "meeting_prep",
  finance: "finance", travel: "finance", approvals: "finance", runs: "brain", home: "brain" };
const STATUS = { done: ["ok", "check", "Done"], approved: ["ok", "check", "Approved"], held: ["wait", "pause", "Waiting for approval"],
  pending: ["wait", "pause", "Waiting for approval"], quiet: ["calm", "moon", "Quiet"], refused: ["stop", "x", "Refused"],
  failed: ["stop", "x", "Stopped"], rejected: ["stop", "x", "Denied"], running: ["calm", "play", "Running"] };
const chip = (key, text) => { const [k, ic, w] = STATUS[key] || ["calm", "minus", String(key).replace(/_/g, " ")]; return h("span", { class: `chip ${k}` }, icon(ic), text || w); };
const kindChip = (kind, ic, text) => h("span", { class: `chip ${kind}` }, icon(ic), text);
const money = (v) => "$" + (v || 0).toFixed(4);
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
function when(iso) {
  const m = String(iso || "").match(/^(\d{4})-(\d{2})-(\d{2})(?:T(\d{2}):(\d{2}))?/);
  if (!m) return "";
  const date = `${+m[3]} ${MONTHS[m[2] - 1]}`;
  if (m[4] === undefined) return date;
  return `${date}, ${m[4] % 12 || 12}:${m[5]} ${m[4] < 12 ? "AM" : "PM"}`;
}
const store = { get: (k) => { try { return localStorage.getItem(k); } catch (e) { return null; } }, set: (k, v) => { try { localStorage.setItem(k, v); } catch (e) { /* no storage */ } } };

const S = { people: [], viewer: null, pages: [], state: {}, registry: {}, loaded: new Set(), token: 0 };
const viewerOf = () => S.people.find((p) => p.person_id === S.viewer) || {};

async function api(path, opts = {}) {
  const method = opts.method || "GET";
  let url = path, init = { method };
  if (method === "GET") url += (path.includes("?") ? "&" : "?") + "viewer=" + encodeURIComponent(S.viewer || "");
  else { init.headers = { "Content-Type": "application/json" }; init.body = JSON.stringify({ ...(opts.body || {}), viewer: S.viewer }); }
  try { const res = await fetch(url, init); const data = await res.json(); data.status = res.status; return data; }
  catch (e) { return { ok: false, error: "The console did not answer. Is it still running?" }; }
}
let toastTimer;
function toast(text) { const t = $("#toast"); t.textContent = text; t.hidden = false; clearTimeout(toastTimer); toastTimer = setTimeout(() => { t.hidden = true; }, 5000); }
const loading = (text = "Loading") => h("p", { class: "spinner" }, text);
const errorLine = (text) => h("p", { class: "err", role: "alert" }, icon("alert"), text);

/* ---------- letters (shared helper for plug-in pages) ---------- */
function letter(m) {
  const lines = String(m.text || "").split("\n").filter((l) => l.trim());
  const body = h("div", { class: "letter-body" }, lines.map((l) => {
    const lab = l.match(/^(Evidence|Why it matters|Next step):\s*(.*)$/);
    return h("p", null, lab ? [h("strong", null, lab[1] + ": "), lab[2]] : l);
  }));
  return h("article", { class: "letter" }, h("div", { class: "letter-head" },
    h("div", { class: "who" }, h("span", { class: "agent-name" }, m.agent_title || m.agent || "Agent"), m.to_name ? ` to ${m.to_name}` : ""),
    h("time", null, when(m.created_at))), body);
}

/* ---------- drawer and run story ---------- */
let lastFocus = null;
function showDrawer(nodes) {
  const body = $("#drawer-body"); body.replaceChildren(...nodes);
  lastFocus = document.activeElement; $("#drawer").inert = false;
  $("#drawer").classList.add("open"); $("#scrim").classList.add("open");
  const c = $("#drawer-close"); if (c) c.focus();
}
function closeDrawer() {
  $("#drawer").classList.remove("open"); $("#scrim").classList.remove("open"); $("#drawer").inert = true;
  if (lastFocus && lastFocus.focus) lastFocus.focus();
}
const closeBtn = () => h("button", { class: "icon-btn", id: "drawer-close", "aria-label": "Close", onclick: closeDrawer }, icon("x"));
const DOT = { ok: "ok", done: "ok", quiet: "calm", skipped: "calm", refused: "stop", failed: "stop", held: "wait" };
function verdict(i) {
  const v = i.verdict;
  if (v === "denied") return kindChip("stop", "x", i.note ? `${i.text}: ${i.note}` : `${i.text} was denied`);
  if (v === "held") return kindChip("wait", "pause", `${i.text}: waits for a person`);
  return kindChip("ok", "check", i.text);
}
function storyTimeline(walk) {
  return h("ol", { class: "timeline" }, walk.steps.filter((s) => s.state !== "skipped" || walk.outcome !== "quiet").map((s) => {
    const k = DOT[s.state] || "ok";
    const verdicts = (s.items || []).filter((i) => i.verdict);
    return h("li", { class: "step" }, h("span", { class: `dot ${k}` }, icon(k === "stop" ? "x" : k === "wait" ? "pause" : "check")),
      h("div", null, h("h4", null, s.title),
        (s.lines || []).length ? h("div", { class: "detail" }, s.lines.map((l) => h("p", null, l))) : null,
        verdicts.length ? h("div", { class: "chip-row" }, verdicts.map(verdict)) : null));
  }));
}
async function runStory(runId) {
  showDrawer([h("div", { class: "drawer-head" }, h("h2", { id: "drawer-title" }, "Loading the run"), closeBtn()), h("div", { class: "drawer-sec" }, loading())]);
  const r = await api("/api/run?id=" + encodeURIComponent(runId));
  if (!r.ok) { showDrawer([h("div", { class: "drawer-head" }, h("h2", { id: "drawer-title" }, "Run not available"), closeBtn()), h("div", { class: "drawer-sec" }, errorLine(r.error))]); return; }
  const run = r.run;
  const who = run.caller_id === "system" ? `Started by the ${run.trigger_kind}` : `Asked by ${run.caller_name}`;
  const secs = [h("div", { class: "drawer-head" }, h("div", { class: "titles" }, h("h2", { id: "drawer-title" }, run.agent_title),
      h("p", { class: "small muted" }, `${who} · ${when(run.started_at)} · ${run.area_name}`), h("div", null, chip(run.status_label))), closeBtn()),
    h("section", { class: "drawer-sec" }, h("p", { class: "headline" }, r.walkthrough.headline), h("h3", null, "How it went"), storyTimeline(r.walkthrough))];
  if ((r.messages || []).length) secs.push(h("section", { class: "drawer-sec" }, h("h3", null, "The letters it wrote"), h("div", { class: "letters" }, r.messages.map(letter))));
  showDrawer(secs);
}

/* ---------- plug-in registry (C8) ---------- */
const ctxFor = () => ({ viewer: { person_id: S.viewer, name: viewerOf().name, role: viewerOf().role }, api, el: h, letter, runStory, toast,
  go: (id, params) => { location.hash = "#" + id + (params ? "?" + new URLSearchParams(params) : ""); } });
window.CompanyOS = { registerPage(def) { if (def && def.id) S.registry[def.id] = def; } };

function loadAsset(tag, attrs) {
  return new Promise((resolve) => { const el = h(tag, { ...attrs, onload: () => resolve(true), onerror: () => resolve(false) }); document.head.append(el); });
}
async function loadPlugins() {
  for (const p of S.pages) {
    if (S.loaded.has(p.id) || !p.script) continue;
    S.loaded.add(p.id);
    if (p.css) await loadAsset("link", { rel: "stylesheet", href: p.css });
    await loadAsset("script", { src: p.script });
  }
}

/* ---------- placeholder, Home ---------- */
const pageInfo = (id) => S.pages.find((p) => p.id === id) || { id, title: id };
function placeholder(p) {
  return h("div", { class: "empty" }, h("span", { class: "empty-ic" }, icon(p.icon || "bot")), h("p", null, `${p.title} is not ready yet.`),
    h("p", { class: "muted" }, "This page is being built. It will show up here by itself when it is ready."));
}
function homeCardShell(p, content, open) {
  return h("section", { class: `home-card fam-${FAMILY[p.id] || "brain"}` }, h("h3", null, p.title), content,
    open === false ? null : h("button", { class: "btn secondary", onclick: () => go(p.id) }, `Open ${p.title}`));
}
async function renderHome(main) {
  const v = viewerOf();
  main.append(h("div", { class: "page" }, h("section", { class: "section" }, h("h2", { class: "hero" }, `Hello, ${v.name}.`),
    h("p", { class: "lead" }, `You are viewing as ${v.role_label}.`), h("p", { class: "muted" }, S.privacy))));
  const grid = h("div", { class: "home-grid" }, loading());
  main.firstChild.append(grid);
  const cards = [];
  for (const p of S.pages.filter((x) => x.id !== "home")) {
    const def = S.registry[p.id];
    let node = null;
    try { if (def && def.homeCard) node = await def.homeCard(ctxFor()); } catch (e) { node = null; }
    if (!def && !p.present) cards.push(homeCardShell(p, h("p", { class: "muted" }, "Not ready yet."), false));
    else if (node) cards.push(homeCardShell(p, node));
  }
  grid.replaceChildren(...cards);
  if (!cards.length) grid.replaceChildren(h("p", { class: "muted" }, "Nothing to show here yet."));
}

/* ---------- Approvals and Runs (built into the shell) ---------- */
function approvalCard(a) {
  const card = h("article", { class: "approval" });
  const done = (status, by, text) => card.replaceChildren(h("div", { class: `result ${status === "approved" ? "ok" : "no"}`, role: "status" },
    h("span", { class: "badge" }, icon(status === "approved" ? "check" : "x")),
    h("div", null, h("strong", null, status === "approved" ? `Approved by ${by}, done` : `Denied by ${by}`), h("p", { class: "muted" }, text || ""))));
  const decide = async (approve) => {
    const r = await api("/api/console/approvals/decide", { method: "POST", body: { approval_id: a.approval_id, approve } });
    if (!r.ok) { toast(r.error); return; }
    done(approve ? "approved" : "rejected", viewerOf().name, approve ? (r.executed && r.executed.result) || "Done." : "Nothing was done.");
  };
  if (a.status !== "pending") { done(a.status, a.decided_by || "someone", a.executed || ""); return card; }
  const args = Object.entries(a.args || {}).filter(([, v]) => typeof v !== "object").map(([k, v]) => `${k.replace(/_/g, " ")}: ${v}`).join(" · ");
  card.append(h("p", { class: "ask" }, `${a.agent_title} wants to do this.`), h("p", { class: "what" }, a.title || a.what),
    args ? h("p", { class: "muted small" }, args) : null, h("p", { class: "muted" }, a.why_held),
    h("div", { class: "actions" }, h("button", { class: "btn primary", onclick: () => decide(true) }, "Approve"),
      h("button", { class: "btn secondary", onclick: () => decide(false) }, "Deny"),
      h("button", { class: "link-btn", onclick: () => runStory(a.run_id) }, "See how this was made")));
  return card;
}
async function renderApprovals(main) {
  main.append(loading());
  const r = await api("/api/console/approvals");
  if (!r.ok) { main.replaceChildren(errorLine(r.error)); return; }
  const open = r.approvals.filter((a) => a.status === "pending"), closed = r.approvals.filter((a) => a.status !== "pending");
  main.replaceChildren(h("div", { class: "page" }, h("section", { class: "section" },
    open.length ? h("div", { class: "approval-list" }, open.map(approvalCard)) : h("p", { class: "lead" }, "Nothing waits for you."),
    closed.length ? [h("h3", null, "Decided"), h("div", { class: "approval-list" }, closed.map(approvalCard))] : null)));
}
async function renderRuns(main) {
  main.append(loading());
  const r = await api("/api/console/runs");
  if (!r.ok) { main.replaceChildren(errorLine(r.error)); return; }
  const s = r.summary;
  const stat = (n, label) => h("div", { class: "stat" }, h("strong", null, n), h("span", null, label));
  const rows = r.runs.map((x) => h("tr", { class: "click", tabindex: "0", onclick: () => runStory(x.run_id), onkeydown: (e) => { if (e.key === "Enter") runStory(x.run_id); } },
    h("td", null, h("span", { class: "agent-name" }, x.agent_title)), h("td", null, x.area_name), h("td", null, chip(x.status_label)),
    h("td", null, when(x.started_at)), h("td", { class: "num" }, money(x.cost_usd)), h("td", { class: "num" }, `${x.cache_hits} of ${x.model_calls}`)));
  main.replaceChildren(h("div", { class: "page" }, h("section", { class: "section" },
    h("div", { class: "stat-row" }, stat(s.run_count, "runs"), stat(s.model_calls, "model calls"), stat(s.cache_hits, "cache hits"), stat(money(s.total_cost_usd), "total cost")),
    r.runs.length ? h("div", { class: "tablewrap" }, h("table", null, h("thead", null, h("tr", null, ["Agent", "Area", "Result", "Started", "Cost", "Cache hits"].map((t, i) => h("th", { class: i > 3 ? "num" : "" }, t)))), h("tbody", null, rows)))
      : h("p", { class: "lead" }, "No runs yet. Go to the next day to start the timer runs."))));
}
const BUILTIN = { home: renderHome, approvals: renderApprovals, runs: renderRuns };
const BUILTIN_HOME = {
  approvals: async () => { const r = await api("/api/console/home"); return r.ok ? h("p", { class: "lead" }, r.pending_approvals ? `${r.pending_approvals} waiting for you.` : "Nothing waits for you.") : null; },
  runs: async () => { const r = await api("/api/console/runs"); return r.ok ? h("p", { class: "lead" }, `${r.summary.run_count} runs, ${money(r.summary.total_cost_usd)} spent.`) : null; },
};
for (const [id, fn] of Object.entries(BUILTIN_HOME)) S.registry[id] = { id, homeCard: fn, render: async (main) => BUILTIN[id](main) };

/* ---------- navigation and rendering ---------- */
function go(id, params) { location.hash = "#" + id + (params ? "?" + new URLSearchParams(params) : ""); }
function current() { const [id, qs] = location.hash.replace(/^#/, "").split("?"); return { id: id || "home", params: Object.fromEntries(new URLSearchParams(qs || "")) }; }
async function render() {
  const token = ++S.token, { id, params } = current();
  const p = S.pages.find((x) => x.id === id);
  closeDrawer();
  const main = $("#main"); main.replaceChildren();
  if (!p) { if (S.pages.length) go("home"); return; }
  $("#page-title").textContent = p.title; document.title = `${p.title} - Company OS`;
  document.querySelectorAll("#nav a").forEach((a) => a.toggleAttribute("aria-current", a.dataset.page === id) || a.removeAttribute("aria-current"));
  document.querySelectorAll("#nav a[aria-current]").forEach((a) => a.setAttribute("aria-current", "page"));
  const def = S.registry[id];
  try {
    if (id === "home") await renderHome(main);
    else if (BUILTIN[id]) await BUILTIN[id](main);
    else if (def && def.render) await def.render(main, { ...ctxFor(), params });
    else main.append(placeholder(p));
  } catch (e) { main.replaceChildren(errorLine("This page could not be drawn. " + (e && e.message ? e.message : ""))); }
  if (token === S.token) { closeRail(); }
}
function buildNav() {
  const nav = $("#nav"); nav.replaceChildren(...S.pages.map((p) => h("a", { href: "#" + p.id, "data-page": p.id }, icon(p.icon), h("span", null, p.title))));
}
function openRail() { $("#rail").classList.add("open"); $("#rail-scrim").classList.add("open"); $("#menu-btn").setAttribute("aria-expanded", "true"); }
function closeRail() { $("#rail").classList.remove("open"); $("#rail-scrim").classList.remove("open"); $("#menu-btn").setAttribute("aria-expanded", "false"); }

/* ---------- role switcher and demo controls ---------- */
function drawViewer() {
  const v = viewerOf();
  $("#viewer-initials").textContent = (v.name || "?")[0];
  $("#viewer-name").textContent = `${v.name} · ${v.role_label}`;
  $("#viewer-role").textContent = "Switch person";
  $("#admin-controls").hidden = v.role !== "admin";
}
function viewerMenu() {
  const menu = $("#viewer-menu"), btn = $("#viewer");
  const open = !menu.hidden;
  if (open) { menu.hidden = true; btn.setAttribute("aria-expanded", "false"); return; }
  menu.replaceChildren(...S.people.map((p) => h("button", { role: "menuitemradio", "aria-checked": String(p.person_id === S.viewer), onclick: () => { menu.hidden = true; btn.setAttribute("aria-expanded", "false"); switchTo(p.person_id); } },
    h("span", { class: "initials" }, p.name[0]), h("span", { class: "who" }, h("span", null, p.name), h("span", null, p.role_label)), p.person_id === S.viewer ? h("span", { class: "tick" }, icon("check")) : null)));
  const r = btn.getBoundingClientRect(); menu.style.top = r.bottom + 8 + "px"; menu.style.right = Math.max(16, innerWidth - r.right) + "px";
  menu.hidden = false; btn.setAttribute("aria-expanded", "true"); const first = menu.querySelector("button"); if (first) first.focus();
}
async function switchTo(personId) {
  S.viewer = personId; store.set("viewer", personId);
  const r = await api("/api/console/pages");
  if (!r.ok) { toast(r.error); return; }
  S.pages = r.pages; S.privacy = r.privacy;
  drawViewer(); buildNav(); await loadPlugins(); await refreshState();
  if (!S.pages.some((p) => p.id === current().id)) go("home"); else await render();
}
async function refreshState() {
  if (viewerOf().role !== "admin") return;
  const r = await api("/api/console/state");
  if (!r.ok) return;
  S.state = r;
  const d = r.today.split("-"); $("#date-pill").textContent = `${+d[2]} ${MONTHS[d[1] - 1]} ${d[0]}`;
  $("#pause").checked = !r.paused; $("#pause-label").textContent = r.paused ? "Agents paused" : "Agents on"; $("#banner").hidden = !r.paused;
}
async function control(path, okText) {
  const r = await api(path, { method: "POST" });
  if (!r.ok) { toast(r.error); return; }
  toast(okText(r)); await refreshState(); await render();
}

async function init() {
  $("#dark").checked = document.documentElement.dataset.theme === "dark";
  $("#dark").addEventListener("change", (e) => { document.documentElement.dataset.theme = e.target.checked ? "dark" : "light"; store.set("theme", e.target.checked ? "dark" : "light"); });
  $("#viewer").addEventListener("click", viewerMenu);
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") { closeDrawer(); const m = $("#viewer-menu"); if (!m.hidden) { m.hidden = true; $("#viewer").focus(); } closeRail(); } });
  document.addEventListener("click", (e) => { const m = $("#viewer-menu"); if (!m.hidden && !m.contains(e.target) && !$("#viewer").contains(e.target)) m.hidden = true; });
  $("#scrim").addEventListener("click", closeDrawer);
  $("#rail-scrim").addEventListener("click", closeRail);
  $("#menu-btn").append(icon("menu")); $("#menu-btn").addEventListener("click", openRail);
  document.querySelectorAll("[data-icon]").forEach((el) => { if (!el.firstChild) el.append(icon(el.dataset.icon)); });
  $("#next-day").addEventListener("click", () => control("/api/console/next_day", (r) => `It is now ${r.now.slice(0, 10)}. ${r.fired.length} runs started.`));
  $("#pause").addEventListener("change", (e) => control(e.target.checked ? "/api/console/resume" : "/api/console/pause", (r) => (r.paused ? "Agents are paused." : "Agents are on.")));
  $("#reset").addEventListener("click", () => { if (confirm("Wipe this demo and start again?")) control("/api/console/reset", () => "The demo is reset."); });
  window.addEventListener("hashchange", render);
  const people = await api("/api/console/people");
  if (!people.ok) { $("#main").append(errorLine(people.error)); return; }
  S.people = people.people;
  const saved = store.get("viewer");
  await switchTo(S.people.some((p) => p.person_id === saved) ? saved : S.people[0].person_id);
}
init();
})();
