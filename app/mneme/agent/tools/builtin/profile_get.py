from app.mneme.agent.tools.base import ToolMetadata

PROFILE_GET_METADATA = ToolMetadata(
    name="profile_get",
    description="Read the current user's profile inferred from their private memory entries.",
    answer_mode="profile_query",
)
