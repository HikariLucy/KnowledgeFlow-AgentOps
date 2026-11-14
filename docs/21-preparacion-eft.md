# Preparación técnica EFT (ISY0101) — Entrega Jupyter/Colab

**Rama:** `feat/eft-notebook` (creada desde `main`)  
**Estado:** Hito 1 técnico (paquete de notebooks y verificación offline) listo; **informe PDF académico, validación real del caso organizacional y defensa individual pendientes**.

---

## 1. Auditoría de módulos Python y recursos requeridos

Para ejecutar el sistema de punta a punta desde notebooks sin duplicar la lógica de producción se auditaron los siguientes componentes del repositorio:

- **Configuración y aplicación web:** `app/core/config.py`, `app/main.py`, `app/api/routes.py`, `app/api/agent_routes.py`, `app/api/observability_routes.py`, `app/api/dashboard_routes.py`.
- **EP1 — RAG, Prompts y FAISS:** `app/rag/prompts.py`, `app/rag/context.py`, `app/rag/loaders.py`, `app/rag/chunking.py`, `app/rag/embeddings.py`, `app/rag/vectorstore.py`, `app/rag/retriever.py`, `app/rag/generator.py`, `app/rag/pipeline.py`, `app/rag/schemas.py`, `app/agents/source_router.py`.
- **EP2 — Agente, Herramientas, Planificación y Memoria:** `app/agentic/planner.py`, `app/agentic/orchestrator.py`, `app/agentic/service.py`, `app/agentic/state.py`, `app/tools/knowledge.py`, `app/tools/incidents.py`, `app/tools/schemas.py`, `app/memory/short_term.py`, `app/memory/semantic.py`, `app/memory/write_back.py`, `app/storage/database.py`, `app/storage/repositories.py`, `app/integrations/crewai_adapter.py`.
- **EP3 — Observabilidad, Benchmark y Dashboard:** `app/observability/telemetry.py`, `app/observability/store.py`, `app/observability/models.py`, `app/observability/dashboard.py`, `app/observability/middleware.py`, `app/evaluation/agentops_dataset.py`, `app/evaluation/agentops_metrics.py`, `app/evaluation/agentops_runner.py`, `app/evaluation/quality_store.py`, `app/ui/observability.html`, `app/ui/static/observability/*`.
- **Recursos y fixtures:** corpus documental en `knowledge/internal/` (3 archivos) y `knowledge/external/` (5 archivos), dataset verificado `evaluation/agentops/dataset_v1.json`, dependencias en `requirements.txt`.

Para evitar duplicaciones manuales difíciles de mantener, los notebooks importan directamente estos módulos y los cuadernos modulares (`01_`–`03_`) inspeccionan su código fuente en vivo mediante `inspect.getsource(...)`.

---

## 2. Matriz de cobertura: indicadores EFT → código → notebook → evidencia

