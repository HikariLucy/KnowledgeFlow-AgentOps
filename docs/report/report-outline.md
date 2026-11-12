# Estructura de Informe Académico (Report Outline) — KnowledgeFlow RAG

Este esquema define la estructura, evidencias técnicas, figuras sugeridas y archivos de respaldo para la redacción del informe técnico-académico del proyecto (límite recomendado: 5 páginas), alineado con los indicadores oficiales de evaluación (IE1–IE9).

---

## Sección 1: Caso Organizacional y Requerimientos del Agente (IE1 — 15%)

### 1.1. Objetivo de la Sección
Contextualizar la problemática de dispersión documental y falta de trazabilidad en las organizaciones, presentando el caso de estudio simulado de **NovaTech SpA** (caso pedagógico).

### 1.2. Evidencias Técnicas Disponibles
- Corpus simulado de políticas internas de acceso, procedimientos de respuesta a incidentes y preguntas frecuentes institucionales.
- Delimitación de necesidades: consulta diferenciada de políticas internas (`INT`) y estándares normativos externos (`EXT`) mediante un agente enrutador (`SourceRouter`).

### 1.3. Archivos del Repositorio Asociados
- [`../../knowledge/internal/politica_accesos.md`](../../knowledge/internal/politica_accesos.md)
- [`../../knowledge/internal/procedimiento_incidentes.md`](../../knowledge/internal/procedimiento_incidentes.md)
- [`../../knowledge/internal/faq_interna.txt`](../../knowledge/internal/faq_interna.txt)

### 1.4. Redacción Pendiente
> [REQUIERE REDACCIÓN DEL EQUIPO: Contexto específico de la organización, delimitación del alcance operativo y justificación de la necesidad de negocio.]

---

## Sección 2: Prompt Engineering y Control de Contexto (IE2 — 10%)

### 2.1. Objetivo de la Sección
Detallar el diseño de prompts adaptados a los requerimientos del caso, las restricciones de grounding y la mitigación de inyección de contexto.

### 2.2. Evidencias Técnicas Disponibles
- **Aislamiento de Planos**: Delimitadores estructurales XML en prompts de usuario y sistema (`<context><source id="S#">...</source></context>`) para separar directivas de control de datos no confiables.
- **Formato Estricto de Citas**: Obligatoriedad de citas `[S#]` vinculadas exclusivamente al contexto provisto.
- **Prompt del Enrutador**: Clasificación estructurada en JSON (`RouteDecision`) con umbral de confianza.

### 2.3. Archivos del Repositorio Asociados
- [`../../app/rag/prompts.py`](../../app/rag/prompts.py)
- [`../../app/agents/source_router.py`](../../app/agents/source_router.py)

### 2.4. Redacción Pendiente
> [REQUIERE REDACCIÓN DEL EQUIPO: Análisis de los patrones de prompting seleccionados y justificación del diseño de instrucciones.]

---

## Sección 3: Flujos RAG Internos y Externos (IE3 — 10%)

### 3.1. Objetivo de la Sección
Describir la configuración de los flujos de recuperación documental para fuentes internas y externas, y la estrategia de balanceo multi-fuente.

### 3.2. Evidencias Técnicas Disponibles
- Ingesta estructurada con preservación de metadatos (`source_type`, `file_name`, `chunk_index`).
- Enrutamiento por ámbito (`internal`, `external`, `all`).
- Recuperación balanceada dual para consultas comparativas ($k/2$ fragmentos internos y $k/2$ externos).

### 3.3. Archivos del Repositorio Asociados
- [`../../app/rag/loaders.py`](../../app/rag/loaders.py)
- [`../../app/rag/retriever.py`](../../app/rag/retriever.py)
- [`../../app/rag/pipeline.py`](../../app/rag/pipeline.py)

### 3.4. Redacción Pendiente
> [REQUIERE REDACCIÓN DEL EQUIPO: Argumentación sobre el balanceo de fuentes y la prevención de sesgo hacia un único dominio.]

---

## Sección 4: Arquitectura de la Solución y Trazabilidad (IE4 — 15%, IE7 — 10%)

### 4.1. Objetivo de la Sección
Exponer el flujo end-to-end desde la interfaz web hasta la capa de persistencia vectorial, API FastAPI y validación de referencias.

