# Hito 3 — Almacenamiento y agregación operacional

Esta capa consume los eventos reales de [observabilidad](12-observabilidad.md). No modifica agentes, incidentes, prompts, proveedores ni herramientas. No incorpora frontend, llamadas Gemini, dependencias nuevas o resultados de benchmark. Todos los datos de las pruebas nuevas son **sintéticos**.

## Configuración y operación

| Variable | Predeterminado | Contrato |
|---|---|---|
| `OBS_ENABLED` | `false` | Emisión de eventos; sigue desactivada por defecto |
| `OBS_STORE_ENABLED` | `false` | Abre el almacén y activa mantenimiento; puede consultar historia con emisión desactivada |
| `OBS_STORE_PATH` | `data/observability/events.sqlite3` | Base exclusiva de telemetría, nunca una base de incidentes |
| `OBS_RETENTION_DAYS` | `7` | 1–365 días por fecha de finalización/timestamp UTC |
| `OBS_MAX_EVENTS` | `50000` | 1–1000000 filas conservadas, compartidas entre todos los modos |
| `OBS_MAX_BYTES` | `67108864` | Techo del archivo SQLite: 1 MiB–1 GiB, redondeado hacia abajo a páginas |
| `OBS_READ_KEY` | Ausente | Secreto administrativo independiente de al menos 32 bytes; ausencia bloquea API |
| `OBS_EXECUTION_MODE` | `unknown` | Un único modo por proceso: `offline`, `mock`, `live`; `unknown` y `offline_mock` son particiones heredadas separadas |

`offline` identifica ejecuciones locales sin sustitutos; `mock` identifica pruebas con dobles, aunque también sean offline. El runner declara `mock`. `live` es una etiqueta, **no autoriza consumo**. No se reclasifican datos históricos `offline_mock` ni `unknown`, y ninguna consulta combina modos. La etiqueta depende de la configuración del operador; no certifica por sí sola ausencia de red.

Ejemplo de inicio sin solicitudes live (las claves se suministran por un mecanismo local, sin versionarlas):

```bash
# Desde la raíz Git KnowledgeFlow-AgentOps/ del workspace.
# OBS_READ_KEY debe existir en el entorno; por ejemplo, generado localmente con secrets.token_hex(32).
OBS_ENABLED=true OBS_STORE_ENABLED=true OBS_EXECUTION_MODE=offline \
  .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-access-log

# Consultar únicamente metadata; no ejecuta el agente.
curl --get http://127.0.0.1:8000/api/observability/metrics \
  -H "X-Observability-Key: $OBS_READ_KEY" --data-urlencode execution_mode=offline
curl --get http://127.0.0.1:8000/api/observability/events \
  -H "X-Observability-Key: $OBS_READ_KEY" --data-urlencode execution_mode=mock \
  --data-urlencode limit=100 --data-urlencode since=2026-11-13T00:00:00Z
```

Usar HTTPS si se accede fuera de loopback y restringir esta clave a operadores: no es autenticación por usuario ni autorización de conversaciones. No incluirla en query strings, código frontend ni logs. La seguridad de la API de negocio sigue siendo un asunto separado. Las consultas devuelven `Cache-Control: no-store`. Sin clave configurada: 503; clave ausente/incorrecta: 401; consulta inválida: 422 sin eco de la entrada; almacén inaccesible: 503, nunca métricas cero.

Con almacenamiento habilitado, el handler escribe **una sola copia** en SQLite y no duplica eventos a stderr. Sin almacenamiento mantiene la salida JSON histórica. No redirigir stderr a un archivo ilimitado en sesiones prolongadas. Los logs ajenos a este observer siguen fuera del alcance del almacén.

## Esquema y límites

SQLite estándar, identidad `PRAGMA application_id=0x4B464F42` y `user_version=1`, tabla `events`. Antes de abrir un archivo existente para escritura se exige esa identidad en modo lectura; se rechazan bases ajenas sin cambiar sus bytes ni permisos. Esquema:

