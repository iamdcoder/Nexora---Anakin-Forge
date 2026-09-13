from enum import Enum

from pydantic import BaseModel, Field

class ValidationStatus(str, Enum):
    ALLOWED = "allowed"
    BLOCKED = "blocked"

class ValidationResult(BaseModel):

    status: ValidationStatus

    reason: str

    violations: list[str] = Field(
        default_factory=list
    )

    validator: str = "unknown"

    severity: str = "error"