# Roadmap de desarrollo — KnowledgeFlow AgentOps

**Última actualización:** 14 de noviembre de 2026  
**Asignatura:** Ingeniería de Soluciones con IA · EP3, con preparación posterior para la EFT  
**Proyecto:** KnowledgeFlow AgentOps · caso NovaTech SpA  
**Dashboard elegido:** interfaz propia con FastAPI + HTML/CSS/JavaScript; **sin Streamlit**.

> **Avance EP3:** **95 % de hitos ponderados completados** (M0–M6 = 95 puntos sobre 100) y **~90 % de preparación conservadora para la entrega**. Son estimaciones distintas: el **95 %** refleja el cierre técnico ponderado de M0–M6 en la rama `feat/observability` (con M5 limitado a evaluación **offline** y M6 validado en **alcance local**), mientras que el **~90 %** incorpora el margen pendiente de M7 que requiere trabajo humano exclusivo (redacción del informe académico de hasta 5 páginas y preparación de la presentación grupal). **No representa nota académica ni avance de la EFT.**

## 1. Cálculo de avance

Los pesos son una **estimación de gestión del proyecto**, no los porcentajes de la rúbrica académica.

| Hito | Entregable y alcance | Peso EP3 | Avance del hito | Aporte al total | Estado y evidencia |
|:---|:---|---:|---:|---:|:---|
| **M0** | Migración de EP1/EP2 y base reproducible | 10 % | 100 % | **10 %** | **Completado** en GitHub; 141/141 blobs cotejados por SHA (`docs/legacy/MIGRACION-EP2.md`) |
| **M1** | Auditoría técnica y regresión offline | 10 % | 100 % | **10 %** | **Completado** (`docs/10-auditoria-ep2.md`, `docs/11-plan-implementacion-ep3.md`) |
| **M2** | Logging JSON, spans, correlación, latencias y sanitización | 15 % | 100 % | **15 %** | **Completado** (`docs/12-observabilidad.md`) |
| **M3** | SQLite, agregación de métricas, filtros, retención y API GET protegida | 15 % | 100 % | **15 %** | **Completado** (`docs/13-agregacion-metricas.md`) |
| **M4** | Dashboard web propio, explorador de trazas y validación visual Playwright | 20 % | 100 % | **20 %** | **Completado** (`docs/14-dashboard-web.md`, `docs/15-validacion-visual.md`, `docs/08-guia-demostracion-dashboard.md`) |
| **M5** | Benchmark evaluado: precisión, consistencia, errores, escenarios variados | 15 % | 100 % (offline) | **15 %** | **Completado únicamente para evaluación offline** (`docs/16-benchmark-experimental.md`); **no representa rendimiento de Gemini real**; evaluación live pendiente |
| **M6** | Seguridad integral, pruebas adversariales y validación de integración | 10 % | 100 % (local) | **10 %** | **Completado para uso local** (`docs/17-auditoria-seguridad.md`); sin afirmar seguridad de producción |
| **M7** | Evidencias, informe EP3 y presentación | 5 % | Parcial | **0 %** (ponderado conservador) | **Parcialmente preparado**: evidencias (`docs/18-evidencias-ep3.md`), guion (`docs/19-guion-demostracion.md`) y checklist (`docs/20-checklist-entrega.md`) listos; **falta informe con autoría humana y presentación** |
| **Total** | **Evaluación Parcial N.º 3** | **100 %** | — | **95 %** (hitos) / **~90 %** (conservador) | M0–M6 cerrados en alcance offline/local; M7 pendiente de autoría humana y defensa |

**Fórmula ponderada de hitos:** `avance = suma(peso_hito × fracción_de_cierre)`. Con M0–M6 cerrados en su alcance técnico definido y M7 parcial sin cierre final: `10 + 10 + 15 + 15 + 20 + 15 + 10 + 0 = 95 %`. La estimación conservadora (~90 %) descuenta además el esfuerzo humano pendiente de redacción, revisión académica y ensayo de exposición.

**Estado del repositorio remoto vs. implementación:**

