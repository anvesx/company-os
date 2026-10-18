// Check page: an optional list of items to look at. Everything is already stored and in use.
CompanyOS.registerPage({
  id: "review", title: "Check", order: 30, icon: "check",
  render: async (main, ctx) => {
    const { el } = ctx;
    const isAdmin = ctx.viewer.role === "admin";
    let scope = "mine";

    const side = (line) => el("div", { class: "review-line" + (line.context ? " review-context" : "") },
      el("span", { class: "review-no" }, "Line " + line.line_no),
      el("div", { class: "review-raw" }, el("small", {}, "Original"), el("p", {}, line.raw)),
      el("div", { class: "review-clean" }, el("small", {}, "Clean English"), el("p", {}, line.clean)));

    const decide = async (r, accept, edited) => {
      const res = await ctx.api("/api/review/decide", { method: "POST", body: { review_id: r.review_id, accept, edited } });
      ctx.toast(res.ok ? (accept ? "Confirmed." : "Dropped.") : res.error);
      if (res.ok) load();
    };

    const editBox = (r, card) => {
      const input = el("textarea", { class: "review-edit", rows: "2" }, r.item.text);
      const save = el("button", { class: "btn secondary", onclick: () => decide(r, true, { text: input.value }) }, "Save and confirm");
      card.append(input, save);
    };

    const sortBox = (r, card) => {
      const area = el("input", { class: "review-area", placeholder: "Client id, for example C04" });
      const go = el("button", { class: "btn secondary", onclick: async () => {
        const res = await ctx.api("/api/review/route_source", { method: "POST", body: { source_id: r.source.source_id, area_id: area.value.trim() } });
        ctx.toast(res.ok ? "Sorted to " + res.area_id + "." : res.error);
        if (res.ok) load();
      } }, "Sort to client");
      card.append(area, go);
    };

    const card = (r) => {
      const c = el("article", { class: "review-card" },
        el("header", {}, el("strong", {}, r.label), el("span", { class: "chip calm" }, r.area_name),
          r.confidence != null ? el("span", { class: "chip warn" }, Math.round(r.confidence * 100) + "% sure") : null),
        el("p", { class: "review-source" }, r.source.title + (r.reason ? " - " + r.reason : "")),
        r.item ? el("p", { class: "review-item" }, r.item.text + " (" + r.item.state + ")") : null,
        r.older ? el("p", { class: "review-older" }, "Replaced: " + r.older.text) : null,
        ...r.lines.map(side));
      if (r.review_id && r.status === "pending") {
        c.append(el("div", { class: "review-actions" },
          el("button", { class: "btn primary", onclick: () => decide(r, true) }, "Confirm"),
          r.item ? el("button", { class: "btn secondary", onclick: () => editBox(r, c) }, "Edit") : null,
          el("button", { class: "btn secondary", onclick: () => decide(r, false) }, "Drop")));
      } else if (r.kind === "unrouted" && isAdmin) {
        sortBox(r, c);
      }
      return c;
    };

    const list = el("div", { class: "review-list" });
    const toggle = el("button", { class: "btn secondary", onclick: () => { scope = scope === "mine" ? "all" : "mine"; load(); } }, "");
    main.append(el("h1", {}, "Check"),
      el("p", { class: "review-note" }, "This page is optional. Items are already stored and in use. Check the ones you want to."),
      toggle, list);

    async function load() {
      toggle.textContent = scope === "mine" ? "Show all in my areas" : "Show only mine";
      const res = await ctx.api("/api/review/list?scope=" + scope);
      list.replaceChildren();
      if (!res.ok) { list.append(el("p", {}, res.error)); return; }
      if (!res.reviews.length) list.append(el("p", {}, "Nothing to check."));
      res.reviews.forEach((r) => list.append(card(r)));
    }
    await load();
  },
  homeCard: async (ctx) => {
    const res = await ctx.api("/api/review/list?scope=all");
    if (!res.ok || !res.count) return null;
    return ctx.el("div", { class: "review-home" }, res.count + " items you may want to check");
  },
});
