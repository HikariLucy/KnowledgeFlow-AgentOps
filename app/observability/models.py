"""Versioned operational and evaluated-quality contracts. No business payloads."""
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.observability.telemetry import OPERATIONS, LOG_CODES, attributes

ExecutionMode = Literal['offline', 'mock', 'live', 'unknown', 'offline_mock']
Status = Literal['ok', 'error', 'cancelled']
HEX32 = r'^[0-9a-f]{32}$'


class EventFilters(BaseModel):
    model_config = ConfigDict(extra='forbid')
    execution_mode: ExecutionMode
    trace_id: str | None = Field(default=None, pattern=HEX32)
    since: datetime | None = None
    until: datetime | None = None
    component: str | None = None
    operation: str | None = None
    status: Status | None = None

    @field_validator('since', 'until')
    @classmethod
    def utc(cls, value):
        if value is not None:
            if value.tzinfo is None:
                raise ValueError('Timezone required')
            return value.astimezone(timezone.utc)
        return value

    @model_validator(mode='after')
    def bounds(self):
        if self.since and self.until and self.since >= self.until:
            raise ValueError('Invalid period')
        if self.component is not None and self.component not in OPERATIONS:
            raise ValueError('Invalid component')
        operations = OPERATIONS.get(self.component, set().union(*OPERATIONS.values()))
        if self.operation is not None and self.operation not in operations:
            raise ValueError('Invalid operation')
        return self


class StoredEvent(BaseModel):
    # Unknown keys are discarded before serialization, even for local producers.
    model_config = ConfigDict(extra='ignore', allow_inf_nan=False)
    schema_version: Literal[1]
    event: Literal['span', 'log']
    event_id: str = Field(pattern=HEX32)
    trace_id: str | None = Field(default=None, pattern=HEX32)
    session_id: str | None = Field(default=None, pattern=r'^(?:[0-9a-f]{32}|[0-9a-f]{64})$')
    span_id: str | None = Field(default=None, pattern=r'^[0-9a-f]{16}$')
    parent_span_id: str | None = Field(default=None, pattern=r'^[0-9a-f]{16}$')
    execution_mode: ExecutionMode
    level: Literal['INFO', 'ERROR']
    timestamp: datetime | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
    component: str | None = None
    operation: str | None = None
    code: str | None = None
    status: Status | None = None
    outcome: Literal['completed', 'failed', 'abstained', 'needs_clarification'] | None = None
    error_code: Literal['timeout', 'validation_error', 'not_found', 'io_error', 'cancelled',
                        'provider_error', 'internal_error', 'http_client_error', 'http_server_error'] | None = None
    duration_ms: float | None = Field(default=None, ge=0)
    input_tokens: int | None = Field(default=None, ge=0, le=10**15, strict=True)
    output_tokens: int | None = Field(default=None, ge=0, le=10**15, strict=True)
    total_tokens: int | None = Field(default=None, ge=0, le=10**15, strict=True)
    dropped_events: int = Field(default=0, ge=0, strict=True)
    attributes: dict = Field(default_factory=dict)

    @field_validator('timestamp', 'started_at', 'ended_at')
    @classmethod
    def utc(cls, value):
        return EventFilters.utc(value)

    @field_validator('attributes')
    @classmethod
    def clean_attributes(cls, value):
        return attributes(value)

    @model_validator(mode='after')
    def valid_shape(self):
        if self.event == 'span':
            if (self.operation not in OPERATIONS.get(self.component, set()) or
                    any(v is None for v in [self.started_at, self.ended_at, self.duration_ms,
                                            self.trace_id, self.span_id, self.status])):
                raise ValueError('Invalid span')
            if self.component != 'provider' and any(v is not None for v in
                    [self.input_tokens, self.output_tokens, self.total_tokens]):
                raise ValueError('Usage only belongs to provider spans')
            if self.code is not None:
                raise ValueError('Invalid span code')
        elif self.timestamp is None or self.code not in LOG_CODES:
            raise ValueError('Invalid log')
        elif any(v is not None for v in [self.component, self.operation, self.status,
                 self.duration_ms, self.input_tokens, self.output_tokens, self.total_tokens]):
            raise ValueError('Invalid log fields')
        return self


class QualityMeasurement(BaseModel):
    """Future evaluated benchmark input, never constructed from operational events."""
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)
    benchmark_id: str = Field(pattern=HEX32)
    dataset_sha256: str = Field(pattern=r'^[0-9a-f]{64}$')
    evaluator_version: str = Field(pattern=r'^[a-zA-Z0-9_.-]{1,64}$')
    execution_mode: Literal['offline', 'mock', 'live']
    synthetic: bool
    evaluated_at: datetime
    metric: Literal['precision', 'consistency']
    numerator: int = Field(ge=0, strict=True)
    denominator: int = Field(gt=0, strict=True)

    @field_validator('evaluated_at')
    @classmethod
    def utc(cls, value):
        return EventFilters.utc(value)

    @model_validator(mode='after')
    def ratio(self):
        if self.numerator > self.denominator:
            raise ValueError('Invalid benchmark ratio')
        return self

    @property
    def value(self):
        return self.numerator / self.denominator
