// Meeting prep page: next client meetings, "Prep me", and the brief with source links into the Brain viewer.
(function () {
  const SECTIONS = [
    ["questions", "Questions to ask"], ["open_requirements", "Open requirements"], ["blockers", "Blockers"],
    ["recent_decisions", "Recent decisions"], ["changed_decisions", "Changed decisions"],
    ["commitments_due", "Commitments due"], ["contradictions", "Statements that conflict"],
  ];

  function when(start) {
    const [day, time] = String(start).split("T");
    const [h, m] = (time || "00:00").split(":").map(Number);
    return `${day}, ${h % 12 || 12}:${String(m).padStart(2, "0")} ${h >= 12 ? "PM" : "AM"} IST`;
  }

  function lineLabel(s) {
    return s.line_from === s.line_to ? `line ${s.line_from}` : `lines ${s.line_from}-${s.line_to}`;
  }

  function sourceLinks(ctx, point) {
    const span = ctx.el("span", {});
    const seen = new Set();
    (point.sources || []).forEach((s) => {
      const key = `${s.source_id}:${s.line_from}`;
      if (seen.has(key)) return;
      seen.add(key);
      const label = `${s.title || s.origin_ref || s.source_id}, ${s.date}, ${lineLabel(s)}`;
      const link = ctx.el("button", { class: "meeting_prep-source", type: "button", title: "Open this line in the Brain" }, label);
      link.addEventListener("click", () => ctx.go("brain", { source_id: s.source_id, line: s.line_from }));
      span.append(" (", link, ")");
    });
    return span;
  }

  function renderPoint(ctx, point) {
    const row = ctx.el("div", { class: "meeting_prep-point" });
    if (point.unconfirmed) row.append(ctx.el("span", { class: "meeting_prep-tag" }, "Unconfirmed"));
    row.append(point.text, sourceLinks(ctx, point));
    return row;
  }

  function renderBrief(ctx, box, reply) {
    box.replaceChildren(ctx.el("h2", {}, `${reply.title} (${when(reply.start_at)})`));
    const brief = reply.brief || {};
    SECTIONS.forEach(([key, title]) => {
      const points = brief[key] || [];
      if (!points.length) return;
      const section = ctx.el("div", { class: "meeting_prep-section" }, ctx.el("h3", {}, title));
      points.forEach((p) => section.append(renderPoint(ctx, p)));
      box.append(section);
    });
    if (brief.watch_out && brief.watch_out.length) {
      const section = ctx.el("div", { class: "meeting_prep-section" }, ctx.el("h3", {}, "Watch out for"));
      brief.watch_out.forEach((w) => section.append(ctx.el("div", { class: "meeting_prep-point" }, w)));
      box.append(section);
    }
    if (reply.quiet) box.append(ctx.el("p", {}, "Nothing is open for this project yet."));
    box.append(ctx.el("div", { class: "meeting_prep-count" }, reply.unconfirmed_line));
  }

  CompanyOS.registerPage({
    id: "meeting_prep", title: "Meeting prep", order: 30, icon: "calendar",
    render: async (main, ctx) => {
      const box = ctx.el("div", { class: "meeting_prep-brief" });
      const list = ctx.el("div", { class: "meeting_prep-list" });
      main.append(ctx.el("h1", {}, "Meeting prep"), list, box);
      const data = await ctx.api("/api/meeting_prep/upcoming");
      if (!data.ok) { list.append(ctx.letter(data.error)); return; }
      if (!data.events.length) list.append(ctx.el("p", {}, "No client meetings are coming up."));
      data.events.forEach((e) => {
        const button = ctx.el("button", { type: "button" }, "Prep me");
        button.addEventListener("click", async () => {
          button.disabled = true;
          const reply = await ctx.api("/api/meeting_prep/brief", { method: "POST", body: { event_id: e.event_id } });
          button.disabled = false;
          if (!reply.ok) { ctx.toast(reply.error); return; }
          renderBrief(ctx, box, reply);
        });
        const card = ctx.el("div", { class: "meeting_prep-card" }, ctx.el("h3", {}, e.title),
          ctx.el("div", {}, `${when(e.start_at)} · ${e.client_name}`),
          ctx.el("div", {}, `${e.unconfirmed_count} unconfirmed items`), button);
        list.append(card);
      });
    },
  });
})();
