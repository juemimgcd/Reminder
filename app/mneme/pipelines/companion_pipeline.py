from app.mneme.agent.adapters import build_mneme_agent
from app.mneme.agent.contracts import AgentRequest
from app.mneme.conf.logging import app_logger
from app.mneme.crud.memory_entry import list_memory_entries_by_user_id
from app.mneme.domains.analysis.growth import build_growth_report
from app.mneme.domains.companion.service import build_companion_response
from app.mneme.domains.memory.service import build_memory_library
from app.mneme.domains.profile.service import build_personal_profile


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
    agent_response = await build_mneme_agent(db).run(
        AgentRequest(
            question=question,
            knowledge_base_id=knowledge_base_id,
            user_id=user_id,
            top_k=top_k,
        )
    )
    rag_result = agent_response.to_legacy_result()

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
