import pytest
from app.services.llm_service import llm_service


def test_llm_mock_response():
    result = llm_service.query(
        "What type of claim is this?",
        document_contents=["hospital admission"],
    )
    assert isinstance(result, dict)
    assert "response" in result
    assert isinstance(result["response"], str)
    assert len(result["response"]) > 0
    assert "conversation_id" in result
    assert "model" in result


def test_llm_mock_returns_conversation_id():
    r1 = llm_service.query("Is this inpatient?", document_contents=[])
    r2 = llm_service.query("Tell me more.", conversation_id=r1["conversation_id"])
    assert r1["conversation_id"] == r2["conversation_id"]
