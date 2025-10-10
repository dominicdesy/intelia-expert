# -*- coding: utf-8 -*-
"""
golden_dataset_weaviate_v2.py - Dataset RAGAS basé sur le contenu RÉEL des documents Health

Ce dataset contient 10 questions extraites directement des documents indexés dans Weaviate:
- ascites_extracted.txt
- ilt_extracted.txt
- infectious_bronchitis_virus_ibv_extracted.txt
- fowl_cholera_extracted.txt

Objectif: Tester le retrieval avec des questions dont les réponses existent CERTAINEMENT dans Weaviate
"""

from typing import List, Dict, Any


def get_weaviate_v2_test_dataset() -> List[Dict[str, Any]]:
    """
    Dataset v2 - 10 questions basées sur le contenu exact des documents Health

    Chaque cas contient:
    - question: Question posée par l'utilisateur
    - ground_truth: Réponse attendue (extraite des documents sources)
    - category: Catégorie de la question
    - source_doc: Document source contenant la réponse
    - difficulty: easy/medium/hard
    - lang: fr/en
    - contexts: Rempli dynamiquement lors de l'évaluation
    - answer: Rempli par le RAG lors de l'évaluation
    """

    return [
        # =================================================================
        # ASCITES (3 questions)
        # =================================================================
        {
            "question": "What is the scientific name for ascites in broiler chickens?",
            "ground_truth": "Pulmonary hypertension syndrome. Ascites refers to the fluid accumulated in the abdominal cavity (waterbelly) as a consequence of heart failure.",
            "category": "health_ascites_definition",
            "source_doc": "ascites_extracted.txt",
            "lang": "en",
            "difficulty": "easy",
            "expected_source": "weaviate",
            "contexts": [],
            "answer": "",
        },
        {
            "question": "How do temperature fluctuations affect ascites incidence in broilers?",
            "ground_truth": "Birds exposed to fluctuating temperatures (±3°C from average) had significantly more mortalities due to ascites and significantly higher average heart weights compared to birds at constant temperatures. The theoretical thermo-neutral air temperature for fully feathered chickens is 75°F (24°C).",
            "category": "health_ascites_temperature",
            "source_doc": "ascites_extracted.txt",
            "lang": "en",
            "difficulty": "medium",
            "expected_source": "weaviate",
            "contexts": [],
            "answer": "",
        },
        {
            "question": "Quelles sont les mesures préventives pour minimiser l'ascite chez les poulets de chair?",
            "ground_truth": "Pour minimiser l'ascite: (1) Maintenir température constante selon les recommandations, (2) Optimiser la qualité de l'air en bougeant l'air régulièrement et efficacement, (3) Garder la litière sèche pour éviter production d'ammoniaque, (4) Considérer un traitement de litière si problèmes récurrents, (5) Réduire le stress (densité optimale, accès constant à eau/aliment, réduire variations de lumière).",
            "category": "health_ascites_prevention",
            "source_doc": "ascites_extracted.txt",
            "lang": "fr",
            "difficulty": "medium",
            "expected_source": "weaviate",
            "contexts": [],
            "answer": "",
        },
        # =================================================================
        # INFECTIOUS LARYNGOTRACHEITIS - ILT (3 questions)
        # =================================================================
        {
            "question": "How does Infectious Laryngotracheitis (ILT) spread between flocks?",
            "ground_truth": "ILT spreads through respiratory and ocular routes. The latent carrier (recovered or vaccinated birds) can shed virus for periods up to 16 months. Transmission occurs from acutely infected birds and is associated with breakdown in biosecurity including movement of personnel, dead bird disposal, manure disposal, and exchanging farm equipment. Incubation time is 6-12 days, and within a flock ILT spreads within a few days.",
            "category": "health_ilt_transmission",
            "source_doc": "ilt_extracted.txt",
            "lang": "en",
            "difficulty": "medium",
            "expected_source": "weaviate",
            "contexts": [],
            "answer": "",
        },
        {
            "question": "What are the clinical signs of severe ILT in chickens?",
            "ground_truth": "Severe ILT presents with: severe coughing (raspy), gasping followed by expectoration of bloody exudate from trachea, neck extended during violent coughing efforts, bloody beaks/faces/feathers, blood or discharge on walls/cages, mortality usually 10-20% but can reach 50-70%, disease persists for 2-6 weeks (longer than most respiratory viral diseases).",
            "category": "health_ilt_symptoms",
            "source_doc": "ilt_extracted.txt",
            "lang": "en",
            "difficulty": "medium",
            "expected_source": "weaviate",
            "contexts": [],
            "answer": "",
        },
        {
            "question": "Why is ILT vaccination in broilers considered risky?",
            "ground_truth": "CEO (Chicken Embryo Origin) vaccines can revert back to virulence - research shows increased virulence after 10th passage. Vaccinated birds become latent carriers and can shed vaccine virus. The vaccination procedure can reduce production efficiencies. Water vaccination carries risks of rolling reactions. Industry statement: 'We try to avoid vaccination of broilers for ILT like the plague'. Frankly, broilers should not be vaccinated.",
            "category": "health_ilt_vaccination_risks",
            "source_doc": "ilt_extracted.txt",
            "lang": "en",
            "difficulty": "hard",
            "expected_source": "weaviate",
            "contexts": [],
            "answer": "",
        },
        # =================================================================
        # INFECTIOUS BRONCHITIS VIRUS - IBV (2 questions)
        # =================================================================
        {
            "question": "How quickly does Infectious Bronchitis Virus (IBV) spread in a flock?",
            "ground_truth": "IBV spreads rapidly among chickens in a flock. The incubation period is 18 to 36 hours post-infection before clinical signs are apparent. The virus spreads by inhalation of virus droplets produced by coughing or sneezing chickens. IBV is not transmitted vertically through the egg.",
            "category": "health_ibv_transmission",
            "source_doc": "infectious_bronchitis_virus_ibv_extracted.txt",
            "lang": "en",
            "difficulty": "easy",
            "expected_source": "weaviate",
            "contexts": [],
            "answer": "",
        },
        {
            "question": "What are the characteristics of the nephrotropic (renal) form of IBV?",
            "ground_truth": "The renal form of IBV has been diagnosed in Ontario. Nephrotropic strains (Gray, Holte, Australian T strain) have high affinity for kidneys and ureters. This form can contribute to mortality rates as high as 25% in younger flocks. Lesions include swollen and inflamed kidneys, distension of ureters with buildup of urate deposits.",
            "category": "health_ibv_renal_form",
            "source_doc": "infectious_bronchitis_virus_ibv_extracted.txt",
            "lang": "en",
            "difficulty": "hard",
            "expected_source": "weaviate",
            "contexts": [],
            "answer": "",
        },
        # =================================================================
        # FOWL CHOLERA (2 questions)
        # =================================================================
        {
            "question": "What are the main sources of Fowl Cholera transmission?",
            "ground_truth": "Main sources: (1) Chronically infected flocks are the most important reservoir, (2) Humans can carry P. multocida via contaminated clothing/equipment without becoming ill, (3) Wild birds (pigeons, sparrows), rats, and flies can carry the organism, (4) Greatest concentrations found in oral, nasal, and ocular excretions which contaminate feed and water. The disease is not egg-transmitted.",
            "category": "health_fowl_cholera_transmission",
            "source_doc": "fowl_cholera_extracted.txt",
            "lang": "en",
            "difficulty": "medium",
            "expected_source": "weaviate",
            "contexts": [],
            "answer": "",
        },
        {
            "question": "Quelles sont les différences entre les formes aiguës et chroniques du choléra aviaire?",
            "ground_truth": "Forme aiguë: période de maladie très courte, seuls des oiseaux morts peuvent être observés, dépression et léthargie, plumes ébouriffées (fièvre), décharge muqueuse buccale, diarrhée blanchâtre aqueuse, mortalité rapide. Forme chronique: infection localisée dans système respiratoire (poumons, sinus, passages nasaux, tissus oculaires, sacs aériens), peut affecter articulations et tissus mous comme les barbillons. Yeux et barbillons enflés sont des signes classiques.",
            "category": "health_fowl_cholera_clinical_forms",
            "source_doc": "fowl_cholera_extracted.txt",
            "lang": "fr",
            "difficulty": "medium",
            "expected_source": "weaviate",
            "contexts": [],
            "answer": "",
        },
    ]
