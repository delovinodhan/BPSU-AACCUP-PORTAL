(async () => {
  const config = window.PORTAL_CONFIG || {};
  const areaOrder = ["Area I","Area II","Area III","Area IV","Area V"];
  const programOrder = ["BSA","BSBA"];
  const secureWorkspaceBase = "https://bpsu-aaccup-dms.onrender.com";
  let evidence = Array.isArray(window.EVIDENCE_DATA) ? [...window.EVIDENCE_DATA] : [];
  let selectedProgram = "BSA";
  let secureWarmPromise = null;
  let pendingSecureUrl = secureWorkspaceBase + "/";

  const el = id => document.getElementById(id);
  const esc = (value = "") => String(value).replace(/[&<>'"]/g, ch => ({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"}[ch]));
  const fmtDate = value => {
    if (!value) return "—";
    const d = new Date(value + (value.length === 10 ? "T00:00:00" : ""));
    return Number.isNaN(d.getTime()) ? value : new Intl.DateTimeFormat("en-PH",{year:"numeric",month:"short",day:"numeric"}).format(d);
  };
  const tags = item => Array.isArray(item.tags) ? item.tags : String(item.tags || "").split(",").map(s=>s.trim()).filter(Boolean);
  const programName = code => (config.programs && config.programs[code]) || code || "Unspecified Program";
  const areaTitle = area => (config.areaTitles && config.areaTitles[area]) || "";

  function warmSecureWorkspace(timeoutMs = 70000) {
    if (secureWarmPromise) return secureWarmPromise;
    const controller = new AbortController();
    const timer = window.setTimeout(() => controller.abort(), timeoutMs);
    secureWarmPromise = fetch(`${secureWorkspaceBase}/health?ts=${Date.now()}`, {
      mode: "no-cors",
      cache: "no-store",
      signal: controller.signal
    }).then(() => true).catch(error => {
      secureWarmPromise = null;
      throw error;
    }).finally(() => window.clearTimeout(timer));
    return secureWarmPromise;
  }

  function setSecureLaunchState(state) {
    const panel = el("service-launch");
    const spinner = el("service-spinner");
    const actions = el("service-launch-actions");
    panel.hidden = false;
    if (state === "starting") {
      spinner.hidden = false;
      spinner.classList.remove("stopped");
      actions.hidden = true;
      el("service-launch-title").textContent = "Starting secure workspace…";
      el("service-launch-copy").textContent = "The secure service may need up to a minute to wake. Please keep this page open.";
    } else {
      spinner.hidden = true;
      actions.hidden = false;
      el("service-launch-title").textContent = "The secure workspace is taking longer than expected";
      el("service-launch-copy").textContent = "Try again, or open it directly after checking your internet connection.";
      el("service-direct").href = pendingSecureUrl;
    }
  }

  async function launchSecureWorkspace(url) {
    pendingSecureUrl = url;
    setSecureLaunchState("starting");
    try {
      await warmSecureWorkspace();
      window.location.assign(url);
    } catch (error) {
      console.warn("Secure workspace did not respond during warm-up.", error);
      setSecureLaunchState("error");
    }
  }

  function wireSecureWorkspace() {
    document.querySelectorAll("[data-secure-link]").forEach(link => link.addEventListener("click", event => {
      if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
      event.preventDefault();
      launchSecureWorkspace(link.href);
    }));
    el("service-retry").addEventListener("click", () => {
      secureWarmPromise = null;
      launchSecureWorkspace(pendingSecureUrl);
    });
    el("service-cancel").addEventListener("click", () => {
      el("service-launch").hidden = true;
    });
    window.setTimeout(() => warmSecureWorkspace().catch(() => {}), 750);
  }

  try {
    const res = await fetch("assets/data/evidence.json?ts=" + Date.now(), { cache: "no-store" });
    if (res.ok) {
      const json = await res.json();
      if (Array.isArray(json)) evidence = json;
    }
  } catch (err) {
    console.warn("Using embedded evidence fallback.", err);
  }

  function renderStats() {
    el("stat-programs").textContent = programOrder.length;
    el("stat-areas").textContent = areaOrder.length;
    el("stat-evidence").textContent = evidence.length;
    el("stat-linked").textContent = evidence.filter(item => item.fileUrl).length;
  }

  function renderProgramTabs() {
    const box = el("program-tabs");
    box.innerHTML = programOrder.map(code => {
      const count = evidence.filter(item => item.programCode === code).length;
      return `<button type="button" class="portal-program-tab ${selectedProgram===code?"active":""}" data-program="${code}">
        <span>${esc(code)}</span>
        <strong>${esc(programName(code))}</strong>
        <small>${count} published ${count===1?"item":"items"}</small>
      </button>`;
    }).join("");
    box.querySelectorAll("[data-program]").forEach(btn => btn.addEventListener("click", () => {
      selectedProgram = btn.dataset.program;
      el("program-filter").value = selectedProgram;
      renderProgramTabs();
      renderAreas();
      renderEvidence();
    }));
  }

  function renderAreas() {
    const grid = el("area-grid");
    grid.innerHTML = areaOrder.map(area => {
      const roman = area.replace("Area ","");
      const count = evidence.filter(item => item.programCode === selectedProgram && item.area === area).length;
      return `<button class="area-card" type="button" data-area="${esc(area)}">
        <span class="area-roman">${esc(roman)}</span>
        <h3>${esc(areaTitle(area))}</h3>
        <p><span class="area-count">${count} published ${count===1?"item":"items"}</span></p>
      </button>`;
    }).join("");
    grid.querySelectorAll(".area-card").forEach(card => card.addEventListener("click", () => {
      el("program-filter").value = selectedProgram;
      el("area-filter").value = card.dataset.area;
      renderEvidence();
      document.querySelector("#evidence").scrollIntoView({behavior:"smooth",block:"start"});
    }));
  }

  function populateFilters() {
    const programFilter = el("program-filter");
    programOrder.forEach(code => programFilter.insertAdjacentHTML("beforeend", `<option value="${esc(code)}">${esc(code)} — ${esc(programName(code))}</option>`));
    programFilter.value = selectedProgram;

    const areaFilter = el("area-filter");
    areaOrder.forEach(area => areaFilter.insertAdjacentHTML("beforeend", `<option value="${esc(area)}">${esc(area)} — ${esc(areaTitle(area))}</option>`));

    const types = [...new Set(evidence.map(item => item.docType).filter(Boolean))].sort();
    types.forEach(type => el("type-filter").insertAdjacentHTML("beforeend", `<option value="${esc(type)}">${esc(type)}</option>`));
    const years = [...new Set(evidence.map(item => item.academicYear).filter(Boolean))].sort().reverse();
    years.forEach(year => el("year-filter").insertAdjacentHTML("beforeend", `<option value="${esc(year)}">${esc(year)}</option>`));
  }

  function filteredEvidence() {
    const q = el("search-input").value.trim().toLowerCase();
    const program = el("program-filter").value;
    const area = el("area-filter").value;
    const type = el("type-filter").value;
    const year = el("year-filter").value;
    return evidence.filter(item => {
      const haystack = [item.title,item.docCode,item.criterion,item.docType,item.academicYear,item.owner,item.description,item.program,item.programCode,item.areaTitle,...tags(item)].join(" ").toLowerCase();
      return (!q || haystack.includes(q)) &&
        (!program || item.programCode === program) &&
        (!area || item.area === area) &&
        (!type || item.docType === type) &&
        (!year || item.academicYear === year);
    }).sort((a,b) => (a.programCode||"").localeCompare(b.programCode||"") || (a.area||"").localeCompare(b.area||"") || (a.criterion||"").localeCompare(b.criterion||"") || (a.title||"").localeCompare(b.title||""));
  }

  function renderEvidence() {
    const rows = filteredEvidence();
    const body = el("evidence-body");
    const tableWrap = document.querySelector(".table-wrap");
    const empty = el("empty-state");
    el("results-summary").textContent = `Showing ${rows.length} of ${evidence.length} published evidence ${evidence.length===1?"item":"items"}.`;

    if (!rows.length) {
      body.innerHTML = "";
      tableWrap.hidden = true;
      empty.hidden = false;
      el("empty-copy").textContent = evidence.length === 0
        ? "No evidence has been published yet. Ready-to-Publish files can be transferred from the BPSU CBA Staging Portal."
        : "No published evidence matches the current program, area, or filters.";
      return;
    }

    tableWrap.hidden = false;
    empty.hidden = true;
    body.innerHTML = rows.map(item => {
      const tagHtml = tags(item).slice(0,4).map(t=>`<span class="tag">${esc(t)}</span>`).join("");
      const action = item.fileUrl
        ? `<a class="doc-action" href="${esc(item.fileUrl)}" target="_blank" rel="noopener">Open file</a>`
        : `<button class="doc-action" type="button" data-detail="${esc(item.id || item.docCode)}">Details</button>`;
      return `<tr>
        <td><span class="doc-title">${esc(item.title || "Untitled evidence")}</span><span class="doc-code">${esc(item.docCode || "—")} · v${esc(item.version || 1)}</span>${tagHtml?`<div class="tag-list">${tagHtml}</div>`:""}</td>
        <td><strong>${esc(item.programCode || "—")}</strong><span class="doc-code">${esc(item.program || programName(item.programCode))}</span></td>
        <td>${esc(item.area || "—")}<span class="doc-code">${esc(item.areaTitle || areaTitle(item.area))}</span></td>
        <td>${esc(item.criterion || "—")}</td>
        <td>${esc(item.docType || "—")}</td>
        <td>${esc(item.academicYear || "—")}</td>
        <td>${esc(fmtDate(item.publishedDate || item.updatedAt))}</td>
        <td>${action}</td>
      </tr>`;
    }).join("");

    body.querySelectorAll("[data-detail]").forEach(btn => btn.addEventListener("click", () => {
      const item = evidence.find(x => (x.id || x.docCode) === btn.dataset.detail);
      if (item) openDialog(item);
    }));
  }

  function openDialog(item) {
    const dialog = el("document-dialog");
    el("dialog-title").textContent = item.title || "Evidence record";
    const fileAction = item.fileUrl ? `<a class="btn btn-maroon" href="${esc(item.fileUrl)}" target="_blank" rel="noopener">Open published file</a>` : `<span class="doc-action disabled">File not linked</span>`;
    el("dialog-content").innerHTML = `
      <div class="detail-grid">
        <div class="detail-item"><span>Program</span><strong>${esc(item.programCode || "—")} — ${esc(item.program || programName(item.programCode))}</strong></div>
        <div class="detail-item"><span>Document code</span><strong>${esc(item.docCode || "—")}</strong></div>
        <div class="detail-item"><span>Version</span><strong>${esc(item.version || 1)}</strong></div>
        <div class="detail-item"><span>Area</span><strong>${esc(item.area || "—")} — ${esc(item.areaTitle || areaTitle(item.area))}</strong></div>
        <div class="detail-item"><span>Criterion / Indicator</span><strong>${esc(item.criterion || "—")}</strong></div>
        <div class="detail-item"><span>Document type</span><strong>${esc(item.docType || "—")}</strong></div>
        <div class="detail-item"><span>Academic year</span><strong>${esc(item.academicYear || "—")}</strong></div>
        <div class="detail-item"><span>Published</span><strong>${esc(fmtDate(item.publishedDate || item.updatedAt))}</strong></div>
        <div class="detail-item"><span>Owner / source</span><strong>${esc(item.owner || config.college || "—")}</strong></div>
      </div>
      ${item.description?`<p class="dialog-description">${esc(item.description)}</p>`:""}
      <div class="dialog-actions">${fileAction}</div>`;
    if (typeof dialog.showModal === "function") dialog.showModal();
  }

  function wireUi() {
    ["search-input","program-filter","area-filter","type-filter","year-filter"].forEach(id => {
      const node = el(id);
      node.addEventListener(id === "search-input" ? "input" : "change", () => {
        if (id === "program-filter" && node.value) {
          selectedProgram = node.value;
          renderProgramTabs();
          renderAreas();
        }
        renderEvidence();
      });
    });
    el("reset-filters").addEventListener("click", () => {
      el("search-input").value = "";
      el("program-filter").value = selectedProgram;
      el("area-filter").value = "";
      el("type-filter").value = "";
      el("year-filter").value = "";
      renderEvidence();
    });
    el("print-btn").addEventListener("click", () => window.print());
    el("dialog-close").addEventListener("click", () => el("document-dialog").close());
    const toggle = document.querySelector(".menu-toggle");
    const nav = el("primary-nav");
    toggle.addEventListener("click", () => {
      const open = nav.classList.toggle("open");
      toggle.setAttribute("aria-expanded", String(open));
    });
    nav.querySelectorAll("a").forEach(link => link.addEventListener("click", () => {
      nav.classList.remove("open");
      toggle.setAttribute("aria-expanded","false");
    }));
  }

  renderStats();
  renderProgramTabs();
  renderAreas();
  populateFilters();
  wireUi();
  wireSecureWorkspace();
  renderEvidence();
})();
