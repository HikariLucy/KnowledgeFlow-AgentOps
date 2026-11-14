# Hito 4 — Dashboard web local de observabilidad

Consola integrada en KnowledgeFlow, HTML/CSS/JavaScript sin framework, Streamlit, CDN ni dependencias frontend. Consume el almacén de eventos del Hito 3; no llama a Gemini ni ejecuta agentes. La telemetría y el dashboard siguen desactivados por defecto.

## Ejecución local

Desde la raíz Git `KnowledgeFlow-AgentOps/` del workspace, con el entorno Python de la aplicación instalado:

```bash
# Elegir una contraseña aleatoria de al menos 32 caracteres ASCII.
# Ingresarla sin eco; no usar OBS_READ_KEY ni copiarla al código.
read -r -s -p 'Contraseña local del dashboard: ' OBS_DASHBOARD_PASSWORD
export OBS_DASHBOARD_PASSWORD

OBS_DASHBOARD_ENABLED=true OBS_STORE_ENABLED=true OBS_ENABLED=false \
  .venv/bin/python -m uvicorn app.main:app \
  --host 127.0.0.1 --port 8000 --no-access-log --no-proxy-headers
```

Abrir **http://127.0.0.1:8000/dashboard**. El navegador solicitará usuario **observer** y la contraseña definida. El dashboard también está enlazado desde la consulta RAG y la página del agente.

No hace falta configurar `OBS_READ_KEY` para este acceso local: los endpoints administrativos del Hito 3 conservan su propio mecanismo y quedan inaccesibles si no tienen clave. `OBS_STORE_ENABLED=true` permite leer el historial y mantener retención aunque `OBS_ENABLED=false`. Una base nueva aparece vacía, sin métricas ni eventos de demostración insertados automáticamente. Elegir el modo y período en que realmente se capturaron eventos. Para capturar sesiones futuras, seguir las instrucciones y restricciones de [observabilidad](12-observabilidad.md) y [almacenamiento](13-agregacion-metricas.md).

| Configuración nueva | Predeterminado | Significado |
|---|---|---|
| `OBS_DASHBOARD_ENABLED` | `false` | Habilita rutas locales; desactivado responde 404 |
| `OBS_DASHBOARD_PASSWORD` | Ausente | Contraseña administrativa independiente, 32+ caracteres ASCII; ausencia responde 503 |

Una contraseña corta/no ASCII o igual a `OBS_READ_KEY` se rechaza en Settings. Reiniciar para aplicar cambios. No versionar `.env` ni claves. No dejar la variable vacía; omitirla si no se usa.

## Acceso y límites de seguridad

- **No soporta exposición remota.** Ejecutar únicamente en loopback, con `--no-proxy-headers`. No publicar, enlazar a `0.0.0.0`, colocar detrás de un reverse proxy, túnel público ni reenviador de puertos. No se implementó autenticación multiusuario, roles ni autorización por conversación.
- Cada ruta del dashboard exige autenticación HTTP Basic independiente, cliente loopback y Host literal `127.0.0.1` o `[::1]`. No se acepta `localhost` ni otro nombre DNS. Se rechazan `Forwarded`, `X-Forwarded-*`, Origin ajeno y `Sec-Fetch-Site` externo. No confiar en proxies que eliminan/reemplazan esas cabeceras; un proxy puede ocultar la procedencia de red, por eso la restricción de despliegue es obligatoria.
- El servidor accede directamente al mismo `EventStore` después de autenticar. No es un proxy HTTP, no acepta destinos arbitrarios y no reenvía `OBS_READ_KEY`. No hay clave en HTML, JavaScript, respuestas JSON, parámetros de URL o almacenamiento web. La contraseña local se introduce en el diálogo del navegador, no en un formulario JavaScript.
- HTTP Basic transmite una credencial, no cifra el transporte. En este hito solo se admite HTTP sobre loopback en una máquina confiable. Otros usuarios/procesos privilegiados del host quedan fuera de este aislamiento. Antes de cualquier acceso remoto se requiere un diseño de autenticación y HTTPS, no relajar estos checks.
- El navegador conserva las credenciales Basic en su contexto. No hay logout fiable en JavaScript: cerrar todas las ventanas del contexto privado y rotar la contraseña/reiniciar revoca el acceso anterior. No usar credenciales en URLs. La autenticación del dashboard **no** protege los endpoints de negocio existentes.
- HTML protegido fuera de `/static`; CSS y módulos públicos no contienen datos ni secretos. Las respuestas del dashboard incluyen `Cache-Control: no-store`, CSP sin scripts inline ni terceros, `frame-ancestors 'none'`, `X-Frame-Options: DENY`, `nosniff` y `Referrer-Policy: no-referrer`. El dashboard no carga las fuentes remotas de las páginas heredadas.
- Contenido dinámico mediante `textContent`, nodos DOM y atributos SVG numéricos. No usa `innerHTML`, localStorage, cookies propias, HTML de eventos ni texto libre de incidentes. Todas las rutas de datos son GET; no hay escritura de incidentes, importación ni ejecución de agentes.

