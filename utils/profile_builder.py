import json
from langchain_core.output_parsers import PydanticOutputParser

from schemas.profile import PersonalProfileResult
from utils.llm import get_llm
from utils.profile_prompt import get_profile_prompt


def build_profile_input(memory_library: dict) -> str:
    js_memory = json.dumps(memory_library,ensure_ascii=False,default=str,indent=2)

    return js_memory



async def build_personal_profile(
        *,
        user_id: int,
        knowledge_base_id: str,
        memory_library: dict,
) -> dict:

    parser = PydanticOutputParser(pydantic_object=PersonalProfileResult)
    instructions = parser.get_format_instructions()
    js_data = build_profile_input(memory_library)

    prompt = get_profile_prompt(format_instructions=instructions)
    llm = get_llm()

    chain = prompt | llm | parser

    result = await chain.ainvoke(
        {
            "user_id":user_id,
            "knowledge_base_id":knowledge_base_id,
            "memory_library_text":js_data
        }

    )

    payload = result.model_dump()
    payload["knowledge_base_id"] = knowledge_base_id
    payload["entry_count"] = len(memory_library.get("timeline", []))
    return payload
























