"""Deterministic quality, retrieval, consistency and operational metrics for AgentOps benchmarks."""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Optional

from pydantic import BaseModel, Field

from app.evaluation.agentops_dataset import AgentOpsCase
from app.observability.store import latency as compute_latency


class CaseExecutionRecord(BaseModel):
    """Sanitized single execution record of one benchmark case (no secrets or full prompts)."""

    case_id: str
    scenario: str
    repeat_index: int = 0
    execution_mode: str
    document_source: str
    human_reviewed: bool
    evaluable: bool = True
    consistency_group: Optional[str] = None

    status: str
    intent: Optional[str] = None
    tool_calls: list[str] = Field(default_factory=list)
    retrieved_files: list[str] = Field(default_factory=list)
    expected_files: list[str] = Field(default_factory=list)
    expected_tools: list[str] = Field(default_factory=list)
    requires_clarification: bool = False
    mutated_incidents: bool = False
    duration_ms: float = 0.0
    error_type: Optional[str] = None
    output_summary: str = ""

    task_correct: Optional[bool] = None
    tool_correct: Optional[bool] = None
    abstention_expected: bool = False
    abstention_correct: Optional[bool] = None
    false_abstention: bool = False
    trace_id: Optional[str] = None


class MetricReport(BaseModel):
    """Structured metric output with denominator, sample size and limitations."""

    value: Optional[float]
    numerator: Optional[int] = None
    denominator: Optional[int] = None
    sample_size: int
    formula: str
    data_source: str
    period: str
    limitations: str


def _normalize_tokens(text: str) -> set[str]:
    norm = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode("ascii").lower()
    tokens = re.findall(r"[a-z0-9_]+", norm)
    stopwords = {"el", "la", "los", "las", "de", "del", "en", "y", "a", "un", "una", "por", "para", "con", "que", "se"}
    return {t for t in tokens if len(t) > 1 and t not in stopwords}


def jaccard_similarity(text_a: str, text_b: str) -> float:
    """Token-level Jaccard similarity on normalized text."""
    tokens_a = _normalize_tokens(text_a)
    tokens_b = _normalize_tokens(text_b)
    if not tokens_a and not tokens_b:
        return 1.0
    if not tokens_a or not tokens_b:
        return 0.0
    return len(tokens_a & tokens_b) / len(tokens_a | tokens_b)


def are_runs_equivalent(
    run_a: CaseExecutionRecord,
    run_b: CaseExecutionRecord,
    *,
    jaccard_threshold: float = 0.60,
) -> bool:
    """Explicit operational and semantic equivalence criterion for repeated runs.

    Two runs are equivalent when they agree on status, intent, executed tools,
    retrieved source files, and semantic token overlap >= threshold (not strict
    character-by-character equality).
    """
    if run_a.status != run_b.status:
        return False
    if run_a.intent != run_b.intent:
        return False
    if sorted(run_a.tool_calls) != sorted(run_b.tool_calls):
        return False
    if sorted(set(run_a.retrieved_files)) != sorted(set(run_b.retrieved_files)):
        return False
    return jaccard_similarity(run_a.output_summary, run_b.output_summary) >= jaccard_threshold


