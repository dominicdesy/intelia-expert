# -*- coding: utf-8 -*-
"""
analyze_ragas_results.py - Analyse détaillée des résultats RAGAS

Compare les résultats avant/après les corrections et génère un rapport détaillé.
"""

import json
import sys
from pathlib import Path

def load_results(filepath):
    """Charge les résultats RAGAS depuis un fichier JSON"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Erreur chargement {filepath}: {e}")
        return None

def analyze_test_case(test_case, idx):
    """Analyse un cas de test individuel"""
    query = test_case.get('query', 'N/A')

    scores = test_case.get('scores', {})
    context_precision = scores.get('context_precision', 0.0)
    context_recall = scores.get('context_recall', 0.0)
    faithfulness = scores.get('faithfulness', 0.0)
    answer_relevancy = scores.get('answer_relevancy', 0.0)

    # Calculer le score moyen pour ce test
    avg_score = (context_precision + context_recall + faithfulness + answer_relevancy) / 4

    return {
        'index': idx,
        'query': query[:100] + '...' if len(query) > 100 else query,
        'context_precision': context_precision,
        'context_recall': context_recall,
        'faithfulness': faithfulness,
        'answer_relevancy': answer_relevancy,
        'average': avg_score
    }

def print_comparison_table(before_results, after_results):
    """Affiche un tableau de comparaison"""

    print("\n" + "="*100)
    print("📊 COMPARAISON RAGAS - AVANT vs APRÈS CORRECTIONS")
    print("="*100)

    # Scores globaux
    print("\n🎯 SCORES GLOBAUX:")
    print("-" * 100)

    before_scores = before_results.get('scores', {})
    after_scores = after_results.get('scores', {})

    metrics = [
        ('Context Precision', 'context_precision'),
        ('Context Recall', 'context_recall'),
        ('Faithfulness', 'faithfulness'),
        ('Answer Relevancy', 'answer_relevancy'),
        ('Overall Score', 'overall')
    ]

    print(f"{'Metric':<25} {'Avant':<15} {'Après':<15} {'Différence':<15} {'Évolution'}")
    print("-" * 100)

    for metric_name, metric_key in metrics:
        before_val = before_scores.get(metric_key, 0.0)
        after_val = after_scores.get(metric_key, 0.0)
        diff = after_val - before_val

        # Calculer pourcentage d'évolution
        if before_val > 0:
            evolution_pct = (diff / before_val) * 100
        else:
            evolution_pct = 0 if diff == 0 else float('inf')

        # Symbole d'évolution
        if diff > 0:
            symbol = "📈"
        elif diff < 0:
            symbol = "📉"
        else:
            symbol = "➡️"

        before_pct = before_val * 100
        after_pct = after_val * 100
        diff_pct = diff * 100

        print(f"{metric_name:<25} {before_pct:>6.2f}%{'':<8} {after_pct:>6.2f}%{'':<8} {diff_pct:>+6.2f}%{'':<8} {symbol} {evolution_pct:>+6.1f}%")

    print()

def analyze_failures(results, title):
    """Analyse les cas d'échec (score = 0)"""
    print("\n" + "="*100)
    print(f"❌ {title}")
    print("="*100)

    detailed = results.get('detailed_scores', [])

    zero_score_tests = []
    partial_failures = []

    for idx, test_case in enumerate(detailed, 1):
        scores = test_case.get('scores', {})

        # Compter combien de métriques sont à 0
        zero_count = sum(1 for v in scores.values() if v == 0.0)

        if zero_count == 4:
            # Tous les scores à 0
            zero_score_tests.append((idx, test_case))
        elif zero_count > 0:
            # Certains scores à 0
            partial_failures.append((idx, test_case, zero_count))

    print(f"\n🔴 Tests avec tous les scores à 0: {len(zero_score_tests)}")
    for idx, test_case in zero_score_tests[:5]:  # Top 5
        query = test_case.get('query', 'N/A')[:80]
        print(f"   #{idx}: {query}...")

    print(f"\n🟡 Tests avec échecs partiels: {len(partial_failures)}")
    for idx, test_case, zero_count in partial_failures[:5]:  # Top 5
        query = test_case.get('query', 'N/A')[:80]
        scores = test_case.get('scores', {})
        print(f"   #{idx}: {query}... ({zero_count}/4 métriques à 0)")
        for metric, value in scores.items():
            if value == 0.0:
                print(f"      - {metric}: 0.0 ❌")

