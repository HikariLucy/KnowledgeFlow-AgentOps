document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("agent-form");
  const actionType = document.getElementById("action-type");
  const sourceScope = document.getElementById("source-scope");
  const messageInput = document.getElementById("agent-message");

  const createFields = document.getElementById("incident-create-fields");
  const noteFields = document.getElementById("incident-note-fields");

  const incidentTitle = document.getElementById("incident-title");
  const incidentDescription = document.getElementById("incident-description");
  const incidentCategory = document.getElementById("incident-category");
  const incidentSeverity = document.getElementById("incident-severity");
  const incidentNote = document.getElementById("incident-note");

  const submitBtn = document.getElementById("agent-submit-btn");
  const loadDemoBtn = document.getElementById("load-demo-btn");
  const newConversationBtn = document.getElementById("new-conversation-btn");
  const conversationIdEl = document.getElementById("conversation-id");

  const loadingEl = document.getElementById("agent-loading");
  const errorEl = document.getElementById("agent-error");
  const errorTitleEl = document.getElementById("agent-error-title");
  const errorMessageEl = document.getElementById("agent-error-message");
  const resultsEl = document.getElementById("agent-results");

  const resultStatus = document.getElementById("result-status");
  const resultIntent = document.getElementById("result-intent");
  const resultIncident = document.getElementById("result-incident");
  const resultIterations = document.getElementById("result-iterations");
  const outputEl = document.getElementById("agent-output");
  const nextActionsEl = document.getElementById("result-next-actions");
  const prepareFollowupBtn = document.getElementById("prepare-followup-btn");
  const followupHint = document.getElementById("followup-hint");

  const planList = document.getElementById("plan-list");
  const toolList = document.getElementById("tool-list");

  const memoryList = document.getElementById("memory-list");
  const memoryCount = document.getElementById("memory-count");

  const sourceList = document.getElementById("source-list");
  const sourceCount = document.getElementById("source-count");

  const observationList = document.getElementById("observation-list");
  const rawJson = document.getElementById("agent-raw-json");

  const storageKey = "knowledgeflow-agent-conversation-id";
  let conversationId = sessionStorage.getItem(storageKey) || createConversationId();
  sessionStorage.setItem(storageKey, conversationId);
  conversationIdEl.textContent = conversationId;

  function createConversationId() {
    if (window.crypto && typeof window.crypto.randomUUID === "function") {
      return `demo-${window.crypto.randomUUID().slice(0, 8)}`;
    }
    return `demo-${Date.now()}`;
  }

  function updateActionFields() {
    const mode = actionType.value;
    createFields.classList.toggle("hidden", mode !== "create_incident");
    noteFields.classList.toggle("hidden", mode !== "incident_note");
  }

  actionType.addEventListener("change", updateActionFields);
  updateActionFields();

  newConversationBtn.addEventListener("click", () => {
    conversationId = createConversationId();
    sessionStorage.setItem(storageKey, conversationId);
    conversationIdEl.textContent = conversationId;
    resultsEl.classList.add("hidden");
    hideError();
  });

  loadDemoBtn.addEventListener("click", () => {
    actionType.value = "create_incident";
    updateActionFields();
    sourceScope.value = "internal";
    messageInput.value = "Perdí mi autenticador MFA. Revisa el procedimiento y registra un incidente.";
    incidentTitle.value = "Pérdida de autenticador MFA";
    incidentDescription.value = "Usuario perdió el dispositivo utilizado para MFA.";
    incidentCategory.value = "access";
    incidentSeverity.value = "medium";
    messageInput.focus();
  });

  prepareFollowupBtn.addEventListener("click", () => {
    actionType.value = "incident_note";
    updateActionFields();
    messageInput.value = "Agrega que la identidad ya fue validada.";
    incidentNote.value = "Identidad del usuario validada.";
    hideError();

    form.scrollIntoView({
      behavior: "smooth",
      block: "start",
    });
    messageInput.focus();
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    hideError();

    const message = messageInput.value.trim();
    if (!message) {
      showError("Solicitud requerida", "Escribe una solicitud válida antes de ejecutar el agente.");
      return;
    }

    const payload = {
      conversation_id: conversationId,
      message,
    };

    const scope = sourceScope.value || null;
    const mode = actionType.value;

    if (mode === "knowledge" || mode === "create_incident") {
      payload.knowledge_query = {
        query: message,
        source_scope: scope,
        top_k: 4,
      };
    }

    if (mode === "create_incident") {
      const title = incidentTitle.value.trim();
      const description = incidentDescription.value.trim();

      if (!title || !description) {
        showError("Datos incompletos", "Título y descripción son obligatorios para crear el incidente.");
        return;
      }

      payload.create_incident = {
        title,
        description,
        category: incidentCategory.value,
        severity: incidentSeverity.value,
      };
    }

    if (mode === "incident_note") {
      const note = incidentNote.value.trim();
      if (!note) {
        showError("Nota requerida", "Escribe el seguimiento que deseas agregar.");
        return;
      }

      payload.append_incident_note = {
        note,
      };
    }

    await executeAgent(payload);
  });

  async function executeAgent(payload) {
    setLoading(true);
    resultsEl.classList.add("hidden");

    try {
      const response = await fetch("/api/agent", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Accept": "application/json",
        },
        body: JSON.stringify(payload),
      });

      const data = await safeReadJson(response);

      if (!response.ok) {
        const detail = data && data.detail
          ? formatDetail(data.detail)
          : `HTTP ${response.status}`;
        showError("No se pudo ejecutar el agente", detail);
        return;
      }

      renderResult(data);
    } catch (error) {
      showError(
        "Error de conexión",
        "No se pudo establecer comunicación con KnowledgeFlow Agent."
      );
    } finally {
      setLoading(false);
    }
  }

  async function safeReadJson(response) {
    try {
      return await response.json();
    } catch {
      return null;
    }
  }

  function formatDetail(detail) {
    if (typeof detail === "string") return detail;
    return JSON.stringify(detail);
  }

  function renderResult(data) {
    const status = data.status || "unknown";

    resultStatus.textContent = status;
    resultStatus.className = `agent-status-${status}`;

    resultIntent.textContent = data.intent || "—";
    resultIncident.textContent = data.incident_id || "—";
    resultIterations.textContent = String(data.iteration_count ?? "—");

    outputEl.textContent = data.output || "Sin salida visible.";

    const canContinueIncident = (
      status === "completed"
      && data.intent === "incident_create"
      && Boolean(data.incident_id)
    );

    nextActionsEl.classList.toggle("hidden", !canContinueIncident);

    if (canContinueIncident) {
      followupHint.textContent = (
        `Continúa sobre ${data.incident_id} sin cambiar de conversación. `
        + "El incident_id será resuelto desde la memoria."
      );
      prepareFollowupBtn.textContent = (
        `Continuar seguimiento de ${data.incident_id}`
      );
    }

    renderPlan(data.plan || [], data.completed_steps || []);
    renderTools(data.tool_calls || []);
    renderMemory(data.memory_context || []);
    renderSources(data.sources || []);
    renderObservations(data.observations || []);

    rawJson.textContent = JSON.stringify(data, null, 2);

    resultsEl.classList.remove("hidden");
    resultsEl.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function renderPlan(plan, completed) {
    planList.textContent = "";
    const completedSet = new Set(completed);

    if (!plan.length) {
      appendEmptyListItem(planList, "No se generó un plan.");
      return;
    }

    plan.forEach((step) => {
      const li = document.createElement("li");
      li.textContent = completedSet.has(step)
        ? `✓ ${step}`
        : step;
      planList.appendChild(li);
    });
  }

  function renderTools(tools) {
    toolList.textContent = "";

    if (!tools.length) {
      const empty = document.createElement("span");
      empty.className = "agent-empty";
      empty.textContent = "Sin tools ejecutadas.";
      toolList.appendChild(empty);
      return;
    }

    tools.forEach((tool) => {
      const chip = document.createElement("span");
      chip.className = "agent-chip";
      chip.textContent = tool;
      toolList.appendChild(chip);
    });
  }

  function renderMemory(memories) {
    memoryList.textContent = "";
    memoryCount.textContent = String(memories.length);

    if (!memories.length) {
      appendEmpty(memoryList, "No se recuperó contexto previo para este turno.");
      return;
    }

    memories.forEach((memory) => {
      const item = document.createElement("div");
      item.className = "agent-ledger-item";

      const title = document.createElement("strong");
      const kind = memory.memory_kind || "memory";
      const role = memory.role ? ` · ${memory.role}` : "";
      title.textContent = `${kind}${role}`;

      const content = document.createElement("p");
      content.textContent = memory.content || "Sin contenido.";

      const meta = document.createElement("span");
      meta.className = "agent-ledger-meta";
      const parts = [];
      if (memory.memory_id) parts.push(memory.memory_id);
      if (typeof memory.score === "number") parts.push(`score ${memory.score.toFixed(3)}`);
      if (memory.created_at) parts.push(memory.created_at);
      meta.textContent = parts.join(" · ") || "context";

      item.append(title, content, meta);
      memoryList.appendChild(item);
    });
  }

  function renderSources(sources) {
    sourceList.textContent = "";
    sourceCount.textContent = String(sources.length);

    if (!sources.length) {
      appendEmpty(sourceList, "Este turno no recuperó fuentes documentales.");
      return;
    }

    sources.forEach((source) => {
      const item = document.createElement("div");
      item.className = "agent-ledger-item";

      const title = document.createElement("strong");
      title.textContent = `${source.id || "S?"} · ${source.file_name || "documento"}`;

      const content = document.createElement("p");
      content.textContent = `${source.source_type || "unknown"} · chunk ${source.chunk_index ?? "—"}`;

      const meta = document.createElement("span");
      meta.className = "agent-ledger-meta";
      meta.textContent = typeof source.score === "number"
        ? `similitud ${source.score.toFixed(4)}`
        : "sin score";

      item.append(title, content, meta);
      sourceList.appendChild(item);
    });
  }

  function renderObservations(observations) {
    observationList.textContent = "";

    if (!observations.length) {
      appendEmpty(observationList, "Sin observaciones operacionales.");
      return;
    }

    observations.forEach((observation) => {
      const card = document.createElement("div");
      card.className = "agent-observation";

      const title = document.createElement("strong");
      title.textContent = observation.tool || observation.component || "observation";

      const body = document.createElement("pre");
      body.textContent = JSON.stringify(observation, null, 2);

      card.append(title, body);
      observationList.appendChild(card);
    });
  }

  function appendEmpty(container, text) {
    const element = document.createElement("div");
    element.className = "agent-empty";
    element.textContent = text;
    container.appendChild(element);
  }

  function appendEmptyListItem(container, text) {
    const element = document.createElement("li");
    element.textContent = text;
    container.appendChild(element);
  }

  function setLoading(active) {
    loadingEl.classList.toggle("hidden", !active);
    submitBtn.disabled = active;
  }

  function showError(title, message) {
    errorTitleEl.textContent = title;
    errorMessageEl.textContent = message;
    errorEl.classList.remove("hidden");
  }

  function hideError() {
    errorEl.classList.add("hidden");
  }
});
