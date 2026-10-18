"use strict";
/* Company OS console. Plain JavaScript, no libraries. Design rules: ../DESIGN.md */

/* ---------- small helpers ---------- */
const $ = (sel, root = document) => root.querySelector(sel);
const S = { state: null, people: [], agents: [], titles: {}, viewAs: "P07", lastRunId: null, dirty: false, token: 0, memArea: null, dept: "finance", inboxAgent: "", perm: null };
const reduced = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const human = (t) => String(t || "").replace(/_/g, " ");
const lowerFirst = (t) => String(t || "").replace(/^./, (c) => c.toLowerCase());
const plural = (n, one, many) => `${n} ${n === 1 ? one : (many || one + "s")}`;

function h(tag, attrs, ...kids) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v === null || v === undefined || v === false) continue;
    if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
    else if (k === "class") el.className = v;
    else el.setAttribute(k, v === true ? "" : v);
  }
  const add = (kid) => {
    if (kid === null || kid === undefined || kid === false) return;
    if (Array.isArray(kid)) kid.forEach(add);
    else el.append(kid instanceof Node ? kid : document.createTextNode(String(kid)));
  };
  kids.forEach(add);
  return el;
}

/* ---------- icons: inline SVG, 1.75px stroke, Lucide style ---------- */
const ICONS = {
  calendar: '<rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/>',
  pulse: '<path d="M22 12h-4l-3 9L9 3l-3 9H2"/>',
  coin: '<path d="M6 3h12M6 8h12M6 13l8.5 8M6 13h3M9 13c6.667 0 6.667-10 0-10"/>',
  store: '<path d="M3 9l1.5-5h15L21 9"/><path d="M3 9a3 3 0 0 0 6 0 3 3 0 0 0 6 0 3 3 0 0 0 6 0"/><path d="M5 12v8h14v-8"/><path d="M10 20v-5h4v5"/>',
  users: '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/>',
  branch: '<path d="M6 3v12"/><circle cx="18" cy="6" r="3"/><circle cx="6" cy="18" r="3"/><path d="M18 9a9 9 0 0 1-9 9"/>',
  key: '<circle cx="7.5" cy="15.5" r="4.5"/><path d="M10.7 12.3L21 2M16 7l3 3M14 9l2 2"/>',
  bot: '<rect x="4" y="8" width="16" height="12" rx="3"/><path d="M12 8V4M9 14h.01M15 14h.01"/>',
  check: '<path d="M20 6L9 17l-5-5"/>',
  x: '<path d="M18 6L6 18M6 6l12 12"/>',
  pause: '<rect x="6" y="4" width="4" height="16" rx="1"/><rect x="14" y="4" width="4" height="16" rx="1"/>',
  flag: '<path d="M4 22V4"/><path d="M4 4h13l-2 4 2 4H4"/>',
  inbox: '<path d="M22 12h-6l-2 3h-4l-2-3H2"/><path d="M5.45 5.11L2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z"/>',
  home: '<path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><path d="M9 22V12h6v10"/>',
  book: '<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>',
  settings: '<path d="M4 21v-7M4 10V3M12 21v-9M12 8V3M20 21v-5M20 12V3M1 14h6M9 8h6M17 16h6"/>',
  chevron: '<path d="M9 18l6-6-6-6"/>',
  play: '<path d="M6 4l14 8-14 8z"/>',
  search: '<circle cx="11" cy="11" r="8"/><path d="M21 21l-4.3-4.3"/>',
  menu: '<path d="M3 6h18M3 12h18M3 18h18"/>',
  moon: '<path d="M21 12.8A9 9 0 1 1 11.2 3 7 7 0 0 0 21 12.8z"/>',
  minus: '<path d="M5 12h14"/>',
  shield: '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>',
  message: '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>',
  building: '<rect x="4" y="2" width="16" height="20" rx="2"/><path d="M9 22v-4h6v4M8 6h.01M12 6h.01M16 6h.01M8 10h.01M12 10h.01M16 10h.01M8 14h.01M12 14h.01M16 14h.01"/>',
  list: '<path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01"/>',
  lock: '<rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>',
  info: '<circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/>',
  save: '<path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><path d="M17 21v-8H7v8M7 3v5h8"/>',
  trend: '<path d="M3 3v18h18"/><path d="M7 15l4-4 3 3 5-6"/>',
  alert: '<circle cx="12" cy="12" r="10"/><path d="M12 8v4M12 16h.01"/>',
  pie: '<path d="M21.21 15.89A10 10 0 1 1 8 2.83"/><path d="M22 12A10 10 0 0 0 12 2v10z"/>',
};
function icon(name) {
  const t = document.createElement("template");
  t.innerHTML = `<svg class="i" viewBox="0 0 24 24" aria-hidden="true" focusable="false">${ICONS[name] || ICONS.bot}</svg>`;
  return t.content.firstChild;
}
function fillIcons(root = document) { root.querySelectorAll("[data-icon]").forEach((el) => { if (!el.firstChild) el.append(icon(el.dataset.icon)); }); }

/* ---------- agents: avatar, colour, status chips ---------- */
const AGENT_ICON = { meeting_prep: "calendar", finance_watch: "coin", spend_advisor: "pie" };
const agentClass = (agent) => "a-" + (AGENT_ICON[agent] ? agent : "unknown");
const titleOf = (agent) => S.titles[agent] || (human(agent).charAt(0).toUpperCase() + human(agent).slice(1));
function avatar(agent, size = 48) { return h("span", { class: `av av-${size} ${agentClass(agent)}`, "aria-hidden": "true" }, icon(AGENT_ICON[agent] || "bot")); }

const STATUS = {
  done: ["ok", "check", "Done"], approved: ["ok", "check", "Approved"], allowed: ["ok", "check", "Allowed"],
  held: ["wait", "pause", "Waiting for approval"], pending: ["wait", "pause", "Waiting for approval"],
  quiet: ["calm", "moon", "Quiet"], flag: ["warn", "flag", "Flag"],
  refused: ["stop", "x", "Refused"], failed: ["stop", "x", "Stopped"], rejected: ["stop", "x", "Denied"], denied: ["stop", "x", "Denied"],
  running: ["calm", "play", "Running"],
};
function chip(key, text) {
  const [kind, ic, word] = STATUS[key] || ["calm", "minus", human(key)];
  return h("span", { class: `chip ${kind}` }, icon(ic), text || word);
}
const kindChip = (kind, ic, text) => h("span", { class: `chip ${kind}` }, icon(ic), text);

/* ---------- formatting ---------- */
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const DAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
function parts(iso) { const m = String(iso || "").match(/^(\d{4})-(\d{2})-(\d{2})(?:T(\d{2}):(\d{2}))?/); return m ? m.slice(1).map((x) => (x === undefined ? null : +x)) : null; }
function when(iso) {
  const p = parts(iso); if (!p) return "";
  const [, mo, d, hh, mm] = p;
  const date = `${d} ${MONTHS[mo - 1]}`;
  if (hh === null) return date;
  return `${date}, ${hh % 12 || 12}:${String(mm).padStart(2, "0")} ${hh < 12 ? "AM" : "PM"}`;
}
function datePill(iso) { const p = parts(iso); if (!p) return ""; const dt = new Date(p[0], p[1] - 1, p[2]); return `${DAYS[dt.getDay()]} ${p[2]} ${MONTHS[p[1] - 1]} ${p[0]}`; }
const money = (v) => "$" + (v || 0).toFixed(4);
const person = (id) => S.people.find((p) => p.person_id === id);
const personName = (id) => (person(id) || {}).name || id;
const firstName = (n) => String(n || "").split(" ")[0];
const areaName = (id) => ((S.state.areas || []).find((a) => a.area_id === id) || {}).name || id;
const initialsOf = (n) => String(n || "?").split(" ").map((w) => w[0]).slice(0, 2).join("").toUpperCase();

