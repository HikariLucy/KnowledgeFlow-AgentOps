# Plan incremental de implementación EP3 — KnowledgeFlow AgentOps

> Para ejecución futura: aplicar `superpowers:executing-plans` tarea por tarea. Este archivo es una propuesta técnica; la auditoría actual no autoriza ni realiza su implementación.

**Objetivo:** añadir observabilidad y evaluación reproducible a la base EP2 manteniendo contratos HTTP, comportamiento RAG, herramientas y memoria.

**Arquitectura:** instrumentación explícita por límites de operación, correlación por contexto de ejecución y eventos JSON sanitizados en almacenamiento local separado. Agregación de solo lectura para un dashboard FastAPI + HTML/CSS/JavaScript integrado con la UI existente.

**Stack:** Python, FastAPI, Pydantic y biblioteca estándar para contexto, reloj y persistencia JSONL. Reutilizar evaluador y dobles existentes; no añadir frameworks frontend ni servicios externos al MVP.

**Especificación y evidencia:** [auditoría EP2](10-auditoria-ep2.md), [alcance](01-alcance-ep3.md), [arquitectura propuesta](02-arquitectura-dashboard.md), [métricas](03-metricas-y-pruebas.md), [seguridad](04-seguridad-y-uso-ia.md). Fecha: 2026-11-13.

## Restricciones globales

- Preservar respuestas, códigos HTTP, planificación, umbrales, reglas de escritura, recuperación y persistencia operacional existentes.
- No generar texto de conclusiones, justificaciones académicas o reflexiones individuales.
- Pruebas offline sin claves, sin `.env`, con red bloqueada y dobles también para embeddings de memoria. No ejecutar Gemini/CrewAI live, ni indexadores reales, sin autorización explícita posterior.
- No hacer push, merge ni cambios de infraestructura. La documentación no implica aprobación de despliegue.
- No registrar prompts, respuestas, chunks, texto de incidentes, memoria, embeddings, secretos, headers, query strings ni razonamiento privado.
- Todo resultado indica unidad, denominador N, período, commit y modo; desconocido es null/N/D. `offline_mock` no constituye evidencia de calidad de Gemini.
- No instrumentar CrewAI como si fuera el motor HTTP: su activación futura es un cambio funcional independiente.

## 1. Arquitectura mínima y contrato

```text
HTTP /api/query o /api/agent
  └─ span raíz de solicitud (incluye dependencias/errores)
      ├─ inicialización de componentes, si ocurre
      └─ RAG o servicio de agente
          ├─ planificación y lectura de memoria
          ├─ herramienta → RAG / SQLite
          │                 ├─ routing
          │                 ├─ embedding → retrieval → selección/contexto
          │                 └─ generación → validación/reparación
          └─ escritura de memoria
                    ↓ eventos de finalización sanitizados
              JSONL local con límites y rotación
                    ↓ lector/agregador de solo lectura
              /api/observability/* → HTML/CSS/JS
```

### Límites del MVP

Un proceso/worker, sin collector remoto, Prometheus, Grafana ni exportador OpenTelemetry. No se ha demostrado necesidad de introducirlos para esta entrega. JSONL queda fuera de `/static`, de `knowledge/`, del índice y de la DB de negocio. Propuesta inicial: `data/observability/`, acceso del usuario del servicio, retención 7 días, máximo 100 MiB y segmentos de 10 MiB, configurables y verificables. Son límites propuestos, no una política ya implantada.

Una cola acotada y un escritor exclusivo serializan eventos; al llenarse, descartarlos con contador de pérdida, sin bloquear ni hacer fallar la operación de negocio. No copiar datos sensibles a un fallback de consola. La pérdida de eventos debe mostrarse como cobertura incompleta. En múltiples workers este diseño requiere un almacén/collector coordinado; no habilitarlos sin esa revisión. El cierre intenta vaciar la cola con tiempo acotado; una caída abrupta puede dejar trazas incompletas.

### Esquema propuesto `SpanEvent` (versión 1)

