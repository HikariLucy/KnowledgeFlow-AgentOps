# EP2 Agent Demo Evidence

## Purpose

This document records reproducible implementation evidence for the KnowledgeFlow Agent EP2 demo. It is factual execution evidence only; it does not replace the team's own technical analysis, justification, conclusions, or personal reflections.

## Validated baseline

Latest fully validated local suite:

```text
242 passed
20 dependency deprecation warnings
pip check: No broken requirements found
compileall: OK
git diff --check: OK
working tree: clean
```

The warnings originate from FastAPI/Starlette and CrewAI deprecation notices and are not test failures.

## Live RAG evidence

The production RAG pipeline was rebuilt locally with:

```text
Documents loaded: 8
Chunks generated: 47
Internal chunks: 13
External chunks: 34
Embedding model: gemini-embedding-2
Embedding dimension: 768
Vector store: FAISS / cosine similarity
```

A live MFA query returned:

```text
abstained: false
citation: S1
primary source: faq_interna.txt
```

## CrewAI hierarchical evidence

A live CrewAI smoke validated:

```text
process: Process.hierarchical
manager tools: []
workers:
  - Knowledge Agent
  - Operations Agent
knowledge tool calls: 3
incidents created: 0
result: PASS
```

A subsequent CrewAI + real RAG E2E run validated:

```text
knowledge calls: 2
non-abstained RAG results: 2
sources:
  - faq_interna.txt
  - politica_accesos.md
  - procedimiento_incidentes.md
citations: S1
incidents created: 0
result: PASS
```

## API agent evidence

Endpoint:

```text
POST /api/agent
```

A live knowledge query returned HTTP 200 and exposed structured trace data:

```text
status: completed
intent: knowledge_query
plan:
  - Consultar base de conocimiento
tool_calls:
  - search_knowledge
sources: 4
citations: S1
iteration_count: 1
```

## Multi-turn write + memory evidence

### Turn 1 — knowledge + incident creation

A live agentic execution performed:

```text
intent: incident_create
plan:
  1. Consultar conocimiento aplicable
  2. Validar información mínima del incidente
  3. Crear incidente

tool_calls:
  - search_knowledge
  - create_incident
```

The visual demo produced incident:

```text
INC-00007
```

The final response preserved both the grounded RAG answer and the operational result:

```text
[grounded MFA procedure with citation S1]

Incidente creado: INC-00007.
```

The UI then exposed a guided action:

```text
Continuar seguimiento de INC-00007
```

The action preserves the current `conversation_id` and prepares a note follow-up without resending the incident identifier.

### Turn 2 — memory-resolved follow-up

The second turn used:

```text
message:
  Agrega que la identidad ya fue validada.

append_incident_note:
  note: Identidad del usuario validada.
```

The user did not resend `INC-00007`.

Observed result:

```text
status: completed
intent: incident_note
incident_id: INC-00007
plan:
  1. Localizar incidente
  2. Agregar nota de seguimiento
tool_calls:
  - search_incidents
  - append_incident_note
output:
  Seguimiento agregado a INC-00007.
```

The memory panel exposed both short-term conversational context and persistent semantic memories. The planner selected the most recent relevant incident and resolved `INC-00007`.

No RAG search was executed during this follow-up:

```text
sources: 0
tool_calls:
  - search_incidents
  - append_incident_note
```

This confirms that the second turn was resolved through workflow memory and operational tools rather than by repeating the documentary retrieval step.

## Adaptive behavior observed

The implementation has live or offline evidence for these controlled outcomes:

```text
1. knowledge_query
   -> search_knowledge

2. incident_create
   -> search_knowledge
   -> create_incident

3. incident_note with memory
   -> search_incidents
   -> append_incident_note

4. incident_note without resolvable context
   -> needs_clarification
   -> no accidental RAG query
   -> no write

5. RAG abstention during a dependent write flow
   -> write is blocked
```

## UI evidence

Route:

```text
GET /agent
```

The workspace exposes:

- stable `conversation_id`;
- execution mode selection;
- documentary scope;
- typed write payloads;
- status and intent;
- incident identifier;
- iteration count;
- completed plan;
- tool calls;
- recovered memory;
- documentary sources;
- operational observations;
- full JSON trace;
- guided multi-turn incident follow-up.

The original EP1 RAG interface remains available at `GET /`.

## Recommended clean presentation sequence

For the classroom demo, use a fresh conversation to avoid showing older test incidents in the memory panel:

```text
1. Open /agent.
2. Click "Nueva conversación".
3. Click "Cargar creación MFA".
4. Execute once.
5. Show:
   - grounded answer + citation;
   - incident ID;
   - plan;
   - search_knowledge + create_incident;
   - sources.
6. Click "Continuar seguimiento de INC-xxxxx".
7. Execute the prepared follow-up once.
8. Show:
   - same incident ID;
   - incident_note intent;
   - search_incidents + append_incident_note;
   - recovered memory;
   - zero documentary sources in the second turn.
```

## External-provider contingency

Gemini can occasionally return transient HTTP 503 high-demand responses. For the demo, `gemini-3.5-flash-lite` has been used successfully as a temporary runtime override without changing the main project configuration:

```bash
GEMINI_CHAT_MODEL=gemini-3.5-flash-lite \
uvicorn app.main:app --reload --port 8000
```

This keeps the local application configuration intact while reducing the risk of a provider-side high-demand failure during the demonstration.