async function api(path, body) {
  const opts = body === undefined ? {} : { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) };
  const res = await fetch(path, opts);
  try { return await res.json(); } catch (e) { return { ok: false, error: "The console did not answer. Is it still running?" }; }
}

let toastTimer;
function toast(text) {
  const t = $("#toast"); t.textContent = text; t.hidden = false;
  clearTimeout(toastTimer); toastTimer = setTimeout(() => { t.hidden = true; }, 5000);
}
async function loadPerm() {
  if (!S.perm || S.perm.person_id !== S.viewAs) S.perm = await api("/api/permissions?person=" + encodeURIComponent(S.viewAs));
  return S.perm;
}
const mayStart = (agent) => !!(S.perm && S.perm.ok && S.perm.agents.includes(agent));
const mayStartFor = (agent, area) => mayStart(agent) && (S.perm.agent_areas[agent] || []).includes(area);
const loading = (text = "Loading") => h("p", { class: "spinner" }, text);
function errorLine(text) { return h("p", { class: "err", role: "alert" }, icon("alert"), text); }

function emptyState(ic, text, buttonLabel, onclick) {
  return h("div", { class: "empty" }, h("span", { class: "empty-ic" }, icon(ic)), h("p", null, text),
    buttonLabel ? h("button", { class: "btn primary", onclick }, buttonLabel) : null);
}

/* ---------- letters ---------- */
function letterBody(text) {
  const body = h("div", { class: "letter-body clamped" });
  let list = null, item = null;
  const label = (line) => {
    const m = line.match(/^(\s*)(Evidence|Why it matters|Next step):\s*(.*)$/);
    return m ? [h("strong", null, m[2] + ": "), m[3]] : [line.trim()];
  };
  String(text || "").split("\n").forEach((raw) => {
    if (!raw.trim()) return;
    const n = raw.match(/^\s*(\d+)\.\s+(.*)$/);
    if (n) {
      if (!list) { list = h("ol", { start: n[1] }); body.append(list); }
      item = h("li", null, label(n[2]));
      list.append(item);
    } else if (item && /^\s+/.test(raw)) {
      item.append(h("div", null, label(raw)));
    } else {
      list = null; item = null;
      body.append(h("p", null, label(raw)));
    }
  });
  return body;
}

function letter(m, opts = {}) {
  const kind = String(m.kind || "note").split("_").pop();
  const body = letterBody(m.text);
  const foot = h("div", { class: "letter-foot" });
  if (opts.runLink && m.run_id) foot.append(h("button", { class: "link-btn", onclick: () => openRun(m.run_id) }, "See how this was made"));
  return h("article", { class: `letter ${agentClass(m.agent)}` },
    h("div", { class: "letter-head" }, avatar(m.agent, 32),
      h("div", { class: "who" }, h("div", null, h("span", { class: "agent-name" }, m.agent_title || titleOf(m.agent)), h("span", { class: "to-long" }, ` → ${m.to_name || personName(m.to_person_id)} · ${kind}`)),
        h("div", { class: "to-short" }, `to ${m.to_name || personName(m.to_person_id)}, ${kind}${m.created_at ? ", " + when(m.created_at) : ""}`)),
      h("time", null, when(m.created_at))),
    body, foot);
}
function fitLetters(root) {
  root.querySelectorAll(".letter").forEach((l) => {
    const body = $(".letter-body.clamped", l);
    if (!body || l.dataset.fit) return;
    l.dataset.fit = "1";
    if (body.scrollHeight <= body.clientHeight + 2) { body.classList.remove("clamped"); return; }
    const btn = h("button", { class: "link-btn", "aria-expanded": "false", onclick: () => {
      const open = body.classList.toggle("clamped") === false;
      btn.textContent = open ? "Show less" : "Show the full message"; btn.setAttribute("aria-expanded", String(open));
    } }, "Show the full message");
    $(".letter-foot", l).prepend(btn);
  });
}

/* ---------- approvals ---------- */
function resultView(status, by, executed) {
  const ok = status === "approved";
  const text = executed && executed.result ? executed.result : "";
  return h("div", { class: `result ${ok ? "ok" : "no"}`, role: "status" },
    h("span", { class: "badge" }, icon(ok ? "check" : "x")),
    h("div", null, h("strong", null, ok ? `Approved by ${by}, done` : `Denied by ${by}`),
      h("p", { class: "muted" }, ok ? (text || "The follow-up was written to company memory.") : "Nothing was written.")));
}

function approvalCard(a) {
  const card = h("article", { class: `approval ${agentClass(a.agent)}` });
  const pendingView = () => {
    const approve = h("button", { class: "btn primary", onclick: () => decide(true) }, "Approve");
    const deny = h("button", { class: "btn secondary", onclick: () => decide(false) }, "Deny");
    const blocked = a.can_decide === false;
    if (blocked) { approve.disabled = true; deny.disabled = true; }
    const msg = h("div");
    const decide = async (yes) => {
      approve.disabled = deny.disabled = true; msg.replaceChildren();
      const d = await api("/api/approvals/decide", { approval_id: a.approval_id, approve: yes, by_person_id: S.viewAs });
      if (!d.ok) { approve.disabled = deny.disabled = false; msg.replaceChildren(errorLine(d.error)); return; }
      const by = d.approval.decided_by || personName(S.viewAs);
      const before = card.offsetHeight;
      if (!reduced()) card.style.height = before + "px";
      card.replaceChildren(resultView(d.status, by, d.executed));
      card.classList.add(yes ? "done-ok" : "done-no");
      if (!reduced()) {
        const target = card.scrollHeight;
        requestAnimationFrame(() => { card.style.height = target + "px"; });
        setTimeout(() => { card.style.height = ""; }, 400);
      }
      S.dirty = true; refreshTop();
    };
    return [
      h("div", { class: "row" }, avatar(a.agent, 32), h("p", { class: "ask" }, h("span", { class: "agent-name" }, a.agent_title), ` wants to ${lowerFirst(a.what)}.`)),
      a.title ? h("p", { class: "what" }, a.title) : null,
      h("p", { class: "muted" }, `Why it needs you: ${a.why_held} About ${areaName(a.area_id)}. Owner: ${a.owner}.`),
      h("div", { class: "actions" }, approve, deny, blocked ? h("p", { class: "cannot" }, icon("lock"), a.cannot_because) : null), msg];
  };
  if (a.status === "pending") card.append(...pendingView());
  else {
    card.classList.add(a.status === "approved" ? "done-ok" : "done-no");
    card.append(resultView(a.status, a.decided_by || "someone", a.executed ? { result: a.executed } : null));
  }
  return card;
}

