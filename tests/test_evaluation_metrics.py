"""Offline unit tests for deterministic evaluation metrics calculation."""

from langchain_core.documents import Document
import pytest

from app.evaluation.metrics import (
    calculate_abstention_summary,
    calculate_generation_summary,
    calculate_retrieval_summary,
    calculate_router_summary,
    classify_abstention_case,
    evaluate_generation_case,
    evaluate_retrieval_case,
    evaluate_router_case,
)
from app.evaluation.schemas import EvaluationCase
from app.rag.schemas import RAGAnswer, SearchResult, SourceReference


# ============================================================================
# Router Metrics Tests
# ============================================================================


def test_router_metrics_accuracy_and_out_of_domain_exclusion():
    """Verify router accuracy calculation excludes out_of_domain cases with expected_scope=None."""
    case_in = EvaluationCase(
        id="R1",
        query="Consulta interna",
        category="internal",
        expected_scope="internal",
        answerable=True,
        expected_source_types=["internal"],
        expected_files=["doc1.md"],
        expected_behavior="grounded_answer",
    )
    case_ext = EvaluationCase(
        id="R2",
        query="Consulta externa",
        category="external",
        expected_scope="external",
        answerable=True,
        expected_source_types=["external"],
        expected_files=["doc2.md"],
        expected_behavior="grounded_answer",
    )
    case_ood = EvaluationCase(
        id="R3",
        query="Consulta fuera de dominio",
        category="out_of_domain",
        expected_scope=None,
        answerable=False,
        expected_source_types=[],
        expected_files=[],
        expected_behavior="abstain",
    )

    # R1 predicted internal (correct), R2 predicted all (incorrect), R3 predicted internal (ignored for router accuracy)
    r1_res = evaluate_router_case(case_in, predicted_scope="internal", confidence=0.9)
    r2_res = evaluate_router_case(case_ext, predicted_scope="all", confidence=0.8)
    r3_res = evaluate_router_case(case_ood, predicted_scope="internal", confidence=0.5)

    assert r1_res.is_correct is True
    assert r2_res.is_correct is False
    assert r3_res.is_correct is None  # OOD has no expected_scope

    summary = calculate_router_summary([r1_res, r2_res, r3_res])
    # Denominator must only be 2 (evaluable cases)
    assert summary.total_evaluable_cases == 2
    assert summary.correct_routes == 1
    assert summary.router_accuracy == 0.50
    assert summary.confusion_matrix["internal"]["internal"] == 1
    assert summary.confusion_matrix["external"]["all"] == 1


# ============================================================================
# Retrieval Metrics Tests
# ============================================================================


def test_retrieval_hit_mrr_and_recall():
    """Verify Hit@K, MRR and expected source recall calculations."""
    case = EvaluationCase(
        id="RET-1",
        query="Pregunta de acceso",
        category="all",
        expected_scope="all",
        answerable=True,
        expected_source_types=["internal", "external"],
        expected_files=["politica_accesos.md", "guia_buenas_practicas.md"],
        expected_behavior="grounded_answer",
    )

    # Mock SearchResults: rank 1 is unrelated, rank 2 is politica_accesos.md, rank 3 is unrelated
    results = [
        SearchResult(
            document=Document(
                page_content="Texto",
                metadata={"file_name": "faq_interna.txt", "source_type": "internal"},
            ),
            score=0.80,
            rank=1,
        ),
        SearchResult(
            document=Document(
                page_content="Texto",
                metadata={"file_name": "politica_accesos.md", "source_type": "internal"},
            ),
            score=0.75,
            rank=2,
        ),
    ]

    ret_eval = evaluate_retrieval_case(case, results, top_k=2)
    assert ret_eval.hit_at_k == 1.0
    assert ret_eval.reciprocal_rank == 0.50  # First match at rank 2 -> 1/2 = 0.5
    assert ret_eval.expected_source_recall_at_k == 0.50  # 1 of 2 expected files found
    # Only internal retrieved, but case expected both internal and external
    assert ret_eval.dual_source_coverage is False


