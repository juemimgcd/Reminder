from sqlalchemy.ext.asyncio import AsyncSession

from app.mneme.agent.contracts import AgentRequest, AgentResponse
from app.mneme.agent.orchestrator import generate_rag_answer
from app.mneme.agent.service import MnemeAgent


class RagAnswerEngine:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def generate(self, request: AgentRequest) -> AgentResponse:
        result = await generate_rag_answer(
            question=request.question,
            db=self.db,
            knowledge_base_id=request.knowledge_base_id,
            user_id=request.user_id,
            top_k=request.top_k,
            llm_config=request.llm_config,
        )
        return AgentResponse.model_validate(result)


def build_mneme_agent(db: AsyncSession) -> MnemeAgent:
    return MnemeAgent(answer_engine=RagAnswerEngine(db))
