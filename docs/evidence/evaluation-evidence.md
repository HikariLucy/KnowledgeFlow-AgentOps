# Evidencia de Evaluación y Calibración — KnowledgeFlow RAG

Este documento detalla los resultados empíricos observados en el barrido paramétrico, el estado de las evaluaciones en vivo dependientes de cuota de API y el registro de procedencia del corpus.

---

## 1. Evidencia Completada: Barrido de Umbrales (Threshold Sweep)

Se ejecutó el barrido paramétrico sobre el dataset verificado ([`../../evaluation/dataset_verified.json`](../../evaluation/dataset_verified.json)) compuesto por **20 casos de prueba** (15 casos *Answerable* y 5 casos *Out-Of-Domain / OOD*), todos con revisión humana formal (`human_reviewed: true`).

### 1.1. Configuración del Barrido
- **Source Router Agent**: `gemini-3.5-flash-lite`
- **Generador RAG**: `gemini-3.5-flash`
- **Embeddings**: `gemini-embedding-2` (dimensión `768`)
- **Top-K**: `4`

### 1.2. Tabla de Resultados Empíricos del Barrido

| Umbral ($\tau$) | Answerable Retained | False Abstention | OOD Correct Abstention | OOD Leakage | Hit@K | Observación Objetiva |
| :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **0.50** | 100.0% (15/15) | 0.0% (0/15) | 0.0% (0/5) | 100.0% (5/5) | 100.0% | OOD leakage = 100% (5/5 consultas fuera de dominio filtradas al contexto). |
| **0.55** | 100.0% (15/15) | 0.0% (0/15) | 60.0% (3/5) | 40.0% (2/5) | 100.0% | OOD leakage = 40% (2/5 consultas fuera de dominio filtradas al contexto). |
| **0.60** | **100.0% (15/15)** | **0.0% (0/15)** | **100.0% (5/5)** | **0.0% (0/5)** | **100.0%** | **15/15 answerable retained; 5/5 OOD abstained. Threshold seleccionado para esta versión.** |
| **0.65** | 100.0% (15/15) | 0.0% (0/15) | 100.0% (5/5) | 0.0% (0/5) | 100.0% | Mismas métricas observadas que 0.60 en el dataset controlado. |
| **0.70** | 100.0% (15/15) | 0.0% (0/15) | 100.0% (5/5) | 0.0% (0/5) | 100.0% | Mismas métricas observadas que 0.60 en el dataset controlado. |
| **0.75** | 60.0% (9/15) | 40.0% (6/15) | 100.0% (5/5) | 0.0% (0/5) | 60.0% | 6/15 answerable false-abstained (40% de falsa abstención en casos válidos). |

> **Observación Técnica Documentada**: $\tau = 0.60$ fue el menor umbral evaluado que, sobre el dataset controlado de 20 casos, conservó el 100% de los casos respondibles y produjo 0% de OOD leakage. No se postula como un óptimo universal fuera de las condiciones experimentales evaluadas.

---

## 2. Estado de la Evaluación Generativa End-to-End Oficial

- **Estado Actual**: `PENDING / BLOCKED BY EXTERNAL API QUOTA`.
- **Detalle de la Restricción y Desacoplamiento**:
  - Durante las corridas live se observó un límite Free Tier de **20 Requests Per Day (RPD)** para `gemini-3.5-flash` (`quotaId: GenerateRequestsPerDayPerProjectPerModel-FreeTier`).
  - La arquitectura desacoplada distribuye las llamadas entre modelos independientes:
    - **Source Router (`gemini-3.5-flash-lite`)**: Requiere $\approx 20$ llamadas de clasificación y operó durante el threshold sweep sin bloqueo de cuota observado.
    - **Generador Grounded (`gemini-3.5-flash`)**: Requiere $\approx 15$ llamadas de síntesis para los casos respondibles, más posibles llamadas de reparación de citas.
  - Al ejecutar el runner oficial sobre los 20 casos completos, la API retornó `429 RESOURCE_EXHAUSTED` al agotarse el cupo diario del modelo generativo.
- **Integridad de Evidencia**: No se fabricaron ni extrapolaron métricas generativas sintéticas para simular la corrida oficial. El runner y los artefactos de logging están preparados para ejecutarse en cuanto se disponga de cuota o clave con facturación habilitada.

---

## 3. Evidencia de la Suite de Pruebas Automatizadas (Tests)