## Pantallas y uso

**Vista general.** Siete KPIs: solicitudes, solicitudes técnicamente exitosas, tasa de errores HTTP, media/p50/p95 HTTP y total de tokens observado. Cada tarjeta muestra unidades, período aplicado y denominador/cobertura. `null`, ausencia y valores no finitos se representan como **N/D**; cero solo representa un conteo observado o un cero reportado. Un error de lectura deja N/D, no contadores ficticios.

**Rendimiento.** Gráficos SVG propios, sin paquetes: media HTTP en 24 intervalos, duración media por componente, resultados de dominio, errores HTTP por intervalo, invocaciones/duración de herramientas y tokens reportados. Enfocar o pasar sobre las barras muestra valores y muestras. Cada gráfico ofrece una tabla expandible con los valores exactos; el selector de herramientas cambia la medida. No se interpolan intervalos sin muestras. La media por intervalo reutiliza `latency()` del Hito 3. Frecuencia significa **conteo de errores por intervalo**, no errores por segundo.

**Ejecuciones.** Tabla de eventos, no una fila por solicitud: incluye traza, fecha UTC de fin/log, modo, componente/operación, estado, duración y categoría de error. Filtros explícitos de modo/período/componente/operación/estado, aplicados al pulsar el botón. Los valores elegidos pero no aplicados no cambian el contexto que se muestra sobre los KPIs.

**Explorador.** Seleccionar un Trace ID o introducirlo consulta solo esa traza en el modo aplicado, sobre todo el período retenido y sin los filtros de componente/operación/estado. Jerarquía por `span_id`/`parent_span_id`, orden entre hermanos por inicio y secuencia, duración monotónica, error, resultado y logs correlacionados. El ancho temporal corresponde a duración; la posición relativa usa UTC y puede verse afectada por ajustes del reloj. Herramientas ordenadas por inicio observado; no pretende inferir causalidad entre operaciones concurrentes.

Las trazas siempre muestran que su **cobertura es parcial o no verificable**: no se puede detectar la pérdida de todos los hijos mirando solo al padre. Se informa específicamente de padres ausentes en los eventos cargados, ausencia de raíz HTTP, ciclos, páginas pendientes y límite visual. No se inventan nodos ni se reconstruyen eventos eliminados. Logs no se cuentan como spans duplicados.

**Calidad.** Precisión y consistencia permanecen **N/D** usando el contrato `evaluated_benchmarks/not_evaluated`, con indicación de falta de muestras. No se derivan de errores, HTTP 200, citas ni tokens. No se generaron benchmarks.

Modo visible en toda consulta: `offline`, `mock`, `live`, `unknown`, `offline_mock`. Mock muestra **DATOS SINTÉTICOS / DOBLES**; las particiones heredadas no se combinan ni se reclasifican. Una etiqueta live no certifica por sí sola uso real: depende del operador, como en Hito 3.

## Contratos locales

Todas las rutas siguientes requieren el control local y HTTP Basic. El frontend no invoca `/api/observability/*`; esos endpoints y su `X-Observability-Key` se mantienen sin cambios.

| GET | Respuesta y parámetros |
|---|---|
| `/dashboard` | HTML protegido, sin interpolación de secretos |
| `/dashboard/api/options` | Allowlist real de componentes/operaciones y modos |
| `/dashboard/api/summary` | Filtros Hito 3; `since` y `until` obligatorios, intervalo >0 y ≤7 días. Retorna `metrics` idénticas a Hito 3, `series` con 24 intervalos, período, fecha de generación, TTL y estado de captura |
| `/dashboard/api/events` | Filtros Hito 3, `limit=50` (1–100), `after=0`; retorna contrato Hito 3 `items/next_after` |
| `/dashboard/api/quality` | `execution_mode` obligatorio; mismo contrato de calidad del Hito 3 |

