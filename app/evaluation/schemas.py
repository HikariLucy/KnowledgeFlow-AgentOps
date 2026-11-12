"""Pydantic schemas and metadata models for the systematic RAG evaluation framework."""

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator

EvaluationCategory = Literal["internal", "external", "all", "out_of_domain"]
ExpectedScope = Literal["internal", "external", "all"]
ExpectedBehavior = Literal["grounded_answer", "abstain"]


class EvaluationCase(BaseModel):
    """Schema for a single controlled test case in the evaluation dataset."""

    id: str = Field(..., min_length=1, description="Unique case identifier (e.g. 'EVAL-001')")
    query: str = Field(..., min_length=3, description="User query or question string")
    category: EvaluationCategory = Field(
        ...,
        description="Evaluation category: 'internal', 'external', 'all', or 'out_of_domain'",
    )
    expected_scope: Optional[ExpectedScope] = Field(
        default=None,
        description="Expected search scope for routing ('internal', 'external', 'all'). None for out_of_domain.",
    )
    answerable: bool = Field(
        ..., description="True if the question is answerable from the knowledge base"
    )
    expected_source_types: List[Literal["internal", "external"]] = Field(
        default_factory=list,
        description="List of source types expected to contain relevant evidence",
    )
    expected_files: List[str] = Field(
        default_factory=list,
        description="List of file names expected to contain the answer (empty if answerable=False)",
    )
    expected_behavior: ExpectedBehavior = Field(
        ...,
        description="Expected pipeline behavior: 'grounded_answer' or 'abstain'",
    )
    notes: Optional[str] = Field(
        default=None, description="Analytical justification and notes for human review"
    )
    human_reviewed: bool = Field(
        default=False,
        description="Must be explicitly True only after verified human review",
    )

    @model_validator(mode="after")
    def validate_case_consistency(self) -> "EvaluationCase":
        """Validate logical consistency between category, scope, and expected behavior."""
        if self.category == "internal" and self.expected_scope != "internal":
            raise ValueError(
                f"Case {self.id}: category='internal' must have expected_scope='internal', got '{self.expected_scope}'."
            )
        if self.category == "external" and self.expected_scope != "external":
            raise ValueError(
                f"Case {self.id}: category='external' must have expected_scope='external', got '{self.expected_scope}'."
            )
        if self.category == "all" and self.expected_scope != "all":
            raise ValueError(
                f"Case {self.id}: category='all' must have expected_scope='all', got '{self.expected_scope}'."
            )

        if self.category == "out_of_domain":
            if self.expected_scope is not None:
                raise ValueError(
                    f"Case {self.id}: out_of_domain cases must have expected_scope=None, got '{self.expected_scope}'."
                )
            if self.answerable:
                raise ValueError(
                    f"Case {self.id}: out_of_domain cases must have answerable=False."
                )
            if self.expected_files:
                raise ValueError(
                    f"Case {self.id}: out_of_domain cases cannot require expected_files."
                )
            if self.expected_source_types:
                raise ValueError(
                    f"Case {self.id}: out_of_domain cases cannot require expected_source_types."
                )
            if self.expected_behavior != "abstain":
                raise ValueError(
                    f"Case {self.id}: out_of_domain cases must have expected_behavior='abstain'."
                )

        if self.answerable:
            if self.expected_scope is None:
                raise ValueError(
                    f"Case {self.id}: answerable=True cases must specify expected_scope."
                )
            if not self.expected_files:
                raise ValueError(
                    f"Case {self.id}: answerable=True cases must specify at least one expected_file."
                )
            if not self.expected_source_types:
                raise ValueError(
                    f"Case {self.id}: answerable=True cases must specify expected_source_types."
                )
            if self.expected_behavior != "grounded_answer":
                raise ValueError(
                    f"Case {self.id}: answerable=True cases must have expected_behavior='grounded_answer'."
                )

        if not self.answerable and self.expected_behavior != "abstain":
            raise ValueError(
                f"Case {self.id}: answerable=False cases must have expected_behavior='abstain'."
            )

        return self


