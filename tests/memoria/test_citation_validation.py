from app.mneme.memoria.server.retrieval.contracts import RetrievedEvidence
from app.mneme.memoria.server.runtime.citations import EvidenceCitationValidator
from app.mneme.memoria.server.runtime.contracts import GeneratedAnswer


def test_invalid_citations_are_removed_and_metadata_is_allowlisted():
    evidence = RetrievedEvidence(
        evidence_id="e1",
        source_type="document",
        source_id="chunk-1",
        content="quoted text",
        score=1,
        metadata={"file_name": "notes.md", "secret": "do-not-leak"},
    )
    answer = GeneratedAnswer(
        answer="answer",
        route="kb_qa",
        confidence=0.95,
        citations=[
            {"evidence_id": "missing", "quote": "x"},
            {"evidence_id": "e1", "quote": "not present"},
            {"evidence_id": "e1", "quote": "quoted text"},
        ],
    )

    result = EvidenceCitationValidator().validate(answer, [evidence])

    assert [item["evidence_id"] for item in result.citations] == ["e1"]
    assert result.citations[0]["metadata"] == {"file_name": "notes.md"}
    assert result.confidence <= 0.6
    assert result.insufficient_evidence is False


def test_private_answer_without_supported_citation_is_downgraded():
    result = EvidenceCitationValidator().validate(
        GeneratedAnswer(answer="answer", route="memory_query", confidence=0.9, citations=[]),
        [],
    )

    assert result.citations == []
    assert result.confidence == 0.25
    assert result.insufficient_evidence is True
