from crud.memory_entry import list_memory_entries_by_user_id
from conf.logging import app_logger
from services.companion_service import build_companion_response
from services.growth_service import build_growth_report
from services.memory_service import build_memory_library
from services.profile_service import build_personal_profile
from services.query_service import generate_rag_answer


async def run_companion_pipeline(
        db,
        *,
        user_id: int,
        knowledge_base_id: str,
        question: str,
        top_k: int = 4,
) -> dict:
    app_logger.bind(module="companion_pipeline").info(
        f"companion pipeline start user_id={user_id} knowledge_base_id={knowledge_base_id} "
        f"top_k={top_k} question_length={len(question)}"
    )
    rag_result = await generate_rag_answer(
        question=question,
        db=db,
        knowledge_base_id=knowledge_base_id,
        user_id=user_id,
        top_k=top_k,
    )

    entries = await list_memory_entries_by_user_id(db, user_id=user_id)
    entry_dicts = [item.__dict__ for item in entries]
    memory_library = build_memory_library(entry_dicts)
    app_logger.bind(module="companion_pipeline").info(
        f"companion pipeline memory loaded user_id={user_id} entry_count={len(entries)}"
    )

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

    result = await build_companion_response(
        user_id=user_id,
        knowledge_base_id=knowledge_base_id,
        question=question,
        rag_result=rag_result,
        profile=profile,
        growth_report=growth_report,
    )
    app_logger.bind(module="companion_pipeline").info(
        f"companion pipeline completed user_id={user_id} knowledge_base_id={knowledge_base_id}"
    )
    return result
