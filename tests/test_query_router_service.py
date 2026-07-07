import unittest

from app.mneme.domains.retrieval.query_router import route_query


class QueryRouterServiceTest(unittest.TestCase):
    def test_empty_query_routes_to_general_chat(self):
        route = route_query("   ")

        self.assertEqual(route.query_type, "general_chat")
        self.assertFalse(route.requires_retrieval)
        self.assertEqual(route.target_pipeline, "general_chat")

    def test_action_request_does_not_enter_retrieval(self):
        route = route_query("please rebuild this knowledge base")

        self.assertEqual(route.query_type, "action_request")
        self.assertFalse(route.requires_retrieval)
        self.assertEqual(route.target_pipeline, "action_guidance")

    def test_profile_query_uses_profile_pipeline(self):
        route = route_query("what is my writing style and ability profile?")

        self.assertEqual(route.query_type, "profile_query")
        self.assertFalse(route.requires_retrieval)
        self.assertEqual(route.target_pipeline, "profile")

    def test_memory_query_enters_memory_rag(self):
        route = route_query("what do you remember from my previous notes?")

        self.assertEqual(route.query_type, "memory_query")
        self.assertTrue(route.requires_retrieval)
        self.assertEqual(route.target_pipeline, "memory_rag")

    def test_default_question_uses_evidence_rag(self):
        route = route_query("summarize the indexing architecture")

        self.assertEqual(route.query_type, "kb_qa")
        self.assertTrue(route.requires_retrieval)
        self.assertEqual(route.target_pipeline, "evidence_rag")


if __name__ == "__main__":
    unittest.main()