- **En `main`:** M0 (migración EP2) y documentación base (`README.md`, `docs/05-roadmap.md`, `docs/08-guia-demostracion-dashboard.md`).
- **En `feat/observability` (PR #1):** implementación completa y verificada offline de M1–M6 y base técnica de M7 (`docs/10-auditoria-ep2.md` a `docs/20-checklist-entrega.md`), validada mediante suites Python offline (con observabilidad activada y desactivada) y pruebas frontend JS.
- **Límite explícito de evaluación:** las pruebas de M5 corresponden a un runner determinista offline; **no sustituyen ni representan el desempeño de Gemini real** en entorno live.

## 2. Fases y criterios de cierre

### M4 — Dashboard web propio (20 %; completado)

**Objetivo:** visualización accesible de los eventos almacenados, integrada a la aplicación existente.

- [x] Confirmar contratos reales de lectura y adaptar la UI según el módulo de observabilidad.
- [x] Diseñar acceso local protegido desde servidor con HTTP Basic; `OBS_READ_KEY` no se entrega al navegador.
- [x] Crear vista general de solicitudes, estados, tasa de errores, p50/p95, tiempos por componente y cobertura de tokens.
- [x] Crear gráficos que consumen agregados del almacén.
- [x] Crear tabla filtrable y paginada por cursor `limit/after`, con modo de ejecución visible.
- [x] Permitir explorar un `trace_id`: eventos, timeline y árbol de `span_id`/`parent_span_id`.
- [x] Señalar explícitamente las trazas truncadas por retención y los resultados **N/D**.
- [x] Validación visual con Playwright en viewports desktop, tablet y móvil y pruebas unitarias frontend JS (`docs/14-dashboard-web.md`, `docs/15-validacion-visual.md`).

**Cierre:** interfaz local navegable, protegida y validada con Playwright. No implica operación productiva.

### M5 — Benchmark experimental (15 %; completado únicamente para evaluación offline)

**Objetivo:** pasar de métricas operacionales a evidencia reproducible de **calidad** sobre el agente.

- [x] Revisar y estructurar `evaluation/dataset_verified.json` con casos evaluables y ground truth explícito.
- [x] Definir criterios de corrección, recuperación RAG, uso de herramientas y repeticiones para consistencia.
- [x] Medir **exactitud de respuesta**, **precisión de recuperación RAG**, **consistencia**, frecuencia de errores y latencia en modo `offline` sin mezclar particiones (`docs/16-benchmark-experimental.md`).
- [x] Registrar metadatos de ejecución, dataset y `trace_id` de los ensayos.
- [x] Poblar `/api/observability/quality` únicamente desde resultados efectivamente evaluados en el almacén.
- [ ] Fase posterior opcional/autorizada: ejecutar evaluación `live` con Gemini controlando cuota y costo (no ejecutada ni incluida en el cierre offline).

**Cierre:** benchmark offline reproducible y verificado en código/pruebas. **Sus resultados no representan rendimiento de Gemini real.**

### M6 — Seguridad, robustez y validación integral (10 %; completado para uso local)

- [x] Revisar la autenticación/autorización de `/api/agent`, `/dashboard` y `/api/observability/*`.
- [x] Verificar redacción de secretos, prompts sensibles, contexto de memoria e incidentes.
- [x] Probar control de acceso, sanitización de excepciones, límites de consulta, casos de prompt injection y prevención de XSS.
- [x] Evaluar impacto de escritura a SQLite sobre latencia (comparación observabilidad activada vs. desactivada) y documentar retención/rotación.
- [x] Ejecutar regresión offline en ambos modos y documentar limitaciones explícitas en `docs/17-auditoria-seguridad.md`.

**Cierre:** matriz de riesgos y pruebas de seguridad para demostración y uso local, sin fallos críticos abiertos en ese alcance. **No constituye certificación ni garantía de seguridad en producción.**

### M7 — Evidencia, informe y presentación EP3 (5 %; parcialmente preparado)

- [x] Consolidar evidencias técnicas, métricas verificadas y guía de demostración (`docs/18-evidencias-ep3.md`, `docs/19-guion-demostracion.md`, `docs/20-checklist-entrega.md`).
- [ ] Redactar el informe académico final de hasta **5 páginas** con autoría humana del equipo, incluyendo justificaciones técnicas, conclusiones, reflexiones y referencias APA.
- [ ] Registrar la declaración formal de uso de herramientas de IA.
- [ ] Preparar y ensayar la demo y exposición grupal (**10 minutos + 10 minutos de preguntas** según la pauta disponible).
- [ ] Confirmar con el docente la sigla/pauta aplicable (ISY1010 vs. ISY0101) y fecha de entrega antes de enviar por AVA y correo.

**Cierre:** todos los entregables reproducibles, redactados por el equipo y verificados según `docs/20-checklist-entrega.md`.

## 3. Riesgos y bloqueos pendientes

| Riesgo | Consecuencia | Acción de mitigación |
|---|---|---|
| PR #1 (`feat/observability` → `main`) pendiente de revisión/merge | `main` aún no integra M1–M7 hasta aprobar el PR | Resolver conflictos en `README.md` y `docs/05-roadmap.md`, validar pruebas y revisar PR #1 antes de hacer merge |
| Benchmark M5 ejecutado solo en modo offline | No refleja exactitud ni latencia real de Gemini en producción | Declararlo explícitamente en informe/defensa; ejecutar muestra live acotada solo si el equipo y docente lo autorizan |
| Alcance local de seguridad M6 | Controles validados para demo local, no para exposición pública en Internet | Mantener despliegue local o detrás de controles adicionales si alguna vez se expone externamente |
| Falta informe humano y ensayo de presentación (M7) | Entrega EP3 incompleta aunque el código esté listo | Redactar informe máx. 5 páginas con autoría humana y ensayar guion de 10 minutos |
| Discrepancia de sigla EP3/EFT (`ISY1010` vs. `ISY0101`) | Riesgo de aplicar formato o rúbrica equivocada | Confirmar con el docente cuál pauta corresponde a EP3 |

## 4. Próximas acciones, en orden

1. **Integración Git:** completar la fusión de `origin/main` en `feat/observability`, validar todas las suites offline y publicar para revisión de PR #1.
2. **Informe EP3 (autoría humana):** usar `docs/18-evidencias-ep3.md` como insumo técnico para redactar el documento de hasta 5 páginas con conclusiones y justificaciones propias del equipo.
3. **Preparación de demo y defensa:** ensayar el flujo completo con `docs/19-guion-demostracion.md` y `docs/08-guia-demostracion-dashboard.md`, verificando el checklist en `docs/20-checklist-entrega.md`.
4. **Confirmación académica:** validar con el docente la sigla vigente (`ISY1010` vs. `ISY0101`) y las condiciones de entrega.

## 5. Relación con la Evaluación Final Transversal (EFT)

La **EFT no está incluida en el avance EP3 (95 % ponderado / ~90 % conservador)**. Es una etapa posterior e independiente que reutilizará EP1 + EP2 + EP3.

| Frente EFT | Entregable futuro |
|---|---|
| Integración | Mostrar RAG, agentes, herramientas, memoria, planificación, observabilidad y seguridad en una solución coherente |
| Notebook/Colab | Demostración reproducible del código solicitado por la pauta EFT |
| Informe | PDF académico con arquitectura, datos y resultados reales |
| Defensa individual | Hasta 10 minutos por estudiante con prototipo y dashboard |
| Ética | Declaración de IA; reflexión y conclusiones redactadas por el propio estudiante |

## 6. Regla de ejecución y mantenimiento de progreso

- Cada cambio de estado en este roadmap debe respaldarse con commit/rama, comando de pruebas y documento de evidencia.
- Ver prompts de trabajo en `prompts/01-auditoria-repositorio.md`, `02-instrumentacion-trazas.md`, `03-benchmark.md`, `04-dashboard-propio.md` y `05-notebook-eft.md`.

- **13-11-2026:** progreso inicial fijado en **50 % EP3** (M0–M3).
- **14-11-2026 (corte M4):** **70 % EP3** estimado al cerrar M4 en `feat/observability` con validación Playwright y pruebas Python/JS offline.
- **14-11-2026 (corte M5–M7):** **95 % de hitos ponderados completados** (M0–M6 cerrados en `feat/observability`: M5 solo offline, M6 alcance local) y **~90 % de preparación conservadora EP3** (M7 con evidencias, guion y checklist listos; pendiente informe con autoría humana y presentación).
