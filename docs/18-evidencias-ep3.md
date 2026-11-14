# Hito 7 — Evidencias técnicas EP3 y borrador estructural de informe

Consolidación verificable de evidencias de KnowledgeFlow AgentOps (M0–M7) y estructura base para el informe académico (máximo 5 páginas).

> **Aviso de autoría académica:** las secciones de **conclusiones**, **justificaciones técnicas propias** y **reflexiones individuales** se dejan señalizadas como `[PENDIENTE DE AUTORÍA HUMANA]` para ser redactadas exclusivamente por el equipo.
> **Discrepancia de sigla:** los materiales de EP3 indican **ISY1010**, mientras que los documentos previos de EP1/EP2 y EFT indican **ISY0101** (`docs/01-alcance-ep3.md`). Confirmar la sigla vigente con el docente.

## 1. Índice de evidencias verificables

1. **Arquitectura de observabilidad:** `docs/12-observabilidad.md`, `app/observability/telemetry.py`, `app/observability/middleware.py`.
2. **Eventos JSON y correlación de trazas:** `app/observability/models.py` (`trace_id`, `span_id`, `parent_span_id`, `execution_mode`, `error_code` en allowlist).
3. **Persistencia SQLite y agregación:** `app/observability/store.py`, `docs/13-agregacion-metricas.md` (`retention_days=7`, `max_events=50000`, `max_bytes=64 MiB`, permisos `0o600`).
4. **Fórmulas y resultados del benchmark offline:** `app/evaluation/agentops_dataset.py`, `app/evaluation/agentops_metrics.py`, `app/evaluation/agentops_runner.py`, `evaluation/agentops/dataset_v1.json`, `docs/16-benchmark-experimental.md`.
   - Corrida offline reproducible (`--mode offline --repeats 3`, **datos deterministas/doubles, NO Gemini live**): `21` ejecuciones (`20` evaluables, `1` pendiente `human_reviewed=false`): `task_accuracy=0.95` (`19/20`), `retrieval_precision=1.0` (`11/11`), `consistency=1.0` (`9/9`), `error_rate=0.0476` (`1/21`), `tool_accuracy=0.95` (`19/20`), `abstention_accuracy=1.0` (`4/4`), `latency_ms` (`mean=0.672 ms`, `p50=0.113 ms`, `p95=2.135 ms`).
5. **Validación visual del dashboard:** `docs/14-dashboard-web.md`, `docs/15-validacion-visual.md` (validado en Chromium/Playwright en `1440×900`, `768×1024`, `390×844` con almacén temporal `mock` aislado y estado vacío real en `data/observability/events.sqlite3`).
6. **Gráficos de latencia y errores:** `app/ui/static/observability/charts.mjs` (SVG nativos sin dependencias externas: latencia HTTP en 24 intervalos, latencia por componente, resultados de ejecución, errores HTTP por intervalo, herramientas y tokens).
7. **Resultados de pruebas automatizadas:** `scripts/run_tests_offline.py --uvloop` y `--observe`, `tests/dashboard_frontend.test.mjs`, `tests/test_agentops_benchmark.py`.
8. **Medidas de seguridad implementadas:** `docs/17-auditoria-seguridad.md`, `app/api/dashboard_routes.py`, `app/api/observability_routes.py`.

---

## 2. Borrador estructural del informe EP3 (máximo 5 páginas)

### 2.1 Caso organizacional
- **Contexto:** NovaTech SpA (caso pedagógico), mesa de consulta normativa y gestión de incidentes operacionales TI.
- **Problema:** Necesidad de auditar ejecuciones agentic (RAG + herramientas + memoria) sin exponer secretos ni contenido sensible de incidentes, distinguiendo modos `offline`, `mock` y `live`.

### 2.2 Arquitectura de observabilidad
- Middleware HTTP y decorador `@instrument` sobre FastAPI, orquestador, planificador, RAG, herramientas y memoria.
- Almacenamiento local en SQLite (`EventStore`) con retención acotada y API administrativa GET (`/api/observability/*`) + consola web local (`/dashboard`).

### 2.3 Herramientas implementadas
- Reutilización de `search_knowledge`, `create_incident`, `search_incidents`, `append_incident_note` con trazabilidad por `span_id`/`parent_span_id` y registro de logs tipados (`safe_log()`).

### 2.4 Metodología experimental
- Dataset `evaluation/agentops/dataset_v1.json` (15 casos: 7 derivados de `evaluation/dataset_verified.json` y 8 fixtures sintéticos; 1 caso `human_reviewed=false` excluido del denominador).
- Repetición `N=3` en grupos de consistencia con criterio de equivalencia operacional/semántica (`are_runs_equivalent()`).
- `[PENDIENTE DE AUTORÍA HUMANA: justificación metodológica del equipo]`

### 2.5 Resultados verificables
- Incluir tabla resumen de la corrida offline (`docs/16-benchmark-experimental.md`) aclarando explícitamente que corresponde a doubles deterministas y **no** a Gemini live.
- Estado de pruebas offline: `348 passed` (sin red externa) y `6 passed` en JS.
- `[PENDIENTE DE AUTORÍA HUMANA: interpretación y discusión técnica de resultados]`

### 2.6 Análisis de trazas
- Inspección de jerarquía padre-hijo en el Explorador de trazas (`/dashboard#traces`): raíz `http/agent`, span `agent/execute`, sub-spans `planner`, `rag`, `tool`, `memory`, `provider` y correlación de logs/errores (`error_code` tipado), más advertencia explícita de cobertura parcial cuando faltan padres o hay retención.

### 2.7 Seguridad
- Resumen de controles verificados en `docs/17-auditoria-seguridad.md`: HTTP Basic + loopback en `/dashboard`, `X-Observability-Key` en `/api/observability/*`, CSP sin `innerHTML`, SQLite `0o600`, aislamiento de benchmarks en `TemporaryDirectory`, y alcance local seguro (`127.0.0.1`).

### 2.8 Conclusiones y reflexiones individuales
- `[PENDIENTE DE AUTORÍA HUMANA: conclusiones técnicas del equipo]`
- `[PENDIENTE DE AUTORÍA HUMANA: reflexiones individuales por integrante]`

### 2.9 Referencias (formato APA 7.ª edición — base a completar/verificar)
- FastAPI. (2024). *HTTP Basic Auth and Security*. FastAPI Documentation. https://fastapi.tiangolo.com/advanced/security/http-basic-auth/
- NIST. (2020). *NIST Privacy Framework: A Tool for Improving Privacy Through Enterprise Risk Management, Version 1.0*. National Institute of Standards and Technology.
- OWASP. (2024). *OWASP Top 10 for Large Language Model Applications / LLM Prompt Injection Prevention Cheat Sheet*. OWASP Foundation.
- SQLite. (2024). *SQLite File Format & PRAGMA Statements*. SQLite Consortium.

### 2.10 Declaración de uso de IA
- `[PENDIENTE DE AUTORÍA HUMANA: declarar herramientas de IA utilizadas en desarrollo/documentación y verificación realizada por el equipo según pauta del curso]`