- `seq INTEGER PRIMARY KEY AUTOINCREMENT`: secuencia estable para paginación, no se reutiliza tras rotación.
- `event_id TEXT UNIQUE`: deduplicación mientras el evento está retenido.
- `occurred_at`: `ended_at` para spans, `timestamp` para logs, UTC con microsegundos fijos.
- `execution_mode`, `trace_id`, `component`, `operation`, `status`: proyecciones indexadas del evento.
- `payload`: JSON validado del mismo evento `schema_version=1`; no existe una segunda tabla de spans ni contadores materializados.

Índices: tiempo, modo/tiempo, modo/secuencia, modo/traza/secuencia, modo/operación/tiempo, modo/estado/tiempo y modo/componente/tiempo. Las consultas usan parámetros SQL. El contrato de ingestión valida IDs hexadecimales, operaciones/códigos cerrados, tiempos con zona, duración finita no negativa, tokens enteros no negativos solo en proveedor y atributos permitidos. Campos extra se descartan; eventos inválidos se rechazan. Máximo 16 KiB por evento serializado. `session_id` pseudónimo se conserva internamente y se excluye de las respuestas API; no se almacenan prompts, textos, nombres, IP ni cuerpos HTTP.

**Rotación lógica:** elimina filas más antiguas por secuencia al alcanzar el máximo de eventos. Al recibir `SQLITE_FULL`, revierte la inserción, elimina el cuarto más antiguo en una transacción independiente y reintenta hasta dos veces. No genera archivos históricos fuera de los límites. SQLite reutiliza páginas liberadas. El archivo puede conservar su tamaño máximo después de borrar; no se ejecuta `VACUUM` durante solicitudes.

**Retención:** borra por fecha al arrancar, al insertar y cada 60 segundos durante el lifespan de FastAPI. Las consultas excluyen expirados inmediatamente, incluso si el proceso estuvo detenido. Con el servidor detenido no existe un servicio externo que borre datos: el borrado físico se retoma al arrancar. `secure_delete=ON` borra contenidos de las filas eliminadas en páginas; no garantiza eliminación forense de snapshots/disco.

**Límite físico:** `max_page_count` se aplica en cada conexión de escritura; archivo principal ≤ `floor(OBS_MAX_BYTES/page_size)*page_size`. Modo journal DELETE, sin WAL acumulativo. Reservar aproximadamente **2× OBS_MAX_BYTES más overhead de journal** para archivo principal y rollback journal transitorio. El límite configurado no es una cuota del directorio ni controla otros archivos. Un archivo existente mayor que el límite se rechaza, no se destruye. Directorios nuevos 0700, archivo 0600; no se cambian permisos de directorios preexistentes. Usar un directorio privado y exclusivo.

Cada escritura abre una conexión, usa transacción inmediata y espera como máximo 100 ms por locks. No hay cola en memoria ni hilo de escritura. La escritura síncrona puede añadir latencia (incluidos hasta 100 ms por contención de cada evento); los spans padre pueden incluir ese overhead. Un fallo se contabiliza en `dropped_events` del proceso y no cambia el resultado de negocio; no hay fallback ilimitado a stderr. Retención, rotación, caídas o bloqueo pueden perder eventos y cortar trazas. Un error inicial de apertura deja consultas en 503; corregir configuración/disco y reiniciar. Se soportan conexiones concurrentes SQLite con configuración común; no es un collector distribuido ni se garantiza captura sin pérdidas con múltiples workers.

## API de lectura v1

Todas las rutas requieren `X-Observability-Key`. No hay endpoints de escritura ni dependencias de servicios/repositorios de incidentes.

| GET | Parámetros | Respuesta |
|---|---|---|
| `/api/observability/events` | Filtros comunes, `limit=100` (1–500), `after=0` (0–2^63−1) | `contract_version=1`, `items`, `next_after` o null |
| `/api/observability/metrics` | Filtros comunes | Solicitudes, ejecuciones, latencia HTTP, componentes, herramientas, tokens y estado de captura |
| `/api/observability/quality` | `execution_mode` obligatorio | `source=evaluated_benchmarks`, `status=not_evaluated`, `precision=null`, `consistency=null`, `benchmarks=[]` |

