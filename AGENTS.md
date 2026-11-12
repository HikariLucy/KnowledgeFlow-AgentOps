# Instrucciones para Codex — KnowledgeFlow AgentOps

- **Idioma:** español para documentación de usuario; código consistente con el estilo existente.
- **Proyecto académico:** EP3 de Ingeniería de Soluciones con IA; evolución de EP2, no reescritura.
- **Tecnologías existentes:** Python/FastAPI, Gemini/FAISS, CrewAI, SQLite, interfaz HTML/CSS/JS. El dashboard debe integrarse aquí; **no usar Streamlit**.
- Revisar README, docs/00-resumen-proyecto.md y docs/05-roadmap.md antes de implementar.
- Comenzar con auditoría y ejecución de `pytest -q` **offline**. No invocar Gemini, CrewAI live ni embeddings pagos sin autorización explícita.
- Preservar contratos API, seguridad de escritura, lógica RAG, memoria y pruebas.
- Logs/trazas: registrar metadatos, no prompts sensibles, secretos, textos de incidentes, datos personales ni razonamiento privado.
- Cada cambio debe incluir pruebas, lista de archivos afectados y limitaciones.
- No inventar métricas, tiempos, resultados ni evidencia; `N/D` cuando falte dato.
- No redactar conclusiones, justificaciones técnicas académicas ni reflexiones individuales: son trabajo del equipo.
- No realizar `git push`, merge ni cambios de infraestructura por iniciativa propia.
