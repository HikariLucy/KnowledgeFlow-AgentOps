"""Document loaders for internal and external knowledge sources."""

from pathlib import Path
from typing import List, Optional, Union
import logging

from langchain_core.documents import Document
from pypdf import PdfReader

from app.rag.schemas import SourceType

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".txt", ".md", ".pdf"}


def infer_source_type(file_path: Union[str, Path]) -> SourceType:
    """Infer whether a file belongs to 'internal' or 'external' sources based on its path.

    Raises:
        ValueError: If neither 'internal' nor 'external' is present in path parts.
    """
    path_obj = Path(file_path)
    parts = [part.lower() for part in path_obj.parts]
    if "internal" in parts:
        return "internal"
    if "external" in parts:
        return "external"
    raise ValueError(
        f"Cannot infer source_type for path '{file_path}'. "
        "Path must reside inside an 'internal' or 'external' directory, "
        "or source_type must be explicitly provided."
    )


def load_text_file(
    file_path: Path, source_type: Optional[SourceType] = None
) -> List[Document]:
    """Load content from a .txt or .md file with UTF-8 encoding (fallback to latin-1)."""
    resolved_source_type = source_type or infer_source_type(file_path)

    try:
        content = file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        content = file_path.read_text(encoding="latin-1")

    if not content.strip():
        return []

    metadata = {
        "source": str(file_path.as_posix()),
        "source_type": resolved_source_type,
        "file_name": file_path.name,
        "file_extension": file_path.suffix.lower(),
    }

    return [Document(page_content=content, metadata=metadata)]


def load_pdf_file(
    file_path: Path, source_type: Optional[SourceType] = None
) -> List[Document]:
    """Load pages from a .pdf file. Returns empty list if no extractable text is found."""
    resolved_source_type = source_type or infer_source_type(file_path)

    reader = PdfReader(str(file_path))
    documents: List[Document] = []

    for page_num, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        if text.strip():
            metadata = {
                "source": str(file_path.as_posix()),
                "source_type": resolved_source_type,
                "file_name": file_path.name,
                "file_extension": file_path.suffix.lower(),
                "page": page_num,
            }
            documents.append(Document(page_content=text, metadata=metadata))

    return documents


def load_document(
    file_path: Union[str, Path], source_type: Optional[SourceType] = None
) -> List[Document]:
    """Load a single supported document file (.txt, .md, .pdf).

    Args:
        file_path: Path to the document.
        source_type: Optional explicit source type ('internal' or 'external').

    Returns:
        List of LangChain Document objects.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the file extension is unsupported or source_type is invalid.
    """
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"Document file not found: {file_path}")

    ext = path.suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file extension '{ext}'. Supported extensions are: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )

    if source_type and source_type not in ("internal", "external"):
        raise ValueError(
            f"Invalid source_type '{source_type}'. Must be 'internal' or 'external'."
        )

    if ext in {".txt", ".md"}:
        return load_text_file(path, source_type)
    elif ext == ".pdf":
        return load_pdf_file(path, source_type)

    return []


def load_directory(
    directory_path: Union[str, Path], source_type: Optional[SourceType] = None
) -> List[Document]:
    """Recursively load all supported documents from a directory.

    Args:
        directory_path: Directory path to scan.
        source_type: Optional explicit source type ('internal' or 'external').

    Returns:
        List of loaded Document objects.
    """
    path = Path(directory_path)
    if not path.exists():
        raise FileNotFoundError(f"Directory not found: {directory_path}")
    if not path.is_dir():
        raise NotADirectoryError(f"Path is not a directory: {directory_path}")

    documents: List[Document] = []
    for item in sorted(path.rglob("*")):
        if item.is_file():
            ext = item.suffix.lower()
            if ext in SUPPORTED_EXTENSIONS:
                try:
                    docs = load_document(item, source_type=source_type)
                    documents.extend(docs)
                except Exception as e:
                    logger.warning("Could not load file %s: %s", item, e)
            else:
                logger.debug("Skipping unsupported file: %s", item)

    return documents


def load_knowledge_base(
    base_dir: Union[str, Path] = "knowledge"
) -> List[Document]:
    """Load all documents from both internal and external directories within base_dir.

    Args:
        base_dir: Path to base knowledge directory.

    Returns:
        List of all loaded Document objects.
    """
    base_path = Path(base_dir)
    documents: List[Document] = []

    internal_dir = base_path / "internal"
    if internal_dir.exists() and internal_dir.is_dir():
        documents.extend(load_directory(internal_dir, source_type="internal"))

    external_dir = base_path / "external"
    if external_dir.exists() and external_dir.is_dir():
        documents.extend(load_directory(external_dir, source_type="external"))

    return documents
