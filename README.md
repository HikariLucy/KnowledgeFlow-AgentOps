# KnowledgeFlow AgentOps

**ISY0101 · Ingeniería de Soluciones con IA · EP3 / preparación EFT**

Continuación de la solución organizacional **NovaTech SpA**:
- [EP1: Knowledge-RAG](https://github.com/HikariLucy/Knowledge-RAG)
- [EP2: KnowledgeFlow-Agent](https://github.com/HikariLucy/KnowledgeFlow-Agent)
- **EP3: KnowledgeFlow-AgentOps** (este repositorio).

## Objetivo

Agregar **observabilidad, trazabilidad y evaluación reproducible** a la base de agentes funcionales sin rehacer el RAG ni el orquestador. Las métricas deben permitir identificar errores, medir calidad, latencia y uso de recursos, y documentar mejoras fundamentadas en evidencia.

**Dashboard:** interfaz propia con **FastAPI + HTML/CSS/JavaScript**, integrada con la UI actual del agente; **sin Streamlit**. Su implementación es un hito pendiente; no se presentan métricas simuladas como resultados reales.

## Estado de migración

**Completada:** 141 archivos de EP2 importados y verificados por SHA, incluidos código, tests, UI, documentación y datasets. El README histórico se conserva en [docs/legacy/README_EP2.md](docs/legacy/README_EP2.md). Consultar [acta técnica de migración](docs/legacy/MIGRACION-EP2.md).

**Pendiente:** ejecutar `pytest -q` en el nuevo entorno, implementar observabilidad, benchmark EP3 y dashboard web propio.

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

| Hito | Entregable | Estado |
|---|---|---|
| 0 | Migrar EP2 y documentar línea base | **Completado (141/141 archivos verificados)** |
| 1 | Auditoría técnica y pruebas offline | Pendiente |
| 2 | Logging JSON, trace/span IDs y medición de latencia | Pendiente |
| 3 | Benchmark y métricas (calidad, consistencia, errores, recursos) | Pendiente |
| 4 | Dashboard web propio, filtros y detalle de trazas | Pendiente |
| 5 | Evidencia, informe EP3 y defensa | Pendiente |
| 6 | Notebook demostrativo para EFT | Pendiente |

Documentos: [Resumen del proyecto](docs/00-resumen-proyecto.md) · [Alcance](docs/01-alcance-ep3.md) · [Arquitectura](docs/02-arquitectura-dashboard.md) · [Métricas](docs/03-metricas-y-pruebas.md) · [Seguridad](docs/04-seguridad-y-uso-ia.md) · [Roadmap](docs/05-roadmap.md) · [Prompts Codex](prompts/README.md).

> **Nota académica:** la pauta EP3 vista en las fuentes indica ISY1010, mientras EFT indica ISY0101. Confirmar la pauta válida con el docente. El informe EP3 tiene límite de cinco páginas, repositorio obligatorio y presentación grupal; la EFT requiere además código en notebook/Colab y defensa individual.
>
> IA: el equipo debe validar código y contenido, declarar herramientas de IA y **redactar por su cuenta** las justificaciones técnicas, conclusiones y reflexiones individuales. Los resultados de benchmark no se inventan.
