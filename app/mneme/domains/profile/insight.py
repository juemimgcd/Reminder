from sqlalchemy.ext.asyncio import AsyncSession

from app.mneme.crud.memory_entry import list_memory_entries_by_knowledge_base_id
from app.mneme.domains.advice.service import build_growth_advice
from app.mneme.domains.analysis.growth import build_growth_report
from app.mneme.domains.memory.service import build_memory_library, serialize_memory_entries
from app.mneme.domains.profile.service import build_personal_profile
from app.mneme.domains.profile.tools import build_evidence_profile_from_entries


def empty_profile_result(*, knowledge_base_id: str) -> dict:
    return {
        "knowledge_base_id": knowledge_base_id,
        "entry_count": 0,
        "profile_summary": "",
        "main_themes": [],
        "ability_tags": [],
        "expression_style": "",
        "growth_focus": [],
    }


def empty_growth_report_result(
        *,
        knowledge_base_id: str,
        recent_days: int,
) -> dict:
    return {
        "knowledge_base_id": knowledge_base_id,
        "analysis_window": f"recent {recent_days} days",
        "stage_summary": "",
        "recent_focus": [],
        "theme_changes": [],
        "highlights": [],
        "blockers": [],
        "next_actions": [],
    }


def empty_growth_advice_result(
        *,
        knowledge_base_id: str,
        focus_goal: str | None,
) -> dict:
    return {
        "knowledge_base_id": knowledge_base_id,
        "focus_goal": focus_goal,
        "advice_summary": "",
        "current_priorities": [],
        "action_suggestions": [],
        "avoid_list": [],
        "one_week_plan": [],
        "reflection_questions": [],
    }


async def load_memory_library_for_knowledge_base(
        db: AsyncSession,
        *,
        knowledge_base_id: str,
) -> tuple[list, dict]:
    rows = await list_memory_entries_by_knowledge_base_id(
        db,
        knowledge_base_id=knowledge_base_id,
    )
    memory_library = build_memory_library(serialize_memory_entries(rows))
    return rows, memory_library


async def build_profile_for_knowledge_base(
        db: AsyncSession,
        *,
        user_id: int,
        knowledge_base_id: str,
) -> tuple[list, dict]:
    rows, memory_library = await load_memory_library_for_knowledge_base(
        db,
        knowledge_base_id=knowledge_base_id,
    )
    if not rows:
        return rows, empty_profile_result(knowledge_base_id=knowledge_base_id)

    result = await build_personal_profile(
        user_id=user_id,
        knowledge_base_id=knowledge_base_id,
        memory_library=memory_library,
    )
    return rows, result


async def build_evidence_profile_for_knowledge_base(
        db: AsyncSession,
        *,
        knowledge_base_id: str,
        recent_days: int = 30,
) -> tuple[list, dict]:
    rows = await list_memory_entries_by_knowledge_base_id(
        db,
        knowledge_base_id=knowledge_base_id,
    )
    result = build_evidence_profile_from_entries(
        knowledge_base_id=knowledge_base_id,
        entries=rows,
        recent_days=recent_days,
    )
    return rows, result.model_dump()


async def build_growth_for_knowledge_base(
        db: AsyncSession,
        *,
        user_id: int,
        knowledge_base_id: str,
        recent_days: int,
) -> tuple[list, dict, dict]:
    rows, memory_library = await load_memory_library_for_knowledge_base(
        db,
        knowledge_base_id=knowledge_base_id,
    )
    if not rows:
        return (
            rows,
            empty_profile_result(knowledge_base_id=knowledge_base_id),
            empty_growth_report_result(
                knowledge_base_id=knowledge_base_id,
                recent_days=recent_days,
            ),
        )

    profile = await build_personal_profile(
        user_id=user_id,
        knowledge_base_id=knowledge_base_id,
        memory_library=memory_library,
    )
    growth = await build_growth_report(
        user_id=user_id,
        knowledge_base_id=knowledge_base_id,
        memory_library=memory_library,
        profile=profile,
        recent_days=recent_days,
    )
    return rows, profile, growth


async def build_advice_for_knowledge_base(
        db: AsyncSession,
        *,
        user_id: int,
        knowledge_base_id: str,
        focus_goal: str | None,
        recent_days: int = 30,
) -> tuple[list, dict, dict, dict]:
    rows, profile, growth = await build_growth_for_knowledge_base(
        db,
        user_id=user_id,
        knowledge_base_id=knowledge_base_id,
        recent_days=recent_days,
    )
    if not rows:
        return (
            rows,
            profile,
            growth,
            empty_growth_advice_result(
                knowledge_base_id=knowledge_base_id,
                focus_goal=focus_goal,
            ),
        )

    advice = await build_growth_advice(
        user_id=user_id,
        knowledge_base_id=knowledge_base_id,
        profile=profile,
        growth_report=growth,
        focus_goal=focus_goal,
    )
    return rows, profile, growth, advice
