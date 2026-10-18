/* Travel page (contract C8). Admin sees every request; CSM and Growth see their own. Classes start with travel-. */
(function () {
  const inr = (n) => "INR " + Number(n || 0).toLocaleString("en-IN");
  const clock = (t) => { const h = +t.slice(0, 2); return ((h % 12) || 12) + ":" + t.slice(3, 5) + (h < 12 ? " AM" : " PM"); };
  const leg = (f) => f.carrier + " " + f.flight_no + ", " + clock(f.depart_time) + " to " + clock(f.arrive_time);
  const STATUS = { held: ["wait", "Waiting for an Admin"], booked: ["ok", "Booked"], denied: ["stop", "Denied"], refused: ["stop", "Refused"], failed: ["warn", "No match"] };

  function option(el, name, checked, title, lines) {
    return el("label", { class: "travel-opt" }, el("input", { type: "radio", name, checked }), el("div", {}, el("strong", {}, title), ...lines.map((l) => el("div", {}, l))));
  }

  function requestCard(el, ctx, r, reload) {
    const [tone, label] = STATUS[r.status] || ["calm", r.status];
    const q = r.request || {};
    const head = el("h4", {}, (q.from_city || "") + " to " + (q.to_city || "") + ", " + (q.depart_on || "") + (q.return_on ? " back " + q.return_on : "") + ", " + (q.pax || "") + " people",
      " ", el("span", { class: "chip " + tone }, label), r.requester_name ? el("span", { class: "travel-who" }, "for " + r.requester_name) : null);
    const kids = [head];
    if (r.booking_ref) kids.push(el("p", {}, "Booking " + r.booking_ref + ", total " + inr(r.total_inr)));
    const trips = r.round_trips && r.round_trips.length ? r.round_trips : r.flights || [];
    if (trips.length) {
      const fname = "f" + r.request_id, hname = "h" + r.request_id;
      const flights = trips.map((t, i) => t.outbound
        ? option(el, fname, i === 0, "Round trip " + (i + 1) + ": " + inr(t.fare_inr) + " a person, " + inr(t.total_inr) + " for " + t.pax,
            ["Out: " + leg(t.outbound), "Back: " + leg(t.return), t.why])
        : option(el, fname, i === 0, "Flight " + (i + 1) + ": " + t.carrier + " " + t.flight_no + ", " + inr(t.fare_inr) + " a person, " + inr(t.total_inr) + " total", [t.why]));
      const hotels = (r.hotels || []).map((h, i) => option(el, hname, i === 0, h.hotel + ", " + inr(h.rate_inr) + " a night, " + inr(h.total_inr) + " total", [h.why]));
      kids.push(el("div", { class: "travel-opts" }, el("h5", {}, q.return_on ? "Best 3 round trips" : "Best 3 flights"), ...flights,
        hotels.length ? el("h5", {}, "Best 3 hotels") : null, ...hotels));
      if (r.status === "held") kids.push(el("button", { class: "btn secondary", onclick: async (e) => {
        const card = e.target.closest(".travel-card"), pick = (n) => { const i = [...card.querySelectorAll('input[name="' + n + '"]')].findIndex((x) => x.checked); return i; };
        const f = trips[pick(fname)], h = (r.hotels || [])[pick(hname)];
        const out = await ctx.api("/api/travel/choose", { method: "POST", body: { request_id: r.request_id, flight_option_id: f.option_id, hotel_option_id: h ? h.option_id : "" } });
        ctx.toast(out.ok ? "Choice saved. It waits for an Admin to approve." : out.error); reload();
      } }, "Use my choice"));
    } else kids.push(el("p", {}, r.letter || ""));
    if ((r.out_of_policy || []).length) kids.push(el("p", { class: "travel-rule" }, r.out_of_policy.length + " option(s) broke the travel policy and are not shown."));
    kids.push(el("p", { class: "travel-rule" }, "Nothing is booked until an Admin approves."));
    return el("div", { class: "travel-card" }, ...kids);
  }

  CompanyOS.registerPage({
    id: "travel", title: "Travel", order: 70, icon: "plane",
    render: async (main, ctx) => {
      const el = ctx.el, list = el("div", {}), msg = el("div", {});
      const text = el("input", { type: "text", class: "travel-q", placeholder: "2 people Mumbai to Pune on 2026-10-28, back on 2026-10-29" });
      async function load() {
        const r = await ctx.api("/api/travel/requests");
        list.replaceChildren(...(r.ok ? (r.requests.length ? r.requests.map((x) => requestCard(el, ctx, x, load)) : [el("p", {}, "No requests yet.")]) : [ctx.letter({ text: r.error })]));
      }
      const go = el("button", { class: "btn primary", onclick: async () => {
        msg.replaceChildren(el("p", {}, "Searching flights and hotels..."));
        const r = await ctx.api("/api/travel/request", { method: "POST", body: { text: text.value } });
        msg.replaceChildren(r.ok ? el("p", {}, "Done. The best options are below. Nothing is booked until an Admin approves.") : ctx.letter({ text: r.error || r.letter }));
        await load();
      } }, "Find options");
      main.append(el("h2", {}, "Travel"), el("p", {}, ctx.viewer.role === "admin" ? "You see every request." : "You see your own requests."),
        el("div", { class: "travel-ask" }, text, go), msg, list);
      await load();
    },
  });
})();
