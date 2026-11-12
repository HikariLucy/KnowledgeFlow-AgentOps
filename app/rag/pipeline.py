import math
from typing import TYPE_CHECKING, List, Optional

from app.core.config import Settings, get_settings
from app.rag.context import build_rag_context
from app.rag.generator import BaseRAGGenerator, GeminiRAGGenerator
from app.rag.retriever import Retriever
from app.rag.schemas import RAGAnswer, SearchResult, SourceScope

if TYPE_CHECKING:
    from app.agents.source_router import BaseSourceRouter


class RAGPipeline:
    """Orchestrates source routing, retrieval, evidence filtering, context building, and grounded generation."""

    def __init__(
        self,
        retriever: Retriever,
        router: Optional["BaseSourceRouter"] = None,
        generator: Optional[BaseRAGGenerator] = None,
        settings: Optional[Settings] = None,
    ):
        self.retriever = retriever
        self.settings = settings or get_settings()
        if router is None:
            from app.agents.source_router import GeminiSourceRouter

            self.router: "BaseSourceRouter" = GeminiSourceRouter(
                settings=self.settings
            )
        else:
            self.router = router

        self.generator = generator or GeminiRAGGenerator(settings=self.settings)

    def _retrieve_balanced_all(self, query: str, top_k: int) -> List[SearchResult]:
        """Perform balanced dual-source retrieval for source_scope='all'.

        Attempts to retrieve half internal and half external results, filling quotas
        if one source lacks sufficient evidence, and sorting final results by score descending.

        Args:
            query: User search query.
            top_k: Total desired Top-K items.

        Returns:
            List of SearchResult items up to top_k, sorted by score descending.
        """
        quota_int = math.ceil(top_k / 2)
        quota_ext = top_k - quota_int

        raw_int = self.retriever.search(query=query, k=top_k, source_type="internal")
        raw_ext = self.retriever.search(query=query, k=top_k, source_type="external")

        # Filter by similarity threshold
        min_sim = self.settings.rag_min_similarity
        valid_int = [r for r in raw_int if r.score >= min_sim]
        valid_ext = [r for r in raw_ext if r.score >= min_sim]

        selected_int = valid_int[:quota_int]
        selected_ext = valid_ext[:quota_ext]

        # Fill remaining slots from either side if one has fewer results than quota
        remaining_slots = top_k - (len(selected_int) + len(selected_ext))
        if remaining_slots > 0:
            if len(valid_int) > len(selected_int):
                selected_int.extend(
                    valid_int[len(selected_int) : len(selected_int) + remaining_slots]
                )
                remaining_slots = top_k - (len(selected_int) + len(selected_ext))

            if remaining_slots > 0 and len(valid_ext) > len(selected_ext):
                selected_ext.extend(
                    valid_ext[len(selected_ext) : len(selected_ext) + remaining_slots]
                )

        combined = selected_int + selected_ext
        # Sort combined results by score descending
        combined.sort(key=lambda x: x.score, reverse=True)
        return combined[:top_k]

    def run(
        self,
        query: str,
        source_scope: Optional[SourceScope] = None,
        top_k: Optional[int] = None,
    ) -> RAGAnswer:
        """Execute full RAG pipeline for a given user query.

        Args:
            query: User question string.
            source_scope: Optional manual override for source scope ('internal', 'external', 'all').
            top_k: Optional override for number of retrieved chunks (defaults to settings.retrieval_top_k).

        Returns:
            Structured RAGAnswer with generated answer, citations, sources, and abstention status.
        """
        if not query or not str(query).strip():
            raise ValueError("Query cannot be empty or whitespace only.")

        clean_query = query.strip()
        k = top_k if top_k is not None and top_k > 0 else self.settings.retrieval_top_k
        min_sim = self.settings.rag_min_similarity

        # Step 1: Source Routing
        if source_scope is not None:
            scope: SourceScope = source_scope
        else:
            decision = self.router.route(clean_query)
            scope = decision.source_scope

        # Step 2: Evidence Retrieval
        if scope == "all":
            filtered_results = self._retrieve_balanced_all(clean_query, top_k=k)
        elif scope == "internal":
            raw_results = self.retriever.search(
                clean_query, k=k, source_type="internal"
            )
            filtered_results = [r for r in raw_results if r.score >= min_sim]
        elif scope == "external":
            raw_results = self.retriever.search(
                clean_query, k=k, source_type="external"
            )
            filtered_results = [r for r in raw_results if r.score >= min_sim]
        else:
            filtered_results = self._retrieve_balanced_all(clean_query, top_k=k)

        # Step 3: Early Abstention Check
        if not filtered_results:
            return RAGAnswer(
                query=clean_query,
                source_scope=scope,
                answer="No encontré evidencia suficiente en las fuentes disponibles para responder esta consulta.",
                citations=[],
                sources=[],
                abstained=True,
            )

        # Step 4: Build Context and Source References
        context_str, source_references = build_rag_context(filtered_results)

        # Step 5: Grounded Answer Generation & Citation Validation
        answer_text, citations, is_grounded = self.generator.generate(
            query=clean_query,
            context_str=context_str,
            source_references=source_references,
            source_scope=scope,
        )

        # Step 6: Assemble final RAGAnswer
        abstained = not is_grounded or (
            "No encontré evidencia suficiente" in answer_text and len(citations) == 0
        )

        return RAGAnswer(
            query=clean_query,
            source_scope=scope,
            answer=answer_text,
            citations=citations,
            sources=source_references,
            abstained=abstained,
        )
