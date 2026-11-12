# Acta técnica de migración de EP2 a AgentOps

- **Origen:** `https://github.com/HikariLucy/KnowledgeFlow-Agent`, rama `main`.
- **Commit fuente:** `53efc993f1edac638f364aac7e6d34982f023bb6`.
- **Destino:** `https://github.com/HikariLucy/KnowledgeFlow-AgentOps`, rama `main`.
- **Fecha de preparación:** 12 de noviembre de 2026.
- **Método:** importación de los contenidos de los archivos de código y documentación mediante la API de GitHub, en commits sucesivos.
- **Cobertura:** 141 blobs de origen importados, incluyendo 103 archivos Python, pruebas, HTML/JS/CSS, documentos, datasets, scripts y configuración.
- **Verificación:** comparación del identificador SHA de cada blob origen/destino; **141/141 coincidencias**. El README original se guardó en `docs/legacy/README_EP2.md` y se creó un README nuevo para EP3.
- **Aclaración:** esta técnica **no preserva el historial completo de commits** de EP2 dentro del repositorio nuevo. El repositorio original permanece disponible y sin modificaciones.
- **Pruebas de ejecución:** **no se han reejecutado** las pruebas de regresión en el nuevo repositorio. La cifra histórica de 242 pruebas está documentada por EP2 y debe verificarse de nuevo.
- **Condición de seguridad:** no se importaron archivos binarios porque el árbol origen no incluía ninguno. No se copiaron `.env`, bases SQLite reales ni índices FAISS, pues no formaban parte del árbol versionado.

## Revalidación solicitada

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
pytest -q
```

Registrar resultados en `docs/10-auditoria-tecnica.md` después de ejecutarlos. El proyecto fuente sigue siendo la referencia histórica de EP2.
