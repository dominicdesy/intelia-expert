# app/api/v1/utils/response_generator.py
from typing import Optional, List, Dict, Any

# Optionnel : si ce module est importé avec __all__, on expose les fonctions publiques.
__all__ = ["format_response", "build_card"]

# --- Helpers -----------------------------------------------------------------

def _normalize_units_text(answer: str) -> str:
    """
    Nettoie quelques variantes d'unités dans le texte libre pour uniformiser l'affichage.
    Exemple : 'm3/h/kg' -> 'm³/h/kg', 'kcal.kg' -> 'kcal/kg', etc.
    """
    if not answer:
        return answer
    out = answer
    out = out.replace(" m3/h/kg", " m³/h/kg").replace("m3/h/kg", "m³/h/kg")
    out = out.replace("kcal.kg", "kcal/kg").replace("kcalkg", "kcal/kg")
    out = out.replace(" / ", "/")
    return out

# --- Public API ---------------------------------------------------------------

def format_response(
    answer: str,
    sources: Optional[List[Dict[str, str]]] = None
) -> Dict[str, Any]:
    """
    Formate une réponse textuelle.

    - Compatibilité conservée avec l'ancien format: {"answer": "...", "sources": [...]}
    - Ajoute 'full_text' pour un affichage direct par le frontend (sans voir {'answer': ...})
    - Laisse passer 'sources' si fourni, sinon l'omet (pas de clé vide).

    Parameters
    ----------
    answer : str
        Texte de la réponse (Markdown autorisé).
    sources : Optional[List[Dict[str, str]]]
        Métadonnées de sources (ex: [{"title": "...", "url": "..."}]).

    Returns
    -------
    Dict[str, Any]
        Payload prêt à l'API, ex:
        {
          "type": "text",
          "answer": "...",
          "full_text": "...",
          "sources": [...]
        }
    """
    text = _normalize_units_text(answer)

    payload: Dict[str, Any] = {
        "type": "text",     # permet au frontend d'identifier un bloc de texte standard
        "answer": text,     # rétro-compat
        "full_text": text,  # à utiliser côté UI pour l'affichage standard
    }
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
    Construit un objet 'card' pour une mise en page compacte dans l'UI.
    - headline ≤ ~120 chars
    - bullets : ≤ 4 éléments, courts
    - followups : ≤ 2 propositions de relance

    Returns un dict de forme:
    {
      "type": "card",
      "headline": "...",
      "bullets": ["...", "..."],
      "footnote": "...",
      "followups": ["...", "..."],
      "sources": [...]
    }
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
