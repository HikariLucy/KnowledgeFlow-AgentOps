"""Unit and integration tests for the Hito 5 AgentOps experimental benchmark."""

import asyncio
from base64 import b64encode
from pathlib import Path
from types import SimpleNamespace

from fastapi import FastAPI
import httpx
from pydantic import SecretStr
import pytest

from app.api.dashboard_routes import router as dashboard_router
from app.api.observability_routes import router as obs_router
from app.evaluation.agentops_dataset import AgentOpsDataset, load_agentops_dataset
from app.evaluation.agentops_metrics import (
    CaseExecutionRecord,
    are_runs_equivalent,
    compute_benchmark_metrics,
)
from app.evaluation.agentops_runner import (
    LiveBenchmarkDisabledError,
    run_agentops_benchmark,
)
from app.evaluation.quality_store import read_quality_summary


def test_load_agentops_dataset_v1_validates_and_separates_sources():
    dataset = load_agentops_dataset("evaluation/agentops/dataset_v1.json")
    assert len(dataset.cases) >= 14
    sources = {c.document_source for c in dataset.cases}
    assert sources == {"corpus_verified", "synthetic_fixture"}
    assert any(not c.human_reviewed for c in dataset.cases)
    assert any(c.consistency_group for c in dataset.cases)


def test_empty_records_return_null_metrics_never_zero():
    metrics = compute_benchmark_metrics(
        [],
        data_source="empty",
        period="n/a",
        limitations="empty dataset",
    )
    for key in ("task_accuracy", "retrieval_precision", "consistency", "error_rate", "tool_accuracy", "abstention_accuracy"):
        assert metrics[key]["value"] is None
        assert metrics[key]["denominator"] == 0
    assert metrics["latency_ms"]["mean"] is None
    assert metrics["counts"]["total_executions"] == 0


def test_consistency_semantic_equivalence_not_strict_equality():
    base = CaseExecutionRecord(
        case_id="C1",
        scenario="rag_internal",
        execution_mode="offline",
        document_source="corpus_verified",
        human_reviewed=True,
        consistency_group="cg1",
        status="completed",
        intent="knowledge_query",
        tool_calls=["search_knowledge"],
        retrieved_files=["politica_accesos.md"],
        output_summary="La contraseña requiere mínimo 14 caracteres combinando símbolos y números.",
    )
    paraphrase = base.model_copy(
        update={
            "repeat_index": 1,
            "output_summary": "Contraseña interna exige mínimo 14 caracteres con números y símbolos.",
        }
    )
    different_tool = base.model_copy(
        update={
            "repeat_index": 2,
            "tool_calls": ["create_incident"],
        }
    )
    assert are_runs_equivalent(base, paraphrase) is True
    assert are_runs_equivalent(base, different_tool) is False


def test_unreviewed_cases_excluded_from_evaluable_denominator():
    reviewed_ok = CaseExecutionRecord(
        case_id="R1",
        scenario="rag_internal",
        execution_mode="offline",
        document_source="corpus_verified",
        human_reviewed=True,
        evaluable=True,
        status="completed",
        task_correct=True,
        tool_correct=True,
        duration_ms=12.0,
    )
    unreviewed = CaseExecutionRecord(
        case_id="U1",
        scenario="security_robustness",
        execution_mode="offline",
        document_source="synthetic_fixture",
        human_reviewed=False,
        evaluable=False,
        status="abstained",
        task_correct=None,
        tool_correct=None,
        duration_ms=8.0,
    )
    metrics = compute_benchmark_metrics(
        [reviewed_ok, unreviewed],
        data_source="test",
        period="now",
        limitations="unit test",
    )
    assert metrics["counts"]["total_executions"] == 2
    assert metrics["counts"]["evaluable_executions"] == 1
    assert metrics["counts"]["pending_validation_cases"] == 1
    assert metrics["task_accuracy"]["denominator"] == 1
    assert metrics["task_accuracy"]["value"] == 1.0


def test_live_benchmark_blocked_by_default():
    dataset = AgentOpsDataset(description="empty test", cases=[])
    with pytest.raises(LiveBenchmarkDisabledError):
        run_agentops_benchmark(dataset, mode="live")


