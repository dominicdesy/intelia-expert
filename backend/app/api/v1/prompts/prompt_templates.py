# app/prompts/prompt_templates.py
from __future__ import annotations
from typing import Dict

_TEMPLATES: Dict[str, str] = {
    "facts_only": (
        "Donne la valeur numérique en premier (unité SI), puis la plage et la source [Doc N]. "
        "Aucune digression."
    ),
    "calc": (
        "Présente le résultat calculé (valeur + unité), liste 2 hypothèses et indique comment affiner."
    ),
    "diagnostic_triage": (
        "Pose au maximum 3 questions pour préciser le cas, puis donne 3 causes probables et 3 actions immédiates sûres."
    ),
    
    # 🆕 NOUVEAUX TEMPLATES CHAIN-OF-THOUGHT
    "cot_diagnostic": """Tu es un expert vétérinaire avicole. Utilise un raisonnement étape par étape pour analyser ce problème complexe.

CONTEXTE: {context}
ENTITÉS EXTRAITES: {entities}
QUESTION: {question}

Suis cette structure de raisonnement avec les balises indiquées :

<thinking>
Analyse initiale du problème :
- Quelle est vraiment la question posée ?
- Quels sont les symptômes/signes critiques ?
- Y a-t-il des informations manquantes importantes ?
</thinking>

<factors>
Facteurs pertinents à analyser :
- Facteur 1: [âge/lignée/conditions d'élevage et impact]
- Facteur 2: [environnement/alimentation et influence]  
- Facteur 3: [antécédents/pratiques et corrélation]
</factors>

<analysis>
Analyse étape par étape :
1. [Première étape d'analyse diagnostique]
2. [Deuxième étape - causes probables]
3. [Troisième étape - diagnostic différentiel]
</analysis>

<reasoning>
Raisonnement logique :
- Pourquoi cette situation se produit-elle ?
- Quelles sont les causes les plus probables selon l'âge/lignée ?
- Comment les différents facteurs interagissent-ils ?
</reasoning>

<recommendations>
Recommandations hiérarchisées :
1. URGENCE IMMÉDIATE: [action à prendre dans les 2-4h]
2. COURT TERME: [actions 24-48h]  
3. PRÉVENTION: [mesures préventives long terme]
</recommendations>

<validation>
Vérification de cohérence :
- Ces recommandations sont-elles réalistes pour {entities.get('species', 'cette espèce')} ?
- Y a-t-il des contre-indications selon l'âge/lignée ?
- Quels sont les indicateurs de succès à surveiller ?
</validation>

Réponse finale structurée pour l'utilisateur :""",

    "cot_optimization": """Tu es un expert en optimisation avicole. Analyse cette question d'optimisation avec un raisonnement structuré.

CONTEXTE: {context}
ENTITÉS EXTRAITES: {entities}
QUESTION: {question}

<thinking>
Compréhension de l'objectif d'optimisation :
- Quel est le paramètre principal à optimiser ?
- Quelles sont les contraintes identifiées ?
- Quel est le contexte économique/technique ?
</thinking>

<current_analysis>
Analyse de la situation actuelle :
- Performance actuelle vs standards de référence
- Écarts identifiés et leur magnitude
- Points forts à préserver
</current_analysis>

<optimization_factors>
Facteurs d'optimisation par ordre d'impact :
1. NUTRITION: [impact potentiel et faisabilité]
2. ENVIRONNEMENT: [leviers disponibles et coûts]
3. GÉNÉTIQUE/MANAGEMENT: [changements possibles]
4. ÉCONOMIQUE: [analyse coût/bénéfice]
</optimization_factors>

<strategy>
Stratégie d'optimisation progressive :
1. IMMÉDIAT (0-2 semaines): [actions sans investissement]
2. COURT TERME (1-2 mois): [ajustements techniques]
3. MOYEN TERME (3-6 mois): [optimisations structurelles]
</strategy>

<impact_prediction>
Prédictions d'impact quantifiées :
- Amélioration attendue: [fourchette réaliste]
- Délai de retour sur investissement
- Risques et mesures d'atténuation
</impact_prediction>

Plan d'action optimal pour l'utilisateur :""",

    "cot_multifactor": """Tu es un consultant expert en aviculture. Traite cette question complexe multi-facteurs avec méthodologie structurée.

CONTEXTE: {context}
ENTITÉS EXTRAITES: {entities}
QUESTION: {question}

<problem_decomposition>
Décomposition du problème complexe :
- Sous-problème 1: [identification et priorité]
- Sous-problème 2: [interdépendances]
- Sous-problème 3: [impacts croisés]
</problem_decomposition>

<factor_analysis>
Analyse des facteurs influents :
- Facteurs contrôlables: [liste et degré de contrôle]
- Facteurs externes: [influence et adaptation possible]
- Facteurs critiques: [seuils d'alerte et surveillance]
</factor_analysis>

<interconnections>
Analyse des interconnections :
- Comment les facteurs s'influencent mutuellement ?
- Quels sont les effets en cascade possibles ?
- Où sont les points de levier maximum ?
</interconnections>

<solution_pathway>
Chemin de solution intégré :
1. DIAGNOSTIC: [état des lieux complet]
2. PRIORISATION: [urgence vs impact]
3. PLAN D'ACTION: [séquencement optimal]
4. MONITORING: [indicateurs de suivi]
</solution_pathway>

<risk_mitigation>
Gestion des risques :
- Risques identifiés et probabilité
- Mesures préventives recommandées
- Plans de contingence si dérive
</risk_mitigation>

Solution intégrée pour l'utilisateur :""",

    "cot_economics": """Tu es un expert en économie avicole. Analyse cette question économique avec raisonnement financier structuré.

CONTEXTE: {context}
ENTITÉS EXTRAITES: {entities}
QUESTION: {question}

<economic_context>
Analyse du contexte économique :
- Objectif financier principal identifié
- Contraintes budgétaires et temporelles
- Variables économiques clés à considérer
</economic_context>

<cost_benefit_breakdown>
Décomposition coûts/bénéfices :
- COÛTS: [fixes, variables, cachés]
- REVENUS: [directs, indirects, potentiels]
- MARGES: [calcul et optimisation]
</cost_benefit_breakdown>

<scenario_analysis>
Analyse de scénarios :
1. SCÉNARIO CONSERVATEUR: [hypothèses prudentes]
2. SCÉNARIO RÉALISTE: [conditions normales]
3. SCÉNARIO OPTIMISTE: [conditions favorables]
</scenario_analysis>

<optimization_levers>
Leviers d'optimisation économique :
- Réduction de coûts: [opportunités identifiées]
- Amélioration revenus: [stratégies possibles]
- Efficacité opérationnelle: [gains de productivité]
</optimization_levers>

<financial_recommendation>
Recommandation financière :
- Calcul ROI et délai de retour
- Analyse de sensibilité aux variables clés
- Plan de mise en œuvre financière
</financial_recommendation>

Stratégie économique optimale pour l'utilisateur :"""
}

