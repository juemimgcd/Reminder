from app.mneme.agent.tools.base import ToolMetadata

PROFILE_GET_METADATA = ToolMetadata(
    name="profile_get",
    description="Read the current user's profile inferred from their private memory entries.",
    capability_id="tool:profile_get",
    answer_modes=frozenset({"profile_query"}),
    evidence_type="profile_snapshot",
)