Filtros comunes: `execution_mode` **obligatorio**, `trace_id` (32 caracteres hex), `since`, `until` (ISO8601 con zona), `component`, `operation`, `status=ok|error|cancelled`. Período `[since, until)` sobre **fin del evento**, limitado por retención. `since < until`; fechas con offset se normalizan a UTC. Operaciones y componentes usan la allowlist de instrumentación, incluida validación de su combinación. Los logs sin operación/estado no coinciden con esos filtros.

Orden de eventos: secuencia de ingestión ascendente. Cada item incluye `sequence` y el evento validado sin `session_id`. Usar `next_after` con los **mismos filtros** para la siguiente página. Null indica fin en ese instante; pueden llegar eventos después. No hay snapshot entre páginas: la retención puede quitar eventos pendientes, pero no duplica los ya vistos. No hay offset profundo ni conteo total extra por página.

Los filtros se aplican a los eventos que alimentan cada agregado, **no expanden automáticamente toda la traza**. Filtrar `component=tool` deja cero spans HTTP en esa selección. La respuesta declara `scope=retained_events`: total cero significa cero eventos retenidos coincidentes, no ausencia garantizada de solicitudes reales. `collection.complete_history=false` evita presentar el almacén como historia completa. `enabled_in_this_process` y `dropped_events_in_this_process` no son contadores globales ni sobrevivientes a reinicios. Un almacén inaccesible devuelve 503.

## Fórmulas y denominadores

- `requests.total`: cantidad de spans `http/agent`, nunca logs ni hijos. `successful`: status ok, `failed`: error, `cancelled`: cancelled. `error_rate = failed / total`; sin solicitudes, null. Cancelaciones están en el denominador y tienen contador separado.
- `executions.total`: spans `agent/execute`. Éxito de dominio: status ok + outcome completed; fallo: status error o outcome failed; abstención y aclaración son categorías separadas; cancelación separada; status ok sin outcome es unknown. HTTP 200 no implica éxito de dominio. Los fallos previos al servicio (422/dependencias) cuentan en HTTP, no inventan ejecuciones de agente.
- Latencia HTTP: `request_latency_ms={count,mean,p50,p95}` sobre durations HTTP en milisegundos monotónicos. Media aritmética; percentil con interpolación lineal: ordenar x, r=(n−1)p, resultado x[floor(r)] + (x[ceil(r)]−x[floor(r)])·fracción(r). Para n=1 ambos percentiles son esa muestra; n=0 → null, count=0.
- `components`: mismas estadísticas por componente para spans, incluyendo errores/cancelaciones. `tools`: mismas estadísticas por operación de componente tool. Duraciones inclusivas: los padres incluyen hijos, **no sumar componentes como tiempo total**. No se mide tiempo exclusivo.
- `tokens.input_tokens|output_tokens|total_tokens`: `{observed_sum, observed_spans, total_spans}` solo para spans provider. Suma de valores presentes; ninguna observación → null; cero solo si fue reportado. Cobertura = observed_spans/total_spans (si hay proveedores). No extrapolar una suma parcial. No sumar input + output para inventar total. Cada intento/reintento tiene su span; un intento fallido sin usage sigue desconocido.

Los cálculos cargan los eventos coincidentes en memoria, acotados por el máximo de filas. Percentiles exactos requieren ordenar muestras. Esto sirve para el volumen local configurado; no se ofrece streaming de percentiles, tasa por segundo, costo monetario, CPU, RSS, SLA ni medición de rendimiento productivo. Los valores pueden cambiar entre llamadas por nuevas capturas y retención.

## Calidad separada

