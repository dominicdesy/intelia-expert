# app/policy/c
from __future__ import annotations
import re
from typing import Optional

# Mots-clés qui déclenchent une redirection vers un vétérinaire (pas de dosage)
_DRUGS = [
    r"enrofloxacine|enrofloxacin|baytril",
    r"amoxicilline|amoxicillin",
    r"tylosine|tylosin|tylosine\s*injection",
    r"oxytetracycline|tétracycline",
    r"florfenicol|tilmicosin|colistine|colistin",
]
_DOSAGE = r"\b(mg\/kg|mg\/l|ml\/l|dose|dosage|posologie|\d+\s?(?:mg|ml)\/?(?:kg|l))\b"

_DRUG_RX = re.compile("|".join(_DRUGS), re.I)
_DOSAGE_RX = re.compile(_DOSAGE, re.I)


def requires_vet_redirect(text: str) -> Optional[str]:
    """Si question implique prescription/dosage, retourner un message de redirection."""
    if not text:
        return None
    t = text.lower()
    if _DRUG_RX.search(t) or _DOSAGE_RX.search(t):
        return (
            "Pour des raisons réglementaires et de biosécurité, je ne fournis pas de posologies ni d’ordonnances. "
            "Consultez votre vétérinaire agréé (et respectez les délais d’attente avant abattage/collecte). "
            "Je peux toutefois rappeler des bonnes pratiques de prévention et d’hygiène si vous le souhaitez."
        )
    return None