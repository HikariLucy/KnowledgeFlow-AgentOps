"""Knowledge retrieval tool backed by the existing EP1 RAG pipeline."""

from app.rag.pipeline import RAGPipeline
from app.tools.schemas import (
    KnowledgeQueryInput,
    KnowledgeQueryResult,
)


class KnowledgeRAGTool:
    """Expose the existing KnowledgeFlow RAG pipeline as an agent tool.

    The tool intentionally depends on the RAGPipeline abstraction instead of
    FastAPI dependencies. This keeps the agent layer independent from HTTP and
    makes the tool straightforward to test with offline pipeline doubles.
    """

    name = "search_knowledge"

    description = (
        "Consulta la base de conocimiento de NovaTech para recuperar políticas, "
        "procedimientos internos, documentación organizacional y fuentes externas "
        "indexadas. Debe utilizarse cuando una decisión requiera evidencia "
        "documental antes de responder o ejecutar otra acción."
    )

    def __init__(self, pipeline: RAGPipeline) -> None:
        self.pipeline = pipeline

    def run(self, arguments: KnowledgeQueryInput) -> KnowledgeQueryResult:
        """Execute the existing RAG pipeline and return an agent-safe result."""
        answer = self.pipeline.run(
            query=arguments.query,
            source_scope=arguments.source_scope,
            top_k=arguments.top_k,
        )

        return KnowledgeQueryResult.model_validate(answer.model_dump())
