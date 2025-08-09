# app/api/v1/utils/response_generator.py
from typing import Optional, List, Dict, Any
from .units import normalize_unit_label

def _normalize_units_text(answer: str) -> str:
    """Nettoie quelques variantes d'unités dans le texte libre."""
    if not answer:
        return answer
    out = answer
    # normalisations fréquentes
    out = out.replace(" m3/h/kg", " m³/h/kg").replace("m3/h/kg", "m³/h/kg")
    out = out.replace("kcal.kg", "kcal/kg").replace("kcalkg", "kcal/kg")
    out = out.replace(" / ", "/")
    return out

def format_response(answer: str, sources: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
    """
    Compat: ancien format { "answer": "...", "sources": [...] }.
    Post-traitement léger sur les unités.
    """
    payload: Dict[str, Any] = {"answer": _normalize_units_text(answer)}
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
    'Card' pour une mise en page compacte.
    - headline ≤ ~120 chars ; bullets: ≤4 items courts
    """
    def _clean(s: str) -> str:
        return _normalize_units_text(s.strip())

    card: Dict[str, Any] = {
        "type": "card",
        "headline": _clean(headline)[:120],
        "bullets": [_clean(b)[:160] for b in bullets if b and b.strip()][:4],
    }
    if footnote:
        card["footnote"] = _clean(footnote)[:180]
    if followups:
        card["followups"] = [_clean(q)[:140] for q in followups if q and q.strip()][:2]
    if sources:
        card["sources"] = sources
    return card
