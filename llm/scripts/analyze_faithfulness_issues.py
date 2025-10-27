"""
Analyse détaillée des problèmes de Faithfulness dans les résultats RAGAS
Version: 1.4.1
Last modified: 2025-10-26
"""
"""
Analyse détaillée des problèmes de Faithfulness dans les résultats RAGAS
Identifie les patterns de hallucination et les problèmes récurrents
"""

import json
import sys

def analyze_faithfulness_issues(json_path: str) -> None:
    """Analyse les résultats RAGAS pour identifier les problèmes de Faithfulness"""

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print("="*80)
    print("ANALYSE DETAILLEE DES PROBLEMES DE FAITHFULNESS")
    print("="*80)
    print()

    # Résumé global
    results = data.get('results', {})
    print("Scores Globaux:")
    print(f"   Overall Score:      {results.get('overall_score', 0)*100:.2f}%")
    print(f"   Faithfulness:       {results.get('faithfulness', 0)*100:.2f}%")
    print(f"   Context Precision:  {results.get('context_precision', 0)*100:.2f}%")
    print(f"   Context Recall:     {results.get('context_recall', 0)*100:.2f}%")
    print(f"   Answer Relevancy:   {results.get('answer_relevancy', 0)*100:.2f}%")
    print()

    # Analyse par question
    test_cases = data.get('test_cases', [])

    print(f"Analyse des {len(test_cases)} Cas de Test:")
    print()

    # Trier par Faithfulness croissant (les pires en premier)
    sorted_cases = sorted(
        test_cases,
        key=lambda x: x.get('scores', {}).get('faithfulness', 1.0)
    )

    # Statistiques
    low_faithfulness = [c for c in test_cases if c.get('scores', {}).get('faithfulness', 1.0) < 0.5]
    medium_faithfulness = [c for c in test_cases if 0.5 <= c.get('scores', {}).get('faithfulness', 1.0) < 0.8]
    high_faithfulness = [c for c in test_cases if c.get('scores', {}).get('faithfulness', 1.0) >= 0.8]

    print(f"   🔴 Faithfulness < 50%:  {len(low_faithfulness)} cas")
    print(f"   🟡 Faithfulness 50-80%: {len(medium_faithfulness)} cas")
    print(f"   🟢 Faithfulness ≥ 80%:  {len(high_faithfulness)} cas")
    print()

    # Analyse détaillée des cas problématiques (Faithfulness < 80%)
    print("="*80)
    print("🔴 CAS PROBLÉMATIQUES (Faithfulness < 80%)")
    print("="*80)
    print()

    problematic_cases = [c for c in sorted_cases if c.get('scores', {}).get('faithfulness', 1.0) < 0.8]

    for i, case in enumerate(problematic_cases, 1):
        scores = case.get('scores', {})
        faithfulness = scores.get('faithfulness', 0.0)

        print(f"{'─'*80}")
        print(f"CAS #{i} - Faithfulness: {faithfulness*100:.1f}%")
        print(f"{'─'*80}")

        # Question
        question = case.get('question', 'N/A')
        print("\n📝 QUESTION:")
        print(f"   {question}")

        # Ground Truth
        ground_truth = case.get('ground_truth', 'N/A')
        print("\n✅ GROUND TRUTH (Réponse Attendue):")
        print(f"   {ground_truth[:300]}{'...' if len(ground_truth) > 300 else ''}")

        # Réponse Générée
        answer = case.get('answer', 'N/A')
        print("\n🤖 RÉPONSE GÉNÉRÉE:")
        print(f"   {answer[:400]}{'...' if len(answer) > 400 else ''}")

        # Contexte utilisé
        contexts = case.get('contexts', [])
        print(f"\n📚 CONTEXTE UTILISÉ ({len(contexts)} documents):")
        for j, ctx in enumerate(contexts[:2], 1):  # Limiter à 2 docs
            print(f"   Doc {j}: {ctx[:200]}{'...' if len(ctx) > 200 else ''}")

        # Scores détaillés
        print("\n📊 SCORES:")
        print(f"   Faithfulness:      {scores.get('faithfulness', 0)*100:.1f}%")
        print(f"   Context Precision: {scores.get('context_precision', 0)*100:.1f}%")
        print(f"   Context Recall:    {scores.get('context_recall', 0)*100:.1f}%")
        print(f"   Answer Relevancy:  {scores.get('answer_relevancy', 0)*100:.1f}%")

        print()

    # Analyse des patterns communs
    print("="*80)
    print("🔍 PATTERNS D'ERREURS IDENTIFIÉS")
    print("="*80)
    print()

    # Pattern 1: Réponses trop génériques
    generic_answers = []
    for case in problematic_cases:
        answer = case.get('answer', '').lower()
        if any(phrase in answer for phrase in [
            "based on general", "in general", "typically", "usually",
            "commonly", "generally speaking", "dans le domaine"
        ]):
            generic_answers.append(case)

    if generic_answers:
        print(f"📌 Pattern 1: Réponses basées sur connaissances générales ({len(generic_answers)} cas)")
        print("   → Le LLM utilise ses connaissances au lieu du contexte fourni")
        print()

    # Pattern 2: Ajout d'informations non présentes dans le contexte
    hallucination_markers = []
    for case in problematic_cases:
        answer = case.get('answer', '').lower()
        contexts_text = ' '.join(case.get('contexts', [])).lower()

        # Chercher des nombres dans la réponse qui ne sont pas dans le contexte
        import re
        answer_numbers = set(re.findall(r'\b\d+(?:\.\d+)?\b', answer))
        context_numbers = set(re.findall(r'\b\d+(?:\.\d+)?\b', contexts_text))

        unique_numbers = answer_numbers - context_numbers
        if len(unique_numbers) > 2:  # Plus de 2 nombres uniques
            hallucination_markers.append({
                'case': case,
                'unique_numbers': unique_numbers
            })

    if hallucination_markers:
        print(f"📌 Pattern 2: Ajout de chiffres non présents dans le contexte ({len(hallucination_markers)} cas)")
        print("   → Hallucinations numériques détectées")
        for item in hallucination_markers[:2]:
            print(f"      Ex: {item['unique_numbers']}")
        print()

    # Pattern 3: Context Recall faible
    low_recall_cases = [c for c in problematic_cases
                       if c.get('scores', {}).get('context_recall', 1.0) < 0.7]

    if low_recall_cases:
        print(f"📌 Pattern 3: Context Recall faible ({len(low_recall_cases)} cas)")
        print("   → Le contexte récupéré ne contient pas toutes les informations nécessaires")
        print()

    # Recommandations
    print("="*80)
    print("💡 RECOMMANDATIONS BASÉES SUR L'ANALYSE")
    print("="*80)
    print()

    if len(generic_answers) > len(problematic_cases) * 0.3:
        print("1. ⚠️  PRIORITÉ HAUTE: Renforcer les prompts pour éviter l'usage de connaissances générales")
        print("   → Ajouter des clauses explicites 'NEVER use general knowledge'")
        print()

    if len(hallucination_markers) > len(problematic_cases) * 0.3:
        print("2. ⚠️  PRIORITÉ HAUTE: Réduire les hallucinations numériques")
        print("   → Baisser la température du LLM (0.1 → 0.05)")
        print("   → Ajouter validation post-génération des chiffres")
        print()

    if len(low_recall_cases) > len(problematic_cases) * 0.3:
        print("3. ⚠️  PRIORITÉ MOYENNE: Améliorer la récupération de contexte")
        print("   → Augmenter encore TOP_K (135 → 150)")
        print("   → Vérifier les filtres de confiance")
        print()

    print("4. 💡 Réduire la température LLM pour réponses plus conservatrices")
    print("5. 💡 Ajouter un système de vérification factuelle post-génération")
    print()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        # Utiliser le fichier le plus récent
        import glob
        json_files = sorted(glob.glob("logs/ragas_evaluation_*.json"), reverse=True)
        if json_files:
            json_path = json_files[0]
            print(f"📁 Utilisation du fichier le plus récent: {json_path}")
            print()
        else:
            print("❌ Aucun fichier de résultats RAGAS trouvé")
            sys.exit(1)
    else:
        json_path = sys.argv[1]

    analyze_faithfulness_issues(json_path)
