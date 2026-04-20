"""
ClaimScribe AI - LLM Router
API endpoints for healthcare domain LLM queries
"""

from typing import Optional, List

from fastapi import APIRouter, HTTPException, Body

from app.models.schemas import LLMQueryRequest, LLMQueryResponse, ConversationSummary
from app.services.llm_service import llm_service
from app.services.document_processor import document_processor

router = APIRouter(prefix="/llm", tags=["Healthcare LLM"])


@router.post("/query", response_model=LLMQueryResponse)
async def query_llm(request: LLMQueryRequest):
    """
    Query the healthcare domain LLM with optional document context.

    The LLM has access to uploaded document content and can answer
    questions about claims processing, billing codes, compliance, etc.

    All queries are logged and PHI is automatically filtered.
    """
    # Gather document contents if requested
    doc_contents = None
    if request.document_ids:
        doc_contents = []
        for doc_id in request.document_ids:
            doc = document_processor.get_document(doc_id)
            if doc:
                # Use masked text if available
                text = doc.masked_text or doc.extracted_text
                doc_contents.append(text)
            else:
                raise HTTPException(status_code=404, detail=f"Document {doc_id} not found")

    # Call LLM service
    result = llm_service.query(
        query=request.query,
        document_contents=doc_contents,
        conversation_id=request.conversation_id,
    )

    return LLMQueryResponse(**result)


@router.get("/conversations")
async def list_conversations():
    """
    List all LLM conversation histories.
    """
    conversations = llm_service.list_conversations()
    return {"conversations": conversations}


@router.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: str):
    """
    Get full message history for a conversation.
    """
    history = llm_service.get_conversation_history(conversation_id)
    if not history:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"conversation_id": conversation_id, "messages": history}
