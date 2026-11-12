# Prompt 03 — Dataset y evaluador de métricas

Actúa como ingeniero de evaluación de sistemas RAG y agentes. Usa los resultados de instrumentación aprobados; preserva `app/evaluation/` y sus pruebas anteriores.

**Implementa:**
1. Dataset EP3 con tipos: consulta documental interna/externa, abstención, operaciones de incidentes, seguimiento multi-turno, errores controlados y prompt injection.
2. Reutilizar `evaluation/dataset_verified.json` cuando sea compatible; **no inventar etiquetas ground truth revisadas**.
3. Métricas con denominadores explícitos: exactitud sobre casos evaluables, consistencia de tareas repetidas, tasa de errores, latencias p50/p95, uso de tokens cuando exista, abstención y tool calls.
4. Separar métricas de router, retrieval y respuesta final.
5. Correr primero pruebas completamente offline/deterministas.
6. Registrar `mode` (`mock/offline/live`), commit, N de muestra, configuración, timestamp, comandos y limitaciones.
7. Crear exportaciones en JSON/CSV aptas para dashboard; datos sintéticos deben llevar `synthetic=true`.
8. Documentar resultados reales únicamente cuando hayan sido ejecutados.

**Límites:** no gastar cuota Gemini sin permiso, no ocultar fallos, no presentar mock como live, no concluir causalidad a partir de una muestra pequeña. No redactar conclusiones o justificaciones académicas.

**Resultado:** scripts, tests, formato de datos, instrucciones, resumen objetivo de mediciones disponibles y pendientes.
