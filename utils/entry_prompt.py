from langchain_core.prompts import ChatPromptTemplate


def get_entry_extraction_prompt(format_instructions: str) -> ChatPromptTemplate:
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "你是一个个人记忆词条抽取助手。"
                "请从输入文本中抽取最有价值的个人词条。"
                "词条类型只允许：theme、event、ability、emotion、stage。"
                "每条词条必须简洁明确，并保留 evidence_text。"
                "如果文本里没有值得抽取的内容，返回空列表。"
                "\n\n输出必须严格遵守下面的格式要求：\n{format_instructions}",
            ),
            (
                "human",
                "document_id={document_id}\n"
                "chunk_id={chunk_id}\n"
                "page_no={page_no}\n\n"
                "原始文本如下：\n{chunk_text}",
            ),
        ]
    )
    return prompt.partial(format_instructions=format_instructions)