| Indicador EFT | Módulos originales | Notebook(s) | Evidencia reproducible |
|---|---|---|---|
| Solución integral LLM + RAG | `app/rag/pipeline.py`, `app/rag/vectorstore.py`, `app/rag/retriever.py`, `app/llm/client.py` | `notebooks/00_knowledgeflow_eft_principal.ipynb`, `notebooks/01_ep1_rag_y_prompts.ipynb` | Indexación FAISS sobre `knowledge/` con embeddings deterministas offline y celda live deshabilitada (`RUN_LIVE_GEMINI = False`) |
| Prompts y control de contexto | `app/rag/prompts.py` (`RAG_SYSTEM_PROMPT`, `format_rag_user_prompt`), `app/rag/context.py` (`build_rag_context`) | `notebooks/00_knowledgeflow_eft_principal.ipynb`, `notebooks/01_ep1_rag_y_prompts.ipynb` | Encapsulamiento `<context>` / `<question>`, citas `[S#]` y defensa ante prompt injection |
| Recuperación RAG interna y externa | `app/rag/loaders.py`, `app/agents/source_router.py`, `app/rag/pipeline.py` (`_retrieve_balanced_all`) | `notebooks/00_knowledgeflow_eft_principal.ipynb`, `notebooks/01_ep1_rag_y_prompts.ipynb` | Consultas con `source_scope` en `internal`, `external` y `all`, más verificación de abstención |
| Agente con herramientas, memoria y planificación | `app/agentic/planner.py`, `app/agentic/orchestrator.py`, `app/agentic/service.py`, `app/tools/incidents.py`, `app/tools/knowledge.py`, `app/memory/short_term.py`, `app/memory/write_back.py` | `notebooks/00_knowledgeflow_eft_principal.ipynb`, `notebooks/02_ep2_agente_herramientas_memoria.ipynb` | Flujo multi-turno sobre SQLite temporal: creación de incidente, búsqueda, nota heredando `incident_id` desde memoria y aclaración controlada |
| Observabilidad y registros sanitizados | `app/observability/telemetry.py`, `app/observability/store.py`, `app/observability/middleware.py` | `notebooks/00_knowledgeflow_eft_principal.ipynb`, `notebooks/03_ep3_observabilidad_benchmark_dashboard.ipynb` | `EventStore` SQLite temporal, correlación `trace_id`/`span_id` y redacción estricta sin prompts ni secretos |
| Benchmark offline y métricas | `app/evaluation/agentops_dataset.py`, `app/evaluation/agentops_runner.py`, `app/evaluation/agentops_metrics.py`, `app/evaluation/quality_store.py` | `notebooks/00_knowledgeflow_eft_principal.ipynb`, `notebooks/03_ep3_observabilidad_benchmark_dashboard.ipynb` | Ejecución determinista sobre `evaluation/agentops/dataset_v1.json` con `not_live_gemini_evidence=True` |
| Seguridad y acceso al dashboard | `app/api/dashboard_routes.py`, `app/api/observability_routes.py`, `app/ui/observability.html` | `notebooks/00_knowledgeflow_eft_principal.ipynb`, `notebooks/03_ep3_observabilidad_benchmark_dashboard.ipynb` | Verificación vía `TestClient` (loopback `127.0.0.1`), HTTP Basic (`401` sin credenciales, `200` autenticado), CSP y endpoints `/dashboard/api/*` |
| Entrega reproducible en Jupyter/Colab | `notebooks/00_`–`03_`, `scripts/run_notebooks_offline.py`, `tests/test_eft_notebooks.py` | Todos los notebooks en `notebooks/` | Validación de esquema nbformat v4, metadatos Colab y ejecución secuencial offline en `pytest` |
| Caso organizacional real (NovaTech SpA) | `knowledge/internal/*` | `notebooks/00_knowledgeflow_eft_principal.ipynb` | **Pendiente de validación**: NovaTech SpA se mantiene como escenario demostrativo del repositorio; no se presenta como empresa real verificada |

---

## 3. Procedimiento de ejecución

### Local (entorno limpio offline)

```bash
.venv/bin/python scripts/run_notebooks_offline.py
.venv/bin/python scripts/run_tests_offline.py --uvloop
.venv/bin/python scripts/run_tests_offline.py --uvloop --observe
```

### Google Colab

1. Abrir `notebooks/00_knowledgeflow_eft_principal.ipynb` desde GitHub en Google Colab.
2. Ejecutar la celda inicial de bootstrap (`IN_COLAB`), que clona el repositorio e instala `requirements.txt`.
3. Ejecutar las celdas de EP1, EP2 y EP3 secuencialmente en modo offline (sin `GEMINI_API_KEY`).
4. Mantener `RUN_LIVE_GEMINI = False` salvo ejecución explícita y autorizada con cuota propia.

---

## 4. Limitaciones identificadas

- **Modo offline vs. Gemini real:** los embeddings hashing y generadores/routers offline en los notebooks son dobles deterministas para reproducibilidad sin red ni cuota; **no representan la calidad, precisión ni latencia de Gemini real**.
- **Dependencias en Colab y entorno local:** `requirements.txt` fija `crewai[google-genai]==1.15.22` y `faiss-cpu>=1.14.0`, cuya instalación en Colab puede tomar varios minutos o requerir reiniciar el runtime si colisiona con paquetes preinstalados. `jupyter` y `nbconvert` no están en `requirements.txt`.
- **Alcance de red del dashboard:** `local_access` en `app/api/dashboard_routes.py` exige IP loopback (`127.0.0.1` / `::1`) y host local; por ello, dentro del notebook el dashboard se verifica mediante `TestClient(..., client=("127.0.0.1", 50000))` y no mediante exposición pública en Colab.
- **Pendientes académicos humanos:** informe académico PDF, validación del caso organizacional real, declaración de uso de IA, conclusiones, reflexiones individuales y defensa oral (máximo 10 minutos).
