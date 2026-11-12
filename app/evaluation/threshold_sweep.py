"""Threshold sweep calibration tool for evaluating similarity thresholds on retrieval results."""

import argparse
import math
from pathlib import Path
import sys
from typing import Dict, List, Optional

from app.core.config import Settings, get_settings
from app.evaluation.dataset import load_dataset
from app.evaluation.schemas import EvaluationDataset
from app.rag.embeddings import GeminiEmbeddings
from app.rag.pipeline import RAGPipeline
from app.rag.retriever import Retriever
from app.rag.schemas import SearchResult
from app.rag.vectorstore import VectorStore, verify_index_freshness
from app.agents.source_router import GeminiSourceRouter


def run_threshold_sweep(
    dataset_path: str = "evaluation/dataset_draft.json",
    thresholds: Optional[List[float]] = None,
    top_k: int = 4,
    settings: Optional[Settings] = None,
    pipeline: Optional[RAGPipeline] = None,
) -> Dict[str, Dict[str, float]]:
    """Perform similarity threshold sweep over retrieval scores without LLM generation calls.

    Retrieval is executed exactly once per query. Different thresholds are evaluated locally
    in memory against the retrieved similarity scores.

    Args:
        dataset_path: Path to dataset JSON.
        thresholds: List of float thresholds (defaults to [0.50, 0.55, 0.60, 0.65, 0.70, 0.75]).
        top_k: Number of Top-K results.
        settings: Application Settings.
        pipeline: Optional initialized RAGPipeline.

    Returns:
        Dictionary mapping each threshold string to its observed behavior metrics.
    """
    if thresholds is None:
        thresholds = [0.50, 0.55, 0.60, 0.65, 0.70, 0.75]

    cfg = settings or get_settings()
    dataset: EvaluationDataset = load_dataset(dataset_path)

    # Initialize Pipeline if needed
    if pipeline is None:
        vdir = cfg.vectorstore_dir
        vectorstore = VectorStore.load_local(vdir)
        if not vectorstore.manifest or not verify_index_freshness(
            vectorstore.manifest, settings=cfg
        ):
            raise RuntimeError(
                "Vector store index is stale. Re-run 'python -m app.rag.indexer' before evaluating."
            )
        embeddings = GeminiEmbeddings(settings=cfg)
        retriever = Retriever(
            vectorstore=vectorstore, embeddings=embeddings, settings=cfg
        )
        router = GeminiSourceRouter(settings=cfg)
        pipeline = RAGPipeline(
            retriever=retriever,
            router=router,
            settings=cfg,
        )

    # 1. Collect single retrieval pass per query with no threshold filter
    print(f"Retrieving raw candidates once for each of the {len(dataset.cases)} cases...")
    cached_retrievals: List[Dict[str, object]] = []

    quota_int = math.ceil(top_k / 2)
    quota_ext = top_k - quota_int

    for idx, case in enumerate(dataset.cases, start=1):
        decision = pipeline.router.route(case.query)
        scope = decision.source_scope

        # Retrieve raw candidates without min_similarity filtering
        if scope == "all":
            raw_int = pipeline.retriever.search(case.query, k=top_k, source_type="internal")
            raw_ext = pipeline.retriever.search(case.query, k=top_k, source_type="external")
            cached_retrievals.append({
                "case": case,
                "scope": "all",
                "raw_internal": raw_int,
                "raw_external": raw_ext,
            })
        elif scope in ("internal", "external"):
            raw_chunks = pipeline.retriever.search(case.query, k=top_k, source_type=scope)
            cached_retrievals.append({
                "case": case,
                "scope": scope,
                "chunks": raw_chunks,
            })
        else:
            raw_chunks = pipeline.retriever.search(case.query, k=top_k)
            cached_retrievals.append({
                "case": case,
                "scope": scope,
                "chunks": raw_chunks,
            })

    # 2. Evaluate thresholds locally in memory
    results_by_threshold: Dict[str, Dict[str, float]] = {}
    answerable_cases = [c for c in dataset.cases if c.answerable]
    total_ans = len(answerable_cases)
    out_of_domain_cases = [c for c in dataset.cases if not c.answerable]
    total_ood = len(out_of_domain_cases)

    for thresh in thresholds:
        retained_ans = 0
        false_abstentions = 0
        correct_abstentions = 0
        ood_accepted = 0
        hits_count = 0

        for item in cached_retrievals:
            case = item["case"]
            scope = item["scope"]

            if scope == "all":
                raw_i: List[SearchResult] = item["raw_internal"]  # type: ignore
                raw_e: List[SearchResult] = item["raw_external"]  # type: ignore

                valid_i = [ch for ch in raw_i if ch.score >= thresh]
                valid_e = [ch for ch in raw_e if ch.score >= thresh]

                sel_i = valid_i[:quota_int]
                sel_e = valid_e[:quota_ext]

                i_def = quota_int - len(sel_i)
                e_def = quota_ext - len(sel_e)

                if i_def > 0 and len(valid_e) > quota_ext:
                    sel_e = valid_e[: quota_ext + i_def]
                elif e_def > 0 and len(valid_i) > quota_int:
                    sel_i = valid_i[: quota_int + e_def]

                comb = sel_i + sel_e
                comb.sort(key=lambda x: x.score, reverse=True)
                valid = comb[:top_k]
            else:
                chunks: List[SearchResult] = item["chunks"]  # type: ignore
                valid = [ch for ch in chunks if ch.score >= thresh][:top_k]

            is_abstained = (len(valid) == 0)

            if case.answerable:
                if not is_abstained:
                    retained_ans += 1
                    ret_files = [str(ch.document.metadata.get("file_name", "")) for ch in valid]
                    if any(ef in ret_files for ef in case.expected_files):
                        hits_count += 1
                else:
                    false_abstentions += 1
            else:
                if is_abstained:
                    correct_abstentions += 1
                else:
                    ood_accepted += 1

        ans_retention_rate = retained_ans / total_ans if total_ans > 0 else 0.0
        false_abst_rate = false_abstentions / total_ans if total_ans > 0 else 0.0
        ood_abst_rate = correct_abstentions / total_ood if total_ood > 0 else 0.0
        ood_leak_rate = ood_accepted / total_ood if total_ood > 0 else 0.0
        hit_rate = hits_count / total_ans if total_ans > 0 else 0.0

        key = f"{thresh:.2f}"
        results_by_threshold[key] = {
            "threshold": thresh,
            "answerable_retained_rate": round(ans_retention_rate, 4),
            "false_abstention_rate": round(false_abst_rate, 4),
            "correct_ood_abstention_rate": round(ood_abst_rate, 4),
            "ood_leakage_rate": round(ood_leak_rate, 4),
            "hit_at_k_rate": round(hit_rate, 4),
        }

    # 3. Print Objective Comparison Table
    print("\n==========================================================================================")
    print("                    SIMILARITY THRESHOLD SWEEP ANALYSIS                                  ")
    print("==========================================================================================")
    print("Nota: Esta tabla presenta datos objetivos observados para análisis humano de compensaciones.")
    print("El sistema no categoriza ningún umbral como óptimo.")
    print("------------------------------------------------------------------------------------------")
    print(f"{'Threshold':<11} | {'Ans. Retained':<14} | {'False Abst.':<12} | {'OOD Abst. (Correct)':<20} | {'OOD Leaked':<11} | {'Hit@K':<8}")
    print("------------------------------------------------------------------------------------------")
    for key, data in results_by_threshold.items():
        print(
            f"{key:<11} | "
            f"{data['answerable_retained_rate'] * 100:>12.1f}% | "
            f"{data['false_abstention_rate'] * 100:>10.1f}% | "
            f"{data['correct_ood_abstention_rate'] * 100:>18.1f}% | "
            f"{data['ood_leakage_rate'] * 100:>9.1f}% | "
            f"{data['hit_at_k_rate'] * 100:>6.1f}%"
        )
    print("==========================================================================================\n")

    return results_by_threshold


def main() -> None:
    """CLI argument parser for threshold sweep."""
    parser = argparse.ArgumentParser(
        description="Run similarity threshold sweep on evaluation dataset without full generation"
    )
    parser.add_argument(
        "--dataset",
        type=str,
        default="evaluation/dataset_draft.json",
        help="Path to evaluation dataset JSON file",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=4,
        help="Top-K retrieval parameter",
    )
    parser.add_argument(
        "--thresholds",
        type=float,
        nargs="+",
        default=[0.50, 0.55, 0.60, 0.65, 0.70, 0.75],
        help="List of similarity thresholds to test (e.g. 0.50 0.55 0.60 0.65 0.70 0.75)",
    )

    args = parser.parse_args()

    try:
        run_threshold_sweep(
            dataset_path=args.dataset,
            thresholds=args.thresholds,
            top_k=args.top_k,
        )
    except Exception as e:
        print(f"Threshold sweep failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
