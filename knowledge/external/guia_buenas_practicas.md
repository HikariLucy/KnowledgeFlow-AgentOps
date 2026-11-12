# Guía de Buenas Prácticas de Ingeniería de Software

> **Aviso Académico**: Documento simulado exclusivamente para fines pedagógicos en el proyecto KnowledgeFlow RAG (Asignatura ISY0101).

## 1. Diseño y Arquitectura Modular
Los sistemas organizacionales deben construirse siguiendo patrones desacoplados y principios de alta cohesión. Cada módulo debe tener una única responsabilidad bien delimitada para facilitar el mantenimiento y la extensibilidad del código.

## 2. Manejo Seguro de Secretos y Configuración
- Las claves de API, tokens y credenciales de acceso jamás deben incorporarse en el código fuente versionado.
- Utilice variables de entorno centralizadas y plantillas seguras (.env.example) para orquestar la configuración en distintos ambientes (desarrollo, staging y producción).

## 3. Estrategias de Pruebas Automatizadas
La pirámide de testing debe priorizar pruebas unitarias rápidas y deterministas, complementadas con pruebas de integración en capas críticas de la aplicación. Toda prueba debe ser reproducible de forma aislada sin requerir servicios externos no simulados.

## 4. Documentación y Trazabilidad
Cada cambio estructural debe documentarse adecuadamente, incluyendo registros de cambios claros, especificaciones de arquitectura y diagramas de flujo que describan el comportamiento esperado de los componentes.
