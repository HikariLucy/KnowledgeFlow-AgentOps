# Auditoría técnica de la base EP2 — KnowledgeFlow AgentOps

Fecha: 2026-11-13. Alcance: inspección local, pruebas offline y propuesta técnica; sin implementación funcional ni evaluación live. Este documento registra evidencia técnica, no conclusiones ni justificaciones académicas del equipo.

## 1. Procedencia y estado del repositorio

El directorio inicial de trabajo no es un repositorio Git. El repositorio real está en su subdirectorio `KnowledgeFlow-AgentOps/`; todas las rutas siguientes son relativas a esa raíz.

| Dato | Evidencia local |
|---|---|
| Rama | `main`, seguimiento `origin/main` |
| HEAD | `d498df0e0516f7a17d60d823b66977c5cd769f16` |
| Último asunto | `docs: actualizar README tras migración verificada de EP2` |
| Remoto fetch/push | `origin`: `https://github.com/HikariLucy/KnowledgeFlow-AgentOps` |
| Árbol inicial | Limpio, `git status --short --branch` mostró únicamente `## main...origin/main` |
| Archivos versionados iniciales | 161, mediante `git ls-files` |
| Fuente histórica declarada | KnowledgeFlow-Agent, SHA `53efc993f1edac638f364aac7e6d34982f023bb6`, según README y acta de migración |

No se realizó fetch, push, merge ni modificación de remotos. La coincidencia con `origin/main` corresponde a referencias locales; no demuestra el estado actual del servidor. La comparación histórica de 141 archivos es una declaración de la migración previa, no una verificación repetida en esta auditoría.

## 2. Estructura y componentes reutilizables

| Ubicación | Implementación observada y reutilización |
|---|---|
| `app/main.py`, `app/api/` | FastAPI, `/health`, `/api/query`, `/api/agent`, UI `/` y `/agent`, recursos `/static`. Dependencias reemplazables para pruebas. Punto de entrada para correlación HTTP. |
| `app/agentic/` | `AgentService`, `AdaptiveOrchestrator`, `RuleBasedPlanner`, `AgentState`. Estados controlados, planificación, validación de argumentos, registro de herramientas y finalización con memoria. Base para eventos del agente. |
| `app/agents/` | Perfiles de manager/especialistas y router de fuentes Gemini/fake. Separar en telemetría planificación por reglas de routing con LLM. |
| `app/integrations/` | Adaptador y wrappers CrewAI. Construyen jerarquía y herramientas; `verbose=False`, crew con `memory=False`, `planning=False`, `cache=False`. No se observó `kickoff` en el flujo HTTP. |
| `app/tools/` | Consulta RAG, creación/búsqueda de incidentes y anexado de notas, con esquemas Pydantic. Límites naturales para spans sin copiar argumentos. |
| `app/memory/` | Ventana por conversación, persistencia SQLite, recuperación semántica con NumPy y write-back de eventos operacionales. No confundir memoria semántica con el índice FAISS documental. |
| `app/storage/` | SQLite, tablas de incidentes, notas y memoria, identificadores públicos y timestamps. Persistencia de negocio, no almacén de observabilidad. |
| `app/rag/`, `app/llm/` | Carga TXT/MD/PDF, chunking, embeddings, FAISS, manifest/fingerprint, recuperación, umbral, contexto, generación y reparación de citas. Cliente Gemini desacoplado. |
| `app/evaluation/` | Evaluador inyectable, métricas, reportes JSON/Markdown y barrido de umbral. Reutilizar cálculos con denominadores explícitos. |
| `app/ui/static/` | HTML/CSS/JS existente para RAG/agente y detalle operativo. Ampliable sin Streamlit ni cambio de frontend. |
| `tests/`, `scripts/` | 36 archivos `test_*.py` en tests; dobles deterministas, mocks del SDK, SQLite temporal y TestClient. Scripts Gemini/RAG live fuera de `testpaths`. |
| `knowledge/`, `evaluation/`, `docs/`, `prompts/`, `notebooks/` | Corpus, datasets y documentación histórica/propuesta. `evaluation/agentops/` y `notebooks/` contienen README, no un benchmark EP3 ejecutado ni notebook implementado. |

No existen en este checkout `.env`, `.venv`, `vectorstore/`, `data/`, `app/observability/` ni `app/api/observability_routes.py`. Los documentos EP3 describen trabajo pendiente, no capacidades ejecutadas.

Flujo HTTP real: `/api/agent` → `AgentService.execute` → `AdaptiveOrchestrator.execute` → planner por reglas → herramientas → memoria. CrewAI es una integración disponible, no el motor de esa ruta. La construcción del servicio depende del pipeline RAG: un índice ausente u obsoleto puede impedir incluso una petición operacional antes de ejecutar el agente.

