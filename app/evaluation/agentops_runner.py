"""Deterministic offline/mock benchmark runner for KnowledgeFlow AgentOps (Hito 5)."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
import time
from typing import Any, Optional
import uuid

from app.agentic.orchestrator import AdaptiveOrchestrator
from app.agentic.planner import RuleBasedPlanner
from app.agentic.state import AgentState
from app.evaluation.agentops_dataset import AgentOpsCase, AgentOpsDataset, load_agentops_dataset
from app.evaluation.agentops_metrics import (
    CaseExecutionRecord,
    compute_benchmark_metrics,
    evaluate_case_record,
)
from app.memory.short_term import ShortTermMemory
from app.memory.write_back import MemoryWriteBack
from app.storage.database import SQLiteDatabase
from app.storage.models import IncidentCreate
from app.storage.repositories import IncidentRepository
from app.tools.incidents import (
    AppendIncidentNoteTool,
    CreateIncidentTool,
    SearchIncidentsTool,
)
from app.tools.schemas import (
    AppendIncidentNoteDraft,
    CreateIncidentInput,
    KnowledgeQueryInput,
    KnowledgeQueryResult,
    KnowledgeSource,
    SearchIncidentsInput,
)

BENCHMARK_VERSION = "agentops-benchmark-v1.0"


class LiveBenchmarkDisabledError(RuntimeError):
    """Raised when live evaluation is requested without explicit opt-in."""


class DeterministicOfflineKnowledgeTool:
    """Offline deterministic double for search_knowledge; never calls Gemini."""

    name = "search_knowledge"

    def __init__(self, case: AgentOpsCase) -> None:
        self.case = case

    def run(self, arguments: KnowledgeQueryInput) -> KnowledgeQueryResult:
        inp = self.case.input
        if inp.get("simulate_tool_error") == "search_knowledge":
            raise RuntimeError("Simulated offline search_knowledge tool failure")

        scope = arguments.source_scope or "internal"
        if inp.get("abstain_retrieval"):
            return KnowledgeQueryResult(
                query=arguments.query,
                source_scope=scope,
                answer="No encontré evidencia suficiente en el corpus.",
                citations=[],
                sources=[],
                abstained=True,
            )

        exp = self.case.expected_result
        files = list(exp.expected_files) or ["politica_accesos.md"]
        keywords = " ".join(exp.expected_keywords)
        sources = [
            KnowledgeSource(
                id=f"S{idx + 1}",
                file_name=fname,
                source_type=(
                    "external"
                    if any(tag in fname for tag in ("owasp", "nist", "guia_", "referencia_"))
                    else "internal"
                ),
                chunk_index=0,
                score=0.91,
            )
            for idx, fname in enumerate(files)
        ]
        citations = [s.id for s in sources]
        citation_str = " ".join(f"[{c}]" for c in citations)
        answer = f"Evidencia offline recuperada ({keywords}) {citation_str}.".strip()
        return KnowledgeQueryResult(
            query=arguments.query,
            source_scope=scope,
            answer=answer,
            citations=citations,
            sources=sources,
            abstained=False,
        )


def _git_sha(repo_root: Optional[Path] = None) -> str:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(repo_root or Path.cwd()),
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=2,
        )
        return out.strip() or "unknown"
    except Exception:
        return "unknown"


def _build_tool_inputs(case: AgentOpsCase, preseeded_ids: list[str]) -> dict[str, Any]:
    inp = case.input
    tool_inputs: dict[str, Any] = {}
    if "knowledge_query" in inp and inp["knowledge_query"] is not None:
        tool_inputs["search_knowledge"] = KnowledgeQueryInput(**inp["knowledge_query"])
    if "create_incident" in inp and inp["create_incident"] is not None:
        tool_inputs["create_incident"] = CreateIncidentInput(**inp["create_incident"])
    if "search_incidents" in inp and inp["search_incidents"] is not None:
        tool_inputs["search_incidents"] = SearchIncidentsInput(**inp["search_incidents"])
    if "append_incident_note" in inp and inp["append_incident_note"] is not None:
        note_payload = dict(inp["append_incident_note"])
        if inp.get("use_preseeded_incident_id") and preseeded_ids and not note_payload.get("incident_id"):
            note_payload["incident_id"] = preseeded_ids[0]
        tool_inputs["append_incident_note"] = AppendIncidentNoteDraft(**note_payload)
    return tool_inputs


def _run_single_case(
    case: AgentOpsCase,
    *,
    mode: str,
    repeat_index: int,
) -> CaseExecutionRecord:
    """Execute one benchmark case inside an isolated temporary SQLite database."""
    with TemporaryDirectory() as tmp_dir:
        db = SQLiteDatabase(Path(tmp_dir) / "benchmark_incidents.db")
        db.initialize()
        repo = IncidentRepository(db)

        preseeded_ids: list[str] = []
        for item in case.input.get("preseed_incidents", []):
            created = repo.create_incident(
                IncidentCreate(
                    title=item["title"],
                    description=item["description"],
                    category=item.get("category", "security"),
                    severity=item.get("severity", "medium"),
                )
            )
            preseeded_ids.append(created.public_id)

        short_term_memory = ShortTermMemory(max_turns=10)
        memory_write_back = MemoryWriteBack(short_term_memory=short_term_memory, semantic_memory=None)
        planner = RuleBasedPlanner(short_term_memory=short_term_memory, semantic_memory=None)
        orchestrator = AdaptiveOrchestrator(
            planner=planner,
            knowledge_tool=DeterministicOfflineKnowledgeTool(case),
            create_incident_tool=CreateIncidentTool(repo),
            search_incidents_tool=SearchIncidentsTool(repo),
            append_incident_note_tool=AppendIncidentNoteTool(repo),
            memory_write_back=memory_write_back,
        )

        conv_id = str(case.input.get("conversation_id") or f"bench-{case.id}-{repeat_index}")
        for turn in case.input.get("preseed_turns", []):
            turn_state = AgentState(conversation_id=conv_id, user_request=turn["message"])
            turn_inputs: dict[str, Any] = {}
            if "create_incident" in turn:
                turn_inputs["create_incident"] = CreateIncidentInput(**turn["create_incident"])
            orchestrator.execute(turn_state, tool_inputs=turn_inputs)

        before_target_count = len(repo.search_incidents(""))
        msg = str(case.input["message"])
        if preseeded_ids and "{preseeded_id}" in msg:
            msg = msg.replace("{preseeded_id}", preseeded_ids[0])
        state = AgentState(conversation_id=conv_id, user_request=msg)
        tool_inputs = _build_tool_inputs(case, preseeded_ids)

        started = time.perf_counter()
        try:
            result = orchestrator.execute(state, tool_inputs=tool_inputs)
            duration_ms = (time.perf_counter() - started) * 1000.0
            status_val = result.status.value
            intent_val = result.state.intent
            tool_calls = list(result.state.tool_calls)
            retrieved_files = [
                str(s.get("file_name", ""))
                for s in result.state.retrieved_context
                if s.get("file_name")
            ]
            req_clarif = result.state.requires_clarification
            output_text = result.output or ""
            error_type = "tool_error" if status_val == "failed" else None
        except Exception:
            duration_ms = (time.perf_counter() - started) * 1000.0
            status_val = "failed"
            intent_val = state.intent
            tool_calls = list(state.tool_calls) or ([inp["simulate_tool_error"]] if inp.get("simulate_tool_error") else [])
            retrieved_files = []
            req_clarif = False
            output_text = ""
            error_type = "tool_error"

        after_target_count = len(repo.search_incidents(""))
        mutated_incidents = (after_target_count != before_target_count) or (
            "append_incident_note" in tool_calls
        )

        return evaluate_case_record(
            case,
            status=status_val,
            intent=intent_val,
            tool_calls=tool_calls,
            retrieved_files=retrieved_files,
            requires_clarification=req_clarif,
            mutated_incidents=mutated_incidents,
            duration_ms=duration_ms,
            output_text=output_text,
            execution_mode=mode,
            repeat_index=repeat_index,
            error_type=error_type,
            trace_id=uuid.uuid4().hex,
        )


def run_agentops_benchmark(
    dataset: AgentOpsDataset,
    *,
    mode: str = "offline",
    scenario: Optional[str] = None,
    repeats: int = 3,
    allow_live: bool = False,
    output_dir: Optional[Path] = None,
    dataset_path: Optional[str] = None,
) -> dict[str, Any]:
    """Run the AgentOps experimental benchmark and return a sanitized summary report."""
    if mode not in {"offline", "mock", "live"}:
        raise ValueError(f"Unsupported benchmark mode: {mode}")
    if repeats < 1:
        raise ValueError("repeats must be >= 1")

    if mode == "live":
        env_allowed = os.getenv("ALLOW_LIVE_BENCHMARK", "").lower() == "true"
        if not (allow_live and env_allowed):
            raise LiveBenchmarkDisabledError(
                "Live benchmark is disabled by default. Set ALLOW_LIVE_BENCHMARK=true and pass allow_live=True explicitly."
            )
        raise LiveBenchmarkDisabledError(
            "Live Gemini benchmark execution is not enabled in Hito 5; configure a live runner explicitly in a controlled phase."
        )

    selected = [
        c for c in dataset.cases
        if (scenario is None or c.scenario == scenario) and mode in c.execution_modes
    ]

    started_at = datetime.now(timezone.utc)
    records: list[CaseExecutionRecord] = []
    for case in selected:
        n_runs = repeats if case.consistency_group else 1
        for rep in range(n_runs):
            records.append(_run_single_case(case, mode=mode, repeat_index=rep))

    ended_at = datetime.now(timezone.utc)
    run_id = f"ao-{mode}-{started_at.strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:8]}"
    git_sha = _git_sha()
    period = f"{started_at.isoformat()} -> {ended_at.isoformat()}"
    limitations = (
        f"Ejecución determinista en modo '{mode}' con herramientas de conocimiento simuladas "
        "(sin llamadas reales a Gemini ni FAISS externo) y SQLite temporal aislado. "
        "Los tiempos medidos reflejan el orquestador local y doubles, no latencia de proveedor real."
    )

    metrics = compute_benchmark_metrics(
        records,
        data_source=dataset_path or "evaluation/agentops/dataset_v1.json",
        period=period,
        limitations=limitations,
    )

    report = {
        "contract_version": 1,
        "benchmark_version": BENCHMARK_VERSION,
        "dataset_version": dataset.version,
        "run_id": run_id,
        "git_sha": git_sha,
        "generated_at": ended_at.isoformat(),
        "execution_mode": mode,
        "synthetic": mode == "mock" or any(r.document_source == "synthetic_fixture" for r in records),
        "provider_mode": "deterministic_offline_stub",
        "not_live_gemini_evidence": True,
        "scenario_filter": scenario,
        "repeats": repeats,
        "metrics": metrics,
        "cases": [r.model_dump() for r in records],
    }

    if output_dir is not None:
        export_benchmark_report(report, output_dir)

    return report


def export_benchmark_report(report: dict[str, Any], output_dir: Path) -> tuple[Path, Path]:
    """Persist sanitized JSON and CSV benchmark artifacts."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    mode = report["execution_mode"]
    run_id = report["run_id"]

    json_path = out / f"{run_id}.json"
    latest_path = out / f"latest_{mode}.json"
    csv_path = out / f"{run_id}.csv"

    serialized = json.dumps(report, indent=2, ensure_ascii=False)
    json_path.write_text(serialized, encoding="utf-8")
    latest_path.write_text(serialized, encoding="utf-8")

    fieldnames = [
        "case_id",
        "scenario",
        "repeat_index",
        "execution_mode",
        "document_source",
        "human_reviewed",
        "status",
        "intent",
        "tool_calls",
        "retrieved_files",
        "task_correct",
        "tool_correct",
        "abstention_correct",
        "duration_ms",
        "trace_id",
    ]
    with open(csv_path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in report.get("cases", []):
            writer.writerow({
                "case_id": row["case_id"],
                "scenario": row["scenario"],
                "repeat_index": row["repeat_index"],
                "execution_mode": row["execution_mode"],
                "document_source": row["document_source"],
                "human_reviewed": row["human_reviewed"],
                "status": row["status"],
                "intent": row["intent"],
                "tool_calls": ",".join(row.get("tool_calls", [])),
                "retrieved_files": ",".join(row.get("retrieved_files", [])),
                "task_correct": row["task_correct"],
                "tool_correct": row["tool_correct"],
                "abstention_correct": row["abstention_correct"],
                "duration_ms": row["duration_ms"],
                "trace_id": row["trace_id"],
            })
    return json_path, csv_path


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="KnowledgeFlow AgentOps offline benchmark runner")
    parser.add_argument("--dataset", default="evaluation/agentops/dataset_v1.json")
    parser.add_argument("--mode", default="offline", choices=["offline", "mock", "live"])
    parser.add_argument("--scenario", default=None)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--output-dir", default="evaluation/agentops/results")
    args = parser.parse_args(argv)

    dataset = load_agentops_dataset(args.dataset)
    report = run_agentops_benchmark(
        dataset,
        mode=args.mode,
        scenario=args.scenario,
        repeats=args.repeats,
        output_dir=Path(args.output_dir),
        dataset_path=args.dataset,
    )
    m = report["metrics"]
    print(
        f"run_id={report['run_id']} mode={report['execution_mode']} "
        f"task_accuracy={m['task_accuracy']['value']} consistency={m['consistency']['value']} "
        f"evaluable={m['counts']['evaluable_executions']} pending={m['counts']['pending_validation_cases']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
