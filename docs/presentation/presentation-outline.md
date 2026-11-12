# Esquema de Presentación Oral (Presentation Outline) — KnowledgeFlow RAG

**Duración Estimada Total**: 10 minutos (8 diapositivas recomendadas, alineadas con los indicadores oficiales IE1–IE9).

---

## Estructura de Diapositivas

### Diapositiva 1: Problema y Caso Organizacional (IE1 — 15%)
- **Duración sugerida**: 1:00 min
- **Contenido Clave**:
  - Problemática de dispersión documental y desconfianza ante alucinaciones de LLMs en el entorno corporativo.
  - Caso simulado **NovaTech SpA** (caso pedagógico): Necesidad de consultar políticas internas de acceso e incidentes y compararlas frente a marcos normativos públicos (OWASP, NIST).
- **Evidencia**: Corpus en [`../../knowledge/internal/`](../../knowledge/internal/) y [`../../knowledge/external/`](../../knowledge/external/).
- **Apoyo al Orador**:
  > [REQUIERE EXPLICACIÓN DEL EQUIPO: Presentación del equipo y planteamiento del caso organizacional.]

---

### Diapositiva 2: Propuesta de Solución: KnowledgeFlow RAG (IE1, IE3)
- **Duración sugerida**: 1:00 min
- **Contenido Clave**:
  - Enfoque *Evidence-First*: Respuestas fundamentadas con trazabilidad documental interactiva.
  - Separación entre conocimiento institucional (`INT`) y público (`EXT`).
  - Compuerta temprana de abstención ante similitud insuficiente ($\tau < 0.60$) para reducir respuestas no respaldadas.
- **Evidencia**: Consola web editorial y esquema `QueryResponse`.
- **Apoyo al Orador**:
  > [REQUIERE EXPLICACIÓN DEL EQUIPO: Explicación de la propuesta de valor y del enfoque de seguridad.]

---

### Diapositiva 3: Arquitectura Técnica y Diagrama Modular (IE4 — 15%, IE7 — 10%)
- **Duración sugerida**: 1:30 min
- **Contenido Clave**:
  - Diagrama end-to-end: Web UI $\to$ FastAPI $\to$ Source Router $\to$ FAISS (Embeddings 768d) $\to$ Early Abstention $\to$ Grounded Generator $\to$ Citation Validator.
  - Desacoplamiento de modelos: `gemini-3.5-flash-lite` (Routing) y `gemini-3.5-flash` (Generación fundamentada).
- **Evidencia**: Diagrama Mermaid en [`../architecture/architecture.md`](../architecture/architecture.md).
- **Apoyo al Orador**:
  > [REQUIERE EXPLICACIÓN DEL EQUIPO: Recorrido por el flujo de componentes y justificación del desacoplamiento.]

---

### Diapositiva 4: Flujos RAG Dual-Source y Balanceo de Fuentes (IE3 — 10%, IE8 — 10%)
- **Duración sugerida**: 1:15 min
- **Contenido Clave**:
  - Agente `GeminiSourceRouter`: Clasificación semántica hacia `internal`, `external` o `all` con fallback de seguridad.
  - Balanceo de cuotas: Asignación equitativa $k/2$ en consultas comparativas (`all`) para evitar que un dominio sature el contexto.
- **Evidencia**: [`../../app/agents/source_router.py`](../../app/agents/source_router.py) y [`../../app/rag/pipeline.py`](../../app/rag/pipeline.py).
- **Apoyo al Orador**:
  > [REQUIERE EXPLICACIÓN DEL EQUIPO: Argumentación sobre cómo se resolvió la recuperación balanceada multi-fuente.]

---

### Diapositiva 5: Prompt Engineering, Seguridad y Validación de Citas (IE2 — 10%, IE6 — 10%)
- **Duración sugerida**: 1:15 min
- **Contenido Clave**:
  - Aislamiento de planos: Directivas de sistema separadas del contexto de datos en bloques XML (mitigación de Prompt Injection).
  - Citas obligatorias `[S#]` y reparación controlada mediante segunda generación correctiva ante citas fantasma.
  - Verificación de coherencia del índice mediante fingerprint determinista SHA-256 (`verify_index_freshness`).
- **Evidencia**: [`../../app/rag/prompts.py`](../../app/rag/prompts.py), [`../../app/rag/generator.py`](../../app/rag/generator.py), [`../../tests/test_security.py`](../../tests/test_security.py).
- **Apoyo al Orador**:
  > [REQUIERE EXPLICACIÓN DEL EQUIPO: Explicación de los patrones de prompting y del mecanismo de validación de citas.]

---

### Diapositiva 6: Calibración Experimental y Compuerta de Abstención (IE6 — 10%, IE8 — 10%)
- **Duración sugerida**: 1:30 min
- **Contenido Clave**:
  - Barrido de umbrales sobre dataset verificado de 20 casos (15 answerable, 5 OOD).
  - Selección del umbral $\tau = 0.60$: menor valor evaluado con 100% de retención de casos válidos y 0% de fuga en preguntas fuera de dominio.
  - Abstención temprana: corte inmediato del flujo si no hay evidencia $\ge 0.60$ (ahorro de cómputo y reducción de respuestas no fundamentadas).
- **Evidencia**: Tabla de resultados en [`../evidence/evaluation-evidence.md`](../evidence/evaluation-evidence.md).
- **Apoyo al Orador**:
  > [REQUIERE EXPLICACIÓN DEL EQUIPO: Presentación de los datos del barrido paramétrico y fundamentación de la decisión.]

---

### Diapositiva 7: Demostración en Vivo / Consola Web (IE9 — 10%)
- **Duración sugerida**: 1:30 min
- **Contenido Clave**:
  - Ejecución en vivo de consulta interna (`[INT]`), consulta externa (`[EXT]`) y consulta fuera de dominio (Abstención).
  - Interacción con citas `[S1]` $\to$ scroll y resaltado en el Evidence Ledger.
  - Despliegue de trazabilidad técnica.
- **Evidencia**: Guía paso a paso en [`../evidence/demo-runbook.md`](../evidence/demo-runbook.md).
- **Apoyo al Orador**:
  > [REQUIERE EXPLICACIÓN DEL EQUIPO: Conducción de la demostración visual según el Demo Runbook.]

---

### Diapositiva 8: Limitaciones de Cuota, Lecciones y Cierre (IE8 — 10%, IE9 — 10%)
- **Duración sugerida**: 1:00 min
- **Contenido Clave**:
  - Restricción de cuota observada durante la evaluación: 20 RPD Free Tier para `gemini-3.5-flash` (`GenerateRequestsPerDayPerProjectPerModel-FreeTier`), mitigada en enrutamiento desacoplando a `gemini-3.5-flash-lite`.
  - Suite de 158 pruebas offline automatizadas y harness de preview aislado.
  - Síntesis de aprendizajes en arquitectura RAG de nivel empresarial.
- **Apoyo al Orador**:
  > [REQUIERE EXPLICACIÓN DEL EQUIPO: Conclusiones finales, reflexiones del equipo y sesión de preguntas.]