/* ---------- the recorded real Claude version ---------- */
async function loadReal() {
  if (S.realLoaded) return S.real;
  const r = await api("/api/real_samples");
  S.real = r && r.available ? r : null; S.realLoaded = true;
  return S.real;
}
function realToggle(agent) {
  const sample = S.real && S.real.samples[agent];
  if (!sample) return null;
  const panel = h("div", { class: "real-panel stack", hidden: true });
  const btn = h("button", { class: "btn secondary", "aria-expanded": "false" }, "See the real Claude version");
  btn.onclick = () => {
    const open = panel.hidden; panel.hidden = !open;
    btn.setAttribute("aria-expanded", String(open)); btn.textContent = open ? "Hide the real Claude version" : "See the real Claude version";
    if (open && !panel.dataset.built) { panel.dataset.built = "1"; panel.append(...realBody(sample)); fitLetters(panel); }
  };
  return h("div", { class: "stack real-toggle" }, btn, panel);
}
function realBody(sample) {
  const nodes = [h("p", { class: "note" }, icon("info"), `Recorded once with real Claude (${String(S.real.model).replace(/^.*\((.+)\)$/, "$1")}) on ${longDate(S.real.generated_at)}; the steps and checks are the same, only the wording comes from the model.`)];
  const letters = sample.letters || [];
  if (sample.status && sample.status !== "done") nodes.push(h("div", null, chip(sample.status === "held" ? "held" : sample.status), sample.reason ? h("p", { class: "muted" }, sample.reason) : null));
  if (letters.length) nodes.push(h("h3", null, letters.length === 1 ? "The letter, in real Claude's words" : "The letters, in real Claude's words"),
    h("div", { class: "letters" }, letters.map((m) => letter({ ...m, agent_title: titleOf(m.agent), to_name: m.to_name }))));
  if (sample.walkthrough) nodes.push(h("h3", null, "How it went"), timeline(sample.walkthrough));
  return nodes;
}

