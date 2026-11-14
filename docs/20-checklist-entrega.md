# Checklist de entrega — EP3 KnowledgeFlow AgentOps

## Bloque técnico (verificado)

- [x] Código base EP1/EP2 preservado (`app/rag/`, `app/agentic/`, `app/tools/`, `app/memory/`, `app/storage/`).
- [x] Instrumentación y trazabilidad JSON (`app/observability/telemetry.py`, `middleware.py`).
- [x] Almacenamiento SQLite acotado y API administrativa protegida (`app/observability/store.py`, `app/api/observability_routes.py`).
- [x] Dashboard web propio en `/dashboard` validado visualmente en Chromium/Playwright (`docs/14-dashboard-web.md`, `docs/15-validacion-visual.md`).
- [x] Benchmark experimental reproducible offline con JSON/CSV (`app/evaluation/agentops_*.py`, `evaluation/agentops/dataset_v1.json`, `docs/16-benchmark-experimental.md`).
- [x] Auditoría de seguridad integral documentada (`docs/17-auditoria-seguridad.md`).
- [x] Suite Python offline y JS aprobadas sin llamadas a red externa.
- [x] Sin secretos, `.env`, ni bases SQLite operacionales en el repositorio Git.

## Bloque académico y operativo (pendiente del equipo)

- [ ] Confirmar con el docente la sigla oficial vigente (**ISY1010** vs **ISY0101**) y fecha/canal de entrega (AVA y correo).
- [ ] Revisar y completar el informe de máximo **5 páginas** (`docs/18-evidencias-ep3.md` como base): redactar **conclusiones**, **justificaciones técnicas propias**, **reflexiones individuales** y **declaración de uso de IA**.
- [ ] Revisar Pull Request en GitHub (`feat/observability` → `main`) y resolver manualmente las diferencias en `README.md` y `docs/05-roadmap.md` con `origin/main`.
- [ ] Ensayar demostración grupal (10 min demo + 10 min preguntas) con `docs/19-guion-demostracion.md`.
- [ ] Exportar PDF final del informe y verificar enlaces del repositorio antes de subir la entrega.
