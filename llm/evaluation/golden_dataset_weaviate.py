# -*- coding: utf-8 -*-
"""
golden_dataset_weaviate.py - Dataset RAGAS pour évaluation Weaviate uniquement

Ce dataset teste UNIQUEMENT le contenu narratif/qualitatif indexé dans Weaviate:
- Guides de management (brooding, ventilation, densité, biosécurité)
- Maladies avicoles (symptômes, prévention, traitement)
- Nutrition générale (types d'aliments, formulation)
- Processing & qualité carcasse

EXCLUS: Questions calculatoires (FCR, poids, consommation) → Ces données sont dans PostgreSQL

Objectif: Obtenir Context Recall réaliste (50-80%) pour optimiser chunking/retrieval/reranking
"""

from typing import List, Dict, Any


def get_weaviate_test_dataset() -> List[Dict[str, Any]]:
    """
    Dataset pour évaluation Weaviate - Questions alignées au contenu Knowledge/

    Chaque cas contient:
    - question: Question posée par l'utilisateur
    - ground_truth: Réponse attendue (validée manuellement)
    - category: Catégorie de la question
    - difficulty: easy/medium/hard
    - expected_source: "weaviate" (pour traçabilité)
    - contexts: Rempli dynamiquement lors de l'évaluation
    - answer: Rempli par le RAG lors de l'évaluation
    """

    return [
        # =================================================================
        # 1. MANAGEMENT - BROODING (Ross 308 Management Guide)
        # =================================================================
        {
            "question": "Quelles sont les meilleures pratiques de brooding pour des poussins Ross 308 au premier jour?",
            "ground_truth": "Les meilleures pratiques de brooding pour Ross 308 incluent: (1) Température initiale de 30-32°C au niveau des poussins, (2) Humidité relative minimum 50-60%, (3) Accès facile à l'eau et à l'aliment dès le placement, (4) Transition entre systèmes supplémentaires et automatiques à 4-5 jours, (5) Surveillance du remplissage du jabot, (6) Ventilation minimale dès le jour 1 pour éviter accumulation de CO2.",
            "category": "management_brooding",
            "lang": "fr",
            "difficulty": "medium",
            "expected_source": "weaviate",
            "contexts": [],
            "answer": "",
        },
        {
            "question": "What is the recommended ambient temperature for Ross 308 broilers from 21 days onwards?",
            "ground_truth": "The recommended ambient temperature for Ross 308 broilers from 21 days onwards is less than 21°C (69.8°F). Fast growing broilers produce large amounts of heat particularly in the second half of the grow-out period, so maintaining cooler temperatures may improve growth rates.",
            "category": "management_temperature",
            "lang": "en",
            "difficulty": "easy",
            "expected_source": "weaviate",
            "contexts": [],
            "answer": "",
        },
        # =================================================================
        # 2. MALADIES - COCCIDIOSE
        # =================================================================
        {
            "question": "Comment prévenir la coccidiose dans un élevage de poulets de chair?",
            "ground_truth": "La prévention de la coccidiose inclut: (1) Utilisation de coccidiostatiques dans l'aliment, (2) Vaccination par spray ou eau de boisson avec vaccins vivants atténués, (3) Biosécurité stricte avec nettoyage et désinfection réguliers, (4) Gestion de la litière pour éviter humidité excessive, (5) Densité d'élevage appropriée, (6) Programme de rotation des anticoccidiens pour éviter résistance parasitaire.",
            "category": "disease_prevention",
            "lang": "fr",
            "difficulty": "medium",
            "expected_source": "weaviate",
            "contexts": [],
            "answer": "",
        },
        {
            "question": "Quels sont les symptômes principaux de la coccidiose chez les poulets?",
            "ground_truth": "Les symptômes principaux de la coccidiose incluent: diarrhée (souvent sanglante dans la coccidiose caecale), plumes ébouriffées, perte d'appétit, léthargie, croissance ralentie, déshydratation, anémie dans les cas sévères. Les lésions intestinales peuvent être visibles à l'autopsie avec épaississement de la paroi intestinale et présence de sang.",
            "category": "disease_symptoms",
            "lang": "fr",
            "difficulty": "medium",
            "expected_source": "weaviate",
            "contexts": [],
            "answer": "",
        },
        # =================================================================
        # 3. MALADIES - NEWCASTLE & RESPIRATOIRES
        # =================================================================
        {
            "question": "What are the clinical signs of Newcastle disease in broilers?",
            "ground_truth": "Clinical signs of Newcastle disease include: respiratory symptoms (gasping, coughing, nasal discharge), nervous signs (tremors, twisted neck, paralysis, circling), greenish watery diarrhea, depression, decreased egg production in layers, swelling around eyes and neck, sudden death. Severity depends on virus strain virulence.",
            "category": "disease_symptoms",
            "lang": "en",
            "difficulty": "medium",
            "expected_source": "weaviate",
            "contexts": [],
            "answer": "",
        },
        {
            "question": "Comment différencier la bronchite infectieuse de la maladie de Newcastle?",
            "ground_truth": "La différenciation clinique peut être difficile car les deux causent des symptômes respiratoires. Différences clés: (1) Newcastle: symptômes nerveux fréquents (torticolis, paralysie), diarrhée verdâtre, mortalité plus élevée. (2) Bronchite infectieuse: principalement respiratoire, trachée avec mucus, pas de symptômes nerveux, chute de ponte marquée chez les pondeuses. Diagnostic définitif requiert tests de laboratoire (PCR, sérologie).",
            "category": "disease_diagnosis",
            "lang": "fr",
            "difficulty": "hard",
            "expected_source": "weaviate",
            "contexts": [],
            "answer": "",
        },
        # =================================================================
        # 4. BIOSÉCURITÉ
        # =================================================================
        {
            "question": "Quelles sont les mesures de biosécurité essentielles pour un élevage de poulets?",
            "ground_truth": "Mesures de biosécurité essentielles: (1) Contrôle des accès avec pédiluves et vestiaires, (2) Protocoles d'entrée/sortie stricts pour visiteurs et employés, (3) Nettoyage et désinfection entre bandes (vide sanitaire), (4) Contrôle des nuisibles (rongeurs, insectes, oiseaux sauvages), (5) Gestion des cadavres appropriée, (6) Eau et aliments de qualité contrôlée, (7) Quarantaine pour nouveaux animaux, (8) Formation du personnel aux bonnes pratiques.",
            "category": "biosecurity",
            "lang": "fr",
            "difficulty": "medium",
            "expected_source": "weaviate",
            "contexts": [],
            "answer": "",
        },
        # =================================================================
        # 5. NUTRITION - GÉNÉRAL (pas de calculs)
        # =================================================================
        {
            "question": "Quels sont les principaux types d'aliments utilisés dans l'élevage de poulets de chair?",
            "ground_truth": "Les principaux types d'aliments sont: (1) Aliment démarrage (0-10 jours): hautement digestible, riche en protéines (22-23%), petites particules. (2) Aliment croissance (10-24 jours): protéines 20-21%, énergie modérée. (3) Aliment finition (24 jours-abattage): protéines 18-19%, énergie élevée pour maximiser gain de poids. (4) Retrait: quelques jours avant abattage, sans additifs médicamenteux. La forme peut être miette, granulé ou farine selon l'âge.",
            "category": "nutrition_general",
            "lang": "fr",
            "difficulty": "medium",
            "expected_source": "weaviate",
            "contexts": [],
            "answer": "",
        },
        {
            "question": "Why is water quality important for broiler production?",
            "ground_truth": "Water quality is critical because: (1) Broilers consume 1.5-2 times more water than feed by weight, (2) Poor water quality reduces feed intake and growth, (3) Contaminated water spreads diseases (E.coli, Salmonella), (4) High mineral content (iron, sulfates) affects taste and palatability, (5) Biofilm in pipes harbors bacteria. Water should be tested regularly for pH (6.0-8.0 ideal), bacterial count, mineral content, and treated appropriately (chlorination, filtration).",
            "category": "management_water",
            "lang": "en",
            "difficulty": "medium",
            "expected_source": "weaviate",
            "contexts": [],
            "answer": "",
        },
        # =================================================================
        # 6. VENTILATION & ENVIRONNEMENT
        # =================================================================
        {
            "question": "Pourquoi la ventilation minimale est-elle importante dès le premier jour?",
            "ground_truth": "La ventilation minimale dès le premier jour est essentielle pour: (1) Éliminer le CO2 et l'ammoniac qui s'accumulent rapidement, (2) Contrôler l'humidité relative (éviter <50% ou >70%), (3) Fournir oxygène frais aux poussins, (4) Prévenir maladies respiratoires, (5) Maintenir qualité de litière. La ventilation doit être équilibrée: suffisante pour qualité d'air mais pas excessive pour ne pas refroidir les poussins.",
            "category": "management_ventilation",
            "lang": "fr",
            "difficulty": "medium",
            "expected_source": "weaviate",
            "contexts": [],
            "answer": "",
        },
        # =================================================================
        # 7. WELFARE & DENSITÉ
        # =================================================================
        {
            "question": "What is the recommended stocking density for Ross 308 broilers?",
            "ground_truth": "Recommended stocking density for Ross 308 depends on target weight and climate: (1) For 2-2.5 kg birds: 30-34 kg/m² final weight (approximately 12-15 birds/m²), (2) For heavier birds: 38-42 kg/m² in controlled environments. Factors to consider: climate control capacity, ventilation efficiency, local regulations, bird welfare, litter management. Lower densities improve welfare, uniformity, and performance but reduce economic efficiency.",
            "category": "management_density",
            "lang": "en",
            "difficulty": "medium",
            "expected_source": "weaviate",
            "contexts": [],
            "answer": "",
        },
        # =================================================================
        # 8. CARCASSE & PROCESSING
        # =================================================================
        {
            "question": "Quels facteurs affectent le rendement en carcasse des poulets de chair?",
            "ground_truth": "Facteurs affectant le rendement carcasse: (1) Génétique (Ross 308 optimisé pour rendement élevé), (2) Nutrition (ratio protéines/énergie, acides aminés), (3) Âge et poids d'abattage, (4) Sexe (mâles meilleur rendement que femelles), (5) Jeûne pré-abattage (trop court ou long réduit rendement), (6) Méthode de refroidissement (eau vs air), (7) Équipement processing (perte durant plumage/éviscération), (8) Présence/absence de gras abdominal dans définition carcasse.",
            "category": "processing_yield",
            "lang": "fr",
            "difficulty": "hard",
            "expected_source": "weaviate",
            "contexts": [],
            "answer": "",
        },
        # =================================================================
        # 9. MALADIES - GÉNÉRAL
        # =================================================================
        {
            "question": "Quelle est la maladie la plus fréquente dans les élevages de poulets de chair?",
            "ground_truth": "La coccidiose est la maladie la plus fréquente dans les élevages de poulets de chair, suivie par les infections respiratoires (bronchite infectieuse, maladie de Newcastle) et les maladies bactériennes comme la colibacillose. La coccidiose est causée par des parasites protozoaires (Eimeria spp.) et reste prévalente malgré les programmes de vaccination et anticoccidiens car le parasite se développe dans l'environnement de la ferme.",
            "category": "disease_statistics",
            "lang": "fr",
            "difficulty": "easy",
            "expected_source": "weaviate",
            "contexts": [],
            "answer": "",
        },
        # =================================================================
        # 10. NUTRITION - FORMULATION (qualitatif)
        # =================================================================
        {
            "question": "What are the main components of a broiler starter feed formulation?",
            "ground_truth": "Main components of broiler starter feed: (1) Energy sources: corn, wheat, sorghum (50-60%), (2) Protein sources: soybean meal, fishmeal, canola meal (30-40%), providing amino acids, (3) Fat/oil: 2-4% for energy density, (4) Minerals: calcium, phosphorus, trace minerals (1-2%), (5) Vitamins: A, D3, E, B-complex (premix), (6) Additives: enzymes (phytase, xylanase), probiotics, organic acids. Formulation targets: 22-23% crude protein, 3000-3100 kcal/kg metabolizable energy.",
            "category": "nutrition_formulation",
            "lang": "en",
            "difficulty": "hard",
            "expected_source": "weaviate",
            "contexts": [],
            "answer": "",
        },
        # =================================================================
        # 11. COMPORTEMENT & MONITORING
        # =================================================================
        {
            "question": "Comment surveiller le bien-être des poulets pendant la phase de croissance?",
            "ground_truth": "Surveillance du bien-être inclut: (1) Observation du comportement (activité, vocalisation, distribution dans le bâtiment), (2) Monitoring de la consommation d'eau et d'aliment (indicateur précoce de problèmes), (3) Évaluation de la qualité de la litière (friabilité, humidité <25%), (4) Inspection des pattes (dermatites plantaires, boiteries), (5) Contrôle de la mortalité quotidienne, (6) Évaluation de l'uniformité du lot, (7) Suivi des performances (poids, croissance), (8) Autopsies en cas de mortalité anormale.",
            "category": "welfare_monitoring",
            "lang": "fr",
            "difficulty": "medium",
            "expected_source": "weaviate",
            "contexts": [],
            "answer": "",
        },
        # =================================================================
        # 12. MALADIES - MÉTABOLIQUES
        # =================================================================
        {
            "question": "What causes ascites in fast-growing broilers?",
            "ground_truth": "Ascites (fluid accumulation in abdomen) is caused by: (1) Rapid growth rate exceeding cardiovascular capacity, (2) High metabolic oxygen demand in fast-growing birds, (3) Pulmonary hypertension leading to right heart failure, (4) Environmental factors: high altitude, poor ventilation, cold stress, (5) Nutritional factors: high energy density, excessive sodium. Prevention includes: controlled growth curves, optimal ventilation, appropriate stocking density, lighting programs to reduce early growth rate, genetic selection for cardiovascular fitness.",
            "category": "disease_metabolic",
            "lang": "en",
            "difficulty": "hard",
            "expected_source": "weaviate",
            "contexts": [],
            "answer": "",
        },
        # =================================================================
        # 13. LIGHTING & PHOTOPERIOD
        # =================================================================
        {
            "question": "Quel programme lumineux est recommandé pour les poulets de chair Ross 308?",
            "ground_truth": "Programme lumineux recommandé pour Ross 308: (1) Jours 0-7: 23 heures de lumière, 1 heure obscurité pour habituer aux pannes, intensité 20-40 lux, (2) Jours 7-14: réduction progressive à 18-20h lumière, (3) Jours 14-abattage: 18h lumière / 6h obscurité, intensité réduite à 5-10 lux. Les périodes d'obscurité améliorent le bien-être, permettent repos, réduisent mortalité cardiovasculaire et troubles métaboliques. Un programme intermittent peut être utilisé pour optimiser conversions alimentaires.",
            "category": "management_lighting",
            "lang": "fr",
            "difficulty": "medium",
            "expected_source": "weaviate",
            "contexts": [],
            "answer": "",
        },
        # =================================================================
        # 14. GUT HEALTH
        # =================================================================
        {
            "question": "How can you maintain good gut health in broilers without antibiotics?",
            "ground_truth": "Maintaining gut health without antibiotics involves: (1) High-quality, highly digestible feed ingredients to reduce undigested substrate for pathogens, (2) Feed enzymes (xylanase, protease) to improve nutrient utilization, (3) Organic acids to reduce pathogenic bacteria pH, (4) Probiotics and prebiotics to promote beneficial microbiota, (5) Essential oils and plant extracts with antimicrobial properties, (6) Optimal coccidiosis control (vaccination or limited anticoccidials), (7) Good water quality and hygiene, (8) Proper stocking density and ventilation to reduce stress.",
            "category": "gut_health",
            "lang": "en",
            "difficulty": "hard",
            "expected_source": "weaviate",
            "contexts": [],
            "answer": "",
        },
        # =================================================================
        # 15. HATCHERY & CHICK QUALITY
        # =================================================================
        {
            "question": "Quels sont les indicateurs d'une bonne qualité de poussins à l'éclosion?",
            "ground_truth": "Indicateurs de qualité des poussins: (1) Apparence: duvet sec et propre, yeux brillants et alertes, (2) Activité: poussins vifs et réactifs, (3) Ombilic: bien cicatrisé, aucun saignement, (4) Pattes: fortes et droites, bonne pigmentation, (5) Poids: uniforme, 38-44g selon génétique, (6) Absence de malformations (bec, pattes, abdomen), (7) Absence de contamination fécale, (8) Bon remplissage de l'abdomen (sac vitellin résiduel optimal). Score Pasgar ≥8/10 indique excellente qualité.",
            "category": "hatchery_quality",
            "lang": "fr",
            "difficulty": "medium",
            "expected_source": "weaviate",
            "contexts": [],
            "answer": "",
        },
    ]


