# Roadmap de desarrollo — KnowledgeFlow AgentOps

**Última actualización:** 14 de noviembre de 2026  
**Asignatura:** Ingeniería de Soluciones con IA · EP3, con preparación posterior para la EFT  
**Proyecto:** KnowledgeFlow AgentOps · caso NovaTech SpA  
**Dashboard elegido:** interfaz propia con FastAPI + HTML/CSS/JavaScript; **sin Streamlit**.

> **Avance EP3 estimado: 70 %** (70 puntos completados de 100 ponderados). Es una estimación de hitos técnicos, **no representa porcentaje de calificación ni avance de la EFT**. M1–M4 se consideran cerrados **según informes y pruebas locales proporcionados por el equipo**; todavía no se han verificado independientemente ni integrado en `main` los cambios funcionales. Las capturas y pruebas E2E de M4 utilizaron un almacén temporal aislado con datos sintéticos etiquetados como `mock`, no un benchmark real.

## 1. Cálculo de avance

Los pesos son una **estimación de gestión del proyecto**, no los porcentajes de la rúbrica académica.

| Hito | Entregable y alcance | Peso EP3 | Avance del hito | Aporte al total | Estado y evidencia |
|:---|:---|---:|---:|---:|:---|
| **M0** | Migración de EP1/EP2 y base reproducible | 10 % | 100 % | **10 %** | Completado en GitHub; 141/141 blobs cotejados por SHA |
| **M1** | Auditoría técnica y regresión offline | 10 % | 100 % | **10 %** | Completado según reporte local; auditoría y 242 tests base reportados |
| **M2** | Logging JSON, spans, correlación, latencias y sanitización | 15 % | 100 % | **15 %** | Completado según reporte local; 275 pruebas totales reportadas |
| **M3** | SQLite, agregación de métricas, filtros, retención y API GET protegida | 15 % | 100 % | **15 %** | Completado según reporte local; 313 pruebas totales reportadas |
| **M4** | Dashboard web propio y explorador de trazas | 20 % | 100 % | **20 %** | Completado según auditoría local: navegador Playwright (desktop/tablet/móvil), 341 pruebas Python y 6 JS; aún no subido a `main` |
| **M5** | Benchmark evaluado: precisión, consistencia, errores, escenarios variados | 15 % | 0 % | **0 %** | Pendiente; calidad sigue N/D |
| **M6** | Seguridad integral, pruebas adversariales y validación de integración | 10 % | 0 % | **0 %** | Pendiente; controles parciales de M2/M3 no equivalen a cierre de seguridad |
| **M7** | Evidencias, informe EP3 y presentación | 5 % | 0 % | **0 %** | Pendiente |
| **Total** | **Evaluación Parcial N.º 3** | **100 %** | — | **70 %** | **Estimación basada en reportes del equipo** |

**Fórmula:** `avance = suma(peso_hito × fracción_de_cierre)`. En el estado actual: `10 + 10 + 15 + 15 + 20 + 0 + 0 + 0 = 70 %`.

**Estado del repositorio remoto vs. implementación local:**

- **Verificado remotamente:** M0 (código y documentación de EP2 copiados, sin transferir historial completo).
- **Reportado como desarrollado localmente:** M1, M2, M3 y M4 en `feat/observability`. La rama local contiene también `docs/14-dashboard-web.md` y `docs/15-validacion-visual.md` según el informe compartido, además de las especificaciones, pruebas y reportes anteriores. **Este código/documentación local no está en la rama remota `main` al actualizar este roadmap**.
- **Pendiente de verificación independiente:** revisar el código/commits de M1–M4 y reproducir tests en CI o entorno limpio después de publicar la rama. No atribuir automáticamente estos reportes a `main`.
- **Ritmo de pruebas informado:** base 242 → observabilidad 275 → agregación 313 → dashboard 341 tests Python offline aprobados (OBS on/off) y 6 JS. Auditoría visual reportada con Playwright Chromium en 1440×900, 768×1024 y 390×844, sin desbordamiento horizontal; interacción con datos `mock` aislados y eliminados tras la prueba. Estas cifras proceden de reportes locales; no se realizaron ejecuciones de CI desde este documento.

