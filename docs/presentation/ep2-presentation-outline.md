# Estructura de Presentación EP2 — KnowledgeFlow Agent

> **Documento de trabajo para la defensa oral.** La pauta asigna 10 minutos de exposición y 10 minutos de preguntas. Esta estructura organiza evidencia, tiempos y demo; no redacta las justificaciones técnicas, conclusiones ni reflexiones que deben ser propias del equipo.

## Objetivo de la exposición

Demostrar de forma clara y verificable que KnowledgeFlow Agent:

- integra herramientas de consulta y escritura;
- mantiene memoria de corto y largo plazo;
- recupera contexto semántico;
- planifica tareas multi-etapa;
- adapta el flujo según condiciones observadas;
- expone trazabilidad técnica;
- ejecuta un caso organizacional simulado de extremo a extremo.

## Distribución total

| Bloque | Tiempo |
|---|---:|
| Introducción y problema | 0:45 |
| Evolución EP1 → EP2 | 0:55 |
| Arquitectura | 1:20 |
| Tools y autonomía | 1:00 |
| Memoria y planificación | 1:15 |
| Decisiones adaptativas + CrewAI | 1:00 |
| Demo live multi-turno | 3:00 |
| Evidencia y cierre | 0:45 |
| **Total** | **10:00** |

Reparto sugerido:

```text
Integrante A:
  slides 1–3
  primera mitad de la demo

Integrante B:
  slides 4–6
  segunda mitad de la demo

Ambos:
  slide 8
  preguntas
```

La distribución puede invertirse. Lo importante es que ambos tengan participación visible y técnica.

---

# Diapositiva 1 — Problema organizacional

**Tiempo:** 0:45  
**Orador sugerido:** Integrante A

## Mostrar

Título:

```text
KnowledgeFlow Agent
De RAG documental a agente operativo con memoria y planificación
```

Subtítulo:

```text
ISY0101 · Evaluación Parcial N°2
```

Problema resumido:

```text
La EP1 podía recuperar y citar conocimiento.
La EP2 debe además decidir, actuar y mantener continuidad.
```

## Evidencia visual

Usar un diagrama simple:

```text
Pregunta → RAG → Respuesta

versus

Solicitud → Plan → Tools → Memoria → Acción
```

## Punto técnico a explicar

Describir el cambio de alcance:

- EP1 = recuperación documental;
- EP2 = flujo agentic operacional.

No dedicar tiempo a volver a explicar toda la EP1.

---

# Diapositiva 2 — Evolución EP1 → EP2

**Tiempo:** 0:55  
**Orador sugerido:** Integrante A

## Mostrar

```text
KnowledgeFlow RAG (EP1)
        ↓
search_knowledge
        ↓
KnowledgeFlow Agent (EP2)
```

La idea visual es mostrar que **el RAG no fue reemplazado**; se convirtió en una tool reutilizable.

## Componentes nuevos EP2

```text
AgentState
RuleBasedPlanner
AdaptiveOrchestrator
IncidentTools
ShortTermMemory
SemanticMemory
MemoryWriteBack
SQLite
CrewAI adapters
```

## Evidencia

```text
README.md
app/agentic/
app/memory/
app/tools/
app/integrations/
```

---

# Diapositiva 3 — Arquitectura implementada

**Tiempo:** 1:20  
**Orador sugerido:** Integrante A

## Mostrar

Usar como base:

```text
docs/architecture/ep2-agent-architecture.mmd
```

Versión visual recomendada:

```text
Usuario
  ↓
UI / FastAPI
  ↓
AgentService
  ↓
RuleBasedPlanner
  ↓
AdaptiveOrchestrator
  ├─ search_knowledge → RAG → FAISS/Gemini
  └─ IncidentTools → SQLite
  ↓
MemoryWriteBack
  ↓
ShortTermMemory + SemanticMemory
  ↓
AgentResponse
```

## Detalles técnicos que conviene nombrar

- FastAPI;
- Pydantic;
- FAISS;
- SQLite;
- Gemini;
- AgentState;
- trazabilidad de plan, tools, memoria y fuentes.

## Advertencia importante

Decir de forma precisa:

```text
POST /api/agent usa AgentService + Planner + AdaptiveOrchestrator.
CrewAI fue integrado y validado en un camino separado.
```

No afirmar que la UI principal pasa por CrewAI.

---

# Diapositiva 4 — Tools y autonomía operacional

**Tiempo:** 1:00  
**Orador sugerido:** Integrante B

## Mostrar

