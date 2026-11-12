"""Offline unit tests for UI Preview Server, fixture validation, and corpus fidelity."""

from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.main import app as prod_app
from app.rag.schemas import QueryResponse
from scripts.ui_preview import app as preview_app, FIXTURES_PATH, PreviewRAGPipeline

preview_client = TestClient(preview_app)
prod_client = TestClient(prod_app)

KNOWLEDGE_ROOT = Path(__file__).resolve().parent.parent / "knowledge"


def test_production_app_is_not_polluted_by_preview_import():
    """Verify that importing scripts.ui_preview does NOT pollute prod_app.dependency_overrides."""
    assert prod_app.dependency_overrides == {}


def test_preview_fixtures_file_exists_and_validates():
    """Verify preview fixture file exists and all scenarios match QueryResponse schema."""
    assert FIXTURES_PATH.exists()
    pipeline = PreviewRAGPipeline(FIXTURES_PATH)
    assert len(pipeline.fixtures) >= 5

    for scenario_name, scenario_data in pipeline.fixtures.items():
        # Validate that each fixture fits QueryResponse
        response_model = QueryResponse(**scenario_data)
        assert response_model.query is not None
        assert response_model.source_scope in ["internal", "external", "all"]


def test_preview_fixtures_corpus_fidelity():
    """Verify that every source in every fixture exists in the real knowledge corpus."""
    pipeline = PreviewRAGPipeline(FIXTURES_PATH)
    disallowed_filenames = {
        "politica_contrasenas.md",
        "procedimiento_seguridad.md",
        "owasp_top_10_llm_overview.md",
    }

    for scenario_name, scenario in pipeline.fixtures.items():
        sources = scenario.get("sources", [])
        for src in sources:
            file_name = src["file_name"]
            source_type = src["source_type"]

            # 1. Assert file is not among invented/disallowed names
            assert file_name not in disallowed_filenames, f"Found disallowed file '{file_name}' in scenario '{scenario_name}'"

            # 2. Assert physical file actually exists under knowledge/{source_type}/
            expected_path = KNOWLEDGE_ROOT / source_type / file_name
            assert expected_path.exists(), f"Corpus file '{expected_path}' does not exist for scenario '{scenario_name}'"


def test_preview_internal_fixture_content_fidelity():
    """Verify that internal password fixture is faithful to politica_accesos.md."""
    pipeline = PreviewRAGPipeline(FIXTURES_PATH)
    internal_scenario = pipeline.fixtures["internal"]

    # Must use politica_accesos.md
    assert internal_scenario["sources"][0]["file_name"] == "politica_accesos.md"

    # Must mention 14 caracteres, MFA, and NOT invent 12 caracteres or 'últimas 5'
    answer_text = internal_scenario["answer"]
    assert "14 caracteres" in answer_text
    assert "12 caracteres" not in answer_text
    assert "últimas 5" not in answer_text


def test_preview_ui_root_serves_html():
    """Verify GET / on preview app returns 200 with UI HTML."""
    response = preview_client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert "KnowledgeFlow" in response.text


def test_preview_health_endpoint():
    """Verify GET /health on preview app returns preview mode."""
    response = preview_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["mode"] == "preview_offline"


def test_preview_scenario_a_internal():
    """Verify preview returns internal scenario with politica_accesos.md and S1 citation."""
    response = preview_client.post(
        "/api/query",
        json={"query": "¿Qué requisitos deben cumplir las contraseñas internas?"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["source_scope"] == "internal"
    assert data["abstained"] is False
    assert "S1" in data["citations"]
    assert len(data["sources"]) >= 1
    assert data["sources"][0]["file_name"] == "politica_accesos.md"
    assert all(s["source_type"] == "internal" for s in data["sources"])


def test_preview_scenario_b_external():
    """Verify preview returns external scenario with real OWASP source."""
    response = preview_client.post(
        "/api/query",
        json={"query": "¿Cómo se previene Prompt Injection según OWASP?"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["source_scope"] == "external"
    assert data["abstained"] is False
    assert "S1" in data["citations"]
    assert data["sources"][0]["file_name"] == "owasp_llm_prompt_injection_prevention.md"
    assert all(s["source_type"] == "external" for s in data["sources"])


def test_preview_scenario_c_mixed():
    """Verify preview returns mixed scenario with both internal and external sources."""
    response = preview_client.post(
        "/api/query",
        json={"query": "Compara el procedimiento interno de incidentes con buenas prácticas externas."},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["source_scope"] == "all"
    assert data["abstained"] is False
    source_types = {s["source_type"] for s in data["sources"]}
    assert "internal" in source_types
    assert "external" in source_types
    assert any(s["file_name"] == "procedimiento_incidentes.md" for s in data["sources"])
    assert any(s["file_name"] == "nist_sp_800_218_ssdf.md" for s in data["sources"])


def test_preview_scenario_d_abstention():
    """Verify preview returns abstention state for out-of-domain query."""
    response = preview_client.post(
        "/api/query",
        json={"query": "¿Cuál es la velocidad de la luz en el vacío?"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["abstained"] is True
    assert data["citations"] == []
    assert data["sources"] == []


def test_preview_scenario_e_density():
    """Verify preview returns 4 real sources and 4 citations for density scenario."""
    response = preview_client.post(
        "/api/query",
        json={"query": "Auditoría integral de accesos, incidentes, inyección de prompts y desarrollo seguro"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["abstained"] is False
    assert len(data["sources"]) == 4
    assert len(data["citations"]) == 4

    file_names = [s["file_name"] for s in data["sources"]]
    assert file_names == [
        "politica_accesos.md",
        "procedimiento_incidentes.md",
        "owasp_llm_prompt_injection_prevention.md",
        "nist_sp_800_218_ssdf.md",
    ]


def test_preview_error_500_trigger():
    """Verify PREVIEW_ERROR_500 trigger produces HTTP 500."""
    response = preview_client.post(
        "/api/query",
        json={"query": "PREVIEW_ERROR_500"},
    )
    assert response.status_code == 500
    data = response.json()
    assert "detail" in data


def test_preview_error_503_trigger():
    """Verify PREVIEW_ERROR_503 trigger produces HTTP 503."""
    response = preview_client.post(
        "/api/query",
        json={"query": "PREVIEW_ERROR_503"},
    )
    assert response.status_code == 503
    data = response.json()
    assert "detail" in data
