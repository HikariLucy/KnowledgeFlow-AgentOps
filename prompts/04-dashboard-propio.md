# Prompt 04 — Dashboard web propio, integrado con FastAPI

Actúa como desarrollador frontend/backend de sistemas de observabilidad, con experiencia en HTML, CSS, JavaScript y FastAPI.

**Decisión de producto:** el usuario **no quiere Streamlit**. No lo instales ni lo utilices. Extiende la **interfaz web ya existente** en `app/ui/static/` de KnowledgeFlow Agent; conserva identidad visual, navegación y compatibilidad.

**Requisitos:**
1. Auditar brevemente los endpoints y archivos frontend existentes antes de programar.
2. Crear endpoints FastAPI **solo lectura** para series, resumen, filtrado de ejecuciones y traza individual desde datos de instrumentación sanitizados.
3. Crear ruta de dashboard integrada con el sitio: Resumen, Rendimiento, Ejecuciones, Calidad.
4. KPIs con N, unidades y procedencia: precisión evaluada, consistencia, errores, latencia p50/p95, token usage cuando exista.
5. Filtros por fecha, modo `offline/mock/live`, escenario, estado, componente y versión de experimento.
6. Gráficos dinámicos y tabla de ejecución: latencia por etapa, evolución temporal, errores, precisión por escenario, listado de `trace_id` y jerarquía de spans.
7. UI responsive, accesible, con errores y estados vacíos correctos. Usar JavaScript y SVG/CSS o biblioteca ligera si es realmente necesaria, documentando la elección.
8. Los ejemplos sintéticos deben identificarse con un aviso visible **DATOS SINTÉTICOS**. Donde no haya datos, mostrar **N/D**, nunca inventar porcentajes.
9. No revelar texto sensible de consultas, incidentes, secretos o documentos. Escapar HTML y validar los filtros.
10. Implementar pruebas backend y frontend apropiadas, sin invocar Gemini ni escribir incidentes.

**Restricciones:** no crear otra app o proyecto separado, no usar Streamlit ni obligar a React/Vite, no modificar la semántica del agente, no hacer push automáticamente.

**Entregar:** archivos, captura o boceto del dashboard, URL local y comandos de ejecución, tests verificados, limitaciones. Documentar implementación real en `docs/13-dashboard-implementacion.md`.
