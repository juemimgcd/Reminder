import unittest

from app.mneme.bootstrap.router_registry import ROUTER_MODULE_NAMES


class GraphDomainConvergenceTest(unittest.TestCase):
    def test_router_registry_uses_graph_domain_router(self):
        legacy_graph_router = ".".join(("app", "mneme", "routers", "graph"))

        self.assertIn("app.mneme.domains.graph.router", ROUTER_MODULE_NAMES)
        self.assertNotIn(legacy_graph_router, ROUTER_MODULE_NAMES)

    def test_graph_domain_modules_are_importable(self):
        from app.mneme.domains.graph.admin import rebuild_graph_projection_for_user
        from app.mneme.domains.graph.projection import sync_document_memory_projection
        from app.mneme.domains.graph.query import build_user_graph_payload_from_neo4j
        from app.mneme.domains.graph.rag import build_graph_rag_decision
        from app.mneme.domains.graph.service import build_user_graph_payload

        self.assertEqual(build_user_graph_payload.__name__, "build_user_graph_payload")
        self.assertEqual(build_user_graph_payload_from_neo4j.__name__, "build_user_graph_payload_from_neo4j")
        self.assertEqual(sync_document_memory_projection.__name__, "sync_document_memory_projection")
        self.assertEqual(rebuild_graph_projection_for_user.__name__, "rebuild_graph_projection_for_user")
        self.assertEqual(build_graph_rag_decision.__name__, "build_graph_rag_decision")

    def test_graph_router_keeps_public_paths(self):
        from app.mneme.main import app

        paths = {route.path for route in app.routes}
        self.assertIn("/graph", paths)
        self.assertIn("/graph/rebuild", paths)
        self.assertIn("/graph/documents/{document_id}", paths)
        self.assertIn("/graph/knowledge-bases/{knowledge_base_id}", paths)
        self.assertIn("/graph/knowledge-bases/{knowledge_base_id}/rag", paths)
        self.assertIn("/graph/knowledge-bases/{knowledge_base_id}/rebuild", paths)


if __name__ == "__main__":
    unittest.main()
