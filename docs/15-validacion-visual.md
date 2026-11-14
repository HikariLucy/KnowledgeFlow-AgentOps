# Validación visual y mejoras UX/UI del dashboard (`/dashboard`)

Documento de verificación en navegador real (Chromium mediante Playwright MCP) sobre la consola local de observabilidad de KnowledgeFlow AgentOps.

## Alcance y entorno de validación

- **URL validada:** `http://127.0.0.1:8000/dashboard` (almacén local vacío en `data/observability/events.sqlite3`) y servidor temporal aislado en `http://127.0.0.1:8001/dashboard` con base SQLite temporal (`/tmp/kf-visual-audit.sqlite3`, eliminada al finalizar) poblada exclusivamente con **98 eventos sintéticos en modo `mock`** para inspeccionar gráficos, paginación y trazas sin mezclar con telemetría real.
- **Viewports probados:** Escritorio (`1440×900`), Tablet (`768×1024`) y Móvil (`390×844`).
- **Seguridad preservada:** Autenticación HTTP Basic (`observer` + contraseña local ≥ 32 caracteres en variable de entorno temporal), sin exposición de `OBS_READ_KEY`, sin llamadas reales a Gemini, sin `innerHTML`, sin dependencias externas ni cambios en la lógica de negocio del agente.

## 1. Diagnóstico de problemas visuales encontrados

Durante la inspección inicial en Chromium se detectaron los siguientes defectos:

1. **Enlace de salto `.skip-link` visible sin foco:** Con `position: fixed; top: -80px`, el enlace `"Ir al contenido"` aparecía superpuesto en capturas de página completa y desplazamientos en móvil/tablet.
2. **Navegación móvil/tablet desalineada:** En `≤ 800px`, `.workspace-nav` usaba `float: right; margin-top: -52px`, provocando superposición y recorte de los enlaces `Consulta RAG` y `Agente` en `390px`.
3. **Asimetría en grillas de KPIs y gráficos:**
   - 7 tarjetas KPI en grilla de 4 columnas (`1440px`) o 2 columnas (`≤ 800px`) dejaban un hueco vacío al final.
   - 5 gráficos secundarios bajo `Latencia HTTP en el tiempo` en grilla de 2 columnas dejaban un hueco vacío junto a `Tokens reportados`.
4. **Eje Y decimal en conteo de errores:** En `Frecuencia de errores HTTP`, cuando el máximo era `1`, el eje Y mostraba `0, 0,25, 0,5, 0,75, 1` errores.
5. **Tabla de eventos sin altura acotada:** Con 50 filas por página, la sección `03 / Ejecuciones y eventos` superaba los `3.000 px` de altura, dificultando el acceso rápido al Explorador de trazas.
6. **Badge de logs de error sin estilo semántico:** En `dashboard.mjs`, los eventos `log` con `level: "ERROR"` no tenían `event.status`, por lo que recibían la clase `state ` (gris) en lugar de `state error` (rojo).
7. **Contraste de textos secundarios y estado `N/D`:** Textos auxiliares (`#74827f`, `#82918e`) tenían contraste bajo sobre `#fffefa`, y el botón `#trace-more` permanecía visible aunque no hubiera traza ni páginas pendientes.

## 2. Mejoras implementadas

- **`app/ui/observability.html`:**
  - `Frecuencia de errores HTTP` promovida a `chart-wide` para equilibrar la grilla (`2` series temporales de ancho completo + grilla `2×2` simétrica para componentes, resultados, herramientas y tokens).
  - Atributo `hidden` inicial en `#trace-more` para evitar ruido visual cuando no hay páginas pendientes.
- **`app/ui/static/observability/dashboard.css`:**
  - `.skip-link` oculta mediante `transform: translateY(-200%); opacity: 0; pointer-events: none` y revelada únicamente en `:focus-visible`.
  - Grilla KPI balanceada: en `4` columnas (`1151px–1599px`), la primera tarjeta (`Total de solicitudes`) ocupa `span 2` (`8` celdas exactas para `7` KPIs); en `≤ 1150px`, `2` columnas con primera tarjeta `1 / -1`; en `≥ 1600px`, `7` columnas en una fila.
  - Diferenciación visual `.kpi.kpi-na` para valores `N/D` frente a `0` observado.
  - Badge ámbar explícito en `.context-strip .synthetic` para `MOCK · DATOS SINTÉTICOS / DOBLES`.
  - `.table-scroll` acotada a `max-height: 460px` con encabezados `thead th` fijos (`position: sticky; top: 0`).
  - Cabecera responsive en `≤ 800px` con Flexbox (sin `float` ni márgenes negativos) y desplazamiento horizontal limpio para `.section-nav`.
  - Contraste reforzado en textos secundarios (`#4f6163`, `#5a6c6e`, `#b0c7cb` en sidebar oscuro) y estilos semánticos `.state.ok`, `.state.error`, `.state.cancelled`, `.state.info`.
