# Roadmap incremental — EP3 y EFT

| Hito | Tarea | Criterio de cierre | Estado |
|---|---|---|---|
| M0 | Migración desde EP2 | 141 archivos comparados por SHA | **Completado** |
| M1 | Auditoría y regresión | `pytest -q` documentado; mapa de riesgos y puntos de instrumentación | **Completado** (`docs/10-auditoria-ep2.md`) |
| M2 | Trazas JSON | IDs relacionados, latencias, errores sanitizados y tests | **Completado** (`docs/12-observabilidad.md`) |
| M3 | Agregación y métricas | SQLite acotado y API protegida | **Completado** (`docs/13-agregacion-metricas.md`) |
| M4 | Dashboard propio | Filtros, KPIs, gráficos, explorador de spans, estados vacíos y Playwright | **Completado** (`docs/14-dashboard-web.md`, `docs/15-validacion-visual.md`) |
| M5 | Evaluación reproducible | Benchmark offline, dataset revisado, resultados desglosados, pruebas | **Completado offline** (`docs/16-benchmark-experimental.md`; live pendiente) |
| M6 | Seguridad | Revisión de permisos, redacción, retención, XSS y casos maliciosos | **Completado (alcance local)** (`docs/17-auditoria-seguridad.md`) |
| M7 | Evidencias EP3 | Evidencias, guion demo, checklist y base de informe máx. 5 páginas | **Base técnica lista** (`docs/18`, `docs/19`, `docs/20`; falta autoría humana y defensa) |
| EFT | Preparación EFT | Notebook/Colab de demostración, informe académico, defensa individual | Pendiente (fuera del alcance EP3) |

## Regla de ejecución con Codex

Trabajar por hitos. Cada hito termina con **diff revisado, pruebas offline, riesgos y evidencia**. Antes de pasar al siguiente, comprobar que EP2 siga funcionando. No ejecutar APIs live ni hacer push automáticamente sin autorización del equipo.

## Primeros prompts

Ver `prompts/01-auditoria-repositorio.md`, `02-instrumentacion-trazas.md`, `03-benchmark.md`, `04-dashboard-propio.md` y `05-notebook-eft.md`.
