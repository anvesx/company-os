/* Deals and playbooks page (contract C8). Classes start with deals-; colours come from the shell variables. */
(function () {
  const SECTIONS = [["initially_wanted", "First wanted"], ["later_changed_to", "Changed to later"], ["chose", "Chose"],
                    ["went_right", "Went right"], ["went_wrong", "Went wrong"]];

  function cited(el, row) {
    return el("span", { class: "deals-cite" }, " (" + (row.cites || []).join(", ") + ")");
  }
  function line(el, text, row) {
    const kids = [];
    const m = /^Unconfirmed:\s*/.exec(text);
    if (m) kids.push(el("span", { class: "deals-unconfirmed" }, "Unconfirmed: "));
    kids.push(m ? text.slice(m[0].length) : text);
    kids.push(cited(el, row));
    return el("li", {}, ...kids);
  }
  function section(el, title, rows, field) {
    return el("div", { class: "deals-section" }, el("h3", {}, title),
      rows.length ? el("ul", {}, ...rows.map((r) => line(el, r[field], r))) : el("p", {}, "Nothing to show."));
  }

  function showBrief(el, box, b, deal) {
    box.replaceChildren(
      el("h3", {}, "Brief: " + deal.name), el("p", {}, b.summary),
      el("div", { class: "deals-section" }, el("h3", {}, "Similar past clients"),
        el("ul", {}, ...b.similar.map((s) => el("li", {}, el("span", { class: "deals-outcome-" + s.outcome }, s.outcome + ": "),
          s.client_label + ". " + s.why, el("span", { class: "deals-cite" }, " (" + s.playbook_id + ")"))))),
      section(el, "Ideas to close", b.closing_ideas, "text"),
      section(el, "Risks", b.risks, "text"),
      section(el, "Kickoff checklist", b.kickoff_questions, "question"));
  }

  CompanyOS.registerPage({
    id: "deals", title: "Deals and playbooks", order: 40, icon: "users",
    render: async (main, ctx) => {
      const el = ctx.el;
      const list = await ctx.api("/api/deals/list");
      const box = el("div", {});
      const stages = el("div", { class: "deals-stages" }, ...(list.stages || []).map((stage) =>
        el("div", { class: "deals-stage" }, el("h4", {}, stage),
          ...list.deals.filter((d) => d.stage === stage).map((d) => el("div", { class: "deals-card" },
            el("strong", {}, d.name), el("div", {}, d.industry || ""),
            el("button", { onclick: async () => {
              box.replaceChildren(el("p", {}, "Preparing the brief..."));
              const r = await ctx.api("/api/deals/brief", { method: "POST", body: { deal_id: d.deal_id } });
              if (r.ok) showBrief(el, box, r.brief, d); else box.replaceChildren(ctx.letter(r.error));
            } }, "Brief me"))))));
      const lib = await ctx.api("/api/deals/playbooks");
      const library = el("div", {}, el("h3", {}, "Playbook library"), ...(lib.playbooks || []).map((p) =>
        el("details", { class: "deals-playbook" },
          el("summary", {}, p.client_label + " (" + p.outcome + ")"),
          ...SECTIONS.map(([key, title]) => el("div", {}, el("h5", {}, title),
            p.sections[key].length ? el("ul", {}, ...p.sections[key].map((e) => el("li", {}, e.text))) : el("p", {}, "None."))))));
      main.replaceChildren(el("h2", {}, "Deals and playbooks"), stages, box, library);
    },
    homeCard: async (ctx) => {
      const list = await ctx.api("/api/deals/list");
      if (!list.ok || !list.deals.length) return null;
      return ctx.el("div", {}, ctx.el("h4", {}, "My deals"),
        ...list.deals.map((d) => ctx.el("p", {}, d.name + " (" + d.stage + ")")));
    },
  });
})();
