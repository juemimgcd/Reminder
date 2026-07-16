import unittest


class UserAiModelConfigContractTest(unittest.TestCase):
    def test_settings_router_is_registered(self):
        from app.mneme.bootstrap.router_registry import ROUTER_MODULE_NAMES

        self.assertIn("app.mneme.memoria.configuration.router", ROUTER_MODULE_NAMES)

    def test_ai_model_config_model_is_registered(self):
        from app.mneme.memoria.models.ai_model_config import AiModelConfig
        from app.mneme.models.base import Base

        self.assertIs(Base.metadata.tables["ai_model_configs"], AiModelConfig.__table__)


if __name__ == "__main__":
    unittest.main()
