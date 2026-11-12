# Guía de Ejecución y Demostración en Vivo (Demo Runbook) — KnowledgeFlow RAG

Este documento describe la secuencia técnica y los comandos operacionales para realizar una demostración en vivo reproducible y estructurada.

---

## 1. Modos de Ejecución Disponibles

### Modo A: Demostración en Vivo Real (Producción Local)
> **Requisito**: Variable `GEMINI_API_KEY` configurada en `.env` y cuota disponible de Google Gemini.

Ejecutar en la terminal:
```powershell
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8010
```
Abrir en el navegador:
```text
http://127.0.0.1:8010/
```

---

### Modo B: Demostración Offline de Respaldo (Backup UI Preview)
> **Propósito**: Respaldo ante fallos de conectividad, indisponibilidad de API o agotamiento de cuota diaria (HTTP 429) durante la presentación.
> **Advertencia**: *Este modo es una previsualización determinista de interfaz. NO ejecuta el pipeline RAG live y NO constituye evidencia de rendimiento.*

Ejecutar en la terminal:
```powershell
python -m uvicorn scripts.ui_preview:app --reload --host 127.0.0.1 --port 8010
```
Abrir en el navegador:
```text
http://127.0.0.1:8010/
```

---

## 2. Secuencia Técnica de Demostración (Paso a Paso)

```text
[Inicio] Presentación de la Mesa de Trabajo Editorial
   ↓
[Paso 1] Explicación del Selector de Procedencia (AUTO / INT / EXT / INT+EXT)
   ↓
[Paso 2] Consulta Interna → Demostración de Citas [S1] y Resaltado en Evidence Ledger
   ↓
[Paso 3] Consulta Externa → Validación de Fuentes Públicas Curadas (OWASP)
   ↓
[Paso 4] Consulta Mixta → Recuperación Dual Balanceada (INT + EXT)
   ↓
[Paso 5] Consulta Fuera de Dominio → Demostración de Abstención Temprana (Similitud < 0.60)
   ↓
[Paso 6] Inspección de Trazabilidad Técnica y Contrato JSON
```

### Paso 1: Apertura y Explicación de la Interfaz
1. Cargar `http://127.0.0.1:8010/`.
2. Destacar la estética **Editorial Knowledge Workbench**:
   - Franja superior compacta con identificadores técnicos (`RAG SYSTEM / EVIDENCE-FIRST RETRIEVAL`).
   - Guía de arquitectura del pipeline en 4 estaciones (`01 ROUTE` $\to$ `02 RETRIEVE` $\to$ `03 VERIFY` $\to$ `04 ANSWER`).
   - Selector segmentado de procedencia: `AUTO`, `INT` (Interno NovaTech), `EXT` (Estándares OWASP/NIST) e `INT + EXT` (Comparativo).

### Paso 2: Ejecución de Consulta Interna
1. Hacer clic en la consulta sugerida `01`: `¿Qué requisitos deben cumplir las contraseñas internas?`.
2. Presionar el botón **Consultar** o pulsar <kbd>Ctrl</kbd>+<kbd>Enter</kbd>.
3. Mostrar:
   - Estado **FUNDAMENTADA** en verde.
   - Presencia de la cita `[S1]` en el texto.
   - Hacer clic sobre `[S1]`: observar el desplazamiento y el halo visual (`.highlighted`) sobre la tarjeta de `politica_accesos.md` en el **Evidence Ledger**.
   - Insignia de procedencia azul pizarra `[INT] INTERNA` y score de similitud coseno.

### Paso 3: Ejecución de Consulta Externa
1. Hacer clic en la consulta sugerida `02`: `¿Cómo se previene Prompt Injection según OWASP?`.
2. Presionar **Consultar**.
3. Mostrar:
   - Clasificación hacia el ámbito `external`.
   - Insignia verde bosque `[EXT] EXTERNA` asociada a `owasp_llm_prompt_injection_prevention.md`.
   - Citas directas que respaldan las recomendaciones de mitigación.

### Paso 4: Ejecución de Consulta Mixta (Dual)
1. Hacer clic en la consulta sugerida `03`: `Compara el procedimiento interno de incidentes con buenas prácticas externas.`.
2. Presionar **Consultar**.
3. Mostrar:
   - El **Evidence Ledger** contiene fuentes combinadas de ambos dominios (`procedimiento_incidentes.md` `[INT]` y `nist_sp_800_218_ssdf.md` `[EXT]`).
   - La franja de trazabilidad reporta `ALCANCE USADO: ALL`.
   - El texto sintetiza la comparación asignando citas independientes a cada afirmación.

### Paso 5: Demostración de Abstención Temprana (Out-Of-Domain)
1. Ingresar en el área de texto: `¿Cuál es la velocidad de la luz en el vacío?`.
2. Presionar **Consultar**.
3. Mostrar:
   - Activación de la tarjeta especial: **"EVIDENCIA INSUFICIENTE (Abstención Controlada)"**.
   - Explicar la compuerta de seguridad: al no superarse el umbral de similitud ($\ge 0.60$), el sistema corta el flujo antes de generar texto para reducir respuestas sin respaldo documental.
   - Cero citas registradas (`citations: []`) y cero fuentes en el ledger (`sources: []`).

### Paso 6: Inspección de Trazabilidad Técnica
1. Desplegar la sección inferior **"Ver trazabilidad técnica del contrato QueryResponse"**.
2. Mostrar la tabla de parámetros y el bloque JSON retornado por la API (`source_scope`, `abstained`, `citations`, `sources`).
