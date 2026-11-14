"""Automated offline verification for EFT Jupyter/Colab notebooks."""

from pathlib import Path

from scripts.run_notebooks_offline import (
    EXPECTED_NOTEBOOKS,
    execute_notebook_offline,
    validate_notebook_schema,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
NOTEBOOKS_DIR = REPO_ROOT / "notebooks"


def test_eft_notebooks_exist_and_have_valid_schema() -> None:
    for name in EXPECTED_NOTEBOOKS:
        path = NOTEBOOKS_DIR / name
        assert path.exists(), f"Missing notebook: {path}"
        data = validate_notebook_schema(path)
        code_cells = [c for c in data["cells"] if c.get("cell_type") == "code"]
        assert len(code_cells) >= 2


def test_eft_principal_notebook_runs_sequentially_offline() -> None:
    path = NOTEBOOKS_DIR / "00_knowledgeflow_eft_principal.ipynb"
    outputs = execute_notebook_offline(path, REPO_ROOT)
    joined = "\n".join(outputs)
    assert "RUN_LIVE_GEMINI=False" in joined
    assert "MODO OFFLINE DETERMINISTA" in joined
    assert "Benchmark offline" in joined
    assert "Dashboard HTML status=200" in joined


def test_eft_modular_notebooks_run_sequentially_offline() -> None:
    for name in (
        "01_ep1_rag_y_prompts.ipynb",
        "02_ep2_agente_herramientas_memoria.ipynb",
        "03_ep3_observabilidad_benchmark_dashboard.ipynb",
    ):
        outputs = execute_notebook_offline(NOTEBOOKS_DIR / name, REPO_ROOT)
        assert len(outputs) >= 2
