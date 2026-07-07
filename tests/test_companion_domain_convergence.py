import unittest

from app.mneme.bootstrap.router_registry import ROUTER_MODULE_NAMES


class CompanionDomainConvergenceTest(unittest.TestCase):
    def test_router_registry_uses_companion_domain_router(self):
        legacy_companion_router = ".".join(("app", "mneme", "routers", "companion"))

        self.assertIn("app.mneme.domains.companion.router", ROUTER_MODULE_NAMES)
        self.assertNotIn(legacy_companion_router, ROUTER_MODULE_NAMES)

    def test_companion_domain_service_is_canonical(self):
        from app.mneme.domains.companion.service import build_companion_response

        self.assertEqual(build_companion_response.__module__, "app.mneme.domains.companion.service")

    def test_companion_router_keeps_public_path(self):
        from app.mneme.main import app

        paths = {route.path for route in app.routes}
        self.assertIn("/companion/knowledge-bases/{knowledge_base_id}/reply", paths)


if __name__ == "__main__":
    unittest.main()