`QualityMeasurement` es un contrato reservado para resultados evaluados: benchmark_id, hash SHA256 del dataset, versión del evaluador, modo explícito, marca synthetic, fecha evaluada UTC, métrica precision/consistency, numerador y denominador positivo. Valida 0 ≤ numerador ≤ denominador y calcula su razón. No contiene texto libre de casos ni se construye desde eventos operacionales.

Todavía no hay importador, tabla de resultados evaluados ni benchmark ejecutado en este hito. Por ello GET quality devuelve null. El futuro evaluador debe definir ground truth, unidad de evaluación, conjunto y criterio de consistencia antes de publicar resultados. Un HTTP correcto, una cita o ausencia de excepción no demuestra precisión ni consistencia.

## Verificación y archivos

```bash
.venv/bin/python scripts/run_tests_offline.py --uvloop
.venv/bin/python scripts/run_tests_offline.py --uvloop --observe
# Omitir --uvloop fuera de sandboxes que bloquean socketpair de asyncio.
.venv/bin/python scripts/run_tests_offline.py --uvloop tests/test_observability_metrics.py tests/test_observability_metrics_api.py
```

El runner elimina variables OBS heredadas, fija modo mock y mantiene almacenamiento global desactivado para no tocar archivos reales. Los tests de integración habilitan almacenamiento temporal explícitamente y verifican captura activada/desactivada. No se usa Gemini real; todos los eventos de fixtures son sintéticos, no resultados live.

Nuevos: `app/observability/models.py`, `store.py`, `app/api/observability_routes.py`, `tests/test_observability_metrics.py`, `test_observability_metrics_api.py`, este documento y `docs/superpowers/plans/2026-11-13-metrics.md`.

Modificados sobre la entrega previa: `app/observability/telemetry.py`, `app/core/config.py`, `app/main.py`, `scripts/run_tests_offline.py`, `.env.example`, `README.md`, `docs/12-observabilidad.md`. Los otros cambios previos de la rama se preservan.

Documentación FastAPI consultada mediante Context7: [APIKeyHeader y dependencias de seguridad](https://fastapi.tiangolo.com/reference/security/). El intento CLI fuera del sandbox fue rechazado por la política de permisos; se utilizó el conector disponible.

### Evidencia ejecutada — 2026-11-13

Entorno reutilizado: Python 3.12.3, `/tmp/knowledgeflow-obs-venv/bin/python`, snapshot de dependencias de Hito 2. No se instalaron dependencias.

| Corrida | Resultado real |
|---|---|
| Línea base antes del Hito 3 | 275 passed, 20 warnings in 5.46s |
| Suite final, observabilidad desactivada por defecto | **313 passed, 20 warnings in 8.75s** |
| Suite final con `--observe` | **313 passed, 20 warnings in 8.99s** |
| Intentos de red en cada corrida | **0** |
| `pip check` | No broken requirements found |
| `git diff --check` | Sin errores |

38 pruebas nuevas, datos sintéticos: schema/allowlist, evento real del observer, deduplicación, modos, trazas, límites de página, período/zona horaria, percentiles, resultados de dominio, tokens parciales, rotación por filas y por capacidad física, expiración/reapertura, permisos, base ajena intacta, fallo de destino, configuración, lifespan, API autenticada, errores sin eco, GET sin mutaciones y paridad de respuesta del agente con SQLite activado/desactivado. Revisión independiente: detectó adopción de SQLite ajeno y normalización de filtros dict; ambos se reprodujeron con pruebas fallidas y se corrigieron antes de las suites finales.

Los 20 warnings de FastAPI/Starlette y CrewAI ya existían en la línea base. `pip check` también avisó que su caché local no era escribible; no afecta a la verificación de dependencias. Los tiempos son de ejecución de pruebas, no latencias productivas.

Artefactos temporales: `/tmp/knowledgeflow-metrics-off.log`, `/tmp/knowledgeflow-metrics-off.xml`, `/tmp/knowledgeflow-metrics-on.log`, `/tmp/knowledgeflow-metrics-on.xml`. No se ejecutaron benchmarks evaluados ni pruebas live. Sin push, merge ni dashboard.