def test_retrieval_dual_source_coverage_true():
    """Verify dual_source_coverage is True when both internal and external sources are retrieved."""
    case = EvaluationCase(
        id="DUAL-1",
        query="Pregunta mixta",
        category="all",
        expected_scope="all",
        answerable=True,
        expected_source_types=["internal", "external"],
        expected_files=["doc_int.md", "doc_ext.txt"],
        expected_behavior="grounded_answer",
    )
    results = [
        SearchResult(
            document=Document(page_content="T1", metadata={"file_name": "doc_int.md", "source_type": "internal"}),
            score=0.85,
            rank=1,
        ),
        SearchResult(
            document=Document(page_content="T2", metadata={"file_name": "doc_ext.txt", "source_type": "external"}),
            score=0.80,
            rank=2,
        ),
    ]

    ret_eval = evaluate_retrieval_case(case, results, top_k=2)
    assert ret_eval.hit_at_k == 1.0
    assert ret_eval.expected_source_recall_at_k == 1.0
    assert ret_eval.dual_source_coverage is True


def test_retrieval_scope_compliance():
    """Verify scope compliance detects when external source leaks into internal scope."""
    case_internal = EvaluationCase(
        id="COMP-1",
        query="Pregunta interna",
        category="internal",
        expected_scope="internal",
        answerable=True,
        expected_source_types=["internal"],
        expected_files=["politica.md"],
        expected_behavior="grounded_answer",
    )
    results_leaked = [
        SearchResult(
            document=Document(page_content="T", metadata={"file_name": "guia.md", "source_type": "external"}),
            score=0.80,
            rank=1,
        )
    ]
    ret_eval = evaluate_retrieval_case(case_internal, results_leaked, top_k=2)
    assert ret_eval.source_scope_compliant is False


# ============================================================================
# Abstention Metrics Tests
# ============================================================================


def test_abstention_classification_and_summary():
    """Verify TP, FP, TN, FN classification and abstention performance metrics."""
    # TP: not answerable & actual_abstained=True
    assert classify_abstention_case(answerable=False, actual_abstained=True) == "TP"
    # FP: answerable & actual_abstained=True
    assert classify_abstention_case(answerable=True, actual_abstained=True) == "FP"
    # TN: answerable & actual_abstained=False
    assert classify_abstention_case(answerable=True, actual_abstained=False) == "TN"
    # FN: not answerable & actual_abstained=False
    assert classify_abstention_case(answerable=False, actual_abstained=False) == "FN"

    case_ans = EvaluationCase(
        id="A1",
        query="Pregunta",
        category="internal",
        expected_scope="internal",
        answerable=True,
        expected_source_types=["internal"],
        expected_files=["doc.md"],
        expected_behavior="grounded_answer",
    )
    case_ood = EvaluationCase(
        id="A2",
        query="Pregunta OOD",
        category="out_of_domain",
        expected_scope=None,
        answerable=False,
        expected_source_types=[],
        expected_files=[],
        expected_behavior="abstain",
    )

    # 1 TN (answerable & answered) + 1 TP (OOD & abstained)
    ans1 = RAGAnswer(query="q1", source_scope="internal", answer="Respuesta [S1]", citations=["S1"], sources=[SourceReference(id="S1", file_name="doc.md", source_type="internal", score=0.8)], abstained=False)
    ans2 = RAGAnswer(query="q2", source_scope="all", answer="No encontré evidencia", citations=[], sources=[], abstained=True)

    g1 = evaluate_generation_case(case_ans, ans1)
    g2 = evaluate_generation_case(case_ood, ans2)

    abst_sum = calculate_abstention_summary([g1, g2])
    assert abst_sum.tp_abstain == 1
    assert abst_sum.tn_abstain == 1
    assert abst_sum.fp_abstain == 0
    assert abst_sum.fn_abstain == 0
    assert abst_sum.abstention_accuracy == 1.0
    assert abst_sum.abstention_precision == 1.0
    assert abst_sum.abstention_recall == 1.0


# ============================================================================
# Citation Integrity & Traceable Generation Tests
# ============================================================================


