# Prompt 05 — Revisión de seguridad y privacidad EP3

Actúa como analista de seguridad de aplicaciones y observabilidad.

Revisa logging, endpoints del dashboard, almacenamiento JSONL, datos de evaluación y tools del agente.

- Verificar que ningún endpoint de observabilidad haga escrituras en incidentes.
- Probar acceso no autorizado y exposición de API keys, `.env`, tokens, RUT, correos y campos sensibles.
- Garantizar escape de texto en UI y evitar inyección de HTML.
- Verificar límite de paginación, tamaño de logs, rotación y controles de retención.
- Comprobar que errores del logger no cambien la lógica de negocio.
- Revisar exposición del servidor en red y proponer controles adecuados a demo local.
- Ejecutar tests offline y registrar evidencia de casos probados.
- Documentar hechos técnicos, riesgos y acciones pendientes en `docs/14-revision-seguridad.md` sin redactar justificaciones o reflexiones académicas.

No invocar APIs externas, no almacenar datos reales de estudiantes/trabajadores, no hacer push.
