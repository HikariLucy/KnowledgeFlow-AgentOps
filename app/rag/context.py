"""Context builder and citation extraction/validation utilities for RAG."""

import re
from typing import List, Set, Tuple
from app.rag.schemas import SearchResult, SourceReference, SourceType


def build_rag_context(
    search_results: List[SearchResult],
) -> Tuple[str, List[SourceReference]]:
    """Transform a list of SearchResult objects into structured context and SourceReferences.

    Assigns dynamic turn identifiers [S1], [S2]... [SN] to each retrieved chunk.

    Args:
        search_results: List of SearchResult items ordered by relevance.

    Returns:
        Tuple of (formatted_context_string, list_of_source_references).
    """
    if not search_results:
        return "", []

    context_blocks: List[str] = []
    source_references: List[SourceReference] = []

    for idx, res in enumerate(search_results, start=1):
        source_id = f"S{idx}"
        meta = res.document.metadata or {}

        file_name = str(meta.get("file_name", "documento"))
        source_type: SourceType = meta.get("source_type", "internal")  # type: ignore
        chunk_idx = meta.get("chunk_index")
        content = res.document.page_content.strip()

        # Build SourceReference
        ref = SourceReference(
            id=source_id,
            file_name=file_name,
            source_type=source_type,
            chunk_index=int(chunk_idx) if chunk_idx is not None else None,
            score=round(float(res.score), 4),
        )
        source_references.append(ref)

        # Build structured context block
        block = (
            f"[{source_id}]\n"
            f"source_type: {source_type}\n"
            f"file_name: {file_name}\n"
            f"chunk_index: {chunk_idx if chunk_idx is not None else 'N/A'}\n"
            f"score: {res.score:.4f}\n"
            f"content:\n{content}"
        )
        context_blocks.append(block)

    formatted_context = "\n\n---\n\n".join(context_blocks)
    return formatted_context, source_references


def extract_citations_from_text(text: str) -> List[str]:
    """Extract citation IDs (e.g. ['S1', 'S2']) from text using regex.

    Args:
        text: Generated response text.

    Returns:
        Ordered, deduplicated list of citation IDs found in the text.
    """
    if not text:
        return []

    # Match patterns like [S1], [S2], [S10]
    matches = re.findall(r"\[S(\d+)\]", text)
    seen: Set[str] = set()
    citations: List[str] = []

    for num in matches:
        cid = f"S{num}"
        if cid not in seen:
            seen.add(cid)
            citations.append(cid)

    return citations


def validate_citations(
    text: str,
    valid_source_ids: Set[str],
) -> Tuple[bool, List[str], List[str]]:
    """Validate citations against available source IDs.

    Args:
        text: Generated response text.
        valid_source_ids: Set of valid source IDs present in context (e.g. {'S1', 'S2', 'S3', 'S4'}).

    Returns:
        Tuple of (is_valid, valid_citations_found, phantom_citations_found).
    """
    found_citations = extract_citations_from_text(text)
    valid_citations: List[str] = []
    phantom_citations: List[str] = []

    for cid in found_citations:
        if cid in valid_source_ids:
            valid_citations.append(cid)
        else:
            phantom_citations.append(cid)

    # Valid if no phantom citations AND at least 1 valid citation when sources exist
    is_valid = (len(phantom_citations) == 0) and (
        len(valid_citations) > 0 or len(valid_source_ids) == 0
    )
    return is_valid, valid_citations, phantom_citations
