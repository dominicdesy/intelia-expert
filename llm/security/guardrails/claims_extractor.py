# -*- coding: utf-8 -*-
"""
claims_extractor.py - Extraction de différents types de claims (affirmations) depuis les réponses
Ce module fournit des méthodes pour extraire des affirmations factuelles, numériques, qualitatives et comparatives
depuis les réponses générées par le système RAG, permettant leur vérification ultérieure.
"""

import re
import logging
from utils.types import List

logger = logging.getLogger(__name__)


class ClaimsExtractor:
    """
    Classe statique pour l'extraction de différents types d'affirmations (claims) depuis les réponses.

    Cette classe fournit des méthodes pour identifier et extraire:
    - Les affirmations factuelles améliorées (données techniques, métriques, recommandations)
    - Les affirmations numériques (valeurs avec unités)
    - Les affirmations qualitatives (recommandations, jugements)
    - Les affirmations comparatives (comparaisons entre éléments)

    Toutes les méthodes sont statiques et peuvent être utilisées sans instancier la classe.
    """

    # Mots-clés du domaine aviculture pour la détection de contexte technique
    DOMAIN_KEYWORDS = {
        "performance": [
            "fcr",
            "ic",
            "indice",
            "conversion",
            "poids",
            "gain",
            "croissance",
            "rendement",
            "efficacité",
            "productivité",
            "performance",
            "résultats",
            "vitesse",
            "développement",
            "évolution",
            "progression",
        ],
        "sante": [
            "mortalité",
            "morbidité",
            "maladie",
            "pathologie",
            "infection",
            "vaccination",
            "vaccin",
            "prophylaxie",
            "traitement",
            "santé",
            "viabilité",
            "résistance",
            "immunité",
            "symptômes",
            "diagnostic",
        ],
        "nutrition": [
            "aliment",
            "alimentation",
            "nutrition",
            "nutritionnel",
            "protéine",
            "énergie",
            "calories",
            "digestibilité",
            "nutriment",
            "vitamines",
            "minéraux",
            "calcium",
            "phosphore",
            "acides",
            "aminés",
            "fibres",
        ],
        "reproduction": [
            "ponte",
            "œuf",
            "œufs",
            "fertility",
            "fertilité",
            "éclosabilité",
            "couvaison",
            "incubation",
            "éclosion",
            "reproduction",
            "couvoir",
            "hatchabilité",
            "embryon",
            "poussin",
            "poussins",
        ],
        "technique": [
            "ventilation",
            "température",
            "densité",
            "éclairage",
            "logement",
            "bâtiment",
            "poulailler",
            "équipement",
            "installation",
            "système",
            "automatisation",
            "contrôle",
            "régulation",
            "ambiance",
        ],
        "genetique": [
            "lignée",
            "souche",
            "race",
            "ross",
            "cobb",
            "hubbard",
            "isa",
            "lohmann",
            "hy-line",
            "hybride",
            "sélection",
            "amélioration",
            "génétique",
            "héritabilité",
            "consanguinité",
        ],
    }

    @staticmethod
    def _extract_enhanced_factual_claims(response: str) -> List[str]:
        """
        Extrait les affirmations factuelles améliorées depuis une réponse.

        Cette méthode identifie les phrases contenant des informations factuelles vérifiables,
        telles que:
        - Valeurs numériques avec unités (poids, température, pourcentages, durées)
        - Métriques de performance (FCR, mortalité, croissance)
        - Recommandations techniques (valeurs optimales, maximales, minimales)
        - Classifications (lignées génétiques, phases, âges)
        - Paramètres techniques (température, densité, ventilation)

        Args:
            response (str): La réponse complète à analyser

        Returns:
            List[str]: Liste des phrases contenant des affirmations factuelles.
                      Retourne une liste vide si aucune affirmation n'est trouvée
                      ou si la phrase est trop courte (< 15 caractères).

        Example:
            >>> response = "Le poids optimal est de 2.5 kg à 42 jours. La température doit être de 32°C."
            >>> claims = ClaimsExtractor._extract_enhanced_factual_claims(response)
            >>> print(claims)
            ['Le poids optimal est de 2.5 kg à 42 jours.', 'La température doit être de 32°C.']

        Note:
            - Les phrases de moins de 15 caractères sont ignorées pour éviter les fragments
            - Chaque phrase ne peut être comptée qu'une seule fois même si elle correspond
              à plusieurs patterns
            - La détection est insensible à la casse (case-insensitive)
        """
        claims = []

        # Segmentation en phrases avec préservation du contexte
        sentences = re.split(r"(?<=[.!?])\s+", response)

        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 15:
                continue

            # Patterns pour identifier les affirmations factuelles
            factual_patterns = [
                r"\d+[.,]?\d*\s*(?:g|kg|%|j|jour|°C|kcal)",  # Valeurs numériques
                r"(?:poids|fcr|mortalité|ponte|croissance)\s+(?:de|est|atteint)",  # Métriques
                r"(?:recommandé|optimal|maximum|minimum|idéal)\s+(?:est|de)",  # Recommandations
                r"(?:lignée|espèce|phase|âge)\s+\w+",  # Classifications
                r"(?:ross|cobb|hubbard|isa)\s*\d*",  # Lignées génétiques
                r"(?:température|densité|ventilation)\s+(?:de|doit|optimal)",  # Paramètres techniques
            ]

            for pattern in factual_patterns:
                if re.search(pattern, sentence.lower(), re.IGNORECASE):
                    claims.append(sentence)
                    break

        return claims

    @staticmethod
    def _extract_numeric_claims(response: str) -> List[str]:
        """
        Extrait les affirmations numériques depuis une réponse.

        Cette méthode identifie toutes les valeurs numériques accompagnées de leurs unités,
        incluant:
        - Masses: grammes (g), kilogrammes (kg)
        - Pourcentages: %
        - Durées: jours (j, jour, jours), semaines
        - Indicateurs de performance: FCR (Feed Conversion Ratio)
        - Températures: degrés Celsius (°C, degrés)
        - Énergie: kilocalories (kcal), calories

        Args:
            response (str): La réponse complète à analyser

        Returns:
            List[str]: Liste des valeurs numériques extraites avec leurs unités.
                      Par exemple: ["2.5 kg", "42 jours", "15%", "FCR 1.8", "32°C"]

        Example:
            >>> response = "Le poulet atteint 2.5 kg en 42 jours avec un FCR de 1.8 et une mortalité de 3%."
            >>> claims = ClaimsExtractor._extract_numeric_claims(response)
            >>> print(claims)
            ['2.5 kg', '42 jours', '1.8', '3%']

        Note:
            - Les nombres peuvent utiliser le point (.) ou la virgule (,) comme séparateur décimal
            - La détection est insensible à la casse
            - Les valeurs FCR sont capturées avec leur contexte (ex: "FCR 1.8")
            - Plusieurs occurrences de la même unité sont toutes capturées
        """
        patterns = [
            r"\d+[.,]?\d*\s*(?:g|kg|grammes?|kilogrammes?)",
            r"\d+[.,]?\d*\s*%",
            r"\d+[.,]?\d*\s*(?:j|jours?|semaines?)",
            r"FCR.*?\d+[.,]?\d*",
            r"\d+[.,]?\d*\s*(?:°C|degrés?)",
            r"\d+[.,]?\d*\s*(?:kcal|calories?)",
        ]

        claims = []
        for pattern in patterns:
            matches = re.findall(pattern, response, re.IGNORECASE)
            claims.extend(matches)

        return claims

    @staticmethod
    def _extract_qualitative_claims(response: str) -> List[str]:
        """
        Extrait les affirmations qualitatives depuis une réponse.

        Cette méthode identifie les affirmations basées sur des jugements, recommandations
        ou évaluations qualitatives, telles que:
        - Recommandations: recommandé, conseillé, préférable
        - Optimalité: optimal, idéal, meilleur
        - Limites: maximum, minimum, critique
        - Qualité: excellent, supérieur, inférieur
        - Avertissements: éviter, problématique
        - Importance: essentiel, critique

        Args:
            response (str): La réponse complète à analyser

        Returns:
            List[str]: Liste des fragments de texte contenant des affirmations qualitatives.
                      Chaque fragment s'étend du mot qualificatif jusqu'à la fin de la phrase
                      (délimitée par ., !, ou ?).

        Example:
            >>> response = "Il est recommandé d'utiliser cette souche. La ventilation est optimale."
            >>> claims = ClaimsExtractor._extract_qualitative_claims(response)
            >>> print(claims)
            ["recommandé d'utiliser cette souche", "optimale"]

        Note:
            - La détection est insensible à la casse
            - Les fragments capturent le contexte autour du mot qualificatif
            - Plusieurs mots qualificatifs peuvent apparaître dans la même phrase,
              générant plusieurs claims
            - Les mots sont recherchés comme mots entiers (word boundaries)
        """
        qualitative_words = [
            "recommandé",
            "optimal",
            "idéal",
            "maximum",
            "minimum",
            "meilleur",
            "préférable",
            "conseillé",
            "éviter",
            "problématique",
            "excellent",
            "supérieur",
            "inférieur",
            "critique",
            "essentiel",
        ]

        claims = []
        for word in qualitative_words:
            pattern = rf"\b{re.escape(word)}\b[^.!?]*"
            matches = re.findall(pattern, response, re.IGNORECASE)
            claims.extend(matches)

        return claims

    @staticmethod
    def _extract_comparative_claims(response: str) -> List[str]:
        """
        Extrait les affirmations comparatives depuis une réponse.

        Cette méthode identifie les comparaisons entre différents éléments, incluant:
        - Comparaisons quantitatives: "plus/moins ... que"
        - Comparaisons de niveau: "supérieur/inférieur à"
        - Comparaisons qualitatives: "mieux/pire que"
        - Comparaisons relatives: "comparé à", "par rapport à"

        Args:
            response (str): La réponse complète à analyser

        Returns:
            List[str]: Liste des expressions comparatives extraites.
                      Par exemple: ["plus élevé que Ross", "supérieur à 2.5", "comparé à la phase"]

        Example:
            >>> response = "Ross 308 a un GMQ plus élevé que Cobb 500, avec une performance supérieure à 2.5."
            >>> claims = ClaimsExtractor._extract_comparative_claims(response)
            >>> print(claims)
            ['GMQ plus élevé que Cobb', 'performance supérieur à 2']

        Note:
            - La détection est insensible à la casse
            - Les patterns capturent le contexte autour de la comparaison
            - Les comparaisons implicites sans marqueurs explicites ne sont pas détectées
            - \\w+ capture les mots alphanumériques (lettres, chiffres, underscore)
        """
        comparative_patterns = [
            r"\w+\s+(?:plus|moins)\s+\w+\s+que\s+\w+",
            r"\w+\s+(?:supérieur|inférieur)\s+à\s+\w+",
            r"\w+\s+(?:mieux|pire)\s+que\s+\w+",
            r"(?:comparé|par rapport)\s+à\s+\w+",
        ]

        claims = []
        for pattern in comparative_patterns:
            matches = re.findall(pattern, response, re.IGNORECASE)
            claims.extend(matches)

        return claims
