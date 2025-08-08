from typing import Optional, List, Dict


def format_response(answer: str, sources: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
    """
    Formats the final response, optionally including sources metadata.
    """
    response: Dict[str, Any] = {"answer": answer}
    if sources:
        response["sources"] = sources
    return response