## 3. Pruebas offline: resultado y límites

Entorno observado: Linux, Python **3.12.3**, pip **24.0**, pytest **7.4.4**. No existe el comando `python`; se utilizó `python3`. El pytest instalado está por debajo del requisito `pytest>=8.0.0`.

No están instalados en ese intérprete: `fastapi`, `pydantic`, `pydantic-settings`, `langchain-core`, `langchain-text-splitters`, `pypdf`, `faiss-cpu`, `numpy`, `google-genai`, `crewai`, `httpx` (consulta con `importlib.metadata.version`). No se instalaron paquetes ni se alteraron otros entornos de proyectos. La consulta de caché de pip tampoco estuvo disponible por permisos.

Se ejecutó la suite configurada por `pytest.ini` (`testpaths = tests`), con claves vacías, plugins externos deshabilitados, telemetría deshabilitada por variables de entorno y un audit hook que rechaza conexión/resolución/envío por sockets Python. Los tests inspeccionados usan fakes/mocks; los de CrewAI construyen objetos sin ejecutar el crew. No se ejecutó ningún script live, indexador o benchmark con proveedor real.

| Ejecución | Resultado observado | Interpretación |
|---|---|---|
| Suite completa, equivalente a `pytest -q` con controles offline y JUnit | **35 errores durante colección, 0.78 s, exit 2** | Imports ausentes (`fastapi`, `pydantic`, `langchain_core`, `crewai`). La suite no llegó a ejecutar casos; no son 35 aserciones fallidas. |
| Pruebas de documentación tras escribir ambos entregables | **2 passed in 0.01s, exit 0** | `tests/test_docs_portability.py`; validación limitada de portabilidad y terminología, no de funcionalidad. |
| Intentos de red bloqueados en esa corrida | **0** | No hubo solicitudes Gemini en la corrida. El hook no sustituye aislamiento de red a nivel de SO para futuros procesos nativos/subprocesos. |
| Regresión funcional de aplicación | **N/D** | No puede declararse aprobada ni rechazada por lógica de negocio. |
| Calidad, latencias operativas, tokens y costo live | **N/D** | No se midieron. El tiempo de pytest no es latencia del agente. |

El log completo de la suite quedó en `/tmp/knowledgeflow-audit/pytest.log`. La comprobación documental quedó en `/tmp/knowledgeflow-audit/docs-tests.log` y `/tmp/knowledgeflow-audit/docs-tests.xml`, con cero intentos de red. El JUnit inicial fue reemplazado por la corrida documental; para los 35 errores se conserva el log de texto. Son artefactos temporales locales, no forman parte del repositorio ni se garantiza su conservación. Su salida final fue:

```text
!!!!!!!!!!!!!!!!!!! Interrupted: 35 errors during collection !!!!!!!!!!!!!!!!!!!
35 errors in 0.78s
OFFLINE_NETWORK_ATTEMPTS_BLOCKED=0
```

Para reproducir el control utilizado, desde la raíz real del repositorio, con dependencias ya aprovisionadas:

```python
# Guardar fuera del repositorio como run_offline.py y ejecutar con python3.
import os
import sys
from pathlib import Path
os.environ.update(
    GEMINI_API_KEY='', GOOGLE_API_KEY='', OPENAI_API_KEY='',
    CREWAI_TELEMETRY_DISABLED='true', OTEL_SDK_DISABLED='true',
    PYTEST_DISABLE_PLUGIN_AUTOLOAD='1', PYTHONDONTWRITEBYTECODE='1',
)
blocked = []
def audit(event, args):
    if event in {'socket.connect', 'socket.getaddrinfo', 'socket.sendto'}:
        blocked.append(event)
        raise RuntimeError('OFFLINE audit: network access blocked')
sys.addaudithook(audit)
sys.path.insert(0, str(Path.cwd()))
import pytest
code = pytest.main([
    '-q', '-p', 'no:cacheprovider',
    '--junitxml=/tmp/knowledgeflow-audit/pytest.xml', *sys.argv[1:],
])
print(f'OFFLINE_NETWORK_ATTEMPTS_BLOCKED={len(blocked)}')
raise SystemExit(code)
```

Crear previamente el directorio temporal. El programa empleado está en `/tmp/knowledgeflow-audit/run_offline.py`. Las variables son defensa adicional: no se ha verificado aquí cómo las interpreta una versión instalada de CrewAI, ya que no está instalada. Para una futura regresión completa usar además aislamiento de red del proceso y un entorno sin credenciales ni `.env`.

## 4. Mapa concreto de instrumentación propuesta

Los siguientes son puntos de inserción futuros; no se han modificado.

