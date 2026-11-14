"""Read-only loader for evaluated benchmark quality results per execution mode."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.observability.models import ExecutionMode


def empty_quality_response(execution_mode: ExecutionMode) -> dict[str, Any]:
    """Return the canonical N/D quality contract when no validated benchmark exists."""
    return {
        "contract_version": 1,
        "execution_mode": execution_mode,
        "source": "evaluated_benchmarks",
        "status": "not_evaluated",
        "precision": None,
        "consistency": None,
        "benchmarks": [],
    }


def read_quality_summary(quality_dir: Path | str | None, execution_mode: ExecutionMode) -> dict[str, Any]:
    """Read the latest sanitized benchmark summary for the requested execution_mode."""
    if quality_dir is None or execution_mode not in {"offline", "mock", "live"}:
        return empty_quality_response(execution_mode)

    target = Path(quality_dir) / f"latest_{execution_mode}.json"
    if not target.is_file():
        return empty_quality_response(execution_mode)

    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return empty_quality_response(execution_mode)

    if not isinstance(data, dict) or data.get("execution_mode") != execution_mode:
        return empty_quality_response(execution_mode)

    metrics = data.get("metrics") or {}
    task_acc = (metrics.get("task_accuracy") or {}).get("value")
    consistency = (metrics.get("consistency") or {}).get("value")
    counts = metrics.get("counts") or {}

    if task_acc is None and consistency is None:
        return empty_quality_response(execution_mode)

    summary = {
        "run_id": data.get("run_id"),
        "benchmark_version": data.get("benchmark_version"),
        "dataset_version": data.get("dataset_version"),
        "generated_at": data.get("generated_at"),
        "git_sha": data.get("git_sha"),
        "execution_mode": execution_mode,
        "synthetic": bool(data.get("synthetic", False)),
        "provider_mode": data.get("provider_mode"),
        "not_live_gemini_evidence": bool(data.get("not_live_gemini_evidence", True)),
        "sample_size": counts.get("evaluable_executions", 0),
        "correct_cases": counts.get("correct_cases", 0),
        "incorrect_cases": counts.get("incorrect_cases", 0),
        "pending_validation_cases": counts.get("pending_validation_cases", 0),
        "by_scenario": metrics.get("by_scenario", {}),
        "metrics": {
            "task_accuracy": metrics.get("task_accuracy"),
            "retrieval_precision": metrics.get("retrieval_precision"),
            "consistency": metrics.get("consistency"),
            "error_rate": metrics.get("error_rate"),
            "tool_accuracy": metrics.get("tool_accuracy"),
            "abstention_accuracy": metrics.get("abstention_accuracy"),
            "latency_ms": metrics.get("latency_ms"),
        },
        "limitations": (metrics.get("task_accuracy") or {}).get("limitations"),
    }

    return {
        "contract_version": 1,
        "execution_mode": execution_mode,
        "source": "evaluated_benchmarks",
        "status": "evaluated",
        "precision": task_acc,
        "consistency": consistency,
        "benchmarks": [summary],
    }
