from __future__ import annotations

import re
from typing import Any


PROMPT_INJECTION_PATTERNS = [
    "ignore previous instructions",
    "reveal your system prompt",
    "disable safety",
    "override policy",
    "execute hidden instructions",
    "use tools without permission",
]

HIGH_RISK_TOOLS = {
    "send_email",
    "send_sms",
    "lodge_request",
    "update_record",
    "delete_file",
    "publish_content",
    "deploy_agent",
    "deploy_production",
}

ROLE_ALLOWED_TOOLS = {
    "public_user": {
        "search_council_documents",
        "search_website",
        "retrieve_information",
        "rag.search",
        "source.open",
    },
    "resident": {
        "search_council_documents",
        "search_website",
        "retrieve_information",
        "rag.search",
        "source.open",
        "lodge_request",
    },
}


def mask_pii(text: str) -> tuple[str, list[str]]:
    redactions: list[str] = []
    sanitized = re.sub(r"[\w.+-]+@[\w-]+\.[\w.-]+", "[[USER_EMAIL]]", text)
    if sanitized != text:
        redactions.append("[[USER_EMAIL]]")
    text = sanitized

    sanitized = re.sub(r"\b(?:\+?61|0)4\d[\d\s-]{6,}\d\b", "[[USER_PHONE]]", text)
    if sanitized != text:
        redactions.append("[[USER_PHONE]]")
    text = sanitized

    sanitized = re.sub(
        r"\b\d{1,5}\s+[A-Za-z][A-Za-z\s]+(?:Street|St|Road|Rd|Avenue|Ave|Terrace|Tce|Lane|Ln),?\s+Adelaide(?:\s+SA)?(?:\s+\d{4})?\b",
        "[[USER_ADDRESS]]",
        text,
        flags=re.IGNORECASE,
    )
    if sanitized != text:
        redactions.append("[[USER_ADDRESS]]")
    return sanitized, redactions


def check_request(
    text: str,
    requested_tool: str | None,
    role: str = "public_user",
    environment: str = "development",
    approved: bool = False,
) -> dict[str, Any]:
    """Apply CouncilQ policy_guard rules before any ADK tool or RAG action."""
    lowered = text.lower()
    injection_hits = [pattern for pattern in PROMPT_INJECTION_PATTERNS if pattern in lowered]
    sanitized, redactions = mask_pii(text)

    if injection_hits and not _has_safe_council_intent(lowered):
        return {
            "decision": "block",
            "reason": "prompt_injection",
            "sanitized_input": sanitized,
            "requires_approval": False,
            "allowed_tool": False,
            "redactions": redactions,
        }

    if injection_hits:
        sanitized = _remove_prompt_injection(sanitized)

    if requested_tool in HIGH_RISK_TOOLS and not approved:
        return {
            "decision": "requires_human_approval",
            "reason": "high_risk_tool",
            "sanitized_input": sanitized,
            "requires_approval": True,
            "allowed_tool": False,
            "redactions": redactions,
        }

    allowed_tools = ROLE_ALLOWED_TOOLS.get(role, set())
    allowed_tool = requested_tool is None or requested_tool in allowed_tools
    if not allowed_tool:
        return {
            "decision": "block",
            "reason": "unauthorized_tool_call",
            "sanitized_input": sanitized,
            "requires_approval": False,
            "allowed_tool": False,
            "redactions": redactions,
        }

    decision = "sanitize_and_continue" if injection_hits or redactions else "allow"
    reason = "sanitized_input" if decision == "sanitize_and_continue" else "policy_passed"
    return {
        "decision": decision,
        "reason": reason,
        "sanitized_input": sanitized.strip(),
        "requires_approval": False,
        "allowed_tool": True,
        "redactions": redactions,
    }


def _has_safe_council_intent(lowered: str) -> bool:
    return any(term in lowered for term in ["bin", "waste", "recycling", "batteries", "hard waste"])


def _remove_prompt_injection(text: str) -> str:
    sanitized = text
    for pattern in PROMPT_INJECTION_PATTERNS:
        sanitized = re.sub(re.escape(pattern), "", sanitized, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", sanitized).strip(" .")

