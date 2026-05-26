from langchain_core.prompts import ChatPromptTemplate


def get_companion_prompt(format_instructions: str) -> ChatPromptTemplate:

    return ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "你是一个陪伴式回答整理助手。"
                "你会基于当前问题的 RAG 回答、引用片段、长期画像和阶段分析，"
                "整理出更像产品结果页的结构化输出。"
                "你不能编造引用，不能输出脱离输入依据的判断，"
                "重点是整合，不是重复做底层检索分析。"
                "输出必须严格遵守格式要求。"
            ),
            (
                "human",
                "current_user_id={user_id}\n"
                "knowledge_base_id={knowledge_base_id}\n"
                "companion_input_text=\n{knowledge_base_id}\n\n"
                "{format_instructions}"
            )



        ]
    ).partial(format_instructions=format_instructions)