/* ---------- drawer with the run story ---------- */
let drawerOpener = null, drawerRunId = null;
function drawerOpen() { return $("#drawer").classList.contains("open"); }
function showDrawer(nodes) {
  const dr = $("#drawer"), body = $("#drawer-body");
  body.replaceChildren(...nodes);
  if (!drawerOpen()) {
    drawerOpener = document.activeElement;
    dr.removeAttribute("inert"); dr.classList.add("open"); $("#scrim").classList.add("open");
  }
  fitLetters(dr);
  const close = $("#drawer-close"); if (close) close.focus({ preventScroll: true });
  dr.scrollTop = 0;
}
function closeDrawer() {
  if (!drawerOpen()) return;
  const dr = $("#drawer");
  dr.classList.remove("open"); dr.setAttribute("inert", ""); $("#scrim").classList.remove("open");
  if (/^#runs\//.test(location.hash)) history.replaceState(null, "", "#runs");
  drawerRunId = null;
  const back = drawerOpener && document.contains(drawerOpener) ? drawerOpener : $("#main");
  if (back) back.focus({ preventScroll: true });
  if (S.dirty) { S.dirty = false; renderPage(true); }
}

const READ_TITLE = { finance_watch: "Read the books", meeting_prep: "Read the meeting notes", spend_advisor: "Read the books and the trips" };
const STEP_ICON = ["book", "search", "message", "shield", "inbox", "save"];
const STATE_KIND = { ok: "ok", held: "wait", quiet: "calm", skipped: "calm", refused: "stop", failed: "stop" };

function verdictChip(v) {
  if (v.verdict === "denied") return kindChip("stop", "x", v.reason ? `${v.what}: ${v.reason}` : `${v.what} was denied`);
  if (v.verdict === "held") return kindChip("wait", "pause", `${v.what}: waits for a person`);
  return kindChip("ok", "check", v.what);
}

function storyStep(s, agent) {
  const items = s.items || [];
  const out = { title: "", kind: STATE_KIND[s.state] || "ok", detail: [] };
  const list = (rows) => h("ul", null, rows.map((r) => h("li", null, r)));
  switch (s.n) {
    case 1: {
      out.title = READ_TITLE[agent] || "Read the data";
      const bad = items.filter((i) => i.verdict !== "allowed");
      out.detail.push(h("p", null, `${plural(items.length, "lookup")}, each one checked before it ran.`));
      if (bad.length) out.detail.push(h("div", { class: "chip-row" }, bad.map((i) => verdictChip({ what: i.text, verdict: i.verdict, reason: i.note }))));
      if (items.length) out.detail.push(h("details", null, h("summary", null, "See what it read"), list(items.map((i) => i.text + (i.note && i.verdict === "allowed" ? ` (${i.note})` : "")))));
      break;
    }
    case 2:
      if (s.state === "quiet") { out.title = "Nothing new today"; out.detail.push(h("p", null, "Nothing needed a look.")); }
      else if (items.length) { out.title = `Found ${plural(items.length, "thing")} to look at`; out.detail.push(list(items.map((i) => i.text + (i.note ? `. ${i.note}` : "")))); }
      else { out.title = "Got the facts ready"; out.detail.push(h("p", null, "The code gathered and counted the facts, so the numbers are exact.")); }
      break;
    case 3:
      if (s.state === "quiet") { out.title = "Nothing new, so no model call"; out.detail.push(h("p", null, "That keeps the cost at zero.")); break; }
      out.title = "Decided what to say";
      if ((s.sentences || []).length) {
        out.detail.push(list(s.sentences.slice(0, 5)));
        if (s.sentences.length > 5) out.detail.push(h("details", null, h("summary", null, `Show ${s.sentences.length - 5} more`), list(s.sentences.slice(5))));
      } else if ((s.lines || []).length) out.detail.push(h("p", null, s.lines.join(" ")));
      if (s.meta) out.detail.push(h("details", null, h("summary", null, "How it ran"), h("p", { class: "muted" }, s.meta)));
      break;
    case 4:
      if (s.state === "refused") out.title = "Stopped at the door";
      else if (s.state === "failed") out.title = "The check found a problem, so nothing was sent";
      else out.title = "Checked before sending";
      if (s.state === "failed") out.detail.push(list(s.lines));
      if ((s.verdicts || []).length) out.detail.push(h("div", { class: "chip-row" }, s.verdicts.map(verdictChip)));
      if ((s.lines || []).some((l) => /Safety check passed/.test(l))) out.detail.push(h("p", null, "Every number and name matched what the code found."));
      break;
    case 5: {
      const told = items.filter((i) => i.verdict === "allowed" && i.message).map((i) => (i.text.match(/^Told (.+?) in private/) || [])[1]).filter(Boolean);
      const held = items.filter((i) => i.verdict === "held");
      const blocked = items.filter((i) => i.verdict === "denied");
      const bits = [];
      if (told.length) bits.push(`Told ${told.join(" and ")}`);
      if (held.length) bits.push(`${plural(held.length, "action")} ${held.length === 1 ? "waits" : "wait"} for approval`);
      out.title = bits.length ? bits.join(", ") : (blocked.length ? "A message was blocked" : "Nobody needed telling");
      if (blocked.length) out.kind = "stop";
      held.forEach((i) => out.detail.push(h("p", null, i.text.replace(/^Follow-up waiting for approval: /, "Waiting for approval: "))));
      if (blocked.length) out.detail.push(h("div", { class: "chip-row" }, blocked.map((i) => verdictChip({ what: i.text, verdict: "denied", reason: i.note }))));
      break;
    }
    default:
      out.title = "Saved to memory";
      (s.lines || []).forEach((l) => out.detail.push(h("p", null, l)));
      if (items.length) out.detail.push(list(items.map((i) => i.text + (i.note ? `. ${i.note}` : ""))));
  }
  return out;
}

function timeline(walk) {
  let steps = walk.steps.filter((s) => s.state !== "skipped" || s.n === 5);
  if (walk.outcome === "quiet") steps = walk.steps.filter((s) => s.n <= 3);
  if (walk.outcome === "refused") steps = walk.steps.filter((s) => s.n === 4);
  const ol = h("ol", { class: "timeline" });
  steps.forEach((s) => {
    const v = storyStep(s, walk.agent);
    const mark = v.kind === "stop" ? "x" : v.kind === "wait" ? "pause" : STEP_ICON[s.n - 1];
    ol.append(h("li", { class: "step" }, h("span", { class: `dot ${v.kind}` }, icon(mark)),
      h("div", null, h("h4", null, v.title), v.detail.length ? h("div", { class: "detail" }, v.detail) : null)));
  });
  return ol;
}

async function renderRun(p, understood) {
  const run = p.run, walk = p.walkthrough;
  S.lastRunId = run.run_id; drawerRunId = run.run_id;
  const who = run.caller_id === "system" ? `Started by the ${run.trigger_kind}` : `Asked by ${run.caller_name}`;
  const head = h("div", { class: "drawer-head" }, avatar(run.agent, 48),
    h("div", { class: "titles" }, h("h2", { id: "drawer-title" }, run.agent_title),
      h("p", { class: "small muted" }, `${who} · ${when(run.started_at)} · ${run.area_name}`),
      h("div", null, chip(run.status_label))),
    h("button", { class: "icon-btn", id: "drawer-close", "aria-label": "Close", onclick: closeDrawer }, icon("x")));
  const sections = [head, h("section", { class: `drawer-sec ${agentClass(run.agent)}` },
    h("p", { class: "headline" }, walk.headline), understood ? h("p", { class: "muted" }, `I understood: ${understood}`) : null,
    h("h3", null, "How it went"), timeline(walk))];
  const msgs = p.messages || [];
  if (msgs.length) sections.push(h("section", { class: "drawer-sec" }, h("h3", null, msgs.length === 1 ? "The letter it wrote" : "The letters it wrote"),
    h("div", { class: "letters" }, msgs.map((m) => letter({ ...m, agent_title: titleOf(m.agent) })))));
  await loadReal();
  const realNode = realToggle(run.agent);
  if (realNode) sections.push(h("section", { class: "drawer-sec" }, realNode));
  const ap = await api("/api/approvals?person=" + encodeURIComponent(S.viewAs));
  const mine = (ap.approvals || []).filter((a) => a.run_id === run.run_id);
  if (mine.length) sections.push(h("section", { class: "drawer-sec" }, h("h3", null, "Needs a decision"), h("div", { class: "approval-list" }, mine.map(approvalCard))));
  showDrawer(sections);
}

async function openRun(id) {
  showDrawer([h("div", { class: "drawer-head" }, h("h2", { id: "drawer-title" }, "Loading the run"),
    h("button", { class: "icon-btn", id: "drawer-close", "aria-label": "Close", onclick: closeDrawer }, icon("x"))), h("div", { class: "drawer-sec" }, loading())]);
  const r = await api("/api/run?id=" + encodeURIComponent(id));
  if (!r.ok) { showDrawer([h("div", { class: "drawer-head" }, h("h2", { id: "drawer-title" }, "Run not found"), h("button", { class: "icon-btn", id: "drawer-close", "aria-label": "Close", onclick: closeDrawer }, icon("x"))), h("div", { class: "drawer-sec" }, errorLine(r.error))]); return; }
  await renderRun(r);
}

async function showRunPayload(p, understood) {
  if (!p.ok) { toast(p.error); return false; }
  await renderRun(p, understood);
  S.dirty = true; refreshTop();
  return true;
}

async function runScenario(s, btn) {
  const label = btn.textContent; btn.disabled = true; btn.textContent = "Running";
  try { await showRunPayload(await api("/api/scenarios/run", { id: s.id, person_id: S.viewAs })); }
  finally { btn.disabled = false; btn.textContent = label; }
}

/* ---------- shared pieces ---------- */
function scenarioTile(s, extra) {
  const btn = h("button", { class: "btn secondary" }, "Try it");
  btn.onclick = () => runScenario(s, btn);
  return h("div", { class: `tile ${agentClass(s.agent)}` },
    h("div", { class: "head" }, avatar(s.agent, 32), h("h4", null, s.title)),
    h("p", null, s.situation), extra || null, btn);
}


/* ---------- Ask finance: a question box for people who may start the spend advisor ---------- */
const FINANCE_PICKS = ["Travel this quarter", "Where can we save?", "Cost by category"];
function askFinanceBox() {
  if (!mayStartFor("spend_advisor", "devx-internal")) return null;
  const input = h("input", { type: "text", id: "finance-input", maxlength: "500", "aria-label": "Your finance question", placeholder: "Ask about company spending, for example: where is our travel money going?" });
  const out = h("div", { role: "status" });
  const picks = h("div", { class: "quick-picks" });
  const lock = (on) => { box.querySelectorAll("button").forEach((b) => { b.disabled = on; }); };
  const go = async (text) => {
    if (!String(text).trim()) { out.replaceChildren(errorLine("Type a question first, for example: where is our travel money going?")); return; }
    out.replaceChildren(loading("Asking finance")); lock(true);
    try {
      const p = await api("/api/finance/ask", { person_id: S.viewAs, text });
      if (!p.ok) { out.replaceChildren(errorLine(p.error)); return; }
      out.replaceChildren(); await showRunPayload(p);
    } finally { lock(false); }
  };
  FINANCE_PICKS.forEach((label) => picks.append(h("button", { class: "quick-pick", type: "button", onclick: () => { input.value = label; go(label); } }, label)));
  input.addEventListener("keydown", (e) => { if (e.key === "Enter") go(input.value); });
  const box = h("section", { class: `section ask-finance ${agentClass("spend_advisor")}`, "aria-labelledby": "h-ask-finance" },
    h("h2", { id: "h-ask-finance" }, "Ask finance"),
    h("p", { class: "muted measure" }, `Asking as ${personName(S.viewAs)}. The answer comes back as a private letter, and the run story shows how it was worked out.`),
    h("div", { class: "ask-box" }, input, h("button", { class: "btn primary", onclick: () => go(input.value) }, "Ask finance")), picks, out);
  return box;
}

/* ---------- pages ---------- */
const pages = {};
const TITLES = { today: "Today", agents: "Agents", departments: "Departments", inbox: "Inbox", approvals: "Approvals", runs: "Runs", memory: "Company memory" };
const NAV = [["today", "home"], ["agents", "bot"], ["departments", "building"], ["inbox", "inbox"], ["approvals", "check"], ["runs", "list"], ["memory", "book"]];
const ALIAS = { home: "today", ask: "today" };

pages.today = async (main) => {
  const t = await api("/api/today?person=" + encodeURIComponent(S.viewAs));
  if (!t.ok) return main.append(errorLine(t.error));
  const n = t.needs_you.length;
  const page = h("div", { class: "page" });
  page.append(h("div", null, h("h2", { class: "hero" }, `Good ${t.part_of_day}, ${firstName(t.person.name)}.`),
    h("p", { class: "status-line" }, n ? `${plural(n, "thing")} ${n === 1 ? "needs" : "need"} you.` : "Nothing needs you right now.")));
  const financeBox = askFinanceBox();
  if (financeBox) page.append(financeBox);

  let hidden = false; try { hidden = localStorage.getItem("tourHidden") === "1"; } catch (e) { /* ignore */ }
  if (!hidden) {
    const steps = h("ol");
    const tour = h("section", { class: "tour", "aria-label": "Tour" },
      h("div", { class: "row between" }, h("p", null, h("strong", null, "New here? "), "Take the 5-step tour."),
        h("div", { class: "row" }, h("button", { class: "btn secondary", "aria-expanded": "false", onclick: (e) => {
          const open = steps.hidden; steps.hidden = !open; e.currentTarget.setAttribute("aria-expanded", String(open)); e.currentTarget.textContent = open ? "Hide the steps" : "Start the tour";
        } }, "Start the tour"),
        h("button", { class: "text-btn", onclick: () => { try { localStorage.setItem("tourHidden", "1"); } catch (e) { /* ignore */ } tour.remove(); } }, "Don't show again"))), steps);
    steps.hidden = true;
    const step = (title, text, label, fn) => steps.append(h("li", null, h("strong", null, title), h("div", null, h("p", { class: "muted" }, text), h("button", { class: "btn secondary", onclick: fn }, label))));
    const first = t.picks[0];
    if (first) step("Run an agent", first.situation, `Run: ${first.title}`, () => runScenario(first, { textContent: "", disabled: false }));
    step("See how it worked", "Every run is told as a short story: what it read, what it found, what it decided, what was checked.", "Open the last run", () => { if (S.lastRunId) openRun(S.lastRunId); else toast("Run an agent first (step 1)."); });
    step("Read the letter", "Anjali, the finance lead, gets the finding in private.", "Open Anjali's inbox", () => { setViewAs("P07"); location.hash = "inbox"; });
    step("Approve the follow-up", "The agent proposed a follow-up. It waits for a person. Try it as Anjali, then as an engineer to see the refusal.", "Open approvals", () => { setViewAs("P07"); location.hash = "approvals"; });
    step("Go to the next day", "The timer and calendar start runs for every agent.", "Go to next day", nextDay);
    page.append(tour);
  }

  const need = h("section", { class: "section", "aria-labelledby": "h-need" }, h("h2", { id: "h-need" }, "Things that need you"));
  if (n) need.append(h("div", { class: "approval-list" }, t.needs_you.map(approvalCard)));
  else {
    const first = t.picks[0];
    need.append(h("p", { class: "calm-line" }, h("span", { class: "muted" }, "Nothing is waiting for you."),
      first ? h("button", { class: "btn secondary", onclick: () => runScenario(first, { textContent: "", disabled: false }) }, `Try: ${first.title}`) : null));
  }
  page.append(need);

  const feed = h("section", { class: "section", "aria-labelledby": "h-feed" }, h("h2", { id: "h-feed" }, "What your agents did"));
  if (t.feed.length) feed.append(h("div", { class: "feed" }, t.feed.map((f) => h("button", { class: `feed-row ${agentClass(f.agent)}`, onclick: () => openRun(f.run_id) },
    avatar(f.agent, 32),
    h("span", { class: "text" }, h("span", { class: "agent-name" }, f.agent_title), f.line.slice(f.agent_title.length)),
    chip(f.status_label), h("time", null, when(f.started_at)), icon("chevron")))));
  else feed.append(emptyState("pulse", "Your agents have not done anything yet. Move the date forward and the timer starts their daily runs.", "Go to next day", nextDay));
  page.append(feed);

  if (t.picks.length) page.append(h("section", { class: "section", "aria-labelledby": "h-try" }, h("h2", { id: "h-try" }, "Try a scenario"),
    h("div", { class: "tiles" }, t.picks.slice(0, 6).map((s) => scenarioTile(s)))));

  if (S.perm.can_ask_in_words) {
  const input = h("input", { type: "text", placeholder: "prep me for EV113", "aria-label": "Your request", id: "ask-input" });
  const out = h("div");
  const go = async () => {
    if (!input.value.trim()) { out.replaceChildren(errorLine("Type a request first, for example: prep me for EV113.")); return; }
    out.replaceChildren(loading("Asking"));
    const p = await api("/api/ask", { text: input.value, caller_id: S.viewAs });
    if (!p.ok) { out.replaceChildren(errorLine(p.error)); return; }
    out.replaceChildren(); await showRunPayload(p, p.understood);
  };
  input.addEventListener("keydown", (e) => { if (e.key === "Enter") go(); });
  page.append(h("section", { class: "section", "aria-labelledby": "h-ask" }, h("h2", { id: "h-ask" }, "Ask in your own words"),
    h("p", { class: "muted measure" }, `Asking as ${t.person.name}. Today the system understands requests like "prep me for EV113". If a request is refused, you will see why.`),
    h("div", { class: "ask-box" }, input, h("button", { class: "btn primary", onclick: go }, "Ask")), out));
  }
  main.append(page);
};

pages.agents = async (main) => {
  const [data, t] = await Promise.all([api("/api/agents"), api("/api/today?person=" + encodeURIComponent(S.viewAs))]);
  const status = (t && t.agent_status) || {};
  await loadReal();
  const page = h("div", { class: "page" }, h("p", { class: "lead" }, "Meet your AI colleagues. Each one has one job, a clear list of who it tells and a short list of things it never does. You see the ones you may start."));
  const grid = h("div", { class: "profiles" });
  const mine = data.agents.filter((a) => mayStart(a.agent));
  if (!mine.length) {
    const name = personName(S.viewAs);
    return main.append(h("div", { class: "page" }, h("div", { class: "empty" }, h("span", { class: "empty-ic" }, icon("bot")),
      h("p", null, `${name} does not start agents directly; agents send them letters.`),
      h("button", { class: "btn primary", onclick: () => { location.hash = "inbox"; } }, "Open the inbox"))));
  }
  mine.forEach((a) => {
    const st = status[a.agent] || { kind: a.available ? "calm" : "calm", text: a.available ? "Ready" : "Being built" };
    const stIcon = { ok: "check", wait: "pause", warn: "flag", stop: "x", calm: "moon" }[st.kind];
    const card = h("section", { class: `profile ${agentClass(a.agent)}`, "aria-labelledby": "ag-" + a.agent },
      h("div", { class: "profile-head" }, avatar(a.agent, 88),
        h("div", { class: "stack" }, h("h3", { id: "ag-" + a.agent }, a.title), a.department ? h("p", { class: "muted" }, a.department) : null,
          h("div", null, kindChip(st.kind, stIcon, st.text)))),
      a.summary ? h("p", null, a.summary) : null);
    const dl = h("dl");
    const sec = (label, node) => dl.append(h("dt", null, label), h("dd", null, node));
    if (a.watches.length) sec("What I watch", h("ul", null, a.watches.map((x) => h("li", null, x))));
    if (a.acts) sec("When I act", a.acts);
    if (a.tells) sec("Who I tell", a.tells);
    card.append(dl);
    const more = h("dl");
    if (a.never.length) more.append(h("dt", null, "What I never do"), h("dd", null, h("ul", null, a.never.map((x) => h("li", null, x)))));
    if (a.who_may_start) more.append(h("dt", null, "Who can start me"), h("dd", null, `${a.who_may_start.join(", ")}. Who can approve my actions: ${a.who_may_approve.join(", ")}.`));
    if (more.children.length) card.append(h("details", { class: "more" }, h("summary", null, "More about this agent"), more));
    if (!a.available) card.append(h("p", { class: "muted" }, a.status_note || "Being built. This agent is not installed yet."));
    else card.append(runForm(a));
    const real = realToggle(a.agent);
    if (real) card.append(real);
    grid.append(card);
  });
  (S.perm.sees_costs ? data.planned || [] : []).forEach((p) => grid.append(h("section", { class: "profile planned" },
    h("div", { class: "profile-head" }, h("span", { class: "av av-88 a-unknown", "aria-hidden": "true" }, icon("users")), h("div", { class: "stack" }, h("h3", null, p.title), h("p", { class: "muted" }, p.department), kindChip("calm", "minus", "Planned"))),
    h("p", null, p.summary))));
  page.append(grid);
  main.append(page);
};

function runForm(a) {
  const holder = h("div", { class: "stack" });
  const open = h("button", { class: "btn primary", "aria-expanded": "false" }, "Run me now");
  const areas = (S.perm.agent_areas[a.agent] || []).map((id) => ({ area_id: id, name: areaName(id) }));
  const area = h("select", { id: "area-" + a.agent }, areas.map((x) => h("option", { value: x.area_id }, x.name)));
  const demo = a.demo || {};
  const demoOk = areas.some((x) => x.area_id === demo.area_id);
  area.value = demoOk ? demo.area_id : (areas[0] || {}).area_id;
  const asOf = h("input", { type: "date", id: "asof-" + a.agent, value: demo.as_of || "" });
  const ev = h("input", { type: "text", id: "ev-" + a.agent, placeholder: "EV113", value: demoOk ? demo.event_id || "" : "" });
  const out = h("div");
  const go = h("button", { class: "btn primary" }, `Run ${lowerFirst(a.title)}`);
  go.onclick = async () => {
    out.replaceChildren(); go.disabled = true;
    const p = await api("/api/run", { agent: a.agent, caller_id: S.viewAs, area_id: area.value, inputs: { as_of: asOf.value, event_id: ev.value } });
    go.disabled = false;
    if (!p.ok) out.replaceChildren(errorLine(p.error)); else await showRunPayload(p);
  };
  const form = h("div", { class: "run-form", hidden: true },
    h("div", { class: "fields" },
      h("label", { class: "field" }, "Client area", area), h("label", { class: "field" }, "Data as of (optional)", asOf),
      a.agent === "meeting_prep" ? h("label", { class: "field" }, "Meeting event", ev) : null),
    demo.line ? h("p", { class: "small demo-line" }, demoOk ? demo.line : `Showing ${areaName(area.value)}. The demo example is about a client you do not work on, so a day may be quiet. Change the date to try other days.`) : null,
    h("p", { class: "small muted" }, `Runs as ${personName(S.viewAs)}. If the combination is not allowed, the run is refused and you will see why.`),
    h("div", null, go), out);
  open.onclick = () => { form.hidden = !form.hidden; open.setAttribute("aria-expanded", String(!form.hidden)); };
  holder.append(open, form);
  return holder;
}

pages.departments = async (main) => {
  const data = await api("/api/scenarios?person=" + encodeURIComponent(S.viewAs));
  const page = h("div", { class: "page" });
  if (!data.departments.length) return main.append(page, emptyState("building", `${personName(S.viewAs)} has no team scenarios to try. Agents send them letters instead.`, "Open the inbox", () => { location.hash = "inbox"; }));
  const body = h("div", { class: "section" });
  const seg = h("div", { class: "seg", role: "group", "aria-label": "Department" });
  const show = (id) => {
    S.dept = id;
    seg.querySelectorAll("button").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.id === id)));
    body.replaceChildren(departmentBody(data.departments.find((d) => d.id === id)));
  };
  data.departments.forEach((d) => seg.append(h("button", { "data-id": d.id, "aria-pressed": "false", onclick: () => show(d.id) }, d.title)));
  page.append(seg, body);
  main.append(page);
  show(data.departments.some((d) => d.id === S.dept) ? S.dept : data.departments[0].id);
};

