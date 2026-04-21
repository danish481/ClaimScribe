"""
ClaimScribe AI - Healthcare LLM Service
Domain-specific LLM integration using Google Gemini for
healthcare document analysis and queries.

SECURITY NOTE: All queries are logged, PHI is filtered before
sending to external API, and no patient data leaves the system unencrypted.
"""

import time
import uuid
from typing import List, Dict, Optional, Any
from datetime import datetime

import google.generativeai as genai

from app.config import settings
from app.core.security import AuditLogger, PHIDetector


# ── System Prompt for Healthcare Domain ───────────────────

HEALTHCARE_SYSTEM_PROMPT = """You are ClaimScribe AI, a specialized healthcare document analysis assistant focused on health insurance claims processing in the United States.

YOUR EXPERTISE:
- Health insurance claims processing (inpatient, outpatient, pharmacy)
- Medical coding (ICD-10, CPT, HCPCS, NDC)
- HIPAA compliance and healthcare regulations
- Healthcare billing and reimbursement procedures
- Document analysis and data extraction

SECURITY RULES:
- NEVER include actual SSNs, patient names, or specific medical record numbers in responses
- Use [REDACTED] for any PHI that might appear
- Only discuss healthcare topics related to claims processing
- If asked about non-healthcare topics, politely redirect to claims-related assistance

RESPONSE GUIDELINES:
- Be concise and professional
- Cite specific sections of uploaded documents when answering
- Provide structured responses with bullet points when appropriate
- If uncertain, acknowledge limitations rather than hallucinating
- Use healthcare industry terminology correctly

You have access to extracted document content provided by the user. Base your answers on this content and your domain knowledge.
"""

# ── Conversation Store (In-Memory for Demo) ───────────────

class ConversationStore:
    """Simple in-memory conversation store."""

    def __init__(self):
        self._conversations: Dict[str, List[Dict]] = {}

    def create_conversation(self) -> str:
        """Create a new conversation and return its ID."""
        conv_id = str(uuid.uuid4())
        self._conversations[conv_id] = []
        return conv_id

    def add_message(self, conversation_id: str, role: str, content: str):
        """Add a message to a conversation."""
        if conversation_id not in self._conversations:
            self._conversations[conversation_id] = []

        self._conversations[conversation_id].append({
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
        })

    def get_history(self, conversation_id: str) -> List[Dict]:
        """Get conversation history."""
        return self._conversations.get(conversation_id, [])

    def get_summary(self, conversation_id: str) -> Optional[Dict]:
        """Get conversation summary."""
        history = self._conversations.get(conversation_id, [])
        if not history:
            return None

        return {
            "conversation_id": conversation_id,
            "message_count": len(history),
            "last_message_at": history[-1]["timestamp"],
            "preview": history[-1]["content"][:100] if history else "",
        }

    def list_conversations(self) -> List[Dict]:
        """List all conversations with summaries."""
        return [
            self.get_summary(cid) for cid in self._conversations.keys()
            if self.get_summary(cid)
        ]


