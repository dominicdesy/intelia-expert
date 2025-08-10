# app/api/v1/utils/response_generator.py
from __future__ import annotations
from typing import Dict, Any, List

def build_card(headline: str, bullets: List[str] | None = None, footnote: str | None = None) -> Dict[str, Any]:
    return {"headline": headline, "bullets": bullets or [], "footnote": footnote}

def _join_lines(lines: List[str]) -> str:
    return "\n".join([l for l in lines if l])

def _format_numeric_first(payload: Dict[str, Any]) -> str:
    # payload attendu: { "value": "XXX unité", "range": "Y–Z", "conditions": "...", "notes": [...] }
    lines = []
    v = payload.get("value")
    if v:
        lines.append(str(v))
    rng = payload.get("range")
    if rng:
        lines.append(f"Plage: {rng}")
    cond = payload.get("conditions")
    if cond:
        lines.append(cond)
    notes = payload.get("notes") or []
    lines += [f"- {n}" for n in notes]
    return _join_lines(lines)

def _format_procedure(payload: Dict[str, Any]) -> str:
    steps = payload.get("steps") or []
    params = payload.get("params") or []
    lines = []
    if steps:
        lines.append("Procédure:")
        for i, s in enumerate(steps[:8], 1):
            lines.append(f"{i}. {s}")
    if params:
        lines.append("")
        lines.append("Paramètres clés:")
        for p in params[:8]:
            lines.append(f"- {p}")
    return _join_lines(lines)

def _format_rules(payload: Dict[str, Any]) -> str:
    main = payload.get("rule") or "Règle principale non disponible."
    items = payload.get("details") or []
    lines = [f"Règle: {main}"]
    for d in items[:8]:
        lines.append(f"- {d}")
    return _join_lines(lines)

def format_response(content: str | Dict[str, Any]) -> str:
    """
    Tolère soit une chaîne prête, soit un dict structuré {mode:..., payload:{...}}
    """
    if isinstance(content, str):
        return content.strip()
    if not isinstance(content, dict):
        return str(content)

    mode = content.get("mode") or "standard"
    payload = content.get("payload") or {}

    if "numeric" in mode or "numbers" in mode:
        return _format_numeric_first(payload)
    if "procedure" in mode:
        return _format_procedure(payload)
    if "rules" in mode:
        return _format_rules(payload)
    if "table" in mode:
        # fallback texte court compatible
        return _format_numeric_first(payload) or _format_rules(payload) or _format_procedure(payload)

    # standard
    parts = []
    head = payload.get("headline")
    if head:
        parts.append(str(head))
    bullets = payload.get("bullets") or []
    for b in bullets:
        parts.append(f"- {b}")
    foot = payload.get("footnote")
    if foot:
        parts.append(foot)
    return _join_lines(parts)