## 2. Fases siguientes y criterios de cierre

### M4 — Dashboard web propio (20 %; completado según revisión local)

**Objetivo:** visualización accesible de los eventos almacenados, integrada a la aplicación existente.

- [x] Confirmar contratos reales de lectura y adaptar la UI según el módulo local de observabilidad (según pruebas reportadas).
- [x] Diseñar acceso local protegido desde servidor con HTTP Basic; `OBS_READ_KEY` no se entrega al navegador (según verificación E2E reportada).
- [x] Crear vista general de solicitudes, estados, tasa de errores, p50/p95, tiempos por componente y cobertura de tokens.
- [x] Crear gráficos que consumen agregados del almacén. La revisión E2E con datos poblados usó exclusivamente fixtures `mock` explícitos; **aún no hay mediciones reales de benchmark**.
- [x] Crear tabla filtrable y paginada por cursor `limit/after`, con modo de ejecución visible.
- [x] Permitir explorar un `trace_id`: eventos, timeline y árbol de `span_id`/`parent_span_id`.
- [x] Señalar explícitamente las trazas truncadas por retención y los resultados **N/D**.
- [x] Reportadas 341 pruebas Python en ambos modos, 6 JS y pruebas reales Playwright de autenticación, filtros, gráficos, paginación, traza completa/parcial y viewports.
- [x] Documentación local reportada en `docs/14-dashboard-web.md` y `docs/15-validacion-visual.md`; capturas locales en `.playwright-mcp/`, **no publicadas en GitHub**.

**Cierre reportado:** interfaz local navegable, protegida y validada con Playwright; mejora UX/UI en grillas, navegación móvil, contraste, scroll de tabla y ejes enteros. **Queda por publicar y verificar en remoto**. No afirmar operación productiva ni calidad evaluada.

### M5 — Benchmark experimental (15 %)

**Objetivo:** pasar de métricas operacionales a evidencia de **calidad** sobre el agente.

- [ ] Revisar/reutilizar `evaluation/dataset_verified.json` y construir datasets EP3 evaluables con etiquetas revisadas.
- [ ] Definir ground truth, criterios de corrección/equivalencia y muestras N por escenario.
- [ ] Medir tareas: consulta RAG interna y externa, abstención, creación/búsqueda/nota de incidentes, continuidad multi-turno, casos incompletos y fallas controladas.
- [ ] Medir **precisión/exactitud**, consistencia en repeticiones válidas, frecuencia de errores y latencia sin mezclar `offline`, `mock`, `live` o particiones heredadas.
- [ ] Registrar SHA, modelo, parámetros, dataset y `trace_id` de los ensayos.
- [ ] Si se autorizan pruebas `live`, limitar cuota y documentar el costo; no ejecutarlas por defecto.
- [ ] Poblar `/api/observability/quality` solo desde resultados efectivamente evaluados.
- [ ] Generar tablas reproducibles y casos fallidos sin fabricar métricas.

**Cierre:** benchmark reproducible, con muestras declaradas, calidad evaluada y evidencia asociada.

### M6 — Seguridad, robustez y validación integral (10 %)

- [ ] Revisar la autenticación/autorización de `/api/agent` y `/api/observability/*`; la API key de telemetría no resuelve por sí misma toda la seguridad del agente.
- [ ] Verificar redacción de secretos, datos personales, prompts sensibles, contexto de memoria y contenido de incidentes.
- [ ] Probar control de acceso, sanitización de excepciones, límites de consulta, casos de prompt injection y prevención de XSS.
- [ ] Evaluar impacto de escritura síncrona a SQLite sobre latencia (comparar OBS activado/desactivado).
- [ ] Documentar retención, rotación, truncamiento de trazas y uso de espacio adicional por journaling.
- [ ] Ejecutar regresión offline y documentar limitaciones; no afirmar garantías de producción sin pruebas.

**Cierre:** matriz de riesgos y pruebas de seguridad, sin fallos críticos abiertos para la demostración.

### M7 — Evidencia, informe y presentación EP3 (5 %)