def test_runner_executes_dataset_v1_offline_and_exports_json_csv(tmp_path):
    dataset = load_agentops_dataset("evaluation/agentops/dataset_v1.json")
    report = run_agentops_benchmark(
        dataset,
        mode="offline",
        repeats=3,
        output_dir=tmp_path,
        dataset_path="evaluation/agentops/dataset_v1.json",
    )
    assert report["not_live_gemini_evidence"] is True
    assert report["provider_mode"] == "deterministic_offline_stub"
    m = report["metrics"]
    assert m["counts"]["pending_validation_cases"] == 1
    assert m["counts"]["evaluable_executions"] >= 14
    assert m["task_accuracy"]["value"] is not None
    assert m["consistency"]["value"] is not None
    assert m["retrieval_precision"]["value"] is not None
    assert m["error_rate"]["value"] is not None
    assert m["tool_accuracy"]["value"] is not None
    assert m["abstention_accuracy"]["value"] is not None
    assert m["latency_ms"]["p95"] is not None

    run_id = report["run_id"]
    assert (tmp_path / f"{run_id}.json").is_file()
    assert (tmp_path / f"{run_id}.csv").is_file()
    assert (tmp_path / "latest_offline.json").is_file()

    # Mode isolation: offline result must not populate mock or live
    assert read_quality_summary(tmp_path, "offline")["status"] == "evaluated"
    assert read_quality_summary(tmp_path, "mock")["status"] == "not_evaluated"
    assert read_quality_summary(tmp_path, "live")["status"] == "not_evaluated"
    assert read_quality_summary(tmp_path, "unknown")["status"] == "not_evaluated"


def test_quality_api_and_dashboard_integration(tmp_path):
    dataset = load_agentops_dataset("evaluation/agentops/dataset_v1.json")
    run_agentops_benchmark(dataset, mode="offline", repeats=2, output_dir=tmp_path)

    app = FastAPI()
    app.include_router(obs_router)
    app.include_router(dashboard_router)
    app.state.observability_settings = SimpleNamespace(
        obs_dashboard_enabled=True,
        obs_dashboard_password=SecretStr("dashboard-password-for-quality-tests-32b"),
        obs_read_key=SecretStr("observability-read-key-for-quality-tests"),
        obs_quality_dir=str(tmp_path),
    )
    app.state.observability_store = None

    auth = "Basic " + b64encode(b"observer:dashboard-password-for-quality-tests-32b").decode()

    async def _call(path, headers):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app, client=("127.0.0.1", 1234)),
            base_url="http://127.0.0.1",
        ) as session:
            return await session.get(path, headers=headers)

    # /api/observability/quality (Hito 3 API key)
    r_obs_off = asyncio.run(_call(
        "/api/observability/quality?execution_mode=offline",
        {"X-Observability-Key": "observability-read-key-for-quality-tests"},
    ))
    assert r_obs_off.status_code == 200
    body_off = r_obs_off.json()
    assert body_off["status"] == "evaluated"
    assert body_off["precision"] is not None
    assert body_off["consistency"] is not None
    assert len(body_off["benchmarks"]) == 1

    # Mock remains not_evaluated (N/D)
    r_obs_mock = asyncio.run(_call(
        "/api/observability/quality?execution_mode=mock",
        {"X-Observability-Key": "observability-read-key-for-quality-tests"},
    ))
    assert r_obs_mock.status_code == 200
    assert r_obs_mock.json()["status"] == "not_evaluated"
    assert r_obs_mock.json()["precision"] is None

    # /dashboard/api/quality (HTTP Basic)
    r_dash = asyncio.run(_call("/dashboard/api/quality?execution_mode=offline", {"Authorization": auth}))
    assert r_dash.status_code == 200
    assert r_dash.json()["status"] == "evaluated"

    # Dashboard HTML contains quality scenario container
    r_html = asyncio.run(_call("/dashboard", {"Authorization": auth}))
    assert r_html.status_code == 200
    assert "quality-scenarios" in r_html.text
