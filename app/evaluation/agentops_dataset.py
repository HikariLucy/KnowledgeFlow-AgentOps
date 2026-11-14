"""Pydantic schemas and loader for the KnowledgeFlow AgentOps experimental benchmark."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal, Optional, Union

from pydantic import BaseModel, Field, model_validator

AgentOpsScenario = Literal[
    "rag_internal",
    "rag_external",
    "rag_mixed",
    "rag_no_evidence",
    "agent_tools",
    "agent_incidents",
    "agent_planning_memory",
    "security_robustness",
    "consistency",
]

DocumentSourceKind = Literal["corpus_verified", "synthetic_fixture"]
ExecutionModeLiteral = Literal["offline", "mock", "live"]


class AgentOpsExpectedResult(BaseModel):
    """Verifiable expectations for one benchmark case."""

    expected_status: Optional[Literal["completed", "failed", "abstained", "needs_clarification"]] = None
    expected_intent: Optional[str] = None
    expected_behavior: Optional[Literal["grounded_answer", "abstain", "clarify", "block_or_abstain", "tool_error_handled"]] = None
    expected_scope: Optional[Literal["internal", "external", "all"]] = None
    expected_files: list[str] = Field(default_factory=list)
    expected_keywords: list[str] = Field(default_factory=list)
    requires_clarification: Optional[bool] = None
    must_not_mutate_incidents: bool = False


class AgentOpsCase(BaseModel):
    """Single verifiable test case for the AgentOps quality benchmark."""

    id: str = Field(..., min_length=1)
    scenario: AgentOpsScenario
    input: dict[str, Any]
    document_source: DocumentSourceKind
    source_ref: Optional[str] = None
    expected_result: AgentOpsExpectedResult
    expected_tools: list[str] = Field(default_factory=list)
    acceptance_criteria: str = Field(..., min_length=5)
    execution_modes: list[ExecutionModeLiteral] = Field(default_factory=lambda: ["offline", "mock"])
    human_reviewed: bool = False
    consistency_group: Optional[str] = None
    notes: Optional[str] = None

    @model_validator(mode="after")
    def validate_case(self) -> "AgentOpsCase":
        if not str(self.input.get("message", "")).strip():
            raise ValueError(f"Case {self.id}: input.message is required and cannot be empty")
        if self.document_source == "corpus_verified" and not self.source_ref:
            raise ValueError(f"Case {self.id}: corpus_verified cases must declare source_ref")
        return self


class AgentOpsDataset(BaseModel):
    """Versioned collection of AgentOps benchmark cases."""

    version: str = Field(default="1.0")
    description: str
    base_rag_dataset: str = Field(default="evaluation/dataset_verified.json")
    cases: list[AgentOpsCase] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_unique_ids(self) -> "AgentOpsDataset":
        seen: set[str] = set()
        for case in self.cases:
            if case.id in seen:
                raise ValueError(f"Duplicate case id in AgentOpsDataset: {case.id}")
            seen.add(case.id)
        return self


def load_agentops_dataset(file_path: Union[str, Path]) -> AgentOpsDataset:
    """Load and validate an AgentOpsDataset JSON file."""
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"AgentOps benchmark dataset not found: '{path}'")
    with open(path, "r", encoding="utf-8") as handle:
        raw = json.load(handle)
    return AgentOpsDataset.model_validate(raw)