- **`app/ui/static/observability/charts.mjs`:**
  - Soporte `integerAxis: true` para métricas de conteo entero (`errores`), evitando ticks fraccionarios (`0,25`).
  - Pista de fondo `.bar-track` en barras horizontales y truncado seguro de etiquetas largas con `<title>` completo.
- **`app/ui/static/observability/dashboard.mjs`:**
  - Normalización en minúsculas de `event.status || event.level` para aplicar correctamente `.state.error` a logs `ERROR`.
  - Gestión de `#trace-more.hidden` según `info.pending` y clase `notice` vs `notice warning` en `#trace-notice` según hallazgos reales de cobertura.

## 3. Verificación funcional y responsive en navegador

Comprobado mediante Playwright MCP tras los últimos cambios:

- **Autenticación (401):** Sin credenciales, `/dashboard` responde `401` (`net::ERR_INVALID_AUTH_CREDENTIALS`). Con credenciales HTTP Basic válidas (`observer`), carga la consola completa.
- **Navegación:** Flujo `/` → `/agent` → `/dashboard` operativo.
- **Estado vacío (`127.0.0.1:8000`):** Muestra `0` en conteos HTTP observados, `N/D` en latencias/tasa/tokens/calidad, gráficos con estado vacío explícito y aviso sin eventos retenidos.
- **Gráficos e interacción (`127.0.0.1:8001`, datos sintéticos `mock`):** Hover sobre barra temporal actualiza `.chart-tooltip`; cambio de selector `#tool-measure` (`Invocaciones` ↔ `Duración media · ms`) actualiza el gráfico localmente; eje de errores muestra enteros (`0`, `1`).
- **Filtros y paginación:** Selección de componente `tool` actualiza `#operation` (`append_incident_note`, `create_incident`, `search_incidents`, `search_knowledge`); aplicar filtro reduce la tabla a `1 eventos en esta página`; paginación `Siguiente →` (`48 eventos` en página 2) y `← Anterior` (`50 eventos` en página 1) verificadas.
- **Explorador de trazas:** Traza `a1b2...` renderiza jerarquía padre-hijo de 8 spans, barra temporal, detalles desplegables, `1 logs correlacionados` y secuencia de herramientas; traza `b2c3...` informa `1 spans con padre ausente entre los eventos cargados` y `No hay raíz HTTP entre los spans cargados`.
- **Error de validación:** Rango personalizado `> 7 días` muestra aviso `.notice.error` sin enviar petición inválida.
- **Responsive (`scrollWidth <= innerWidth`):** `desktopOverflow: false` (`1440×900`), `tabletOverflow: false` (`768×1024`), `mobileOverflow: false` (`390×844`).

## 4. Pruebas ejecutadas tras la edición final

| Comprobación | Resultado |
|---|---|
| `.venv/bin/python scripts/run_tests_offline.py --uvloop` | **341 passed, 20 warnings** (`OFFLINE_NETWORK_ATTEMPTS_BLOCKED=0`) |
| `.venv/bin/python scripts/run_tests_offline.py --uvloop --observe` | **341 passed, 20 warnings** (`OFFLINE_NETWORK_ATTEMPTS_BLOCKED=0`) |
| `node tests/dashboard_frontend.test.mjs` | **6 passed, 0 failed** |
| `node --check` (`dashboard.mjs`, `charts.mjs`, `core.mjs`) | Sin errores de sintaxis |
| `git diff --check` | Sin errores de formato |

## 5. Archivos modificados y creados

- Modificados:
  - `app/ui/observability.html`
  - `app/ui/static/observability/dashboard.css`
  - `app/ui/static/observability/dashboard.mjs`
  - `app/ui/static/observability/charts.mjs`
- Creados:
  - `docs/15-validacion-visual.md`

## 6. Limitaciones observadas

- Las páginas heredadas `/` y `/agent` conservan enlaces a Google Fonts (`fonts.googleapis.com` / `fonts.gstatic.com`), los cuales generan errores CORS en consola cuando se navega con cabecera `Authorization` compartida o en entornos sin acceso externo; `/dashboard` no carga fuentes remotas.
- La validación con datos poblados se realizó sobre eventos sintéticos explícitos en modo `mock` dentro de un archivo SQLite temporal (`/tmp/kf-visual-audit.sqlite3`, eliminado tras la auditoría), dado que `data/observability/events.sqlite3` no contenía eventos retenidos.