| Tool | Función |
|---|---|
| `search_knowledge` | consulta evidencia RAG |
| `create_incident` | crea incidente |
| `search_incidents` | localiza incidentes |
| `append_incident_note` | agrega seguimiento |

## Contratos

```text
Pydantic
→ payload validado
→ tool
→ repository/pipeline
```

## Evidencia a nombrar

- no SQL arbitrario desde el LLM;
- escritura separada de consulta;
- incidentes identificados como `INC-xxxxx`;
- tool calls visibles en la UI.

## Justificación

**REDACTAR Y EXPONER CON PALABRAS PROPIAS DEL EQUIPO.**

El equipo debe explicar por qué esta separación de tools se ajusta a su flujo organizacional.

---

# Diapositiva 5 — Memoria y planificación

**Tiempo:** 1:15  
**Orador sugerido:** Integrante B

## Mostrar

```text
ShortTermMemory
  → contexto reciente

LongTermMemoryStore
  → persistencia

SemanticMemory
  → recuperación por similitud

MemoryWriteBack
  → guarda eventos relevantes
```

## Planificación

Intenciones:

```text
knowledge_query
incident_create
incident_search
incident_note
```

Ejemplo:

```text
incident_create

1. Consultar conocimiento aplicable
2. Validar información mínima
3. Crear incidente
```

## Punto visual clave

Mostrar la continuidad:

```text
Turno 1
crea INC-xxxxx
      ↓
memoria
      ↓
Turno 2
"agrega seguimiento"
      ↓
recupera INC-xxxxx sin reenviar el ID
```

---

# Diapositiva 6 — Decisiones adaptativas + integración CrewAI

**Tiempo:** 1:00  
**Orador sugerido:** Integrante B

## Parte A — Decisiones adaptativas

Mostrar solo ejemplos concretos:

```text
Consulta
→ search_knowledge

Creación
→ search_knowledge
→ create_incident

Follow-up con memoria
→ search_incidents
→ append_incident_note

Sin contexto
→ needs_clarification

RAG abstained
→ bloqueo de escritura dependiente
```

## Parte B — CrewAI

Mostrar:

```text
Process.hierarchical

Manager
  ├─ Knowledge Agent
  └─ Operations Agent
```

Facts:

```text
Manager tools: []
Knowledge Agent: search_knowledge
Operations Agent: incident tools
memory=False
planning=False
```

## Justificación de orquestación

**REDACTAR Y EXPONER SIN IA.**

El equipo debe preparar su propia explicación técnica de:

- por qué eligió esos roles;
- por qué el Manager no ejecuta tools;
- por qué planificación y memoria quedaron fuera de CrewAI;
- cómo la arquitectura responde al requerimiento organizacional.

---

# Diapositiva 7 — Demo live multi-turno

**Tiempo:** 3:00  
**Oradores sugeridos:** ambos

Usar:

```text
docs/evidence/ep2-demo-runbook.md
```

## 7A — Turno 1

**Tiempo:** ~1:30  
**Orador:** Integrante A

1. abrir `/agent`;
2. pulsar **Nueva conversación**;
3. pulsar **Cargar creación MFA**;
4. ejecutar.

Mostrar:

```text
STATUS: completed
INTENT: incident_create
INCIDENT: INC-xxxxx

TOOLS:
search_knowledge
create_incident
```

Señalar:

- respuesta grounded;
- cita `[S1]`;
- fuentes;
- plan completado;
- incidente creado.

No abrir todo el JSON salvo que el profesor lo pida.

## 7B — Turno 2

**Tiempo:** ~1:30  
**Orador:** Integrante B

Pulsar:

```text
Continuar seguimiento de INC-xxxxx
```

Ejecutar el follow-up.

Mostrar:

```text
STATUS: completed
INTENT: incident_note
INCIDENT: mismo INC-xxxxx

TOOLS:
search_incidents
append_incident_note
```

Luego mostrar:

```text
MEMORY > 0
EVIDENCE = 0
```

Explicación factual:

- el ID no fue reenviado;
- se recuperó desde memoria;
- no se necesitó RAG en el segundo turno;
- la operación escribió una nota sobre el mismo incidente.

---

# Diapositiva 8 — Evidencia técnica y cierre

**Tiempo:** 0:45  
**Oradores:** ambos

## Mostrar

```text
242 tests passed
20 warnings deprecación conocidos
pip check: OK
compileall: OK
git diff --check: OK
```

Live validado:

```text
✓ RAG real
✓ FAISS / 47 chunks
✓ Gemini
✓ CrewAI hierarchical
✓ API agentic
✓ SQLite
✓ MemoryWriteBack
✓ follow-up multi-turno
✓ UI agentic
```

## Limitaciones factuales

