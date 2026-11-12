/**
 * KnowledgeFlow RAG — Frontend Application Logic
 * Security: Strict DOM node creation; untrusted LLM output is never parsed as HTML.
 */

document.addEventListener("DOMContentLoaded", () => {
  // Elements
  const queryForm = document.getElementById("query-form");
  const queryInput = document.getElementById("query-input");
  const submitBtn = document.getElementById("submit-btn");
  const loadingState = document.getElementById("loading-state");
  const errorState = document.getElementById("error-state");
  const errorTitle = document.getElementById("error-title");
  const errorMessage = document.getElementById("error-message");
  const retryBtn = document.getElementById("retry-btn");
  const resultsArea = document.getElementById("results-area");
  const pipelineGuide = document.getElementById("pipeline-guide");
  const scopeLegend = document.getElementById("scope-legend");

  // Results & Traceability Elements
  const answerHeading = document.getElementById("answer-heading");
  const groundingStatusPill = document.getElementById("grounding-status-pill");
  const scopeBadge = document.getElementById("scope-badge");
  const answerContent = document.getElementById("answer-content");
  const abstentionBox = document.getElementById("abstention-box");

  const traceScope = document.getElementById("trace-scope");
  const traceSourcesCount = document.getElementById("trace-sources-count");
  const traceCitationsCount = document.getElementById("trace-citations-count");
  const traceGroundedState = document.getElementById("trace-grounded-state");
  const traceStampState = document.getElementById("trace-stamp-state");

  const techTableBody = document.getElementById("tech-table-body");
  const techJsonContent = document.getElementById("tech-json-content");

  // Evidence Ledger Elements
  const evidenceList = document.getElementById("evidence-list");
  const evidenceCountBadge = document.getElementById("evidence-count-badge");
  const evidenceEmpty = document.getElementById("evidence-empty");

  // Reference Query Buttons & Scope Inputs
  const referenceButtons = document.querySelectorAll(".ref-item-btn, .chip-btn");
  const scopeRadios = document.querySelectorAll('input[name="source_scope"]');

  let lastPayload = null;
  const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");

  // Initialize Reference Query Buttons
  referenceButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      const queryText = btn.getAttribute("data-query");
      if (queryText) {
        queryInput.value = queryText;
        const suggestedScope = btn.getAttribute("data-scope");
        const matchingScope = Array.from(scopeRadios).find((radio) => radio.value === suggestedScope);
        if (matchingScope) {
          matchingScope.checked = true;
          matchingScope.dispatchEvent(new Event("change", { bubbles: true }));
        }
        queryInput.focus();
      }
    });
  });

  // Scope Selector Legend Live Update
  scopeRadios.forEach((radio) => {
    radio.addEventListener("change", () => {
      if (radio.checked && scopeLegend) {
        const legendText = radio.getAttribute("data-legend");
        if (legendText) {
          scopeLegend.textContent = legendText;
        }
      }
    });
  });

  // Ctrl+Enter or Cmd+Enter to submit
  queryInput.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
      e.preventDefault();
      queryForm.requestSubmit();
    }
  });

  // Retry Button Handler
  retryBtn.addEventListener("click", () => {
    if (lastPayload) {
      executeQuery(lastPayload);
    }
  });

  // Form Submit Handler
  queryForm.addEventListener("submit", (e) => {
    e.preventDefault();
    const query = queryInput.value.trim();
    if (!query) {
      showError("Consulta requerida", "Por favor ingresa una pregunta o consulta válida.", 422);
      return;
    }

    const selectedScopeInput = document.querySelector('input[name="source_scope"]:checked');
    const sourceScope = selectedScopeInput && selectedScopeInput.value ? selectedScopeInput.value : null;

    const payload = {
      query: query,
      source_scope: sourceScope,
      k: null,
    };

    lastPayload = payload;
    executeQuery(payload);
  });

  /**
   * Execute Query against POST /api/query
   */
  async function executeQuery(payload) {
    hideError();
    showLoading(true);
    resultsArea.classList.add("hidden");
    if (pipelineGuide) pipelineGuide.classList.add("is-processing");

    try {
      const response = await fetch("/api/query", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Accept": "application/json",
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        if (response.status === 422) {
          showError("Consulta inválida", "La consulta no cumple los requisitos esperados.", 422);
        } else if (response.status === 503) {
          showError("Índice no disponible", "El índice documental no está listo o se encuentra desactualizado (503).", 503);
        } else if (response.status === 500) {
          showError("Error de procesamiento", "El motor no pudo completar la consulta (500). Revisa el servicio antes de reintentar.", 500);
        } else {
          showError("Error de procesamiento", `El servidor retornó estado HTTP ${response.status}.`, response.status);
        }
        return;
      }

      const data = await response.json();
      renderResults(data);
    } catch (networkErr) {
      showError("Error de conexión", "No se pudo establecer comunicación con el servidor KnowledgeFlow RAG.", 0);
    } finally {
      showLoading(false);
    }
  }

  /**
   * Render QueryResponse safely to the DOM
   */
  function renderResults(data) {
    // 1. Traceability Strip & Header Meta
    const isAbstained = Boolean(data.abstained);
    const scopeUsed = formatScope(data.source_scope);
    const citations = Array.isArray(data.citations) ? data.citations : [];
    const sources = Array.isArray(data.sources) ? data.sources : [];

    scopeBadge.textContent = `ALCANCE: ${scopeUsed}`;
    traceScope.textContent = scopeUsed;
    traceSourcesCount.textContent = sources.length.toString();
    traceCitationsCount.textContent = citations.length.toString();

    // 2. Abstention vs Grounded State
    if (isAbstained) {
      answerHeading.textContent = "Consulta sin Evidencia Suficiente";
      groundingStatusPill.textContent = "ABSTENCIÓN";
      groundingStatusPill.className = "status-pill status-abstain";

      traceGroundedState.textContent = "EVIDENCIA INSUFICIENTE";
      traceGroundedState.className = "trace-value state-abstain";
      traceStampState.textContent = "ABSTAINED";

      answerContent.classList.add("hidden");
      abstentionBox.classList.remove("hidden");
    } else {
      answerHeading.textContent = "Respuesta fundamentada";
      groundingStatusPill.textContent = "FUNDAMENTADA";
      groundingStatusPill.className = "status-pill status-grounded";

      traceGroundedState.textContent = "FUNDAMENTADA";
      traceGroundedState.className = "trace-value state-grounded";
      traceStampState.textContent = "VERIFIED";

      abstentionBox.classList.add("hidden");
      answerContent.classList.remove("hidden");

      // Secure Grounded Text Rendering
      renderGroundedText(data.answer || "Respuesta sin contenido retornado.", citations);
    }

    // 3. Render Evidence Ledger
    renderEvidenceLedger(sources);

    // 4. Render Technical Traceability Details
    renderTechnicalDetails(data);

    // Show Results
    resultsArea.classList.remove("hidden");
    if (pipelineGuide) pipelineGuide.classList.add("hidden");
    safeScrollIntoView(resultsArea, "start");
  }

  /**
   * Safely render answer text and convert [S#] citations into interactive badges
   */
  function renderGroundedText(text, citations) {
    // Clear previous content safely
    answerContent.textContent = "";

    // Regular expression matching [S1], [S2], etc.
    const citationRegex = /(\[S\d+\])/g;
    const allowedCitations = new Set(citations.map((citation) => String(citation).replace(/^\[|\]$/g, "")));
    const parts = text.split(citationRegex);

    parts.forEach((part) => {
      if (!part) return;

      const match = part.match(/^\[(S\d+)\]$/);
      if (match && allowedCitations.has(match[1])) {
        const sourceId = match[1];
        const badge = document.createElement("button");
        badge.type = "button";
        badge.className = "citation-badge";
        badge.textContent = `[${sourceId}]`;
        badge.setAttribute("aria-label", `Ver fuente ${sourceId}`);
        badge.setAttribute("title", `Ir a fuente ${sourceId} en la evidencia`);
        badge.setAttribute("aria-controls", `evidence-item-${sourceId}`);
        badge.setAttribute("aria-pressed", "false");
        badge.dataset.sourceId = sourceId;

        badge.addEventListener("click", () => {
          highlightEvidenceItem(sourceId);
        });

        answerContent.appendChild(badge);
      } else {
        // Safe standard text node
        answerContent.appendChild(document.createTextNode(part));
      }
    });
  }

  /**
   * Render Evidence Ledger Column
   */
  function renderEvidenceLedger(sources) {
    evidenceList.textContent = "";
    evidenceCountBadge.textContent = sources.length.toString();

    if (!sources || sources.length === 0) {
      evidenceEmpty.classList.remove("hidden");
      return;
    }

    evidenceEmpty.classList.add("hidden");

    sources.forEach((source) => {
      const item = document.createElement("div");
      item.className = "evidence-item";
      item.id = `evidence-item-${source.id}`;
      item.setAttribute("role", "listitem");
      item.setAttribute("tabindex", "-1");
      item.setAttribute("aria-label", `Fuente ${source.id}: ${source.file_name || "documento desconocido"}`);
      item.dataset.sourceType = source.source_type || "unknown";

      // Top Row: Source ID Badge + Provenance Badge
      const topRow = document.createElement("div");
      topRow.className = "evidence-top-row";

      const idBadge = document.createElement("span");
      idBadge.className = "evidence-id-badge";
      idBadge.textContent = source.id;

      const provBadge = document.createElement("span");
      const isInternal = source.source_type === "internal";
      provBadge.className = `prov-badge ${isInternal ? "prov-internal" : "prov-external"}`;
      provBadge.textContent = isInternal ? "[INT] INTERNA" : "[EXT] EXTERNA";

      topRow.appendChild(idBadge);
      topRow.appendChild(provBadge);

      // Filename
      const filename = document.createElement("span");
      filename.className = "evidence-filename";
      filename.textContent = source.file_name || "documento_desconocido";

      // Meta Row: Chunk Index + Similarity Score
      const metaRow = document.createElement("div");
      metaRow.className = "evidence-meta-row";

      const chunkInfo = document.createElement("span");
      chunkInfo.className = "chunk-info";
      chunkInfo.textContent = source.chunk_index !== null && source.chunk_index !== undefined
        ? `Fragmento ${source.chunk_index}`
        : "Documento completo";

      const simScore = document.createElement("span");
      simScore.className = "sim-score";
      const formattedScore = typeof source.score === "number" ? source.score.toFixed(3) : "—";
      simScore.textContent = `Similitud ${formattedScore}`;

      metaRow.appendChild(chunkInfo);
      metaRow.appendChild(simScore);

      item.appendChild(topRow);
      item.appendChild(filename);
      item.appendChild(metaRow);

      evidenceList.appendChild(item);
    });
  }

  /**
   * Highlight and scroll to a specific evidence item card
   */
  function highlightEvidenceItem(sourceId) {
    const targetElement = document.getElementById(`evidence-item-${sourceId}`);
    if (!targetElement) return;

    // Clear previous active highlights
    document.querySelectorAll(".evidence-item.highlighted").forEach((el) => {
      el.classList.remove("highlighted");
    });

    document.querySelectorAll(".citation-badge[aria-pressed='true']").forEach((badge) => {
      badge.setAttribute("aria-pressed", "false");
    });

    targetElement.classList.add("highlighted");
    document.querySelectorAll(`.citation-badge[data-source-id="${sourceId}"]`).forEach((badge) => {
      badge.setAttribute("aria-pressed", "true");
    });
    safeScrollIntoView(targetElement, "nearest");
    targetElement.focus({ preventScroll: true });
  }

  /**
   * Render Technical Details Table and Raw JSON
   */
  function renderTechnicalDetails(data) {
    techTableBody.textContent = "";

    const rows = [
      { key: "source_scope", val: data.source_scope || "all" },
      { key: "abstained", val: String(data.abstained) },
      { key: "citations_count", val: String((data.citations || []).length) },
      { key: "citations_list", val: JSON.stringify(data.citations || []) },
      { key: "sources_count", val: String((data.sources || []).length) },
    ];

    (data.sources || []).forEach((source) => {
      rows.push({
        key: `source.${source.id}`,
        val: `${source.source_type || "unknown"} · ${source.file_name || "documento_desconocido"} · chunk ${source.chunk_index ?? "—"} · score ${typeof source.score === "number" ? source.score.toFixed(3) : "—"}`,
      });
    });

    rows.forEach(({ key, val }) => {
      const tr = document.createElement("tr");

      const th = document.createElement("th");
      th.scope = "row";
      th.textContent = key;

      const td = document.createElement("td");
      td.textContent = val;

      tr.appendChild(th);
      tr.appendChild(td);
      techTableBody.appendChild(tr);
    });

    techJsonContent.textContent = JSON.stringify(data, null, 2);
  }

  /**
   * Loading state helper
   */
  function showLoading(isLoading) {
    if (isLoading) {
      loadingState.classList.remove("hidden");
      submitBtn.disabled = true;
    } else {
      loadingState.classList.add("hidden");
      submitBtn.disabled = false;
      if (pipelineGuide) pipelineGuide.classList.remove("is-processing");
    }
  }

  /**
   * Error state helpers
   */
  function showError(title, message, code) {
    errorTitle.textContent = title;
    errorMessage.textContent = message;
    errorState.classList.remove("hidden");
    if (pipelineGuide) {
      pipelineGuide.classList.remove("hidden");
      pipelineGuide.classList.remove("is-processing");
    }
    safeScrollIntoView(errorState, "nearest");
  }

  function hideError() {
    errorState.classList.add("hidden");
  }

  function formatScope(scope) {
    const scopeLabels = {
      internal: "INT",
      external: "EXT",
      all: "INT + EXT",
    };
    return scopeLabels[String(scope || "all").toLowerCase()] || String(scope).toUpperCase();
  }

  function safeScrollIntoView(element, block) {
    element.scrollIntoView({
      behavior: prefersReducedMotion.matches ? "auto" : "smooth",
      block,
    });
  }
});
