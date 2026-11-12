# Prompt 02 — Instrumentación segura y trazas

Actúa como desarrollador Python especializado en observabilidad. Trabaja sobre el diagnóstico aprobado de `docs/10-auditoria-tecnica.md`.

**Objetivo:** registrar el recorrido de `POST /api/agent` y sus herramientas sin alterar las respuestas ni permisos actuales.

**Implementar incrementalmente:**
- Estructura JSON para eventos: timestamp UTC, `session_id` opaco, `trace_id` por solicitud, `span_id` por operación, `parent_span_id`, componente, operación, estado, duración, tipo de error y modo `offline/mock/live`.
- Correlación mediante un contexto aislado por solicitud; no filtrar IDs de otras conversaciones.
- Métrica `duration_ms` basada en reloj monotónico para endpoint, planner, orquestador, tools RAG, memoria y escritura en incidentes.
- Recolección de tokens **solo si** la respuesta del proveedor lo informa; en otro caso null.
- Exportación local JSONL con lectura limitada, rotación o política de retención y `.gitignore` actualizado.
- Sanitización de logs: prohibir API keys, RUT, correos, consultas y documentos completos, textos de incidentes y razonamiento interno privado.
- Pruebas offline de correlación, errores y no-regresión.

**Restricciones:** no cambiar schemas externos, decisiones del planner, abstenciones, operaciones ni seguridad. No invocar APIs de pago. No crear datos de prueba indistinguibles de datos reales. No push.

**Entrega:** código, tests, documentación con contrato JSON y comandos exactos; resumen factual de `pytest`, errores/limitaciones y ejemplo de traza **sintética rotulada**.
