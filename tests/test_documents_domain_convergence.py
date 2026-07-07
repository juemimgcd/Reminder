import unittest

from app.mneme.bootstrap.router_registry import ROUTER_MODULE_NAMES


class DocumentsDomainConvergenceTest(unittest.TestCase):
    def test_router_registry_uses_documents_domain_router(self):
        self.assertIn("app.mneme.domains.documents.router", ROUTER_MODULE_NAMES)
        legacy_documents_router = ".".join(("app", "mneme", "routers", "documents"))

        self.assertNotIn(legacy_documents_router, ROUTER_MODULE_NAMES)

    def test_documents_pipeline_imports_from_domain(self):
        from app.mneme.domains.documents.pipeline import run_document_index_pipeline

        self.assertEqual(run_document_index_pipeline.__name__, "run_document_index_pipeline")

    def test_documents_router_keeps_public_paths(self):
        from app.mneme.main import app

        paths = {route.path for route in app.routes}
        self.assertIn("/kb/documents/upload", paths)
        self.assertIn("/kb/documents", paths)
        self.assertIn("/kb/documents/{document_id}/preview", paths)
        self.assertIn("/kb/documents/{document_id}/index", paths)
        self.assertIn("/kb/documents/{document_id}", paths)


if __name__ == "__main__":
    unittest.main()
