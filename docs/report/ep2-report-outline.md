# Estructura de Informe EP2 — KnowledgeFlow Agent

> **Documento de trabajo para el equipo.** Esta estructura está alineada con la pauta oficial de la EP2 y con la implementación real del repositorio. No contiene conclusiones, reflexiones personales ni justificaciones técnicas redactadas por IA. Esas partes deben ser escritas por el equipo.

## Restricción formal

La pauta exige un informe escrito de **máximo cinco páginas**, en Word o PDF, que integre de manera estructurada los aspectos clave del trabajo.

Además, el repositorio debe contener:

- código fuente;
- documentación de funcionamiento;
- bocetos/diagramas de diseño;
- evidencia de pruebas;
- README con instrucciones precisas para ejecutar y validar el sistema.

## Distribución propuesta de las 5 páginas

### Página 1 — Problema, objetivo y evolución EP1 → EP2

#### 1. Contexto del problema

Contenido factual sugerido:

- caso organizacional simulado: NovaTech SpA;
- EP1 resolvía recuperación documental mediante RAG;
- EP2 amplía esa capacidad hacia un agente capaz de ejecutar acciones operacionales;
- necesidad de integrar consulta, escritura, memoria, planificación y trazabilidad.

#### 2. Objetivo del agente

Elementos observables que pueden describirse:

- consultar conocimiento;
- crear/buscar/actualizar incidentes;
- mantener continuidad entre turnos;
- adaptar el flujo según evidencia y contexto;
- exponer trazabilidad del plan y las tools.

#### 3. Evolución arquitectónica

Diagrama compacto recomendado:

```text
EP1
Usuario → RAGPipeline → FAISS/Gemini → Respuesta con citas

EP2
Usuario → Planner/Orchestrator
        → search_knowledge → RAG
        → incident tools → SQLite
        → MemoryWriteBack
        → respuesta + estado + trazabilidad
```

**Evidencia de repositorio:**

```text
docs/architecture/ep2-agent-architecture.md
README.md
```

---

### Página 2 — Diseño e implementación del agente

#### 4. Componentes principales

Describir objetivamente:

```text
AgentService
RuleBasedPlanner
AdaptiveOrchestrator
AgentState
KnowledgeRAGTool
CreateIncidentTool
SearchIncidentsTool
AppendIncidentNoteTool
Pydantic schemas
SQLite / IncidentRepository
```

#### 5. Herramientas configuradas

Tabla compacta sugerida:

| Tool | Tipo | Función |
|---|---|---|
| `search_knowledge` | Consulta | Recupera evidencia mediante RAG |
| `create_incident` | Escritura | Crea incidente validado |
| `search_incidents` | Consulta operacional | Localiza incidentes |
| `append_incident_note` | Escritura | Agrega seguimiento sin sobrescribir historial |

#### 6. Framework agentic

Hechos que pueden reportarse:

- CrewAI 1.15.22 está integrado mediante adapters;
- existe `Process.hierarchical`;
- Manager sin tools operacionales;
- Knowledge Agent limitado a `search_knowledge`;
- Operations Agent limitado a tools de incidentes;
- `memory=False` y `planning=False` en CrewAI porque el runtime principal usa componentes propios para esas capacidades;
- el endpoint `POST /api/agent` no pasa actualmente por CrewAI.

#### 7. Espacio reservado para justificación técnica del equipo

**REDACTAR SIN IA.**

El equipo debe explicar con sus propias palabras por qué eligió:

- CrewAI;
- planner determinista;
- separación de tools;
- Pydantic;
- SQLite;
- FastAPI;
- RAG como tool reutilizable.

Esta sección es crítica para IE9.

---

### Página 3 — Memoria, recuperación de contexto y planificación

#### 8. Memoria de corto plazo

Hechos:

- `ShortTermMemory`;
- ventana configurable;
- aislamiento por `conversation_id`;
- mensajes user/assistant recientes.

#### 9. Memoria persistente y semántica

Hechos:

- `LongTermMemoryStore` sobre SQLite;
- `SemanticMemory`;
- embeddings;
- similitud coseno;
- metadata con `incident_id`;
- recuperación filtrada por conversación.

#### 10. MemoryWriteBack

Flujo factual:

```text
resultado de ejecución
→ MemoryWriteBack
→ short-term
→ long-term/semantic para eventos operacionales relevantes
```

No se persiste cada consulta read-only como evento operacional.

#### 11. Planificación

Intenciones implementadas:

```text
knowledge_query
incident_create
incident_search
incident_note
```

Ejemplo de plan de creación:

```text
1. Consultar conocimiento aplicable
2. Validar información mínima
3. Crear incidente
```

Prioridad de resolución del incidente:

```text
1. ID explícito
2. AgentState
3. short-term más reciente
4. long-term más reciente
```

#### 12. Evidencia de continuidad

Caso validado:

```text
Turno 1:
RAG → create_incident → INC-00007

Turno 2:
"Agrega que la identidad ya fue validada."
→ memoria recupera INC-00007
→ search_incidents
→ append_incident_note
```

El usuario no reenvía el identificador.

---

### Página 4 — Orquestación, decisiones adaptativas y arquitectura

#### 13. Diagrama principal

Usar la versión compacta de:

```text
docs/architecture/ep2-agent-architecture.mmd
```