def get_template(key: str) -> str:
    return _TEMPLATES.get(key, "Réponse concise et structurée.")

# 🆕 NOUVELLES FONCTIONS POUR CHAIN-OF-THOUGHT

def get_cot_template_for_intent(intent: str) -> str:
    """
    Retourne le template CoT approprié selon l'intention détectée
    """
    cot_mapping = {
        "Diagnostics": "cot_diagnostic",
        "HealthDiagnosis": "cot_diagnostic", 
        "OptimizationStrategy": "cot_optimization",
        "Economics": "cot_economics",
        "TroubleshootingMultiple": "cot_multifactor",
        "ProductionAnalysis": "cot_multifactor",
        "MultiFactor": "cot_multifactor"
    }
    
    template_key = cot_mapping.get(intent, "cot_multifactor")  # fallback générique
    return _TEMPLATES.get(template_key, _TEMPLATES["cot_multifactor"])

def build_cot_prompt(question: str, context: str, entities: dict, intent: str) -> str:
    """
    Construit un prompt CoT complet en utilisant le bon template
    """
    template = get_cot_template_for_intent(intent)
    
    return template.format(
        question=question,
        context=context,
        entities=entities
    )

def is_cot_suitable(intent: str, question: str) -> bool:
    """
    Détermine si Chain-of-Thought est approprié pour cette intention/question
    """
    # Intentions complexes nécessitant CoT
    complex_intents = [
        "Diagnostics", "HealthDiagnosis", "OptimizationStrategy", 
        "Economics", "TroubleshootingMultiple", "ProductionAnalysis",
        "MultiFactor"
    ]
    
    # Mots-clés indiquant complexité
    complex_keywords = [
        "optimiser", "améliorer", "problème", "stratégie", "diagnostic",
        "plusieurs", "facteurs", "pourquoi", "comment", "analyse",
        "rentabilité", "efficacité", "recommandation", "causes"
    ]
    
    # Indicateurs de questions multi-étapes
    multi_step_indicators = [
        " et ", " puis ", " ensuite ", "d'abord", "enfin",
        "étapes", "procédure", "protocole", "plan"
    ]
    
    return (
        intent in complex_intents or
        any(kw in question.lower() for kw in complex_keywords) or
        any(indicator in question.lower() for indicator in multi_step_indicators) or
        len(question.split()) > 15  # Questions longues souvent complexes
    )
