from sqlalchemy.ext.asyncio import AsyncSession

from app.mneme.crud.memory_entry import list_memory_entries_by_user_id
from app.mneme.domains.analysis.growth import build_growth_report
from app.mneme.domains.memory.service import build_memory_library
from app.mneme.domains.profile.service import build_personal_profile


async def run_analysis_pipeline(
        db: AsyncSession,
        *,
        user_id: int,
        knowledge_base_id: str,
        recent_days: int = 30,
) -> dict:
    entries = await list_memory_entries_by_user_id(db,user_id=user_id)
    entry_dict = [u.__dict__ for u in entries]
    library = build_memory_library(entry_dict)

    profile = await build_personal_profile(
        user_id=user_id,
        knowledge_base_id=knowledge_base_id,
        memory_library=library
    )
    report = await build_growth_report(
        user_id=user_id,
        knowledge_base_id=knowledge_base_id,
        memory_library=library,
        profile=profile
    )
    return report



















