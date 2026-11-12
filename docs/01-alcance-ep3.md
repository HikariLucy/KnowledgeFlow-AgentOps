# Alcance EP3 y relación con la EFT

## Fuente académica y discrepancia

La pauta de EP3 de los materiales del proyecto se titula **Evaluación Parcial N.º 3 — Implementación de Observabilidad** y señala **ISY1010**, un 35% de ponderación, encargo grupal 60% y presentación grupal 40%. El PDF `EFT_ISY0101_Estudiante.pdf` se titula **Evaluación Final Transversal**, señala **ISY0101**, un 40% de ponderación, encargo individual 20% y defensa individual 80%. No confundirlas; confirmar la pauta vigente con el docente.

## Requisitos de EP3 según pauta disponible

| Entregable | Evidencia verificable | Estado |
|---|---|---|
| ≥ 3 métricas aplicadas al agente | Scripts, dataset, fórmulas y tabla de resultados | Pendiente |
| Precisión / consistencia / frecuencia de errores | Benchmark con ground truth revisado | Pendiente |
| Latencia / recursos | Duraciones por tramo; tokens solo si están disponibles | Pendiente |
| Logs y trazabilidad | Identificadores correlacionados y eventos JSON sin secretos | Pendiente |
| Dashboard de monitoreo | Vista funcional propia con filtros, gráficos y trazas | Pendiente |
| Recomendaciones prácticas | Hallazgos con evidencia y propuestas escritas por el equipo | Pendiente |
| Informe técnico | Hasta **5 páginas**, capturas, gráficos, referencias APA | Pendiente |
| Repositorio | Código fuente, documentación, bocetos, pruebas y README de ejecución | Parcial: EP2 importada |
| Presentación | **10 minutos de exposición + 10 de preguntas por pareja** | Pendiente |
| Entrega | AVA y correo del docente, según fecha indicada por el curso | Pendiente |

La pauta admite **Grafana, Kibana, Streamlit, Power BI u otras herramientas**: no obliga a Streamlit. Una UI HTML/CSS/JS que exhiba métricas y trazas es compatible con ese alcance, siempre que realmente funcione y demuestre resultados.

## EFT: lo adicional

La EFT requiere la solución completa EP1+EP2+EP3: prompts y RAG, agente con herramientas y memoria, arquitectura, observabilidad, seguridad y mejora. Exige informe académico **PDF**, código en **Jupyter Notebook/Colab**, copia por AVA y correo, y defensa **individual** de hasta 10 minutos que muestre prototipo y dashboard.

## Fuera de alcance del MVP

- Recrear el RAG o cambiar el agente por un framework nuevo.
- Entrenar/fine-tuning del LLM.
- Stack SaaS obligatorio de monitoreo, infraestructura nueva o despliegue productivo.
- Activar llamadas a Gemini en CI o tests por defecto.
- Almacenar razonamiento interno privado del modelo.
- Publicar secretos, bases de datos reales o registros con información personal.

**Regla:** funcionalidades propuestas no se presentan como implementadas y resultados de ejemplo no se rotulan como evidencia experimental.
