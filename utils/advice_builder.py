import json

from langchain_core.output_parsers import PydanticOutputParser

from schemas.advice import GrowthAdviceResult
from utils.advice_prompt import get_growth_advice_prompt
from clients.llm_client import get_llm


def build_advice_input(
        *,
        knowledge_base_id: str,
        profile: dict,
        growth_report: dict,
        focus_goal: str | None,
) -> str:

    payload = {
        "knowledge_base_id":knowledge_base_id,
        "focus_goal":focus_goal,
        "profile":profile,
        "growth_report":growth_report
    }
    js_data = json.dumps(
        payload,
        ensure_ascii=False,
        default=str,
        indent=2
    )
    return js_data






async def build_growth_advice(
        *,
        user_id: int,
        knowledge_base_id: str,
        profile: dict,
        growth_report: dict,
        focus_goal: str | None = None,
) -> dict:

    parser = PydanticOutputParser(pydantic_object=GrowthAdviceResult)
    instruction = parser.get_format_instructions()

    prompt = get_growth_advice_prompt(format_instructions=instruction)
    llm = get_llm()
    chain = prompt | llm | parser

    result = await chain.ainvoke(
        {
            "user_id":user_id,
            "knowledge_base_id":knowledge_base_id,
            "advice_input_text":build_advice_input(
                knowledge_base_id=knowledge_base_id,
                profile=profile,
                growth_report=growth_report,
                focus_goal=focus_goal
            )
        }
    )

    payload = result.model_dump()
    payload["knowledge_base_id"] = knowledge_base_id
    payload["focus_goal"] = focus_goal
    return payload