class EvaluationDataset(BaseModel):
    """Collection of evaluation cases representing a dataset file."""

    version: str = Field(default="1.0", description="Dataset schema version")
    description: str = Field(..., description="Description of the dataset corpus and purpose")
    cases: List[EvaluationCase] = Field(..., min_length=1, description="List of evaluation cases")

    @model_validator(mode="after")
    def validate_unique_case_ids(self) -> "EvaluationDataset":
        """Ensure all case IDs within the dataset are strictly unique."""
        ids = [c.id for c in self.cases]
        duplicates = [cid for cid in ids if ids.count(cid) > 1]
        if duplicates:
            raise ValueError(
                f"EvaluationDataset contains duplicate case IDs: {set(duplicates)}"
            )
        return self


# ============================================================================
# Individual Evaluation Results per Case
# ============================================================================


class RouterEvaluationResult(BaseModel):
    """Evaluation result for the Source Routing Agent step."""

    case_id: str
    expected_scope: Optional[ExpectedScope] = None
    predicted_scope: str
    model_reported_confidence: Optional[float] = None
    is_correct: Optional[bool] = None  # None for out_of_domain cases


class RetrievalEvaluationResult(BaseModel):
    """Evaluation result for the semantic retrieval step at source/file level."""

    case_id: str
    expected_files: List[str]
    retrieved_files: List[str]
    hit_at_k: float = Field(..., ge=0.0, le=1.0)
    reciprocal_rank: float = Field(..., ge=0.0, le=1.0)
    expected_source_recall_at_k: float = Field(..., ge=0.0, le=1.0)
    source_scope_compliant: bool
    dual_source_coverage: Optional[bool] = None


class GenerationEvaluationResult(BaseModel):
    """Evaluation result for grounded generation, citations, and abstention."""

    case_id: str
    answerable: bool
    actual_abstained: bool
    abstention_class: Literal["TP", "FP", "TN", "FN"]
    final_citation_count: int
    valid_final_citation_count: int
    has_required_citation: bool
    all_citations_resolve_to_sources: bool
    final_citation_integrity_pass: bool
    traceable_answer_success: bool
    generated_answer: str


class CaseEvaluationResult(BaseModel):
    """Complete evaluation record for a single case across all dimensions."""

    case: EvaluationCase
    router_result: RouterEvaluationResult
    retrieval_result: RetrievalEvaluationResult
    generation_result: GenerationEvaluationResult


# ============================================================================
# Summary & Aggregated Metrics Models
# ============================================================================


class RouterSummaryMetrics(BaseModel):
    """Aggregated metrics for Source Routing Agent."""

    total_evaluable_cases: int
    correct_routes: int
    router_accuracy: float
    confusion_matrix: Dict[str, Dict[str, int]]


class RetrievalSummaryMetrics(BaseModel):
    """Aggregated source-level metrics for Retrieval."""

    total_answerable_cases: int
    hit_at_k_rate: float
    mean_reciprocal_rank: float
    mean_expected_source_recall_at_k: float
    scope_compliance_rate: float
    dual_source_coverage_rate: Optional[float] = None


class AbstentionSummaryMetrics(BaseModel):
    """Aggregated metrics for Abstention behavior (positive class: abstain)."""

    total_cases: int
    tp_abstain: int  # answerable=False & actual_abstained=True
    fp_abstain: int  # answerable=True & actual_abstained=True
    tn_abstain: int  # answerable=True & actual_abstained=False
    fn_abstain: int  # answerable=False & actual_abstained=False
    abstention_accuracy: float
    abstention_precision: float
    abstention_recall: float


class CitationAndGenerationSummaryMetrics(BaseModel):
    """Aggregated metrics for citation integrity and traceable generation."""

    total_answerable_cases: int
    total_generated_answers: int
    citation_integrity_rate: float
    traceable_answer_success_rate: float


class EvaluationRunMetadata(BaseModel):
    """Execution metadata and environment traceability information."""

    timestamp: str
    git_commit: str
    git_dirty: bool
    router_model: str
    chat_model: str
    embedding_model: str
    top_k: int
    rag_min_similarity: float
    dataset_path: str
    dataset_version: str
    dataset_has_unreviewed: bool
    vector_index_fingerprint: Optional[str] = None


class EvaluationReport(BaseModel):
    """Complete structured evaluation report."""

    metadata: EvaluationRunMetadata
    router_summary: RouterSummaryMetrics
    retrieval_summary: RetrievalSummaryMetrics
    abstention_summary: AbstentionSummaryMetrics
    generation_summary: CitationAndGenerationSummaryMetrics
    cases: List[CaseEvaluationResult]
