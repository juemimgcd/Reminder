import unittest

from app.mneme.bootstrap.router_registry import ROUTER_MODULE_NAMES


class AdviceDomainConvergenceTest(unittest.TestCase):
    def test_router_registry_uses_advice_domain_router(self):
        legacy_advice_router = ".".join(("app", "mneme", "routers", "advice"))

        self.assertIn("app.mneme.domains.advice.router", ROUTER_MODULE_NAMES)
        self.assertNotIn(legacy_advice_router, ROUTER_MODULE_NAMES)

    def test_advice_domain_service_is_canonical(self):
        from app.mneme.domains.advice.service import build_growth_advice

        self.assertEqual(build_growth_advice.__module__, "app.mneme.domains.advice.service")

    def test_advice_router_keeps_public_path(self):
        from app.mneme.main import app

        paths = set(app.openapi()["paths"])
        self.assertIn("/advice/knowledge-bases/{knowledge_base_id}", paths)


if __name__ == "__main__":
    unittest.main()
