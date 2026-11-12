"""Systematic Evaluation Runner for KnowledgeFlow RAG."""

import argparse
from datetime import datetime, timezone
import logging
from pathlib import Path
import subprocess
import sys
import time
from typing import Optional, Tuple

from app.core.config import Settings, get_settings
from app.evaluation.dataset import (
    has_unreviewed_cases,
    load_dataset,
    validate_dataset_for_official_run,
)
from app.evaluation.metrics import (
    calculate_abstention_summary,
    calculate_generation_summary,
    calculate_retrieval_summary,
    calculate_router_summary,
    evaluate_generation_case,
    evaluate_retrieval_case,
    evaluate_router_case,
)
from app.evaluation.reporter import save_json_report, save_markdown_summary
from app.evaluation.retrieval_utils import retrieve_balanced_raw
from app.evaluation.schemas import (
    CaseEvaluationResult,
    EvaluationDataset,
    EvaluationReport,
    EvaluationRunMetadata,
)
from app.rag.embeddings import GeminiEmbeddings
from app.rag.generator import GeminiRAGGenerator
from app.rag.pipeline import RAGPipeline
from app.rag.retriever import Retriever
from app.rag.vectorstore import VectorStore, verify_index_freshness
from app.agents.source_router import GeminiSourceRouter

logger = logging.getLogger(__name__)


def get_git_metadata() -> Tuple[str, bool]:
    """Retrieve current Git commit hash and dirty status.

    Returns:
        Tuple of (commit_hash, is_dirty).
    """
    try:
        commit_res = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        commit_hash = commit_res.stdout.strip()
    except Exception:
        commit_hash = "unknown"

    try:
        status_res = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            check=True,
        )
        is_dirty = len(status_res.stdout.strip()) > 0
    except Exception:
        is_dirty = False

    return commit_hash, is_dirty


