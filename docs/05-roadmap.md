# Roadmap incremental — EP3 y EFT

| Hito | Tarea | Criterio de cierre | Estado |
|---|---|---|---|
| M0 | Migración desde EP2 | 141 archivos comparados por SHA | **Completado** |
| M1 | Auditoría y regresión | `pytest -q` documentado; mapa de riesgos y puntos de instrumentación | Pendiente |
| M2 | Trazas JSON | IDs relacionados, latencias, errores sanitizados y tests | Pendiente |
| M3 | Evaluación reproducible | Benchmark, dataset revisado, resultados desglosados, pruebas | Pendiente |
| M4 | Dashboard propio | Filtros, KPIs, gráficos, explorador de spans y estados vacíos | Pendiente |
| M5 | Seguridad | Revisión de permisos, redacción, retención y casos maliciosos | Pendiente |
| M6 | Evidencias EP3 | Capturas, análisis de logs, material presentación, informe máx. 5 páginas | Pendiente |
| M7 | EFT | Notebook/Colab de demostración, informe académico, defensa individual | Pendiente |

## Regla de ejecución con Codex

Trabajar por hitos. Cada hito termina con **diff revisado, pruebas offline, riesgos y evidencia**. Antes de pasar al siguiente, comprobar que EP2 siga funcionando. No ejecutar APIs live ni hacer push automáticamente sin autorización del equipo.

## Primeros prompts

Ver `prompts/01-auditoria-repositorio.md`, `02-instrumentacion-trazas.md`, `03-benchmark.md`, `04-dashboard-propio.md` y `05-notebook-eft.md`.
