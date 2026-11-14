# Observabilidad local segura

> Esta página conserva el alcance y evidencia del Hito 2. El Hito 3 agrega persistencia acotada, retención, agregación y API de lectura; ver [contrato y operación actual](13-agregacion-metricas.md). Las limitaciones históricas sobre ausencia de almacenamiento/rotación se refieren al Hito 2. Para sesiones prolongadas usar la configuración del Hito 3, no la redirección JSONL de demostración.

Implementación basada en [la auditoría EP2](10-auditoria-ep2.md) y [el plan incremental](11-plan-implementacion-ep3.md). Alcance entregado: instrumentación y pruebas; no dashboard, collector, benchmark live ni cambios en reglas de negocio. No requiere servicios externos ni nuevas dependencias de aplicación.

## Activación y ejecución

Desde la raíz Git, el subdirectorio `KnowledgeFlow-AgentOps/` del workspace:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pip check
OBS_ENABLED=true .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-access-log
```

Instalar paquetes no es ejecutar el agente. No enviar solicitudes live ni ejecutar el indexador sin autorización para consumir Gemini. Una operación de incidentes también puede generar embeddings de memoria. Las pruebas siguientes sustituyen proveedores; no necesitan índice, API key ni `.env`.

| Variable | Valor por defecto | Uso |
|---|---|---|
| `OBS_ENABLED` | `false` | Activa spans y logs JSON propios. Se lee al importar `app.main`; reiniciar para cambiar. |
| `OBS_EXECUTION_MODE` | `unknown` | `unknown`, `offline_mock` o `live`; etiqueta explícita, no activa llamadas ni autoriza consumo. |
| `OBS_SESSION_KEY` | Ausente | Secreto de al menos 32 bytes para HMAC de sesión. Sin él se genera una clave aleatoria por proceso. No dejar una variable vacía: omitirla. |

`OBS_SESSION_KEY` es `SecretStr` en Settings. Generar un valor aleatorio local, por ejemplo con `python3 -c 'import secrets; print(secrets.token_hex(32))'`, y suministrarlo por entorno o `.env` excluido de Git. No copiar el valor a documentos/evidencias. Cambiarlo rompe deliberadamente la correlación anterior; compartirlo entre procesos permite correlación estable de sesiones, pero no agrega un almacén multiworker.

El logger dedicado emite **una línea JSON por evento a stderr**, sin propagar al logger raíz. No instala handlers sobre librerías de terceros. Uvicorn y librerías pueden tener sus propios logs; no se afirma que todo stderr de cualquier proceso sea JSON ni que logs externos queden sanitizados. `--no-access-log` evita el registro de IP/URL por el access logger de Uvicorn.

Para conservar la salida local de una demostración autorizada:

```bash
mkdir -p data/observability
chmod 700 data/observability
umask 077
OBS_ENABLED=true .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-access-log --log-level critical 2>data/observability/run.jsonl
```

`data/observability/` está excluido de Git. La redirección captura también stderr ajeno al logger si lo hubiera; los consumidores deben validar JSON y `schema_version`. Esta entrega no implementa rotación/retención ni almacenamiento interno: cerrar/archivar/borrar los archivos de demo de acuerdo con la política del equipo. No publicarlos ni montarlos bajo `/static`.

## Correlación y campos

- `session_id`: HMAC-SHA256 del conversation_id validado, sin persistir el valor original. Permite relacionar turnos con la misma clave de proceso. Antes de validar una petición, se usa un ID aleatorio; los errores 422/503 previos al endpoint no leen el body para intentar recuperar una sesión.
- `trace_id`: nuevo UUID por petición `/api/agent`. Nunca se toma de headers aportados por cliente. Se devuelve en `X-Trace-ID` en respuestas que atraviesan el middleware, incluidos errores HTTP manejados.
- `span_id`: identificador de operación; `parent_span_id` enlaza el padre o es null en la raíz. `ContextVar` aísla ejecuciones concurrentes y restaura el contexto al terminar o lanzar una excepción.
- `started_at`/`ended_at`: fechas UTC. `duration_ms`: diferencia de `time.perf_counter`, no resta de fechas. Los padres incluyen el tiempo de sus hijos: no sumar todos los spans como latencia total.
- `event`: `span` o `log`; `schema_version=1`, `event_id` y `level` (`INFO`/`ERROR`). Los logs usan códigos fijos, no mensajes de excepción ni stack traces.
- `status`: resultado técnico `ok/error/cancelled`. `outcome`: resultado de dominio cuando existe (`completed/failed/abstained/needs_clarification`). Un HTTP 200 puede contener outcome failed; una abstención o aclaración no se convierte en error técnico.
- `error_code`: categoría cerrada, entre ellas validation_error, timeout, io_error, not_found, provider_error, internal_error, http_client_error, http_server_error y cancelled. No es diagnóstico exhaustivo del proveedor: no se distingue todavía cuota de otros errores SDK.
- `attributes`: allowlist con HTTP status, intención canónica, herramientas utilizadas, conteo de llamadas/iteraciones/resultados/fuentes/citas, scope, abstención y degradación cuando el resultado los ofrece.
- `input_tokens`, `output_tokens`, `total_tokens`: enteros observados o null; solamente spans `provider` contienen uso. No se duplican tokens en padres. `output_tokens` corresponde a candidates, no a tokens privados de pensamiento. `total_tokens` conserva el total reportado y puede diferir de input + output. No se registra razonamiento interno.
- `dropped_events`: contador por proceso de fallos de emisión/preparación de telemetría; se incluye en posteriores spans que sí logren emitirse. No puede conservarse si el proceso cae o el destino nunca se recupera.

`provider_call` lee `usage_metadata` de respuestas Gemini. Para embeddings también acepta estadísticas explícitas `embeddings[].statistics.token_count`, si todos los valores son enteros no negativos aunque el SDK los modele como float. No transforma caracteres facturables en tokens ni estima totales ausentes. Los mocks sin metadata y respuestas sin uso producen null; cero se conserva únicamente si fue reportado.

## Puntos instrumentados y compatibilidad

| Componente | Operaciones |
|---|---|
| HTTP | Middleware ASGI puro para `/api/agent`; abarca dependencias, validación y envío de respuesta |
| Servicio y orquestador | `AgentService.execute`, `AdaptiveOrchestrator.execute` |
| Planificador | `RuleBasedPlanner.plan`, `hydrate_memory_context` |
| Herramientas | `search_knowledge`, `create_incident`, `search_incidents`, `append_incident_note` en sus métodos `run` |
| Memoria | Búsqueda/remember semánticos y write-back; errores absorbidos siguen reflejándose como degradación |
| RAG | Pipeline, retrieval, routing/generación Gemini |
| Proveedor | Una emisión por intento real de `generate_content`/`embed_content`, incluidos reintentos y reparación existentes |

Los decoradores conservan firma, retorno y excepción de negocio. No cambian reglas, llamadas al SDK, reintentos, prompts, SQL, contratos JSON ni decisiones del planner. `X-Trace-ID` es la única adición al contrato HTTP. Los logs antiguos de rutas, loaders, router y generador se sustituyeron por códigos sanitizados; con observabilidad desactivada tampoco se emiten esos logs propios. El cliente Gemini, la memoria y los datos originales de respuesta no se reescribieron.

Un fallo del destino de logs, del reloj de preparación o de la generación de metadata no debe romper el resultado del negocio; está cubierto por pruebas. La escritura a stderr es síncrona: un destino lento aún puede añadir espera. No se implementó la cola/rotación sugerida en el plan; se eligió esta entrega mínima sin threads de escritura ni almacenamiento nuevo. El alcance actual del usuario prima sobre los hitos futuros del plan.

No se registran cuerpos HTTP, query strings, IP, headers, argumentos de herramientas, conversation_id original, incident IDs, texto de memoria, archivos fuente, vectores, respuestas, prompts, API keys ni error textual. No se serializa `AgentState`/`AgentRequest`. Los IDs son pseudónimos, no autenticación. La ausencia de autorización y la exposición de memoria en el contrato de negocio señaladas por la auditoría siguen pendientes; no se debe publicar el servicio como aplicación multiusuario segura por incorporar telemetría.

## Pruebas offline y evidencia

```bash
# Requiere checkout sin .env; el runner no borra ni modifica uno existente.
.venv/bin/python scripts/run_tests_offline.py
.venv/bin/python scripts/run_tests_offline.py --observe

