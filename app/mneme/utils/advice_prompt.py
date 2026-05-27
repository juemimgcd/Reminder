from langchain_core.prompts import ChatPromptTemplate


def get_growth_advice_prompt(format_instructions: str) -> ChatPromptTemplate:
    # 你要做的事：
    # 1. 用 ChatPromptTemplate.from_messages(...)
    # 2. 准备一个 system 消息
    # 3. 明确告诉模型：输入包含长期画像、阶段报告、可选 focus_goal
    # 4. 明确告诉模型：建议要少、具体、低负担、可执行
    # 5. 明确告诉模型：不能脱离输入编造背景，不能输出空泛鸡汤
    # 6. 在 human 消息里至少包含 user_id、knowledge_base_id、advice_input_text
    # 7. 把 format_instructions 拼进去，约束输出结构
    return ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "你是一个成长建议助手。"
                "你会基于长期画像、阶段分析和可选 focus goal，"
                "给出少量、具体、低负担、可执行的成长建议。"
                "你不能脱离输入编造背景，不能给出空泛鸡汤，"
                "也不要一次性给过多建议。"
                "输出必须严格遵守格式要求。"
            )
            ,
            (
                "human",
                "current_user_id={user_id}\n"
                "knowledge_base_id={knowledge_base_id}\n"
                "advice_input=\n{advice_input_text}\n\n"
                "{format_instructions}"
            )


        ]
    ).partial(format_instructions=format_instructions)







