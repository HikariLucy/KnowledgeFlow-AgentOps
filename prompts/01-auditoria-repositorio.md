# Prompt 01 — Auditoría y regresión

Actúa como ingeniero senior de Python/FastAPI, agentes, RAG y calidad de software.

**Contexto:** trabaja en `KnowledgeFlow-AgentOps`, copia verificada de `KnowledgeFlow-Agent` (EP2), con 141 archivos de código, pruebas y documentos conservados. El objetivo EP3 es observabilidad y trazabilidad; no queremos reescribir el agente.

**Tareas, sin modificar código funcional:**
1. Leer README, AGENTS.md, docs/00-resumen-proyecto.md, docs/01-alcance-ep3.md y docs/05-roadmap.md.
2. Mostrar rama, `git status`, estructura relevante y dependencias.
3. Ejecutar `pytest -q` en modo offline; registrar exactamente resultados, entorno y errores.
4. Inspeccionar `app/main.py`, rutas FastAPI, `AdaptiveOrchestrator`, planner, RAG, herramientas, memoria, evaluación y UI.
5. Determinar puntos de instrumentación y cuáles KPIs se pueden derivar **sin** consumir API.
6. Identificar datos personales/secretos que podrían filtrarse en logs.
7. Redactar `docs/10-auditoria-tecnica.md` con hallazgos fácticos y `docs/11-plan-instrumentacion.md` con etapas y criterios de aceptación.
8. Listar cambios propuestos; no implementarlos hasta revisión.

**Restricciones:** no invocar Gemini, no consumir cuota, no hacer push, no tocar entornos ni secretos, no inventar resultados, no redactar conclusiones ni justificaciones académicas. Explicitar pruebas que no pudieron ejecutarse.

**Salida esperada:** mapa de componentes, pruebas verificadas, recomendaciones de instrumentación como tareas técnicas a evaluar, riesgos y archivos donde aplicar cada cambio.
