import unittest
from pathlib import Path

from app.mneme.bootstrap.router_registry import ROUTER_MODULE_NAMES


class FinalBackendConvergenceTest(unittest.TestCase):
    def test_router_registry_uses_only_domain_routers(self):
        self.assertTrue(ROUTER_MODULE_NAMES)
        for module_name in ROUTER_MODULE_NAMES:
            self.assertTrue(
                module_name.startswith("app.mneme.domains."),
                f"legacy router module still registered: {module_name}",
            )

    def test_public_routes_are_preserved(self):
        from app.mneme.main import app

        paths = {route.path for route in app.routes}
        expected_paths = {
            "/health",
            "/health/neo4j",
            "/health/readiness",
            "/auth/register",
            "/auth/login",
            "/auth/me",
            "/users/{user_id}/knowledge-bases",
            "/analysis/knowledge-bases/{knowledge_base_id}/growth",
            "/analysis/knowledge-bases/{knowledge_base_id}/analytics",
            "/tasks/{task_id}",
            "/tasks/{task_id}/cancel",
            "/tasks/{task_id}/retry",
        }
        self.assertTrue(expected_paths.issubset(paths), expected_paths - paths)

    def test_remaining_business_modules_are_canonical(self):
        from app.mneme.domains.analysis.growth import build_growth_report
        from app.mneme.domains.analysis.service import build_knowledge_base_analytics_report
        from app.mneme.domains.documents.resources import delete_document_resources
        from app.mneme.domains.documents.service import submit_document_index_task
        from app.mneme.domains.eval.service import build_eval_run
        from app.mneme.domains.health.readiness import build_production_readiness_report
        from app.mneme.domains.retrieval.citation_validation import validate_citation_drafts
        from app.mneme.domains.tasks.admin import cancel_document_index_task
        from app.mneme.domains.tasks.outbox import dispatch_pending_outbox_events
        from app.mneme.domains.tasks.state import transition_task_status

        expected_modules = {
            build_growth_report: "app.mneme.domains.analysis.growth",
            build_knowledge_base_analytics_report: "app.mneme.domains.analysis.service",
            delete_document_resources: "app.mneme.domains.documents.resources",
            submit_document_index_task: "app.mneme.domains.documents.service",
            build_eval_run: "app.mneme.domains.eval.service",
            build_production_readiness_report: "app.mneme.domains.health.readiness",
            validate_citation_drafts: "app.mneme.domains.retrieval.citation_validation",
            cancel_document_index_task: "app.mneme.domains.tasks.admin",
            dispatch_pending_outbox_events: "app.mneme.domains.tasks.outbox",
            transition_task_status: "app.mneme.domains.tasks.state",
        }
        for function, module_name in expected_modules.items():
            self.assertEqual(function.__module__, module_name)

    def test_old_business_files_are_removed(self):
        old_paths = [
            "app/mneme/routers/health.py",
            "app/mneme/routers/auth.py",
            "app/mneme/routers/users.py",
            "app/mneme/routers/analysis.py",
            "app/mneme/routers/tasks.py",
            "app/mneme/routers/__init__.py",
            "app/mneme/services/analytics_service.py",
            "app/mneme/services/citation_validation_service.py",
            "app/mneme/services/document_service.py",
            "app/mneme/services/eval_service.py",
            "app/mneme/services/growth_service.py",
            "app/mneme/services/outbox_service.py",
            "app/mneme/services/production_readiness_service.py",
            "app/mneme/services/resource_service.py",
            "app/mneme/services/task_admin_service.py",
            "app/mneme/services/task_state_service.py",
            "app/mneme/services/__init__.py",
            "app/mneme/workflow/dispatcher.py",
            "app/mneme/workflow/outbox.py",
            "app/mneme/workflow/queue.py",
            "app/mneme/workflow/task_state.py",
            "app/mneme/workflow/jobs/index.py",
            "app/mneme/workflow/jobs/outbox.py",
            "app/mneme/workflow/__init__.py",
            "app/mneme/workflow/jobs/__init__.py",
        ]
        for path in old_paths:
            self.assertFalse(Path(path).exists(), path)


if __name__ == "__main__":
    unittest.main()
