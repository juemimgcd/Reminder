import unittest


class ChatSessionPersistenceContractTest(unittest.TestCase):
    def test_chat_session_router_is_registered(self):
        from app.mneme.bootstrap.router_registry import ROUTER_MODULE_NAMES

        self.assertIn("app.mneme.domains.chat.router", ROUTER_MODULE_NAMES)

    def test_chat_message_model_is_registered(self):
        import app.mneme.models as models

        self.assertTrue(hasattr(models, "ChatSession"))
        self.assertTrue(hasattr(models, "ChatMessage"))

    def test_chat_mode_and_agent_run_are_persisted_fields(self):
        from app.mneme.memoria.models.automation import DurableAgentRun
        from app.mneme.models.chat_message import ChatMessage
        from app.mneme.models.chat_session import ChatSession

        self.assertIn("answer_mode", ChatSession.__table__.columns)
        self.assertIn("multi_agent_enabled", ChatSession.__table__.columns)
        self.assertIn("agent_run_id", ChatMessage.__table__.columns)
        self.assertIn("execution_mode", DurableAgentRun.__table__.columns)

    def test_multi_agent_is_opt_in_by_default(self):
        from app.mneme.memoria.server.contracts.answers import AnswerRequest
        from app.mneme.schemas.chat_session import ChatSessionCreateRequest

        session = ChatSessionCreateRequest(
            knowledge_base_id="kb-1",
            answer_mode="analysis_query",
        )
        request = AnswerRequest(
            request_id="request-1",
            owner_id=1,
            knowledge_base_id="kb-1",
            message_id="message-1",
            question="Compare the evidence",
            answer_mode="analysis_query",
        )

        self.assertFalse(session.multi_agent_enabled)
        self.assertEqual(request.execution_mode, "single")


if __name__ == "__main__":
    unittest.main()
