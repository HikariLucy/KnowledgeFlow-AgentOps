# Prompt 06 — Notebook de demostración EFT

Actúa como ingeniero Python con experiencia en Jupyter/Google Colab. La EFT exige entregar código en formato notebook/Colab además de informe PDF y defensa individual.

Construye `notebooks/knowledgeflow_agentops_eft.ipynb` como **punto de entrada demostrativo** sobre los módulos reales del proyecto. No dupliques manualmente toda la aplicación en celdas gigantes.

El notebook debe:
1. Explicar dependencias, modo offline y cómo clonar/instalar el proyecto.
2. Inicializar fixtures deterministas sin claves de API para demostrar RAG/agentes cuando existan dobles de prueba.
3. Ejecutar métricas y mostrar gráficas/tablas a partir de datasets verificados.
4. Visualizar ejemplo de trazas sanitizadas y conectar por URL local al dashboard si el ambiente lo permite.
5. Incorporar celdas live opcionales, deshabilitadas por defecto, con manejo seguro de credenciales y aviso de consumo de cuota.
6. Ser compatible con ejecución limpia y con validación automatizada sin secretos.
7. Distinguir resultados sintéticos de experimentos reales.

No redactar conclusiones, justificaciones técnicas ni reflexiones de alumnos; dejar indicaciones para escritura humana.
