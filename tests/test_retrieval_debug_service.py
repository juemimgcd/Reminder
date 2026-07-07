import unittest

from app.mneme.schemas.chat import QueryRouteDecision
from app.mneme.domains.retrieval.debug import (
    build_answer_debug,
    build_non_retrieval_debug,
    preview_text,
)


class RetrievalDebugServiceTest(unittest.TestCase):
    def test_preview_text_collapses_whitespace_and_truncates(self):
        preview = preview_text("alpha\n\n beta   gamma delta", max_chars=16)

        self.assertEqual(preview, "alpha beta gamma...")

    def test_non_retrieval_debug_records_route_and_zero_counts(self):
        route = QueryRouteDecision(
            query_type="action_request",
            requires_retrieval=False,
            target_pipeline="action_guidance",
            confidence="medium",
            reason="system action",
        )

        debug = build_non_retrieval_debug(route=route, reason="action request bypassed retrieval")

        self.assertEqual(debug["route"]["query_type"], "action_request")
        self.assertEqual(debug["counts"]["candidate_count"], 0)
        self.assertEqual(debug["answer_debug"]["path"], "action_guidance")
        self.assertEqual(debug["final_context"], [])

    def test_answer_debug_lists_available_and_cited_sources(self):
        debug = build_answer_debug(
            answer="answer text",
            sources=[{"source_id": "S1"}, {"source_id": "S2"}],
            citations=[{"source_id": "S2"}],
            confidence="high",
            uncertainty=None,
        )

        self.assertEqual(debug["answer_length"], len("answer text"))
        self.assertEqual(debug["available_source_ids"], ["S1", "S2"])
        self.assertEqual(debug["cited_source_ids"], ["S2"])
        self.assertEqual(debug["confidence"], "high")


if __name__ == "__main__":
    unittest.main()