- [ ] Consolidar capturas y gráficos verdaderos del dashboard.
- [ ] Preparar tabla de resultados y análisis de ejecución con datos verificables.
- [ ] Preparar informe de hasta **5 páginas**, según la pauta de EP3 consultada, con referencias APA.
- [ ] Registrar el uso de IA; las **justificaciones técnicas, conclusiones y reflexiones** deben redactarlas los estudiantes.
- [ ] Preparar demo y exposición grupal **10 minutos + 10 minutos de preguntas** según la pauta disponible.
- [ ] Comprobar la pauta y fecha aplicable con el docente antes de entregar por AVA y correo.

**Cierre:** todos los entregables reproducibles y disponibles para el evaluador.

## 3. Riesgos y bloqueos inmediatos

| Riesgo | Consecuencia | Acción de mitigación |
|---|---|---|
| M1–M4 siguen sin push/merge | `main` no representa el 70 % estimado | Revisar `git status`, realizar commit local, publicar rama y abrir PR sin sobrescribir trabajo |
| Clave de observabilidad expuesta al navegador | Lectura no autorizada de telemetría | Proteger por sesión/autorización en servidor, sin `X-Observability-Key` visible en cliente |
| Precisión y consistencia siguen `null` | Rubrica de calidad aún no demostrada | Diseñar y ejecutar benchmark evaluado con ground truth |
| Retención puede cortar una traza | Diagnósticos incompletos | Marcar traza parcial y documentar cobertura del período |
| SQLite síncrono y journaling | Posible latencia adicional/uso de disco | Medir overhead y espacio con dataset reproducible |
| Reportes de pruebas solo locales | Falta evidencia auditada en repositorio remoto | Publicar la rama y validar en entorno limpio o CI |
| Discrepancia de sigla EP3/EFT | Riesgo de aplicar instrucciones equivocadas | Confirmar con docente cuál pauta corresponde a EP3 |

## 4. Próximas acciones, en orden

1. **Punto de control Git:** proteger los cambios locales; commit en `feat/observability`, comparar con `origin/main` actualizado y publicar la rama con revisión. No mezclar este roadmap con las modificaciones funcionales sin revisar diffs.
2. **Comenzar M5:** preparar y validar dataset, ground truth, métricas de calidad, escenarios repetidos y pipeline de resultados reproducibles. No confundir datos `mock` de Playwright con evaluación de IA.
3. **Implementar M5:** benchmark y pruebas repetibles, distinguir datos sintéticos de datos reales.
4. **Cerrar M6 y M7:** seguridad, regresión, informe y presentación.

No se asignan fechas exactas porque el equipo no ha confirmado el calendario de entrega vigente.

## 5. Relación con la Evaluación Final Transversal (EFT)

La **EFT no está incluida en el 70 %**. Es una etapa posterior que aprovecha EP1 + EP2 + EP3; debe contar con una planificación y porcentaje independiente.

| Frente EFT | Entregable futuro |
|---|---|
| Integración | Mostrar RAG, agentes, herramientas, memoria, planificación, observabilidad y seguridad en una solución coherente |
| Notebook/Colab | Demostración reproducible del código solicitado por la pauta EFT |
| Informe | PDF académico con arquitectura, datos y resultados reales |
| Defensa individual | Hasta 10 minutos por estudiante con prototipo y dashboard |
| Ética | Declaración de IA; reflexión y conclusiones redactadas por el propio estudiante |

---

## 6. Mantenimiento de progreso

Actualizar este archivo **solo con evidencia**. Para cada cambio de estado, registrar rama/commit, comando de pruebas, muestras, capturas y documento de respaldo.

- **13-11-2026:** progreso inicial fijado en **50 % EP3**, sumando M0–M3. M1–M3 basados en reportes locales; M4–M7 pendientes.
- **14-11-2026:** **70 % EP3** estimado al cerrar M4 según reporte de auditoría visual con Chromium/Playwright y pruebas Python/JS. M5–M7 siguen pendientes; implementaciones M1–M4 continúan locales sin push/merge al actualizar. Evidencia visual con `mock` aislado; dataset operativo retenido vacío.
