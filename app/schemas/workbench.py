
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=False)


class DiagnosisRequest(Input):
    code: str = Field(min_length=1, max_length=16_000)
    language: Literal["python", "c", "java", "javascript", "go"] = "python"
    goal: Literal["sum-all", "first-or-empty"] | None = None
    request_id: UUID


class AnswerRequest(Input):
    answer: str = Field(min_length=1, max_length=80)
    attempt_id: UUID
