# Hito 5 — Benchmark experimental de calidad y consistencia

Sistema de evaluación reproducible para KnowledgeFlow AgentOps (`app/evaluation/agentops_*.py`), ejecutable sin llamadas externas a Gemini ni modificación de incidentes operacionales.

## 1. Arquitectura de evaluación

- **Dataset y esquema:** `app/evaluation/agentops_dataset.py` define `AgentOpsCase`, `AgentOpsDataset` y `load_agentops_dataset()`.
- **Métricas y equivalencia:** `app/evaluation/agentops_metrics.py` implementa `evaluate_case_record()`, `are_runs_equivalent()` y `compute_benchmark_metrics()`. Reutiliza `app.observability.store.latency()` para `mean`, `p50` y `p95`.
- **Runner offline determinista:** `app/evaluation/agentops_runner.py` ejecuta `AdaptiveOrchestrator` y `RuleBasedPlanner` sobre una base `SQLiteDatabase` temporal aislada (`TemporaryDirectory`), con `ShortTermMemory` y un doble determinista (`DeterministicOfflineKnowledgeTool`) para `search_knowledge`. Exporta JSON y CSV sanitizados.
- **Lector de calidad:** `app/evaluation/quality_store.py` expone `read_quality_summary(quality_dir, execution_mode)` manteniendo separación estricta entre `offline`, `mock`, `live` y `unknown`.

## 2. Estructura del dataset (`evaluation/agentops/dataset_v1.json`)

Contiene **15 casos** organizados en cuatro grupos, referenciando `evaluation/dataset_verified.json` sin alterar el corpus original:

- **Recuperación documental RAG (`rag_internal`, `rag_external`, `rag_mixed`, `rag_no_evidence`):** 6 casos derivados de `EVAL-003`, `EVAL-005`, `EVAL-007`, `EVAL-010`, `EVAL-011` y `EVAL-016` (`document_source="corpus_verified"`).
- **Comportamiento del agente (`agent_tools`, `agent_incidents`, `agent_planning_memory`):** 5 casos (selección de herramienta, creación/búsqueda/nota en incidentes y seguimiento multi-turno con memoria de corto plazo).
- **Seguridad y robustez (`security_robustness`):** 4 casos (intento de prompt injection sin mutación de incidentes, solicitud incompleta con `needs_clarification`, fallo simulado de herramienta y un caso sintético `AO-SEC-004` con `human_reviewed=false`).
- **Consistencia:** 3 grupos (`cg_internal_password`, `cg_abstention_ood`, `cg_incident_create`) repetidos `N=3` veces bajo condiciones equivalentes.

Separación de fuentes: `7` casos `corpus_verified` y `8` casos `synthetic_fixture`.

## 3. Definición matemática de métricas

Cuando un denominador es `0` o no existen muestras, la métrica devuelve `null` (nunca `0`).

| Métrica | Fórmula | Denominador / Alcance |
|---|---|---|
| **Exactitud de tarea** (`task_accuracy`) | `casos_correctos / casos_evaluables` | Solo `human_reviewed=true` |
| **Precisión de recuperación RAG** (`retrieval_precision`) | `documentos_relevantes_recuperados / total_documentos_recuperados` | Casos evaluables con `expected_files` |
| **Consistencia** (`consistency`) | `repeticiones_equivalentes / repeticiones_validas` | Grupos con `N ≥ 2` ejecuciones no fallidas |
| **Tasa de errores** (`error_rate`) | `ejecuciones_failed / total_ejecuciones` | Total de ejecuciones del benchmark |
| **Latencia** (`latency_ms`) | `mean`, `p50`, `p95` en ms | Reutiliza `store.latency()` sobre `perf_counter()` |
| **Uso de herramientas** (`tool_accuracy`) | `tareas_herramienta_correcta / tareas_evaluables` | Igualdad de conjunto esperado vs ejecutado |
| **Abstención** (`abstention_accuracy`) | `abstenciones_correctas / casos_abstencion_esperada` | Incluye conteo separado de `false_abstentions` |

**Criterio de equivalencia en consistencia (`are_runs_equivalent`):** dos ejecuciones son equivalentes si coinciden en `status`, `intent`, conjunto ordenado de `tool_calls`, conjunto de `retrieved_files` y similitud Jaccard sobre tokens normalizados `≥ 0.60` (no igualdad textual estricta).

## 4. Criterios de validación

- Cada caso declara `id`, `scenario`, `input`, `document_source`, `source_ref`, `expected_result`, `expected_tools`, `acceptance_criteria`, `execution_modes` y `human_reviewed`.
- Los casos con `human_reviewed=false` (como `AO-SEC-004`) se marcan `evaluable=false`, se excluyen del denominador de `task_accuracy` y `tool_accuracy`, y se reportan en `pending_validation_cases`.