| Campos | Contrato |
|---|---|
| `schema_version`, `event_id` | Versión y UUID para deduplicar |
| `trace_id`, `span_id`, `parent_span_id` | IDs aleatorios propios; raíz con parent null; no reutilizar conversation_id ni aceptar IDs externos arbitrarios |
| `started_at`, `ended_at`, `duration_ms` | UTC para fechas; reloj monotónico para duración no negativa |
| `component`, `operation` | Catálogo cerrado, p. ej. `tool/create_incident`, `memory/search`, `rag/retrieve`, `llm/generate` |
| `status`, `error_code` | `ok/error/cancelled`; código de catálogo o null, nunca excepción textual |
| `outcome`, `degraded` | Resultado de dominio separado: completed, needs_clarification, abstained, failed; degradación independiente del HTTP status |
| `execution_mode`, `git_commit`, `config_id` | `offline_mock/live/unknown`; procedencia confiable, no deducida del nombre de modelo ni enviada por el cliente |
| `attributes` | Allowlist tipada por operación: ruta plantilla, método, HTTP status, intent controlado, nombre de herramienta/modelo, k, umbral, cantidad de resultados/citas, intento, fingerprint |
| `input_tokens`, `output_tokens`, `total_tokens` | Enteros reportados por proveedor o null; no estimar desde caracteres ni duplicar consumo en spans padres |
| `run_id`, `case_id` | Opcionales para benchmark, asignados por evaluador con dataset sintético/revisado |

El esquema rechaza campos extra y limita longitudes/tamaño de evento. Un solo evento final por span; lectores deduplican por `event_id`. `trace_id` no se usa como etiqueta de agregación de métricas. No persistir `conversation_id`, hashes simples de mensajes ni IDs de incidentes: el MVP correlaciona un turno; el benchmark relaciona turnos mediante un escenario sintético. Si posteriormente se necesita correlación personal, requiere diseño de acceso/retención específico.

`ContextVar` mantiene contexto y se restaura en `finally`. Un context manager `span(component, operation, *, attributes=None)` emite al finalizar y no suprime ni reemplaza excepciones de negocio. Fallos internos del sink no deben convertirse en respuestas 500. Instrumentar límites explícitos, sin envolver indiscriminadamente todo método ni modificar reintentos o sleeps.

Los spans padres incluyen tiempo de hijos; no sumar sus duraciones como latencia total. Separar duración del intento LLM, espera/reintento y llamada lógica. `usage` se toma en el punto donde todavía existe la respuesta SDK, antes de reducirla a texto/vector. Si el SDK no lo expone, se conserva null.

### Semántica de métricas

| Métrica | Denominador/regla |
|---|---|
| Solicitudes y HTTP error rate | Spans raíz HTTP; 5xx/N solicitudes terminadas; 4xx separados |
| Fallos del agente | `outcome=failed` / turnos del agente terminados; abstención/aclaración no son errores técnicos |
| Degradación | Turnos con fallo absorbido de memoria/router / turnos con esa operación; mostrar cobertura |
| Herramientas | Intentos y errores por nombre permitido; contar en un solo límite, incluso si lanza excepción |
| Latencia | Duración raíz o por operación; media, p50, p95, N; percentil nearest-rank `ceil(p*N)` sobre muestras ordenadas; N=0 → null |
| Uso | Sumar solo spans de intentos proveedor con metadata disponible; mostrar cobertura `attempts_with_usage/attempts_total` |
| Calidad RAG | Reutilizar métricas por archivo/fuente de EP2 con sus denominadores; no llamarlas precisión semántica de respuesta |
| Consistencia | Para cada caso/configuración, comparar repeticiones 2..N contra la primera con regla predefinida; equivalencias/(N−1); menos de 2 ejecuciones válidas → N/D |

Para consistencia offline comparar status, intent, secuencia de herramientas, abstención y conjunto de IDs de fuentes; excluir IDs de incidentes generados y fechas. No comparar texto libre con igualdad exacta como prueba de consistencia semántica live. CPU/RSS y costos monetarios quedan fuera del MVP; mostrar N/D hasta disponer de medición/metodología verificable.

## 2. Hitos y criterios de aceptación

