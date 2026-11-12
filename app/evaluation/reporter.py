"""Report generator for saving evaluation outputs in structured JSON and readable Markdown."""

import json
from pathlib import Path
from typing import Union

from app.evaluation.schemas import EvaluationReport


def save_json_report(report: EvaluationReport, output_path: Union[str, Path]) -> None:
    """Save EvaluationReport as structured JSON.

    Args:
        report: Complete EvaluationReport instance.
        output_path: File destination path.
    """
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report.model_dump(), f, indent=2, ensure_ascii=False)


def generate_markdown_summary(report: EvaluationReport) -> str:
    """Generate objective Markdown summary of evaluation results.

    Contains numerical summaries, confusion matrices, detailed case table and failure analysis.
    Does NOT contain subjective academic reflections.
    """
    m = report.metadata
    r_sum = report.router_summary
    ret_sum = report.retrieval_summary
    abst_sum = report.abstention_summary
    gen_sum = report.generation_summary

    lines = [
        "# KnowledgeFlow RAG — Reporte de Evaluación Sistemática",
        "",
        "## 1. Metadatos de la Corrida",
        f"- **Fecha y Hora (UTC)**: {m.timestamp}",
        f"- **Git Commit**: `{m.git_commit}` (Dirty: `{m.git_dirty}`)",
        f"- **Source Router Model**: `{m.router_model}`",
        f"- **RAG Generation Model**: `{m.chat_model}`",
        f"- **Embedding Model**: `{m.embedding_model}`",
        f"- **Top-K Configurado**: `{m.top_k}`",
        f"- **Umbral de Similitud (RAG_MIN_SIMILARITY)**: `{m.rag_min_similarity:.2f}`",
        f"- **Dataset Evaluado**: `{m.dataset_path}` (Versión: `{m.dataset_version}`)",
        f"- **Casos no revisados por humanos**: `{'Sí (Resultados exploratorios)' if m.dataset_has_unreviewed else 'No (Dataset Verificado)'}`",
    ]

    if m.vector_index_fingerprint:
        lines.append(f"- **Fingerprint del Índice FAISS**: `{m.vector_index_fingerprint[:16]}...`")

    lines.extend([
        "",
        "---",
        "",
        "## 2. Resumen Cuantitativo de Métricas",
        "",
        "| Dimensión Evaluada | Métrica | Valor Obtenido | Casos Evaluados |",
        "| :--- | :--- | :--- | :--- |",
        f"| **Source Routing** | Router Accuracy | **{r_sum.router_accuracy * 100:.1f}%** ({r_sum.correct_routes}/{r_sum.total_evaluable_cases}) | {r_sum.total_evaluable_cases} (in-domain) |",
        f"| **Retrieval (File-level)** | Hit@{m.top_k} Rate | **{ret_sum.hit_at_k_rate * 100:.1f}%** | {ret_sum.total_answerable_cases} (answerable) |",
        f"| **Retrieval (File-level)** | Mean Reciprocal Rank (MRR) | **{ret_sum.mean_reciprocal_rank:.4f}** | {ret_sum.total_answerable_cases} |",
        f"| **Retrieval (File-level)** | Expected Source Recall@{m.top_k} | **{ret_sum.mean_expected_source_recall_at_k * 100:.1f}%** | {ret_sum.total_answerable_cases} |",
        f"| **Retrieval (File-level)** | Scope Compliance Rate | **{ret_sum.scope_compliance_rate * 100:.1f}%** | {ret_sum.total_answerable_cases} |",
    ])

    if ret_sum.dual_source_coverage_rate is not None:
        lines.append(
            f"| **Retrieval (Dual-source)** | Dual Source Coverage (All) | **{ret_sum.dual_source_coverage_rate * 100:.1f}%** | Casos 'all' mixtos |"
        )

    lines.extend([
        f"| **Abstention** | Abstention Accuracy | **{abst_sum.abstention_accuracy * 100:.1f}%** | {abst_sum.total_cases} (total casos) |",
        f"| **Abstention** | Abstention Precision | **{abst_sum.abstention_precision * 100:.1f}%** (TP={abst_sum.tp_abstain}, FP={abst_sum.fp_abstain}) | {abst_sum.total_cases} |",
        f"| **Abstention** | Abstention Recall | **{abst_sum.abstention_recall * 100:.1f}%** (TP={abst_sum.tp_abstain}, FN={abst_sum.fn_abstain}) | {abst_sum.total_cases} |",
        f"| **Citations** | Final Citation Integrity Rate | **{gen_sum.citation_integrity_rate * 100:.1f}%** | {gen_sum.total_generated_answers} (respuestas generadas) |",
        f"| **Generation Contract** | Traceable Answer Success Rate | **{gen_sum.traceable_answer_success_rate * 100:.1f}%** | {gen_sum.total_answerable_cases} (answerable) |",
        "",
        "---",
        "",
        "## 3. Matriz de Confusión — Source Routing",
        "",
        "| Esperado \\ Predicho | `internal` | `external` | `all` |",
        "| :--- | :--- | :--- | :--- |",
    ])

    for exp_scope in ["internal", "external", "all"]:
        row = r_sum.confusion_matrix.get(exp_scope, {})
        c_int = row.get("internal", 0)
        c_ext = row.get("external", 0)
        c_all = row.get("all", 0)
        lines.append(f"| **`{exp_scope}`** | {c_int} | {c_ext} | {c_all} |")

    lines.extend([
        "",
        "---",
        "",
        "## 4. Matriz de Confusión — Abstención (Clase Positiva = Abstain)",
        "",
        "| Condición Real \\ Decisión Sistema | Abstención (actual_abstained=True) | Respuesta (actual_abstained=False) |",
        "| :--- | :--- | :--- |",
        f"| **No Respondible (answerable=False)** | **True Positive (TP)**: {abst_sum.tp_abstain} | **False Negative (FN)**: {abst_sum.fn_abstain} |",
        f"| **Respondible (answerable=True)** | **False Positive (FP)**: {abst_sum.fp_abstain} | **True Negative (TN)**: {abst_sum.tn_abstain} |",
        "",
        "---",
        "",
        "## 5. Detalle por Caso de Evaluación",
        "",
        "| ID | Cat. | Scope Esp. | Scope Pred. | Hit@K | RR | Citas | Abstained | Traceable Success |",
        "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
    ])

    for c_res in report.cases:
        c = c_res.case
        r = c_res.router_result
        ret = c_res.retrieval_result
        gen = c_res.generation_result

        exp_sc = c.expected_scope or "N/A"
        pred_sc = r.predicted_scope
        hit_str = "✓" if ret.hit_at_k > 0 else ("-" if not c.answerable else "✗")
        rr_str = f"{ret.reciprocal_rank:.2f}" if c.answerable else "-"
        cit_str = f"{gen.final_citation_count} (✓)" if gen.final_citation_integrity_pass else f"{gen.final_citation_count} (✗)"
        abst_str = "Sí" if gen.actual_abstained else "No"
        succ_str = "✓" if gen.traceable_answer_success else "✗"

        lines.append(
            f"| `{c.id}` | `{c.category}` | `{exp_sc}` | `{pred_sc}` | {hit_str} | {rr_str} | {cit_str} | {abst_str} | {succ_str} |"
        )

    # 6. Observaciones y Discrepancias
    failures = []
    for c_res in report.cases:
        c = c_res.case
        reasons = []
        if c.expected_scope is not None and c_res.router_result.is_correct is False:
            reasons.append(f"Routing mismatch (expected '{c.expected_scope}', got '{c_res.router_result.predicted_scope}')")
        if c.answerable and c_res.retrieval_result.hit_at_k == 0.0:
            reasons.append(f"Retrieval miss (expected files {c.expected_files}, retrieved {c_res.retrieval_result.retrieved_files})")
        if c_res.generation_result.abstention_class in ("FP", "FN"):
            reasons.append(f"Abstention discrepancy (class: {c_res.generation_result.abstention_class})")
        if c.answerable and not c_res.generation_result.final_citation_integrity_pass:
            reasons.append("Citation integrity failed")

        if reasons:
            failures.append(f"- **`{c.id}`** ({c.query}): " + "; ".join(reasons))

    lines.extend([
        "",
        "---",
        "",
        "## 6. Registro Objetivo de Discrepancias",
        "",
    ])

    if failures:
        lines.extend(failures)
    else:
        lines.append("No se registraron discrepancias ni fallos en la corrida evaluada.")

    lines.append("")
    return "\n".join(lines)


def save_markdown_summary(
    report: EvaluationReport,
    output_path: Union[str, Path],
) -> None:
    """Generate and save Markdown summary file."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    content = generate_markdown_summary(report)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
