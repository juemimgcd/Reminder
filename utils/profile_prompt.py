from langchain_core.prompts import ChatPromptTemplate


def get_profile_prompt(format_instructions:str):
    return ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "你是一个个人画像分析助手。"
                "你会根据知识库级 memory library，总结长期主题、能力轮廓、表达风格和稳定关注点。"
                "你只能基于输入内容做判断，不能编造经历，不能做过度心理分析。"
                "输出必须严格遵守格式要求。"
            ),
            (
                "human",
                "current_user_id={user_id}\n"
                "knowledge_base_id={knowledge_base_id}\n"
                "memory_library=\n{memory_library_text}\n\n"
                "{format_instructions}"
            )


        ]
    ).partial(format_instructions=format_instructions)




