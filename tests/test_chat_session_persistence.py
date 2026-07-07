import unittest


class ChatSessionPersistenceContractTest(unittest.TestCase):
    def test_chat_session_router_is_registered(self):
        from app.mneme.bootstrap.router_registry import ROUTER_MODULE_NAMES

        self.assertIn("app.mneme.domains.chat.router", ROUTER_MODULE_NAMES)

    def test_chat_message_model_is_registered(self):
        import app.mneme.models as models

        self.assertTrue(hasattr(models, "ChatSession"))
        self.assertTrue(hasattr(models, "ChatMessage"))


if __name__ == "__main__":
    unittest.main()
