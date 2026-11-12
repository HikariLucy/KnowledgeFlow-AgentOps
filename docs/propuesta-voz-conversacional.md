# Propuesta: Conversación por Voz Gratuita para KnowledgeFlow RAG

> **Estado**: Prototipo / Propuesta en evaluación
> **Autor**: Dhani Amit Egueta Ríos (LASC Sentinel)
> **Revisión**: Jesús (compañero de equipo)
> **Fecha**: 2026-09-01

---

## 1. Idea central

Que el asistente **KnowledgeFlow RAG** no solo se consulte por texto (web / CLI / API), sino que puedas **hablarle y que te responda hablado**, en un diálogo natural, **gratis**, y con **más contexto del que da una IA web** (porque responde sobre la base de conocimiento del proyecto con citas verificables).

El flujo sería:

```text
Tú hablas ──► Whisper (STT: voz → texto)
                 │
                 ▼
        KnowledgeFlow RAG (respuesta con contexto documental + citas [S#])
                 │
                 ▼
        Edge TTS (TTS: texto → voz) ──► Te responde hablado
```

**Gratis**: Whisper local o Groq (free tier), Gemini embeddings y respuestas con cuota gratuita, y Edge TTS de Microsoft (sin costo).

---

## 2. Qué ya existe (de dónde sale la propuesta)

La funcionalidad ya existe como **prototipo funcional** en `GipSik-Unifier/gui/app_unificada.py` (modo "LASC UNIFICADO – Voz → Agente"):

- Graba el micrófono en chunks de 5s y **transcribe en un hilo aparte** sin perder audio entre chunks.
- **Múltiples motores de transcripción** conmutables:
  - **Local GPU**: Whisper `large-v3-turbo`, `small` (faster-whisper).
  - **Local CPU**: Whisper `base`, `tiny` (funcionan sin GPU).
  - **Nube**: Groq API `whisper-large-v3` (transcripción de alta calidad sin GPU local).
- **Detección automática** de servidores Whisper remotos en la red (por puerto y latencia).
- Envía el texto transcrito al agente y **lee la respuesta con Edge TTS** (`edge-tts`, voz `es-CL-CatalinaNeural`), con fallback a Piper (local) y ElevenLabs (avanzado).
- Conversación acumulativa (mantiene historial) + botones para generar, copiar y guardar prompts optimizados.

También existe `GipSik-Unifier/tts/cliente_tts_gui_serv_A_B.py`: cliente TTS de escritorio que manda texto a un servidor y reproduce la voz (Edge-TTS / ElevenLabs, con velocidad ajustable).

---

## 3. Cómo se integraría en KnowledgeFlow RAG

En lugar de que la consulta entre por el endpoint `POST /api/query`, entraría por voz:

| Componente | Pieza actual | Propuesta en KnowledgeFlow |
|-----------|--------------|------------------------------|
| **Entrada de voz** | Micrófono + PyAudio (chunks 5s) | Mismo patrón, reutilizable |
| **STT (voz → texto)** | Whisper local/Groq | Conecta al `Retriever` de KnowledgeFlow |
| **Respuesta** | LASC Sentinel (pool de APIs) | `RAGPipeline.run(query)` con citas `[S#]` |
| **TTS (texto → voz)** | Edge TTS / Piper / ElevenLabs | Edge TTS (gratis) para responder hablado |
| **UI** | Tkinter `app_unificada.py` | Se añade un modo voz a la UI web de KnowledgeFlow |

La ventaja: la respuesta ya no es "memoria general de la IA", sino que se fundamenta en los documentos del proyecto y muestra de dónde salió cada afirmación (trazabilidad `[S1]..[SN]`).

---

## 4. Requisitos y consideraciones (importante)

- **Transcripción local sin GPU**: Whisper `base`/`tiny` funcionan en CPU pero con **menor calidad de transcripción** (más errores en acentos, ruido y tecnicismos). Para mejor calidad sin GPU se recomienda **Groq API** (whisper-large-v3, free tier) o un servidor remoto con GPU.
- **Sin dependencia de pago**: Edge TTS es gratuito; las APIs de Gemini/Groq tienen cuotas gratuitas razonables para demostración.
- **Latencia**: transcripción local en CPU es más lenta; el patrón de chunks de 5s ya minimiza la espera.
- **Micrófono**: requiere PyAudio y permisos de audio en el SO.
- **Prototipo**: la UI es Tkinter de escritorio; requiere pulido (manejo de errores, indicadores visuales, prueba en distintos micrófonos).

---

## 5. Mejoras propuestas (es un prototipo)

1. Portar la funcionalidad de voz a la **UI web** de KnowledgeFlow (WebAudio + MediaRecorder → `/api/transcribe` → RAG → `/api/tts`).
2. Exponer endpoints REST propios: `POST /api/transcribe` (recibe WAV, devuelve texto) y `POST /api/tts` (recibe texto, devuelve audio).
3. **VAD (Voice Activity Detection)** para detectar silencio y cortar automáticamente.
4. Selector de voz y velocidad Edge TTS en la interfaz.
5. Historial de conversación por voz con persistencia (guardar logs como ya hace el prototipo).
6. Pruebas automatizadas para el flujo voz (mock de Whisper y Edge TTS).

---

## 6. Criterios de éxito (para saber que funciona)

- Hablo y el sistema me transcribe correctamente (según motor elegido).
- El RAG responde fundamentado con citas `[S#]` sobre la base de conocimiento.
- La respuesta se escucha por Edge TTS en español.
- Todo el flujo se completa sin pagar (solo cuotas gratuitas).
- Si no hay GPU: funciona con modelos `base`/`tiny` o Groq.

---

*Propuesta creada para revisión del equipo. El código fuente del prototipo vive en `GipSik-Unifier/`.*
