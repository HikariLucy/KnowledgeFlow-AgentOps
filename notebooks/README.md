# Notebooks para la EFT (ISY0101) — KnowledgeFlow AgentOps

Este directorio contiene la entrega técnica reproducible en formato **Jupyter / Google Colab** para la Evaluación Final Transversal (EFT), reutilizando directamente los módulos estables de EP1, EP2 y EP3 en `app/` sin duplicar la lógica de negocio.

## Notebooks disponibles

| Notebook | Propósito | Alcance |
|---|---|---|
| [00_knowledgeflow_eft_principal.ipynb](00_knowledgeflow_eft_principal.ipynb) | Cuaderno principal integrador | Flujo completo EP1 (RAG + Prompts) → EP2 (Agente + Herramientas + Memoria) → EP3 (Observabilidad + Benchmark + Dashboard) en modo offline + sección live deshabilitada por defecto |
| [01_ep1_rag_y_prompts.ipynb](01_ep1_rag_y_prompts.ipynb) | Módulo EP1 | Inspección en vivo de `app/rag/prompts.py` y `app/rag/context.py`, chunking, indexación FAISS y recuperación dual (`internal`, `external`, `all`) + abstención |
| [02_ep2_agente_herramientas_memoria.ipynb](02_ep2_agente_herramientas_memoria.ipynb) | Módulo EP2 | Inspección en vivo de `app/agentic/service.py` y `app/memory/short_term.py`, planificación, herramientas de incidentes sobre SQLite temporal y continuidad conversacional |
| [03_ep3_observabilidad_benchmark_dashboard.ipynb](03_ep3_observabilidad_benchmark_dashboard.ipynb) | Módulo EP3 | Inspección en vivo de `app/observability/telemetry.py` y `app/api/dashboard_routes.py`, trazas sanitizadas, benchmark offline y validación FastAPI del dashboard |

## Ejecución en modo offline (por defecto)

Todos los notebooks arrancan con `RUN_LIVE_GEMINI = False`, eliminan `GEMINI_API_KEY` del entorno de ejecución y usan directorios SQLite temporales (`tempfile.TemporaryDirectory`) junto con dobles deterministas offline. **Los resultados del modo offline no representan el rendimiento de Gemini real.**

### En Python local

```bash
source .venv/bin/activate
.venv/bin/python scripts/run_notebooks_offline.py
```

Para abrir de forma interactiva en Jupyter local, instalar `jupyterlab` o `notebook` en el entorno virtual (no está incluido en `requirements.txt`).

### En Google Colab

1. Subir o abrir `notebooks/00_knowledgeflow_eft_principal.ipynb` en Google Colab.
2. Ejecutar la primera celda de código: detecta `google.colab`, clona la rama correspondiente del repositorio e instala `requirements.txt` automáticamente.
3. Ejecutar las celdas siguientes en orden para reproducir EP1, EP2 y EP3 en modo offline.
4. La sección live permanece deshabilitada (`RUN_LIVE_GEMINI = False`) para evitar consumo accidental de cuota.

## Limitaciones conocidas

- `requirements.txt` incluye `crewai[google-genai]==1.15.22` y `faiss-cpu>=1.14.0`; en Google Colab la primera instalación puede tardar varios minutos y requerir reinicio de entorno si hay conflictos con versiones preinstaladas de `numpy` o `pydantic`.
- `jupyter` y `nbconvert` no forman parte de `requirements.txt`; la validación automatizada local se ejecuta mediante `scripts/run_notebooks_offline.py` y `pytest`.
- NovaTech SpA se mantiene como escenario demostrativo del repositorio; su validación como caso organizacional real sigue pendiente.
