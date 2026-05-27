from langchain_openai import ChatOpenAI

from app.mneme.conf.config import settings


# ```python
# from langchain_openai import ChatOpenAI
#
# model = ChatOpenAI(
#     model="...",
#     temperature=0,
#     max_tokens=None,
#     timeout=None,
#     max_retries=2,
#     # api_key="...",
#     # base_url="...",
#     # organization="...",
#     # other params...
# )
# ```



def get_llm() -> ChatOpenAI:

    return ChatOpenAI(
        model=settings.LLM_MODEL_NAME,
        api_key=settings.DASHSCOPE_API_KEY,
        base_url=settings.LLM_BASE_URL,
        temperature=settings.LLM_TEMPERATURE

    )