Series: `since`, `until`, `requests`, `errors`, `mean_ms`; intervalos `[since,until)` por fecha de finalización HTTP. Sin muestras → requests/errors=0 y mean_ms=null. Agregados centrales reutilizan `aggregate_events()` extraído literalmente de `EventStore.metrics`; no cambian fórmulas ni denominadores. Una prueba compara la respuesta dashboard con el store usando los mismos filtros.

Errores: 401 sin credenciales válidas; 403 acceso no local/origen incorrecto; 404 dashboard desactivado; 413 selección demasiado grande; 422 filtros inválidos sin eco de valores; 503 configuración/almacén inaccesible. POST de datos no soportado (405).

## Coste, paginación y consistencia

- Resumen: **una lectura acotada**, `LIMIT 50001`; más de 50000 filas devuelve 413 sin agregados parciales. Máximo 7 días. Reutiliza filtros e índices SQLite existentes. Los agregados y series del resumen salen del mismo conjunto leído.
- Caché por proceso de **10 segundos y hasta 8 selecciones**, claves con todos los filtros; lock para no repetir cómputos concurrentes sobre el mismo lector. La fecha de generación se muestra. Puede conservar información hasta 10 segundos después de su expiración en almacenamiento; no es captura en tiempo real.
- Sin polling automático. Un arranque consulta opciones una vez, y cada aplicación de filtros realiza resumen + primera página + calidad. Cambiar medida de herramientas es local, no repite consultas.
- Tabla: 50 eventos por petición, secuencia de ingestión ascendente; historial de cursores para anterior/siguiente. Solo conserva la página actual, no descarga el almacén completo. Un fallo de página conserva la última página correcta para reintentar.
- Traza: páginas manuales de 100 eventos; deduplicación por event_id, máximo 1000 eventos en memoria. No carga páginas automáticamente; el límite y páginas pendientes son visibles.
- AbortController y contadores de generación impiden que respuestas de filtros/trazas anteriores sobrescriban la selección actual.
- Como en Hito 3, no hay snapshot entre páginas. Dentro de un conjunto estable no se omiten ni duplican filas; nuevas inserciones y retención pueden cambiar resultados entre peticiones. Resumen y tabla pueden observar instantes diferentes. Los percentiles exactos siguen ordenando muestras en memoria; no se afirma rendimiento productivo medido.

## Pruebas y validación

```bash
.venv/bin/python scripts/run_tests_offline.py --uvloop
.venv/bin/python scripts/run_tests_offline.py --uvloop --observe
.venv/bin/python scripts/run_tests_offline.py --uvloop tests/test_dashboard.py
node tests/dashboard_frontend.test.mjs
node --check app/ui/static/observability/dashboard.mjs
node --check app/ui/static/observability/charts.mjs
```

Omitir `--uvloop` en entornos donde asyncio funciona sin la limitación de socketpair. Node.js se usa solo para probar JavaScript, no para servir la aplicación. Si no está instalado, pytest marca esa comprobación como omitida; las corridas de esta entrega sí la ejecutaron. Los seis tests Node cubren N/D/cero, jerarquía, padres faltantes, ciclos, logs, deduplicación/límite y cursores.

Los tests Python usan eventos **sintéticos** y ASGI sin red. Cubren cada ruta protegida, credenciales incorrectas, desactivación, peer/Host/Origin/proxy, API Hito 3 todavía protegida, ausencia de secretos, CSP, vacíos, calidad, fórmulas, modos, paginación estable, fechas/coste, caché/expiración, lectura sin mutaciones y assets sin HTML protegido. No son benchmarks ni evidencia live.

**Limitación visual pendiente:** no se obtuvo una ejecución de navegador verificable ni capturas. La herramienta externa no pudo acceder al servidor local. La revisión automática rechazó enviar el código y los fixtures a su proceso externo de Playwright por riesgo de exportación. Se intentó una alternativa local sin exportación: herramientas temporales instaladas exclusivamente desde wheels de caché en `/tmp/knowledgeflow-dashboard-browser`; Chrome local falló por `setsockopt: Operation not permitted` del sandbox. No se cambiaron dependencias de aplicación. Se verificaron contratos y sintaxis, pero quedan pendientes la inspección visual y la interacción integral en navegador real.