# Solo en Linux/sandboxes que bloquean el socketpair de asyncio:
.venv/bin/python scripts/run_tests_offline.py --uvloop
.venv/bin/python scripts/run_tests_offline.py --uvloop --observe

# Con reporte JUnit, fuera del repositorio:
.venv/bin/python scripts/run_tests_offline.py --uvloop --junitxml=/tmp/knowledgeflow-tests.xml
```

El runner vacía claves comunes, desactiva telemetría externa por variables, usa almacenamiento temporal de CrewAI y ejecuta pytest sin plugins externos. Un audit hook bloquea resolución/conexión/envío de sockets Python y falla la corrida si detecta intentos, aunque una librería los absorba. No sustituye firewall/aislamiento del sistema para extensiones nativas y subprocesos. Las corridas verificadas se ejecutaron en sandbox con red restringida, sin `.env` ni proveedores reales. `--uvloop` solo selecciona el bucle de los tests: no modifica `app.main` ni obliga a ese backend en producción.

Evidencia ejecutada el 2026-11-13, Python 3.12.3, intérprete temporal `/tmp/knowledgeflow-obs-venv/bin/python`:

| Corrida | Resultado real |
|---|---|
| Base heredada antes de integrar spans (excluyendo los 3 archivos nuevos) | **242 passed, 20 warnings in 4.69s** |
| Suite completa, modo de aplicación desactivado por defecto (las pruebas nuevas activan su observer) | **275 passed, 20 warnings in 5.02s** |
| Suite completa con `--observe` | **275 passed, 20 warnings in 4.88s** |
| Contador de red de las tres corridas | **0** |
| `pip check` | **No broken requirements found** |

Los 20 warnings son de deprecación FastAPI/Starlette y CrewAI, también presentes en la línea base. No son fallos de observabilidad. Los tiempos de pytest no son mediciones de latencia productiva. Consumo/costo live: **N/D**.

Los 33 tests nuevos cubren JSON, allowlist, errores sin secretos, jerarquía, aislamiento concurrente, HMAC estable por sesión, Unicode, reloj monotónico, cancelación, fallo de reloj/destino/log, metadata SDK real con proveedor mock, tokens inválidos/ausentes/cero, reintentos, estado de dominio frente a HTTP, degradación de memoria, API 422/503/500 y paridad de respuestas/operaciones SQLite. Se verificó creación, consulta y anexado sin registrar contenido.

Artefactos temporales: `/tmp/knowledgeflow-obs-final.log`, `/tmp/knowledgeflow-obs-final.xml`, `/tmp/knowledgeflow-obs-enabled.log`, `/tmp/knowledgeflow-obs-enabled.xml`. Se conserva el [snapshot de dependencias](evidence/observability-test-environment.txt) como referencia de versiones, no como lock con hashes. La instalación por red falló por DNS; el entorno final se resolvió con `pip --no-index` desde wheels de caché local, sin modificar `requirements.txt`. Para reproducir versiones con acceso al registro:

```bash
.venv/bin/python -m pip install -r requirements.txt -c docs/evidence/observability-test-environment.txt
```

Context7 CLI fuera del sandbox fue rechazado por la política del entorno; se consultó el conector Context7 y se contrastó el esquema con google-genai 1.65.0 instalado. Referencias: [middleware ASGI y ContextVar en Starlette](https://github.com/kludex/starlette/blob/main/docs/middleware.md), [modelos de respuesta del SDK Google Gen AI](https://github.com/googleapis/python-genai/blob/main/google/genai/types.py). La documentación vigente puede diferir de la versión fijada; las pruebas usan modelos de la versión instalada.

## Pendientes separados de esta entrega

Agregación/percentiles y dashboard; persistencia con cola, rotación/retención y backpressure; propagación W3C entre servicios y collector; métricas CPU/RSS/costo; benchmark con ground truth y autorización live; instrumentación de ejecución CrewAI live y otras rutas HTTP. La correlación entregada es local al proceso/flujo: no se afirma tracing distribuido interoperable completo. Las excepciones no manejadas emitidas por el middleware exterior de FastAPI pueden producir un 500 sin `X-Trace-ID`, aunque el span de error queda registrado. La API de negocio sigue requiriendo una revisión de autenticación/propiedad de conversaciones antes de exposición compartida.

## Archivos de esta entrega

| Tipo | Archivos |
|---|---|
| Nuevos, núcleo | `app/observability/__init__.py`, `telemetry.py`, `middleware.py` |
| Modificados, entrada/configuración | `app/main.py`, `app/core/config.py`, `app/api/agent_routes.py`, `app/api/routes.py`, `.env.example`, `.gitignore` |
| Modificados, agente | `app/agentic/service.py`, `orchestrator.py`, `planner.py`, `app/agents/source_router.py` |
| Modificados, herramientas/memoria | `app/tools/incidents.py`, `knowledge.py`, `app/memory/semantic.py`, `write_back.py` |
| Modificados, RAG | `app/rag/pipeline.py`, `retriever.py`, `generator.py`, `embeddings.py`, `loaders.py` |
| Nuevos, verificación | `scripts/run_tests_offline.py`, `tests/test_observability_core.py`, `test_observability_middleware.py`, `test_observability_integration.py` |
| Documentación | `README.md` modificado; este documento y `docs/evidence/observability-test-environment.txt` nuevos |

Los nombres abreviados comparten el directorio de la ruta anterior en la misma celda. `docs/10-auditoria-ep2.md` y `docs/11-plan-implementacion-ep3.md` ya estaban sin versionar al iniciar esta implementación y se preservaron. No se cambiaron tests heredados, requirements, repositorios remotos, índices ni bases de negocio. Trabajo en rama local `feat/observability`; sin commits, merge ni push.
