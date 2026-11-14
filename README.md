# KnowledgeFlow AgentOps

**ISY0101 · Ingeniería de Soluciones con IA · EP3 / preparación EFT**

Continuación de la solución organizacional **NovaTech SpA**:
- [EP1: Knowledge-RAG](https://github.com/HikariLucy/Knowledge-RAG)
- [EP2: KnowledgeFlow-Agent](https://github.com/HikariLucy/KnowledgeFlow-Agent)
- **EP3: KnowledgeFlow-AgentOps** (este repositorio).

## Objetivo

Agregar **observabilidad, trazabilidad y evaluación reproducible** a la base de agentes funcionales sin rehacer el RAG ni el orquestador. Las métricas deben permitir identificar errores, medir calidad, latencia y uso de recursos, y documentar mejoras fundamentadas en evidencia.

**Dashboard:** interfaz propia con **FastAPI + HTML/CSS/JavaScript**, integrada con la UI actual del agente; **sin Streamlit**. El equipo reportó su implementación y mostró su funcionamiento visual **en la rama local `feat/observability`**, todavía no integrada en `main`; la revisión visual integral y el cierre de M4 siguen pendientes. No se presentan métricas simuladas como resultados reales. **[Cómo iniciar y demostrar el dashboard](docs/08-guia-demostracion-dashboard.md).**

## Estado de migración

**Completada:** 141 archivos de EP2 importados y verificados por SHA, incluidos código, tests, UI, documentación y datasets. El README histórico se conserva en [docs/legacy/README_EP2.md](docs/legacy/README_EP2.md). Consultar [acta técnica de migración](docs/legacy/MIGRACION-EP2.md).

**Estado EP3 al 13-11-2026:** avance **estimado de hitos cerrados: 50 %** (M0–M3). M0 está verificado en GitHub; M1–M3 fueron reportados completos localmente. **M4: dashboard implementado localmente, con 341 pruebas Python y 6 JavaScript informadas, y capturas de navegación manual; pendiente revisión visual integral e integración de la rama.** El próximo cierre de M4 elevaría la estimación a 70 %. M5 benchmark, M6 seguridad integral y M7 entrega siguen pendientes. El código de M1–M4 **aún no está publicado en `main`**. Ver [roadmap ponderado](docs/05-roadmap.md).

## Base migrada desde EP2

El código original de EP2, las herramientas, memoria, pruebas, conocimientos de demostración, scripts y documentación histórica se importan desde el repositorio `HikariLucy/KnowledgeFlow-Agent` (rama `main`, snapshot del commit fuente `53efc993f1edac638f364aac7e6d34982f023bb6`). El README anterior se conserva en [docs/legacy/README_EP2.md](docs/legacy/README_EP2.md). Esta copia **no traslada por sí sola el historial Git** del repositorio anterior; conserva su procedencia.

## Ejecutar la base heredada

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
pytest -q
uvicorn app.main:app --reload --port 8000
```

Windows: activar `.venv\Scripts\Activate.ps1`. Las dependencias y pruebas se verificarán sobre el repositorio migrado. Las funciones con Gemini requieren una API key; **no ejecutarlas durante las pruebas offline**.

## Plan de trabajo

**Progreso estimado EP3: 50 %** (elaboración ponderada; no es nota académica ni avance EFT).

| Hito | Peso | Estado |
|---|---:|---|
| M0 Migración EP2 | 10 % | Verificado en GitHub |
| M1 Auditoría y regresión offline | 10 % | Reportado completado localmente |
| M2 Instrumentación JSON y trazabilidad | 15 % | Reportado completado localmente |
| M3 SQLite, agregados y API de observabilidad | 15 % | Reportado completado localmente |
| M4 Dashboard web propio | 20 % | Implementado localmente; validación integral y publicación pendientes |
| M5 Benchmark de precisión y consistencia | 15 % | Pendiente |
| M6 Seguridad y validación integral | 10 % | Pendiente |
| M7 Evidencias, informe y presentación EP3 | 5 % | Pendiente |

[Roadmap completo y criterios de cierre](docs/05-roadmap.md). La EFT tendrá planificación separada.

Documentos: [Resumen del proyecto](docs/00-resumen-proyecto.md) · [Alcance](docs/01-alcance-ep3.md) · [Arquitectura](docs/02-arquitectura-dashboard.md) · [Métricas](docs/03-metricas-y-pruebas.md) · [Seguridad](docs/04-seguridad-y-uso-ia.md) · [Roadmap](docs/05-roadmap.md) · **[Guía para mostrar el dashboard](docs/08-guia-demostracion-dashboard.md)** · [Prompts Codex](prompts/README.md).

> **Nota académica:** la pauta EP3 vista en las fuentes indica ISY1010, mientras EFT indica ISY0101. Confirmar la pauta válida con el docente. El informe EP3 tiene límite de cinco páginas, repositorio obligatorio y presentación grupal; la EFT requiere además código en notebook/Colab y defensa individual.
>
> IA: el equipo debe validar código y contenido, declarar herramientas de IA y **redactar por su cuenta** las justificaciones técnicas, conclusiones y reflexiones individuales. Los resultados de benchmark no se inventan.