| Capa y símbolo | Medición permitida | Casos que deben capturarse |
|---|---|---|
| `app/main.py`; `api/routes.py:query_rag`, `api/agent_routes.py:execute_agent` | Span raíz: método, plantilla de ruta, HTTP status, duración; ID generado internamente | Validación 422, dependencia 503, excepción 500, cancelación; envolver también resolución de dependencias |
| `api/routes.py:get_rag_pipeline`, `api/agent_routes.py:get_agent_service` | Inicialización/caché, carga y vigencia del índice | Arranque frío frente a caliente, sin registrar rutas absolutas |
| `agentic/service.py:AgentService.execute` | Una ejecución por turno, resultado del dominio | No usar `conversation_id` como `trace_id`; no serializar request/response |
| `agentic/orchestrator.py:execute`, `_finalize`, `_failure`, `_clarification` | Estado final, iteraciones, llamadas de herramientas, fallo/degradación | Retornos anticipados y errores absorbidos de memoria; HTTP 200 no implica éxito del dominio |
| `agentic/planner.py:plan`, `hydrate_memory_context` | Intent controlado, número de pasos, conteos de memoria, estado de recuperación | Plan por reglas sin razonamiento privado, memoria indisponible |
| `tools/knowledge.py:KnowledgeRAGTool.run`; `tools/incidents.py:*Tool.run` | Nombre permitido, duración, resultado y cantidad devuelta | Contar intento antes de llamada; excepción; evitar duplicar la misma llamada en wrappers CrewAI |
| `memory/short_term.py:add_message/get_messages`; `long_term.py:add_memory/list_memories/get_memory` | Operación, cantidad y duración | Sin mensajes, metadatos arbitrarios ni embeddings |
| `memory/semantic.py:search/remember`; `write_back.py:record` | Lookup, embedding y persistencia separados; estado de degradación | `search` genera embedding aun sin memorias; write-back operacional también puede llamar Gemini |
| `rag/pipeline.py:run`, `_retrieve_balanced_all` | Scope, k, umbral, candidatos/seleccionados, abstención | Dos búsquedas cuando scope=all; early return sin generación |
| `agents/source_router.py:route`, `_fallback_decision` | Resultado normalizado, fallback, intentos | Fallo capturado que termina en scope=all |
| `rag/retriever.py:search`; `vectorstore.py:similarity_search` | Separar embedding de consulta y búsqueda FAISS | Doble embedding en recuperación balanceada; fingerprint solo como metadato de ejecución |
| `rag/embeddings.py:_call_embed_api`; `rag/generator.py:_call_gemini`, `generate` | Intento proveedor, duración, modelo, uso reportado si existe, validación/reparación | Hasta 4 intentos por llamada de generación; reparación adicional; espera incluida en duración padre |
| `storage/database.py:connect`, `storage/repositories.py` | Operación controlada y duración de almacenamiento | No SQL con parámetros ni textos; instrumentación no debe abrir transacciones sobre tablas de negocio |
| `evaluation/runner.py:run_evaluation` | Run/case IDs, etapa evaluada, SHA, configuración, modo | Separar evaluación de retrieval aislado del recorrido RAG, no sumar como una sola consulta de producción |

## 5. Métricas, logs y trazabilidad existentes

- **Agente:** `AgentState` registra plan, herramientas requeridas/llamadas, pasos completados, observaciones, `iteration_count`, `max_iterations=6`. `ExecutionStatus`: completed, needs_clarification, abstained, failed. Son datos de una ejecución retornados por API, no spans persistidos ni contadores agregados. Los errores de memoria incluyen `error_type` y estado unavailable.
- **RAG:** referencias/citas, scope, scores y abstención. La integridad de citas comprueba referencias resolubles; no demuestra exactitud semántica de todas las afirmaciones. El índice conserva manifest, fecha, modelo, dimensión, configuración y fingerprint SHA-256; comprueba dimensión/cantidad al cargar y frescura al construir el pipeline.
- **Evaluación:** accuracy/matriz de confusión del router, Hit@K, MRR, recall de fuentes esperadas, cumplimiento de scope, cobertura dual, matriz TP/FP/TN/FN de abstención, accuracy/precision/recall de abstención, integridad de citas y éxito de respuesta trazable. Evidencia: `app/evaluation/metrics.py` y `schemas.py`.
- **Procedencia de evaluación:** timestamp, commit, dirty, modelos, k, umbral, ruta/versión/revisión del dataset y fingerprint. Exportación JSON/Markdown. No incluye modo offline/mock/live, IDs de spans, consumo ni latencias.
- **Datasets:** tanto `dataset_verified.json` como `dataset_draft.json` tienen 20 casos y 20 flags `human_reviewed=true`. Es conteo de campos, no validación independiente de revisión humana ni de calidad.
- **Logs:** `logging.getLogger` en rutas, loaders, router y generador; warnings de fallback/reintentos/reparación y errores con texto de excepciones. CLI usa `print` y algunos scripts imprimen consulta/respuesta/snippets. No se encontró configuración propia de JSON, sanitización central, rotación, retención o correlación.
- **No implementado en `app/`:** `trace_id`/`span_id`, árbol temporal de spans, percentiles/latencia por componente, persistencia de telemetría, métricas de tokens/costo/CPU/RSS, tasa agregada de errores, consistencia por repeticiones y endpoints/dashboard de observabilidad. La presencia de palabras “trace” en UI no equivale a tracing distribuido. No se auditó telemetría interna de dependencias ausentes.

