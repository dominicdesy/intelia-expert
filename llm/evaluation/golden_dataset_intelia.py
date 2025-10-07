# -*- coding: utf-8 -*-
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
            "expected_behavior": "Doit utiliser reverse lookup (2400g → jour 35) puis calculer consommation cumulée avec interpolation proportionnelle",
            "contexts": [],
            "answer": ""
        },

        # =================================================================
        # 2. MALADIES - STATISTIQUES
        # =================================================================
        {
            "question": "Quelle maladie frappe le plus souvent les élevages de broiler ?",
            "ground_truth": "La coccidiose est la maladie la plus fréquente dans les élevages de broilers, suivie par les infections respiratoires (bronchite infectieuse, maladie de Newcastle) et les maladies bactériennes comme la colibacillose.",
            "category": "disease_statistics",
            "expected_behavior": "Doit fournir réponse basée sur documentation maladies courantes",
            "contexts": [],
            "answer": ""
        },

        # =================================================================
        # 3. MALADIES - PRÉVENTION
        # =================================================================
        {
            "question": "Comment prévenir la coccidiose ?",
            "ground_truth": "La prévention de la coccidiose inclut: (1) Utilisation de coccidiostatiques dans l'aliment, (2) Vaccination par spray ou eau de boisson (vaccins vivants atténués), (3) Biosécurité stricte (nettoyage et désinfection), (4) Gestion de la litière (éviter humidité excessive), (5) Densité appropriée, (6) Programme de rotation des anticoccidiens pour éviter résistance.",
            "category": "disease_prevention",
            "expected_behavior": "Doit récupérer documentation sur prévention coccidiose",
            "contexts": [],
            "answer": ""
        },

        # =================================================================
        # 4. OUT-OF-DOMAIN (DOIT ÊTRE REJETÉ)
        # =================================================================
        {
            "question": "Qu'est-ce que la cryptomonnaie ?",
            "ground_truth": "Je suis désolé, mais cette question ne concerne pas la production avicole. Je suis spécialisé dans les questions relatives aux poulets de chair, pondeuses, nutrition, santé et gestion d'élevage. Puis-je vous aider avec une question sur l'aviculture ?",
            "category": "out_of_domain",
            "expected_behavior": "Doit être détecté comme hors-domaine et poliment refusé",
            "contexts": [],
            "answer": ""
        },

        # =================================================================
        # 5. MALADIES - SYMPTÔMES
        # =================================================================
        {
            "question": "Quels sont les symptômes de Newcastle ?",
            "ground_truth": "Les symptômes de la maladie de Newcastle incluent: détresse respiratoire (toux, éternuements, respiration difficile), diarrhée verdâtre, signes nerveux (torticolis, paralysie des ailes et pattes, tremblements, mouvements circulaires), chute brutale de la ponte chez les pondeuses, œufs déformés ou sans coquille, mortalité élevée (jusqu'à 100% en souches virulentes).",
            "category": "disease_symptoms",
            "expected_behavior": "Doit récupérer documentation complète sur Newcastle",
            "contexts": [],
            "answer": ""
        },

        # =================================================================
        # 6. MÉTRIQUES - QUESTION INCOMPLÈTE (CLARIFICATION NÉCESSAIRE)
        # =================================================================
        {
            "question": "Quel est le poids d'un Ross 308 mâle ?",
            "ground_truth": "Pour vous donner le poids précis d'un Ross 308 mâle, j'ai besoin de connaître l'âge en jours. Par exemple: à 21 jours, le poids est de 966g; à 28 jours, 1550g; à 35 jours, 2441g; à 42 jours, 3131g. À quel âge souhaitez-vous connaître le poids ?",
            "category": "clarification_needed",
            "expected_behavior": "Doit demander clarification pour l'âge, idéalement donner exemples",
            "contexts": [],
            "answer": ""
        },

        # =================================================================
        # 7. MULTI-LANGUE - ANGLAIS
        # =================================================================
        {
            "question": "What is the weight of a Cobb 500 male?",
            "ground_truth": "To provide the precise weight of a Cobb 500 male, I need to know the age in days. For example: at 21 days, the weight is approximately 950g; at 28 days, 1520g; at 35 days, 2380g; at 42 days, 3050g. At what age would you like to know the weight?",
            "category": "multilingual_english",
            "expected_behavior": "Doit détecter anglais et répondre en anglais avec demande de clarification",
            "contexts": [],
            "answer": ""
        },

        # =================================================================
        # 8. QUESTION TROP VAGUE
        # =================================================================
        {
            "question": "Quel est le poids d'un poulet ?",
            "ground_truth": "Le poids d'un poulet varie selon la souche (Ross 308, Cobb 500, etc.), le sexe (mâle, femelle, mixte), et surtout l'âge. Pourriez-vous préciser: (1) Quelle souche de poulet ? (2) Quel sexe ? (3) À quel âge en jours ? Par exemple, un Ross 308 mâle à 35 jours pèse environ 2441g.",
            "category": "too_vague",
            "expected_behavior": "Doit demander clarifications multiples (breed, sex, age)",
            "contexts": [],
            "answer": ""
        },

        # =================================================================
        # 9. COMPARATIF - DEUX SOUCHES
        # =================================================================
        {
            "question": "Compare le poids de Ross 308 vs Cobb 500 à 35 jours",
            "ground_truth": "À 35 jours pour les mâles: Ross 308 atteint 2441g tandis que Cobb 500 atteint 2380g, soit une différence de 61g en faveur de Ross 308 (+2.6%). Pour le FCR à 35 jours: Ross 308 a un FCR de 1.390 et Cobb 500 de 1.410, soit une différence de 0.020 en faveur de Ross 308 (meilleure conversion alimentaire).",
            "category": "comparative",
            "expected_behavior": "Doit comparer poids ET FCR, donner différences absolues et relatives",
            "contexts": [],
            "answer": ""
        },

        # =================================================================
        # 10. MÉTRIQUES SIMPLES - FCR
        # =================================================================
        {
            "question": "Quel est le FCR d'un Ross 308 mâle de 21 jours ?",
            "ground_truth": "Le FCR (Feed Conversion Ratio) d'un Ross 308 mâle à 21 jours est de 1.141.",
            "category": "metric_simple",
            "expected_behavior": "Doit récupérer valeur exacte depuis PostgreSQL",
            "contexts": [],
            "answer": ""
        },

        # =================================================================
        # 11. MULTI-LANGUE - THAÏ (HORS SCOPE)
        # =================================================================
        {
            "question": "น้ำหนักของ Ross 308 อายุ 35 วัน",
            "ground_truth": "Je suis désolé, mais je ne peux traiter que les questions en français ou en anglais. Pourriez-vous reformuler votre question dans l'une de ces langues ? (Note: This question asks about Ross 308 weight at 35 days in Thai)",
            "category": "unsupported_language",
            "expected_behavior": "Doit détecter langue non supportée et demander traduction FR/EN",
            "contexts": [],
            "answer": ""
        },

        # =================================================================
        # 12. CALCUL TROUPEAU
        # =================================================================
        {
            "question": "Combien de kg d'aliment pour 10,000 Ross 308 du jour 0 au jour 42 ?",
            "ground_truth": "Pour élever 10,000 Ross 308 de 0 à 42 jours, il faut environ 52,000-54,000 kg d'aliment (poids moyen ~3.1 kg × FCR ~1.68 × 10,000 oiseaux, ajusté pour mortalité ~3%).",
            "category": "flock_calculation",
            "expected_behavior": "Doit calculer: poids final × FCR × nombre d'oiseaux × (1 - mortalité)",
            "contexts": [],
            "answer": ""
        },

        # =================================================================
        # 13. REVERSE LOOKUP - POIDS CIBLE
        # =================================================================
        {
            "question": "À quel âge Ross 308 mâle atteint-il 3 kg ?",
            "ground_truth": "Ross 308 mâle atteint 3000g (3 kg) entre le jour 41 et 42. Plus précisément, au jour 42, le poids est de 3131g.",
            "category": "reverse_lookup",
            "expected_behavior": "Doit utiliser reverse_lookup pour trouver âge correspondant à 3000g",
            "contexts": [],
            "answer": ""
        },

        # =================================================================
        # 14. PROJECTION DE CROISSANCE
        # =================================================================
        {
            "question": "Quel sera le poids à 42j si je suis à 1.2kg à 28j ?",
            "ground_truth": "Si votre troupeau Ross 308 pèse 1200g à 28 jours au lieu de 1550g attendu, il y a un retard significatif de 350g (23%). En projetant avec le taux de croissance standard, le poids à 42j serait d'environ 2400-2500g au lieu des 3131g attendus. Il est important d'identifier et corriger les causes du retard (nutrition, santé, environnement).",
            "category": "projection_diagnostic",
            "expected_behavior": "Doit détecter sous-performance, projeter avec ajustement, alerter sur retard",
            "contexts": [],
            "answer": ""
        },

        # =================================================================
        # 15. DIAGNOSTIC - RETARD DE CROISSANCE
        # =================================================================
        {
            "question": "Mon troupeau Ross 308 à 28j pèse 1300g au lieu de 1550g, c'est grave ?",
            "ground_truth": "Oui, un retard de 250g (16%) à 28 jours est significatif. Les causes possibles incluent: (1) Qualité ou quantité insuffisante d'aliment, (2) Température inadéquate (stress thermique ou froid), (3) Maladies subcliniques (coccidiose, entérite), (4) Densité excessive, (5) Qualité de l'eau, (6) Mauvaise ventilation. Il faut investiguer rapidement pour corriger le problème.",
            "category": "diagnostic_underperformance",
            "expected_behavior": "Doit calculer écart %, évaluer gravité, lister causes possibles",
            "contexts": [],
            "answer": ""
        },

        # =================================================================
        # 16. DIAGNOSTIC - FCR ÉLEVÉ
        # =================================================================
        {
            "question": "Mon FCR à 35j est de 1.65 au lieu de 1.39, quelles sont les causes ?",
            "ground_truth": "Un FCR de 1.65 au lieu de 1.39 à 35 jours indique une surconsommation d'aliment ou une sous-performance de croissance (+19% vs objectif). Causes possibles: (1) Qualité nutritionnelle de l'aliment (énergie, digestibilité), (2) Gaspillage d'aliment (mangeoires mal réglées, abreuvoirs qui fuient), (3) Maladies affectant l'absorption (coccidiose, entérite), (4) Température inadéquate (augmente les besoins énergétiques), (5) Stress chronique, (6) Souche inadaptée aux conditions.",
            "category": "diagnostic_fcr",
            "expected_behavior": "Doit calculer écart FCR, identifier impact économique, lister causes",
            "contexts": [],
            "answer": ""
        },

        # =================================================================
        # 17. NUTRITION - PROTÉINE STARTER (COBB 500)
        # =================================================================
        {
            "question": "Quel taux de protéine dans l'aliment starter pour Cobb 500 ?",
            "ground_truth": "Le taux de protéine recommandé dans l'aliment starter pour Cobb 500 (0-10 jours) est de 22-23% de protéine brute, avec une énergie métabolisable de 2950-3000 kcal/kg.",
            "category": "nutrition_specification",
            "expected_behavior": "Doit récupérer spécifications nutritionnelles Cobb 500 starter",
            "contexts": [],
            "answer": ""
        },

        # =================================================================
        # 18. NUTRITION - DIFFÉRENCE PHASES
        # =================================================================
        {
            "question": "Quelle est la différence entre aliment starter et grower ?",
            "ground_truth": "L'aliment starter (0-10j) a une protéine plus élevée (22-23%) et énergie modérée (2950-3000 kcal/kg) pour soutenir la croissance rapide initiale. L'aliment grower (11-24j) a une protéine réduite (20-21%) et énergie plus élevée (3100-3200 kcal/kg) pour optimiser le gain de poids. Le starter utilise aussi des ingrédients plus digestibles et des granules plus petits.",
            "category": "nutrition_concept",
            "expected_behavior": "Doit expliquer différences composition et objectifs nutritionnels",
            "contexts": [],
            "answer": ""
        },

        # =================================================================
        # 19. ENVIRONNEMENT - TEMPÉRATURE DÉMARRAGE
        # =================================================================
        {
            "question": "Quelle température pour des poussins Ross 308 au jour 1 ?",
            "ground_truth": "La température ambiante optimale pour les poussins Ross 308 au jour 1 est de 32-34°C, avec une température sous éleveuse (radiant) de 40-42°C. L'humidité doit être maintenue à 60-70%.",
            "category": "environment_temperature",
            "expected_behavior": "Doit fournir température ambiante ET sous éleveuse, plus humidité",
            "contexts": [],
            "answer": ""
        },

        # =================================================================
        # 20. DIAGNOSTIC - STRESS THERMIQUE
        # =================================================================
        {
            "question": "Mon bâtiment est à 35°C au jour 21, est-ce trop chaud ?",
            "ground_truth": "Oui, 35°C à 21 jours est beaucoup trop chaud. La température recommandée à 21 jours est de 21-23°C. À 35°C, les poulets sont en stress thermique sévère: réduction de consommation d'aliment, halètement, mortalité possible. Il faut immédiatement augmenter la ventilation, vérifier les systèmes de refroidissement (pad cooling, brumisation), et assurer accès à eau fraîche abondante.",
            "category": "diagnostic_heat_stress",
            "expected_behavior": "Doit comparer avec température cible, évaluer gravité, donner actions correctives urgentes",
            "contexts": [],
            "answer": ""
        },

        # =================================================================
        # 21. MULTI-MÉTRIQUES
        # =================================================================
        {
            "question": "Donne-moi poids, FCR et mortalité pour Ross 308 mâle à 28 jours",
            "ground_truth": "Ross 308 mâle à 28 jours: Poids = 1550g, FCR = 1.277, Mortalité cumulée = 2.0-2.5% (selon conditions d'élevage).",
            "category": "multi_metric",
            "expected_behavior": "Doit extraire 3 métriques différentes simultanément",
            "contexts": [],
            "answer": ""
        },

        # =================================================================
        # 22. COMPARATIF MULTI-ÂGES
        # =================================================================
        {
            "question": "Compare Ross 308 et Cobb 500 à 21, 28 et 35 jours",
            "ground_truth": "Comparaison Ross 308 vs Cobb 500 mâles:\n\nJour 21: Ross 308 = 966g, Cobb 500 = 950g (différence +16g)\nJour 28: Ross 308 = 1550g, Cobb 500 = 1520g (différence +30g)\nJour 35: Ross 308 = 2441g, Cobb 500 = 2380g (différence +61g)\n\nRoss 308 maintient un avantage de poids croissant avec l'âge. Les FCR sont similaires avec léger avantage Ross 308 (1.390 vs 1.410 à 35j).",
            "category": "comparative_multi_age",
            "expected_behavior": "Doit comparer 3 âges × 2 souches, calculer différences, identifier tendances",
            "contexts": [],
            "answer": ""
        },

        # =================================================================
        # 23. QUESTION SUBJECTIVE
        # =================================================================
        {
            "question": "Quel est le meilleur: Ross 308 ou Cobb 500 ?",
            "ground_truth": "Les deux souches sont excellentes, le choix dépend de vos objectifs et conditions:\n\nRoss 308: Léger avantage en poids vif (+2-3%) et FCR légèrement meilleur, robustesse, adapté aux marchés demandant gros calibres.\n\nCobb 500: Rendement carcasse légèrement supérieur, uniformité excellente, très polyvalent.\n\nLe 'meilleur' dépend de: (1) Marché cible (poids abattage), (2) Prix aliment local, (3) Conditions climatiques, (4) Exigences rendement vs poids vif. Les deux offrent performances similaires dans des conditions optimales.",
            "category": "subjective_comparison",
            "expected_behavior": "Doit éviter réponse absolue, présenter avantages de chaque souche, contextualiser",
            "contexts": [],
            "answer": ""
        },

        # =================================================================
        # 24. VALIDATION - ÂGE HORS LIMITES
        # =================================================================
        {
            "question": "Poids Ross 308 jour 500",
            "ground_truth": "L'âge de 500 jours est hors des limites pour un broiler Ross 308, qui est élevé pour la viande et généralement abattu entre 35-56 jours. Les données de performance Ross 308 couvrent la période 0-63 jours. Si vous élevez des reproducteurs Ross 308, les données sont différentes. Pourriez-vous préciser votre besoin ?",
            "category": "validation_age_limit",
            "expected_behavior": "Doit détecter âge invalide pour broiler, expliquer limites, demander clarification",
            "contexts": [],
            "answer": ""
        },

        # =================================================================
        # 25. CONVERSATIONNEL - CONTINUITÉ SIMPLE
        # =================================================================
        {
            "question": "Quel est le poids Ross 308 mâle à 21 jours ?",
            "ground_truth": "Le poids d'un Ross 308 mâle à 21 jours est de 966 grammes.",
            "category": "conversational_turn1",
            "expected_behavior": "Réponse directe, mémoriser contexte (Ross 308 mâle)",
            "contexts": [],
            "answer": "",
            "follow_up_question": "Et à 28 jours ?",
            "follow_up_ground_truth": "À 28 jours, le poids d'un Ross 308 mâle est de 1550 grammes (gain de 584g entre jour 21 et 28)."
        },

        # =================================================================
        # 26. CONVERSATIONNEL - FOLLOW-UP (TOUR 2)
        # =================================================================
        {
            "question": "Et à 28 jours ?",
            "ground_truth": "À 28 jours, le poids d'un Ross 308 mâle est de 1550 grammes (gain de 584g entre jour 21 et 28).",
            "category": "conversational_turn2",
            "expected_behavior": "Doit utiliser contexte précédent (Ross 308 mâle) pour répondre",
            "contexts": [],
            "answer": "",
            "requires_previous_context": True,
            "context_from_question": "Quel est le poids Ross 308 mâle à 21 jours ?"
        },

        # =================================================================
        # 27. CONVERSATIONNEL - COMPARATIF TOUR 1
        # =================================================================
        {
            "question": "Compare Ross 308 et Cobb 500 à 35j",
            "ground_truth": "À 35 jours pour les mâles: Ross 308 atteint 2441g tandis que Cobb 500 atteint 2380g, soit une différence de 61g en faveur de Ross 308 (+2.6%). Pour le FCR: Ross 308 = 1.390, Cobb 500 = 1.410, différence de 0.020 en faveur de Ross 308.",
            "category": "conversational_comparative_turn1",
            "expected_behavior": "Réponse comparative complète, mémoriser contexte comparaison",
            "contexts": [],
            "answer": "",
            "follow_up_question": "Lequel consomme le plus d'aliment ?",
            "follow_up_ground_truth": "À 35 jours, Ross 308 mâle consomme légèrement plus d'aliment en valeur absolue (3394g vs 3352g pour Cobb 500), soit +42g. Cependant, grâce à son meilleur FCR (1.390 vs 1.410), Ross 308 convertit cet aliment plus efficacement en poids vif."
        },

        # =================================================================
        # 28. CONVERSATIONNEL - FOLLOW-UP COMPARATIF (TOUR 2)
        # =================================================================
        {
            "question": "Lequel consomme le plus d'aliment ?",
            "ground_truth": "À 35 jours, Ross 308 mâle consomme légèrement plus d'aliment en valeur absolue (3394g vs 3352g pour Cobb 500), soit +42g. Cependant, grâce à son meilleur FCR (1.390 vs 1.410), Ross 308 convertit cet aliment plus efficacement en poids vif.",
            "category": "conversational_comparative_turn2",
            "expected_behavior": "Doit utiliser contexte comparaison Ross 308 vs Cobb 500 à 35j",
            "contexts": [],
            "answer": "",
            "requires_previous_context": True,
            "context_from_question": "Compare Ross 308 et Cobb 500 à 35j"
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
