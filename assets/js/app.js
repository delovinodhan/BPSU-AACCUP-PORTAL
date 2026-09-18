(() => {
  const config = window.PORTAL_CONFIG || {};
  const evidence = Array.isArray(window.EVIDENCE_DATA) ? window.EVIDENCE_DATA : [];
  const areaOrder = ["Area I","Area II","Area III","Area IV","Area V","Area VI","Area VII","Area VIII","Area IX","Area X"];

  const el = (id) => document.getElementById(id);
  const fmtDate = (value) => {
    if (!value) return "—";
    const d = new Date(value + (value.length === 10 ? "T00:00:00" : ""));
    return Number.isNaN(d.getTime()) ? value : new Intl.DateTimeFormat("en-PH", { year: "numeric", month: "short", day: "numeric" }).format(d);
  };
  const esc = (value = "") => String(value).replace(/[&<>'"]/g, (ch) => ({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"}[ch]));
  const tags = (item) => Array.isArray(item.tags) ? item.tags : String(item.tags || "").split(",").map(s => s.trim()).filter(Boolean);

  function renderStats() {
    el("stat-areas").textContent = areaOrder.length;
    el("stat-evidence").textContent = evidence.length;
    el("stat-linked").textContent = evidence.filter(item => item.fileUrl).length;
    el("stat-updated").textContent = fmtDate(config.lastUpdated);
  }

  function renderAreas() {
    const grid = el("area-grid");
    grid.innerHTML = areaOrder.map(area => {
      const roman = area.replace("Area ", "");
      const count = evidence.filter(item => item.area === area).length;
      const title = (config.areaTitles && config.areaTitles[area]) || "Official area title to be configured";
      return `<button class="area-card" type="button" data-area="${esc(area)}">
        <span class="area-roman">${esc(roman)}</span>
        <h3>${esc(title)}</h3>
        <p><span class="area-count">${count} published ${count === 1 ? "item" : "items"}</span></p>
      </button>`;
    }).join("");

    grid.querySelectorAll(".area-card").forEach(card => card.addEventListener("click", () => {
      el("area-filter").value = card.dataset.area;
      renderEvidence();
      document.querySelector("#evidence").scrollIntoView({ behavior: "smooth", block: "start" });
    }));
  }

  function populateFilters() {
    const areaFilter = el("area-filter");
    areaOrder.forEach(area => areaFilter.insertAdjacentHTML("beforeend", `<option value="${esc(area)}">${esc(area)}</option>`));

    const types = [...new Set(evidence.map(item => item.docType).filter(Boolean))].sort();
    types.forEach(type => el("type-filter").insertAdjacentHTML("beforeend", `<option value="${esc(type)}">${esc(type)}</option>`));

    const years = [...new Set(evidence.map(item => item.academicYear).filter(Boolean))].sort().reverse();
    years.forEach(year => el("year-filter").insertAdjacentHTML("beforeend", `<option value="${esc(year)}">${esc(year)}</option>`));
  }

  function filteredEvidence() {
    const q = el("search-input").value.trim().toLowerCase();
    const area = el("area-filter").value;
    const type = el("type-filter").value;
    const year = el("year-filter").value;

    return evidence.filter(item => {
      const haystack = [item.title, item.docCode, item.criterion, item.docType, item.academicYear, item.owner, item.description, ...tags(item)].join(" ").toLowerCase();
      return (!q || haystack.includes(q)) && (!area || item.area === area) && (!type || item.docType === type) && (!year || item.academicYear === year);
    }).sort((a,b) => (a.area || "").localeCompare(b.area || "") || (a.criterion || "").localeCompare(b.criterion || "") || (a.title || "").localeCompare(b.title || ""));
  }

  function renderEvidence() {
    const rows = filteredEvidence();
    const body = el("evidence-body");
    const tableWrap = document.querySelector(".table-wrap");
    const empty = el("empty-state");
    el("results-summary").textContent = `Showing ${rows.length} of ${evidence.length} published evidence ${evidence.length === 1 ? "item" : "items"}.`;

    if (!rows.length) {
      body.innerHTML = "";
      tableWrap.hidden = true;
      empty.hidden = false;
      el("empty-copy").textContent = evidence.length === 0
        ? "No evidence has been published yet. Add only approved records to assets/data/portal-data.js."
        : "No published evidence matches the current search and filters.";
      return;
    }

    tableWrap.hidden = false;
    empty.hidden = true;
    body.innerHTML = rows.map(item => {
      const tagHtml = tags(item).slice(0,4).map(t => `<span class="tag">${esc(t)}</span>`).join("");
      const action = item.fileUrl
        ? `<a class="doc-action" href="${esc(item.fileUrl)}" target="_blank" rel="noopener">Open file</a>`
        : `<button class="doc-action" type="button" data-detail="${esc(item.id || item.docCode)}">Details</button>`;
      return `<tr>
        <td><span class="doc-title">${esc(item.title || "Untitled evidence")}</span><span class="doc-code">${esc(item.docCode || "—")} · v${esc(item.version || 1)}</span>${tagHtml ? `<div class="tag-list">${tagHtml}</div>` : ""}</td>
        <td>${esc(item.area || "—")}</td>
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
        <div class="detail-item"><span>Document code</span><strong>${esc(item.docCode || "—")}</strong></div>
        <div class="detail-item"><span>Version</span><strong>${esc(item.version || 1)}</strong></div>
        <div class="detail-item"><span>Area</span><strong>${esc(item.area || "—")}</strong></div>
        <div class="detail-item"><span>Criterion / Indicator</span><strong>${esc(item.criterion || "—")}</strong></div>
        <div class="detail-item"><span>Document type</span><strong>${esc(item.docType || "—")}</strong></div>
        <div class="detail-item"><span>Academic year</span><strong>${esc(item.academicYear || "—")}</strong></div>
        <div class="detail-item"><span>Published</span><strong>${esc(fmtDate(item.publishedDate || item.updatedAt))}</strong></div>
        <div class="detail-item"><span>Owner / source</span><strong>${esc(item.owner || config.college || "—")}</strong></div>
      </div>
      ${item.description ? `<p class="dialog-description">${esc(item.description)}</p>` : ""}
      <div class="dialog-actions">${fileAction}</div>`;
    if (typeof dialog.showModal === "function") dialog.showModal();
  }

  function wireUi() {
    ["search-input","area-filter","type-filter","year-filter"].forEach(id => {
      const node = el(id);
      node.addEventListener(id === "search-input" ? "input" : "change", renderEvidence);
    });
    el("reset-filters").addEventListener("click", () => {
      el("search-input").value = "";
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
      toggle.setAttribute("aria-expanded", "false");
    }));
  }

  renderStats();
  renderAreas();
  populateFilters();
  wireUi();
  renderEvidence();
})();