- dependencia de Gemini para generación/embeddings;
- posibles errores 503 del proveedor;
- FAISS y SQLite son locales;
- runtime principal y CrewAI son caminos separados.

## Cierre

**LA CONCLUSIÓN ORAL DEBE SER FORMULADA POR EL EQUIPO SIN IA.**

Usar esta slide solo como apoyo visual de evidencia.

---

# Qué dejar fuera de las slides principales

No llenar la presentación con:

- listado de 242 tests;
- código fuente;
- JSON completo;
- todas las clases;
- explicación exhaustiva de EP1;
- historial de commits;
- warnings completos;
- detalles de instalación.

Eso queda como material de respaldo.

---

# Slides de respaldo para preguntas

Estas slides pueden existir después de la diapositiva 8 y no cuentan dentro del flujo normal de 10 minutos.

## Backup A — Runtime vs CrewAI

```text
Runtime UI/API:
FastAPI
→ AgentService
→ RuleBasedPlanner
→ AdaptiveOrchestrator

CrewAI:
Manager
→ workers
→ BaseTool adapters
```

Pregunta que resuelve:

```text
"¿La UI usa CrewAI?"
```

Respuesta factual:

```text
No. CrewAI está integrado y validado como runtime jerárquico separado.
```

## Backup B — Memoria

```text
Short-term:
mensajes recientes

Long-term:
eventos persistidos

Semantic:
recuperación por embeddings/similitud
```

Pregunta que resuelve:

```text
"¿Cómo recuerda el incidente?"
```

## Backup C — Seguridad

```text
Pydantic validation
max_iterations
RAG abstention
write blocking
incident existence validation
conversation isolation
no arbitrary SQL
```

## Backup D — Evidencia de pruebas

```text
242 passed
```

Mostrar captura o terminal únicamente si se solicita.

---

# Preguntas técnicas probables

## Puede responderse con hechos del sistema

### ¿El endpoint /api/agent usa CrewAI?

```text
No. Usa AgentService + RuleBasedPlanner + AdaptiveOrchestrator.
CrewAI se validó de forma separada mediante adapters.
```

### ¿Qué diferencia hay entre memoria short-term y semantic memory?

```text
Short-term mantiene contexto conversacional reciente.
SemanticMemory recupera eventos persistentes relevantes mediante similitud.
```

### ¿Qué pasa si no hay incidente en memoria?

```text
El sistema responde needs_clarification y solicita el identificador.
No ejecuta una escritura sin contexto resuelto.
```

### ¿Qué pasa si el RAG no encuentra evidencia?

```text
Puede responder abstained y bloquear una escritura que dependa de esa evidencia.
```

### ¿Cómo controlan loops?

```text
AgentState incluye max_iterations y el runtime registra iteration_count.
```

### ¿Dónde persisten los incidentes?

```text
SQLite, mediante IncidentRepository.
```

### ¿Por qué el segundo turno tiene cero fuentes?

```text
Porque el follow-up usa memoria + tools operacionales y no necesita volver a consultar conocimiento documental.
```

## Preguntas cuya respuesta debe preparar el equipo sin IA

- ¿Por qué eligieron CrewAI?
- ¿Por qué eligieron un planner determinista?
- ¿Por qué SQLite?
- ¿Por qué separaron memoria y planificación de CrewAI?
- ¿Por qué esta arquitectura es adecuada para NovaTech?
- ¿Qué mejorarían en una siguiente versión?
- ¿Qué aprendieron?
- ¿Cuál fue la contribución individual de cada integrante?

---

# Preflight de presentación

Antes de entrar a la sala:

```bash
cd ~/proyectos/KnowledgeFlow-Agent
source .venv/bin/activate

git status

test -f vectorstore/index.faiss && echo "FAISS OK"
test -f vectorstore/documents.json && echo "MANIFEST OK"

ss -ltnp | grep ':8000' || true
```

Runtime recomendado:

```bash
GEMINI_CHAT_MODEL=gemini-3.5-flash-lite \
uvicorn app.main:app --reload --port 8000
```

Abrir previamente:

```text
http://127.0.0.1:8000/agent
```

No ejecutar una consulta de prueba inmediatamente antes de la demo si no es necesario.

---

# Evidencia de respaldo

```text
docs/architecture/ep2-agent-architecture.md
docs/evidence/ep2-agent-demo-evidence.md
docs/evidence/ep2-demo-runbook.md
docs/report/ep2-report-outline.md
README.md
```

La presentación debe usar la evidencia para respaldar lo explicado, pero las justificaciones y conclusiones deben ser formuladas por los integrantes.
