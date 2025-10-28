# -*- coding: utf-8 -*-
"""
golden_dataset_intelia.py - Dataset de test pour Intelia Expert
Version: 1.4.1
Last modified: 2025-10-26
"""
"""
golden_dataset_intelia.py - Dataset de test pour Intelia Expert

Questions de test avec ground truth pour évaluation RAGAS.
Maintenu et enrichi progressivement.
"""

from typing import List, Dict, Any


def get_intelia_test_dataset() -> List[Dict[str, Any]]:
    """
    Dataset de test pour Intelia Expert.

    Chaque cas contient:
    - question: Question posée par l'utilisateur
    - ground_truth: Réponse attendue (validée manuellement)
    - category: Catégorie de la question
    - expected_behavior: Comportement attendu du système
    - contexts: Rempli dynamiquement lors de l'évaluation
    - answer: Rempli par le RAG lors de l'évaluation
    """

    return [
        # =================================================================
        # 1. CALCULS COMPLEXES
        # =================================================================
        {
            "question": "Je suis rendu au 18e jour de production et j'élève du Ross 308 mâle. De combien de moulées est-ce que j'aurai besoin pour atteindre un poids cible de 2,4 kg ?",
            "ground_truth": "Pour atteindre un poids cible de 2400g au jour 35, vous aurez besoin de 2.16 kg d'aliment par poulet entre le jour 18 et le jour 35.",
            "category": "calculation",
            "lang": "fr",
            "difficulty": "easy",
            "expected_behavior": "Doit utiliser reverse lookup (2400g → jour 35) puis calculer consommation cumulée avec interpolation proportionnelle",
            "contexts": [],
            "answer": "",
        },
        # =================================================================
        # 2. MALADIES - STATISTIQUES
        # =================================================================
        {
            "question": "Quelle maladie frappe le plus souvent les élevages de broiler ?",
            "ground_truth": "La coccidiose est la maladie la plus fréquente dans les élevages de broilers, suivie par les infections respiratoires (bronchite infectieuse, maladie de Newcastle) et les maladies bactériennes comme la colibacillose.",
            "category": "disease_statistics",
            "lang": "fr",
            "difficulty": "easy",
            "expected_behavior": "Doit fournir réponse basée sur documentation maladies courantes",
            "contexts": [],
            "answer": "",
        },
        # =================================================================
        # 3. MALADIES - PRÉVENTION
        # =================================================================
        {
            "question": "Comment prévenir la coccidiose ?",
            "ground_truth": "La prévention de la coccidiose inclut: (1) Utilisation de coccidiostatiques dans l'aliment, (2) Vaccination par spray ou eau de boisson (vaccins vivants atténués), (3) Biosécurité stricte (nettoyage et désinfection), (4) Gestion de la litière (éviter humidité excessive), (5) Densité appropriée, (6) Programme de rotation des anticoccidiens pour éviter résistance.",
            "category": "disease_prevention",
            "lang": "fr",
            "difficulty": "medium",
            "expected_behavior": "Doit récupérer documentation sur prévention coccidiose",
            "contexts": [],
            "answer": "",
        },
        # =================================================================
        # 4. OUT-OF-DOMAIN (DOIT ÊTRE REJETÉ)
        # =================================================================
        {
            "question": "Qu'est-ce que la cryptomonnaie ?",
            "ground_truth": "Je suis désolé, mais cette question ne concerne pas la production avicole. Je suis spécialisé dans les questions relatives aux poulets de chair, pondeuses, nutrition, santé et gestion d'élevage. Puis-je vous aider avec une question sur l'aviculture ?",
            "category": "out_of_domain",
            "lang": "fr",
            "difficulty": "easy",
            "expected_behavior": "Doit être détecté comme hors-domaine et poliment refusé",
            "exclude_from_main": True,
            "contexts": [],
            "answer": "",
        },
        # =================================================================
        # 5. MALADIES - SYMPTÔMES
        # =================================================================
        {
            "question": "Quels sont les symptômes de Newcastle ?",
            "ground_truth": "Les symptômes de la maladie de Newcastle incluent: détresse respiratoire (toux, éternuements, respiration difficile), diarrhée verdâtre, signes nerveux (torticolis, paralysie des ailes et pattes, tremblements, mouvements circulaires), chute brutale de la ponte chez les pondeuses, œufs déformés ou sans coquille, mortalité élevée (jusqu'à 100% en souches virulentes).",
            "category": "disease_symptoms",
            "lang": "fr",
            "difficulty": "easy",
            "expected_behavior": "Doit récupérer documentation complète sur Newcastle",
            "contexts": [],
            "answer": "",
        },
        # =================================================================
        # 6. MÉTRIQUES - QUESTION INCOMPLÈTE (CLARIFICATION NÉCESSAIRE)
        # =================================================================
        {
            "question": "Quel est le poids d'un Ross 308 mâle ?",
            "ground_truth": "Pour vous donner le poids précis d'un Ross 308 mâle, j'ai besoin de connaître l'âge en jours. Par exemple: à 21 jours, le poids est de 966g; à 28 jours, 1550g; à 35 jours, 2441g; à 42 jours, 3131g. À quel âge souhaitez-vous connaître le poids ?",
            "category": "clarification_needed",
            "lang": "fr",
            "difficulty": "medium",
            "expected_behavior": "Doit demander clarification pour l'âge, idéalement donner exemples",
            "contexts": [],
            "answer": "",
        },
        # =================================================================
        # 7. MULTI-LANGUE - ANGLAIS
        # =================================================================
        {
            "question": "What is the weight of a Cobb 500 male?",
            "ground_truth": "To provide the precise weight of a Cobb 500 male, I need to know the age in days. For example: at 21 days, the weight is approximately 950g; at 28 days, 1520g; at 35 days, 2380g; at 42 days, 3050g. At what age would you like to know the weight?",
            "category": "multilingual_english",
            "lang": "fr",
            "difficulty": "easy",
            "expected_behavior": "Doit détecter anglais et répondre en anglais avec demande de clarification",
            "contexts": [],
            "answer": "",
        },
        # =================================================================
        # 8. QUESTION TROP VAGUE
        # =================================================================
        {
            "question": "Quel est le poids d'un poulet ?",
            "ground_truth": "Le poids d'un poulet varie selon la souche (Ross 308, Cobb 500, etc.), le sexe (mâle, femelle, mixte), et surtout l'âge. Pourriez-vous préciser: (1) Quelle souche de poulet ? (2) Quel sexe ? (3) À quel âge en jours ? Par exemple, un Ross 308 mâle à 35 jours pèse environ 2441g.",
            "category": "too_vague",
            "lang": "fr",
            "difficulty": "easy",
            "expected_behavior": "Doit demander clarifications multiples (breed, sex, age)",
            "contexts": [],
            "answer": "",
        },
        # =================================================================
        # 9. COMPARATIF - DEUX SOUCHES
        # =================================================================
        {
            "question": "Compare le poids de Ross 308 vs Cobb 500 à 35 jours",
            "ground_truth": "À 35 jours pour les mâles: Ross 308 atteint 2441g tandis que Cobb 500 atteint 2380g, soit une différence de 61g en faveur de Ross 308 (+2.6%). Pour le FCR à 35 jours: Ross 308 a un FCR de 1.390 et Cobb 500 de 1.410, soit une différence de 0.020 en faveur de Ross 308 (meilleure conversion alimentaire).",
            "category": "comparative",
            "lang": "fr",
            "difficulty": "medium",
            "expected_behavior": "Doit comparer poids ET FCR, donner différences absolues et relatives",
            "contexts": [],
            "answer": "",
        },
        # =================================================================
        # 10. MÉTRIQUES SIMPLES - FCR
        # =================================================================
        {
            "question": "Quel est le FCR d'un Ross 308 mâle de 21 jours ?",
            "ground_truth": "Le FCR (Feed Conversion Ratio) d'un Ross 308 mâle à 21 jours est de 1.141.",
            "category": "metric_simple",
            "lang": "fr",
            "difficulty": "medium",
            "expected_behavior": "Doit récupérer valeur exacte depuis PostgreSQL",
            "contexts": [],
            "answer": "",
        },
        # =================================================================
        # 11. MULTI-LANGUE - THAÏ (HORS SCOPE)
        # =================================================================
        {
            "question": "น้ำหนักของ Ross 308 อายุ 35 วัน",
            "ground_truth": "Je suis désolé, mais je ne peux traiter que les questions en français ou en anglais. Pourriez-vous reformuler votre question dans l'une de ces langues ? (Note: This question asks about Ross 308 weight at 35 days in Thai)",
            "category": "unsupported_language",
            "lang": "fr",
            "difficulty": "easy",
            "expected_behavior": "Doit détecter langue non supportée et demander traduction FR/EN",
            "contexts": [],
            "answer": "",
        },
        # =================================================================
        # 12. CALCUL TROUPEAU
        # =================================================================
        {
            "question": "Combien de kg d'aliment pour 10.000 Ross 308 du jour 0 au jour 42 ?",
            "ground_truth": "Pour élever 10.000 Ross 308 de 0 à 42 jours, il faut environ 52.000-54.000 kg d'aliment (poids moyen ~3.1 kg × FCR ~1.68 × 10.000 oiseaux, ajusté pour mortalité ~3%).",
            "category": "flock_calculation",
            "lang": "fr",
            "difficulty": "hard",
            "expected_behavior": "Doit calculer: poids final × FCR × nombre d'oiseaux × (1 - mortalité)",
            "contexts": [],
            "answer": "",
        },
        # =================================================================
        # 13. REVERSE LOOKUP - POIDS CIBLE
        # =================================================================
        {
            "question": "À quel âge Ross 308 mâle atteint-il 3 kg ?",
            "ground_truth": "Ross 308 mâle atteint 3000g (3 kg) entre le jour 41 et 42. Plus précisément, au jour 42, le poids est de 3131g.",
            "category": "reverse_lookup",
            "lang": "fr",
            "difficulty": "hard",
            "expected_behavior": "Doit utiliser reverse_lookup pour trouver âge correspondant à 3000g",
            "contexts": [],
            "answer": "",
        },
        # =================================================================
        # 14. PROJECTION DE CROISSANCE
        # =================================================================
        {
            "question": "Quel sera le poids à 42j si je suis à 1.2kg à 28j ?",
            "ground_truth": "Si votre troupeau Ross 308 pèse 1200g à 28 jours au lieu de 1550g attendu, il y a un retard significatif de 350g (23%). En projetant avec le taux de croissance standard, le poids à 42j serait d'environ 2400-2500g au lieu des 3131g attendus. Il est important d'identifier et corriger les causes du retard (nutrition, santé, environnement).",
            "category": "projection_diagnostic",
            "lang": "fr",
            "difficulty": "hard",
            "expected_behavior": "Doit détecter sous-performance, projeter avec ajustement, alerter sur retard",
            "contexts": [],
            "answer": "",
        },
        # =================================================================
        # 15. DIAGNOSTIC - RETARD DE CROISSANCE
        # =================================================================
        {
            "question": "Mon troupeau Ross 308 à 28j pèse 1300g au lieu de 1550g, c'est grave ?",
            "ground_truth": "Oui, un retard de 250g (16%) à 28 jours est significatif. Les causes possibles incluent: (1) Qualité ou quantité insuffisante d'aliment, (2) Température inadéquate (stress thermique ou froid), (3) Maladies subcliniques (coccidiose, entérite), (4) Densité excessive, (5) Qualité de l'eau, (6) Mauvaise ventilation. Il faut investiguer rapidement pour corriger le problème.",
            "category": "diagnostic_underperformance",
            "lang": "fr",
            "difficulty": "hard",
            "expected_behavior": "Doit calculer écart %, évaluer gravité, lister causes possibles",
            "contexts": [],
            "answer": "",
        },
        # =================================================================
        # 16. DIAGNOSTIC - FCR ÉLEVÉ
        # =================================================================
        {
            "question": "Mon FCR à 35j est de 1.65 au lieu de 1.39, quelles sont les causes ?",
            "ground_truth": "Un FCR de 1.65 au lieu de 1.39 à 35 jours indique une surconsommation d'aliment ou une sous-performance de croissance (+19% vs objectif). Causes possibles: (1) Qualité nutritionnelle de l'aliment (énergie, digestibilité), (2) Gaspillage d'aliment (mangeoires mal réglées, abreuvoirs qui fuient), (3) Maladies affectant l'absorption (coccidiose, entérite), (4) Température inadéquate (augmente les besoins énergétiques), (5) Stress chronique, (6) Souche inadaptée aux conditions.",
            "category": "diagnostic_fcr",
            "lang": "fr",
            "difficulty": "hard",
            "expected_behavior": "Doit calculer écart FCR, identifier impact économique, lister causes",
            "contexts": [],
            "answer": "",
        },
        # =================================================================
        # 17. NUTRITION - PROTÉINE STARTER (COBB 500)
        # =================================================================
        {
            "question": "Quel taux de protéine dans l'aliment starter pour Cobb 500 ?",
            "ground_truth": "Le taux de protéine recommandé dans l'aliment starter pour Cobb 500 (0-10 jours) est de 22-23% de protéine brute, avec une énergie métabolisable de 2950-3000 kcal/kg.",
            "category": "nutrition_specification",
            "lang": "fr",
            "difficulty": "hard",
            "expected_behavior": "Doit récupérer spécifications nutritionnelles Cobb 500 starter",
            "contexts": [],
            "answer": "",
        },
        # =================================================================
        # 18. NUTRITION - DIFFÉRENCE PHASES
        # =================================================================
        {
            "question": "Quelle est la différence entre aliment starter et grower ?",
            "ground_truth": "L'aliment starter (0-10j) a une protéine plus élevée (22-23%) et énergie modérée (2950-3000 kcal/kg) pour soutenir la croissance rapide initiale. L'aliment grower (11-24j) a une protéine réduite (20-21%) et énergie plus élevée (3100-3200 kcal/kg) pour optimiser le gain de poids. Le starter utilise aussi des ingrédients plus digestibles et des granules plus petits.",
            "category": "nutrition_concept",
            "lang": "fr",
            "difficulty": "medium",
            "expected_behavior": "Doit expliquer différences composition et objectifs nutritionnels",
            "contexts": [],
            "answer": "",
        },
        # =================================================================
        # 19. ENVIRONNEMENT - TEMPÉRATURE DÉMARRAGE
        # =================================================================
        {
            "question": "Quelle température pour des poussins Ross 308 au jour 1 ?",
            "ground_truth": "La température ambiante optimale pour les poussins Ross 308 au jour 1 est de 32-34°C, avec une température sous éleveuse (radiant) de 40-42°C. L'humidité doit être maintenue à 60-70%.",
            "category": "environment_temperature",
            "lang": "fr",
            "difficulty": "medium",
            "expected_behavior": "Doit fournir température ambiante ET sous éleveuse, plus humidité",
            "contexts": [],
            "answer": "",
        },
        # =================================================================
        # 20. DIAGNOSTIC - STRESS THERMIQUE
        # =================================================================
        {
            "question": "Mon bâtiment est à 35°C au jour 21, est-ce trop chaud ?",
            "ground_truth": "Oui, 35°C à 21 jours est beaucoup trop chaud. La température recommandée à 21 jours est de 21-23°C. À 35°C, les poulets sont en stress thermique sévère: réduction de consommation d'aliment, halètement, mortalité possible. Il faut immédiatement augmenter la ventilation, vérifier les systèmes de refroidissement (pad cooling, brumisation), et assurer accès à eau fraîche abondante.",
            "category": "diagnostic_heat_stress",
            "lang": "fr",
            "difficulty": "medium",
            "expected_behavior": "Doit comparer avec température cible, évaluer gravité, donner actions correctives urgentes",
            "contexts": [],
            "answer": "",
        },
        # =================================================================
        # 21. MULTI-MÉTRIQUES
        # =================================================================
        {
            "question": "Donne-moi poids, FCR et mortalité pour Ross 308 mâle à 28 jours",
            "ground_truth": "Ross 308 mâle à 28 jours: Poids = 1550g, FCR = 1.277, Mortalité cumulée = 2.0-2.5% (selon conditions d'élevage).",
            "category": "multi_metric",
            "lang": "fr",
            "difficulty": "medium",
            "expected_behavior": "Doit extraire 3 métriques différentes simultanément",
            "contexts": [],
            "answer": "",
        },
        # =================================================================
        # 22. COMPARATIF MULTI-ÂGES
        # =================================================================
        {
            "question": "Compare Ross 308 et Cobb 500 à 21, 28 et 35 jours",
            "ground_truth": "Comparaison Ross 308 vs Cobb 500 mâles:\n\nJour 21: Ross 308 = 966g, Cobb 500 = 950g (différence +16g)\nJour 28: Ross 308 = 1550g, Cobb 500 = 1520g (différence +30g)\nJour 35: Ross 308 = 2441g, Cobb 500 = 2380g (différence +61g)\n\nRoss 308 maintient un avantage de poids croissant avec l'âge. Les FCR sont similaires avec léger avantage Ross 308 (1.390 vs 1.410 à 35j).",
            "category": "comparative_multi_age",
            "lang": "fr",
            "difficulty": "hard",
            "expected_behavior": "Doit comparer 3 âges × 2 souches, calculer différences, identifier tendances",
            "contexts": [],
            "answer": "",
        },
        # =================================================================
        # 23. QUESTION SUBJECTIVE
        # =================================================================
        {
            "question": "Quel est le meilleur: Ross 308 ou Cobb 500 ?",
            "ground_truth": "Les deux souches sont excellentes, le choix dépend de vos objectifs et conditions:\n\nRoss 308: Léger avantage en poids vif (+2-3%) et FCR légèrement meilleur, robustesse, adapté aux marchés demandant gros calibres.\n\nCobb 500: Rendement carcasse légèrement supérieur, uniformité excellente, très polyvalent.\n\nLe 'meilleur' dépend de: (1) Marché cible (poids abattage), (2) Prix aliment local, (3) Conditions climatiques, (4) Exigences rendement vs poids vif. Les deux offrent performances similaires dans des conditions optimales.",
            "category": "subjective_comparison",
            "lang": "fr",
            "difficulty": "subjective",
            "expected_behavior": "Doit éviter réponse absolue, présenter avantages de chaque souche, contextualiser",
            "contexts": [],
            "answer": "",
        },
        # =================================================================
        # 24. VALIDATION - ÂGE HORS LIMITES
        # =================================================================
        {
            "question": "Poids Ross 308 jour 500",
            "ground_truth": "L'âge de 500 jours est hors des limites pour un broiler Ross 308, qui est élevé pour la viande et généralement abattu entre 35-56 jours. Les données de performance Ross 308 couvrent la période 0-63 jours. Si vous élevez des reproducteurs Ross 308, les données sont différentes. Pourriez-vous préciser votre besoin ?",
            "category": "validation_age_limit",
            "lang": "fr",
            "difficulty": "hard",
            "expected_behavior": "Doit détecter âge invalide pour broiler, expliquer limites, demander clarification",
            "contexts": [],
            "answer": "",
        },
        # =================================================================
        # 25. CONVERSATIONNEL - CONTINUITÉ SIMPLE
        # =================================================================
        {
            "question": "Quel est le poids Ross 308 mâle à 21 jours ?",
            "ground_truth": "Le poids d'un Ross 308 mâle à 21 jours est de 966 grammes.",
            "category": "conversational_turn1",
            "lang": "fr",
            "difficulty": "easy",
            "expected_behavior": "Réponse directe, mémoriser contexte (Ross 308 mâle)",
            "contexts": [],
            "answer": "",
            "follow_up_question": "Et à 28 jours ?",
            "follow_up_ground_truth": "À 28 jours, le poids d'un Ross 308 mâle est de 1550 grammes (gain de 584g entre jour 21 et 28).",
        },
        # =================================================================
        # 26. CONVERSATIONNEL - FOLLOW-UP (TOUR 2)
        # =================================================================
        {
            "question": "Et à 28 jours ?",
            "ground_truth": "À 28 jours, le poids d'un Ross 308 mâle est de 1550 grammes (gain de 584g entre jour 21 et 28).",
            "category": "conversational_turn2",
            "lang": "fr",
            "difficulty": "easy",
            "expected_behavior": "Doit utiliser contexte précédent (Ross 308 mâle) pour répondre",
            "contexts": [],
            "answer": "",
            "requires_previous_context": True,
            "context_from_question": "Quel est le poids Ross 308 mâle à 21 jours ?",
        },
        # =================================================================
        # 27. CONVERSATIONNEL - COMPARATIF TOUR 1
        # =================================================================
        {
            "question": "Compare Ross 308 et Cobb 500 à 35j",
            "ground_truth": "À 35 jours pour les mâles: Ross 308 atteint 2441g tandis que Cobb 500 atteint 2380g, soit une différence de 61g en faveur de Ross 308 (+2.6%). Pour le FCR: Ross 308 = 1.390, Cobb 500 = 1.410, différence de 0.020 en faveur de Ross 308.",
            "category": "conversational_comparative_turn1",
            "lang": "fr",
            "difficulty": "medium",
            "expected_behavior": "Réponse comparative complète, mémoriser contexte comparaison",
            "contexts": [],
            "answer": "",
            "follow_up_question": "Lequel consomme le plus d'aliment ?",
            "follow_up_ground_truth": "À 35 jours, Ross 308 mâle consomme légèrement plus d'aliment en valeur absolue (3394g vs 3352g pour Cobb 500), soit +42g. Cependant, grâce à son meilleur FCR (1.390 vs 1.410), Ross 308 convertit cet aliment plus efficacement en poids vif.",
        },
        # =================================================================
        # 28. CONVERSATIONNEL - FOLLOW-UP COMPARATIF (TOUR 2)
        # =================================================================
        {
            "question": "Lequel consomme le plus d'aliment ?",
            "ground_truth": "À 35 jours, Ross 308 mâle consomme légèrement plus d'aliment en valeur absolue (3394g vs 3352g pour Cobb 500), soit +42g. Cependant, grâce à son meilleur FCR (1.390 vs 1.410), Ross 308 convertit cet aliment plus efficacement en poids vif.",
            "category": "conversational_comparative_turn2",
            "lang": "fr",
            "difficulty": "easy",
            "expected_behavior": "Doit utiliser contexte comparaison Ross 308 vs Cobb 500 à 35j",
            "contexts": [],
            "answer": "",
            "requires_previous_context": True,
            "context_from_question": "Compare Ross 308 et Cobb 500 à 35j",
        },
        # =================================================================
        # PHASE 3 TEST CASES (29-38)
        # =================================================================
        # =================================================================
        # 29. QUERY DECOMPOSER - MULTI-FACTOR (ET)
        # =================================================================
        {
            "question": "Impact de la température et densité sur le poids Ross 308 mâle à 35 jours",
            "ground_truth": """À 35 jours, Ross 308 mâle atteint 2441g dans conditions optimales.

Impact température:
- Température optimale: 21-23°C maintient les performances maximales
- Température élevée (>28°C): réduit le poids de 8-12% (stress thermique, baisse de consommation)
- Température froide (<18°C): réduit le poids de 5-8% (augmentation des besoins énergétiques)

Impact densité:
- Densité optimale: 10-12 oiseaux/m² permet d'atteindre les standards
- Densité excessive (>15 oiseaux/m²): réduit le poids de 5-10% (compétition pour mangeoires, stress, uniformité réduite)
- Densité faible (<8 oiseaux/m²): peut légèrement améliorer performances individuelles mais réduit rentabilité

Les deux facteurs peuvent avoir des effets cumulatifs négatifs si mal gérés simultanément.""",
            "category": "phase3_query_decomposer",
            "lang": "fr",
            "difficulty": "medium",
            "expected_behavior": "Doit détecter complexité (2 facteurs avec 'et'), décomposer en 2 sous-requêtes (température, densité), exécuter chaque sous-requête indépendamment, puis agréger avec stratégie 'combine'",
            "expected_query_type": "HYBRID",
            "expected_complexity": "complex",
            "expected_decomposition": True,
            "sub_queries_expected": 2,
            "aggregation_strategy": "combine",
            "contexts": [],
            "answer": "",
        },
        # =================================================================
        # 30. QUERY DECOMPOSER - MULTI-FACTOR (COMMA)
        # =================================================================
        {
            "question": "Effet de la nutrition, ventilation et éclairage sur la mortalité Ross 308",
            "ground_truth": """La mortalité Ross 308 est influencée par plusieurs facteurs:

Nutrition:
- Déficiences nutritionnelles (protéines, vitamines): augmentent mortalité de 2-5%
- Qualité aliment (fraîcheur, mycotoxines): peut doubler la mortalité
- Programme alimentaire inadapté: augmente mortalité de 1-3%

Ventilation:
- Ventilation insuffisante: augmente mortalité de 3-8% (maladies respiratoires, ammoniaque)
- Ventilation excessive: stress thermique, augmente mortalité de 1-3%
- Renouvellement d'air optimal: maintient mortalité <3-4%

Éclairage:
- Programme lumineux inadapté: augmente mortalité de 1-2%
- Intensité excessive: stress, picage, augmente mortalité
- Photopériode optimale (16-18h): favorise croissance et réduit mortalité

Mortalité cumulée cible à 35j: 2.0-2.5% en conditions optimales.""",
            "category": "phase3_query_decomposer",
            "lang": "fr",
            "difficulty": "medium",
            "expected_behavior": "Doit détecter 3+ facteurs séparés par virgules, décomposer en 3 sous-requêtes, agréger avec stratégie 'combine' pour lister chaque impact séparément",
            "expected_query_type": "HYBRID",
            "expected_complexity": "complex",
            "expected_decomposition": True,
            "sub_queries_expected": 3,
            "aggregation_strategy": "combine",
            "contexts": [],
            "answer": "",
        },
        # =================================================================
        # 31. QUERY DECOMPOSER - COMPARE STRATEGY
        # =================================================================
        {
            "question": "Comparer l'impact de la nutrition versus la température sur le FCR Ross 308",
            "ground_truth": """Comparaison des impacts nutrition vs température sur FCR Ross 308:

Impact Nutrition (plus important):
- Formulation inadéquate: peut dégrader FCR de 0.10-0.20 points (ex: 1.39 → 1.49-1.59)
- Qualité des ingrédients: impact de 0.05-0.15 points
- Forme physique (granulés vs farine): impact de 0.03-0.08 points
Impact moyen: 10-15% de dégradation possible

Impact Température (significatif mais moindre):
- Stress thermique (>28°C): dégrade FCR de 0.05-0.12 points (baisse de consommation, halètement)
- Température sous-optimale (froid): dégrade FCR de 0.03-0.08 points (besoins énergétiques accrus)
Impact moyen: 5-10% de dégradation possible

Conclusion: La nutrition a un impact 1.5-2x plus important que la température sur le FCR. Cependant, une température extrême peut complètement annuler les bénéfices d'une nutrition optimale.""",
            "category": "phase3_query_decomposer",
            "lang": "fr",
            "difficulty": "medium",
            "expected_behavior": "Doit détecter mot-clé 'comparer/versus', décomposer en 2 sous-requêtes (nutrition, température), puis agréger avec stratégie 'compare' pour montrer différences/similitudes",
            "expected_query_type": "HYBRID",
            "expected_complexity": "complex",
            "expected_decomposition": True,
            "sub_queries_expected": 2,
            "aggregation_strategy": "compare",
            "contexts": [],
            "answer": "",
        },
        # =================================================================
        # 32. ENHANCED CLARIFICATION - NUTRITION AMBIGUITY
        # =================================================================
        {
            "question": "Quelle formule d'aliment donner à mes poulets?",
            "ground_truth": "Pour recommander la formule d'aliment appropriée, j'ai besoin de précisions:\n\n1. **Âge ou phase de production**: \n   - Starter (0-10 jours): 22-23% protéine, 2950-3000 kcal/kg\n   - Grower (11-24 jours): 20-21% protéine, 3100-3200 kcal/kg\n   - Finisher (25+ jours): 18-19% protéine, 3200-3300 kcal/kg\n\n2. **Race**: Ross 308, Cobb 500, autre?\n\n3. **Objectif**: Poids maximum, FCR optimal, ou coût minimal?\n\nPouvez-vous préciser ces informations pour que je vous donne la formule exacte adaptée à votre situation?",
            "category": "phase3_enhanced_clarification",
            "lang": "fr",
            "difficulty": "medium",
            "expected_behavior": "Doit détecter ambiguïté type 'nutrition_ambiguity' (pas d'âge/phase spécifié), demander clarifications avec exemples concrets des différentes phases",
            "expected_clarification": True,
            "ambiguity_type": "nutrition_ambiguity",
            "missing_fields": ["age", "production_phase"],
            "contexts": [],
            "answer": "",
        },
        # =================================================================
        # 33. ENHANCED CLARIFICATION - HEALTH SYMPTOM VAGUE
        # =================================================================
        {
            "question": "Mes poulets sont malades depuis 3 jours",
            "ground_truth": "Pour vous aider à identifier le problème et vous conseiller, j'ai besoin de plus d'informations:\n\n1. **Symptômes observés**: \n   - Respiratoires? (toux, éternuements, respiration difficile)\n   - Digestifs? (diarrhée, couleur des fientes)\n   - Nerveux? (tremblements, paralysie, torticolis)\n   - Baisse de consommation d'aliment ou d'eau?\n\n2. **Âge des poulets**: en jours?\n\n3. **Race**: Ross 308, Cobb 500, autre?\n\n4. **Mortalité**: Combien de pertes?\n\n5. **Statut vaccinal**: Protocole de vaccination suivi?\n\nCes informations me permettront de vous orienter vers un diagnostic et des actions correctives appropriées.",
            "category": "phase3_enhanced_clarification",
            "lang": "fr",
            "difficulty": "medium",
            "expected_behavior": "Doit détecter ambiguïté type 'health_symptom_vague' (symptômes non spécifiés), demander détails sur symptômes observés, âge, race, mortalité",
            "expected_clarification": True,
            "ambiguity_type": "health_symptom_vague",
            "missing_fields": ["age", "breed", "symptoms"],
            "contexts": [],
            "answer": "",
        },
        # =================================================================
        # 34. ENHANCED CLARIFICATION - ENVIRONMENT VAGUE
        # =================================================================
        {
            "question": "Quelle température idéale pour mes poulets?",
            "ground_truth": "La température optimale varie considérablement selon l'âge:\n\n**Démarrage (0-7 jours)**:\n- Ambiante: 32-34°C\n- Sous éleveuse: 40-42°C\n\n**Croissance (8-21 jours)**:\n- Semaine 2: 28-30°C\n- Semaine 3: 24-26°C\n\n**Finition (22+ jours)**:\n- 21-23°C\n\n**Pouvez-vous préciser l'âge de vos poulets (en jours) pour que je vous donne la température exacte recommandée?**\n\nNote: La race (Ross 308, Cobb 500) a peu d'impact sur les besoins en température.",
            "category": "phase3_enhanced_clarification",
            "lang": "fr",
            "difficulty": "medium",
            "expected_behavior": "Doit détecter ambiguïté type 'environment_vague' (température sans précision d'âge), demander âge et donner exemples pour différentes phases",
            "expected_clarification": True,
            "ambiguity_type": "environment_vague",
            "missing_fields": ["age"],
            "contexts": [],
            "answer": "",
        },
        # =================================================================
        # 35. ENHANCED CLARIFICATION - MANAGEMENT BROAD
        # =================================================================
        {
            "question": "Comment améliorer ma rentabilité en élevage?",
            "ground_truth": "Améliorer la rentabilité nécessite une approche ciblée sur plusieurs axes. Pour vous conseiller efficacement, j'ai besoin de précisions:\n\n1. **Problème principal actuel**:\n   - FCR trop élevé (mauvaise conversion)?\n   - Poids insuffisant à l'abattage?\n   - Mortalité excessive?\n   - Coût alimentaire trop élevé?\n\n2. **Votre situation actuelle**:\n   - Race élevée: Ross 308, Cobb 500, autre?\n   - Âge d'abattage cible: 35j, 42j, 49j?\n   - Performances actuelles vs objectifs?\n\n3. **Contraintes**:\n   - Budget pour investissements?\n   - Infrastructure existante?\n\nAvec ces informations, je pourrai vous proposer des actions concrètes et priorisées pour maximiser votre rentabilité.",
            "category": "phase3_enhanced_clarification",
            "lang": "fr",
            "difficulty": "medium",
            "expected_behavior": "Doit détecter ambiguïté type 'management_broad' (question trop large), demander précisions sur problème spécifique, situation actuelle, contraintes",
            "expected_clarification": True,
            "ambiguity_type": "management_broad",
            "missing_fields": ["breed", "age", "metric", "current_performance"],
            "contexts": [],
            "answer": "",
        },
        # =================================================================
        # 36. ENHANCED CLARIFICATION - GENETICS INCOMPLETE
        # =================================================================
        {
            "question": "Comparer Ross 308 et Cobb 500",
            "ground_truth": 'Pour comparer Ross 308 et Cobb 500 de manière pertinente, j\'ai besoin de précisions:\n\n1. **Critère de comparaison**:\n   - Poids vif?\n   - FCR (conversion alimentaire)?\n   - Mortalité?\n   - Rendement carcasse?\n   - Coût global de production?\n   - Tous les critères?\n\n2. **Âge de référence**: 21j, 28j, 35j, 42j, ou autre?\n\n3. **Sexe**: Mâles, femelles, ou mixte?\n\nExemple: "Comparer Ross 308 et Cobb 500 sur poids et FCR à 35j pour mâles"\n\nCela me permettra de vous fournir une comparaison chiffrée et précise.',
            "category": "phase3_enhanced_clarification",
            "lang": "fr",
            "difficulty": "medium",
            "expected_behavior": "Doit détecter ambiguïté type 'genetics_incomplete' (comparaison sans critères), demander métrique de comparaison, âge, sexe",
            "expected_clarification": True,
            "ambiguity_type": "genetics_incomplete",
            "missing_fields": ["metric", "age", "sex"],
            "contexts": [],
            "answer": "",
        },
        # =================================================================
        # 37. ENHANCED CLARIFICATION - TREATMENT PROTOCOL VAGUE
        # =================================================================
        {
            "question": "Quel protocole vaccinal appliquer?",
            "ground_truth": "Le protocole vaccinal dépend de plusieurs facteurs. Pour vous recommander un protocole adapté, j'ai besoin de:\n\n1. **Âge des poulets**: Poussins d'un jour, en croissance, ou protocole complet 0-42j?\n\n2. **Race**: Broilers (Ross 308, Cobb 500) ou pondeuses?\n\n3. **Région/Pays**: Les maladies prévalentes varient (ex: Newcastle obligatoire dans certaines zones)\n\n4. **Statut sanitaire de la région**:\n   - Présence de maladies endémiques?\n   - Vaccination obligatoire contre certaines maladies?\n\n5. **Type d'élevage**: Intensif, plein air, bio?\n\n**Protocole de base broilers (France/Europe)**:\n- J1: Marek (couvoir) + IB + Newcastle\n- J10-14: Gumboro\n- J21: Rappel Newcastle (zones à risque)\n\nPouvez-vous préciser votre situation pour un protocole personnalisé?",
            "category": "phase3_enhanced_clarification",
            "lang": "fr",
            "difficulty": "medium",
            "expected_behavior": "Doit détecter ambiguïté type 'treatment_protocol_vague' (protocole sans contexte), demander âge, race, région, type d'élevage",
            "expected_clarification": True,
            "ambiguity_type": "treatment_protocol_vague",
            "missing_fields": ["age", "breed", "region"],
            "contexts": [],
            "answer": "",
        },
        # =================================================================
        # 38. EDGE CASE - EMPTY QUERY
        # =================================================================
        {
            "question": "",
            "ground_truth": "Je n'ai pas reçu de question. Comment puis-je vous aider aujourd'hui? Vous pouvez me poser des questions sur:\n\n- **Performances**: poids, FCR, mortalité pour différentes races et âges\n- **Santé**: maladies, symptômes, traitements, prévention\n- **Nutrition**: formulations alimentaires, phases de production\n- **Environnement**: température, densité, ventilation, éclairage\n- **Comparaisons**: Ross 308 vs Cobb 500, etc.\n\nN'hésitez pas à poser votre question!",
            "category": "phase3_edge_case",
            "lang": "fr",
            "difficulty": "easy",
            "expected_behavior": "Doit détecter query vide/None, retourner QueryType.HYBRID comme safe fallback, répondre poliment en proposant des exemples de questions",
            "expected_query_type": "HYBRID",
            "exclude_from_main": True,
            "contexts": [],
            "answer": "",
        },
        # =================================================================
        # 39. FARM-TO-PLANT INTEGRATION (Historically OOD)
        # =================================================================
        {
            "question": "What are the main data points processing plants need from farms to plan efficiently?",
            "ground_truth": """Processing plants require critical data points from farms:

**Production Schedule:** Flock placement dates, harvest dates, number of birds, expected weight (2.0-2.8 kg), production forecast.

**Performance Metrics:** Body weight, FCR, mortality rate, uniformity (CV% <10%), health status.

**Breed Info:** Type (Ross 308, Cobb 500), sex ratio, parent flock age.

**Quality & Safety:** Feed withdrawal timing (8-12h), last medication, transport time, antibiotic withdrawal compliance, quality issues.

**Logistics:** Farm location, loading capacity, catching crew, preferred catch time, crate availability.

**Compliance:** Certification status, vaccination records, feed traceability, biosecurity audits.

**Benefits:** Optimizes line speed, reduces costs, ensures compliance, improves yield prediction, enhances traceability.

Modern farms use management software with APIs for automatic data sharing.""",
            "category": "farm_to_plant_integration",
            "lang": "en",
            "difficulty": "medium",
            "expected_behavior": "Doit fournir réponse détaillée sur intégration ferme-usine. Historiquement détecté comme OOD, mais devrait maintenant répondre car lié à l'aviculture et données de performance",
            "expected_query_type": "KNOWLEDGE",
            "historical_note": "Previously classified as OOD - test if system now handles farm-to-plant supply chain questions",
            "contexts": [],
            "answer": "",
        },
    ]


def get_test_dataset_by_category(category: str) -> List[Dict[str, Any]]:
    """
    Filtre le dataset par catégorie.

    Args:
        category: Catégorie à filtrer (calculation, disease, comparative, etc.)

    Returns:
        Liste des questions de cette catégorie
    """
    dataset = get_intelia_test_dataset()
    return [case for case in dataset if case["category"] == category]


def get_categories() -> List[str]:
    """Retourne toutes les catégories disponibles"""
    dataset = get_intelia_test_dataset()
    return list(set(case["category"] for case in dataset))


# Pour compatibilité avec ragas_evaluator.py existant
def generate_poultry_golden_dataset() -> List[Dict[str, Any]]:
    """Alias pour compatibilité avec l'ancien code"""
    return get_intelia_test_dataset()