## 5. Ejecución offline y preparación para evaluación live

- **Offline / Mock:** El runner no realiza llamadas de red ni usa `.env` con claves de Gemini. Toda ejecución offline registra `provider_mode: "deterministic_offline_stub"` y `not_live_gemini_evidence: true`.
- **Live (deshabilitada por defecto):** `mode="live"` lanza `LiveBenchmarkDisabledError` salvo habilitación explícita (`ALLOW_LIVE_BENCHMARK=true` y `allow_live=True`, además de configurar `OBS_LIVE_BENCHMARK_ENABLED=true` y un runner live controlado en una fase posterior). En este hito no se ejecutaron llamadas a Gemini.
- **Control de cuota futuro:** al habilitar evaluación live deberá usarse `--scenario` acotado y `--repeats 1` o `2` con presupuesto de solicitudes explícito.

## 6. Contratos e integración con observabilidad y dashboard

- `app/core/config.py` añade `obs_quality_dir: str = "evaluation/agentops/results"` y `obs_live_benchmark_enabled: bool = False`.
- `GET /api/observability/quality?execution_mode=<modo>` y `GET /dashboard/api/quality?execution_mode=<modo>` leen `latest_<modo>.json` desde `obs_quality_dir` mediante `read_quality_summary()`.
- Si no hay archivo para el modo consultado, devuelven `status: "not_evaluated"`, `precision: null`, `consistency: null`, `benchmarks: []`, manteniendo **N/D** en el dashboard.
- En `app/ui/observability.html` y `app/ui/static/observability/dashboard.mjs`, la sección `05 / Calidad del agente` muestra `Precisión`, `Consistencia`, versión, fecha, commit, indicador de fixtures sintéticos/offline y tabla de desglose por escenario cuando `status === "evaluated"`.

## 7. Resultados efectivamente obtenidos (corrida offline verificada)

Ejecución realizada con `.venv/bin/python -m app.evaluation.agentops_runner --mode offline --repeats 3 --output-dir /tmp/ao-bench-check` sobre `evaluation/agentops/dataset_v1.json`:

- **Total de ejecuciones:** `21` (`20` evaluables, `1` pendiente de validación).
- **Exactitud de tarea (`task_accuracy`):** `0.95` (`19 / 20`).
- **Precisión de recuperación (`retrieval_precision`):** `1.0` (`11 / 11` documentos relevantes en `8` casos RAG).
- **Consistencia (`consistency`):** `1.0` (`9 / 9` repeticiones equivalentes en `3` grupos).
- **Tasa de errores (`error_rate`):** `0.0476` (`1 / 21`, correspondiente al fallo simulado `AO-SEC-003`).
- **Uso de herramientas (`tool_accuracy`):** `0.95` (`19 / 20`).
- **Abstención (`abstention_accuracy`):** `1.0` (`4 / 4`, `0` falsas abstenciones).
- **Latencia offline (orquestador + doubles):** `mean = 0.672 ms`, `p50 = 0.113 ms`, `p95 = 2.135 ms` (`N = 21`).

## 8. Pruebas ejecutadas tras la edición final

- `.venv/bin/python scripts/run_tests_offline.py --uvloop`: **348 passed, 20 warnings** (`OFFLINE_NETWORK_ATTEMPTS_BLOCKED=0`).
- `.venv/bin/python scripts/run_tests_offline.py --uvloop --observe`: **348 passed, 20 warnings** (`OFFLINE_NETWORK_ATTEMPTS_BLOCKED=0`).
- `node tests/dashboard_frontend.test.mjs`: **6 passed, 0 failed**.
- `node --check app/ui/static/observability/dashboard.mjs` y `git diff --check`: sin errores.

## 9. Limitaciones

- La corrida experimental ejecutada utiliza `DeterministicOfflineKnowledgeTool` (doubles deterministas) y `semantic_memory=None`; no mide calidad semántica ni latencia del modelo Gemini real ni de embeddings live.
- Por defecto `evaluation/agentops/results/` se mantiene sin archivos de resultados pre-cargados para que el dashboard real muestre **N/D** hasta que el operador ejecute y publique un benchmark explícitamente.

## 10. Comandos de reproducción

```bash
# Ejecutar benchmark offline y exportar JSON/CSV en directorio temporal
.venv/bin/python -m app.evaluation.agentops_runner --mode offline --repeats 3 --output-dir /tmp/ao-bench

# Ejecutar suite completa offline (incluye tests/test_agentops_benchmark.py)
.venv/bin/python scripts/run_tests_offline.py --uvloop
.venv/bin/python scripts/run_tests_offline.py --uvloop --observe
```
