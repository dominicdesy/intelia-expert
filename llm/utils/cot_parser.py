# -*- coding: utf-8 -*-
"""
cot_parser.py - Chain-of-Thought Parser for Backend

Extracts <thinking>, <analysis>, and <answer> sections from LLM responses
Saves thinking/analysis to database for analytics and debugging
Returns only <answer> to frontend for clean UX
"""

import re
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class CotParser:
    """Parser for Chain-of-Thought structured responses"""

    @staticmethod
    def parse_cot_response(content: str) -> Dict[str, Optional[str]]:
        """
        Parse CoT XML structure from LLM response

        Args:
            content: Full LLM response with potential CoT tags

        Returns:
            Dict with keys:
                - thinking: Content of <thinking> section (or None)
                - analysis: Content of <analysis> section (or None)
                - answer: Content of <answer> section (or full content if no tags)
                - has_structure: Boolean indicating if CoT tags were found
                - raw_response: Original unmodified content
        """
        if not content:
            return {
                "thinking": None,
                "analysis": None,
                "answer": "",
                "has_structure": False,
                "raw_response": content,
            }

        # Extract thinking section
        thinking_match = re.search(
            r"<thinking>(.*?)</thinking>", content, re.DOTALL | re.IGNORECASE
        )
        thinking = thinking_match.group(1).strip() if thinking_match else None

        # Extract analysis section
        analysis_match = re.search(
            r"<analysis>(.*?)</analysis>", content, re.DOTALL | re.IGNORECASE
        )
        analysis = analysis_match.group(1).strip() if analysis_match else None

        # Extract answer section
        answer_match = re.search(
            r"<answer>(.*?)</answer>", content, re.DOTALL | re.IGNORECASE
        )

        # DEBUG: Log what was found
        logger.debug(f"🔍 Regex matches - thinking: {thinking_match is not None}, analysis: {analysis_match is not None}, answer: {answer_match is not None}")
        if thinking_match:
            logger.debug(f"🔍 Thinking found: {len(thinking)} chars")
        if analysis_match:
            logger.debug(f"🔍 Analysis found: {len(analysis)} chars")

        if answer_match:
            # Perfect case: all three tags present
            answer = answer_match.group(1).strip()
            has_structure = True
            logger.debug(f"✅ Complete CoT structure with <answer> tag")
        elif thinking_match or analysis_match:
            # Fallback: thinking/analysis present but answer tag missing
            # This happens when max_tokens is reached before </answer> can be generated
            # Extract everything after </analysis> or </thinking> as the answer
            logger.warning(f"⚠️ Answer tag NOT found, but thinking/analysis present - extracting content after tags")

            # Find the last closing tag (</analysis> or </thinking>)
            last_closing_analysis = content.rfind("</analysis>")
            last_closing_thinking = content.rfind("</thinking>")

            # Get position after the last closing tag
            split_pos = max(last_closing_analysis, last_closing_thinking)

            if split_pos > 0:
                # Extract everything after the last closing tag
                split_pos += len("</analysis>") if last_closing_analysis > last_closing_thinking else len("</thinking>")
                answer = content[split_pos:].strip()
                has_structure = True
                logger.info(f"🔧 Extracted answer from content after tags: {len(answer)} chars")
            else:
                # Fallback: use full content
                answer = content.strip()
                has_structure = False
                logger.warning(f"⚠️ Could not find closing tags, using full content")
        else:
            # No CoT structure at all - use full content as answer
            answer = content.strip()
            has_structure = False
            logger.debug(f"No CoT tags found, using full content as answer")

        # Log CoT detection
        if has_structure:
            logger.info(
                f"🧠 CoT structure detected - thinking: {len(thinking or '')} chars, "
                f"analysis: {len(analysis or '')} chars, answer: {len(answer)} chars"
            )
        else:
            logger.debug("No CoT structure found - using full response as answer")

        return {
            "thinking": thinking,
            "analysis": analysis,
            "answer": answer,
            "has_structure": has_structure,
            "raw_response": content,
        }

    @staticmethod
    def strip_cot_tags(content: str) -> str:
        """
        Remove all CoT XML tags from content, leaving only the answer

        Args:
            content: Full LLM response with potential CoT tags

        Returns:
            Clean answer text without any XML tags
        """
        parsed = CotParser.parse_cot_response(content)
        return parsed["answer"]

    @staticmethod
    def has_cot_structure(content: str) -> bool:
        """
        Quick check if content contains CoT structure

        Args:
            content: Full LLM response

        Returns:
            True if <thinking>, <analysis>, or <answer> tags found
        """
        if not content:
            return False

        return bool(
            re.search(r"<(thinking|analysis|answer)>", content, re.IGNORECASE)
        )


# Convenience functions for direct import
def parse_cot_response(content: str) -> Dict[str, Optional[str]]:
    """Parse CoT response - convenience function"""
    return CotParser.parse_cot_response(content)


def strip_cot_tags(content: str) -> str:
    """Strip CoT tags - convenience function"""
    return CotParser.strip_cot_tags(content)


def has_cot_structure(content: str) -> bool:
    """Check for CoT structure - convenience function"""
    return CotParser.has_cot_structure(content)
