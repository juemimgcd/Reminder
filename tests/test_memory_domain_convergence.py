import unittest

from app.mneme.bootstrap.router_registry import ROUTER_MODULE_NAMES


class MemoryDomainConvergenceTest(unittest.TestCase):
    def test_router_registry_uses_memory_domain_router(self):
        legacy_memory_router = ".".join(("app", "mneme", "routers", "memory"))

        self.assertIn("app.mneme.domains.memory.router", ROUTER_MODULE_NAMES)
        self.assertNotIn(legacy_memory_router, ROUTER_MODULE_NAMES)

    def test_memory_domain_modules_are_canonical(self):
        from app.mneme.domains.memory.governance import build_memory_governance_view
        from app.mneme.domains.memory.service import build_memory_library

        self.assertEqual(build_memory_library.__module__, "app.mneme.domains.memory.service")
        self.assertEqual(build_memory_governance_view.__module__, "app.mneme.domains.memory.governance")

    def test_memory_router_keeps_public_paths(self):
        from app.mneme.main import app

        paths = set(app.openapi()["paths"])
        self.assertIn("/memory/knowledge-bases/{knowledge_base_id}/library", paths)
        self.assertIn("/memory/knowledge-bases/{knowledge_base_id}/governance", paths)
        self.assertIn("/memory/knowledge-bases/{knowledge_base_id}/rebuild", paths)
        self.assertIn("/memory/documents/{document_id}/library", paths)


if __name__ == "__main__":
    unittest.main()
