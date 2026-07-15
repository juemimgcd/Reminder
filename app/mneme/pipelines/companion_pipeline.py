from app.mneme.conf.logging import app_logger
from app.mneme.domains.chat.service import (
    _resolve_model_config,
    answer_via_memory_agent,
    build_chat_message_id,
    memory_agent_answer_to_chat_result,
)


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
    model_config = await _resolve_model_config(db, user_id=user_id, config_id=None)
    await db.rollback()
    agent_response = await answer_via_memory_agent(
        owner_id=user_id,
        question=question,
        answer_mode="analysis_query",
        top_k=top_k,
        knowledge_base_id=knowledge_base_id,
        session_id=None,
        message_id=build_chat_message_id(),
        model_config=model_config,
    )
    result = memory_agent_answer_to_chat_result(agent_response)
    return {
        "knowledge_base_id": knowledge_base_id,
        "question": question,
        "direct_answer": result["answer"],
        "citations": result["citations"],
        "profile_snapshot": "",
        "growth_snapshot": "",
        "next_step_hint": "",
        "follow_up_questions": [],
        "companion_message": result["answer"],
    }