def test_generation_citation_integrity_and_traceability():
    """Verify live citation integrity pass and traceable answer success metric."""
    case = EvaluationCase(
        id="G1",
        query="Pregunta",
        category="internal",
        expected_scope="internal",
        answerable=True,
        expected_source_types=["internal"],
        expected_files=["doc.md"],
        expected_behavior="grounded_answer",
    )

    # Valid response with S1
    ans_valid = RAGAnswer(
        query="q",
        source_scope="internal",
        answer="Respuesta válida [S1].",
        citations=["S1"],
        sources=[SourceReference(id="S1", file_name="doc.md", source_type="internal", score=0.85)],
        abstained=False,
    )
    g_val = evaluate_generation_case(case, ans_valid)
    assert g_val.final_citation_integrity_pass is True
    assert g_val.traceable_answer_success is True

    # Invalid response without citations
    ans_no_cit = RAGAnswer(
        query="q",
        source_scope="internal",
        answer="Respuesta sin citas.",
        citations=[],
        sources=[SourceReference(id="S1", file_name="doc.md", source_type="internal", score=0.85)],
        abstained=False,
    )
    g_no_cit = evaluate_generation_case(case, ans_no_cit)
    assert g_no_cit.final_citation_integrity_pass is False
    assert g_no_cit.traceable_answer_success is False

    # Summary
    sum_gen = calculate_generation_summary([g_val, g_no_cit], [case, case])
    assert sum_gen.total_answerable_cases == 2
    assert sum_gen.total_generated_answers == 2
    assert sum_gen.citation_integrity_rate == 0.50
    assert sum_gen.traceable_answer_success_rate == 0.50


def test_false_abstention_does_not_inflate_citation_integrity_rate():
    """Verify false abstention is excluded from citation_integrity denominator and penalizes traceable_answer_success."""
    case1 = EvaluationCase(id="C1", query="consulta 1", category="internal", expected_scope="internal", answerable=True, expected_source_types=["internal"], expected_files=["doc.md"], expected_behavior="grounded_answer")
    case2 = EvaluationCase(id="C2", query="consulta 2", category="internal", expected_scope="internal", answerable=True, expected_source_types=["internal"], expected_files=["doc.md"], expected_behavior="grounded_answer")
    case3 = EvaluationCase(id="C3", query="consulta 3", category="internal", expected_scope="internal", answerable=True, expected_source_types=["internal"], expected_files=["doc.md"], expected_behavior="grounded_answer")

    # 1. Answer generated with valid citation
    ans1 = RAGAnswer(query="consulta 1", source_scope="internal", answer="R1 [S1]", citations=["S1"], sources=[SourceReference(id="S1", file_name="doc.md", source_type="internal", score=0.8)], abstained=False)
    # 2. False abstention (answerable=True but abstained=True)
    ans2 = RAGAnswer(query="consulta 2", source_scope="internal", answer="Abstención indebida", citations=[], sources=[], abstained=True)
    # 3. Answer generated without citation
    ans3 = RAGAnswer(query="consulta 3", source_scope="internal", answer="Sin citas", citations=[], sources=[SourceReference(id="S1", file_name="doc.md", source_type="internal", score=0.8)], abstained=False)

    g1 = evaluate_generation_case(case1, ans1)
    g2 = evaluate_generation_case(case2, ans2)
    g3 = evaluate_generation_case(case3, ans3)

    summary = calculate_generation_summary([g1, g2, g3], [case1, case2, case3])
    assert summary.total_answerable_cases == 3
    assert summary.total_generated_answers == 2  # Only C1 and C3 generated answers
    assert summary.citation_integrity_rate == 0.50  # 1 pass out of 2 generated answers (C2 did not inflate it!)
    assert summary.traceable_answer_success_rate == 0.3333  # 1 pass out of 3 answerable cases


def test_out_of_domain_excluded_from_retrieval_summary():
    """Verify out-of-domain cases (answerable=False) do not contribute to retrieval summary metrics."""
    case_ans = EvaluationCase(id="ANS-1", query="consulta respondible", category="internal", expected_scope="internal", answerable=True, expected_source_types=["internal"], expected_files=["doc.md"], expected_behavior="grounded_answer")
    case_ood = EvaluationCase(id="OOD-1", query="consulta fuera de dominio", category="out_of_domain", expected_scope=None, answerable=False, expected_source_types=[], expected_files=[], expected_behavior="abstain")

    ret_ans = evaluate_retrieval_case(case_ans, [SearchResult(document=Document(page_content="T", metadata={"file_name": "doc.md", "source_type": "internal"}), score=0.9, rank=1)], top_k=2)
    ret_ood = evaluate_retrieval_case(case_ood, [], top_k=2)

    summary = calculate_retrieval_summary([ret_ans, ret_ood], [case_ans, case_ood])
    assert summary.total_answerable_cases == 1
    assert summary.hit_at_k_rate == 1.0
    assert summary.mean_reciprocal_rank == 1.0
