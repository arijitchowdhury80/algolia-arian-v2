"""PRISM Module Interface -- every module implements this."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import ClassVar

from pydantic import BaseModel, ConfigDict

from prism_platform.core.types import ModuleResult, ValidationResult


class ExecutionContext(BaseModel):
    """Passed to every module. Provides shared context."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    audit_id: str
    account_id: str
    domain: str
    company_name: str
    ticker: str | None = None
    is_private: bool = False


class ModuleInterface(ABC):
    """Every module implements this. No exceptions."""

    name: ClassVar[str]
    version: ClassVar[str]
    description: ClassVar[str]
    layer: ClassVar[str]  # intelligence, synthesis, quality, delivery

    input_schema: ClassVar[type[BaseModel]]
    output_schema: ClassVar[type[BaseModel]]
    dependencies: ClassVar[list[str]]
    requires_llm: ClassVar[bool]

    timeout_seconds: ClassVar[int]
    max_retries: ClassVar[int]

    @abstractmethod
    async def execute(self, context: ExecutionContext) -> ModuleResult:
        """Run the module. Returns structured result with provenance."""
        ...

    @abstractmethod
    async def validate(self, result: ModuleResult) -> ValidationResult:
        """Verify the output meets quality standards."""
        ...

    async def health_check(self) -> bool:
        """Check if external dependencies are available."""
        return True
