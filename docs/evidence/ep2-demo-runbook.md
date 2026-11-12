# Runbook de Demo EP2 — KnowledgeFlow Agent

Este documento define una secuencia reproducible para la demostración en vivo de la EP2. Su objetivo es reducir improvisación y separar claramente la evidencia técnica de las explicaciones orales del equipo.

> Alcance: este runbook describe el runtime principal expuesto por `POST /api/agent` y la UI `GET /agent`. La integración CrewAI jerárquica fue validada por separado y no debe presentarse como si este endpoint pasara actualmente por CrewAI.

---

## 1. Objetivo de la demo

Demostrar, en un único flujo de dos turnos, que KnowledgeFlow Agent puede:

1. interpretar una solicitud operacional;
2. consultar conocimiento interno mediante RAG;
3. mostrar evidencia y citas;
4. crear un incidente validado;
5. escribir el resultado en memoria;
6. recuperar el incidente en el siguiente turno;
7. continuar la operación sin que el usuario reenvíe el `incident_id`;
8. mostrar plan, herramientas, memoria, fuentes y observaciones.

Duración objetivo de la demo funcional: **3 a 5 minutos**.

---

## 2. Preflight — 5 minutos antes de presentar

### 2.1 Entrar al proyecto

```bash
cd ~/proyectos/KnowledgeFlow-Agent
source .venv/bin/activate
git status
```

Esperado:

```text
working tree clean
branch: feat/ep2-agent-foundation
```

### 2.2 Verificar índice local

```bash
test -f vectorstore/index.faiss && echo "index.faiss: OK"
test -f vectorstore/documents.json && echo "documents.json: OK"
```

Esperado:

```text
index.faiss: OK
documents.json: OK
```

Si falta el índice:

```bash
python -m app.rag.indexer
```

### 2.3 Verificar suite mínima

No es necesario ejecutar las 242 pruebas inmediatamente antes de exponer. Para un smoke rápido:

```bash
pytest -q   tests/test_agent_api.py   tests/test_orchestrator.py   tests/test_planner.py   tests/test_memory_write_back.py
```

La última validación completa registrada fue:

```text
242 passed
20 warnings
pip check: No broken requirements found
compileall: OK
git diff --check: OK
```

### 2.4 Confirmar puerto 8000

```bash
ss -ltnp | grep ':8000' || true
```

Si ya existe un servidor correcto, reutilizarlo. Si es un proceso antiguo:

```bash
pkill -f 'uvicorn app.main:app' || true
```

---

## 3. Iniciar runtime de demo

Para reducir el riesgo de HTTP 503 por alta demanda del proveedor, usar temporalmente Flash Lite:

```bash
GEMINI_CHAT_MODEL=gemini-3.5-flash-lite \
uvicorn app.main:app --reload --port 8000
```

Mantener esta terminal visible como respaldo técnico.

Abrir:

```text
http://127.0.0.1:8000/agent
```

La UI heredada de EP1 permanece disponible en:

```text
http://127.0.0.1:8000/
```

---

## 4. Demo principal — Turno 1

### Paso 1 — Crear contexto limpio

En `/agent`:

1. pulsar **Nueva conversación**;
2. verificar que cambió el `conversation_id`;
3. pulsar **Cargar creación MFA**.

La UI debe preparar:

```text
Tipo:
Consultar + crear incidente

Alcance:
Interno

Mensaje:
Perdí mi autenticador MFA. Revisa el procedimiento y registra un incidente.
```

Payload operacional:

```text
title: Pérdida de autenticador MFA
category: access
severity: medium
description: Usuario perdió el dispositivo utilizado para MFA.
```

### Paso 2 — Ejecutar

Pulsar **Ejecutar agente** una sola vez.

### Paso 3 — Evidencia que se debe mostrar

En la franja superior del resultado:

```text
STATUS: completed
INTENT: incident_create
INCIDENT: INC-xxxxx
ITERATIONS: 1
```

En **Respuesta del agente**:

- procedimiento MFA recuperado;
- al menos una cita `[S1]`;
- mensaje final `Incidente creado: INC-xxxxx.`.

En **Plan y herramientas**:

```text
✓ Consultar conocimiento aplicable
✓ Validar información mínima del incidente
✓ Crear incidente
```

Tools esperadas:

```text
search_knowledge
create_incident
```

En **Fuentes recuperadas**:

- `faq_interna.txt` debe aparecer entre las fuentes;
- pueden aparecer `politica_accesos.md` y `procedimiento_incidentes.md`;
- mostrar score de similitud.

En **Observaciones operacionales**:

```text
search_knowledge -> completed
create_incident  -> completed
```

### Punto verbal sugerido

Explicar únicamente el comportamiento observable:

> “En este turno el agente primero consulta conocimiento interno, conserva las fuentes recuperadas y luego ejecuta la escritura operacional mediante una herramienta tipada. La respuesta expone tanto el plan como las tools ejecutadas.”

---

## 5. Demo principal — Turno 2

### Paso 1 — No cambiar de conversación

No pulsar **Nueva conversación**.

Después del Turno 1 aparecerá:

```text
Continuar seguimiento de INC-xxxxx
```

Pulsar ese botón.

La UI debe cambiar automáticamente a:

```text
Tipo:
Seguimiento del incidente en memoria

Mensaje:
Agrega que la identidad ya fue validada.

Nota:
Identidad del usuario validada.
```

El `incident_id` no se envía nuevamente.

### Paso 2 — Ejecutar

Pulsar **Ejecutar agente**.

### Paso 3 — Evidencia que se debe mostrar

Resultado esperado:

```text
STATUS: completed
INTENT: incident_note
INCIDENT: mismo INC-xxxxx del Turno 1
ITERATIONS: 1
```

