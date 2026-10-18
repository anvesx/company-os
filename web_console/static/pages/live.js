"use strict";
/* Live call page: plays a simulated call line by line and shows the copilot's suggestions with their sources. */
CompanyOS.registerPage({
  id: "live", title: "Live call", order: 55, icon: "pulse",
  render: async (main, ctx) => {
    const el = ctx.el;
    const state = { lines: [], next: 0, session: null, playing: false, speed: 1, timer: null, busy: false };
    const head = el("div", {}, el("h2", {}, "Live call"),
      el("p", { class: "muted measure" }, "Play a simulated call. The copilot checks each line against what the company already knows and suggests the next question."));
    const picker = el("div", { class: "live-bar" });
    const controls = el("div", { class: "live-bar", hidden: true });
    const us = el("div", { class: "live-col" }, el("h4", {}, "DevX"));
    const them = el("div", { class: "live-col" }, el("h4", {}, "Client"));
    const cards = el("div", { class: "live-cards", "aria-live": "polite" }, el("p", { class: "muted small" }, "Suggestions appear here."));
    const summary = el("div", { class: "live-summary", hidden: true });
    const grid = el("div", { class: "live-grid", hidden: true }, el("div", { class: "live-call" }, us, them),
      el("div", {}, el("h3", {}, "Suggested questions"), cards));
    main.append(head, picker, controls, grid, summary);

    const status = el("span", { class: "muted small" });
    const playBtn = el("button", { class: "live-btn live-primary", type: "button" }, "Play");
    const speeds = [1, 2, 4].map((s) => el("button", { class: "live-btn", type: "button", "aria-pressed": s === 1 ? "true" : "false",
      onclick: () => { state.speed = s; speeds.forEach((b, i) => b.setAttribute("aria-pressed", [1, 2, 4][i] === s ? "true" : "false")); } }, `${s}x`));
    controls.append(playBtn, ...speeds, status);

    const sourceText = (c) => c.origin_ref ? `Source: ${c.origin_ref}, line ${c.line_no}` : c.checklist_id ? `Source: kickoff checklist (${(c.learned_from || []).join(", ") || "past deals"})` : "";
    function addSuggestion(s) {
      if (!cards.querySelector(".live-card")) cards.textContent = "";
      cards.prepend(el("div", { class: "live-card" },
        el("span", { class: `live-tag live-${s.kind}` }, { gap: "Gap", contradiction: "Contradiction", follow_up: "Follow up" }[s.kind] || s.kind),
        el("p", {}, s.text), el("p", { class: "live-source" }, `Line ${s.line_no}. ${s.why}`),
        ...s.cites.map((c) => el("p", { class: "live-source" }, sourceText(c)))));
    }
    function addLine(l) {
      const mine = String(l.speaker_id).startsWith("P");
      const box = el("div", { class: `live-line ${mine ? "live-us" : "live-them"}` },
        el("strong", {}, l.speaker), el("div", {}, l.clean_text));
      if (l.clean_text !== l.text) box.append(el("div", { class: "live-orig" }, l.text));
      (mine ? us : them).append(box);
    }
    async function step() {
      if (state.busy || !state.playing) return;
      if (state.next >= state.lines.length) { state.playing = false; playBtn.textContent = "Play"; return finish(); }
      state.busy = true;
      const line = state.lines[state.next++];
      const r = await ctx.api("/api/live/hear", { method: "POST", body: { session_id: state.session, line_no: line.line_no } });
      state.busy = false;
      if (!r.ok) { ctx.toast(r.error); state.playing = false; return; }
      addLine(line);
      r.suggestions.forEach(addSuggestion);
      status.textContent = `Line ${state.next} of ${state.lines.length}`;
      schedule();
    }
    function schedule() { clearTimeout(state.timer); if (state.playing) state.timer = setTimeout(step, 1500 / state.speed); }
    async function finish() {
      const r = await ctx.api("/api/live/end", { method: "POST", body: { session_id: state.session } });
      if (!r.ok) return ctx.toast(r.error);
      summary.hidden = false; summary.textContent = "";
      summary.append(el("h3", {}, "Call summary"), el("p", {}, r.summary), el("ul", {}, ...(r.next_steps || []).map((t) => el("li", {}, t))),
        el("p", { class: "muted small" }, r.run_id ? `Run ${r.run_id}` : ""));
      if (r.run_id) summary.append(el("button", { class: "live-btn", type: "button", onclick: () => ctx.runStory(r.run_id) }, "See the run"));
    }
    playBtn.addEventListener("click", () => {
      state.playing = !state.playing; playBtn.textContent = state.playing ? "Pause" : "Play";
      if (state.playing) step(); else clearTimeout(state.timer);
    });

    async function begin(call) {
      const r = await ctx.api("/api/live/start", { method: "POST", body: { call_id: call.call_id } });
      if (!r.ok) return ctx.toast(r.error);
      Object.assign(state, { lines: r.lines, next: 0, session: r.session_id, playing: false });
      us.replaceChildren(el("h4", {}, "DevX")); them.replaceChildren(el("h4", {}, r.client_name));
      cards.replaceChildren(el("p", { class: "muted small" }, "Suggestions appear here."));
      summary.hidden = true; grid.hidden = false; controls.hidden = false; playBtn.textContent = "Play"; status.textContent = r.title;
    }
    const list = await ctx.api("/api/live/calls");
    if (!list.ok || !list.calls.length) { picker.append(el("p", { class: "muted" }, list.error || "No calls are open to you.")); return; }
    list.calls.forEach((c) => picker.append(el("button", { class: "live-btn", type: "button", onclick: () => begin(c) }, c.title)));
  },
});
