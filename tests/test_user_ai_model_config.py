import unittest


class UserAiModelConfigContractTest(unittest.TestCase):
    def test_settings_router_is_registered(self):
        from app.mneme.bootstrap.router_registry import ROUTER_MODULE_NAMES

        self.assertIn("app.mneme.domains.settings.router", ROUTER_MODULE_NAMES)

    def test_ai_model_config_model_is_registered(self):
        import app.mneme.models as models

        self.assertTrue(hasattr(models, "AiModelConfig"))


if __name__ == "__main__":
    unittest.main()