Respuesta:

```text
Seguimiento agregado a INC-xxxxx.
```

Plan:

```text
✓ Localizar incidente
✓ Agregar nota de seguimiento
```

Tools:

```text
search_incidents
append_incident_note
```

En **MEMORY / Contexto recuperado**:

- debe aparecer contexto short-term del turno anterior;
- debe aparecer memoria persistente asociada al incidente;
- el incidente correcto debe ser el más reciente y relevante de la conversación.

En **EVIDENCE / Fuentes recuperadas**:

```text
0
```

Esto es correcto. El segundo turno no necesita volver al RAG.

### Punto verbal sugerido

> “En el segundo turno no reenviamos el identificador. El planner recupera el incidente desde la memoria de la conversación y ejecuta únicamente las herramientas operacionales necesarias. Por eso no hay nuevas fuentes RAG en este turno.”

---

## 6. Qué NO afirmar durante la demo

No decir que:

- `POST /api/agent` ejecuta CrewAI internamente;
- CrewAI controla actualmente la memoria del endpoint;
- CrewAI controla actualmente el planner del endpoint;
- la demo de escritura pasa por el Manager de CrewAI.

La arquitectura validada actualmente tiene dos caminos:

### Runtime principal de la UI/API

```text
FastAPI
→ AgentService
→ RuleBasedPlanner
→ AdaptiveOrchestrator
→ Tools
→ MemoryWriteBack
```

### Integración CrewAI validada por separado

```text
CrewAI Manager
→ Knowledge Agent / Operations Agent
→ CrewAI BaseTool adapters
→ domain tools
```

CrewAI fue validado en vivo para delegación jerárquica y RAG real read-only, pero no es el runtime detrás de `/api/agent`.

---

## 7. Contingencias

### A. HTTP 503 de Gemini

Síntoma:

```text
503 UNAVAILABLE
This model is currently experiencing high demand
```

Acción:

1. mantener `gemini-3.5-flash-lite` como override de demo;
2. reintentar una sola vez;
3. si persiste, pasar a evidencia registrada en:
   - `docs/evidence/ep2-agent-demo-evidence.md`;
   - capturas de la demo validada;
   - suite offline.

No presentar un 503 del proveedor como falla lógica del agente.

### B. Puerto 8000 ocupado

```bash
ss -ltnp | grep ':8000'
```

Si es el mismo servidor, reutilizarlo.

Si no:

```bash
pkill -f 'uvicorn app.main:app'
```

y levantar nuevamente.

### C. El follow-up no encuentra memoria

Verificar primero:

- mismo `conversation_id`;
- no haber pulsado **Nueva conversación**;
- el Turno 1 debe haber terminado en `completed`;
- debe haberse creado un `INC-xxxxx`.

Si no existe contexto resoluble, el comportamiento seguro esperado es:

```text
needs_clarification
¿A qué incidente deseas agregar el seguimiento?
```

No debe ejecutar `search_knowledge` accidentalmente ni escribir sin ID resuelto.

### D. Aparecen incidentes históricos en MEMORY

La base SQLite conserva memorias persistentes de pruebas anteriores.

Para una demo visual limpia:

- usar **Nueva conversación** antes del Turno 1;
- la recuperación semántica está filtrada por `conversation_id`, por lo que los eventos de otras conversaciones no deben gobernar el follow-up;
- si existen memorias antiguas de la misma conversación de pruebas, crear una conversación nueva.

### E. RAG se abstiene

No forzar una escritura manualmente durante la exposición.

El comportamiento correcto es que una abstención del RAG pueda detener una acción que dependa de esa evidencia.

---

## 8. Respaldo por API si la UI falla

### Turno 1

```bash
curl -s \
  -X POST \
  http://127.0.0.1:8000/api/agent \
  -H 'Content-Type: application/json' \
  -d '{
    "conversation_id": "demo-respaldo-001",
    "message": "Perdí mi autenticador MFA. Revisa el procedimiento y registra un incidente.",
    "knowledge_query": {
      "query": "¿Qué procedimiento corresponde ante la pérdida de un autenticador MFA?",
      "source_scope": "internal",
      "top_k": 4
    },
    "create_incident": {
      "title": "Pérdida de autenticador MFA",
      "description": "Usuario perdió el dispositivo utilizado para MFA.",
      "category": "access",
      "severity": "medium"
    }
  }' | python -m json.tool
```

### Turno 2

Mantener el mismo `conversation_id`:

```bash
curl -s \
  -X POST \
  http://127.0.0.1:8000/api/agent \
  -H 'Content-Type: application/json' \
  -d '{
    "conversation_id": "demo-respaldo-001",
    "message": "Agrega que la identidad ya fue validada.",
    "append_incident_note": {
      "note": "Identidad del usuario validada."
    }
  }' | python -m json.tool
```

---

## 9. Evidencia de respaldo

Documentos relevantes:

```text
docs/evidence/ep2-agent-demo-evidence.md
README.md
```

Última validación registrada:

```text
242 passed
20 warnings conocidos
No broken requirements found
```

Hitos live registrados:

- RAG real + FAISS + Gemini;
- CrewAI hierarchical + Knowledge Agent;
- API agentic;
- creación de incidente;
- MemoryWriteBack;
- recuperación multi-turno;
- follow-up sin reenviar `incident_id`;
- UI agentic con trace.

---

## 10. Cierre de la demo

Cerrar mostrando tres ideas observables:

```text
1. RAG aporta evidencia documental.
2. Las tools convierten esa evidencia en una acción operacional controlada.
3. La memoria permite continuar el flujo en un turno posterior sin repetir contexto.
```

No usar esta sección como conclusión académica del informe; es únicamente una guía operativa para cerrar la demostración en vivo.
