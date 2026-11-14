# Hito 4 — Dashboard local de observabilidad

Especificación: solicitud Hito 4; contratos reales de docs/13 y app/api/observability_routes.py. Alcance autorizado: implementación local completa, sin publicación ni proveedores.

Diseño: consola de fondo claro con identidad editorial KnowledgeFlow, navegación lateral, KPIs con cobertura, gráficos SVG accesibles e interactivos, tabla paginada y explorador de trazas. Calidad conserva N/D. No nuevos paquetes.

Acceso: flag desactivado por defecto, peer loopback + Host literal loopback + rechazo de proxy/origen externo, HTTP Basic con contraseña propia de mínimo 32 caracteres. Nunca usar OBS_READ_KEY en HTML/JS ni reenviarla. GETs locales autenticados consultan el mismo EventStore; API Hito 3 permanece intacta. Uso remoto no soportado.

Alternativas: proxy público descartado por seguridad; introducir autenticación multiusuario excede acceso local solicitado. HTTP Basic evita mantener sesiones/tokens en JS y entrega el desafío al navegador. Limitación: credencial local en caché del navegador; cerrar contexto y rotar secreto para revocar.

- [x] Pruebas backend primero: autenticación, origen/host/peer, endpoints previos, filtros, paginación, vacío, agregados sin cambio, privacidad, costo y calidad.
- [x] Backend: dashboard_routes.py, dashboard.py (lector acotado y cache por proceso de 10 s/8 consultas), config/main. Máximo 7 días y 50000 eventos por resumen; rechazar consultas mayores sin resultados parciales.
- [x] Frontend: HTML fuera de static (ruta protegida); CSS/JS organizados en static/observability. SVG propios; contenido dinámico textContent; gráficos con tablas accesibles. Paginación limit/after, sin descargas automáticas. AbortController y generación para respuestas obsoletas.
- [x] Pruebas JS con node:test: N/D, ceros reales, jerarquía, ciclos, padres ausentes y paginación estable. Validación visual local si el entorno permite navegador.
- [x] Documentar docs/14-dashboard-web.md, navegación existente, variables y evidencia. Revisar seguridad independientemente y ejecutar suites offline completas off/on.

Riesgos: modo heredado no equivale a mock; agregados filtrados no representan toda la traza; finalización UTC no es inicio monotónico; falta de raíz/hijos no permite declarar traza completa; cache de pocos segundos puede anteceder retención; sin credenciales o store devolver error, nunca datos ficticios.

## Cierre y evidencia

Implementación local realizada. Suite offline off/on: 341 passed en cada modo, 20 warnings heredados, 0 intentos de red. 6 tests JavaScript aprobados (incluidos mediante una prueba Python). Revisión independiente sin defectos importantes; recuperación de paginación ajustada. Navegador no verificado: proceso externo rechazado por riesgo de exportación; alternativa local bloqueada por sockets del sandbox. Sin capturas ni afirmaciones de validación visual. Detalle e inventario en docs/14-dashboard-web.md. Sin push, merge ni informe académico.
