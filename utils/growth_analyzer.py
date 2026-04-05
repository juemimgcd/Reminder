import json
from datetime import timedelta
from langchain_core.output_parsers import PydanticOutputParser

from schemas.growth_report import GrowthReportResult
from utils.growth_prompt import get_growth_report_prompt
from utils.llm import get_llm
from utils.profile_prompt import get_profile_prompt

def split_timeline_by_recent_days(
        timeline: list[dict],
        recent_days: int = 30,
) -> tuple[list[dict], list[dict]]:

    if not timeline:
        return [], []

    latest_time = max(item["created_at"] for item in timeline)
    cutoff = latest_time - timedelta(days=recent_days)
    earlier = [item for item in timeline if item["created_at"] < cutoff]
    recent = [item for item in timeline if item["created_at"] >= cutoff]


    if not earlier and len(timeline) >= 4:
        middle = len(timeline) // 2
        earlier = timeline[:middle]
        recent = timeline[middle:]

    return earlier, recent







def build_growth_input(
        *,
        knowledge_base_id: str,
        memory_library: dict,
        profile: dict,
        recent_days: int,
) -> str:

    timeline = memory_library.get("timeline")
    earlier_timeline,recent_timeline = split_timeline_by_recent_days(timeline=timeline,recent_days=recent_days)

    payload = {
        "knowledge_base_id": knowledge_base_id,
        "recent_days":recent_days,
        "profile":profile,
        "earlier_timeline":earlier_timeline,
        "recent_timeline":recent_timeline

    }

    str_data = json.dumps(payload,ensure_ascii=False,default=str,indent=2)
    return str_data







async def build_growth_report(
        *,
        user_id: int,
        knowledge_base_id: str,
        memory_library: dict,
        profile: dict,
        recent_days: int = 30,
) -> dict:

    parser = PydanticOutputParser(pydantic_object=GrowthReportResult)
    instructions = parser.get_format_instructions()
    growth_input_text = build_growth_input(
        knowledge_base_id=knowledge_base_id,
        memory_library=memory_library,
        profile=profile,
        recent_days=recent_days,
    )


    prompt = get_growth_report_prompt(instructions)
    llm = get_llm()

    chain = prompt | llm | parser

    result = await chain.ainvoke(
        {
            "user_id":user_id,
            "knowledge_base_id":knowledge_base_id,
            "growth_input_text":growth_input_text

        }
    )

    payload = result.model_dump()
    payload["knowledge_base_id"] = knowledge_base_id
    return payload



























