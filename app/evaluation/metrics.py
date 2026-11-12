"""Deterministic calculation of evaluation metrics for Routing, Retrieval, Abstention and Generation."""

from typing import Dict, List, Literal, Optional, Set

from app.evaluation.schemas import (
    AbstentionSummaryMetrics,
    CitationAndGenerationSummaryMetrics,
    EvaluationCase,
    GenerationEvaluationResult,
    RetrievalEvaluationResult,
    RetrievalSummaryMetrics,
    RouterEvaluationResult,
    RouterSummaryMetrics,
)
from app.rag.schemas import RAGAnswer, SearchResult


# ============================================================================
# 1. Source Routing Metrics
# ============================================================================


def evaluate_router_case(
    case: EvaluationCase,
    predicted_scope: str,
    confidence: Optional[float] = None,
) -> RouterEvaluationResult:
    """Evaluate router classification for a single case.

    Note: out_of_domain cases have expected_scope=None and are not marked as correct/incorrect.
    """
    is_correct: Optional[bool] = None
    if case.expected_scope is not None:
        is_correct = (predicted_scope.lower().strip() == case.expected_scope.lower().strip())

    return RouterEvaluationResult(
        case_id=case.id,
        expected_scope=case.expected_scope,
        predicted_scope=predicted_scope,
        model_reported_confidence=confidence,
        is_correct=is_correct,
    )


def calculate_router_summary(
    results: List[RouterEvaluationResult],
) -> RouterSummaryMetrics:
    """Calculate aggregated accuracy and confusion matrix for evaluable routing cases."""
    evaluable = [r for r in results if r.expected_scope is not None]
    total = len(evaluable)
    correct = sum(1 for r in evaluable if r.is_correct is True)
    accuracy = correct / total if total > 0 else 0.0

    scopes = ["internal", "external", "all"]
    matrix: Dict[str, Dict[str, int]] = {
        exp: {pred: 0 for pred in scopes} for exp in scopes
    }

    for r in evaluable:
        exp = str(r.expected_scope)
        pred = str(r.predicted_scope)
        if exp in matrix and pred in matrix[exp]:
            matrix[exp][pred] += 1

    return RouterSummaryMetrics(
        total_evaluable_cases=total,
        correct_routes=correct,
        router_accuracy=round(accuracy, 4),
        confusion_matrix=matrix,
    )


# ============================================================================
# 2. Retrieval Metrics (Source / File Level)
# ============================================================================


def evaluate_retrieval_case(
    case: EvaluationCase,
    search_results: List[SearchResult],
    top_k: int = 4,
    retrieval_scope: Optional[str] = None,
) -> RetrievalEvaluationResult:
    """Evaluate retrieval performance at source/file level for a single case.

    Args:
        case: EvaluationCase under evaluation.
        search_results: Raw Top-K SearchResult items pre-threshold.
        top_k: Top-K evaluation cut-off.
        retrieval_scope: Explicit scope used for retrieval evaluation (defaults to case.expected_scope).
    """
    if not case.answerable or not case.expected_files:
        return RetrievalEvaluationResult(
            case_id=case.id,
            expected_files=[],
            retrieved_files=[],
            hit_at_k=0.0,
            reciprocal_rank=0.0,
            expected_source_recall_at_k=0.0,
            source_scope_compliant=True,
            dual_source_coverage=None,
        )

    effective_scope = retrieval_scope if retrieval_scope is not None else case.expected_scope

    retrieved_k = search_results[:top_k]
    retrieved_files = [
        str(r.document.metadata.get("file_name", "")) for r in retrieved_k
    ]
    retrieved_types = [
        str(r.document.metadata.get("source_type", "")) for r in retrieved_k
    ]

    # Hit@K
    has_hit = any(ef in retrieved_files for ef in case.expected_files)
    hit_at_k = 1.0 if has_hit else 0.0

    # Reciprocal Rank (RR = 1/r where r is 1-indexed position of first relevant file)
    reciprocal_rank = 0.0
    for rank, rf in enumerate(retrieved_files, start=1):
        if rf in case.expected_files:
            reciprocal_rank = 1.0 / rank
            break

    # Expected Source Recall@K
    unique_retrieved_expected = set(retrieved_files).intersection(set(case.expected_files))
    expected_recall = (
        len(unique_retrieved_expected) / len(case.expected_files)
        if case.expected_files
        else 0.0
    )

    # Source Scope Compliance (evaluates against effective_scope used for retrieval)
    if effective_scope == "internal":
        compliant = all(st == "internal" for st in retrieved_types) if retrieved_types else True
    elif effective_scope == "external":
        compliant = all(st == "external" for st in retrieved_types) if retrieved_types else True
    else:
        compliant = True

    # Dual Source Coverage (only for comparative cases expecting both internal and external)
    dual_coverage: Optional[bool] = None
    if case.expected_scope == "all" and set(case.expected_source_types) == {"internal", "external"}:
        has_int = "internal" in retrieved_types
        has_ext = "external" in retrieved_types
        dual_coverage = (has_int and has_ext)

    return RetrievalEvaluationResult(
        case_id=case.id,
        expected_files=case.expected_files,
        retrieved_files=retrieved_files,
        hit_at_k=round(hit_at_k, 4),
        reciprocal_rank=round(reciprocal_rank, 4),
        expected_source_recall_at_k=round(expected_recall, 4),
        source_scope_compliant=compliant,
        dual_source_coverage=dual_coverage,
    )


