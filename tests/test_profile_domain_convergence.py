import unittest

from app.mneme.bootstrap.router_registry import ROUTER_MODULE_NAMES


class ProfileDomainConvergenceTest(unittest.TestCase):
    def test_router_registry_uses_profile_domain_router(self):
        legacy_profile_router = ".".join(("app", "mneme", "routers", "profile"))

        self.assertIn("app.mneme.domains.profile.router", ROUTER_MODULE_NAMES)
        self.assertNotIn(legacy_profile_router, ROUTER_MODULE_NAMES)

    def test_profile_domain_modules_are_canonical(self):
        from app.mneme.domains.profile.insight import build_profile_for_knowledge_base
        from app.mneme.domains.profile.service import build_personal_profile
        from app.mneme.domains.profile.tools import build_evidence_profile_from_entries

        self.assertEqual(build_personal_profile.__module__, "app.mneme.domains.profile.service")
        self.assertEqual(build_evidence_profile_from_entries.__module__, "app.mneme.domains.profile.tools")
        self.assertEqual(build_profile_for_knowledge_base.__module__, "app.mneme.domains.profile.insight")

    def test_profile_router_keeps_public_paths(self):
        from app.mneme.main import app

        paths = set(app.openapi()["paths"])
        self.assertIn("/profile/knowledge-bases/{knowledge_base_id}", paths)
        self.assertIn("/profile/knowledge-bases/{knowledge_base_id}/evidence", paths)


if __name__ == "__main__":
    unittest.main()