function departmentBody(d) {
  const box = h("div", { class: "page" });
  const top = h("div", { class: "stack" }, h("p", { class: "lead" }, d.intro));
  (d.notes || []).forEach((n) => top.append(h("p", { class: "note" }, icon("info"), n)));
  if (d.view_as && d.view_as !== S.viewAs) top.append(h("p", { class: "muted" }, "Letters for this team go to ", h("button", { class: "link-btn", onclick: () => { setViewAs(d.view_as); location.hash = "inbox"; } }, `${personName(d.view_as)}'s inbox`), "."));
  box.append(top);
  const financeBox = d.id === "finance" ? askFinanceBox() : null;
  if (financeBox) box.append(financeBox);
  const tiles = h("div", { class: "tiles" });
  d.scenarios.forEach((s) => {
    const named = s.as_named ? " on purpose, to show a refusal" : "";
    const meta = s.agent ? h("p", { class: "meta" }, `${s.agent_title}, run as ${s.caller_name}${named}${s.inputs.as_of ? `, data as of ${s.inputs.as_of}` : ""}.`) : null;
    const look = h("p", { class: "look" }, s.look_for);
    if (s.status === "link") {
      tiles.append(h("div", { class: "tile" }, h("h4", null, s.title), h("p", null, s.situation), look,
        h("button", { class: "btn secondary", onclick: () => { location.hash = "approvals"; } }, "Open my approvals")));
    } else if (s.status === "being_built") {
      tiles.append(h("div", { class: `tile ${agentClass(s.agent)}` }, h("div", { class: "head" }, avatar(s.agent, 32), h("h4", null, s.title)), h("p", null, s.situation), kindChip("calm", "minus", "Being built"),
        h("p", { class: "meta" }, "The button works as soon as this agent is installed.")));
    } else {
      tiles.append(scenarioTile(s, h("div", { class: "stack" }, look, meta)));
    }
  });
  (d.planned || []).forEach((p) => tiles.append(h("div", { class: "tile planned" }, h("h4", null, p.title), kindChip("calm", "minus", "Planned, not built yet"), h("p", { class: "muted" }, p.text))));
  box.append(tiles);
  if (d.id === "cto") { const live = h("section", { class: "section" }, h("h2", null, "Cost, cache and guardrails"), loading()); box.append(live); costPanel(live); }
  return box;
}

