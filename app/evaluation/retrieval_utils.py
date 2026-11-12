"""Retrieval evaluation utilities, including raw pre-threshold balanced search."""

import math
from typing import List

from app.rag.retriever import Retriever
from app.rag.schemas import SearchResult


def retrieve_balanced_raw(
    retriever: Retriever,
    query: str,
    top_k: int = 4,
) -> List[SearchResult]:
    """Perform balanced dual retrieval across internal and external sources without threshold filtering.

    Used specifically for isolated retrieval evaluation (Hit@K, MRR, Expected Source Recall@K)
    to measure pure semantic retrieval before threshold abstention cutoff.

    Args:
        retriever: Initialized Retriever instance.
        query: User query string.
        top_k: Total number of results to return.

    Returns:
        List of SearchResult items up to top_k, balanced across internal and external sources.
    """
    if top_k <= 0:
        return []

    quota_internal = math.ceil(top_k / 2)
    quota_external = top_k - quota_internal

    raw_internal = retriever.search(query, k=top_k, source_type="internal")
    raw_external = retriever.search(query, k=top_k, source_type="external")

    selected_internal = raw_internal[:quota_internal]
    selected_external = raw_external[:quota_external]

    # Fill deficit if one subset has fewer items
    int_deficit = quota_internal - len(selected_internal)
    ext_deficit = quota_external - len(selected_external)

    if int_deficit > 0 and len(raw_external) > quota_external:
        selected_external = raw_external[: quota_external + int_deficit]
    elif ext_deficit > 0 and len(raw_internal) > quota_internal:
        selected_internal = raw_internal[: quota_internal + ext_deficit]

    combined = selected_internal + selected_external
    combined.sort(key=lambda x: x.score, reverse=True)

    return combined[:top_k]
