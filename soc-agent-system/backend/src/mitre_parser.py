"""MITRE ATT&CK tag extraction and merging utilities."""
import json
import re
import logging
from typing import List

from models import MitreTag

logger = logging.getLogger(__name__)


def extract_mitre_tags(agent_output: str, source: str = "priority_agent") -> List[MitreTag]:
    """
    Extract MITRE ATT&CK tags from agent output using regex.
    
    Looks for <MITRE_TAGS>...</MITRE_TAGS> XML-style block containing JSON array.
    Filters out tags with confidence < 0.6.
    
    Args:
        agent_output: Raw LLM output string
        source: Source identifier for the tags (default: "priority_agent")
        
    Returns:
        List of MitreTag objects, or empty list if extraction fails
    """
    try:
        # Extract content between <MITRE_TAGS> and </MITRE_TAGS>
        pattern = r'<MITRE_TAGS>\s*(.*?)\s*</MITRE_TAGS>'
        match = re.search(pattern, agent_output, re.DOTALL | re.IGNORECASE)
        
        if not match:
            logger.debug(f"No <MITRE_TAGS> block found in {source} output")
            return []
        
        json_str = match.group(1).strip()
        
        # Parse JSON array
        tags_data = json.loads(json_str)
        
        if not isinstance(tags_data, list):
            logger.warning(f"MITRE_TAGS content is not a list in {source} output")
            return []
        
        # Convert to MitreTag objects
        tags = []
        for tag_dict in tags_data:
            try:
                # Validate required fields
                if not isinstance(tag_dict, dict):
                    continue
                
                if "technique_id" not in tag_dict:
                    continue
                
                # Set defaults for optional fields
                tag_dict.setdefault("technique_name", tag_dict["technique_id"])
                tag_dict.setdefault("tactic", "Unknown")
                tag_dict.setdefault("tactic_id", "TA0000")
                tag_dict.setdefault("confidence", 0.8)
                tag_dict["source"] = source
                
                # Create MitreTag
                tag = MitreTag(**tag_dict)
                
                # Filter by confidence threshold
                if tag.confidence >= 0.6:
                    tags.append(tag)
                else:
                    logger.debug(f"Filtered out low-confidence tag: {tag.technique_id} ({tag.confidence})")
                    
            except Exception as e:
                logger.debug(f"Skipping malformed MITRE tag entry: {e}")
                continue
        
        logger.info(f"Extracted {len(tags)} MITRE tags from {source}")
        return tags
        
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse MITRE_TAGS JSON from {source}: {e}")
        return []
    except Exception as e:
        logger.warning(f"Unexpected error extracting MITRE tags from {source}: {e}")
        return []


def build_wazuh_tags(mitre_hints: List[str]) -> List[MitreTag]:
    """
    Build MITRE tags from Wazuh hints with confidence 1.0.
    
    Args:
        mitre_hints: List of technique IDs from Wazuh (e.g. ["T1475", "T1533"])
        
    Returns:
        List of MitreTag objects with source="wazuh" and confidence=1.0
    """
    tags = []
    
    for technique_id in mitre_hints:
        # Validate technique ID format
        if not isinstance(technique_id, str) or not technique_id.startswith("T"):
            logger.debug(f"Skipping invalid Wazuh technique ID: {technique_id}")
            continue
        
        # Create tag with placeholder values (will be enriched later if needed)
        tag = MitreTag(
            technique_id=technique_id,
            technique_name=technique_id,  # Placeholder
            tactic="Unknown",  # Placeholder
            tactic_id="TA0000",  # Placeholder
            confidence=1.0,
            source="wazuh"
        )
        tags.append(tag)
    
    logger.info(f"Built {len(tags)} MITRE tags from Wazuh hints")
    return tags


def merge_mitre_tags(wazuh_tags: List[MitreTag], priority_tags: List[MitreTag]) -> List[MitreTag]:
    """
    Merge MITRE tags from multiple sources with deduplication.
    
    Rules:
    - Wazuh tags come first (highest priority)
    - Deduplicate by technique_id (keep first occurrence)
    - Cap at 6 techniques maximum
    
    Args:
        wazuh_tags: Tags from Wazuh (confidence 1.0)
        priority_tags: Tags from PriorityAgent LLM
        
    Returns:
        Merged and deduplicated list of up to 6 MitreTag objects
    """
    merged = []
    seen_ids = set()
    
    # Add Wazuh tags first (highest priority)
    for tag in wazuh_tags:
        if tag.technique_id not in seen_ids:
            merged.append(tag)
            seen_ids.add(tag.technique_id)
    
    # Add PriorityAgent tags (deduplicate)
    for tag in priority_tags:
        if tag.technique_id not in seen_ids:
            merged.append(tag)
            seen_ids.add(tag.technique_id)
    
    # Cap at 6 techniques
    if len(merged) > 6:
        logger.info(f"Capping MITRE tags from {len(merged)} to 6")
        merged = merged[:6]
    
    logger.info(f"Merged {len(merged)} MITRE tags (Wazuh: {len(wazuh_tags)}, Priority: {len(priority_tags)})")
    return merged

