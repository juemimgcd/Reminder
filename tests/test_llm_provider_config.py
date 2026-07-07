import unittest

from app.mneme.clients.llm_client import build_llm_kwargs
from app.mneme.conf.config import Settings


class LlmProviderConfigTest(unittest.TestCase):
    def test_requested_providers_resolve_openai_compatible_defaults(self):
        cases = {
            "qwen": ("https://dashscope.aliyuncs.com/compatible-mode/v1", "qwen-plus", "DASHSCOPE_API_KEY"),
            "mimo": ("https://api.xiaomimimo.com/v1", "mimo-v2.5-pro", "MIMO_API_KEY"),
            "kimi": ("https://api.moonshot.ai/v1", "kimi-k2.6", "KIMI_API_KEY"),
            "glm": ("https://api.z.ai/api/paas/v4", "glm-5", "GLM_API_KEY"),
            "deepseek": ("https://api.deepseek.com", "deepseek-v4-flash", "DEEPSEEK_API_KEY"),
        }

        for provider, (base_url, model_name, key_field) in cases.items():
            with self.subTest(provider=provider):
                settings = Settings(
                    _env_file=None,
                    LLM_PROVIDER=provider,
                    LLM_BASE_URL="",
                    LLM_MODEL_NAME="",
                    **{key_field: f"{provider}-key"},
                )

                kwargs = build_llm_kwargs(settings)

                self.assertEqual(kwargs["base_url"], base_url)
                self.assertEqual(kwargs["model"], model_name)
                self.assertEqual(kwargs["api_key"], f"{provider}-key")

    def test_generic_api_key_overrides_provider_specific_key(self):
        settings = Settings(
            _env_file=None,
            LLM_PROVIDER="kimi",
            LLM_API_KEY="generic-key",
            KIMI_API_KEY="kimi-key",
            LLM_BASE_URL="",
            LLM_MODEL_NAME="",
        )

        kwargs = build_llm_kwargs(settings)

        self.assertEqual(kwargs["api_key"], "generic-key")

    def test_mimo_adds_api_key_header_for_platform_compatibility(self):
        settings = Settings(
            _env_file=None,
            LLM_PROVIDER="mimo",
            MIMO_API_KEY="mimo-key",
            LLM_BASE_URL="",
            LLM_MODEL_NAME="",
        )

        kwargs = build_llm_kwargs(settings)

        self.assertEqual(kwargs["default_headers"], {"api-key": "mimo-key"})


if __name__ == "__main__":
    unittest.main()
