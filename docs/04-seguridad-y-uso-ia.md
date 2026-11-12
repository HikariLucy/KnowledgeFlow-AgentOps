# Seguridad, privacidad y uso responsable

## Controles propuestos

- **Minimización:** logs y trazas solo con metadatos necesarios (IDs opacos, timestamps, componente, operación, resultado, duración, error_type).
- **Redacción:** no registrar `.env`, API keys, credenciales, RUT, correos, teléfonos, prompts íntegros, contenido documental privado ni textos de incidentes.
- **IDs y correlación:** `session_id` agrupa conversación, `trace_id` identifica solicitud, `span_id` operación; `parent_span_id` conecta hijos.
- **Permisos:** el dashboard solo lectura requiere control de acceso antes de cualquier publicación. En la demo local también evitar exponer el servidor a la red.
- **Integridad:** no permitir a eventos ni dashboard ejecutar `create_incident` o `append_incident_note` por vías indirectas.
- **Resiliencia:** una falla del subsistema de telemetría no debe causar escritura indebida ni revelar secretos.
- **Retención:** definir duración y rotación para datos locales. Excluir `*.jsonl` runtime, bases reales, índices FAISS y resultados sensibles del control de versiones.
- **Validación:** sanitizar errores, prevenir inyección de texto en HTML y probar permisos de endpoints.

## Ética y reglamento académico

La pauta de EP3 y la EFT permiten IA para asistencia en redacción, referencias y diagramas, pero exigen **ideas, análisis, justificaciones y reflexiones propios**. Prohíben que IA redacte conclusiones, justificaciones técnicas y reflexiones individuales. El equipo debe declarar las herramientas usadas, revisar todas las salidas y citar el apoyo conforme a Duoc UC.

### Registro de uso de IA (para completar y validar)

| Herramienta | Uso permitido | Archivo/resultado revisado | Revisión humana |
|---|---|---|---|
| ChatGPT | Plan de trabajo, documentación auxiliar y estructura de prompts | Por completar | Por completar |
| Codex | Implementación de código y pruebas supervisadas | Por completar | Por completar |

No atribuir resultados de pruebas, observaciones o conclusiones a quien no los haya realizado.
