from dataclasses import dataclass
from enum import Enum


class ToolRiskLevel(str, Enum):
    READ = "read"
    LOW_WRITE = "low_write"
    HIGH_WRITE = "high_write"
    DESTRUCTIVE = "destructive"


class ToolApprovalPolicy(str, Enum):
    NEVER = "never"
    PROPOSE = "propose"
    ALWAYS = "always"


@dataclass(frozen=True)
class WriteActionDefinition:
    name: str
    risk_level: ToolRiskLevel
    description: str
    apply_enabled: bool = False


WRITE_ACTION_CATALOG = {
    item.name: item
    for item in (
        WriteActionDefinition(
            name="memory_review.propose",
            risk_level=ToolRiskLevel.LOW_WRITE,
            description="Propose a memory item for user review without mutating canonical memory.",
        ),
        WriteActionDefinition(
            name="document_reindex.propose",
            risk_level=ToolRiskLevel.HIGH_WRITE,
            description="Propose reindexing a document without starting the task.",
        ),
        WriteActionDefinition(
            name="profile_revision.propose",
            risk_level=ToolRiskLevel.HIGH_WRITE,
            description="Propose a profile revision without applying it.",
        ),
    )
}
