"""Tests for document loaders and metadata extraction."""

import io
from pathlib import Path
import pytest
from pypdf import PdfWriter

from app.rag.loaders import (
    load_document,
    load_directory,
    load_knowledge_base,
    infer_source_type,
    SUPPORTED_EXTENSIONS,
)


def test_infer_source_type():
    """Verify source_type inference from file path hierarchy."""
    assert infer_source_type("knowledge/internal/politica.md") == "internal"
    assert infer_source_type("knowledge/external/guia.txt") == "external"

    with pytest.raises(ValueError, match="Cannot infer source_type"):
        infer_source_type("some/other/path.md")


def test_load_document_with_explicit_source_type(tmp_path):
    """Verify explicit source_type overrides path inference."""
    custom_file = tmp_path / "custom_note.md"
    custom_file.write_text("Contenido personalizado", encoding="utf-8")

    docs = load_document(custom_file, source_type="external")
    assert len(docs) == 1
    assert docs[0].metadata["source_type"] == "external"


def test_load_internal_markdown_file():
    """Verify an internal .md file is loaded with full metadata."""
    file_path = Path("knowledge/internal/politica_accesos.md")
    docs = load_document(file_path)

    assert len(docs) == 1
    doc = docs[0]
    assert "NovaTech SpA" in doc.page_content
    assert doc.metadata["source_type"] == "internal"
    assert doc.metadata["file_name"] == "politica_accesos.md"
    assert doc.metadata["file_extension"] == ".md"
    assert doc.metadata["source"] == file_path.as_posix()


def test_load_external_text_file():
    """Verify an external .txt file is loaded with full metadata."""
    file_path = Path("knowledge/external/referencia_seguridad.txt")
    docs = load_document(file_path)

    assert len(docs) == 1
    doc = docs[0]
    assert "Cifrado en Transito" in doc.page_content
    assert doc.metadata["source_type"] == "external"
    assert doc.metadata["file_name"] == "referencia_seguridad.txt"
    assert doc.metadata["file_extension"] == ".txt"
    assert doc.metadata["source"] == file_path.as_posix()


def test_load_pdf_without_extractable_text_returns_empty_list(tmp_path):
    """Verify valid PDF without extractable text returns empty list."""
    pdf_path = tmp_path / "blank.pdf"

    # Create a blank PDF with no text
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    with open(pdf_path, "wb") as f:
        writer.write(f)

    docs = load_document(pdf_path, source_type="internal")
    assert docs == []


def test_load_empty_directory(tmp_path):
    """Verify loading an empty directory returns an empty list without crashing."""
    empty_dir = tmp_path / "empty_dir"
    empty_dir.mkdir()

    docs = load_directory(empty_dir)
    assert docs == []


def test_load_directory_ignores_unsupported_files(tmp_path):
    """Verify directory loading ignores unsupported file extensions."""
    test_dir = tmp_path / "mixed_dir"
    test_dir.mkdir()

    # Create supported and unsupported files
    (test_dir / "valid.txt").write_text("Texto soportado", encoding="utf-8")
    (test_dir / "ignored.exe").write_text("binario", encoding="utf-8")
    (test_dir / "data.csv").write_text("a,b,c", encoding="utf-8")

    docs = load_directory(test_dir, source_type="internal")
    assert len(docs) == 1
    assert docs[0].metadata["file_name"] == "valid.txt"


def test_load_document_raises_on_unsupported_file(tmp_path):
    """Verify load_document raises ValueError when file extension is not supported."""
    bad_file = tmp_path / "unsupported.csv"
    bad_file.write_text("col1,col2", encoding="utf-8")

    with pytest.raises(ValueError, match="Unsupported file extension"):
        load_document(bad_file)


def test_load_document_raises_on_missing_file():
    """Verify load_document raises FileNotFoundError for non-existent path."""
    with pytest.raises(FileNotFoundError):
        load_document("knowledge/internal/non_existent_file.md")


def test_load_directory_raises_on_missing_dir():
    """Verify load_directory raises FileNotFoundError for non-existent path."""
    with pytest.raises(FileNotFoundError):
        load_directory("knowledge/non_existent_dir")


def test_load_knowledge_base():
    """Verify load_knowledge_base loads internal and external demo datasets."""
    docs = load_knowledge_base("knowledge")
    assert len(docs) >= 5

    internal_docs = [d for d in docs if d.metadata["source_type"] == "internal"]
    external_docs = [d for d in docs if d.metadata["source_type"] == "external"]

    assert len(internal_docs) >= 3  # politica, procedimiento, faq
    assert len(external_docs) >= 2  # guia, referencia

    for doc in docs:
        assert doc.metadata["file_extension"] in SUPPORTED_EXTENSIONS
        assert "source" in doc.metadata
        assert "file_name" in doc.metadata
