import json

from langchain_core.output_parsers import PydanticOutputParser

from app.mneme.clients.llm_client import get_llm
from app.mneme.conf.logging import app_logger
from app.mneme.schemas.companion import CompanionAnswerResult
from app.mneme.utils.companion_prompt import get_companion_prompt


def build_companion_input(
        *,
        question: str,
        rag_result: dict,
        profile: dict,
        growth_report: dict,
) -> str:

    payload = {
        "question":question,
        "rag_result":rag_result,
        "profile":profile,
        "growth_report":growth_report
    }
    js_data = json.dumps(payload,ensure_ascii=False,default=str,indent=2)
    return js_data





async def build_companion_response(
        *,
        user_id: int,
        knowledge_base_id: str,
        question: str,
        rag_result: dict,
        profile: dict,
        growth_report: dict,
) -> dict:
    app_logger.bind(module="companion_service").info(
        f"build companion response start user_id={user_id} knowledge_base_id={knowledge_base_id} "
        f"question_length={len(question)}"
    )

    parser = PydanticOutputParser(pydantic_object=CompanionAnswerResult)
    instruction = parser.get_format_instructions()

    prompt = get_companion_prompt(format_instructions=instruction)
    llm = get_llm()

    chain = prompt | llm | parser
    result = await chain.ainvoke(
        {
            "user_id":user_id,
            "knowledge_base_id":knowledge_base_id,
            "companion_input_text":build_companion_input(
                question=question,
                rag_result=rag_result,
                profile=profile,
                growth_report=growth_report
            )

        }
    )

    payload = result.model_dump()
    payload["knowledge_base_id"] = knowledge_base_id
    payload["question"] = question
    app_logger.bind(module="companion_service").info(
        f"build companion response completed user_id={user_id} knowledge_base_id={knowledge_base_id}"
    )
    return payload






















