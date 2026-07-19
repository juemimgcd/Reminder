import unittest

from app.mneme.domains.eval.service import (
    calculate_citation_accuracy,
    calculate_faithfulness,
    evaluate_case,
    evaluate_retrieval,
    summarize_eval_results,
)
from app.mneme.schemas.eval import EvalCase, EvalPrediction


class EvalServiceTest(unittest.TestCase):
    def test_retrieval_metrics_use_expected_chunk_hits(self):
        metrics = evaluate_retrieval(
            expected_source_chunk_ids=["chunk-2", "chunk-4"],
            debug={
                "final_context": [
                    {"chunk_id": "chunk-1"},
                    {"chunk_id": "chunk-2"},
                    {"chunk_id": "chunk-3"},
                ]
            },
            k=3,
        )

        self.assertEqual(metrics.recall_at_k, 0.5)
        self.assertEqual(metrics.mrr, 0.5)
        self.assertAlmostEqual(metrics.ndcg, 0.3868528072)
        self.assertTrue(metrics.source_hit)

    def test_citation_accuracy_checks_cited_source_chunks(self):
        accuracy = calculate_citation_accuracy(
            expected_source_chunk_ids=["chunk-expected"],
            sources=[
                {"source_id": "S1", "source_chunk_ids": ["chunk-other"]},
                {"source_id": "S2", "source_chunk_ids": ["chunk-expected"]},
            ],
            citations=[
                {"source_id": "S1"},
                {"source_id": "S2"},
            ],
        )

        self.assertEqual(accuracy, 0.5)

    def test_faithfulness_counts_only_available_valid_citations(self):
        score = calculate_faithfulness(
            sources=[{"source_id": "S1"}, {"source_id": "S2"}],
            citations=[
                {"source_id": "S1", "validation_status": "valid", "quote_found": True},
                {"source_id": "S2", "validation_status": "invalid", "quote_found": False},
                {"source_id": "S3", "validation_status": "valid", "quote_found": True},
            ],
        )

        self.assertEqual(score, 1 / 3)

    def test_evaluate_case_combines_retrieval_generation_and_engineering_metrics(self):
        result = evaluate_case(
            case=EvalCase(
                case_id="case-1",
                question="What retrieves memories?",
                expected_answer="vector keyword memory",
                expected_source_chunk_ids=["chunk-2"],
                tags=["retrieval"],
                difficulty="easy",
            ),
            prediction=EvalPrediction(
                answer="The system uses vector, keyword, and memory recall.",
                sources=[
                    {
                        "source_id": "S1",
                        "source_chunk_ids": ["chunk-2"],
                    }
                ],
                citations=[
                    {
                        "source_id": "S1",
                        "validation_status": "valid",
                        "quote_found": True,
                    }
                ],
                debug={"final_context": [{"chunk_id": "chunk-2"}]},
                latency_ms=123.0,
                llm_call_count=1,
                retrieval_count=3,
            ),
            k=5,
        )

        self.assertEqual(result.case_id, "case-1")
        self.assertEqual(result.retrieval.recall_at_k, 1.0)
        self.assertEqual(result.generation.citation_accuracy, 1.0)
        self.assertGreater(result.generation.answer_relevance, 0.0)
        self.assertEqual(result.engineering.latency_ms, 123.0)

        summary = summarize_eval_results([result])
        self.assertEqual(summary["case_count"], 1)
        self.assertEqual(summary["avg_recall_at_k"], 1.0)


if __name__ == "__main__":
    unittest.main()
