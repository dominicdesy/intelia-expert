from typing import Optional, List, Dict, Any

def format_response(answer: str, sources: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
    """
    Compat: ancien format { "answer": "...", "sources": [...] }.
    """
    payload: Dict[str, Any] = {"answer": answer}
    if sources:
        payload["sources"] = sources
    return payload

def build_card(
    *,
    headline: str,
    bullets: List[str],
    footnote: Optional[str] = None,
    followups: Optional[List[str]] = None,
    sources: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """
    Nouveau format 'card' pour une belle mise en page côté UI.
    - headline: une phrase très courte (≤ 90 caractères)
    - bullets : 2–4 items courts (≤ 120 caractères chacun)
    - footnote: petite note/disclaimer (facultatif)
    - followups: 0–2 questions de clarification
    - sources: citations abrégées [{source, snippet}]
    """
    card: Dict[str, Any] = {
        "type": "card",
        "headline": headline.strip(),
        "bullets": [b.strip() for b in bullets if b and b.strip()][:4],
    }
    if footnote:
        card["footnote"] = footnote.strip()
    if followups:
        card["followups"] = [q.strip() for q in followups if q and q.strip()][:2]
    if sources:
        card["sources"] = sources
    return card