Cada hito produce un diff revisable y su evidencia. No avanzar sobre una regresión fallida. Los nombres de archivos nuevos siguientes son propuestas, no archivos ya creados.

### H0 — Recuperar línea base offline (requisito previo)

**Archivos:** revisar `requirements.txt`, `pytest.ini`, `tests/conftest.py`; proponer `scripts/run_tests_offline.py` y archivo de constraints reproducible tras resolver dependencias. No alterar lógica de aplicación.

- [ ] Crear un entorno aislado con Python 3.12 y dependencias declaradas; verificar resolución y `pip check`, registrar versiones exactas. Aprovisionamiento de paquetes separado de la ejecución offline; usar wheelhouse local si no hay red.
- [ ] Reproducir la guardia de red de la auditoría, ampliada con aislamiento a nivel de proceso; impedir carga de credenciales y llamadas desde SDKs/subprocesos. Mantener TestClient en memoria.
- [ ] Ejecutar la suite completa `python -m pytest -q` con guardia activa; conservar log, JUnit, versión de intérprete/dependencias y SHA.
- [ ] Verificar que los tests de CrewAI solo construyen objetos y que todos los caminos de embeddings usan dobles; añadir prueba del guard que rechace una conexión externa antes de envío.

**Aceptación:** colección completa, cero errores de colección, cero fallos funcionales, omisiones explícitamente justificadas, cero solicitudes externas; no reemplazar módulos ausentes por stubs de importación para simular compatibilidad. El resultado previo de 35 errores sigue vigente hasta obtener evidencia nueva. No fijar un conteo esperado de tests aprobados sin ejecutarlos.

### H1 — Contrato, correlación y almacenamiento seguro

**Crear:** `app/observability/{__init__,schemas,context,sanitize,sink}.py`, `tests/test_observability_core.py`, `tests/test_observability_privacy.py`. **Modificar:** `app/core/config.py`, `.gitignore` para opciones y exclusión de logs. Variables propuestas: enabled, directory, retention_days, max_bytes, segment_bytes; deshabilitado por defecto al introducir la capa.

**Interfaces:** `span(component, operation, *, attributes=None)` produce contexto con IDs; `emit(event: SpanEvent) -> None` aplica allowlist y envía al sink; `sanitize_attributes(operation, attributes) -> dict` rechaza claves no previstas. Ninguna interfaz recibe un request/AgentState completo.

- [ ] Escribir y ejecutar tests que fallen por ausencia de contrato: árbol padre/hijo, restauración después de excepción, dos ejecuciones concurrentes sin mezcla y reloj de prueba controlado.
- [ ] Implementar esquema y contexto con timestamps UTC/reloj monotónico inyectable; error técnico cerrado sin texto libre.
- [ ] Implementar cola/escritor, permisos, rotación y purga por antigüedad/tamaño; contador de eventos descartados fuera del propio sink fallido.
- [ ] Probar secretos señuelo anidados, saltos de línea, atributos extra, mensajes de excepción, disco no escribible/lleno, cola llena y última línea JSON truncada.
- [ ] Ejecutar los tests nuevos y la suite offline completa; revisar diff y logs generados.

**Aceptación:** JSON válido sin datos señuelo; IDs únicos y parentesco correcto; ninguna excepción del sink altera el resultado de negocio; límites y purga verificables con reloj/archivos temporales. Cero cambios a tablas de incidentes/memoria.

### H2 — Instrumentación HTTP, agente, herramientas y memoria

**Modificar:** `app/main.py`, `app/api/{routes,agent_routes}.py`, `app/agentic/{service,orchestrator,planner}.py`, `app/tools/{knowledge,incidents}.py`, `app/memory/{short_term,long_term,semantic,write_back}.py`. **Crear:** `tests/test_observability_api.py`, `tests/test_observability_agent.py`.

**Interfaces:** consumir `span`/`emit`; publicar únicamente eventos v1. Mantener `AgentRequest`, `AgentResponse`, `QueryRequest` y `QueryResponse` sin cambios. Correlación HTTP mediante header de respuesta `X-Trace-ID` generado en servidor, sin confiar en el valor enviado por cliente.