async function costPanel(root) {
  const c = await api("/api/costs");
  const stat = (label, value) => h("div", { class: "stat" }, h("strong", null, value), h("span", null, label));
  const kind = (k) => (k === "allowed" ? "allowed" : k === "denied" ? "denied" : k === "held" ? "held" : "refused");
  const rows = c.guardrail_decisions || [];
  root.replaceChildren(h("h2", null, "Cost, cache and guardrails"),
    h("div", { class: "stat-row" }, stat("Runs", c.run_count), stat("Model calls", c.model_calls), stat("Total cost", money(c.total_cost_usd)), stat("Saved-prefix hits (cache)", Math.round(c.cache_hit_rate * 100) + "%")),
    h("p", { class: "muted measure" }, "A cache hit means the model call reused saved text, so it cost less. Runs so far: " + (Object.entries(c.run_status || {}).map(([k, v]) => `${v} ${k}`).join(", ") || "none yet") + "."),
    h("h3", null, "Cost by agent"),
    (c.by_agent || []).length ? h("div", { class: "tablewrap" }, h("table", null, h("thead", null, h("tr", null, ["Agent", "Model calls", "Cache hits", "Cache misses", "Cost"].map((t, i) => h("th", { class: i ? "num" : "" }, t)))),
      h("tbody", null, c.by_agent.map((a) => h("tr", null, h("td", null, h("span", { class: "agent-cell " + agentClass(a.agent) }, avatar(a.agent, 32), a.agent_title)), h("td", { class: "num" }, a.calls), h("td", { class: "num" }, a.hits), h("td", { class: "num" }, a.writes), h("td", { class: "num" }, money(a.cost_usd))))))) : h("p", { class: "muted" }, "No model calls yet. Try a scenario first."),
    h("h3", null, "What the guardrails decided"),
    Object.keys(c.guardrail_counts || {}).length ? h("div", { class: "chip-row" }, Object.entries(c.guardrail_counts).map(([k, v]) => chip(kind(k), `${v} ${k}`))) : h("p", { class: "muted" }, "No decisions yet."),
    rows.length ? h("div", { class: "tablewrap" }, h("table", null, h("thead", null, h("tr", null, ["Run", "Decision", "What", "Reason"].map((t) => h("th", null, t)))),
      h("tbody", null, rows.map((d) => h("tr", null, h("td", null, h("button", { class: "link-btn", onclick: () => openRun(d.run_id) }, d.run_id)), h("td", null, chip(kind(d.verdict))), h("td", null, d.what), h("td", null, d.reason)))))) : null);
}