def evaluate_case_record(
    case: AgentOpsCase,
    *,
    status: str,
    intent: Optional[str],
    tool_calls: list[str],
    retrieved_files: list[str],
    requires_clarification: bool,
    mutated_incidents: bool,
    duration_ms: float,
    output_text: str,
    execution_mode: str,
    repeat_index: int = 0,
    error_type: Optional[str] = None,
    trace_id: Optional[str] = None,
) -> CaseExecutionRecord:
    """Evaluate a single execution against the case's verifiable ground truth."""
    exp = case.expected_result
    evaluable = bool(case.human_reviewed)

    # Tool selection & execution accuracy
    tool_correct: Optional[bool] = None
    if evaluable:
        tool_correct = sorted(tool_calls) == sorted(case.expected_tools)

    # Abstention evaluation
    abstention_expected = exp.expected_behavior in {"abstain", "block_or_abstain"} or exp.expected_status == "abstained"
    abstention_correct: Optional[bool] = None
    false_abstention = False
    if evaluable:
        if abstention_expected:
            abstention_correct = (status == "abstained") and (not mutated_incidents if exp.must_not_mutate_incidents else True)
        elif status == "abstained":
            false_abstention = True

    # Task accuracy (only for human-reviewed, evaluable cases)
    task_correct: Optional[bool] = None
    if evaluable:
        checks: list[bool] = []
        if exp.expected_status is not None:
            checks.append(status == exp.expected_status)
        if exp.expected_intent is not None:
            checks.append(intent == exp.expected_intent)
        if exp.requires_clarification is not None:
            checks.append(requires_clarification == exp.requires_clarification)
        if exp.must_not_mutate_incidents:
            checks.append(not mutated_incidents)
        if case.expected_tools:
            checks.append(sorted(tool_calls) == sorted(case.expected_tools))
        if exp.expected_files:
            checks.append(any(ef in retrieved_files for ef in exp.expected_files))
        if exp.expected_keywords:
            lowered = (output_text or "").lower()
            checks.append(all(kw.lower() in lowered for kw in exp.expected_keywords))
        task_correct = all(checks) if checks else False

    return CaseExecutionRecord(
        case_id=case.id,
        scenario=case.scenario,
        repeat_index=repeat_index,
        execution_mode=execution_mode,
        document_source=case.document_source,
        human_reviewed=case.human_reviewed,
        evaluable=evaluable,
        consistency_group=case.consistency_group,
        status=status,
        intent=intent,
        tool_calls=list(tool_calls),
        retrieved_files=list(retrieved_files),
        expected_files=list(exp.expected_files),
        expected_tools=list(case.expected_tools),
        requires_clarification=requires_clarification,
        mutated_incidents=mutated_incidents,
        duration_ms=round(float(duration_ms), 3),
        error_type=error_type,
        output_summary=(output_text or "")[:240],
        task_correct=task_correct,
        tool_correct=tool_correct,
        abstention_expected=abstention_expected,
        abstention_correct=abstention_correct,
        false_abstention=false_abstention,
        trace_id=trace_id,
    )


