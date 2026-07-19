import unittest

from app.mneme.domains.retrieval.citation_validation import (
    apply_citation_confidence_policy,
    quote_exists_in_source,
    validate_citation_drafts,
)
from app.mneme.schemas.chat import EvidenceCitationDraft


class CitationValidationServiceTest(unittest.TestCase):
    def test_quote_match_ignores_case_and_whitespace(self):
        self.assertTrue(
            quote_exists_in_source(
                quote="Graph backed retrieval",
                source_text="Graph\n backed   retrieval keeps evidence traceable.",
            )
        )

    def test_empty_quote_never_matches(self):
        self.assertFalse(quote_exists_in_source(quote="  ", source_text="anything"))

    def test_validate_citations_keeps_valid_and_reports_invalid(self):
        result = validate_citation_drafts(
            [
                EvidenceCitationDraft(source_id="S1", quote="vector recall", reason="supports retrieval"),
                EvidenceCitationDraft(source_id="S2", quote="missing quote", reason="bad quote"),
                EvidenceCitationDraft(source_id="S3", quote="anything", reason="bad source"),
            ],
            [
                {
                    "source_id": "S1",
                    "document_id": "doc-1",
                    "chunk_id": "chunk-1",
                    "page_no": 2,
                    "text": "The system combines vector recall with keyword recall.",
                },
                {
                    "source_id": "S2",
                    "document_id": "doc-2",
                    "chunk_id": "chunk-2",
                    "page_no": None,
                    "text": "This source does not contain the requested evidence.",
                },
            ],
        )

        self.assertEqual(len(result["valid_citations"]), 1)
        self.assertEqual(len(result["invalid_citations"]), 2)
        self.assertEqual(result["valid_citations"][0]["document_id"], "doc-1")
        self.assertEqual(result["invalid_citations"][0]["validation_reason"], "quote_not_found_in_source")
        self.assertEqual(result["invalid_citations"][1]["validation_reason"], "source_id_not_found")
        self.assertEqual(
            result["summary"],
            {
                "source_count": 2,
                "draft_citation_count": 3,
                "valid_citation_count": 1,
                "invalid_citation_count": 2,
                "has_valid_citation": True,
            },
        )

    def test_confidence_is_lowered_when_all_citations_fail(self):
        confidence, uncertainty = apply_citation_confidence_policy(
            confidence="high",
            uncertainty=None,
            citation_validation={
                "summary": {
                    "source_count": 1,
                    "draft_citation_count": 1,
                    "valid_citation_count": 0,
                    "invalid_citation_count": 1,
                }
            },
        )

        self.assertEqual(confidence, "low")
        self.assertIn("did not match retrieved sources", uncertainty)


if __name__ == "__main__":
    unittest.main()