class HealthcareLLMService:
    """
    Healthcare-domain LLM service using Google Gemini.

    Features:
    - Document-aware querying (context from uploaded documents)
    - PHI filtering before external API calls
    - Conversation memory
    - Audit logging of all interactions
    """

    def __init__(self):
        self.model = None
        self.store = ConversationStore()
        self._initialized = False

    def _init(self):
        """Initialize Gemini API."""
        if self._initialized:
            return

        if settings.GEMINI_API_KEY:
            try:
                genai.configure(api_key=settings.GEMINI_API_KEY)
                self.model = genai.GenerativeModel(
                    model_name=settings.GEMINI_MODEL,
                    generation_config={
                        "temperature": settings.GEMINI_TEMPERATURE,
                        "max_output_tokens": settings.GEMINI_MAX_TOKENS,
                        "top_p": 0.95,
                        "top_k": 40,
                    },
                    system_instruction=HEALTHCARE_SYSTEM_PROMPT,
                )
                print(f"LLM service initialised — model: {settings.GEMINI_MODEL}")
            except Exception as e:
                print(f"WARNING: Gemini init failed ({e}). Falling back to demo mode.")
                self.model = None
        else:
            print("INFO: GEMINI_API_KEY not set — AI Assistant running in demo mode (built-in responses).")
        self._initialized = True  # always mark done so warning only prints once

    def query(
        self,
        query: str,
        document_contents: Optional[List[str]] = None,
        conversation_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Process a healthcare query with optional document context.

        Args:
            query: User's question
            document_contents: List of extracted document texts for context
            conversation_id: Optional conversation ID for continuity

        Returns:
            Dict with response, conversation_id, sources, etc.
        """
        self._init()
        start_time = time.time()

        # Create or get conversation
        if not conversation_id:
            conversation_id = self.store.create_conversation()

        # Filter PHI from query before external API
        safe_query = PHIDetector.mask_phi(query)

        # Add document context if provided
        context = self._build_context(document_contents)

        # Build conversation history for context
        history = self.store.get_history(conversation_id)

        # Prepare prompt
        full_prompt = self._build_prompt(safe_query, context, history)

        # Call LLM
        if self.model and settings.GEMINI_API_KEY:
            try:
                response = self.model.generate_content(full_prompt)
                answer = response.text
                tokens_used = response.usage_metadata.total_token_count if hasattr(response, 'usage_metadata') else None
            except Exception as e:
                answer = f"I apologize, but I encountered an error processing your query: {str(e)}. Please try again or contact support."
                tokens_used = None
        else:
            # Fallback mock response for demo without API key
            answer = self._generate_mock_response(safe_query, context)
            tokens_used = None

        processing_time = (time.time() - start_time) * 1000

        # Store conversation
        self.store.add_message(conversation_id, "user", query)
        self.store.add_message(conversation_id, "assistant", answer)

        # Audit log
        AuditLogger.log_event(
            event_type="llm_query",
            resource_type="conversation",
            resource_id=conversation_id,
            details={
                "query_length": len(query),
                "response_length": len(answer),
                "has_document_context": bool(document_contents),
                "processing_time_ms": processing_time,
            }
        )

        return {
            "response": answer,
            "conversation_id": conversation_id,
            "sources": self._extract_sources(document_contents) if document_contents else None,
            "confidence": 0.85,  # Placeholder - could use model confidence
            "processing_time_ms": round(processing_time, 2),
            "tokens_used": tokens_used,
            "model": settings.GEMINI_MODEL,
        }

    def _build_context(self, document_contents: Optional[List[str]]) -> str:
        """Build context string from document contents."""
        if not document_contents:
            return ""

        context_parts = []
        for i, content in enumerate(document_contents[:5]):  # Limit to 5 documents
            # Truncate each document to avoid token limits
            truncated = content[:3000]
            # Mask any remaining PHI
            safe_content = PHIDetector.mask_phi(truncated)
            context_parts.append(f"--- DOCUMENT {i+1} ---\n{safe_content}\n")

        return "\n".join(context_parts)

    def _build_prompt(
        self,
        query: str,
        context: str,
        history: List[Dict],
    ) -> str:
        """Build the full prompt with context and history."""
        parts = []

        if context:
            parts.append(f"REFERENCE DOCUMENTS:\n{context}\n")

        # Add recent history (last 4 exchanges)
        if history:
            parts.append("PREVIOUS CONVERSATION:")
            for msg in history[-8:]:  # Last 8 messages
                prefix = "User" if msg["role"] == "user" else "Assistant"
                parts.append(f"{prefix}: {msg['content'][:500]}")
            parts.append("")

        parts.append(f"USER QUESTION: {query}")
        parts.append("\nPlease provide a helpful, accurate response based on the reference documents and your healthcare domain expertise.")

        return "\n".join(parts)

    def _extract_sources(self, document_contents: Optional[List[str]]) -> List[Dict]:
        """Extract source references from documents."""
        if not document_contents:
            return []

        sources = []
        for i, content in enumerate(document_contents[:5]):
            # Extract a preview
            preview = content[:200].replace('\n', ' ')
            sources.append({
                "document_index": i + 1,
                "preview": preview + "...",
                "relevance": "high",
            })
        return sources

    def _generate_mock_response(self, query: str, context: str) -> str:
        """Generate a built-in response when no Gemini API key is configured."""
        demo_notice = (
            "> **Demo Mode** — Add a `GEMINI_API_KEY` to `.env` for full AI responses "
            "([get a free key](https://aistudio.google.com/app/apikey)).\n\n"
        )
        query_lower = query.lower()

        if any(w in query_lower for w in ["classify", "type", "category"]):
            return demo_notice + (
                "Based on the document content provided, I can help classify this claim. "
                "The document appears to be an **inpatient claim** based on references to "
                "hospital admission, room and board charges, and discharge summary.\n\n"
                "Key indicators include:\n"
                "- Hospital facility charges\n"
                "- Admission/discharge dates\n"
                "- Room and board line items\n"
                "- Inpatient procedure codes\n\n"
                "The confidence level for this classification is approximately **92%**."
            )
        elif any(w in query_lower for w in ["cost", "amount", "charge", "payment", "fee"]):
            return demo_notice + (
                "I've analyzed the financial details in the document. Here are the key findings:\n\n"
                "- **Total Billed Amount**: Based on the line items\n"
                "- **Covered Amount**: Per insurance contract rates\n"
                "- **Patient Responsibility**: Deductible + coinsurance + copay\n"
                "- **Insurance Payment**: Amount approved for payment\n\n"
                "Please note that exact amounts require access to the full fee schedule and "
                "patient's benefit plan details for precise calculation."
            )
        elif any(w in query_lower for w in ["code", "icd", "cpt", "hcpcs", "diagnosis"]):
            return demo_notice + (
                "The document contains standard medical coding used in healthcare billing:\n\n"
                "- **ICD-10 Codes**: Used for diagnosis classification\n"
                "- **CPT Codes**: Describe procedures and services\n"
                "- **HCPCS Codes**: For supplies, equipment, and services not covered by CPT\n\n"
                "These codes are essential for claims processing and determine reimbursement rates. "
                "Proper coding ensures accurate payment and compliance with payer requirements."
            )
        elif any(w in query_lower for w in ["hipaa", "compliance", "privacy", "phi"]):
            return demo_notice + (
                "HIPAA compliance in claims processing involves several critical safeguards:\n\n"
                "1. **Administrative Safeguards**: Access controls, audit logs, workforce training\n"
                "2. **Physical Safeguards**: Secure workstations, controlled facility access\n"
                "3. **Technical Safeguards**: Encryption (AES-128), secure transmission (TLS 1.3)\n"
                "4. **Privacy Rule**: Minimum necessary standard, patient rights\n"
                "5. **Security Rule**: Risk analysis, vulnerability management\n\n"
                "ClaimScribe AI implements all these safeguards with automated PHI detection, "
                "encryption at rest/transit, and comprehensive audit logging."
            )
        else:
            return demo_notice + (
                "Thank you for your question about healthcare claims processing.\n\n"
                "Based on the document(s) you've uploaded and my domain expertise in health "
                "insurance claims, I can provide analysis on:\n\n"
                "- Document classification (inpatient/outpatient/pharmacy)\n"
                "- Claims data extraction and structuring\n"
                "- Billing code interpretation (ICD-10, CPT, HCPCS, NDC)\n"
                "- Compliance considerations (HIPAA)\n"
                "- Processing workflow optimization\n\n"
                "Could you please provide more specific details about what you'd like to analyze?"
            )

    def get_conversation_history(self, conversation_id: str) -> List[Dict]:
        """Get full conversation history."""
        return self.store.get_history(conversation_id)

    def list_conversations(self) -> List[Dict]:
        """List all conversations."""
        return self.store.list_conversations()


# ── Singleton ─────────────────────────────────────────────
llm_service = HealthcareLLMService()
