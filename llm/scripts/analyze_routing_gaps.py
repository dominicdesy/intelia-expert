# -*- coding: utf-8 -*-
"""
analyze_routing_gaps.py - Analyse des gaps pour atteindre 100% de couverture

Identifie les cas où le routing échoue et propose des solutions
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from retrieval.postgresql.router import QueryRouter


def analyze_routing_gaps():
    """Analyse les gaps actuels du routing"""
    router = QueryRouter()

    # Test cases problématiques (5-8% qui empêchent 100%)
    edge_cases = [
        # Questions contextuelles (multi-turn)
        ("Et pour les femelles?", "CONTEXT_REQUIRED", "metrics"),
        ("Même chose pour le Hubbard?", "CONTEXT_REQUIRED", "metrics"),
        ("À cet âge-là?", "CONTEXT_REQUIRED", "metrics"),
        ("Pour cette race?", "CONTEXT_REQUIRED", "metrics"),

        # Questions ambiguës (unités/métriques implicites)
        ("Performance à 35 jours", "AMBIGUOUS", "metrics"),
        ("Résultats Cobb 500", "AMBIGUOUS", "metrics"),
        ("Données de croissance", "AMBIGUOUS", "metrics"),
        ("Les chiffres", "AMBIGUOUS", "metrics"),

        # Questions nécessitant calculs
        ("Écart entre Ross et Cobb", "CALCULATION", "metrics"),
        ("Différence de FCR", "CALCULATION", "metrics"),
        ("Gain comparé au standard", "CALCULATION", "metrics"),
        ("Combien de plus que la cible?", "CALCULATION", "metrics"),

        # Questions très courtes
        ("Poids?", "TOO_SHORT", "metrics"),
        ("FCR", "TOO_SHORT", "metrics"),
        ("Newcastle", "TOO_SHORT", "knowledge"),
        ("Traitement?", "TOO_SHORT", "knowledge"),

        # Questions complexes multi-critères
        ("Impact nutrition et température sur FCR males Ross 308", "MULTI_CRITERIA", "hybrid"),
        ("Relation densité mortalité selon breed", "MULTI_CRITERIA", "hybrid"),
        ("Performance selon climat et alimentation", "MULTI_CRITERIA", "hybrid"),
    ]

    print("\n" + "="*80)
    print("ANALYSE DES GAPS POUR ATTEINDRE 100% DE COUVERTURE")
    print("="*80 + "\n")

    # Statistiques
    stats = {
        "metrics": 0,
        "knowledge": 0,
        "hybrid": 0
    }

    gaps_by_type = {}
    correct_routing = 0
    total = len(edge_cases)

    for query, gap_type, expected in edge_cases:
        result = router.route_query(query)
        stats[result.value] += 1

        if gap_type not in gaps_by_type:
            gaps_by_type[gap_type] = []

        is_correct = (result.value == expected)
        if is_correct:
            correct_routing += 1

        gaps_by_type[gap_type].append({
            "query": query,
            "routed_to": result.value,
            "expected": expected,
            "correct": is_correct
        })

    # Résultats globaux
    accuracy = (correct_routing / total) * 100
    print(f"📊 PRÉCISION ACTUELLE SUR CAS DIFFICILES: {correct_routing}/{total} ({accuracy:.1f}%)\n")

    print("DISTRIBUTION DES ROUTING:")
    for route_type, count in stats.items():
        pct = (count / total) * 100
        print(f"   {route_type:12} : {count:2}/{total} ({pct:5.1f}%)")

    # Gaps par catégorie
    print("\n" + "="*80)
    print("GAPS PAR CATÉGORIE")
    print("="*80 + "\n")

    for gap_type, queries in gaps_by_type.items():
        correct = sum(1 for q in queries if q["correct"])
        accuracy = (correct / len(queries)) * 100 if queries else 0

        print(f"\n🔴 {gap_type} ({correct}/{len(queries)} correct, {accuracy:.0f}%):")
        for item in queries:
            status = "✅" if item["correct"] else "❌"
            print(f"   {status} \"{item['query']}\" → {item['routed_to']} (expected: {item['expected']})")

    # Recommandations
    print("\n" + "="*80)
    print("ROADMAP VERS 100% DE COUVERTURE")
    print("="*80 + "\n")

    recommendations = {
        "CONTEXT_REQUIRED": {
            "priority": "🔴 CRITIQUE",
            "impact": "+3-4%",
            "solutions": [
                "Créer ContextManager pour stocker dernier contexte (breed, age, sex)",
                "Détecter pronouns/démonstratifs (femelles, lui, ça, cette race)",
                "Résoudre coréférences via contexte conversation",
                "Expandre query: 'Et pour femelles?' → 'Poids femelles Ross 308 35j'"
            ]
        },
        "AMBIGUOUS": {
            "priority": "🟡 MOYEN",
            "impact": "+2-3%",
            "solutions": [
                "Module Clarification: demander précision utilisateur",
                "Enrichissement sémantique via embeddings",
                "Mapper 'performance' → [poids, FCR, gain, mortalité]",
                "LLM expansion pour termes vagues"
            ]
        },
        "CALCULATION": {
            "priority": "🟢 FAIBLE",
            "impact": "+1-2%",
            "solutions": [
                "Ajouter QueryType.CALCULATION",
                "Router vers PostgreSQL + post-processing calculs",
                "Détecter patterns: 'écart', 'différence', 'comparé à', 'de plus'",
                "Extraire entités à comparer (Ross vs Cobb)"
            ]
        },
        "TOO_SHORT": {
            "priority": "🟡 MOYEN",
            "impact": "+1-2%",
            "solutions": [
                "LLM expansion: 'FCR' → 'Quel est le FCR?'",
                "Utiliser contexte conversation pour enrichir",
                "Heuristiques: 'poids?' → METRICS, 'Newcastle' → KNOWLEDGE",
                "Fallback intelligent selon historique"
            ]
        },
        "MULTI_CRITERIA": {
            "priority": "🟢 FAIBLE",
            "impact": "+1%",
            "solutions": [
                "Décomposer en sous-requêtes via LLM",
                "Router chaque critère séparément",
                "Agréger résultats avec orchestration LLM",
                "Toujours utiliser HYBRID pour multi-critères"
            ]
        }
    }

    for gap_type, info in recommendations.items():
        print(f"\n{info['priority']} {gap_type} (Impact: {info['impact']})")
        for i, solution in enumerate(info["solutions"], 1):
            print(f"   {i}. {solution}")

    # Plan d'action
    print("\n" + "="*80)
    print("PLAN D'ACTION PRIORISÉ")
    print("="*80 + "\n")

    action_plan = [
        {
            "phase": "Phase 1 - Quick Wins (Court terme)",
            "tasks": [
                "✅ Enrichir keywords METRICS/KNOWLEDGE (FAIT)",
                "✅ Ajouter LLM fallback Layer 2 (FAIT)",
                "🔲 Implémenter ContextManager pour multi-turn",
                "🔲 Ajouter heuristiques pour questions courtes"
            ],
            "impact": "92% → 96%",
            "effort": "2-3 jours"
        },
        {
            "phase": "Phase 2 - Intelligence Sémantique (Moyen terme)",
            "tasks": [
                "🔲 Module Clarification pour questions ambiguës",
                "🔲 Enrichissement sémantique via embeddings",
                "🔲 LLM expansion pour questions courtes/vagues",
                "🔲 QueryType.CALCULATION avec post-processing"
            ],
            "impact": "96% → 98%",
            "effort": "1-2 semaines"
        },
        {
            "phase": "Phase 3 - Orchestration Avancée (Long terme)",
            "tasks": [
                "🔲 Décomposition multi-critères via LLM",
                "🔲 Graph de connaissances breed-metrics",
                "🔲 Fine-tuning modèle avicole spécifique",
                "🔲 Monitoring & amélioration continue"
            ],
            "impact": "98% → 99.5%+",
            "effort": "1 mois+"
        }
    ]

    for phase_info in action_plan:
        print(f"\n📌 {phase_info['phase']}")
        print(f"   Impact: {phase_info['impact']} | Effort: {phase_info['effort']}")
        for task in phase_info["tasks"]:
            print(f"      {task}")

    # Estimation finale
    print("\n" + "="*80)
    print("ESTIMATION COUVERTURE FINALE")
    print("="*80 + "\n")

    coverage_estimate = """
État actuel (v2.0):
  Layer 1 (keywords):     92-95% ✅
  Layer 2 (LLM fallback): 92-95% ✅

Après Phase 1 (ContextManager + Heuristiques):
  Couverture globale:     96-97% 🎯

Après Phase 2 (Clarification + Sémantique):
  Couverture globale:     98-99% 🚀

Après Phase 3 (Orchestration + Fine-tuning):
  Couverture globale:     99.5%+ 🏆

Note: 100% parfait irréaliste (edge cases infinis)
      → Objectif réaliste: 99%+ avec fallback gracieux
"""
    print(coverage_estimate)

    print("\n💡 RECOMMANDATION IMMÉDIATE:")
    print("   → Implémenter ContextManager (Phase 1) pour passer de 92% à 96%")
    print("   → Coût: ~2-3 jours développement, impact immédiat sur multi-turn\n")


if __name__ == "__main__":
    analyze_routing_gaps()