Comprobación manual local recomendada: ventana de escritorio y móvil (390 px), tabulación sobre filtros/barras, modo vacío y modo con datos retenidos, siguiente/anterior, traza con padre ausente, fallo temporal del servidor y recuperación. Nunca rellenar la UI con datos reales o sintéticos sin declarar su procedencia.

## Inventario del Hito 4

Nuevos:

- `app/api/dashboard_routes.py`: acceso local y rutas GET.
- `app/observability/dashboard.py`: lectura acotada, series y caché.
- `app/ui/observability.html`: página protegida fuera de static.
- `app/ui/static/observability/dashboard.css`: diseño responsive aislado.
- `app/ui/static/observability/dashboard.mjs`: filtros, estados, consultas, tabla y explorador.
- `app/ui/static/observability/charts.mjs`: SVG accesibles y tablas de valores.
- `app/ui/static/observability/core.mjs`: formato, jerarquía y cursores testeables.
- `tests/test_dashboard.py`, `tests/dashboard_frontend.test.mjs`.
- `docs/14-dashboard-web.md`, `docs/superpowers/plans/2026-11-13-dashboard.md`.

Modificados:

- `app/main.py`: registra router local.
- `app/core/config.py`: flag y contraseña independientes, validación.
- `app/observability/store.py`: extrae la agregación existente a función reutilizable, sin cambiar resultados.
- `app/ui/static/index.html`, `app/ui/static/agent.html`: enlaces de navegación.
- `.env.example`, `README.md`, `docs/02-arquitectura-dashboard.md`: configuración y estado.

Se preservan los cambios previos de Hitos 2 y 3. Sin modificaciones a agentes/herramientas, sin nuevas dependencias runtime, sin push, merge, despliegue ni informe académico.

Referencia de autenticación consultada vía Context7: [HTTP Basic en FastAPI](https://fastapi.tiangolo.com/advanced/security/http-basic-auth/). La política del entorno impide Context7 CLI fuera del sandbox; se utilizó el conector disponible.

### Evidencia ejecutada — 2026-11-13

Intérprete reutilizado: `/tmp/knowledgeflow-obs-venv/bin/python`, Python 3.12.3; Node.js 24.21.0 para comprobaciones frontend. No cambió `requirements.txt`.

| Comprobación | Resultado real |
|---|---|
| Línea base Hito 3 antes de los cambios | 313 passed, 20 warnings in 8.15s |
| Suite final, observabilidad desactivada | **341 passed, 20 warnings in 9.07s** |
| Suite final, `--observe` | **341 passed, 20 warnings in 9.44s** |
| Intentos de red de cada suite offline | **0** |
| Tests específicos dashboard Python | **28 passed** (incluyen ejecución de Node) |
| Tests de comportamiento JavaScript | **6 passed**, sin omitidos |
| Sintaxis `dashboard.mjs` / `charts.mjs` | Correcta |
| `git diff --check` | Sin errores |
| Navegador / capturas | **No verificado**, restricciones detalladas arriba |

Los 20 warnings heredados son de deprecación FastAPI/Starlette y CrewAI. Los tiempos son duración de tests, no métricas productivas. Los seis tests JavaScript se ejecutan dentro de una prueba Python: no sumarlos otra vez a 341. El dataset de cada test está identificado como sintético.

Revisión independiente de código sin hallazgos importantes; se corrigió la recuperación de paginación tras error temporal conservando la página previa. Esa recuperación se revisó en código; la interacción integral sigue cubierta por la limitación de navegador ya declarada.

Artefactos temporales: `/tmp/dashboard-baseline.log`, `/tmp/dashboard-off.log`, `/tmp/dashboard-off.xml`, `/tmp/dashboard-on.log`, `/tmp/dashboard-on.xml`. Las pruebas visuales fallidas y los fixtures temporales no se presentan como evidencia de una UI validada. Servidores temporales de comprobación detenidos. Cambios locales conservados en `feat/observability`, sin commits automáticos, push ni merge.