def run_evaluation(
    dataset_path: str = "evaluation/dataset_draft.json",
    output_dir: str = "evaluation/results",
    require_reviewed: bool = False,
    require_clean: bool = False,
    delay_seconds: float = 1.0,
    top_k: Optional[int] = None,
    settings: Optional[Settings] = None,
    pipeline: Optional[RAGPipeline] = None,
) -> EvaluationReport:
    """Execute evaluation over a dataset and save JSON + Markdown reports."""
    cfg = settings or get_settings()
    k = top_k if top_k is not None and top_k > 0 else cfg.retrieval_top_k

    # 1. Check Git status
    git_commit, git_dirty = get_git_metadata()
    if require_clean and git_dirty:
        raise RuntimeError(
            "Working tree is dirty. Cannot proceed with official evaluation run (--require-clean active)."
        )

    # 2. Load and validate dataset
    dataset: EvaluationDataset = load_dataset(dataset_path)
    is_unreviewed = has_unreviewed_cases(dataset)

    if require_reviewed:
        validate_dataset_for_official_run(dataset)
    elif is_unreviewed:
        print("\n====================================================================")
        print("WARNING: Dataset contains human_reviewed=false cases.")
        print("Results are exploratory and must not be presented as final academic evidence.")
        print("====================================================================\n")

    # 3. Initialize Pipeline if not provided
    v_fingerprint = None
    if pipeline is None:
        vdir = cfg.vectorstore_dir
        vectorstore = VectorStore.load_local(vdir)
        if not vectorstore.manifest or not verify_index_freshness(
            vectorstore.manifest, settings=cfg
        ):
            raise RuntimeError(
                "Vector store index is stale. Re-run 'python -m app.rag.indexer' before evaluating."
            )
        v_fingerprint = vectorstore.manifest.fingerprint

        embeddings = GeminiEmbeddings(settings=cfg)
        retriever = Retriever(
            vectorstore=vectorstore, embeddings=embeddings, settings=cfg
        )
        router = GeminiSourceRouter(settings=cfg)
        generator = GeminiRAGGenerator(settings=cfg)
        pipeline = RAGPipeline(
            retriever=retriever,
            router=router,
            generator=generator,
            settings=cfg,
        )
    else:
        if hasattr(pipeline.retriever.vectorstore, "manifest") and pipeline.retriever.vectorstore.manifest:
            v_fingerprint = pipeline.retriever.vectorstore.manifest.fingerprint

    # 4. Evaluate each case
    case_results = []
    total_cases = len(dataset.cases)

    print(f"Starting evaluation of {total_cases} cases from '{dataset_path}' (Top-K={k})...\n")

    for idx, case in enumerate(dataset.cases, start=1):
        print(f"[{idx}/{total_cases}] Evaluating case {case.id} ({case.category})...")

        # Step A: Routing (evaluates router accuracy independently)
        route_decision = pipeline.router.route(case.query)
        r_eval = evaluate_router_case(
            case=case,
            predicted_scope=route_decision.source_scope,
            confidence=route_decision.confidence,
        )

        # Step B: Isolated Retrieval (evaluates retrieval quality independently using case.expected_scope)
        if case.answerable and case.expected_scope is not None:
            if case.expected_scope == "all":
                retrieved_chunks = retrieve_balanced_raw(pipeline.retriever, case.query, top_k=k)
            else:
                retrieved_chunks = pipeline.retriever.search(
                    case.query, k=k, source_type=case.expected_scope
                )
        else:
            retrieved_chunks = []

        ret_eval = evaluate_retrieval_case(
            case=case,
            search_results=retrieved_chunks,
            top_k=k,
            retrieval_scope=case.expected_scope,
        )

        # Step C: End-to-End Generation & Abstention
        rag_answer = pipeline.run(
            query=case.query,
            source_scope=route_decision.source_scope,
            top_k=k,
        )
        gen_eval = evaluate_generation_case(case=case, answer=rag_answer)

        case_record = CaseEvaluationResult(
            case=case,
            router_result=r_eval,
            retrieval_result=ret_eval,
            generation_result=gen_eval,
        )
        case_results.append(case_record)

        if delay_seconds > 0 and idx < total_cases:
            time.sleep(delay_seconds)

    # 5. Calculate aggregated summary metrics
    r_results = [cr.router_result for cr in case_results]
    ret_results = [cr.retrieval_result for cr in case_results]
    gen_results = [cr.generation_result for cr in case_results]

    r_summary = calculate_router_summary(r_results)
    ret_summary = calculate_retrieval_summary(ret_results, dataset.cases)
    abst_summary = calculate_abstention_summary(gen_results)
    gen_summary = calculate_generation_summary(gen_results, dataset.cases)

    # 6. Build EvaluationReport
    run_meta = EvaluationRunMetadata(
        timestamp=datetime.now(timezone.utc).isoformat(),
        git_commit=git_commit,
        git_dirty=git_dirty,
        router_model=cfg.gemini_router_model,
        chat_model=cfg.gemini_chat_model,
        embedding_model=cfg.gemini_embedding_model,
        top_k=k,
        rag_min_similarity=cfg.rag_min_similarity,
        dataset_path=str(dataset_path),
        dataset_version=dataset.version,
        dataset_has_unreviewed=is_unreviewed,
        vector_index_fingerprint=v_fingerprint,
    )

    report = EvaluationReport(
        metadata=run_meta,
        router_summary=r_summary,
        retrieval_summary=ret_summary,
        abstention_summary=abst_summary,
        generation_summary=gen_summary,
        cases=case_results,
    )

    # 7. Persist Report Files
    timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_base = Path(output_dir)
    json_path = out_base / f"evaluation_{timestamp_str}.json"
    md_path = out_base / f"evaluation_{timestamp_str}_summary.md"

    save_json_report(report, json_path)
    save_markdown_summary(report, md_path)

    print("\n====================================================================")
    print("                    EVALUATION RUN COMPLETE                         ")
    print("====================================================================")
    print(f"JSON Report:      {json_path}")
    print(f"Markdown Summary: {md_path}")
    print("--------------------------------------------------------------------")
    print(f"Router Accuracy:             {r_summary.router_accuracy * 100:.1f}% ({r_summary.correct_routes}/{r_summary.total_evaluable_cases})")
    print(f"Retrieval Hit@{k} Rate:       {ret_summary.hit_at_k_rate * 100:.1f}%")
    print(f"Retrieval MRR:               {ret_summary.mean_reciprocal_rank:.4f}")
    print(f"Abstention Accuracy:         {abst_summary.abstention_accuracy * 100:.1f}%")
    print(f"Citation Integrity Rate:     {gen_summary.citation_integrity_rate * 100:.1f}%")
    print(f"Traceable Answer Success:    {gen_summary.traceable_answer_success_rate * 100:.1f}%")
    print("====================================================================\n")

    return report


def main() -> None:
    """CLI entrypoint for evaluation runner."""
    parser = argparse.ArgumentParser(
        description="Run systematic evaluation on KnowledgeFlow RAG dataset"
    )
    parser.add_argument(
        "--dataset",
        type=str,
        default="evaluation/dataset_draft.json",
        help="Path to evaluation dataset JSON file (default: evaluation/dataset_draft.json)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="evaluation/results",
        help="Directory to store evaluation output reports (default: evaluation/results)",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=None,
        help="Top-K retrieval override",
    )
    parser.add_argument(
        "--require-reviewed",
        action="store_true",
        help="Abort if dataset contains cases with human_reviewed=false",
    )
    parser.add_argument(
        "--require-clean",
        action="store_true",
        help="Abort if Git working tree is dirty",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Delay in seconds between case evaluations to respect API rate limits",
    )

    args = parser.parse_args()

    try:
        run_evaluation(
            dataset_path=args.dataset,
            output_dir=args.output_dir,
            require_reviewed=args.require_reviewed,
            require_clean=args.require_clean,
            delay_seconds=args.delay,
            top_k=args.top_k,
        )
    except Exception as e:
        print(f"\nEvaluation failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