## 6. Riesgos y compatibilidad

| Prioridad | Hallazgo / evidencia | Impacto y tratamiento propuesto |
|---|---|---|
| Alta | Dependencias ausentes y pytest inferior al mínimo | Bloquea regresión. Aprovisionar entorno aislado, resolver requirements y conservar versiones antes de instrumentar. |
| Alta | `AgentResponse.memory_context`, planner y service incluyen contenido de memoria; conversation_id lo aporta el cliente. No hay autenticación/autorización en rutas inspeccionadas | Posible acceso cruzado si se conoce/reutiliza el ID al compartir el servicio. Validación Pydantic no es autorización. Mantener demo aislada y tratar acceso/propiedad como cambio de seguridad separado. Nunca exportar este contenido a telemetría. |
| Alta | Logs interpolan excepciones del SDK, paths y mensajes; `logger.exception` en agente | Posible exposición de contenido o datos internos. Allowlist de campos, códigos de error controlados y pruebas con secretos señuelo; no copiar `str(exc)` a eventos. |
| Alta | SQLite conserva textos, metadata y embeddings; manifest FAISS JSON conserva chunks; short-term guarda request/output | No se observó TTL/cifrado aplicativo ni control de acceso de archivos. No reutilizar tablas de negocio como logs. Definir permisos, minimización, retención y borrado para nuevos datos. |
| Alta | Consultas de memoria y write-back usan `GeminiEmbeddings` | Una operación de incidentes puede provocar llamadas pagadas aunque no solicite RAG. Offline requiere sustituir también memoria, no solo generador/router. |
| Media | Requirements mayormente con límites inferiores; sin lock versionado; CrewAI `==1.15.22`, google-genai `~=1.65.0`, FAISS `>=1.14.0` | Compatibilidad conjunta, disponibilidad de wheels y API del SDK pendientes de resolución. No afirmar incompatibilidad confirmada ni disponibilidad actual de modelos basándose en nombres configurados. |
| Media | Endpoints async invocan ejecución síncrona y reintentos con `time.sleep`; singletons y memoria por proceso | Posible bloqueo y divergencia entre workers; pruebas de concurrencia pendientes. MVP de telemetría con un worker explícito. No cambiar concurrencia de negocio en esta fase. |
| Media | `SemanticMemory` persiste vectores sin versión de modelo/dimensión en cada registro | Cambio de embeddings puede producir scores no comparables o error dimensional; separar migración/reindexado de instrumentación. |
| Media | Caché del pipeline verifica frescura al construir, no en cada consulta | Registrar fingerprint/configuración de esa instancia; no prometer detección inmediata de cambios posteriores del corpus. |
| Media | Métricas heredadas devuelven 0.0 con denominador cero | Dashboard EP3 debe convertir falta de muestra a null/N/D usando N, sin modificar contratos históricos. |
| Media | Evaluador hace routing, retrieval aislado y luego pipeline; reportes guardan query y respuesta | No confundir duración/costo de benchmark con una solicitud real ni publicar reportes crudos; resumen sanitizado separado. |
| Media | Flags de revisión en archivo draft y verified; reporte no distingue fakes | No inferir evidencia real por nombre de archivo/modelo. Añadir modo, hash del dataset y versión del fixture en EP3. |
| Media | No hay guardia general de red en `tests/conftest.py`; scripts live existen | Un `pytest` sin controles podría depender del entorno/telemetría de librerías. Incorporar bloqueo reproducible y separación explícita de pruebas live. |

No se hicieron escaneos de vulnerabilidades de dependencias, pruebas de carga, validación del catálogo Gemini ni consultas de documentación externa: esta es una revisión del código local, no una certificación de versiones actuales. No se inspeccionaron valores de secretos ni bases reales.

## 7. Entrega y pendientes

Cambios autorizados: este documento y [plan EP3](11-plan-implementacion-ep3.md). Código, dependencias, tests y configuración originales permanecen sin cambios. El siguiente paso necesario es obtener una línea base funcional offline en un entorno con dependencias; después, ejecutar los hitos del plan en una tarea de implementación separada. No hay evidencia para declarar terminada la regresión funcional.