def get_weaviate_test_summary() -> Dict[str, Any]:
    """Résumé du dataset Weaviate pour validation"""
    dataset = get_weaviate_test_dataset()

    categories = {}
    for item in dataset:
        cat = item['category']
        categories[cat] = categories.get(cat, 0) + 1

    return {
        "total_cases": len(dataset),
        "categories": categories,
        "languages": {
            "fr": sum(1 for item in dataset if item['lang'] == 'fr'),
            "en": sum(1 for item in dataset if item['lang'] == 'en'),
        },
        "difficulty": {
            "easy": sum(1 for item in dataset if item['difficulty'] == 'easy'),
            "medium": sum(1 for item in dataset if item['difficulty'] == 'medium'),
            "hard": sum(1 for item in dataset if item['difficulty'] == 'hard'),
        },
    }


if __name__ == "__main__":
    # Validation rapide du dataset
    dataset = get_weaviate_test_dataset()
    summary = get_weaviate_test_summary()

    print("=" * 80)
    print("GOLDEN DATASET WEAVIATE - VALIDATION")
    print("=" * 80)
    print(f"\nTotal test cases: {summary['total_cases']}")
    print("\nLangues:")
    print(f"  - Français: {summary['languages']['fr']}")
    print(f"  - English: {summary['languages']['en']}")
    print("\nDifficulté:")
    print(f"  - Easy: {summary['difficulty']['easy']}")
    print(f"  - Medium: {summary['difficulty']['medium']}")
    print(f"  - Hard: {summary['difficulty']['hard']}")
    print("\nCatégories:")
    for cat, count in sorted(summary['categories'].items()):
        print(f"  - {cat}: {count}")
    print("\n✅ Dataset validé - Prêt pour évaluation RAGAS")
