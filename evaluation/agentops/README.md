# Benchmark EP3 — AgentOps

Aquí se alojarán escenarios, fixtures offline y resultados agregados (versionados solo si están sanitizados).

Requisitos de registro de ejecución: `run_id`, `git_sha`, `timestamp`, `mode` (`offline/mock/live`), `synthetic`, `scenario`, `N`, `metrics`, `trace_id`, modelo/configuración. La ausencia de medida se representa como null.

Nunca subir credenciales, prompts sensibles, SQLite operacional, documentos privados ni logs JSONL completos. Reutilizar cuando corresponda la base `evaluation/dataset_verified.json`.