pages.inbox = async (main) => {
  const [r, t] = await Promise.all([api("/api/inbox?person=" + encodeURIComponent(S.viewAs)), api("/api/today?person=" + encodeURIComponent(S.viewAs))]);
  if (!r.ok) return main.append(errorLine(r.error));
  const page = h("div", { class: "page" });
  if (!r.messages.length) {
    const pick = (t.picks || [])[0];
    page.append(emptyState("inbox", pick ? `Nothing for ${firstName(r.person)} yet. Run the ${lowerFirst(pick.agent_title)} to see what ${firstName(r.person)} receives.` : `Nothing for ${firstName(r.person)} yet.`,
      pick ? `Run the ${lowerFirst(pick.agent_title)}` : null, () => runScenario(pick, { textContent: "", disabled: false })));
    return main.append(page);
  }
  page.append(h("p", { class: "lead" }, `Private letters from agents to ${r.person}, newest first.`));
  const agents = [...new Set(r.messages.map((m) => m.agent))];
  const list = h("div", { class: "letters" });
  const filters = h("div", { class: "filters", role: "group", "aria-label": "Filter by agent" });
  const draw = () => {
    filters.querySelectorAll("button").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.agent === S.inboxAgent)));
    list.replaceChildren(...r.messages.filter((m) => !S.inboxAgent || m.agent === S.inboxAgent).map((m) => letter({ ...m, to_name: r.person }, { runLink: true })));
    fitLetters(list);
  };
  if (!agents.includes(S.inboxAgent)) S.inboxAgent = "";
  filters.append(h("button", { "data-agent": "", onclick: () => { S.inboxAgent = ""; draw(); } }, "All agents"));
  agents.forEach((a) => filters.append(h("button", { "data-agent": a, onclick: () => { S.inboxAgent = a; draw(); } }, titleOf(a))));
  if (agents.length > 1) page.append(filters);
  page.append(list); main.append(page); draw();
};

pages.approvals = async (main) => {
  const r = await api("/api/approvals?person=" + encodeURIComponent(S.viewAs));
  const page = h("div", { class: "page" });
  const waiting = r.approvals.filter((a) => a.status === "pending"), decided = r.approvals.filter((a) => a.status !== "pending");
  if (!r.approvals.length) {
    const t = await api("/api/today?person=" + encodeURIComponent(S.viewAs)), pick = (t.picks || [])[0];
    page.append(emptyState("check", pick ? "Nothing is waiting for you. Run a scenario to create an approval." : "Nothing is waiting for you.", pick ? `Try: ${pick.title}` : null, () => runScenario(pick, { textContent: "", disabled: false })));
    return main.append(page);
  }
  page.append(h("section", { class: "section", "aria-labelledby": "h-wait" }, h("h2", { id: "h-wait" }, "Waiting for a decision"),
    h("p", { class: "muted measure" }, `You are viewing as ${personName(S.viewAs)}. An approved action runs once. Only the right people can decide.`),
    waiting.length ? h("div", { class: "approval-list" }, waiting.map(approvalCard)) : h("p", null, "Nothing is waiting right now.")));
  if (decided.length) page.append(h("section", { class: "section", "aria-labelledby": "h-dec" }, h("h2", { id: "h-dec" }, "Decided"),
    h("div", { class: "decided-list" }, decided.map((a) => h("div", { class: `decided-row ${agentClass(a.agent)}` }, avatar(a.agent, 32),
      h("div", { class: "grow" }, h("strong", null, a.title || a.what), h("p", { class: "small muted" }, `${a.agent_title}. ${a.status === "approved" ? "Approved" : "Denied"} by ${a.decided_by || "someone"}, ${when(a.decided_at)}.`)),
      chip(a.status), h("button", { class: "link-btn", onclick: () => openRun(a.run_id) }, "See the run"))))));
  main.append(page);
};

