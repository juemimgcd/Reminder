from langchain_core.prompts import ChatPromptTemplate


def get_growth_advice_prompt(format_instructions: str) -> ChatPromptTemplate:
    return ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "你是一个成长建议助手。"
                "你会基于长期画像、阶段分析和可选 focus goal，"
                "给出少量、具体、低负担、可执行的成长建议。"
                "你不能脱离输入编造背景，不能给出空泛鸡汤，"
                "也不要一次性给出过多建议。"
                "输出必须严格遵守格式要求。",
            ),
            (
                "human",
                "current_user_id={user_id}\n"
                "knowledge_base_id={knowledge_base_id}\n"
                "advice_input=\n{advice_input_text}\n\n"
                "{format_instructions}",
            ),
        ]
    ).partial(format_instructions=format_instructions)
