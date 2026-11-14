# Guion de demostración EP3 — KnowledgeFlow AgentOps

Duración objetivo: **10 minutos de demostración + 10 minutos de preguntas** (según pauta referenciada en `docs/01-alcance-ep3.md`).

## Preparación previa (antes de presentar)

1. Confirmar entorno `.venv` instalado y `git status` limpio.
2. Definir contraseña local (≥32 caracteres ASCII) sin mostrarla en pantalla:

```bash
read -r -s -p 'Contraseña local del dashboard: ' OBS_DASHBOARD_PASSWORD
export OBS_DASHBOARD_PASSWORD
```

3. Iniciar servidor local en loopback:

```bash
OBS_DASHBOARD_ENABLED=true OBS_STORE_ENABLED=true OBS_ENABLED=true OBS_EXECUTION_MODE=offline \
  .venv/bin/python -m uvicorn app.main:app \
  --host 127.0.0.1 --port 8000 --no-access-log --no-proxy-headers
```

*(Si no se desea capturar tráfico nuevo durante la demo, usar `OBS_ENABLED=false` y un almacén poblado explícitamente; distinguir siempre datos `mock` de datos `offline`/`live`.)*

## Secuencia de demostración (10 min)

1. **Minuto 0–2 · Contexto y arquitectura:**
   - Mostrar `/` (Consulta RAG) y `/agent` (Agente con planificación, herramientas y memoria).
   - Navegar al enlace **Observabilidad** (`/dashboard`) y mostrar el diálogo de autenticación HTTP Basic (`observer`).
2. **Minuto 2–4 · Vista general y métricas:**
   - Mostrar filtros (`Modo`, `Período`, `Componente`, `Operación`, `Estado`), las 7 tarjetas KPI y la separación explícita entre `0` observado y `N/D`.
3. **Minuto 4–6 · Rendimiento y trazas:**
   - Mostrar gráficos SVG nativos (latencia en 24 intervalos, componentes, errores, herramientas, tokens).
   - Seleccionar un `Trace ID` en `Ejecuciones y eventos` para abrir el **Explorador de trazas** y mostrar la jerarquía de spans y advertencia de cobertura parcial.
4. **Minuto 6–8 · Benchmark experimental y calidad:**
   - Explicar la sección `05 / Calidad del agente` (`N/D` cuando no hay benchmark cargado).
   - Ejecutar en terminal el benchmark reproducible offline:
     ```bash
     .venv/bin/python -m app.evaluation.agentops_runner --mode offline --repeats 3 --output-dir /tmp/ao-demo
     ```
   - Mostrar los resultados reales (`19/20`, consistencia `1.0`) aclarando que son doubles offline, **no** Gemini live.
5. **Minuto 8–10 · Seguridad y pruebas:**
   - Mostrar intento sin credenciales (`401`) o desde `localhost` (`403`), y resumen de `docs/17-auditoria-seguridad.md`.
   - Ejecutar `node tests/dashboard_frontend.test.mjs` o mostrar salida de `scripts/run_tests_offline.py`.

## Posibles preguntas (10 min Q&A)

- ¿Por qué el dashboard muestra `N/D` en calidad sin benchmark? → Regla de no inferir calidad desde HTTP 200 o ausencia de errores.
- ¿Cómo se evita mezclar mocks con producción? → Partición obligatoria por `execution_mode` y etiqueta visible `MOCK · DATOS SINTÉTICOS / DOBLES`.
- ¿Cómo se protegen las credenciales? → `OBS_READ_KEY` nunca llega al navegador; `/dashboard` usa HTTP Basic independiente y solo acepta loopback.
