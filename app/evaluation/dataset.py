"""Dataset loader, saver and validation utilities for evaluation cases."""

import json
from pathlib import Path
from typing import Union

from app.evaluation.schemas import EvaluationDataset


def load_dataset(file_path: Union[str, Path]) -> EvaluationDataset:
    """Load and validate an EvaluationDataset from a JSON file.

    Args:
        file_path: Path to the JSON dataset file.

    Returns:
        Validated EvaluationDataset instance.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If JSON is invalid or fails Pydantic schema validation.
    """
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"Evaluation dataset file not found: '{path}'")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return EvaluationDataset.model_validate(data)


def save_dataset(dataset: EvaluationDataset, file_path: Union[str, Path]) -> None:
    """Save an EvaluationDataset to a JSON file with pretty formatting.

    Args:
        dataset: EvaluationDataset instance to persist.
        file_path: Destination path for the JSON file.
    """
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(dataset.model_dump(), f, indent=2, ensure_ascii=False)


def has_unreviewed_cases(dataset: EvaluationDataset) -> bool:
    """Check if the dataset contains any unreviewed cases (human_reviewed=False)."""
    return any(not c.human_reviewed for c in dataset.cases)


def validate_dataset_for_official_run(dataset: EvaluationDataset) -> None:
    """Ensure all cases in the dataset have been reviewed and approved by humans.

    Raises:
        ValueError: If any case has human_reviewed=False.
    """
    unreviewed = [c.id for c in dataset.cases if not c.human_reviewed]
    if unreviewed:
        raise ValueError(
            f"Dataset contains {len(unreviewed)} unreviewed cases: {unreviewed[:5]}... "
            "Cannot proceed with official run (--require-reviewed is active)."
        )
