"""Offline unit tests to verify documentation portability, rubric alignment, and neutral claims."""

from pathlib import Path
import pytest

DOCS_DIR = Path(__file__).resolve().parent.parent / "docs"
README_FILE = Path(__file__).resolve().parent.parent / "README.md"


def test_docs_do_not_contain_absolute_local_paths():
    """Verify that no markdown or mmd files in docs/ or README.md contain absolute local URLs."""
    disallowed_patterns = [
        "file:///",
        "C:\\Users\\",
        "c:/Users/",
        "KnowledgeFlow%20RAG",
    ]

    all_files = list(DOCS_DIR.rglob("*.md")) + list(DOCS_DIR.rglob("*.mmd")) + [README_FILE]
    assert len(all_files) >= 7

    for file_path in all_files:
        content = file_path.read_text(encoding="utf-8")
        for pattern in disallowed_patterns:
            assert pattern not in content, (
                f"File '{file_path.name}' contains disallowed local path pattern: '{pattern}'"
            )


def test_docs_do_not_contain_absolute_claims_or_invalid_terms():
    """Verify that no docs contain exaggerated or absolute claims."""
    forbidden_terms = [
        "ÓPTIMO EXPERIMENTAL",
        "100% de los módulos",
        "erradicando alucinaciones",
        "impidiendo secuestro",
        "autorreparación determinista",
    ]

    all_files = list(DOCS_DIR.rglob("*.md")) + list(DOCS_DIR.rglob("*.mmd"))

    for file_path in all_files:
        content = file_path.read_text(encoding="utf-8")
        for term in forbidden_terms:
            assert term not in content, (
                f"File '{file_path.name}' contains forbidden absolute phrase: '{term}'"
            )
