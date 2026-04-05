"""
Input sanitizer for prompt injection detection.
Tier 2B: Detects and redacts 8 categories of injection patterns before LLM prompts.

Pattern categories:
1. Instruction override ("ignore previous instructions", "disregard all", etc.)
2. Role override ("you are now", "act as", "pretend to be")
3. System tag injection ("</system>", "<system>", "[SYSTEM:", etc.)
4. Data extraction ("repeat all", "output all", "reveal", "show me")
5. Disregard patterns ("DISREGARD", "FORGET", specific all-caps commands)
6. XML tag injection ("<admin>", "</config>", malicious markup)
7. Mode manipulation ("debug mode", "developer mode", "maintenance mode")
8. Prompt extraction ("what is your system prompt", "show your instructions")
"""

import re
import logging
from typing import Tuple

logger = logging.getLogger(__name__)

# Compiled regex patterns for performance
PATTERNS = {
    "instruction_override": re.compile(
        r"(?i)(ignore|disregard|forget|skip)\s+(all\s+)?(previous|prior|above|earlier)\s+(instructions?|prompts?|commands?|rules?|constraints?)",
        re.IGNORECASE
    ),
    "role_override": re.compile(
        r"(?i)(you are now|act as|pretend to be|simulate|roleplay as|assume the role)",
        re.IGNORECASE
    ),
    "system_tag_injection": re.compile(
        r"(</?system>|\[SYSTEM:|\[/SYSTEM\]|<system\s|</system>)",
        re.IGNORECASE
    ),
    "data_extraction": re.compile(
        r"(?i)(repeat|output|reveal|show|display|print|return|give\s+me).*(all|every|entire|complete|full)",
        re.IGNORECASE
    ),
    "disregard_all_caps": re.compile(
        r"\b(DISREGARD|IGNORE|FORGET|OVERRIDE|BYPASS)\s+(ALL|EVERYTHING|PREVIOUS)\b"
    ),
    "xml_tag_injection": re.compile(
        r"(</?admin>|</?config>|</?root>|</?privileged>|</\w+>\s*<\w+>)",
        re.IGNORECASE
    ),
    "mode_manipulation": re.compile(
        r"(?i)(you are now in|enter|activate|enable|switch to|go into)\s+.*(debug|developer|admin|maintenance|test|god)\s+mode",
        re.IGNORECASE
    ),
    "prompt_extraction": re.compile(
        r"(?i)(what is|show|reveal|display|print|give\s+me).*(system\s+)?(prompt|instructions|guidelines|rules)",
        re.IGNORECASE
    ),
}


def _detect_injection(text: str) -> Tuple[bool, list[str]]:
    """
    Detect injection patterns in text.
    
    Returns:
        (detected: bool, matched_categories: list[str])
    """
    detected = False
    matched_categories = []
    
    for category, pattern in PATTERNS.items():
        if pattern.search(text):
            detected = True
            matched_categories.append(category)
    
    return detected, matched_categories


def sanitize_for_prompt(text: str, field_name: str, source: str) -> str:
    """
    Generic sanitizer for any external text before prompt construction.
    
    Args:
        text: The input text to sanitize
        field_name: Name of the field (for logging)
        source: Source identifier (for logging, e.g., "threat_123", "note_456")
    
    Returns:
        Sanitized text with injections redacted
    """
    detected, categories = _detect_injection(text)
    
    if detected:
        logger.warning(
            f"[PROMPT_INJECTION] Detected in {field_name} from {source}: categories={categories}"
        )
        return f"[REDACTED: potential prompt injection detected in {field_name}]"
    
    return text


def sanitize_historical_note(note: str, note_id: str) -> str:
    """
    Sanitize historical analyst notes before HistoricalAgent prompt construction.
    
    Args:
        note: The analyst note text
        note_id: Identifier for the note (for logging)
    
    Returns:
        Sanitized note
    """
    return sanitize_for_prompt(note, "historical_note", f"note_{note_id}")


def sanitize_context_description(description: str, context_id: str) -> str:
    """
    Sanitize context descriptions before ContextAgent prompt construction.
    
    Args:
        description: The context description text
        context_id: Identifier for the context (for logging)
    
    Returns:
        Sanitized description
    """
    return sanitize_for_prompt(description, "context_description", f"context_{context_id}")


def sanitize_threat_details(details: str, threat_id: str) -> str:
    """
    Sanitize threat details before any agent prompt construction.
    
    Args:
        details: The threat details text
        threat_id: Identifier for the threat (for logging)
    
    Returns:
        Sanitized details
    """
    return sanitize_for_prompt(details, "threat_details", f"threat_{threat_id}")
