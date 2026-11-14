# Guía rápida: iniciar y demostrar el dashboard de observabilidad

**Proyecto:** KnowledgeFlow AgentOps (EP3)  
**Interfaz:** FastAPI + HTML/CSS/JavaScript, sin Streamlit  
**URL:** http://127.0.0.1:8000/dashboard  
**Última actualización:** 14 de noviembre de 2026

> **Estado del código:** el dashboard fue implementado y comprobado visualmente por el equipo **en su entorno local**, sobre `feat/observability`. Al publicar esta guía, la rama remota `main` todavía **no contenía** `app/api/dashboard_routes.py` ni los archivos del dashboard. **Por tanto, estos comandos requieren la copia local actualizada o una integración futura de esa rama.** La guía no significa que el código de M4 se haya subido a GitHub.

## 1. Requisitos

- Abrir una terminal Linux Mint en la carpeta **que contiene `app/`, `requirements.txt` y `.venv/`**.
- Haber instalado dependencias y contar con los archivos locales del Hito 4, en particular `app/api/dashboard_routes.py` y `app/ui/static/observability/`.
- Preparar una **contraseña propia de al menos 32 caracteres ASCII**, distinta de `OBS_READ_KEY`. No copiar contraseñas de documentación, chats o repositorios públicos.
- Utilizar la URL literal `127.0.0.1`, **no `localhost`**. El servidor debe escuchar solamente en loopback.

## 2. Iniciar el panel en modo lectura, sin capturar nuevos eventos

Desde la terminal:

```bash
cd ~/proyectos/KnowledgeFlow-AgentOps/KnowledgeFlow-AgentOps
source .venv/bin/activate

# Introducir una contraseña privada; el texto no se muestra al escribir.
read -r -s -p "Contraseña local del dashboard (mínimo 32 caracteres ASCII): " OBS_DASHBOARD_PASSWORD
echo
export OBS_DASHBOARD_PASSWORD

# Dashboard activo; store legible; captura desactivada.
OBS_DASHBOARD_ENABLED=true \
OBS_STORE_ENABLED=true \
OBS_ENABLED=false \
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

> **Diferencia importante:** `OBS_DASHBOARD_PASSWORD` es el nombre exacto tanto para `read` como para `export`. Algunas versiones locales de `docs/14-dashboard-web.md` contienen un ejemplo con el nombre incorrecto `OBSDASHBOARD_PASSWORD`; no repetir ese error.

Si el entorno virtual aún no existe:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

La instalación de dependencias puede requerir red. El **inicio en modo lectura no invoca Gemini ni ejecuta consultas**.

## 3. Abrir el dashboard

Navegar a **http://127.0.0.1:8000/dashboard** (o seleccionar **Observabilidad** desde la interfaz principal).

Se solicitará autenticación HTTP Basic:

| Campo | Valor |
|---|---|
| Usuario | `observer` |
| Contraseña | La introducida en el paso 2 |

El navegador puede recordar las credenciales mientras permanezca abierto. No ponerlas en URLs ni en archivos del repositorio.

**Pantallas disponibles** en la implementación local reportada:

1. **Vista general:** solicitudes, éxitos, tasa de errores, latencia media/p50/p95, tokens observados y cobertura.
2. **Rendimiento:** latencia HTTP en el tiempo, latencias por componente, resultados, errores y uso de herramientas.
3. **Ejecuciones y eventos:** tabla filtrable con paginación `limit/after`.
4. **Explorador de trazas:** búsqueda por `trace_id`, jerarquía de spans, secuencia y advertencias de trazas parciales.
5. **Calidad del agente:** precisión y consistencia, mostradas como **N/D** mientras no haya benchmarks evaluados.

## 4. Por qué inicialmente no aparecen gráficos

Con el comando del paso 2, `OBS_ENABLED=false`; esto **permite leer el historial**, pero **no captura eventos nuevos**. Si la base SQLite todavía no tiene eventos para el período y el modo elegidos, verás `0 solicitudes`, `Sin eventos retenidos` y gráficos **N/D**. Es un estado esperado, **no un fallo del frontend**.

El selector **Modo de ejecución** (por ejemplo `offline`, `mock`, `live`) y el **Período** filtran todos los indicadores. No confundir ausencia de muestras con calidad, precisión o consistencia cero.

### Capturar nuevos eventos de forma explícita

Detener FastAPI con `Ctrl+C` y volver a iniciarlo **desde la misma terminal**, conservando `OBS_DASHBOARD_PASSWORD`:

```bash
OBS_DASHBOARD_ENABLED=true \
OBS_STORE_ENABLED=true \
OBS_ENABLED=true \
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Ahora se instrumentarán las **ejecuciones nuevas** de los flujos habilitados. La captura **no es retroactiva**. Abrir el dashboard por sí solo no ejecuta agentes.

- Para una demostración **sin consumo de API**, usar únicamente ejecuciones offline propias, instrumentadas y persistidas en el store del entorno actual; verificar el modo y la ruta de almacenamiento en `docs/12-observabilidad.md` y `docs/13-agregacion-metricas.md`. Las pruebas automatizadas pueden utilizar SQLite temporal: **no asumir** que llenan el dashboard.
- Las consultas del agente/RAG que utilizan **Gemini real pueden consumir cuota**. Ejecutarlas solo con autorización y configuración adecuada; no se activan automáticamente al abrir el dashboard.
- Después de generar ejecuciones, volver a `/dashboard`, seleccionar el **modo** de las ejecuciones registradas, ampliar el **período** si hace falta y pulsar **Aplicar y actualizar**.
- **Calidad** seguirá en `N/D` hasta que se construya e incorpore el benchmark validado del Hito M5. No fabricar resultados para llenar esta sección.

