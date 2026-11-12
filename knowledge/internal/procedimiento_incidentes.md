# Procedimiento de Gestión de Incidentes de Seguridad — NovaTech SpA

> **Aviso Académico**: Documento simulado exclusivamente para fines pedagógicos en el proyecto KnowledgeFlow RAG (Asignatura ISY0101).

## 1. Detección y Notificación
Cualquier evento inusual, anomalía en registros del sistema o sospecha de compromiso de credenciales debe ser reportado inmediatamente a través del canal de guardia de ciberseguridad (alerta-seguridad@novatech-demo.local) o registrando un ticket de severidad alta en la mesa de ayuda.

## 2. Clasificación de Severidad
- **Severidad 1 (Crítica)**: Interrupción total de servicios centrales o filtración confirmada de datos confidenciales. Tiempo de respuesta inicial: menor a 15 minutos.
- **Severidad 2 (Alta)**: Afectación parcial de aplicaciones productivas sin pérdida identificada de datos. Tiempo de respuesta inicial: menor a 45 minutos.
- **Severidad 3 (Media/Baja)**: Intentos aislados de escaneo o incidentes que no comprometen la disponibilidad ni la integridad. Tiempo de respuesta inicial: menor a 4 horas.

## 3. Contención y Mitigación
1. Aislar las estaciones de trabajo o servidores afectados de la red corporativa.
2. Preservar la evidencia digital (volcado de memoria RAM y logs de auditoría) antes de reiniciar equipos.
3. Notificar al comité técnico de incidentes para coordinar la remediación.

## 4. Cierre y Lecciones Aprendidas
Dentro de los 3 días hábiles posteriores a la resolución del incidente, se debe elaborar un informe post-mortem que identifique la causa raíz, el impacto y las acciones correctivas preventivas.
