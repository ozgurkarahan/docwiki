/* DocWiki Studio browser UI: vanilla ES2020, no build step, no external resource.
 * Everything the API returns (answers, source titles, file names, errors) is untrusted: it only
 * reaches the page through createElement/textContent, and a link must be http(s). */
(() => {
  "use strict";

  /* ---------- constants ---------- */
  const POLL_MS = 2000;
  const REFRESH_BUSY_MS = 5000;
  const REFRESH_IDLE_MS = 10000;
  const ACTIVE = new Set(["running", "waiting_approval"]);
  const RISKY_TOOLS = new Set(["ingest_start", "recompile"]);
  const RUN_COST_WARNING = "Adding a new or changed document starts a pipeline run on Azure: about 15 minutes and about 10 USD of model usage for the sample corpus. Continue?";
  const AGENTS = {
    researcher: {
      label: "Researcher", icon: "search", working: "Researcher is reading the wiki…",
      placeholder: "Ask about a procedure, a value, a revision or a contradiction in your documents…",
    },
    librarian: {
      label: "Librarian", icon: "list", working: "Librarian is checking the pipeline…",
      placeholder: "Ask about the pipeline, or tell the Librarian what to run…",
    },
  };
  const DOC_STATUS = {
    new: ["New", "info"], pending: ["Pending", "warn"], done: ["Done", "ok"],
    failed: ["Failed", "bad"], quarantined: ["Quarantined", "orange"], deleted: ["Deleted", "muted"],
  };
  const RUN_STATUS = {
    running: ["Running", "info"], succeeded: ["Succeeded", "ok"], failed: ["Failed", "bad"], "no-op": ["No-op", "muted"],
  };
  const TURN_STATUS = {
    running: ["Working…", "info"], waiting_approval: ["Needs your approval", "warn"], done: ["Answered", "ok"],
    error: ["Failed", "bad"], cancelled: ["Cancelled", "muted"], gone: ["Forgotten", "bad"],
  };
  const STAGES = [
    "discover", "extract", "classify", "compile", "entities", "topics", "links",
    "indexes", "agentkit", "evidence", "verify", "site", "publish",
  ];
  const TOOL_ICONS = {
    search: "search", get_page: "file", get_index: "file", get_links: "link", get_evidence: "evidence",
    query_table: "grid", get_skill: "book", list_skills: "book", list_sources: "list",
    list_proposals: "list", run_status: "pipeline", quality_report: "shield",
    ingest_start: "play", recompile: "refresh", decide_proposal: "check",
  };
  const PROVENANCE = {
    "native-text": ["Native text", "ok"], "deterministic-table": ["Table", "info"],
    ocr: ["OCR", "warn"], "model-description": ["Generated description", "muted"],
  };
  const EXT_FAMILY = {
    pdf: "pdf", docx: "doc", xlsx: "xls", xlsm: "xls", csv: "xls", tsv: "xls", pptx: "ppt",
    png: "img", jpg: "img", jpeg: "img", gif: "img", bmp: "img", tif: "img", tiff: "img", webp: "img",
  };
  const SVG_NS = "http://www.w3.org/2000/svg";
  const ICONS = {
    upload: "M12 16V4m0 0L7 9m5-5 5 5M4 16v3a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-3",
    external: "M14 4h6v6M20 4l-9 9M18 14v4a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4",
    file: "M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8zM14 3v5h5",
    pipeline: "M22 12h-4l-3 9L9 3l-3 9H2",
    chat: "M21 12a8 8 0 0 1-11.6 7.1L4 20l1-4.3A8 8 0 1 1 21 12z",
    search: "M11 4a7 7 0 1 0 0 14 7 7 0 0 0 0-14zM21 21l-4.5-4.5",
    list: "M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01",
    grid: "M5 5h14a1 1 0 0 1 1 1v12a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1zM4 10h16M9 5v14",
    link: "M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1",
    evidence: "M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18zM8.5 12.5l2.5 2.5 4.5-5",
    shield: "M12 3l8 3v6c0 4.6-3.2 7.8-8 9-4.8-1.2-8-4.4-8-9V6zM9 12l2 2 4-4",
    play: "M7 4.5v15l12-7.5z", refresh: "M20 12a8 8 0 1 1-2.5-5.8M20 4v5h-5", check: "M5 12.5l4.5 4.5L19 7.5", x: "M6 6l12 12M18 6L6 18",
    book: "M4 5a2 2 0 0 1 2-2h13v16H6a2 2 0 0 0-2 2zM4 21a2 2 0 0 1 2-2h13",
    alert: "M12 3l10 18H2zM12 10v5M12 18v.01",
    clock: "M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18zM12 7.5V12l3 2",
    coin: "M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18zM14.5 9.5c-.5-1-1.4-1.5-2.5-1.5-1.4 0-2.5.8-2.5 2s1 1.7 2.5 2 2.5.8 2.5 2-1.1 2-2.5 2c-1.1 0-2-.5-2.5-1.5M12 6.5V8M12 16v1.5",
    tool: "M4 6l6 6-6 6M12 18h8",
  };

  /* ---------- state ---------- */
  const state = {
    me: null, docs: null, pipeline: null, agent: "researcher", filter: "",
    sizes: new Map(), seen: new Map(), runOpen: new Map(),
  };
  const turns = [];
  const uploads = [];
  let uploadSeq = 0;

  /* ---------- DOM helpers ---------- */
  const $ = (selector, root = document) => root.querySelector(selector);
  const plural = (n, one, many = `${one}s`) => `${n} ${n === 1 ? one : many}`;
  const flat = (kids) => kids.flat(Infinity).filter((kid) => kid != null && kid !== false);

  function h(tag, props, ...kids) {
    const el = document.createElement(tag);
    for (const [key, value] of Object.entries(props || {})) {
      if (value == null || value === false) continue;
      if (key === "class") el.className = value;
      else if (key === "text") el.textContent = value;
      else if (key === "dataset") Object.assign(el.dataset, value);
      else if (key.startsWith("on")) el.addEventListener(key.slice(2), value);
      else if (key !== "style") el.setAttribute(key, value === true ? "" : String(value));
    }
    el.append(...flat(kids));
    return el;
  }

  /* Replace the children of el (null, undefined and false are skipped, arrays are flattened). */
  function fill(el, ...kids) {
    el.replaceChildren(...flat(kids));
    return el;
  }

  function icon(name, extra = "") {
    const svg = document.createElementNS(SVG_NS, "svg");
    const path = document.createElementNS(SVG_NS, "path");
    svg.setAttribute("viewBox", "0 0 24 24");
    svg.setAttribute("class", `icon ${extra}`.trim());
    svg.setAttribute("aria-hidden", "true");
    path.setAttribute("d", ICONS[name] || ICONS.tool);
    svg.append(path);
    return svg;
  }

  /* Keyed in-place update: only the entries whose signature changed are rebuilt. */
  function syncList(parent, items, keyOf, sigOf, build) {
    const old = new Map(Array.from(parent.children, (el) => [el.dataset.key, el]));
    const next = items.map((item) => {
      const key = String(keyOf(item));
      const sig = sigOf(item);
      const prev = old.get(key);
      if (prev && prev.dataset.sig === sig) { old.delete(key); return prev; }
      const el = build(item);
      Object.assign(el.dataset, { key, sig });
      return el;
    });
    old.forEach((el) => el.remove());
    next.forEach((el, i) => {
      if (parent.children[i] !== el) parent.insertBefore(el, parent.children[i] || null);
    });
  }

  /* ---------- formatting ---------- */
  function formatBytes(n) {
    if (typeof n !== "number") return "";
    if (n < 1024) return `${n} B`;
    const [value, unit] = n < 1048576 ? [n / 1024, "KB"] : n < 1073741824 ? [n / 1048576, "MB"] : [n / 1073741824, "GB"];
    return `${value >= 100 ? Math.round(value) : value.toFixed(1)} ${unit}`;
  }

  function formatDuration(seconds) {
    if (typeof seconds !== "number" || !Number.isFinite(seconds) || seconds < 0) return "";
    if (seconds > 0 && seconds < 1) return "<1 s";
    const s = Math.round(seconds);
    if (s < 60) return `${s} s`;
    const m = Math.floor(s / 60);
    if (m < 60) return s % 60 ? `${m} min ${String(s % 60).padStart(2, "0")} s` : `${m} min`;
    return m % 60 ? `${Math.floor(m / 60)} h ${String(m % 60).padStart(2, "0")} min` : `${m / 60} h`;
  }

  const latencyText = (answer) => `${(Number(answer.latency_s) || 0).toFixed(1)} s`;

  const parseDate = (iso) => { const date = iso ? new Date(iso) : null; return date && !Number.isNaN(date.getTime()) ? date : null; };

  function relativeTime(iso) {
    const date = parseDate(iso);
    if (!date) return "";
    const s = Math.max(0, (Date.now() - date.getTime()) / 1000);
    const steps = [[45, 0, "just now"], [3600, 60, "min"], [86400, 3600, "h"], [2592000, 86400, "d"], [31536000, 2592000, "mo"], [Infinity, 31536000, "y"]];
    const [, unit, label] = steps.find(([limit]) => s < limit);
    return unit ? `${Math.max(1, Math.floor(s / unit))} ${label} ago` : label;
  }

  const timeEl = (iso) => {
    const date = parseDate(iso);
    const title = date && date.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
    return date ? h("time", { datetime: iso, title, text: relativeTime(iso) }) : null;
  };

  function safeUrl(value) {
    if (typeof value !== "string" || !/^https?:\/\//i.test(value)) return null;
    try { return new URL(value).href; } catch { return null; }
  }

  function prettyJson(value) {
    try { return JSON.stringify(typeof value === "string" ? JSON.parse(value) : value, null, 2) ?? ""; } catch { return String(value); }
  }

  /* ---------- API ---------- */
  class ApiError extends Error {
    constructor(status, message, expired = false) { super(message); Object.assign(this, { status, expired }); }
  }

  let expiredShown = false;
  function sessionExpired() {
    if (!expiredShown) {
      expiredShown = true;
      $("#session-banner").hidden = false;
      setTimeout(() => location.reload(), 1500);
    }
    return new ApiError(401, "Your session expired", true);
  }

  async function api(path, { method = "GET", json, body } = {}) {
    const headers = { "X-Requested-With": "XMLHttpRequest" };
    if (method !== "GET") headers["X-DocWiki-Studio"] = "1";
    if (json !== undefined) {
      headers["Content-Type"] = "application/json";
      body = JSON.stringify(json);
    }
    let res;
    try {
      res = await fetch(path, { method, headers, body, credentials: "same-origin", redirect: "manual" });
    } catch {
      throw new ApiError(0, "Cannot reach the Studio. Check your connection.");
    }
    if (res.status === 401 || res.type === "opaqueredirect") throw sessionExpired();
    /* Container Apps built-in auth answers an AJAX call without a valid session with an empty 403;
       the Studio's own refusals always carry a JSON {error}. */
    const isJson = (res.headers.get("content-type") || "").includes("application/json");
    if (res.status === 403 && !isJson) throw sessionExpired();
    const data = await res.json().catch(() => null);
    if (!res.ok) throw new ApiError(res.status, (data && data.error) || `Request failed (${res.status}).`);
    return data;
  }

  /* ---------- toasts, announcements, confirm dialog ---------- */
  function toast(message, kind = "info") {
    const el = h("div", { class: `toast toast-${kind}`, role: kind === "error" ? "alert" : "status" },
      icon(kind === "error" ? "alert" : kind === "success" ? "check" : "clock"),
      h("span", { class: "toast-text", text: message }),
      h("button", { type: "button", class: "icon-btn", "aria-label": "Dismiss", onclick: () => el.remove() }, icon("x")));
    $("#toasts").append(el);
    setTimeout(() => el.remove(), kind === "error" ? 9000 : 5000);
  }

  const report = (err) => { if (!err.expired) toast(err.message, "error"); };

  function announce(message) {
    $("#live").textContent = "";
    setTimeout(() => { $("#live").textContent = message; }, 50);
  }

  function confirmDialog({ title, body, items = [], confirmLabel }) {
    const dialog = $("#confirm-dialog");
    if (dialog.open) return Promise.resolve(false);
    $("#confirm-title").textContent = title;
    $("#confirm-body").textContent = body;
    $("#confirm-ok").textContent = confirmLabel;
    const shown = items.slice(0, 5).map(([name, size]) =>
      h("li", null, h("span", { class: "dialog-file", text: name }), size ? h("span", { class: "muted", text: formatBytes(size) }) : null));
    if (items.length > 5) shown.push(h("li", { class: "muted", text: `and ${items.length - 5} more` }));
    fill($("#confirm-items"), shown);
    dialog.returnValue = "";
    return new Promise((resolve) => {
      dialog.addEventListener("close", () => resolve(dialog.returnValue === "ok"), { once: true });
      dialog.showModal();
    });
  }

  /* ---------- /api/me ---------- */
  function applyMe() {
    const me = state.me;
    const wiki = safeUrl(me.wiki_url);
    const signOut = typeof me.sign_out_url === "string" && /^(\/|https?:\/\/)/.test(me.sign_out_url) ? me.sign_out_url : null;
    $("#wiki-link").hidden = !wiki;
    if (wiki) $("#wiki-link").setAttribute("href", wiki);
    $("#user-chip").hidden = !me.user;
    $("#user-name").textContent = me.user || "";
    $("#user-avatar").textContent = (me.user || "?").trim().charAt(0).toUpperCase();
    $("#signout-link").hidden = !signOut;
    if (signOut) $("#signout-link").setAttribute("href", signOut);
    const extensions = me.extensions || [];
    const main = [".pdf", ".docx", ".xlsx"].filter((ext) => extensions.includes(ext));
    $("#drop-hint").textContent = `Accepted: ${main.join(" ")} … up to ${me.max_upload_mb} MB`;
    $("#drop-hint").title = `Accepted file types: ${extensions.join(" ")}`;
    $("#uploads-left").textContent = typeof me.uploads_left === "number" ? `${plural(me.uploads_left, "upload")} left today` : "";
    $("#dropzone").classList.toggle("is-disabled", me.uploads_left === 0);
    $("#file-input").disabled = me.uploads_left === 0;
    syncAsk();
  }

  /* ---------- documents ---------- */
  function applyDocuments(data) {
    for (const doc of data.documents) {
      const before = state.seen.get(doc.path);
      if (before && before !== doc.status) announce(`${doc.path} is now ${doc.status}`);
      state.seen.set(doc.path, doc.status);
    }
    state.docs = data;
    renderDocuments();
  }

  function renderDocuments() {
    const data = state.docs;
    if (!data) return;
    const query = state.filter.trim().toLowerCase();
    const rows = data.documents.filter((d) => !query || d.path.toLowerCase().includes(query));
    syncList($("#doc-list"), rows, (d) => d.path, (d) => JSON.stringify([d, relativeTime(d.modified), state.sizes.get(d.path)]), docRow);
    const empty = $("#doc-empty");
    empty.hidden = rows.length > 0;
    empty.textContent = data.documents.length ? "No document matches the filter." : "No document yet. Drop a file above to start the pipeline.";
    const pills = Object.entries(data.counts).filter(([, n]) => n > 0).map(([status, n]) =>
      h("span", { class: `count-pill tone-${(DOC_STATUS[status] || [])[1] || "muted"}` }, h("b", { text: n }), ` ${status}`));
    fill($("#doc-summary"), h("span", { class: "doc-total", text: plural(data.total, "document") }), pills,
      data.unreadable_states ? h("span", { class: "text-warn", text: `${plural(data.unreadable_states, "state file")} unreadable` }) : null);
  }

  function extBadge(path) {
    const ext = ((/\.([^./]+)$/.exec(path) || [])[1] || "").toLowerCase();
    return h("span", { class: `ext ext-${EXT_FAMILY[ext] || "txt"}`, "aria-hidden": "true", text: (ext === "markdown" ? "md" : ext).slice(0, 4).toUpperCase() || "FILE" });
  }

  function statusChip(status) {
    const [label, tone] = DOC_STATUS[status] || [status, "muted"];
    return h("span", { class: `status status-${status} tone-${tone}`, dataset: { status }, text: label });
  }

  function docRow(d) {
    const slash = d.path.lastIndexOf("/");
    const link = safeUrl(d.wiki_url);
    const size = typeof d.size === "number" ? d.size : state.sizes.get(d.path);
    const meta = [formatBytes(size), d.modified ? relativeTime(d.modified) : "", d.stage && d.status !== "done" ? `stage ${d.stage}` : "",
      d.status === "done" && !d.in_release ? "not in the served release yet" : ""].filter(Boolean);
    return h("li", { class: `doc doc-${d.status}`, dataset: { path: d.path, status: d.status } },
      extBadge(d.path),
      h("div", { class: "doc-main" },
        h("div", { class: "doc-line" },
          h("span", { class: "doc-name" }, h("span", { class: "doc-folder", text: slash >= 0 ? d.path.slice(0, slash + 1) : "" }), h("span", { class: "doc-file", text: d.path.slice(slash + 1) })),
          statusChip(d.status)),
        h("div", { class: "doc-meta" },
          h("span", { text: meta.join(" · ") || "—" }),
          link ? h("a", { class: "doc-link", href: link, target: "_blank", rel: "noopener noreferrer" }, "Open in wiki", icon("external")) : null),
        (d.status === "failed" || d.status === "quarantined") && d.last_error ? h("p", { class: "doc-error", text: d.last_error }) : null));
  }

  /* ---------- uploads ---------- */
  const encodePath = (path) => path.split("/").map(encodeURIComponent).join("/");
  const extOf = (name) => (/\.[^./]+$/.exec(name) || [""])[0].toLowerCase();

  function addFiles(files) {
    const me = state.me;
    if (!me) return toast("The Studio is still loading, try again in a moment.", "info");
    if (me.uploads_left === 0) return toast("The daily upload allowance is used up.", "error");
    const folder = $("#folder-input").value.split("/").map((part) => part.trim()).filter(Boolean);
    const accepted = [];
    for (const file of files) {
      const entry = { id: ++uploadSeq, file, path: [...folder, file.name].join("/"), state: "queued", message: "" };
      if (uploads.some((u) => u.path === entry.path && (u.state === "queued" || u.state === "uploading"))) continue;
      const ext = extOf(file.name);
      const problem = !(me.extensions || []).includes(ext) ? `Unsupported file type ${ext || "(none)"}`
        : !file.size ? "The file is empty"
          : file.size > me.max_upload_mb * 1048576 ? `Larger than ${me.max_upload_mb} MB` : "";
      if (problem) Object.assign(entry, { state: "error", message: problem });
      else accepted.push(entry);
      uploads.push(entry);
    }
    renderUploads();
    if (accepted.length) confirmUpload(accepted);
  }

  async function confirmUpload(entries) {
    const ok = await confirmDialog({
      title: "Upload and start a pipeline run?", body: RUN_COST_WARNING, confirmLabel: "Upload",
      items: entries.map((e) => [`raw/${e.path}`, e.file.size]),
    });
    if (!ok) { entries.forEach(removeUpload); return; }
    let halted = false;
    for (const entry of entries) {
      if (halted) Object.assign(entry, { state: "error", message: "Skipped: the daily upload allowance is used up." });
      else halted = (await uploadOne(entry, false)) === 429;
    }
    renderUploads();
    refreshAll();
  }

  async function uploadOne(entry, replace) {
    Object.assign(entry, { state: "uploading", message: "Uploading…" });
    renderUploads();
    let failure = null;
    try {
      const res = await api(`/api/documents/${encodePath(entry.path)}${replace ? "?replace=1" : ""}`, { method: "PUT", body: entry.file });
      Object.assign(entry, { state: "done", message: res.replaced ? "Replaced. The pipeline will recompile it." : "Uploaded. The pipeline picks it up shortly." });
      state.sizes.set(entry.path, res.size);
      if (state.me && typeof res.uploads_left === "number") { state.me.uploads_left = res.uploads_left; applyMe(); }
      toast(`${entry.path} uploaded`, "success");
      setTimeout(() => removeUpload(entry), 9000);
    } catch (err) {
      if (err.expired) return err.status;
      failure = err.status;
      if (err.status === 409) Object.assign(entry, { state: "exists", message: "Already exists in the pipeline input." });
      else Object.assign(entry, { state: "error", message: err.message });
    }
    renderUploads();
    return failure;
  }

  async function replaceUpload(entry) {
    const ok = await confirmDialog({
      title: "Replace this document?", body: `raw/${entry.path} already exists. ${RUN_COST_WARNING}`, confirmLabel: "Replace",
    });
    if (!ok) return;
    await uploadOne(entry, true);
    refreshAll();
  }

  function removeUpload(entry) {
    const i = uploads.indexOf(entry);
    if (i >= 0) uploads.splice(i, 1);
    renderUploads();
  }

  const renderUploads = () => syncList($("#upload-list"), uploads, (e) => e.id, (e) => `${e.state}|${e.message}`, uploadItem);

  function uploadItem(e) {
    const tone = { queued: "muted", uploading: "info", done: "ok", exists: "warn", error: "bad" }[e.state];
    const closable = e.state === "error" || e.state === "exists";
    return h("li", { class: `upload tone-${tone}`, dataset: { state: e.state } },
      e.state === "uploading" ? h("span", { class: "spinner", "aria-hidden": "true" }) : icon({ queued: "clock", done: "check", exists: "alert", error: "x" }[e.state], "upload-ic"),
      h("div", { class: "upload-text" }, h("span", { class: "upload-name", text: e.path }), h("span", { class: "upload-msg", text: e.message || "Waiting for your confirmation" })),
      e.state === "exists" ? h("button", { type: "button", class: "btn btn-secondary btn-sm", text: "Replace", onclick: () => replaceUpload(e) }) : null,
      closable ? h("button", { type: "button", class: "icon-btn", "aria-label": `Dismiss ${e.path}`, onclick: () => removeUpload(e) }, icon("x")) : null,
      e.state === "uploading" ? h("span", { class: "bar", "aria-hidden": "true" }, h("i")) : null);
  }

  function wireUploads() {
    const zone = $("#dropzone");
    const input = $("#file-input");
    const hasFiles = (e) => e.dataTransfer && Array.from(e.dataTransfer.types || []).includes("Files");
    input.addEventListener("change", () => { const files = Array.from(input.files); input.value = ""; addFiles(files); });
    for (const type of ["dragenter", "dragover"]) {
      zone.addEventListener(type, (e) => { if (hasFiles(e)) { e.preventDefault(); zone.classList.add("is-over"); } });
    }
    zone.addEventListener("dragleave", () => zone.classList.remove("is-over"));
    zone.addEventListener("drop", (e) => { zone.classList.remove("is-over"); if (hasFiles(e)) addFiles(Array.from(e.dataTransfer.files)); });
    for (const type of ["dragover", "drop"]) window.addEventListener(type, (e) => { if (hasFiles(e)) e.preventDefault(); });
  }

  /* ---------- pipeline ---------- */
  function renderPipeline() {
    const p = state.pipeline;
    if (!p) return;
    const [text, tone] = p.queued == null ? ["unknown", "unknown"] : p.queued > 0 ? [`${p.queued} waiting`, "busy"] : ["idle", "idle"];
    $("#queue-pill").className = `queue queue-${tone}`;
    fill($("#queue-pill"), h("i", { class: "dot" }), "Queue: ", h("b", { text }));
    renderRelease(p.release);
    syncList($("#run-list"), p.runs, (r) => r.run_id, (r) => JSON.stringify([r, relativeTime(r.started_at), state.runOpen.get(r.run_id), formatDuration(runSeconds(r))]), runItem);
    $("#run-empty").hidden = p.runs.length > 0;
    $("#run-banner").hidden = !(p.runs[0] && p.runs[0].status === "running");
  }

  function renderRelease(rel) {
    const box = $("#release-box");
    if (!rel) return fill(box, h("p", { class: "muted", text: "No release has been published yet." }));
    const link = safeUrl(rel.wiki_url);
    const count = (n, word) => (n == null ? `${word}s: —` : plural(n, word));
    fill(box,
      h("div", { class: "release-top" }, h("span", { class: "eyebrow", text: "Served release" }), h("span", { class: "badge tone-muted", text: rel.audience })),
      h("code", { class: "release-id", text: rel.release_id }),
      h("p", { class: "release-meta" }, "Published ", timeEl(rel.published_at), ` · ${count(rel.sources, "source")} · ${count(rel.pages, "page")}`),
      link ? h("a", { class: "btn btn-secondary btn-sm", href: link, target: "_blank", rel: "noopener noreferrer" }, "Open the wiki", icon("external")) : null);
  }

  function runSeconds(run) {
    const start = parseDate(run.started_at);
    const end = parseDate(run.finished_at);
    if (run.status === "running" && start) return (Date.now() - start.getTime()) / 1000;
    return start && end ? (end - start) / 1000 : run.cost && run.cost.duration_s;
  }

  function runItem(run) {
    const [label, tone] = RUN_STATUS[run.status] || [run.status, "muted"];
    const open = state.runOpen.has(run.run_id) ? state.runOpen.get(run.run_id) : state.pipeline.runs.indexOf(run) < 2;
    const card = h("details", { class: "run-card", open },
      h("summary", null,
        h("span", { class: `badge tone-${tone} badge-${run.status}`, text: label }),
        h("span", { class: "run-kind" }, run.kind, h("span", { class: "muted", text: ` · ${run.requested_by}` })),
        run.is_current ? h("span", { class: "badge tone-ok badge-outline", text: "current" }) : null,
        h("span", { class: "run-when" }, timeEl(run.started_at))),
      h("div", { class: "run-body" }, runCounts(run), stageBar(run), runGates(run), runFacts(run)));
    card.addEventListener("toggle", () => state.runOpen.set(run.run_id, card.open));
    return h("li", { class: `run run-${run.status}` }, card);
  }

  function runCounts(run) {
    const c = run.counts || {};
    const part = (key, bad) => (c[key] > 0 ? h("span", { class: `count${bad ? " count-bad" : ""}`, text: `${c[key]} ${key}` }) : null);
    const parts = [part("new"), part("changed"), part("deleted"), part("unchanged"), part("quarantined", true), part("failed", true)].filter(Boolean);
    return h("p", { class: "run-counts" }, h("span", { class: "muted", text: `${plural(c.sources_total || 0, "source")}:` }),
      parts.length ? parts : h("span", { class: "muted", text: "no changes" }));
  }

  function stageBar(run) {
    if (!run.stages.length) return null;
    const known = new Map(run.stages.map((s) => [s.stage, s]));
    const order = [...STAGES, ...run.stages.map((s) => s.stage).filter((name) => !STAGES.includes(name))];
    const last = Math.max(...order.map((name, i) => (known.has(name) ? i : -1)));
    const bar = h("ol", { class: "stagebar", "aria-label": "Pipeline stages" });
    order.forEach((name, i) => {
      const s = known.get(name);
      const status = s ? s.status : run.status === "running" && i === last + 1 ? "running" : "todo";
      const tip = s
        ? [s.status, s.duration_s > 0 && formatDuration(s.duration_s), s.items && plural(s.items, "item"), s.cache_hits && `${s.cache_hits} cached`, s.failures && plural(s.failures, "failure")]
        : [status === "running" ? "in progress" : i > last ? "not reached" : "no report"];
      const seg = h("li", { class: `stage stage-${status}`, title: [name, ...tip].filter(Boolean).join(" · ") });
      seg.style.flexGrow = String(1 + Math.sqrt((s && s.duration_s) || 0));
      bar.append(seg);
    });
    const failed = run.stages.filter((s) => s.status === "failed").map((s) => s.stage);
    const ran = run.stages.length === order.length ? `${order.length} stages` : `${run.stages.length} of ${order.length} stages ran`;
    return h("div", { class: "stages" }, bar, h("p", { class: "stage-caption", text: ran + (failed.length ? ` · failed at ${failed.join(", ")}` : "") }));
  }

  function runGates(run) {
    const { summary = {}, not_passing: failing = [] } = run.gates || {};
    const total = Object.values(summary).reduce((a, b) => a + b, 0);
    if (!total) return null;
    const keys = ["pass", "warn", "fail", "skipped"].filter((k) => summary[k]);
    keys.push(...Object.keys(summary).filter((k) => summary[k] && !keys.includes(k)));
    return h("div", { class: "run-gates" },
      h("p", null, h("b", { text: plural(total, "gate") }), `: ${keys.map((k) => `${summary[k]} ${k}`).join(", ")}`),
      failing.length ? h("ul", { class: "gate-list" }, failing.map((g) =>
        h("li", { class: `gate tone-${g.status === "fail" ? "bad" : "warn"}` },
          h("code", { text: g.gate }), ` ${g.name} · ${g.status}`, g.blocking ? h("span", { class: "badge tone-bad badge-outline", text: "blocking" }) : null))) : null);
  }

  function runFacts(run) {
    const duration = formatDuration(runSeconds(run));
    const cost = run.cost || {};
    const facts = [
      duration ? h("span", { class: "fact" }, icon("clock"), run.status === "running" ? `running for ${duration}` : duration) : null,
      typeof cost.total === "number" ? h("span", { class: "fact" }, icon("coin"), `${cost.total > 0 && cost.total < 0.01 ? "<0.01" : cost.total.toFixed(2)} ${cost.currency || "USD"}`) : null,
      run.errors_total ? h("span", { class: "fact text-bad", text: plural(run.errors_total, "error") }) : null,
      run.warnings_total ? h("span", { class: "fact text-warn", text: plural(run.warnings_total, "warning") }) : null,
    ].filter(Boolean);
    return facts.length ? h("p", { class: "run-facts" }, facts) : null;
  }

  /* ---------- safe Markdown (paragraphs, lists, tables, code, bold, inline code, citations) ---------- */
  const INLINE = /`([^`\n]+)`|\*\*(.+?)\*\*|\[\^?(\d{1,3}(?:\s*,\s*\d{1,3})*)\](?![(:])/;
  const TABLE_SEP = /^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$/;
  const cells = (line) => line.trim().replace(/^\||\|$/g, "").split("|").map((cell) => cell.trim());

  function citation(n, sources) {
    const source = sources.get(n);
    const href = source && safeUrl(source.url);
    const tip = source ? [source.title, source.locator_label].filter(Boolean).join(" — ") : "No matching source";
    const label = `[${n}]`;
    return h("sup", { class: source ? "cite" : "cite cite-missing" },
      href ? h("a", { href, target: "_blank", rel: "noopener noreferrer", title: tip, text: label }) : h("span", { title: tip, text: label }));
  }

  function inline(text, sources) {
    const re = new RegExp(INLINE.source, "g");
    const out = [];
    let last = 0;
    let m;
    while ((m = re.exec(text))) {
      if (m.index > last) out.push(text.slice(last, m.index));
      if (m[1] !== undefined) out.push(h("code", { text: m[1] }));
      else if (m[2] !== undefined) out.push(h("strong", null, inline(m[2], sources)));
      else out.push(...m[3].split(",").map((n) => citation(Number(n), sources)));
      last = re.lastIndex;
    }
    if (last < text.length) out.push(text.slice(last));
    return out;
  }

  function renderMarkdown(text, sources) {
    const out = document.createDocumentFragment();
    const lines = String(text).replace(/\r\n?/g, "\n").split("\n");
    let para = [];
    let list = null;
    let i = 0;
    const flush = () => {
      if (para.length) out.append(h("p", null, inline(para.join(" "), sources)));
      para = [];
    };
    while (i < lines.length) {
      const line = lines[i++];
      const trimmed = line.trim();
      let match;
      if (trimmed.startsWith("```")) {
        flush(); list = null;
        const code = [];
        while (i < lines.length && !lines[i].trim().startsWith("```")) code.push(lines[i++]);
        i += 1;
        out.append(h("pre", { class: "md-code" }, h("code", { text: code.join("\n") })));
      } else if (!trimmed) {
        flush(); list = null;
      } else if (trimmed.includes("|") && i < lines.length && TABLE_SEP.test(lines[i])) {
        flush(); list = null;
        const head = cells(trimmed);
        const rows = [];
        i += 1;
        while (i < lines.length && lines[i].trim() && lines[i].includes("|")) rows.push(cells(lines[i++]));
        out.append(h("div", { class: "md-table" }, h("table", null,
          h("thead", null, h("tr", null, head.map((c) => h("th", null, inline(c, sources))))),
          h("tbody", null, rows.map((row) => h("tr", null, row.map((c) => h("td", null, inline(c, sources)))))))));
      } else if ((match = /^\s*([-*•]|\d{1,3}[.)])\s+(.+)$/.exec(line))) {
        flush();
        const ordered = /\d/.test(match[1]);
        if (!list || list.ordered !== ordered) {
          list = { ordered, el: h(ordered ? "ol" : "ul", ordered ? { start: parseInt(match[1], 10) } : null) };
          out.append(list.el);
        }
        list.el.append(h("li", null, inline(match[2], sources)));
      } else if ((match = /^\s{0,3}#{1,6}\s+(.*?)\s*#*\s*$/.exec(line))) {
        flush(); list = null;
        out.append(h("p", { class: "md-heading" }, inline(match[1], sources)));
      } else if (list && /^\s{2,}\S/.test(line)) {
        list.el.lastElementChild.append(" ", ...inline(trimmed, sources));
      } else {
        list = null;
        para.push(trimmed);
      }
    }
    flush();
    return out;
  }

  /* ---------- agents: asking, polling, approvals, answers ---------- */
  function setAgent(name) {
    state.agent = name;
    $(`input[name="agent"][value="${name}"]`).checked = true;
    document.querySelectorAll("[data-for]").forEach((el) => { el.hidden = el.dataset.for !== name; });
    $("#ask-input").placeholder = AGENTS[name].placeholder;
    syncAsk();
  }

  function syncAsk() {
    const me = state.me;
    const busy = turns.some((t) => t.active);
    const agents = me ? me.agents || [] : [];
    const left = me ? me.questions_left : 0;
    const button = $("#ask-btn");
    button.disabled = busy || !agents.includes(state.agent) || !(left > 0);
    button.title = me && !(left > 0) ? "The daily question limit is reached" : busy ? "A question is still running" : "";
    $("#questions-left").textContent = me ? `${plural(left, "question")} left today` : "";
    document.querySelectorAll('input[name="agent"]').forEach((radio) => { radio.disabled = !!me && !agents.includes(radio.value); });
    const note = $("#agent-note");
    note.hidden = !me || agents.length > 0;
    note.textContent = "The agents are not configured on this Studio yet, so questions are disabled.";
  }

  async function ask() {
    if ($("#ask-btn").disabled) return;
    const box = $("#ask-input");
    const question = box.value.trim();
    if (!question) { box.focus(); return toast("Type a question first.", "info"); }
    $("#ask-btn").disabled = true;
    try {
      const res = await api("/api/ask", { method: "POST", json: { agent: state.agent, question } });
      state.me.questions_left = res.questions_left;
      box.value = "";
      addTurn(state.agent, question, res.job_id, null);
    } catch (err) {
      if (err.status === 409 && (await loadJobs())) toast("Another question is still running — showing it", "info");
      else report(err);
      syncAsk();
    }
  }

  function addTurn(agent, question, jobId, job) {
    if (turns.some((t) => t.jobId === jobId)) return;
    const t = { agent, question, jobId, job, active: !job || ACTIVE.has(job.status), base: job ? job.elapsed_s : 0, syncedAt: performance.now(), sig: "" };
    t.statusEl = h("span", { class: "status" });
    t.stateEl = h("div", { class: "turn-state" });
    t.el = h("details", { class: `turn turn-${agent}`, open: true },
      h("summary", null,
        h("span", { class: `agent-tag agent-${agent}` }, icon(AGENTS[agent].icon), AGENTS[agent].label),
        h("span", { class: "turn-q", text: question }), t.statusEl),
      h("div", { class: "turn-body" }, t.stateEl));
    turns.forEach((other) => { other.el.open = false; });
    turns.unshift(t);
    $("#thread").prepend(t.el);
    $("#thread-empty").hidden = true;
    updateTurn(t);
    syncAsk();
    if (t.active) track(t);
  }

  const nap = (t, ms) => new Promise((resolve) => {
    const id = setTimeout(resolve, ms);
    t.wake = () => { clearTimeout(id); resolve(); };
  });

  async function track(t) {
    let failures = 0;
    while (t.active) {
      try {
        const job = await api(`/api/jobs/${encodeURIComponent(t.jobId)}`);
        failures = 0;
        Object.assign(t, { job, problem: "", base: job.elapsed_s, syncedAt: performance.now() });
        if (!ACTIVE.has(job.status)) t.active = false;
      } catch (err) {
        if (err.expired) return;
        if (err.status === 404) Object.assign(t, { gone: true, active: false });
        else if (++failures >= 3) t.problem = "Connection problem, retrying…";
      }
      updateTurn(t);
      if (t.active) await nap(t, failures ? POLL_MS * 2 : POLL_MS);
    }
    syncAsk();
    if (t.agent === "librarian") refreshAll();
  }

  function updateTurn(t) {
    const status = t.gone ? "gone" : t.job ? t.job.status : "running";
    const [label, tone] = TURN_STATUS[status];
    const latency = status === "done" && t.job.answer ? ` · ${latencyText(t.job.answer)}` : "";
    t.statusEl.className = `status tone-${tone}${ACTIVE.has(status) ? " is-live" : ""}`;
    t.statusEl.textContent = label + latency;
    const sig = JSON.stringify([status, t.job && t.job.approvals, t.job && !!t.job.answer, t.problem]);
    if (sig === t.sig) return;
    const first = t.sig === "";
    t.sig = sig;
    fill(t.stateEl, stateNodes(t, status));
    if (!first) announce(`${AGENTS[t.agent].label}: ${label}`);
  }

  function askAgain(t) {
    setAgent(t.agent);
    $("#ask-input").value = t.question;
    $("#ask-input").focus();
  }

  function stateNodes(t, status) {
    const job = t.job || {};
    const approvals = (job.approvals || []).map((a) => approvalCard(t, a));
    if (ACTIVE.has(status)) return [workingLine(t, status), ...approvals];
    if (status === "done" && job.answer) return [...approvals, answerCard(t)];
    const cancelled = status === "cancelled";
    const message = status === "gone" ? "The Studio restarted and forgot this question; ask it again."
      : cancelled ? "You cancelled this question." : job.error || "The agent call failed.";
    return [h("div", { class: `alert alert-${cancelled ? "muted" : "bad"}`, role: cancelled ? null : "alert" },
      icon(cancelled ? "x" : "alert"),
      h("div", { class: "alert-text" }, h("strong", { text: cancelled ? "Cancelled" : "The question failed" }), h("p", { text: message })),
      h("button", { type: "button", class: "btn btn-secondary btn-sm", text: "Ask again", onclick: () => askAgain(t) })), ...approvals];
  }

  const elapsedText = (t) => formatDuration(Math.floor(t.base + (performance.now() - t.syncedAt) / 1000));

  function workingLine(t, status) {
    t.elapsedEl = h("span", { class: "elapsed", text: elapsedText(t) });
    return h("div", { class: "working" },
      h("span", { class: "dots", "aria-hidden": "true" }, h("i"), h("i"), h("i")),
      h("span", { class: "working-text", text: status === "waiting_approval" ? "Waiting for your decision…" : AGENTS[t.agent].working }),
      t.elapsedEl,
      t.problem ? h("span", { class: "text-warn", text: t.problem }) : null,
      h("button", { type: "button", class: "btn btn-quiet btn-sm", text: "Cancel", onclick: () => cancelTurn(t) }));
  }

  async function cancelTurn(t) {
    try { await api(`/api/jobs/${encodeURIComponent(t.jobId)}`, { method: "DELETE" }); } catch (err) { if (err.status !== 409) report(err); }
    if (t.wake) t.wake();
  }

  function approvalCard(t, a) {
    if (a.state !== "pending") {
      const approved = a.state === "approved";
      return h("p", { class: `decided tone-${approved ? "ok" : "bad"}` }, icon(approved ? "check" : "x"), h("code", { text: a.name }), ` ${a.state}`);
    }
    const buttons = [
      h("button", { type: "button", class: "btn btn-primary", onclick: () => decide(t, a, true, buttons) }, icon("check"), "Approve"),
      h("button", { type: "button", class: "btn btn-danger", onclick: () => decide(t, a, false, buttons) }, icon("x"), "Deny"),
    ];
    return h("div", { class: "approval", role: "group", "aria-label": `Approval needed for ${a.name}` },
      h("div", { class: "approval-head" }, icon("shield"), h("strong", null, `The ${AGENTS[t.agent].label} wants to run `, h("code", { text: a.name })),
        a.server_label ? h("span", { class: "muted", text: a.server_label }) : null),
      h("pre", { class: "approval-args", text: prettyJson(a.arguments) }),
      RISKY_TOOLS.has(a.name) ? h("p", { class: "approval-note", text: "Starting or re-running ingestion triggers a pipeline run (minutes, model costs)." }) : null,
      h("div", { class: "approval-actions" }, buttons));
  }

  async function decide(t, approval, approve, buttons) {
    buttons.forEach((button) => { button.disabled = true; });
    try {
      await api(`/api/jobs/${encodeURIComponent(t.jobId)}/approvals/${encodeURIComponent(approval.id)}`, { method: "POST", json: { approve } });
    } catch (err) {
      report(err);
      buttons.forEach((button) => { button.disabled = false; });
    }
    if (t.wake) t.wake();
  }

  function answerCard(t) {
    const answer = t.job.answer;
    const sources = answer.sources || [];
    const bySource = new Map(sources.map((s) => [s.n, s]));
    const calls = answer.tool_calls || [];
    const tokens = answer.usage && answer.usage.total_tokens;
    const receipt = [`${answer.agent}${answer.version ? ` v${answer.version}` : ""}`, plural(calls.length, "tool call"),
      tokens ? `${tokens.toLocaleString("en-US")} tokens` : "", latencyText(answer)].filter(Boolean).join(" · ");
    return h("div", { class: "answer" },
      h("div", { class: "answer-body" }, answer.body ? renderMarkdown(answer.body, bySource) : h("p", { class: "muted", text: "The agent returned no text." })),
      sources.length ? h("section", { class: "sources" }, h("h4", { text: "Sources" }), h("ul", null, sources.map(sourceItem))) : null,
      calls.length ? h("details", { class: "trace" }, h("summary", { text: `How the agent worked · ${plural(calls.length, "tool call")}` }), h("ol", { class: "tool-list" }, calls.map(toolItem))) : null,
      h("p", { class: "receipt", text: receipt }));
  }

  function sourceItem(s) {
    const href = safeUrl(s.url);
    const title = s.title || s.path || "Untitled source";
    const [label, tone] = PROVENANCE[s.provenance] || [s.provenance, "muted"];
    return h("li", null,
      h("span", { class: "src-n", text: `[${s.n}]` }),
      href ? h("a", { href, target: "_blank", rel: "noopener noreferrer", text: title }) : h("span", { text: title }),
      s.locator_label ? h("span", { class: "muted", text: ` — ${s.locator_label}` }) : null,
      s.provenance ? h("span", { class: `badge tone-${tone}`, text: label }) : null);
  }

  function toolItem(call) {
    const tone = { completed: "ok", denied: "bad", failed: "bad", error: "bad" }[call.status] || "muted";
    const args = call.arguments && call.arguments !== "{}" ? prettyJson(call.arguments) : "";
    return h("li", { class: "tool" },
      h("span", { class: "tool-ic" }, icon(TOOL_ICONS[call.name] || "tool")),
      h("code", { class: "tool-name", text: call.name }),
      h("span", { class: `badge tone-${tone}`, text: call.status }),
      call.server_label ? h("span", { class: "muted", text: call.server_label }) : null,
      call.error ? h("p", { class: "tool-error", text: call.error }) : null,
      args ? h("details", { class: "tool-args" }, h("summary", { text: "arguments" }), h("pre", { text: args })) : null);
  }

  /* The server keeps the questions of this Studio (every browser): add the ones this page does not show yet,
   oldest first so the newest ends on top, and attach to the running one. Resolves to its id, or null. */
  async function loadJobs() {
    let list;
    try { list = (await api("/api/jobs")) || {}; } catch { return null; }
    const missing = (list.jobs || []).filter((j) => AGENTS[j.agent] && !turns.some((t) => t.jobId === j.job_id)).reverse();
    const details = await Promise.allSettled(missing.map((j) => api(`/api/jobs/${encodeURIComponent(j.job_id)}`)));
    missing.forEach((j, i) => {
      const job = details[i].status === "fulfilled" ? details[i].value : null;
      if (job || j.job_id === list.active) addTurn(j.agent, j.question, j.job_id, job);
    });
    return list.active || null;
  }

  /* ---------- refresh loop ---------- */
  let refreshTimer = 0;
  let refreshing = false;
  let refreshAgain = false;

  async function refreshAll() {
    if (refreshing) { refreshAgain = true; return; }
    refreshing = true;
    clearTimeout(refreshTimer);
    const results = await Promise.allSettled([api("/api/documents"), api("/api/pipeline"), state.me ? null : api("/api/me")]);
    const [docs, pipe, me] = results;
    if (me.status === "fulfilled" && me.value) { state.me = me.value; applyMe(); }
    if (docs.status === "fulfilled") applyDocuments(docs.value);
    if (pipe.status === "fulfilled") { state.pipeline = pipe.value; renderPipeline(); }
    $("#conn-badge").hidden = !results.some((r) => r.status === "rejected" && !r.reason.expired);
    refreshing = false;
    if (refreshAgain) { refreshAgain = false; return refreshAll(); }
    scheduleRefresh();
  }

  function scheduleRefresh() {
    clearTimeout(refreshTimer);
    if (document.hidden) return;
    const busy = (state.docs && state.docs.documents.some((d) => d.status === "new" || d.status === "pending"))
      || (state.pipeline && state.pipeline.runs[0] && state.pipeline.runs[0].status === "running");
    refreshTimer = setTimeout(refreshAll, busy ? REFRESH_BUSY_MS : REFRESH_IDLE_MS);
  }

  /* ---------- start ---------- */
  function wire() {
    document.querySelectorAll("[data-icon]").forEach((el) => el.append(icon(el.dataset.icon)));
    document.querySelectorAll('input[name="agent"]').forEach((radio) =>
      radio.addEventListener("change", () => { if (radio.checked) setAgent(radio.value); }));
    $("#ask-form").addEventListener("submit", (e) => { e.preventDefault(); ask(); });
    $("#ask-input").addEventListener("keydown", (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "Enter") { e.preventDefault(); ask(); }
    });
    $("#samples").addEventListener("click", (e) => {
      const chip = e.target.closest(".sample");
      if (chip) { $("#ask-input").value = chip.textContent; $("#ask-input").focus(); }
    });
    $("#doc-filter").addEventListener("input", (e) => { state.filter = e.target.value; renderDocuments(); });
    const dialog = $("#confirm-dialog");
    $("#confirm-ok").addEventListener("click", () => dialog.close("ok"));
    $("#confirm-cancel").addEventListener("click", () => dialog.close("cancel"));
    dialog.addEventListener("click", (e) => { if (e.target === dialog) dialog.close("cancel"); });
    document.addEventListener("visibilitychange", () => { if (document.hidden) clearTimeout(refreshTimer); else refreshAll(); });
    setInterval(() => {
      for (const t of turns) if (t.active && t.elapsedEl) t.elapsedEl.textContent = elapsedText(t);
    }, 500);
  }

  async function init() {
    wire();
    wireUploads();
    setAgent("researcher");
    await Promise.all([refreshAll(), loadJobs()]);
  }

  init();
})();
