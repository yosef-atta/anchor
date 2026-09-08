"""Data models and validation schemas for Anchor."""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


class Origin(StrEnum):
    LIVE = "live"
    BOOTSTRAP = "bootstrap"


def _validate_non_empty_str(v: str, field_name: str) -> str:
    if not isinstance(v, str) or not v.strip():
        raise ValueError(f"'{field_name}' must be a non-empty string.")
    return v.strip()


class DecisionInput(BaseModel):
    title: str = Field(..., description="Short title describing the decision.")
    category: str = Field(..., description="Category classification for the decision.")
    decision: str = Field(..., description="The decision that was made.")
    reason: str = Field(..., description="The rationale behind the decision.")
    origin: Origin = Field(default=Origin.LIVE, description="Origin of the record: live or bootstrap.")

    @field_validator("title", mode="before")
    @classmethod
    def validate_title(cls, v: str) -> str:
        return _validate_non_empty_str(v, "title")

    @field_validator("category", mode="before")
    @classmethod
    def validate_category(cls, v: str) -> str:
        return _validate_non_empty_str(v, "category")

    @field_validator("decision", mode="before")
    @classmethod
    def validate_decision(cls, v: str) -> str:
        return _validate_non_empty_str(v, "decision")

    @field_validator("reason", mode="before")
    @classmethod
    def validate_reason(cls, v: str) -> str:
        return _validate_non_empty_str(v, "reason")


class NoteInput(BaseModel):
    title: str = Field(..., description="Short title describing the note.")
    category: str = Field(..., description="Category classification for the note.")
    text: str = Field(..., description="Note text content.")
    origin: Origin = Field(default=Origin.LIVE, description="Origin of the record: live or bootstrap.")

    @field_validator("title", mode="before")
    @classmethod
    def validate_title(cls, v: str) -> str:
        return _validate_non_empty_str(v, "title")

    @field_validator("category", mode="before")
    @classmethod
    def validate_category(cls, v: str) -> str:
        return _validate_non_empty_str(v, "category")

    @field_validator("text", mode="before")
    @classmethod
    def validate_text(cls, v: str) -> str:
        return _validate_non_empty_str(v, "text")


class DecisionRecord(BaseModel):
    id: str
    seq: int
    title: str
    category: str
    decision: str
    reason: str
    origin: Origin
    created_at: str
    updated_at: str
    deleted_at: str | None = None


class NoteRecord(BaseModel):
    id: str
    seq: int
    title: str
    category: str
    text: str
    origin: Origin
    created_at: str
    updated_at: str
    deleted_at: str | None = None


class RecordType(StrEnum):
    DECISION = "decision"
    NOTE = "note"


class SearchResultItem(BaseModel):
    id: str
    record_type: RecordType
    title: str
    category: str
    snippet: str
    origin: Origin
    created_at: str


class SearchResult(BaseModel):
    query: str
    total: int
    page: int
    page_size: int
    items: list[SearchResultItem]


class ContextResult(BaseModel):
    query: str
    decisions: list[DecisionRecord] = Field(default_factory=list)
    notes: list[NoteRecord] = Field(default_factory=list)


class BatchAction(StrEnum):
    EDIT = "edit"
    DELETE = "delete"
    ADD_DECISION = "add_decision"
    ADD_NOTE = "add_note"


class BatchOperation(BaseModel):
    action: BatchAction
    id: str | None = None
    changes: dict[str, Any] | None = None
    data: dict[str, Any] | None = None

    @field_validator("action", mode="before")
    @classmethod
    def normalize_action(cls, v: Any) -> Any:
        if isinstance(v, str):
            v_clean = v.lower().strip().replace("-", "_")
            if v_clean == "add_decision":
                return BatchAction.ADD_DECISION
            if v_clean == "add_note":
                return BatchAction.ADD_NOTE
            if v_clean == "edit":
                return BatchAction.EDIT
            if v_clean == "delete":
                return BatchAction.DELETE
        return v

    @model_validator(mode="after")
    def validate_operation_fields(self) -> "BatchOperation":
        if self.action == BatchAction.EDIT:
            if not self.id:
                raise ValueError("'id' is required for 'edit' operation.")
            if self.changes is None or len(self.changes) == 0:
                raise ValueError("'changes' dictionary with at least one field is required for 'edit' operation.")
        elif self.action == BatchAction.DELETE:
            if not self.id:
                raise ValueError("'id' is required for 'delete' operation.")
        elif self.action in (BatchAction.ADD_DECISION, BatchAction.ADD_NOTE):
            if not self.data:
                raise ValueError(f"'data' dictionary is required for '{self.action.value}' operation.")
        return self


class BatchMutation(BaseModel):
    operations: list[BatchOperation] = Field(..., min_length=1)


class BatchResult(BaseModel):
    applied: int
    records: list[DecisionRecord | NoteRecord] = Field(default_factory=list)