/* ---------- top bar, viewer, menu ---------- */
async function refreshTop() {
  S.state = await api("/api/state");
  const dp = parts(S.state.now);
  $("#date-pill .long").textContent = datePill(S.state.now); $("#date-pill .short").textContent = dp ? `${dp[2]} ${MONTHS[dp[1] - 1]}` : "";
  const on = !S.state.paused;
  $("#pause").checked = on; $("#pause-label").textContent = on ? "Agents on" : "Agents paused";
  $("#banner").hidden = on;
  const a = await api("/api/approvals?person=" + encodeURIComponent(S.viewAs));
  const n = (a.approvals || []).filter((x) => x.status === "pending" && x.can_decide).length;
  const c = $("#nav .count"); if (c) { c.textContent = n; c.hidden = !n; c.setAttribute("aria-label", `${plural(n, "approval")} waiting for you`); }
}
function drawNav() {
  const nav = $("#nav"); nav.replaceChildren();
  NAV.forEach(([id, ic]) => nav.append(h("a", { href: "#" + id, "data-page": id }, icon(ic), TITLES[id], id === "approvals" ? h("span", { class: "count", hidden: true }, "0") : null)));
}
function setViewAs(id) {
  S.viewAs = id; S.perm = null; try { localStorage.setItem("viewAs", id); } catch (e) { /* ignore */ }
  const p = person(id) || {};
  $("#viewer-initials").textContent = initialsOf(p.name); $("#viewer-name").textContent = p.name || ""; $("#viewer-role").textContent = p.role_label || "";
  $("#viewer").setAttribute("aria-label", `Viewing as ${p.name}, ${p.role_label}. Change person`);
}
function openViewerMenu() {
  const menu = $("#viewer-menu"), btn = $("#viewer");
  menu.replaceChildren(...S.people.map((p) => h("button", { role: "menuitemradio", "aria-checked": String(p.person_id === S.viewAs), onclick: () => { closeMenus(); setViewAs(p.person_id); refreshTop(); renderPage(true); } },
    h("span", { class: "initials" }, initialsOf(p.name)), h("span", { class: "who" }, h("span", null, p.name), h("span", null, p.role_label)), p.person_id === S.viewAs ? h("span", { class: "tick" }, icon("check")) : null)));
  menu.hidden = false;
  const r = btn.getBoundingClientRect(), w = menu.offsetWidth;
  menu.style.top = r.bottom + 8 + "px"; menu.style.left = Math.max(16, Math.min(r.right - w, innerWidth - w - 16)) + "px";
  btn.setAttribute("aria-expanded", "true");
  (menu.querySelector('[aria-checked="true"]') || menu.firstChild).focus();
}
function closeMenus() {
  const menu = $("#viewer-menu");
  if (!menu.hidden) { menu.hidden = true; $("#viewer").setAttribute("aria-expanded", "false"); $("#viewer").focus(); }
}
function setRail(open) {
  $("#rail").classList.toggle("open", open); $("#rail-scrim").classList.toggle("open", open);
  $("#menu-btn").setAttribute("aria-expanded", String(open));
  if (innerWidth < 900) { if (open) $("#rail").removeAttribute("inert"); else $("#rail").setAttribute("inert", ""); }
}
function placeControls() {
  const small = innerWidth < 900, dest = small ? $("#rail-controls") : $(".top-actions");
  const order = small ? ["#viewer", ".switch", "#reset"] : ["#date-pill", "#next-day", "#viewer", ".switch", "#reset"];
  order.forEach((sel) => dest.append($(sel)));
}
const railInert = () => { placeControls(); if (innerWidth < 900 && !$("#rail").classList.contains("open")) $("#rail").setAttribute("inert", ""); else $("#rail").removeAttribute("inert"); };

async function nextDay() {
  const btn = $("#next-day"); btn.disabled = true;
  try {
    const r = await api("/api/next_day", {});
    if (!r.ok) return toast(r.error);
    const sum = Object.entries(r.summary || {}).map(([k, v]) => `${v} ${k}`).join(", ");
    await refreshTop();
    toast(`It is now ${datePill(r.now)}. ` + (r.fired.length ? `Agents started ${plural(r.fired.length, "run")}: ${sum}.` : "No agent was due today."));
    renderPage(true);
  } finally { btn.disabled = false; }
}

/* ---------- router ---------- */
let currentPage = "today";
async function renderPage(quiet) {
  const raw = (location.hash.slice(1) || "today").split("/");
  const page = ALIAS[raw[0]] || (pages[raw[0]] ? raw[0] : "today"), arg = raw[1];
  currentPage = page;
  const token = ++S.token;
  document.querySelectorAll("#nav a").forEach((a) => (a.dataset.page === page ? a.setAttribute("aria-current", "page") : a.removeAttribute("aria-current")));
  $("#page-title").textContent = TITLES[page];
  document.title = `${TITLES[page]} - Company OS console`;
  await loadPerm();
  const main = $("#main"), keepY = scrollY;
  const fresh = h("div");
  try { await pages[page](fresh, quiet ? null : arg); }
  catch (e) { fresh.replaceChildren(errorLine("Something went wrong showing this page: " + e.message)); }
  if (token !== S.token) return;
  main.replaceChildren(...fresh.childNodes);
  fitLetters(main);
  if (quiet) window.scrollTo(0, keepY); else { window.scrollTo(0, 0); }
}
async function onHash() { setRail(false); await renderPage(false); }

function setTheme(dark) {
  document.documentElement.dataset.theme = dark ? "dark" : "light";
  try { localStorage.setItem("theme", dark ? "dark" : "light"); } catch (e) { /* ignore */ }
}
async function start() {
  let dark = false; try { dark = localStorage.getItem("theme") === "dark"; } catch (e) { /* ignore */ }
  $("#dark").checked = dark; $("#dark").onchange = (e) => setTheme(e.target.checked);
  window.addEventListener("hashchange", onHash); window.addEventListener("popstate", onHash);
  fillIcons(); $("#menu-btn").append(icon("menu"));
  drawNav();
  const [people, agents, state] = await Promise.all([api("/api/people"), api("/api/agents"), api("/api/state")]);
  S.people = people.people; S.state = state;
  (agents.agents || []).forEach((a) => (S.titles[a.agent] = a.title));
  try { const v = localStorage.getItem("viewAs"); if (v && person(v)) S.viewAs = v; } catch (e) { /* ignore */ }
  if (!person(S.viewAs) && S.people.length) S.viewAs = S.people[0].person_id;
  setViewAs(S.viewAs);
  await refreshTop();
  $("#next-day").onclick = nextDay;
  $("#viewer").onclick = () => ($("#viewer-menu").hidden ? openViewerMenu() : closeMenus());
  $("#menu-btn").onclick = () => setRail(!$("#rail").classList.contains("open"));
  $("#rail-scrim").onclick = () => setRail(false);
  $("#scrim").onclick = closeDrawer;
  $("#pause").onchange = async (e) => { await api(e.target.checked ? "/api/resume" : "/api/pause", {}); await refreshTop(); toast(e.target.checked ? "Agents are on." : "Agents are paused. New runs will be refused."); };
  $("#reset").onclick = async () => {
    if (!confirm("Reset the demo? This removes all runs, letters and memory of this session and sets the date back.")) return;
    await api("/api/reset", {}); S.lastRunId = null; closeDrawer(); await refreshTop(); toast("The demo is back to a clean start."); renderPage(true);
  };
  document.addEventListener("click", (e) => { const m = $("#viewer-menu"); if (!m.hidden && !m.contains(e.target) && !$("#viewer").contains(e.target)) { m.hidden = true; $("#viewer").setAttribute("aria-expanded", "false"); } });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      if (!$("#viewer-menu").hidden) { closeMenus(); e.preventDefault(); }
      else if (drawerOpen()) { closeDrawer(); e.preventDefault(); }
      else if ($("#rail").classList.contains("open")) { setRail(false); $("#menu-btn").focus(); }
      return;
    }
    const menu = $("#viewer-menu");
    if (!menu.hidden && (e.key === "ArrowDown" || e.key === "ArrowUp")) {
      const items = [...menu.querySelectorAll("button")], i = items.indexOf(document.activeElement);
      items[(i + (e.key === "ArrowDown" ? 1 : -1) + items.length) % items.length].focus(); e.preventDefault();
    }
    if (e.key === "Tab" && drawerOpen()) {
      const f = [...$("#drawer").querySelectorAll("button, a[href], input, select, summary, [tabindex]:not([tabindex='-1'])")].filter((x) => !x.disabled && x.offsetParent !== null);
      if (!f.length) return;
      if (e.shiftKey && document.activeElement === f[0]) { f[f.length - 1].focus(); e.preventDefault(); }
      else if (!e.shiftKey && document.activeElement === f[f.length - 1]) { f[0].focus(); e.preventDefault(); }
    }
  });
  window.addEventListener("resize", railInert); railInert();
  renderPage(false);
}
start();