def compute_benchmark_metrics(
    records: list[CaseExecutionRecord],
    *,
    data_source: str,
    period: str,
    limitations: str,
) -> dict[str, Any]:
    """Compute all required metrics from execution records; return null when denominator is 0."""
    if not records:
        empty_metric = lambda formula: MetricReport(
            value=None,
            numerator=0,
            denominator=0,
            sample_size=0,
            formula=formula,
            data_source=data_source,
            period=period,
            limitations=limitations,
        ).model_dump()
        return {
            "task_accuracy": empty_metric("correctos / evaluables"),
            "retrieval_precision": empty_metric("documentos_relevantes_recuperados / total_documentos_recuperados"),
            "consistency": empty_metric("repeticiones_equivalentes / repeticiones_validas"),
            "error_rate": empty_metric("ejecuciones_failed / total_ejecuciones"),
            "tool_accuracy": empty_metric("tareas_herramienta_correcta / tareas_evaluables"),
            "abstention_accuracy": empty_metric("abstenciones_correctas / casos_abstencion_esperada"),
            "false_abstentions": 0,
            "latency_ms": compute_latency([]),
            "counts": {
                "total_executions": 0,
                "evaluable_executions": 0,
                "correct_cases": 0,
                "incorrect_cases": 0,
                "pending_validation_cases": 0,
                "corpus_cases": 0,
                "synthetic_cases": 0,
            },
            "by_scenario": {},
        }

    evaluable = [r for r in records if r.evaluable and r.task_correct is not None]
    correct_n = sum(1 for r in evaluable if r.task_correct)
    task_acc = round(correct_n / len(evaluable), 4) if evaluable else None

    # Retrieval precision: relevant retrieved docs / total retrieved docs across RAG cases with expected_files
    rel_docs = 0
    total_docs = 0
    rag_ret_cases = 0
    for r in records:
        if r.evaluable and r.expected_files and r.retrieved_files:
            rag_ret_cases += 1
            expected_set = set(r.expected_files)
            total_docs += len(r.retrieved_files)
            rel_docs += sum(1 for f in r.retrieved_files if f in expected_set)
    ret_prec = round(rel_docs / total_docs, 4) if total_docs > 0 else None

    # Consistency across repeated groups
    groups: dict[str, list[CaseExecutionRecord]] = {}
    for r in records:
        if r.consistency_group and r.status != "failed":
            groups.setdefault(r.consistency_group, []).append(r)
    con_num = 0
    con_den = 0
    for group_runs in groups.values():
        if len(group_runs) < 2:
            continue
        anchor = group_runs[0]
        con_den += len(group_runs)
        con_num += sum(1 for run in group_runs if are_runs_equivalent(anchor, run))
    consistency_val = round(con_num / con_den, 4) if con_den > 0 else None

    # Error rate
    failed_n = sum(1 for r in records if r.status == "failed")
    error_rate_val = round(failed_n / len(records), 4) if records else None

    # Tool accuracy
    tool_eval = [r for r in records if r.evaluable and r.tool_correct is not None]
    tool_ok = sum(1 for r in tool_eval if r.tool_correct)
    tool_acc = round(tool_ok / len(tool_eval), 4) if tool_eval else None

    # Abstention accuracy & false abstentions
    abs_eval = [r for r in records if r.evaluable and r.abstention_expected and r.abstention_correct is not None]
    abs_ok = sum(1 for r in abs_eval if r.abstention_correct)
    abs_acc = round(abs_ok / len(abs_eval), 4) if abs_eval else None
    false_abs = sum(1 for r in records if r.evaluable and r.false_abstention)

    # Latency (reusing app.observability.store.latency)
    lat_stats = compute_latency([r.duration_ms for r in records])

    # Scenario breakdown
    by_scenario: dict[str, dict[str, Any]] = {}
    for r in records:
        bucket = by_scenario.setdefault(
            r.scenario,
            {"total": 0, "evaluable": 0, "correct": 0, "incorrect": 0, "pending_validation": 0, "failed": 0},
        )
        bucket["total"] += 1
        if r.status == "failed":
            bucket["failed"] += 1
        if not r.human_reviewed:
            bucket["pending_validation"] += 1
        elif r.task_correct is True:
            bucket["evaluable"] += 1
            bucket["correct"] += 1
        elif r.task_correct is False:
            bucket["evaluable"] += 1
            bucket["incorrect"] += 1

    pending_ids = {r.case_id for r in records if not r.human_reviewed}
    corpus_ids = {r.case_id for r in records if r.document_source == "corpus_verified"}
    synthetic_ids = {r.case_id for r in records if r.document_source == "synthetic_fixture"}

    return {
        "task_accuracy": MetricReport(
            value=task_acc,
            numerator=correct_n,
            denominator=len(evaluable),
            sample_size=len(evaluable),
            formula="casos_correctos / casos_evaluables",
            data_source=data_source,
            period=period,
            limitations=limitations,
        ).model_dump(),
        "retrieval_precision": MetricReport(
            value=ret_prec,
            numerator=rel_docs,
            denominator=total_docs,
            sample_size=rag_ret_cases,
            formula="documentos_relevantes_recuperados / total_documentos_recuperados",
            data_source=data_source,
            period=period,
            limitations=limitations,
        ).model_dump(),
        "consistency": MetricReport(
            value=consistency_val,
            numerator=con_num,
            denominator=con_den,
            sample_size=con_den,
            formula="repeticiones_equivalentes / repeticiones_validas",
            data_source=data_source,
            period=period,
            limitations=limitations,
        ).model_dump(),
        "error_rate": MetricReport(
            value=error_rate_val,
            numerator=failed_n,
            denominator=len(records),
            sample_size=len(records),
            formula="ejecuciones_failed / total_ejecuciones",
            data_source=data_source,
            period=period,
            limitations=limitations,
        ).model_dump(),
        "tool_accuracy": MetricReport(
            value=tool_acc,
            numerator=tool_ok,
            denominator=len(tool_eval),
            sample_size=len(tool_eval),
            formula="tareas_herramienta_correcta / tareas_evaluables",
            data_source=data_source,
            period=period,
            limitations=limitations,
        ).model_dump(),
        "abstention_accuracy": MetricReport(
            value=abs_acc,
            numerator=abs_ok,
            denominator=len(abs_eval),
            sample_size=len(abs_eval),
            formula="abstenciones_correctas / casos_abstencion_esperada",
            data_source=data_source,
            period=period,
            limitations=limitations,
        ).model_dump(),
        "false_abstentions": false_abs,
        "latency_ms": lat_stats,
        "counts": {
            "total_executions": len(records),
            "evaluable_executions": len(evaluable),
            "correct_cases": correct_n,
            "incorrect_cases": len(evaluable) - correct_n,
            "pending_validation_cases": len(pending_ids),
            "corpus_cases": len(corpus_ids),
            "synthetic_cases": len(synthetic_ids),
        },
        "by_scenario": by_scenario,
    }