### 4.2. Evidencias Técnicas Disponibles
- Diagrama de arquitectura Mermaid con capas desacopladas (UI, API, Enrutamiento, Recuperación, Compuerta de Abstención, Generación, Validación de Citas).
- Persistencia FAISS con embeddings normalizados `gemini-embedding-2` (768d).
- Verificación de coherencia del índice mediante fingerprint determinista SHA-256 (`verify_index_freshness`).
- Interfaz web editorial con Evidence Ledger y trazabilidad documental interactiva.

### 4.3. Tablas y Figuras Sugeridas
- Diagrama Mermaid de Arquitectura ([`../architecture/architecture.mmd`](../architecture/architecture.mmd), [`../architecture/architecture.md`](../architecture/architecture.md)).

### 4.4. Archivos del Repositorio Asociados
- [`../architecture/architecture.md`](../architecture/architecture.md)
- [`../../app/rag/vectorstore.py`](../../app/rag/vectorstore.py)
- [`../../app/api/routes.py`](../../app/api/routes.py)

### 4.5. Redacción Pendiente
> [REQUIERE REDACCIÓN DEL EQUIPO: Justificación técnica de las decisiones de arquitectura, desacoplamiento de modelos y diseño de componentes.]

---

## Sección 5: Coherencia, Evaluación Experimental y Fundamentación de Decisiones (IE5 — 10%, IE6 — 10%, IE8 — 10%)

### 5.1. Objetivo de la Sección
Presentar los resultados empíricos del barrido de umbrales, la calibración de la compuerta de abstención temprana, el estado de las evaluaciones live y la justificación técnica de las decisiones adoptadas.

### 5.2. Evidencias Técnicas Disponibles
- **Barrido Paramétrico (Threshold Sweep)**: Resultados con $Top\text{-}K=4$ sobre 20 casos revisados humanamente (0.60 seleccionado como el menor umbral evaluado que retiene 100% de casos válidos con 0% de fuga OOD).
- **Validación de Citas y Coherencia**: Sistema de citas obligatorias `[S#]` y reparación controlada ante citas fantasma.
- **Estado de Evaluación Live**: Reporte de estado `PENDING` por límite Free Tier de 20 RPD observado en `gemini-3.5-flash` (`quotaId: GenerateRequestsPerDayPerProjectPerModel-FreeTier`), documentando la restricción sin inventar métricas sintéticas.
- **Suite de Pruebas**: 158 tests automatizados ejecutados 100% offline.

### 5.3. Tablas y Figuras Sugeridas
- Tabla de resultados del Threshold Sweep ([`../evidence/evaluation-evidence.md`](../evidence/evaluation-evidence.md#12-tabla-de-resultados-empíricos-del-barrido)).
- Matriz de Trazabilidad con Rúbrica ([`../evidence/implementation-evidence.md`](../evidence/implementation-evidence.md#2-trazabilidad-con-pauta-oficial-de-evaluación-indicadores-ie1---ie9)).

### 5.4. Archivos del Repositorio Asociados
- [`../../app/evaluation/threshold_sweep.py`](../../app/evaluation/threshold_sweep.py)
- [`../../evaluation/dataset_verified.json`](../../evaluation/dataset_verified.json)
- [`../evidence/evaluation-evidence.md`](../evidence/evaluation-evidence.md)

### 5.5. Redacción Pendiente
> [REQUIERE REDACCIÓN DEL EQUIPO: Fundamentación final de decisiones de diseño, análisis crítico de resultados, conclusiones académicas y reflexiones individuales.]

---

## Sección 6: Planificación de Integridad Académica y Formato APA

### 6.1. Declaración de Uso de Herramientas de IA
> [REQUIERE REDACCIÓN DEL EQUIPO: Declaración explícita del uso de asistentes y herramientas de inteligencia artificial en el desarrollo del proyecto, de acuerdo con la normativa institucional.]

### 6.2. Checklist de Citación y Formato APA
- [ ] Referencias completas en formato APA para fuentes autoritativas externas:
  - OWASP Foundation. (2026). *OWASP LLM Prompt Injection Prevention Cheat Sheet*.
  - National Institute of Standards and Technology. (2022). *Secure Software Development Framework (SSDF) Version 1.1: Recommendations for Mitigating the Risk of Software Vulnerabilities* (NIST SP 800-218).
  - National Institute of Standards and Technology. (2020). *NIST Privacy Framework: A Tool for Improving Privacy through Enterprise Risk Management, Version 1.0*.
- [ ] Citas parentéticas en texto en las secciones teóricas y metodológicas.
- [ ] Consistencia en la numeración y títulos de tablas y figuras.
- [ ] Declaración firmada/declarada de autoría y uso de IA.