def calculate_retrieval_summary(
    results: List[RetrievalEvaluationResult],
    cases: List[EvaluationCase],
) -> RetrievalSummaryMetrics:
    """Calculate aggregated retrieval metrics across answerable cases."""
    answerable_ids = {c.id for c in cases if c.answerable}
    ans_results = [r for r in results if r.case_id in answerable_ids]
    total = len(ans_results)

    if total == 0:
        return RetrievalSummaryMetrics(
            total_answerable_cases=0,
            hit_at_k_rate=0.0,
            mean_reciprocal_rank=0.0,
            mean_expected_source_recall_at_k=0.0,
            scope_compliance_rate=0.0,
            dual_source_coverage_rate=None,
        )

    hit_rate = sum(r.hit_at_k for r in ans_results) / total
    mrr = sum(r.reciprocal_rank for r in ans_results) / total
    mean_recall = sum(r.expected_source_recall_at_k for r in ans_results) / total
    compliance_rate = sum(1 for r in ans_results if r.source_scope_compliant) / total

    dual_cases = [r for r in ans_results if r.dual_source_coverage is not None]
    dual_rate = (
        sum(1 for r in dual_cases if r.dual_source_coverage is True) / len(dual_cases)
        if dual_cases
        else None
    )

    return RetrievalSummaryMetrics(
        total_answerable_cases=total,
        hit_at_k_rate=round(hit_rate, 4),
        mean_reciprocal_rank=round(mrr, 4),
        mean_expected_source_recall_at_k=round(mean_recall, 4),
        scope_compliance_rate=round(compliance_rate, 4),
        dual_source_coverage_rate=round(dual_rate, 4) if dual_rate is not None else None,
    )


# ============================================================================
# 3. Abstention Metrics
# ============================================================================


def classify_abstention_case(
    answerable: bool,
    actual_abstained: bool,
) -> Literal["TP", "FP", "TN", "FN"]:
    """Classify abstention outcome with 'abstain' as positive class."""
    if not answerable and actual_abstained:
        return "TP"
    elif answerable and actual_abstained:
        return "FP"
    elif answerable and not actual_abstained:
        return "TN"
    else:  # not answerable and not actual_abstained
        return "FN"


def calculate_abstention_summary(
    results: List[GenerationEvaluationResult],
) -> AbstentionSummaryMetrics:
    """Calculate aggregated abstention confusion matrix and performance metrics."""
    total = len(results)
    tp = sum(1 for r in results if r.abstention_class == "TP")
    fp = sum(1 for r in results if r.abstention_class == "FP")
    tn = sum(1 for r in results if r.abstention_class == "TN")
    fn = sum(1 for r in results if r.abstention_class == "FN")

    accuracy = (tp + tn) / total if total > 0 else 0.0
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0

    return AbstentionSummaryMetrics(
        total_cases=total,
        tp_abstain=tp,
        fp_abstain=fp,
        tn_abstain=tn,
        fn_abstain=fn,
        abstention_accuracy=round(accuracy, 4),
        abstention_precision=round(precision, 4),
        abstention_recall=round(recall, 4),
    )


# ============================================================================
# 4. Citation and Grounded Generation Metrics
# ============================================================================


def evaluate_generation_case(
    case: EvaluationCase,
    answer: RAGAnswer,
) -> GenerationEvaluationResult:
    """Evaluate live citation integrity and traceable generation outcome."""
    abst_class = classify_abstention_case(case.answerable, answer.abstained)
    valid_source_ids: Set[str] = {s.id for s in answer.sources}
    citations = answer.citations or []

    final_cit_count = len(citations)
    valid_cits = [c for c in citations if c in valid_source_ids]
    valid_cit_count = len(valid_cits)

    if not answer.abstained and len(answer.sources) > 0:
        has_required = final_cit_count >= 1
        all_resolve = (final_cit_count > 0 and final_cit_count == valid_cit_count)
        integrity_pass = has_required and all_resolve
    else:
        has_required = False
        all_resolve = (final_cit_count == 0)
        integrity_pass = False

    # Traceable answer success rate (verifies pipeline contract for answerable cases)
    if case.answerable:
        traceable_success = (
            (not answer.abstained)
            and (len(answer.sources) > 0)
            and (final_cit_count > 0)
            and integrity_pass
        )
    else:
        traceable_success = answer.abstained

    return GenerationEvaluationResult(
        case_id=case.id,
        answerable=case.answerable,
        actual_abstained=answer.abstained,
        abstention_class=abst_class,
        final_citation_count=final_cit_count,
        valid_final_citation_count=valid_cit_count,
        has_required_citation=has_required,
        all_citations_resolve_to_sources=all_resolve,
        final_citation_integrity_pass=integrity_pass,
        traceable_answer_success=traceable_success,
        generated_answer=answer.answer,
    )


def calculate_generation_summary(
    results: List[GenerationEvaluationResult],
    cases: List[EvaluationCase],
) -> CitationAndGenerationSummaryMetrics:
    """Calculate aggregated citation integrity (over generated answers) and traceable answer success rates."""
    answerable_ids = {c.id for c in cases if c.answerable}
    ans_results = [r for r in results if r.case_id in answerable_ids]
    total_ans = len(ans_results)

    # Citation integrity rate is calculated strictly over ACTUALLY GENERATED non-abstained answers
    generated_answers = [r for r in ans_results if not r.actual_abstained]
    total_generated = len(generated_answers)

    cit_pass_rate = (
        sum(1 for r in generated_answers if r.final_citation_integrity_pass) / total_generated
        if total_generated > 0
        else 0.0
    )

    # Traceable answer success rate penalizes false abstentions over total answerable cases
    traceable_pass_rate = (
        sum(1 for r in ans_results if r.traceable_answer_success) / total_ans
        if total_ans > 0
        else 0.0
    )

    return CitationAndGenerationSummaryMetrics(
        total_answerable_cases=total_ans,
        total_generated_answers=total_generated,
        citation_integrity_rate=round(cit_pass_rate, 4),
        traceable_answer_success_rate=round(traceable_pass_rate, 4),
    )
