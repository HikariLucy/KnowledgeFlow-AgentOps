# Resumen del proyecto — KnowledgeFlow AgentOps

**Asignatura:** Ingeniería de Soluciones con IA · **Caso:** NovaTech SpA · **Etapa:** EP3, con preparación para la EFT.

## Necesidad

KnowledgeFlow ya permite responder consultas documentales mediante RAG y ejecutar operaciones controladas sobre incidentes usando agentes y memoria. La nueva etapa debe permitir **observar, medir, explicar fallas y evaluar mejoras** de esas ejecuciones.

## Solución planteada

Incorporar una capa transversal de **instrumentación**, un conjunto de **evaluaciones reproducibles** y un **dashboard web propio**, manteniendo el sistema EP1/EP2.

- **Base funcional migrada:** FastAPI, RAG Gemini/FAISS, CrewAI, herramientas de incidentes, memoria SQLite, interfaz web, pruebas y documentación previa.
- **Módulos EP3 por desarrollar:** registros JSON estructurados, correlación de trazas, latencias por componente, métricas de calidad/consistencia/errores, dashboard y evidencia comparativa.
- **Frontend definido:** HTML, CSS y JavaScript que consumen endpoints JSON de FastAPI. **No se utilizará Streamlit.**

## Flujo objetivo

```text
Usuario → FastAPI → Planner/Orquestador → RAG y/o herramientas → Respuesta
             │             │                  │
             └────────── eventos/spans/latencias ──────────┐
                                                            ↓
                                               Datos estructurados
                                                            ↓
                                      Evaluador + Dashboard web propio
                                                            ↓
                                       Evidencia → análisis del equipo
```

## Evidencia que debemos obtener

1. Benchmarks con casos revisados, denominadores explícitos y escenarios variados.
2. Latencia total y por componente: media, p50 y p95.
3. Consistencia en repeticiones comparables, tasa de errores y uso de recursos cuando exista medición.
4. Identificación de anomalías con un `trace_id` reproducible y logs sanitizados.
5. Capturas del dashboard y reporte técnico elaborado **por el equipo** a partir de datos reales.

## Estado real al inicio de EP3

| Elemento | Estado |
|---|---|
| Copia de EP2 a AgentOps | **Hecho:** 141 archivos importados y SHA de blobs cotejados |
| Código RAG/agente | **Migrado:** funcionamiento reportado por EP2; requiere regresión en destino |
| Métricas y dashboard nuevos | **Pendientes** |
| Benchmark medido con AgentOps | **Pendiente** |
| Hallazgos, propuestas y defensa | **Pendientes** |

**Procedencia:** KnowledgeFlow-Agent, rama `main`, commit `53efc993f1edac638f364aac7e6d34982f023bb6`. README EP2 histórico: `docs/legacy/README_EP2.md`. Esta migración copia contenidos; no transfiere el historial completo de Git.

> Documento de alcance y síntesis técnica inicial; no sustituye las conclusiones ni justificaciones personales que exige el curso.
