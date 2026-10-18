/* Finance page (contract C8, Admin only). Classes start with finance-. */
(function () {
  const inr = (n) => "INR " + Number(n || 0).toLocaleString("en-IN");
  const clock = (t) => { if (!t) return ""; const h = +t.slice(0, 2); return ((h % 12) || 12) + ":" + t.slice(3, 5) + (h < 12 ? " AM" : " PM"); };
  const day = (d) => { const x = new Date(d + "T00:00:00"); return x.toLocaleDateString("en-IN", { day: "numeric", month: "short" }); };

  function flightRow(el, f) {
    const tail = f.arrive_time ? " to " + clock(f.arrive_time) : "";
    return el("tr", {}, el("td", {}, f.carrier + " " + f.flight_no), el("td", {}, clock(f.depart_time) + tail),
      el("td", {}, inr(f.fare_inr)), el("td", {}, "seen " + day(f.seen_on)), el("td", { class: "finance-save" }, "save " + inr(f.saving_inr)));
  }
  function table(el, rows) { return el("table", { class: "finance-table" }, el("tbody", {}, ...rows)); }

  function tripCard(el, t) {
    const p = t.paid, best = t.verdict !== "cheaper_option_existed";
    const paid = el("div", { class: "finance-paid" }, el("strong", {}, "Booked: "),
      (p.flight_no ? p.carrier + " " + p.flight_no + " at " + clock(p.depart_time) + ", " : p.carrier + ", ") + p.cabin + ", " + inr(p.fare_inr) +
      " (booked " + day(p.booked_on) + ")" + (t.hotel_paid ? ". Hotel: " + t.hotel_paid.hotel + ", " + inr(t.hotel_paid.rate_inr) + " a night, " + t.hotel_paid.nights + " night(s)" : ""));
    const kids = [el("h4", {}, t.trip_id + "  " + t.route + ", " + day(t.depart_on), " ",
      el("span", { class: "chip " + (best ? "ok" : "warn") }, best ? "Best option chosen" : "Cheaper option existed")), paid];
    (t.rules || []).forEach((r) => kids.push(el("p", { class: "finance-rule" }, "Policy: " + r.text)));
    if (t.cheaper_flights.length) kids.push(el("h5", {}, "Cheaper flights"), table(el, t.cheaper_flights.map((f) => flightRow(el, f))));
    if (t.cheaper_hotels.length) kids.push(el("h5", {}, "Cheaper hotels"), table(el, t.cheaper_hotels.map((h) => el("tr", {},
      el("td", {}, h.hotel), el("td", {}, inr(h.rate_inr) + " a night"), el("td", { class: "finance-save" }, "save " + inr(h.saving_inr))))));
    return el("div", { class: "finance-card" }, ...kids);
  }

  function findingCard(el, f) {
    return el("div", { class: "finance-card" },
      el("h4", {}, f.kind.replace(/_/g, " "), " ", el("span", { class: "chip " + (f.severity === "high" ? "stop" : "warn") }, f.severity), " ", inr(f.amount_inr)),
      el("p", {}, el("strong", {}, "Evidence: "), f.evidence), el("p", {}, el("strong", {}, "Why it matters: "), f.why_it_matters),
      el("p", {}, el("strong", {}, "Next step: "), f.next_step),
      el("div", { class: "finance-records" }, ...f.records.map((r) => el("details", {}, el("summary", {}, r.type + " " + r.id),
        el("pre", {}, Object.entries(r.detail).map(([k, v]) => k + ": " + v).join("\n"))))));
  }

  CompanyOS.registerPage({
    id: "finance", title: "Finance", order: 60, icon: "coin",
    render: async (main, ctx) => {
      const el = ctx.el;
      const findBox = el("div", {}), tripBox = el("div", {}), split = el("div", {}), answer = el("div", {});
      async function loadFindings() {
        const r = await ctx.api("/api/finance/findings");
        findBox.replaceChildren(...(r.ok && r.findings.length ? r.findings.map((f) => findingCard(el, f))
          : [el("p", {}, r.ok ? "No findings yet. Press Check the books." : r.error)]));
      }
      const check = el("button", { class: "btn secondary", onclick: async () => {
        findBox.replaceChildren(el("p", {}, "Checking the books..."));
        const r = await ctx.api("/api/finance/check", { method: "POST", body: {} });
        if (r.run_id) ctx.toast("Finance watch ran."); await loadFindings();
      } }, "Check the books");
      const input = el("input", { type: "text", class: "finance-q", placeholder: "Ask about spending, for example: where can we save on travel?" });
      const ask = el("button", { class: "btn primary", onclick: async () => {
        answer.replaceChildren(el("p", {}, "Thinking..."));
        const r = await ctx.api("/api/finance/ask", { method: "POST", body: { question: input.value } });
        answer.replaceChildren(r.ok ? el("pre", { class: "finance-answer" }, r.answer) : ctx.letter({ text: r.error }));
      } }, "Ask");
      main.append(el("h2", {}, "Finance"), el("h3", {}, "Findings from the books"), check, findBox,
        el("h3", {}, "Trips: paid against cheaper options"), tripBox, el("h3", {}, "Travel spend by team"), split,
        el("h3", {}, "Ask the spend advisor"), el("div", { class: "finance-ask" }, input, ask), answer);
      await loadFindings();
      const t = await ctx.api("/api/finance/trips");
      if (t.ok) {
        tripBox.replaceChildren(el("p", {}, "If the top cheaper option had been taken on each trip, DevX would have saved " + inr(t.top_option_saving_inr) + "."),
          ...t.trips.slice().reverse().map((x) => tripCard(el, x)));
        const max = Math.max(1, ...t.spend_by_team.map((s) => s.travel_inr));
        split.replaceChildren(...t.spend_by_team.map((s) => el("div", { class: "finance-bar" }, el("span", {}, s.team.replace(/_/g, " ")),
          el("div", { class: "finance-bar-fill", style: "width:" + Math.round(100 * s.travel_inr / max) + "%" }), el("span", {}, inr(s.travel_inr)))));
      } else tripBox.replaceChildren(ctx.letter({ text: t.error }));
    },
  });
})();