La suite cuenta con **158 pruebas unitarias e integración** ejecutadas de manera $100\%$ offline:

```text
======================= 158 passed, 3 warnings in 3.23s =======================
```

### 3.1. Cobertura de Componentes Críticos del Pipeline
1. **Carga y Chunking** (`test_loaders.py`): Ingesta de Markdown/TXT, deduplicación de chunks y metadatos estructurados.
2. **Embeddings & Vectorstore** (`test_vectorstore.py`): Normalización de vectores, persistencia FAISS, fingerprint determinista SHA-256 e invalidación ante cambios en corpus.
3. **Recuperación y Balanceo** (`test_retriever.py`, `test_pipeline.py`): Filtros por ámbito (`internal`, `external`, `all`) y preservación de cuotas equitativas $k/2$.
4. **Enrutamiento Inteligente** (`test_router.py`, `test_model_separation.py`): Validaciones de JSON tipado, manejo de baja confianza y desacoplamiento de modelos (`gemini-3.5-flash-lite` vs `gemini-3.5-flash`).
5. **Generación y Citaciones** (`test_generator.py`, `test_prompts.py`): Detección de citas válidas `[S#]`, rechazo de identificadores fantasma y rutina de reparación controlada.
6. **Seguridad** (`test_security.py`): Aislamiento ante Prompt Injection en contexto y en preguntas de usuario.
7. **Calibración** (`test_threshold_sweep.py`): Barrido de umbrales sobre el dataset verificado.
8. **Interfaz Web y API** (`test_ui.py`, `test_api.py`, `test_health.py`): Endpoints `/api/query`, `/health`, `/docs` y entrega de assets HTML/CSS/JS.
9. **Aislamiento de Preview y Fidelidad** (`test_ui_preview.py`): Inmunidad de `app.main.app.dependency_overrides == {}` y validación de existencia física de las fuentes de fixtures en el corpus real.

### 3.2. Clasificación de Warnings
- **Starlette TestClient / httpx**: Advertencia de deprecación estándar en el entorno de pruebas de FastAPI.
- **FastAPI HTTP_422**: Renombramiento de constante numérica a favor de `HTTP_422_UNPROCESSABLE_CONTENT`.
- **Google GenAI / Python 3.14 `_UnionGenericAlias`**: Deprecación menor de tipado en versión preview de Python 3.14.

---

## 4. Procedencia y Gobernanza del Corpus Documental

### 4.1. Corpus Interno Simulado (NovaTech SpA)
Diseñado con fines pedagógicos y académicos para la asignatura ISY0101:
- `knowledge/internal/politica_accesos.md`: Política de contraseñas ($\ge 14$ caracteres, MFA obligatorio, menor privilegio).
- `knowledge/internal/procedimiento_incidentes.md`: Procedimiento de notificación, clasificación de severidad (1 a 3) y post-mortem.
- `knowledge/internal/faq_interna.txt`: Preguntas frecuentes institucionales sobre soporte y herramientas.

### 4.2. Corpus Externo Pedagógico
- `knowledge/external/guia_buenas_practicas.md`: Directrices generales de desarrollo seguro.
- `knowledge/external/referencia_seguridad.txt`: Conceptos de autenticación y cifrado.

### 4.3. Corpus Externo Autoritativo Curado
Resúmenes técnicos estructurados basados en fuentes públicas oficiales:
1. **OWASP LLM Prompt Injection Prevention Cheat Sheet**:
   - Archivo: `knowledge/external/owasp_llm_prompt_injection_prevention.md`
   - Fuente Oficial: OWASP Cheat Sheet Series
   - URL: `https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html`
   - Fecha de consulta: 2026-09-01
2. **NIST SP 800-218: Secure Software Development Framework (SSDF v1.1)**:
   - Archivo: `knowledge/external/nist_sp_800_218_ssdf.md`
   - Fuente Oficial: NIST Special Publication 800-218
   - URL: `https://csrc.nist.gov/pubs/sp/800/218/final`
   - Fecha de consulta: 2026-09-01
3. **NIST Privacy Framework v1.0**:
   - Archivo: `knowledge/external/nist_privacy_framework_data_minimization.md`
   - Fuente Oficial: NIST Privacy Framework Version 1.0
   - URL: `https://www.nist.gov/privacy-framework/privacy-framework`
   - Fecha de consulta: 2026-09-01