- [ ] Preparar pruebas de paridad de status/body y efectos SQLite con observabilidad activada/desactivada, usando fixtures del agente existente.
- [ ] Crear raíz que cubra resolución de dependencias y respuesta de errores; instrumentar servicio, planner, herramientas y finalización según el mapa de auditoría.
- [ ] Capturar fallo propagado de herramienta, failed de dominio con HTTP 200, abstención, aclaración, error de memoria absorbido y límite de iteraciones, sin cambiar su tratamiento.
- [ ] Ejecutar tests API/orquestador/memoria y suite offline; verificar una traza por turno y una llamada contada por herramienta.

**Aceptación:** respuestas y efectos operacionales equivalentes; 422/503/500 correlacionados; memoria degradada visible sin cambiar outcome; ningún request/response o contexto de memoria serializado en eventos; concurrencia de trazas aislada. No aplicar autenticación nueva a endpoints de negocio dentro de este hito: esa corrección requiere alcance propio.

### H3 — RAG y llamadas a proveedor

**Modificar:** `app/rag/{pipeline,retriever,embeddings,generator,vectorstore}.py`, `app/agents/source_router.py`; instrumentar `build_rag_context` desde pipeline. **Crear:** `tests/test_observability_rag.py`.

**Interfaces:** eventos v1 por etapa; metadata de uso opcional obtenida de respuesta SDK, nunca de contenido. Conservar interfaces de retorno actuales de generador/embeddings.

- [ ] Preparar pruebas con reloj y SDK falso para router exitoso/fallback, scope manual, búsqueda dual, abstención temprana, reparación de citas y reintentos.
- [ ] Instrumentar retrieval y embedding por separado, conteos de candidatos/seleccionados y generación/reparación; registrar intento incluso en excepción.
- [ ] Adaptar extracción de uso solo después de consultar documentación vigente de la versión resuelta con Context7, siguiendo AGENTS.md; no inventar campos SDK.
- [ ] Ejecutar los tests RAG/SDK existentes y nuevos; verificar que instrumentación no añade invocaciones al proveedor ni duplica tokens en spans padre.

**Aceptación:** fake sin uso → null, nunca costo 0 inferido; abstención sin generación; scope=all refleja las dos búsquedas existentes; número y orden de llamadas/reintentos conservado. No optimizar el doble embedding como parte de instrumentación.

### H4 — Agregación y benchmark EP3 reproducible

**Crear:** `app/observability/{queries,metrics}.py`, `evaluation/agentops/dataset.json`, `app/evaluation/agentops_runner.py`, `tests/test_observability_metrics.py`, `tests/test_agentops_evaluation.py`. **Reutilizar:** métricas EP2 sin cambiar contratos; ampliar reporter solo con exportación separada sanitizada.

**Interfaces:** `summarize(filters) -> Summary`, `list_traces(filters, cursor, limit) -> TracePage`, `get_trace(trace_id) -> TraceDetail`. Summary lleva N, unidades, período, modo, cobertura y versión. Cursor y limit validados, límite propuesto 100 registros por página.

- [ ] Definir fixtures y resultado esperado para consulta interna/externa, fuera de dominio, creación validada, nota multi-turno, fallo de herramienta, fallo de memoria, falta de contexto e intento de instrucción maliciosa. SQLite temporal aislada por escenario; multi-turno comparte solo su escenario.
- [ ] Definir casos/repeticiones y equivalencia antes de correr; metadatos con SHA, dirty, hash de dataset, config_id, fingerprint y modo. Empezar con 3 repeticiones offline por escenario, sin presentarlas como estadística del modelo real.
- [ ] Implementar agregación y normalización N=0 → null, filtros por tiempo UTC/componente/estado/modo, deduplicación y exclusión explícita de trazas incompletas de métricas de finalización.
- [ ] Ejecutar benchmark offline con fakes; exportar resultados separados de reportes crudos y conservar vínculo run/case/trace. No reetiquetar evidencia EP2 como ejecución EP3.
- [ ] Probar percentiles para muestras conocidas, errores con distintos denominadores, duplicados, corpus vacío, datos parciales y separación de modos; correr suite completa.

