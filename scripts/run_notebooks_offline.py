"""Validate and sequentially execute EFT Jupyter notebooks in offline mode."""

from __future__ import annotations

from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import sys
from typing import Any


EXPECTED_NOTEBOOKS = (
    "00_knowledgeflow_eft_principal.ipynb",
    "01_ep1_rag_y_prompts.ipynb",
    "02_ep2_agente_herramientas_memoria.ipynb",
    "03_ep3_observabilidad_benchmark_dashboard.ipynb",
)


def validate_notebook_schema(notebook_path: Path) -> dict[str, Any]:
    """Load and validate basic nbformat v4 + Colab compatibility."""
    data = json.loads(notebook_path.read_text(encoding="utf-8"))
    if data.get("nbformat") != 4:
        raise ValueError(f"{notebook_path.name}: expected nbformat == 4")
    metadata = data.get("metadata", {})
    if "kernelspec" not in metadata or "colab" not in metadata:
        raise ValueError(f"{notebook_path.name}: missing kernelspec or colab metadata")
    cells = data.get("cells")
    if not isinstance(cells, list) or not cells:
        raise ValueError(f"{notebook_path.name}: cells must be a non-empty list")
    return data


def execute_notebook_offline(notebook_path: Path, repo_root: Path) -> list[str]:
    """Execute all code cells of a notebook sequentially in an isolated namespace."""
    data = validate_notebook_schema(notebook_path)
    namespace: dict[str, Any] = {"__name__": "__main__"}
    outputs: list[str] = []

    old_cwd = Path.cwd()
    old_env_key = os.environ.pop("GEMINI_API_KEY", None)
    try:
        os.chdir(repo_root)
        if str(repo_root) not in sys.path:
            sys.path.insert(0, str(repo_root))

        for idx, cell in enumerate(data["cells"], start=1):
            if cell.get("cell_type") != "code":
                continue
            source = "".join(cell.get("source", []))
            if not source.strip():
                continue
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                exec(compile(source, f"{notebook_path.name}#cell-{idx}", "exec"), namespace)
            outputs.append(buffer.getvalue())

        if namespace.get("RUN_LIVE_GEMINI", False):
            raise AssertionError(f"{notebook_path.name}: RUN_LIVE_GEMINI must stay False by default")
    finally:
        os.chdir(old_cwd)
        if old_env_key is not None:
            os.environ["GEMINI_API_KEY"] = old_env_key

    return outputs


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    nb_dir = repo_root / "notebooks"
    for name in EXPECTED_NOTEBOOKS:
        path = nb_dir / name
        if not path.exists():
            raise FileNotFoundError(f"Missing expected notebook: {path}")
        outputs = execute_notebook_offline(path, repo_root)
        print(f"[OK] {name} ({len(outputs)} code cells executed offline)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
