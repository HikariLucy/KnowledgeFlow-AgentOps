"""Offline unit tests for evaluation dataset schema, loader and validation gates."""

from pathlib import Path
import pytest

from app.evaluation.dataset import (
    has_unreviewed_cases,
    load_dataset,
    save_dataset,
    validate_dataset_for_official_run,
)
from app.evaluation.schemas import EvaluationCase, EvaluationDataset


def test_valid_evaluation_case():
    """Verify valid EvaluationCase instantiation."""
    case = EvaluationCase(
        id="TEST-001",
        query="¿Cómo reportar un incidente?",
        category="internal",
        expected_scope="internal",
        answerable=True,
        expected_source_types=["internal"],
        expected_files=["procedimiento_incidentes.md"],
        expected_behavior="grounded_answer",
        notes="Prueba unitaria válida",
        human_reviewed=False,
    )
    assert case.id == "TEST-001"
    assert case.answerable is True
    assert case.expected_scope == "internal"


def test_out_of_domain_case_consistency():
    """Verify out-of-domain case requires expected_scope=None and expected_files=[]."""
    case = EvaluationCase(
        id="TEST-OOD",
        query="¿Cuál es la distancia a la Luna?",
        category="out_of_domain",
        expected_scope=None,
        answerable=False,
        expected_source_types=[],
        expected_files=[],
        expected_behavior="abstain",
        notes="Caso fuera de dominio",
        human_reviewed=False,
    )
    assert case.expected_scope is None
    assert case.answerable is False
    assert case.expected_behavior == "abstain"


def test_out_of_domain_with_expected_scope_raises():
    """Verify out_of_domain case with explicit expected_scope raises ValueError."""
    with pytest.raises(ValueError, match="out_of_domain cases must have expected_scope=None"):
        EvaluationCase(
            id="TEST-ERR",
            query="¿Pregunta OOD?",
            category="out_of_domain",
            expected_scope="internal",  # Invalid
            answerable=False,
            expected_source_types=[],
            expected_files=[],
            expected_behavior="abstain",
        )


def test_answerable_without_files_raises():
    """Verify answerable=True without expected_files raises ValueError."""
    with pytest.raises(ValueError, match="must specify at least one expected_file"):
        EvaluationCase(
            id="TEST-ERR2",
            query="¿Pregunta válida sin fuentes?",
            category="internal",
            expected_scope="internal",
            answerable=True,
            expected_source_types=["internal"],
            expected_files=[],  # Invalid: cannot be empty for answerable=True
            expected_behavior="grounded_answer",
        )


def test_dataset_duplicate_ids_rejected():
    """Verify EvaluationDataset rejects duplicate case IDs."""
    case1 = EvaluationCase(
        id="DUP-01",
        query="Consulta 1",
        category="internal",
        expected_scope="internal",
        answerable=True,
        expected_source_types=["internal"],
        expected_files=["doc1.md"],
        expected_behavior="grounded_answer",
    )
    case2 = EvaluationCase(
        id="DUP-01",  # Duplicate ID
        query="Consulta 2",
        category="internal",
        expected_scope="internal",
        answerable=True,
        expected_source_types=["internal"],
        expected_files=["doc2.md"],
        expected_behavior="grounded_answer",
    )
    with pytest.raises(ValueError, match="duplicate case IDs"):
        EvaluationDataset(
            version="1.0",
            description="Dataset con IDs duplicados",
            cases=[case1, case2],
        )


def test_load_and_save_dataset_roundtrip(tmp_path):
    """Verify dataset serialization and deserialization preserves all fields."""
    case = EvaluationCase(
        id="ROUNDTRIP-01",
        query="Consulta de prueba",
        category="external",
        expected_scope="external",
        answerable=True,
        expected_source_types=["external"],
        expected_files=["guia.md"],
        expected_behavior="grounded_answer",
        human_reviewed=False,
    )
    dataset = EvaluationDataset(
        version="1.0",
        description="Dataset temporal",
        cases=[case],
    )

    save_file = tmp_path / "dataset_test.json"
    save_dataset(dataset, save_file)

    loaded = load_dataset(save_file)
    assert len(loaded.cases) == 1
    assert loaded.cases[0].id == "ROUNDTRIP-01"
    assert loaded.cases[0].human_reviewed is False


def test_human_review_gate_detection():
    """Verify has_unreviewed_cases and validate_dataset_for_official_run detect unreviewed records."""
    unreviewed_case = EvaluationCase(
        id="CASE-UNREV",
        query="Pregunta",
        category="internal",
        expected_scope="internal",
        answerable=True,
        expected_source_types=["internal"],
        expected_files=["doc.md"],
        expected_behavior="grounded_answer",
        human_reviewed=False,
    )
    dataset = EvaluationDataset(
        description="Test unreviewed",
        cases=[unreviewed_case],
    )

    assert has_unreviewed_cases(dataset) is True
    with pytest.raises(ValueError, match="unreviewed cases"):
        validate_dataset_for_official_run(dataset)


def test_category_scope_mismatch_raises():
    """Verify mismatch between category and expected_scope raises ValueError."""
    with pytest.raises(ValueError, match="category='internal' must have expected_scope='internal'"):
        EvaluationCase(
            id="ERR-CAT-1",
            query="Consulta interna",
            category="internal",
            expected_scope="external",  # Mismatch
            answerable=True,
            expected_source_types=["internal"],
            expected_files=["doc.md"],
            expected_behavior="grounded_answer",
        )

    with pytest.raises(ValueError, match="category='external' must have expected_scope='external'"):
        EvaluationCase(
            id="ERR-CAT-2",
            query="Consulta externa",
            category="external",
            expected_scope="all",  # Mismatch
            answerable=True,
            expected_source_types=["external"],
            expected_files=["doc.md"],
            expected_behavior="grounded_answer",
        )


def test_draft_dataset_integrity():
    """Verify evaluation/dataset_draft.json on disk is valid and conforms to 20 controlled cases."""
    draft_path = Path("evaluation/dataset_draft.json")
    assert draft_path.is_file()

    dataset = load_dataset(draft_path)
    assert len(dataset.cases) == 20

    # All 20 cases in draft are now human reviewed
    reviewed_cases = [c.id for c in dataset.cases if c.human_reviewed]
    pending_cases = [c.id for c in dataset.cases if not c.human_reviewed]
    assert len(reviewed_cases) == 20
    assert len(pending_cases) == 0
    assert has_unreviewed_cases(dataset) is False

    # Check categories distribution
    categories = [c.category for c in dataset.cases]
    assert categories.count("internal") == 5
    assert categories.count("external") == 5
    assert categories.count("all") == 5
    assert categories.count("out_of_domain") == 5


def test_verified_dataset_integrity():
    """Verify evaluation/dataset_verified.json is valid, passes official run validation, and has 20 reviewed cases."""
    verified_path = Path("evaluation/dataset_verified.json")
    assert verified_path.is_file()

    dataset = load_dataset(verified_path)
    assert len(dataset.cases) == 20
    assert has_unreviewed_cases(dataset) is False

    # Passes official gate without raising
    validate_dataset_for_official_run(dataset)

    # Check categories distribution
    categories = [c.category for c in dataset.cases]
    assert categories.count("internal") == 5
    assert categories.count("external") == 5
    assert categories.count("all") == 5
    assert categories.count("out_of_domain") == 5
