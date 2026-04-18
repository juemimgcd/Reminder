from sqlalchemy.ext.asyncio import AsyncSession

from crud.memory_entry import list_memory_entries_by_user_id
from services.growth_service import build_growth_report
from services.memory_service import build_memory_library
from services.profile_service import build_personal_profile


async def run_analysis_pipeline(
        db: AsyncSession,
        *,
        user_id: int,
        knowledge_base_id: str,
        recent_days: int = 30,
) -> dict:
    # 你要做的事：
    # 1. 读取 memory entries
    # 2. 组织 memory_library
    # 3. 生成 profile
    # 4. 生成 growth_report
    # 5. 返回最终 report
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



