def analyze_successes(results, title):
    """Analyse les meilleurs cas de test"""
    print("\n" + "="*100)
    print(f"✅ {title}")
    print("="*100)

    detailed = results.get('detailed_scores', [])

    # Calculer score moyen pour chaque test
    test_scores = []
    for idx, test_case in enumerate(detailed, 1):
        scores = test_case.get('scores', {})
        avg_score = sum(scores.values()) / len(scores) if scores else 0
        test_scores.append((idx, test_case, avg_score))

    # Trier par score décroissant
    test_scores.sort(key=lambda x: x[2], reverse=True)

    print(f"\n🏆 Top 5 meilleurs tests:")
    for idx, test_case, avg_score in test_scores[:5]:
        query = test_case.get('query', 'N/A')[:80]
        scores = test_case.get('scores', {})
        print(f"\n   #{idx}: {query}... (score moyen: {avg_score*100:.1f}%)")
        for metric, value in scores.items():
            symbol = "✅" if value > 0.7 else "🟡" if value > 0.3 else "❌"
            print(f"      - {metric}: {value*100:.1f}% {symbol}")

def main():
    """Fonction principale"""

    # Chemins des fichiers
    before_file = Path(__file__).parent.parent / "logs" / "ragas_post_auth_fixes.json"
    after_file = Path(__file__).parent.parent / "logs" / "ragas_post_followup_fixes.json"

    # Vérifier existence
    if not before_file.exists():
        print(f"❌ Fichier introuvable: {before_file}")
        return

    if not after_file.exists():
        print(f"❌ Fichier introuvable: {after_file}")
        return

    # Charger résultats
    print("📂 Chargement des résultats RAGAS...")
    before_results = load_results(before_file)
    after_results = load_results(after_file)

    if not before_results or not after_results:
        print("❌ Impossible de charger les résultats")
        return

    # Afficher comparaison
    print_comparison_table(before_results, after_results)

    # Analyser échecs (après corrections)
    analyze_failures(after_results, "ANALYSE DES ÉCHECS (APRÈS CORRECTIONS)")

    # Analyser succès (après corrections)
    analyze_successes(after_results, "ANALYSE DES SUCCÈS (APRÈS CORRECTIONS)")

    # Résumé final
    print("\n" + "="*100)
    print("📋 RÉSUMÉ FINAL")
    print("="*100)

    before_overall = before_results.get('scores', {}).get('overall', 0.0)
    after_overall = after_results.get('scores', {}).get('overall', 0.0)
    diff = after_overall - before_overall

    print(f"\nScore global AVANT: {before_overall*100:.2f}%")
    print(f"Score global APRÈS: {after_overall*100:.2f}%")
    print(f"Évolution: {diff*100:+.2f}% {'📈' if diff > 0 else '📉' if diff < 0 else '➡️'}")

    # Évaluation
    if after_overall < 0.30:
        print("\n⚠️  STATUT: INSUFFISANT (< 30%)")
        print("   Recommandations:")
        print("   - Améliorer la qualité des documents contextuels")
        print("   - Optimiser la recherche vectorielle")
        print("   - Valider les prompts de génération")
    elif after_overall < 0.70:
        print("\n🟡 STATUT: MODÉRÉ (30-70%)")
        print("   Recommandations:")
        print("   - Affiner la sélection de contexte")
        print("   - Améliorer la fidélité des réponses")
    else:
        print("\n✅ STATUT: EXCELLENT (> 70%)")
        print("   Le système performe bien!")

    print()

if __name__ == "__main__":
    main()