**Aceptación:** mismos fixtures/configuración producen mismos resultados operacionales; duración sigue siendo observada, no fijada; métricas calculables desde eventos; N=0 se representa N/D; no aparecen queries/respuestas sensibles en exportación; no se ejecuta el runner EP2 con su pipeline live por defecto.

### H5 — API de consulta y dashboard propio

**Crear:** `app/api/observability_routes.py`, `app/ui/static/observability.{html,css,js}`, `tests/test_observability_dashboard.py`. **Modificar:** registro de rutas en `app/main.py` y navegación de la UI existente.

**Interfaces HTTP propuestas:** `GET /api/observability/summary`, `/traces`, `/traces/{trace_id}`. Paginación/filtros consumen H4; sin endpoints de escritura. Ruta de página `/observability`.

- [ ] Definir acceso antes de exponer datos: MVP local por defecto, API deshabilitada sin configuración; para servicio compartido, dependencia de autorización por token de entorno usando header Authorization, no query string, no token embebido en JS ni guardado en localStorage/logs. La UI mantiene el token solo en memoria. Si se adopta autenticación existente externa, verificarla por integración antes de habilitar.
- [ ] Probar 401/403 según política elegida, IDs inexistentes, filtros inválidos, límites y acceso a logs fuera del directorio permitido; ningún endpoint devuelve bytes de archivo arbitrario.
- [ ] Construir resumen, tabla paginada y árbol de spans; usar texto escapado/`textContent`, estados de carga/error/vacío, unidades, N y modo visible. DATOS SINTÉTICOS para fakes.
- [ ] Verificar navegación, filtros, teclado y visualización móvil con fixture sanitizada; ejecutar tests de UI existentes y nuevos.

**Aceptación:** sin acciones sobre incidentes; acceso no autorizado bloqueado; datos desconocidos N/D; detalle rastreable al evento, sin HTML inyectado; sin regresión de `/` y `/agent`. No desplegar públicamente el servicio de negocio sin tratar su riesgo de autorización identificado en la auditoría.

### H6 — Verificación de seguridad, impacto y evidencia técnica

**Archivos:** ampliar tests de observabilidad y `docs/evidence/` con resultados sanitizados; actualizar estado del roadmap únicamente cuando haya evidencia.

- [ ] Ejecutar suite offline completa y benchmark con telemetría activada/desactivada sobre la misma configuración; registrar overhead observado, N y condiciones. Objetivo inicial propuesto: p95 adicional local ≤10 ms en 100 turnos con fakes después de calentamiento; registrar incumplimiento y revisar diseño, no editar resultados.
- [ ] Verificar que operaciones conservan salida/efectos con sink roto, rotación concurrente, falta de eventos y cancelación. Probar retención y descarte sin guardar cuerpos ni excepciones.
- [ ] Revisar un corpus de eventos con secretos/PII señuelo y revisión humana de campos permitidos; validar que reportes/archivos exportados no eluden sanitización.
- [ ] Conservar commit, versiones, comandos, log/JUnit, datasets/hash, eventos sanitizados y capturas reales del dashboard. Revisar diff final; dejar rollback por configuración de observabilidad deshabilitada.

**Aceptación:** resultado verificable por escenario, regresión funcional aprobada, límites y pérdida de telemetría visibles, riesgos pendientes expresos. Prueba live, carga multiworker, CPU/RSS, costos y semántica del modelo permanecen N/D hasta trabajo y autorización específicos. El informe y defensa académica los redacta el equipo.

## 3. Orden y foco de revisión

Orden: H0 → H1 → H2 → H3 → H4 → H5 → H6. Seguridad del dato empieza en H1, no se posterga al último hito. Revisar especialmente: aislamiento concurrente (H1/H2), éxito HTTP con error de dominio (H2), uso desconocido/reintentos (H3), denominador vacío/modos mezclados (H4), datos incompletos y acceso no autorizado (H5/H6).

Estado de todos los hitos: **pendientes de implementación**. La auditoría ejecutó pruebas, pero H0 sigue abierto por dependencias ausentes. No se ha construido ni publicado el dashboard, generado métricas operativas ni consumido tokens Gemini como parte de este plan.
