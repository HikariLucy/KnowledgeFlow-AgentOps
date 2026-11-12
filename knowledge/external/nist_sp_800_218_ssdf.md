# Resumen Curado — NIST SP 800-218: Secure Software Development Framework (SSDF v1.1)

> **Tipo de Documento**: Resumen técnico curado para KnowledgeFlow RAG basado en una fuente pública oficial.
> **Fuente Oficial de Referencia**: NIST Special Publication 800-218 (SSDF Version 1.1).
> **Organización Emisora**: National Institute of Standards and Technology (NIST), U.S. Department of Commerce.
> **URL de Origen**: https://csrc.nist.gov/pubs/sp/800/218/final
> **Fecha de Consulta**: 2026-09-01
> **Aviso de Procedencia**: Este archivo constituye una síntesis pedagógica y técnica curada para propósitos de evaluación y RAG en KnowledgeFlow RAG (ISY0101), no una reproducción íntegra del documento original.

## 1. Protección de Todas las Formas de Código (Protect Software - PS.1)
- **Práctica PS.1**: Proteger todas las formas de código frente a accesos no autorizados y manipulaciones maliciosas.
- **Implementación**: Aplicar controles apropiados de acceso, autenticación e integridad sobre repositorios de código fuente, configuraciones, imágenes y artefactos de compilación durante todo el ciclo de vida del desarrollo.

## 2. Pruebas de Código Ejecutable para Identificar Vulnerabilidades (Produce Well-Secured Software - PW.8)
- **Práctica PW.8**: Probar el código ejecutable para identificar vulnerabilidades y verificar el cumplimiento de los requisitos de seguridad.
- **Determinación y Alcance**: Determinar cuándo corresponde realizar pruebas de código ejecutable, seleccionar los tipos de pruebas adecuados (como dynamic vulnerability testing, fuzz testing o penetration testing según corresponda) y definir su alcance.
- **Ejecución y Registro**: Diseñar y ejecutar las pruebas, documentar los resultados obtenidos y clasificar/triagear los problemas de seguridad detectados. La automatización de pruebas puede mejorar la repetibilidad, consistencia y trazabilidad de los hallazgos.

## 3. Identificación y Confirmación Continua de Vulnerabilidades (Respond to Vulnerabilities - RV.1)
- **Práctica RV.1**: Identificar y confirmar vulnerabilidades de forma continua.
- **Monitoreo y Reportes**: Recopilar información sobre vulnerabilidades potenciales provenientes de usuarios, adquirentes, investigadores de seguridad y fuentes públicas; investigar los reportes creíbles y analizar o probar el código para confirmar la existencia de vulnerabilidades. Mantener políticas estructuradas para la divulgación y remediación de vulnerabilidades.

## 4. Análisis de Vulnerabilidades y Causas Raíz (Respond to Vulnerabilities - RV.3)
- **Práctica RV.3**: Analizar las vulnerabilidades identificadas para determinar sus causas raíz.
- **Lecciones Aprendidas y Reducción de Recurrencia**: Registrar y documentar las causas de las vulnerabilidades, registrar las lecciones aprendidas, analizar patrones recurrentes y actualizar el ciclo de vida de desarrollo de software (SDLC) cuando corresponda para prevenir que vulnerabilidades similares vuelvan a ocurrir.
