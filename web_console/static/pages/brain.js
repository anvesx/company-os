// Brain inbox page (contract C8): drop zone, paste box, agent step strip, source viewer with item to line links.
CompanyOS.registerPage({
  id: "brain", title: "Brain inbox", order: 20, icon: "inbox",
  render: async (main, ctx) => {
    const { el } = ctx;
    const AGENTS = [["brain_cleaner", "Cleaner"], ["brain_extractor", "Extractor"], ["brain_linker", "Linker"], ["brain_playbook", "Playbook writer"]];
    const strip = el("div", { class: "brain-strip" });
    const list = el("div", { class: "brain-list" });
    const viewer = el("div", { class: "brain-viewer" }, el("p", { class: "brain-hint" }, "Pick a source to see its lines and facts."));
    const status = el("p", { class: "brain-status" });
    const paste = el("textarea", { class: "brain-paste", rows: 5, placeholder: "Or paste a transcript, an email or a chat here" });
    const file = el("input", { type: "file", class: "brain-file", accept: ".json,.docx,.eml,.txt" });

    const drawStrip = (steps) => {
      strip.replaceChildren(...AGENTS.map(([id, label]) => {
        const s = (steps || []).find((x) => x.agent === id);
        const state = s ? s.status : "idle";
        const node = el("button", { class: `brain-step brain-step-${state}`, title: s ? s.summary : "Not run yet" },
          el("strong", {}, label), el("span", {}, s ? s.summary : "waiting"));
        if (s && s.run_id) node.onclick = () => ctx.runStory(s.run_id);
        return node;
      }));
    };

    const showSource = async (id) => {
      const r = await ctx.api(`/api/brain/source?id=${encodeURIComponent(id)}`);
      if (!r.ok) { viewer.replaceChildren(ctx.letter(r.error)); return; }
      drawStrip(r.steps);
      const rows = r.lines.map((l) => el("tr", { "data-line": l.line_no, class: l.untranslated ? "brain-line brain-untranslated" : "brain-line" },
        el("td", {}, String(l.line_no)), el("td", {}, l.speaker || ""), el("td", { class: "brain-raw" }, l.raw),
        el("td", { class: "brain-clean" }, l.untranslated ? "No English version yet" : (l.clean || ""))));
      const light = (item) => rows.forEach((row) => {
        const n = Number(row.getAttribute("data-line"));
        row.classList.toggle("brain-lit", n >= item.line_from && n <= item.line_to);
      });
      const items = r.items.map((i) => {
        const b = el("button", { class: `brain-item brain-item-${i.confirmed ? "active" : "unconfirmed"}` },
          el("span", { class: "brain-kind" }, i.kind), " ", i.text,
          el("small", {}, ` ${i.topic} · lines ${i.line_from}-${i.line_to}${i.confirmed ? "" : " · not confirmed"}`));
        b.onclick = () => light(i);
        return b;
      });
      viewer.replaceChildren(
        el("h3", {}, r.source.title || r.source.origin_ref),
        el("p", { class: "brain-meta" }, `${r.source.kind} · ${r.source.area_id} · ${r.source.status}`),
        el("div", { class: "brain-cols" },
          el("table", { class: "brain-lines" }, el("thead", {}, el("tr", {}, ...["#", "Who", "Original", "English"].map((t) => el("th", {}, t)))), el("tbody", {}, ...rows)),
          el("div", { class: "brain-items" }, el("h4", {}, `Facts (${items.length})`), ...items)));
    };

    const loadList = async () => {
      const r = await ctx.api("/api/brain/sources");
      list.replaceChildren(...(r.sources || []).map((s) => {
        const b = el("button", { class: "brain-source" }, el("strong", {}, s.title || s.origin_ref),
          el("small", {}, `${s.area_id} · ${s.lines} lines · ${s.items} facts · ${s.status}`));
        b.onclick = () => showSource(s.source_id);
        return b;
      }));
    };

    const send = async (body) => {
      status.textContent = "Working on it...";
      const r = await ctx.api("/api/brain/drop", { method: "POST", body });
      if (!r.ok) { status.textContent = r.error; return; }
      status.textContent = r.visible ? (r.held ? "Stored on hold. An Admin will sort it." : "Done.") : r.message;
      if (r.steps) drawStrip(r.steps);
      await loadList();
      if (r.source_id) showSource(r.source_id);
    };

    const toB64 = (buf) => { let s = ""; new Uint8Array(buf).forEach((c) => { s += String.fromCharCode(c); }); return btoa(s); };
    const takeFile = async (f) => { if (f) send({ filename: f.name, content_b64: toB64(await f.arrayBuffer()) }); };
    file.onchange = () => takeFile(file.files[0]);
    const zone = el("div", { class: "brain-drop" }, el("p", {}, "Drop a file here (Fathom JSON, Word, email or chat export)"), file);
    zone.ondragover = (e) => { e.preventDefault(); zone.classList.add("brain-over"); };
    zone.ondragleave = () => zone.classList.remove("brain-over");
    zone.ondrop = (e) => { e.preventDefault(); zone.classList.remove("brain-over"); takeFile(e.dataTransfer.files[0]); };
    const go = el("button", { class: "brain-go" }, "Add pasted text");
    go.onclick = () => { if (paste.value.trim()) { send({ kind: "paste", text: paste.value }); paste.value = ""; } };

    drawStrip([]);
    main.replaceChildren(el("h2", {}, "Brain inbox"), zone, paste, go, status, strip, el("div", { class: "brain-body" }, list, viewer));
    await loadList();
  },
});