### Distinguir dos tipos de datos

- **Telemetría operacional:** solicitudes, resultados, latencias, herramientas y trazas.
- **Calidad evaluada:** precisión/consistencia basadas en dataset, ground truth y repeticiones; **no** se calcula a partir de la ausencia de errores HTTP.

## 5. Guion breve para mostrarlo en clase (2–3 minutos dentro de la exposición)

1. **Contexto:** explicar que EP1 resuelve la consulta con RAG, EP2 añade el agente con memoria y herramientas, y EP3 aporta observabilidad.
2. **Navegación:** entrar desde la aplicación KnowledgeFlow al enlace **Observabilidad**.
3. **Vista general:** mostrar el período, modo, cobertura y las métricas disponibles; aclarar que **N/D** significa que falta evidencia suficiente.
4. **Rendimiento:** mostrar la división de latencias, errores y uso de herramientas. Si el almacén está vacío, explicar que no hay muestras retenidas; no afirmar mejoras cuantitativas.
5. **Ejecuciones:** seleccionar un `trace_id` real si existe y abrir el **Explorador de trazas** para explicar `trace_id`, `span_id` y `parent_span_id`.
6. **Seguridad:** indicar que el dashboard es local, de solo lectura y solicita una contraseña independiente; `OBS_READ_KEY` no se envía al navegador.
7. **Calidad:** diferenciar indicadores operacionales de la precisión y consistencia del benchmark, que todavía está pendiente de evaluación.
8. **Cierre:** describir brevemente los próximos hitos: benchmarking, seguridad integral e informe EP3. El diagnóstico/justificación académica debe ser redactado y defendido por el equipo.

**Antes de la presentación:** practicar el recorrido con datos verificables y sin internet si se utilizarán ejecuciones offline; verificar visualmente resolución y filtros; preparar capturas reales y sanitizadas solo si la interfaz se ha comprobado en navegador.

## 6. Resolución de problemas

| Síntoma | Causa probable | Qué hacer |
|---|---|---|
| `{"detail":"Dashboard disabled"}` (404) | `OBS_DASHBOARD_ENABLED=false` | Reiniciar con `OBS_DASHBOARD_ENABLED=true`. |
| 401 o ventana de contraseña repetida | Credenciales incorrectas | Usuario `observer`; introducir exactamente la contraseña definida para el proceso. |
| 403 | Acceso no local, nombre Host distinto o cabeceras de proxy/origen rechazadas | Usar `http://127.0.0.1:8000/dashboard` desde el propio equipo, sin túnel/proxy. |
| 503 | Contraseña ausente/inválida o almacén no disponible | Verificar configuración privada, longitud ASCII y acceso al store. |
| Abre el formulario de «Consulta de conocimiento» | Estás en la portada `/` | Abrir **`/dashboard`** o usar el enlace **Observabilidad**. |
| Dashboard vacío, gráficos N/D | Captura desactivada, modo/período incorrecto o base nueva | Verificar `OBS_ENABLED`, generar ejecuciones autorizadas y filtrar por su modo/período. |
| `/dashboard` no existe en otro clon | Se inició `main` sin los cambios locales de Hito 4 | Comprobar que la rama/copia utilizada contenga `app/api/dashboard_routes.py`. |
| Se solicitan credenciales tras reinicio | La contraseña no fue persistida en el entorno | Volver a introducirla con `read -r -s` y exportarla; no guardar contraseñas en Git. |

## 7. Seguridad y alcance

- Solo demo local; no ejecutar con `--host 0.0.0.0`.
- No publicar `.env`, contraseña del dashboard, `OBS_READ_KEY`, cookies, datos personales, logs sensibles ni contenido de incidentes.
- Los endpoints administrativos `/api/observability/*` usan **`X-Observability-Key`** de forma independiente. **No hace falta** configurarla para el dashboard local y nunca debe insertarse en JavaScript.
- El dashboard es de **solo lectura**; no crea incidentes ni ejecuta agentes.
- **Auditoría visual completada según reporte local del equipo (14-11-2026):** 341 pruebas Python offline en ambos modos OBS, 6 pruebas JavaScript, y revisión real en Chromium con Playwright de autenticación, navegación, tooltips, filtros, paginación, trazas y viewports **1440×900, 768×1024, 390×844** sin desbordamiento horizontal. Los datos poblados procedían de **SQLite temporal `mock`**, eliminada después; esto **no** significa que haya evidencia de calidad real del agente. Código, informe `docs/15-validacion-visual.md` y capturas permanecen locales y **no están aún en `main`**. Auditoría/ejecuciones no reproducidas independientemente por quien escribe esta guía.
- Documentación técnica de la rama local: `docs/12-observabilidad.md`, `docs/13-agregacion-metricas.md` y `docs/14-dashboard-web.md`.

---

**Nota de trazabilidad:** esta guía es documentación operativa. No modifica código funcional ni importa automáticamente la rama local `feat/observability` a GitHub.
