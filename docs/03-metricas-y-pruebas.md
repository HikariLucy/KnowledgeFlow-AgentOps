# Catálogo de métricas, fórmulas y plan de pruebas

Todas las métricas del módulo deben mostrar **unidad, muestra N, origen, modo de ejecución y período**. Se evita reportar una precisión global si hay tareas incomparables.

| Métrica | Fórmula o método | Notas |
|---|---|---|
| Exactitud de tarea | `correctos / evaluables` | Solo ground truth revisado. Si no hay referencia, N/D |
| Precisión de contexto RAG | `documentos relevantes recuperados / documentos recuperados` | A nivel documento o chunk, pero no mezclar |
| Consistencia | `salidas semántica/operacionalmente equivalentes / repeticiones válidas` | Definir equivalencia antes; agrupar mismo escenario y configuración |
| Error rate | `ejecuciones failed / total ejecuciones` | Mostrar también timeout, tool_error, llm_error |
| Latencia | `fin_monotónico - inicio_monotónico` | ms por etapa y total; p50/p95, mediana y N |
| Uso de recursos | Tokens entrada/salida reportados; memoria/CPU si se instrumentan | Ausencia de metadatos = null, no cero |
| Abstención | `abstenciones correctas / casos donde corresponde abstenerse` | Medir también falsas abstenciones |
| Herramientas | Cantidad y duración de tool calls; errores por tool | Evitar confundir acciones con llamadas internas |

## Escenarios mínimos recomendados

1. Consulta interna con respuesta respaldada y citas.
2. Consulta externa con documentos verificados.
3. Pregunta fuera del dominio con abstención esperada.
4. Creación de incidente con validaciones y permisos.
5. Seguimiento multi-turno usando memoria.
6. Fallo controlado en herramienta o LLM.
7. Intento de prompt injection documentado, sin ejecutar acciones no autorizadas.
8. Contexto incompleto y recuperación irrelevante.

## Protocolo

1. Congelar versión del código (SHA), modelo, `top_k`, umbral, fecha y dataset.
2. Etiquetar `offline`, `mock` o `live` a cada ejecución y no mezclarlas al comparar.
3. Usar `evaluation/dataset_verified.json` como referencia RAG anterior, revisando si sus campos sirven para el agente EP3.
4. Construir fixtures deterministas sin llamadas externas para tests, más pruebas live acotadas y explícitas.
5. Repetir escenarios no deterministas con N declarado, no extrapolar una sola respuesta.
6. Guardar salida estructurada y agregados reproducibles; no editar resultados manualmente.
7. Correlacionar cada anomalía con logs mediante `trace_id` y el commit usado.
8. Las recomendaciones y conclusiones se redactarán por el equipo, **no por IA**, en el informe.

## Criterios de aceptación

- Pruebas offline ejecutables sin `.env` ni credenciales.
- Una corrida real no se confunde con una simulación.
- Percentiles calculados sobre datos observados, sin valores inventados.
- Logs sanitizados y sin estado conversacional sensible.
- Dashboard con estados vacíos claros y sin errores ante datasets parciales.
