from app.mneme.crud.memory_entry import list_memory_entries_by_user_id
from app.mneme.domains.advice.service import build_growth_advice
from app.mneme.services.growth_service import build_growth_report
from app.mneme.domains.memory.service import build_memory_library
from app.mneme.domains.profile.service import build_personal_profile


async def run_advice_pipeline(
        db,
        *,
        user_id: int,
        knowledge_base_id: str,
        focus_goal: str | None = None,
) -> dict:
    entries = await list_memory_entries_by_user_id(db, user_id=user_id)
    entry_dicts = [item.__dict__ for item in entries]

    memory_library = build_memory_library(entry_dicts)

    profile = await build_personal_profile(
        user_id=user_id,
        knowledge_base_id=knowledge_base_id,
        memory_library=memory_library,
    )

    growth_report = await build_growth_report(
        user_id=user_id,
        knowledge_base_id=knowledge_base_id,
        memory_library=memory_library,
        profile=profile,
    )

    advice = await build_growth_advice(
        user_id=user_id,
        knowledge_base_id=knowledge_base_id,
        profile=profile,
        growth_report=growth_report,
        focus_goal=focus_goal,
    )

    return advice