Componentes mínimos a mostrar:

```text
UI
→ FastAPI
→ AgentService
→ Planner
→ Orchestrator
→ Tools
   ├─ RAG / FAISS / Gemini
   └─ IncidentRepository / SQLite
→ MemoryWriteBack
→ Memoria
```

#### 14. Comportamiento adaptativo

Tabla factual:

| Condición | Comportamiento |
|---|---|
| Consulta documental | `search_knowledge` |
| Crear incidente | `search_knowledge → create_incident` |
| Follow-up con memoria | `search_incidents → append_incident_note` |
| Follow-up sin contexto | `needs_clarification` |
| RAG abstiene | escritura dependiente bloqueada |
| Componente ausente | `failed` controlado |

#### 15. Trazabilidad

`AgentResponse` expone:

```text
status
intent
plan
required_tools
tool_calls
completed_steps
memory_context
sources
observations
incident_id
iteration_count
output
```

La UI permite visualizar estos datos sin exponer chain-of-thought.

#### 16. Espacio reservado para explicación de orquestación del equipo

**REDACTAR SIN IA.**

El equipo debe explicar con sus propias palabras:

- cómo se relacionan planner y orchestrator;
- cómo se decide cuándo leer y cuándo escribir;
- cómo la memoria influye en el segundo turno;
- por qué se separó el runtime principal de la validación CrewAI.

---

### Página 5 — Pruebas, evidencia, limitaciones, IA y cierre

#### 17. Validación técnica

Último estado confirmado:

```text
242 passed
20 warnings de deprecación
pip check: No broken requirements found
compileall: OK
git diff --check: OK
working tree: clean
```

Evidencia live:

- RAG real: 8 documentos / 47 chunks;
- embeddings `gemini-embedding-2`, 768 dimensiones;
- consulta MFA grounded con `S1`;
- CrewAI jerárquico validado;
- API `POST /api/agent` validada;
- creación de incidente;
- continuidad multi-turno;
- UI agentic;
- follow-up sin reenviar ID.

#### 18. Limitaciones observables

Se pueden mencionar como hechos:

- dependencia externa de Gemini para embeddings/generación;
- posibilidad de HTTP 503 por alta demanda;
- FAISS y SQLite son locales;
- el runtime principal `/api/agent` y CrewAI son caminos separados;
- la recuperación semántica de memoria actual está pensada para escala pequeña/demo;
- no existe remediación automática arbitraria;
- las operaciones de escritura están limitadas a tools tipadas.

#### 19. Uso de IA

La pauta exige declarar las herramientas de IA usadas y cómo se aplicaron.

El equipo debe completar una declaración factual propia, por ejemplo indicando:

```text
Herramienta:
Uso:
Contenido revisado/validado por:
```

No incluir afirmaciones falsas de autoría o revisión.

#### 20. Referencias APA

Incluir referencias de los frameworks y tecnologías realmente usados.

Candidatos a documentar:

- CrewAI;
- FastAPI;
- Pydantic;
- Google Gen AI SDK / Gemini;
- FAISS;
- documentación técnica utilizada.

Las referencias finales deben revisarse y formatearse en APA por el equipo.

#### 21. Conclusión y reflexiones

**NO REDACTAR CON IA.**

La pauta exige:

- conclusión propia del equipo;
- reflexión individual de cada integrante;
- sin apoyo de IA.

Reservar aquí el espacio necesario dentro de las cinco páginas.

---

# Matriz rápida pauta → evidencia

| Indicador | Evidencia disponible |
|---|---|
| IE1 Herramientas autónomas | `search_knowledge`, `create_incident`, `search_incidents`, `append_incident_note` |
| IE2 Frameworks | CrewAI + adapters + FastAPI/Pydantic |
| IE3 Memoria | ShortTermMemory + LongTermMemoryStore + MemoryWriteBack |
| IE4 Contexto semántico | SemanticMemory + embeddings + recuperación por conversation_id |
| IE5 Planificación | RuleBasedPlanner + planes explícitos + prioridad de incident ID |
| IE6 Informe/diagramas | arquitectura EP2 + README + evidencia + runbook |
| IE7 Decisiones adaptativas | abstención, aclaración, create flow, follow-up por memoria |
| IE8 Diagrama + README | `ep2-agent-architecture.*` + README |
| IE9 Justificación | **debe redactarla el equipo** |
| IE10 Lenguaje técnico/evidencia | demo, 242 tests, fuentes, tool calls, memory trace |

---

# Material del repositorio a citar en el informe

```text
README.md
docs/architecture/ep2-agent-architecture.md
docs/architecture/ep2-agent-architecture.mmd
docs/evidence/ep2-agent-demo-evidence.md
docs/evidence/ep2-demo-runbook.md
tests/
app/agentic/
app/memory/
app/tools/
app/integrations/
```

# Recomendación de densidad

Para respetar el máximo de cinco páginas:

- usar un solo diagrama principal;
- una tabla de tools;
- una tabla de decisiones adaptativas;
- una tabla mínima de evidencia;
- evitar capturas grandes dentro del informe;
- dejar las capturas completas y JSON en GitHub;
- referenciar README/evidence docs en vez de copiar todo;
- reservar espacio real para la conclusión y reflexiones obligatorias del equipo.
