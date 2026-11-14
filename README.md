# KnowledgeFlow AgentOps

**ISY0101 · Ingeniería de Soluciones con IA · EP3 / preparación EFT**

Continuación de la solución organizacional **NovaTech SpA**:
- [EP1: Knowledge-RAG](https://github.com/HikariLucy/Knowledge-RAG)
- [EP2: KnowledgeFlow-Agent](https://github.com/HikariLucy/KnowledgeFlow-Agent)
- **EP3: KnowledgeFlow-AgentOps** (este repositorio).

## Objetivo

Agregar **observabilidad, trazabilidad y evaluación reproducible** a la base de agentes funcionales sin rehacer el RAG ni el orquestador. Las métricas deben permitir identificar errores, medir calidad, latencia y uso de recursos, y documentar mejoras fundamentadas en evidencia.

**Dashboard:** interfaz propia con **FastAPI + HTML/CSS/JavaScript**, integrada con la UI actual del agente; **sin Streamlit**. Implementación local documentada en [docs/14-dashboard-web.md](docs/14-dashboard-web.md), validación visual con Chromium/Playwright en [docs/15-validacion-visual.md](docs/15-validacion-visual.md) y guía de ejecución en **[Cómo iniciar y demostrar el dashboard](docs/08-guia-demostracion-dashboard.md)**. No se presentan métricas simuladas como resultados reales.

## Estado del proyecto (EP3)

**Avance EP3 (rama `feat/observability`):** **95 % de hitos ponderados completados** (M0–M6 = 95/100 puntos) y **~90 % de preparación conservadora de entrega**, al considerar que el informe académico con autoría humana y la presentación grupal siguen pendientes en M7. Ver [roadmap ponderado](docs/05-roadmap.md).

- **M0 — Migración EP2 (completado):** 141 archivos de EP2 importados y verificados por SHA, incluidos código, tests, UI, documentación y datasets. El README histórico se conserva en [docs/legacy/README_EP2.md](docs/legacy/README_EP2.md). Consultar [acta técnica de migración](docs/legacy/MIGRACION-EP2.md).
- **M1 — Auditoría y regresión offline (completado):** auditoría técnica de EP2 y regresión offline verificada; ver [docs/10-auditoria-ep2.md](docs/10-auditoria-ep2.md) y [docs/11-plan-implementacion-ep3.md](docs/11-plan-implementacion-ep3.md).
- **M2 — Observabilidad JSON y trazabilidad (completado):** capa local de observabilidad JSON con `trace_id`/`span_id`, latencias, errores sanitizados y tokens reportados por el proveedor; ver [Observabilidad local segura](docs/12-observabilidad.md).
- **M3 — Agregación operacional SQLite y API (completado):** almacenamiento SQLite acotado y API de lectura protegida (`/api/observability/*`); ver [Hito 3](docs/13-agregacion-metricas.md).
- **M4 — Dashboard web propio (completado):** consola de lectura protegida en `/dashboard` (desactivada por defecto si no se habilita observabilidad). [Ejecución, contratos y límites](docs/14-dashboard-web.md) y [validación visual Playwright](docs/15-validacion-visual.md).
- **M5 — Benchmark experimental (completado únicamente para evaluación offline):** runner determinista y métricas de calidad/consistencia en [Hito 5](docs/16-benchmark-experimental.md), sin llamadas reales a Gemini. **Los resultados del benchmark offline no representan el rendimiento de Gemini real**; la evaluación live autorizada queda pendiente como fase separada.
- **M6 — Seguridad y validación integral (completado para alcance local):** matriz de auditoría, control de acceso, redacción, sanitización, XSS y pruebas adversariales en [Hito 6](docs/17-auditoria-seguridad.md). No implica certificación ni garantías de producción.
- **M7 — Evidencias, informe y presentación EP3 (parcialmente preparado):** base técnica de evidencias, guion de demostración y checklist listos en [docs/18-evidencias-ep3.md](docs/18-evidencias-ep3.md), [docs/19-guion-demostracion.md](docs/19-guion-demostracion.md) y [docs/20-checklist-entrega.md](docs/20-checklist-entrega.md); **pendiente** la redacción humana del informe (máx. 5 páginas) y la presentación/defensa grupal.

## Base migrada desde EP2

El código original de EP2, las herramientas, memoria, pruebas, conocimientos de demostración, scripts y documentación histórica se importan desde el repositorio `HikariLucy/KnowledgeFlow-Agent` (rama `main`, snapshot del commit fuente `53efc993f1edac638f364aac7e6d34982f023bb6`). El README anterior se conserva en [docs/legacy/README_EP2.md](docs/legacy/README_EP2.md). Esta copia **no traslada por sí sola el historial Git** del repositorio anterior; conserva su procedencia.

## Ejecutar la base y pruebas offline

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
.venv/bin/python scripts/run_tests_offline.py --uvloop
.venv/bin/python scripts/run_tests_offline.py --uvloop --observe
node tests/dashboard_frontend.test.mjs
uvicorn app.main:app --reload --port 8000
```

Windows: activar `.venv\Scripts\Activate.ps1`. Las funciones con Gemini requieren una API key; **no ejecutarlas durante las pruebas offline**. Para iniciar el dashboard de observabilidad de forma segura en local, consultar [docs/08-guia-demostracion-dashboard.md](docs/08-guia-demostracion-dashboard.md) y [docs/14-dashboard-web.md](docs/14-dashboard-web.md).

## Plan de trabajo

**Progreso EP3:** **95 % de hitos ponderados completados** (M0–M6) y **~90 % de preparación conservadora EP3** (estimación de gestión del proyecto; no es nota académica ni avance EFT).

| Hito | Peso | Estado | Evidencia |
|---|---:|---|---|
| M0 Migración EP2 | 10 % | **Completado** | `docs/legacy/MIGRACION-EP2.md` (141/141 archivos) |
| M1 Auditoría y regresión offline | 10 % | **Completado** | `docs/10-auditoria-ep2.md`, `docs/11-plan-implementacion-ep3.md` |
| M2 Instrumentación JSON y trazabilidad | 15 % | **Completado** | `docs/12-observabilidad.md` |
| M3 SQLite, agregados y API de observabilidad | 15 % | **Completado** | `docs/13-agregacion-metricas.md` |
| M4 Dashboard web propio y validación visual | 20 % | **Completado** | `docs/14-dashboard-web.md`, `docs/15-validacion-visual.md` |
| M5 Benchmark de precisión y consistencia | 15 % | **Completado (solo offline)** | `docs/16-benchmark-experimental.md` (evaluación live pendiente) |
| M6 Seguridad y validación integral | 10 % | **Completado (alcance local)** | `docs/17-auditoria-seguridad.md` (sin garantías de producción) |
| M7 Evidencias, informe y presentación EP3 | 5 % | **Parcialmente preparado** | `docs/18-evidencias-ep3.md`, `docs/19-guion-demostracion.md`, `docs/20-checklist-entrega.md` (pendiente informe humano y presentación) |

[Roadmap completo y criterios de cierre](docs/05-roadmap.md). La EFT tendrá planificación separada.

## Documentación

- **Guías generales:** [Resumen del proyecto](docs/00-resumen-proyecto.md) · [Alcance](docs/01-alcance-ep3.md) · [Arquitectura](docs/02-arquitectura-dashboard.md) · [Métricas](docs/03-metricas-y-pruebas.md) · [Seguridad](docs/04-seguridad-y-uso-ia.md) · [Roadmap](docs/05-roadmap.md) · **[Guía para mostrar el dashboard](docs/08-guia-demostracion-dashboard.md)** · [Prompts Codex](prompts/README.md).
- **Hitos M1–M7:** [M1 Auditoría](docs/10-auditoria-ep2.md) · [Plan EP3](docs/11-plan-implementacion-ep3.md) · [M2 Observabilidad](docs/12-observabilidad.md) · [M3 Agregación](docs/13-agregacion-metricas.md) · [M4 Dashboard](docs/14-dashboard-web.md) · [M4 Validación visual](docs/15-validacion-visual.md) · [M5 Benchmark](docs/16-benchmark-experimental.md) · [M6 Seguridad](docs/17-auditoria-seguridad.md) · [M7 Evidencias](docs/18-evidencias-ep3.md) · [M7 Guion demo](docs/19-guion-demostracion.md) · [M7 Checklist](docs/20-checklist-entrega.md).

> **Nota académica:** la pauta EP3 vista en las fuentes indica ISY1010, mientras EFT indica ISY0101. Confirmar la pauta válida con el docente. El informe EP3 tiene límite de cinco páginas, repositorio obligatorio y presentación grupal; la EFT requiere además código en notebook/Colab y defensa individual.
>
> IA: el equipo debe validar código y contenido, declarar herramientas de IA y **redactar por su cuenta** las justificaciones técnicas, conclusiones y reflexiones individuales. Los resultados de benchmark no se inventan.
