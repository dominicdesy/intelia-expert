# -*- coding: utf-8 -*-
"""
Helper functions for StandardQueryHandler
"""

import logging
import traceback
from utils.types import Dict, Any, List
from core.response_validator import get_response_validator

logger = logging.getLogger(__name__)


def parse_contextual_history(preprocessed_data: Dict[str, Any]) -> List[Dict[str, str]]:
    """
    Parse contextual history from preprocessed_data into list of Q/A dicts

    Args:
        preprocessed_data: Preprocessed data containing contextual_history

    Returns:
        List of dicts with 'question' and 'answer' keys
    """
    contextual_history = preprocessed_data.get("contextual_history", "")

    conversation_context_list = []
    if contextual_history:
        # Parse context to extract Q/A pairs
        # Format: "Q: ... R: ...\nQ: ... R: ..."
        exchanges = contextual_history.split("\n")

        for exchange in exchanges:
            exchange = exchange.strip()
            if not exchange:
                continue

            # Extract Q and R from each line
            if "Q:" in exchange and "R:" in exchange:
                try:
                    q_part = exchange.split("R:")[0].replace("Q:", "").strip()
                    r_part = exchange.split("R:")[1].strip()

                    if q_part and r_part:
                        conversation_context_list.append(
                            {"question": q_part, "answer": r_part}
                        )
                except IndexError:
                    logger.warning(f"Cannot parse exchange: {exchange[:50]}...")
                    continue

        logger.info(
            f"Context parsed: {len(conversation_context_list)} exchanges extracted"
        )

    return conversation_context_list


async def generate_response_with_generator(
    response_generator,
    context_docs: List,
    query: str,
    language: str,
    preprocessed_data: Dict,
) -> str:
    """
    Generate response using generator with conversation history

    Args:
        response_generator: Response generator instance
        context_docs: Context documents retrieved
        query: User's question
        language: Response language
        preprocessed_data: Preprocessed data containing history

    Returns:
        Generated text response
    """
    if not response_generator:
        logger.warning("Response generator not available, returning raw context")
        return format_context_as_fallback(context_docs)

    try:
        conversation_history = preprocessed_data.get("contextual_history", "")

        # Récupérer le domaine détecté depuis metadata
        metadata = preprocessed_data.get("metadata", {})
        validation_details = metadata.get("validation_details", {})
        detected_domain = validation_details.get("detected_domain", None)

        logger.info(
            f"Generating response with history "
            f"(docs={len(context_docs)}, language={language}, "
            f"history={'YES' if conversation_history else 'NO'}, domain={detected_domain})"
        )

        response = await response_generator.generate_response(
            query=query,
            context_docs=context_docs,
            language=language,
            conversation_context=conversation_history,
            detected_domain=detected_domain,
        )

        # Validation qualité de la réponse
        try:
            validator = get_response_validator()
            quality_report = validator.validate_response(
                response=response,
                query=query,
                domain=detected_domain,
                language=language,
                context_docs=context_docs,
            )

            # Logger les issues détectées
            if quality_report.issues:
                logger.warning(
                    f"Qualité réponse: score={quality_report.quality_score:.2f}, "
                    f"issues={len(quality_report.issues)}"
                )
                for issue in quality_report.issues[:3]:  # Top 3 issues
                    logger.warning(
                        f"  - [{issue.severity}] {issue.issue_type}: {issue.description}"
                    )
            else:
                logger.info(
                    f"Qualité réponse: score={quality_report.quality_score:.2f}, aucun problème détecté"
                )

            # Si score trop bas, logger en warning
            if quality_report.quality_score < 0.6:
                logger.warning(
                    f"Score qualité faible ({quality_report.quality_score:.2f}), "
                    f"amélioration recommandée"
                )

        except Exception as val_err:
            logger.error(f"Erreur validation qualité: {val_err}")

        return response

    except Exception as e:
        logger.error(f"Error generating response with history: {e}")
        logger.error(f"Full traceback:\n{traceback.format_exc()}")
        return format_context_as_fallback(context_docs)


def format_context_as_fallback(context_docs: List) -> str:
    """
    Fallback formatting if generator unavailable

    Args:
        context_docs: Context documents

    Returns:
        Formatted text from documents
    """
    if not context_docs:
        return "Aucun document de contexte disponible."

    formatted_parts = []
    for i, doc in enumerate(context_docs[:5], 1):  # Limit to 5 docs
        content = doc.get("content", "") if isinstance(doc, dict) else str(doc)
        formatted_parts.append(f"[Doc {i}] {content[:200]}...")

    return "\n\n".join(formatted_parts)
