# KnowledgeFlow AgentOps

**ISY0101 · Ingeniería de Soluciones con IA · EP3 / preparación EFT**

Continuación de la solución organizacional **NovaTech SpA**:
- [EP1: Knowledge-RAG](https://github.com/HikariLucy/Knowledge-RAG)
- [EP2: KnowledgeFlow-Agent](https://github.com/HikariLucy/KnowledgeFlow-Agent)
- **EP3: KnowledgeFlow-AgentOps** (este repositorio).

## Objetivo

Agregar **observabilidad, trazabilidad y evaluación reproducible** a la base de agentes funcionales sin rehacer el RAG ni el orquestador. Las métricas deben permitir identificar errores, medir calidad, latencia y uso de recursos, y documentar mejoras fundamentadas en evidencia.

**Dashboard:** interfaz propia con **FastAPI + HTML/CSS/JavaScript**, integrada con la UI actual del agente; **sin Streamlit**. Implementación local documentada en [docs/14](docs/14-dashboard-web.md); no se presentan métricas simuladas como resultados reales.

## Estado de migración

**Completada:** 141 archivos de EP2 importados y verificados por SHA, incluidos código, tests, UI, documentación y datasets. El README histórico se conserva en [docs/legacy/README_EP2.md](docs/legacy/README_EP2.md). Consultar [acta técnica de migración](docs/legacy/MIGRACION-EP2.md).

**Verificado:** regresión offline de EP1/EP2 y capa local de observabilidad JSON con trazas, latencias y tokens reportados por el proveedor. Configuración, comandos y evidencia: [Observabilidad local segura](docs/12-observabilidad.md).

**Agregación operacional:** almacenamiento SQLite acotado y API de lectura protegida; ver [Hito 3](docs/13-agregacion-metricas.md).

**Dashboard local:** consola de lectura protegida en `/dashboard`, desactivada por defecto. [Ejecución, contratos y límites](docs/14-dashboard-web.md) y [validación visual Playwright](docs/15-validacion-visual.md).

**Benchmark experimental offline:** runner determinista y métricas de calidad/consistencia en [Hito 5](docs/16-benchmark-experimental.md) (sin llamadas reales a Gemini).

**Seguridad y evidencias EP3:** matriz de auditoría en [Hito 6](docs/17-auditoria-seguridad.md), [evidencias e informe base](docs/18-evidencias-ep3.md), [guion de demostración](docs/19-guion-demostracion.md) y [checklist](docs/20-checklist-entrega.md). Pendiente: evaluación live autorizada con Gemini y redacción humana del informe académico.

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
| M0 | Migrar EP2 y documentar línea base | **Completado (141/141 archivos verificados)** |
| M1 | Auditoría técnica y pruebas offline | **Completado** (`docs/10`, `docs/12`) |
| M2 | Logging JSON, trace/span IDs y latencia | **Completado** (`docs/12`) |
| M3 | Agregación SQLite y API de lectura protegida | **Completado** (`docs/13`) |
| M4 | Dashboard web propio y validación visual | **Completado** (`docs/14`, `docs/15`) |
| M5 | Benchmark experimental offline | **Completado (offline)** (`docs/16`; evaluación live pendiente) |
| M6 | Auditoría de seguridad integral | **Completado (alcance local)** (`docs/17`) |
| M7 | Evidencias técnicas, guion y checklist EP3 | **Base técnica lista** (`docs/18`, `docs/19`, `docs/20`; pendiente autoría humana) |

Documentos: [Resumen del proyecto](docs/00-resumen-proyecto.md) · [Alcance](docs/01-alcance-ep3.md) · [Arquitectura](docs/02-arquitectura-dashboard.md) · [Métricas](docs/03-metricas-y-pruebas.md) · [Seguridad](docs/04-seguridad-y-uso-ia.md) · [Roadmap](docs/05-roadmap.md) · [Prompts Codex](prompts/README.md).

> **Nota académica:** la pauta EP3 vista en las fuentes indica ISY1010, mientras EFT indica ISY0101. Confirmar la pauta válida con el docente. El informe EP3 tiene límite de cinco páginas, repositorio obligatorio y presentación grupal; la EFT requiere además código en notebook/Colab y defensa individual.
>
> IA: el equipo debe validar código y contenido, declarar herramientas de IA y **redactar por su cuenta** las justificaciones técnicas, conclusiones y reflexiones individuales. Los resultados de benchmark no se inventan.
