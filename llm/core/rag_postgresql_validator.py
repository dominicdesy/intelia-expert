# -*- coding: utf-8 -*-
"""
rag_postgresql_validator.py - Validateur flexible pour requêtes PostgreSQL
VERSION 4.1: Fusion OpenAI + Contextualisation intelligente
- Préserve tous les champs originaux
- Logs diagnostiques
- Invalidation des métriques invalides
- Auto-détection enrichie dynamique
- 🆕 Messages de clarification conversationnels multilingues
- 🆕 Génération de questions plutôt que de simples messages d'erreur
- 🆕 FUSION avec OpenAI interpretation avant validation
"""

import re
import logging
from typing import Dict, List, Optional, Any

from utils.breeds_registry import get_breeds_registry

logger = logging.getLogger(__name__)


class PostgreSQLValidator:
    """Validateur intelligent avec auto-détection, alternatives et contextualisation"""

    def __init__(self, intents_config_path: str = "llm/config/intents.json"):
        """
        Initialise le validateur avec breeds_registry

        Args:
            intents_config_path: Chemin vers intents.json
        """
        self.logger = logger
        self.breeds_registry = get_breeds_registry(intents_config_path)

        logger.info(
            f"PostgreSQLValidator initialisé avec breeds_registry "
            f"({len(self.breeds_registry.get_all_breeds())} races)"
        )

    def validate_context(
        self, entities: Dict, query: str, language: str = "fr"
    ) -> Dict:
        """
        🆕 Valide le contexte avec fusion OpenAI AVANT validation

        Args:
            entities: Entités extraites (peut contenir _openai_interpretation)
            query: Requête utilisateur
            language: Langue détectée

        Returns:
            Dict avec status et missing_fields après fusion
        """
        # ✅ FUSION: Récupérer les entités OpenAI si disponibles
        openai_interp = entities.get("_openai_interpretation", {})

        # Enrichir avec OpenAI AVANT validation
        if openai_interp:
            if not entities.get("age_days") and "age_days" in openai_interp:
                entities["age_days"] = openai_interp["age_days"]
                logger.info(
                    f"✅ Age récupéré depuis OpenAI: {openai_interp['age_days']}"
                )

            if not entities.get("breed") and "breed" in openai_interp:
                entities["breed"] = openai_interp["breed"]
                logger.info(
                    f"✅ Breed récupéré depuis OpenAI: {openai_interp['breed']}"
                )

            if not entities.get("metric_type") and "metric_type" in openai_interp:
                entities["metric_type"] = openai_interp["metric_type"]
                logger.info(
                    f"✅ Metric récupéré depuis OpenAI: {openai_interp['metric_type']}"
                )

        # MAINTENANT valider ce qui manque vraiment
        missing_fields = []
        if not entities.get("breed"):
            missing_fields.append("breed")
        if not entities.get("age_days"):  # Ne sera plus None car fusionné!
            missing_fields.append("age")
        if not entities.get("metric") and not entities.get("metric_type"):
            missing_fields.append("metric")

        return {
            "status": "complete" if not missing_fields else "needs_fallback",
            "missing_fields": missing_fields,
            "enhanced_entities": entities,
        }

    def flexible_query_validation(
        self, query: str, entities: Dict[str, Any], language: str = "fr"
    ) -> Dict[str, Any]:
        """
        Validation flexible qui essaie de compléter les requêtes incomplètes

        🆕 VERSION 4.1: Fusion avec OpenAI interpretation AVANT validation

        CORRECTION FINALE: Commence toujours par les entités ORIGINALES,
        puis enrichit SEULEMENT les champs manquants avec auto-détection.
        Cela garantit que 'sex' et autres champs du comparison_handler sont préservés.

        Args:
            query: Requête utilisateur
            entities: Entités extraites (peut contenir _openai_interpretation)
            language: Langue détectée (fr, en, es, etc.)

        Returns:
            Dict avec status: "complete" | "incomplete_but_processable" | "needs_fallback"
        """

        entities = entities or {}
        missing = []
        suggestions = []

        # 🔥 LOG CRITIQUE #1 : Ce qui ARRIVE au validator
        logger.debug(f"🔍 VALIDATOR INPUT entities: {entities}")
        logger.debug(
            f"🔍 VALIDATOR INPUT - 'sex' present: {'sex' in entities}, value: {entities.get('sex')}"
        )
        logger.debug(
            f"🔍 VALIDATOR INPUT - 'breed' present: {'breed' in entities}, value: {entities.get('breed')}"
        )
        logger.debug(
            f"🔍 VALIDATOR INPUT - 'age_days' present: {'age_days' in entities}, value: {entities.get('age_days')}"
        )
        logger.debug(
            f"🔍 VALIDATOR INPUT - 'explicit_sex_request' present: {'explicit_sex_request' in entities}, value: {entities.get('explicit_sex_request')}"
        )
        logger.debug(
            f"🔍 VALIDATOR INPUT - 'metric_type' present: {'metric_type' in entities}, value: {entities.get('metric_type')}"
        )

        # 🟢 CORRECTION CRITIQUE: Copier TOUTES les entités originales en priorité
        # Cela préserve automatiquement 'sex', 'explicit_sex_request', etc.
        enhanced_entities = dict(entities) if entities else {}

        # 🆕 FUSION OpenAI: Récupérer les entités OpenAI si disponibles
        openai_interp = enhanced_entities.get("_openai_interpretation", {})

        if openai_interp:
            logger.debug(f"🔍 OpenAI interpretation trouvée: {openai_interp}")

            # Enrichir UNIQUEMENT les champs manquants avec OpenAI
            if not enhanced_entities.get("age_days") and "age_days" in openai_interp:
                enhanced_entities["age_days"] = openai_interp["age_days"]
                logger.info(
                    f"✅ Age récupéré depuis OpenAI: {openai_interp['age_days']}"
                )

            if not enhanced_entities.get("breed") and "breed" in openai_interp:
                enhanced_entities["breed"] = openai_interp["breed"]
                logger.info(
                    f"✅ Breed récupéré depuis OpenAI: {openai_interp['breed']}"
                )

            if (
                not enhanced_entities.get("metric_type")
                and "metric_type" in openai_interp
            ):
                enhanced_entities["metric_type"] = openai_interp["metric_type"]
                logger.info(
                    f"✅ Metric récupéré depuis OpenAI: {openai_interp['metric_type']}"
                )

        # 🔥 LOG CRITIQUE #2 : Juste après dict(entities) et fusion OpenAI
        logger.debug(
            f"🔍 enhanced_entities AFTER dict(entities) + OpenAI fusion: {enhanced_entities}"
        )
        logger.debug(
            f"🔍 AFTER COPY - 'sex' present: {'sex' in enhanced_entities}, value: {enhanced_entities.get('sex')}"
        )
        logger.debug(
            f"🔍 AFTER COPY - 'explicit_sex_request' present: {'explicit_sex_request' in enhanced_entities}"
        )
        logger.debug(
            f"🔍 AFTER COPY - 'metric_type' present: {'metric_type' in enhanced_entities}, value: {enhanced_entities.get('metric_type')}"
        )

        # 🟡 NOUVEAU : Invalider metric_type si c'est 'as_hatched' ou autre valeur invalide
        # ✅ CORRECTION: Vérifier les DEUX champs
        metric = enhanced_entities.get("metric_type") or enhanced_entities.get("metric")
        if metric:
            metric_lower = str(metric).lower().strip()
            invalid_metrics = [
                "as_hatched",
                "as-hatched",
                "mixed",
                "none",
                "",
                "male",
                "female",
            ]
            if metric_lower in invalid_metrics:
                logger.warning(
                    f"⚠️ metric invalide '{metric}' → None, auto-détection activée"
                )
                enhanced_entities["metric_type"] = None
                enhanced_entities["metric"] = None  # ✅ Effacer les deux

        # 🟢 Auto-détection breed SEULEMENT si absent dans les entités originales ET OpenAI
        if not enhanced_entities.get("breed"):
            logger.debug("🔍 Breed ABSENT, auto-detecting from query...")
            detected_breed = self._detect_breed_from_query(query)
            if detected_breed:
                enhanced_entities["breed"] = detected_breed
                logger.debug(f"✅ Auto-detected breed: {detected_breed}")
            else:
                logger.debug("❌ No breed detected in query")
                missing.append("breed")
                # 🆕 Suggestion conversationnelle selon la langue
                suggestions.append(self._get_breed_suggestion(language))
        else:
            logger.debug(
                f"🔍 Breed PRESENT: '{enhanced_entities.get('breed')}', skipping auto-detection"
            )

        # 🟢 Auto-détection age SEULEMENT si absent dans les entités originales ET OpenAI
        if not enhanced_entities.get("age_days"):
            logger.debug("🔍 Age ABSENT, auto-detecting from query...")
            detected_age = self._detect_age_from_query(query)
            if detected_age:
                enhanced_entities["age_days"] = detected_age
                logger.debug(f"✅ Auto-detected age: {detected_age} days")
            else:
                logger.debug("❌ No age detected in query")
                # Pour certaines requêtes, l'âge n'est pas critique
                if any(
                    word in query.lower()
                    for word in [
                        "recommande",
                        "meilleur",
                        "compare",
                        "général",
                        "recommend",
                        "best",
                        "compare",
                        "general",
                    ]
                ):
                    logger.debug("🔍 General query, age not critical")
                    pass  # Requête générale - pas besoin d'âge spécifique
                else:
                    missing.append("age")
                    # 🆕 Suggestion conversationnelle selon la langue
                    suggestions.append(self._get_age_suggestion(language))
        else:
            logger.debug(
                f"🔍 Age PRESENT: '{enhanced_entities.get('age_days')}', skipping auto-detection"
            )

        # 🟡 AMÉLIORÉ : Auto-détection metric avec vérification de 'metric' OU 'metric_type'
        if not enhanced_entities.get("metric_type") and not enhanced_entities.get(
            "metric"
        ):
            logger.debug("🔍 Metric ABSENT, auto-detecting from query...")
            detected_metric = self._auto_detect_metric_type(query)
            if detected_metric:
                enhanced_entities["metric_type"] = detected_metric
                logger.debug(f"✅ Auto-detected metric: {detected_metric}")
            else:
                logger.debug("❌ No metric detected in query")
                missing.append("metric")
                suggestions.append(self._get_metric_suggestion(language))
        else:
            # Métrique présente (soit metric, soit metric_type)
            metric_value = enhanced_entities.get("metric") or enhanced_entities.get(
                "metric_type"
            )
            logger.debug(
                f"🔍 Metric PRESENT: '{metric_value}', skipping auto-detection"
            )

        # 🔥 LOG CRITIQUE #3 : Avant de retourner
        logger.debug(f"🔍 enhanced_entities FINAL before return: {enhanced_entities}")
        logger.debug(
            f"🔍 FINAL - 'sex' present: {'sex' in enhanced_entities}, value: {enhanced_entities.get('sex')}"
        )
        logger.debug(
            f"🔍 FINAL - 'explicit_sex_request' present: {'explicit_sex_request' in enhanced_entities}, value: {enhanced_entities.get('explicit_sex_request')}"
        )
        logger.debug(
            f"🔍 FINAL - 'metric_type' present: {'metric_type' in enhanced_entities}, value: {enhanced_entities.get('metric_type')}"
        )

        # 🔥 VÉRIFICATION CRITIQUE : Comparaison INPUT vs OUTPUT
        input_keys = set(entities.keys())
        output_keys = set(enhanced_entities.keys())
        lost_keys = input_keys - output_keys

        if lost_keys:
            logger.error(f"❌❌❌ VALIDATOR LOST KEYS: {lost_keys}")
            logger.error(f"❌ INPUT had: {input_keys}")
            logger.error(f"❌ OUTPUT has: {output_keys}")

            # 🟢 CORRECTION : RESTAURER les champs perdus
            for key in lost_keys:
                enhanced_entities[key] = entities[key]
                logger.warning(f"⚠️ RESTORED lost key '{key}': {entities[key]}")

            logger.debug(f"🔍 enhanced_entities AFTER restoration: {enhanced_entities}")
        else:
            logger.debug("✅ No keys lost, all fields preserved")

        # 🟢 Log de debug pour vérifier que tous les champs sont préservés
        if entities:
            preserved_fields = [k for k in entities.keys() if k in enhanced_entities]
            if preserved_fields:
                logger.debug(f"✅ Preserved original fields: {preserved_fields}")

        # Déterminer le statut
        if not missing:
            logger.debug("✅ Validation complete, returning enhanced_entities")
            return {"status": "complete", "enhanced_entities": enhanced_entities}

        elif len(missing) <= 1 and ("breed" not in missing):
            # 🆕 CORRECTION CRITIQUE : Vérifier si l'âge manquant est critique
            if "age" in missing:
                # Pour des métriques qui varient fortement avec l'âge, c'est critique
                critical_metrics = [
                    "weight",
                    "body_weight",
                    "poids",
                    "feed_conversion",
                    "conversion",
                    "fcr",
                    "daily_gain",
                    "gain",
                ]
                metric = enhanced_entities.get("metric_type", "").lower()
                metric_name = enhanced_entities.get("metric", "").lower()

                # Vérifier si la métrique est critique
                is_critical_metric = any(m in metric for m in critical_metrics) or any(
                    m in metric_name for m in critical_metrics
                )

                if is_critical_metric:
                    logger.debug(
                        f"❌ Age manquant pour métrique critique '{metric}' - needs_fallback"
                    )
                    helpful_message = self._generate_conversational_question(
                        query, missing, suggestions, language
                    )
                    return {
                        "status": "needs_fallback",
                        "missing": missing,
                        "suggestions": suggestions,
                        "helpful_message": helpful_message,
                    }

            # Si ce n'est pas critique (ex: mortalité générale), on peut traiter
            logger.debug(f"⚠️ Validation incomplete but processable, missing: {missing}")
            return {
                "status": "incomplete_but_processable",
                "message": f"Autoriser la requête sans {', '.join(missing)} spécifique",
                "enhanced_entities": enhanced_entities,
                "missing": missing,
            }

        else:
            # Trop d'informations manquantes - 🆕 Message conversationnel
            logger.debug(f"❌ Validation needs fallback, missing: {missing}")
            helpful_message = self._generate_conversational_question(
                query, missing, suggestions, language
            )
            return {
                "status": "needs_fallback",
                "missing": missing,
                "suggestions": suggestions,
                "helpful_message": helpful_message,
            }

    def _get_breed_suggestion(self, language: str) -> str:
        """Retourne une suggestion pour la race selon la langue"""
        suggestions = {
            "fr": "Quelle race/souche élevez-vous ? (Ross 308, Cobb 500, Hubbard, etc.)",
            "en": "Which breed/strain are you raising? (Ross 308, Cobb 500, Hubbard, etc.)",
            "es": "¿Qué raza/cepa está criando? (Ross 308, Cobb 500, Hubbard, etc.)",
        }
        return suggestions.get(language, suggestions["fr"])

    def _get_age_suggestion(self, language: str) -> str:
        """Retourne une suggestion pour l'âge selon la langue"""
        suggestions = {
            "fr": "À quel âge (en jours) souhaitez-vous cette information ?",
            "en": "At what age (in days) would you like this information?",
            "es": "¿A qué edad (en días) desea esta información?",
        }
        return suggestions.get(language, suggestions["fr"])

    def _get_metric_suggestion(self, language: str) -> str:
        """Retourne une suggestion pour la métrique selon la langue"""
        suggestions = {
            "fr": "Quelle métrique vous intéresse ? (poids vif, conversion alimentaire, gain quotidien, mortalité)",
            "en": "Which metric are you interested in? (body weight, feed conversion, daily gain, mortality)",
            "es": "¿Qué métrica le interesa? (peso vivo, conversión alimenticia, ganancia diaria, mortalidad)",
        }
        return suggestions.get(language, suggestions["fr"])

    def _generate_conversational_question(
        self,
        query: str,
        missing: List[str],
        suggestions: List[str],
        language: str = "fr",
    ) -> str:
        """
        🆕 NOUVEAU: Génère une question de clarification conversationnelle

        Args:
            query: Requête originale
            missing: Champs manquants
            suggestions: Suggestions détaillées (non utilisées directement)
            language: Langue de la réponse

        Returns:
            Question conversationnelle formatée
        """

        # Templates d'introduction selon la langue
        intros = {
            "fr": "Pour vous donner une réponse précise, j'ai besoin de quelques informations supplémentaires.",
            "en": "To provide you with an accurate answer, I need some additional information.",
            "es": "Para darle una respuesta precisa, necesito información adicional.",
        }

        # Templates pour plusieurs champs manquants
        multiple_intros = {
            "fr": "Pourriez-vous préciser :",
            "en": "Could you please specify:",
            "es": "¿Podría especificar:",
        }

        intro = intros.get(language, intros["fr"])

        # 🔧 CORRECTION : Générer les bonnes suggestions basées sur les champs MISSING
        contextual_suggestions = []
        for field in missing:
            if "breed" in field.lower() or "race" in field.lower():
                contextual_suggestions.append(self._get_breed_suggestion(language))
            elif "age" in field.lower() or "âge" in field.lower():
                contextual_suggestions.append(self._get_age_suggestion(language))
            elif "metric" in field.lower() or "métrique" in field.lower():
                contextual_suggestions.append(self._get_metric_suggestion(language))

        # Construction de la question
        parts = [intro]

        if len(contextual_suggestions) > 1:
            # Plusieurs champs manquants
            parts.append(f"\n\n{multiple_intros.get(language, multiple_intros['fr'])}")
            for suggestion in contextual_suggestions:
                parts.append(f"\n• {suggestion}")
        elif len(contextual_suggestions) == 1:
            # Un seul champ manquant
            parts.append(f"\n\n{contextual_suggestions[0]}")
        else:
            # Fallback si aucune suggestion générée
            parts.append("\n\nVeuillez fournir les informations manquantes.")

        return "".join(parts)

    def _generate_validation_help_message(
        self, query: str, missing: List[str], suggestions: List[str]
    ) -> str:
        """
        Génère un message d'aide pour validation
        🆕 DÉPRÉCIÉE: Utiliser _generate_conversational_question à la place
        """
        return (
            f"Informations manquantes pour traiter votre requête : {', '.join(missing)}. "
            f"Suggestions : {' '.join(suggestions)}"
        )

    def validate_and_enhance(self, entities: Dict, query: str) -> Dict:
        """
        Valider et enrichir les entités
        Méthode alternative avec invalidation explicite des métriques invalides
        """

        enhanced = dict(entities) if entities else {}
        missing = []
        message = ""

        # 🟡 NOUVEAU : Invalider metric_type si c'est 'as_hatched' ou valeur invalide
        metric = enhanced.get("metric_type")
        if metric:
            metric_lower = str(metric).lower().strip()
            invalid_metrics = [
                "as_hatched",
                "as-hatched",
                "mixed",
                "none",
                "",
                "male",
                "female",
            ]
            if metric_lower in invalid_metrics:
                self.logger.warning(
                    f"⚠️ metric_type invalide '{metric}' → None, auto-détection activée"
                )
                enhanced["metric_type"] = None

        # Si metric_type est None, activer auto-détection
        if not enhanced.get("metric_type"):
            self.logger.debug("🔍 Metric ABSENT, auto-detecting from query...")
            detected = self._auto_detect_metric_type(query)
            if detected:
                enhanced["metric_type"] = detected
                self.logger.debug(f"✅ Auto-detected metric: {detected}")
            else:
                self.logger.debug("❌ No metric detected in query")
                missing.append("metric_type")
        else:
            self.logger.debug(
                f"🔍 Metric PRESENT: '{enhanced['metric_type']}', skipping auto-detection"
            )

        # Vérifier breed avec breeds_registry
        if not enhanced.get("breed"):
            detected_breed = self._detect_breed_from_query(query)
            if detected_breed:
                enhanced["breed"] = detected_breed
            else:
                missing.append("breed")

        # Vérifier age
        if not enhanced.get("age_days"):
            detected_age = self._detect_age_from_query(query)
            if detected_age:
                enhanced["age_days"] = detected_age
            else:
                missing.append("age_days")

        # Déterminer statut
        if not missing:
            status = "complete"
        elif len(missing) <= 1:
            status = "incomplete_but_processable"
            message = f"Informations manquantes: {', '.join(missing)}"
        else:
            status = "needs_fallback"
            message = f"Trop d'informations manquantes: {', '.join(missing)}"

        return {
            "status": status,
            "enhanced_entities": enhanced,
            "missing": missing,
            "message": message,
        }

    def _detect_breed_from_query(self, query: str) -> Optional[str]:
        """
        Détecte la race dans le texte de la requête via breeds_registry
        Version 3.1: CORRIGÉ - get_all_breeds() retourne Set[str], pas des objets
        """
        query_lower = query.lower()

        # Itérer sur toutes les races connues (Set[str] de noms canoniques)
        for breed_name in self.breeds_registry.get_all_breeds():
            # breed_name est une string comme "ross 308", "cobb 500"

            # Vérifier le nom canonique
            if breed_name.lower() in query_lower:
                logger.debug(f"✅ Breed détecté (canonical): {breed_name}")
                return breed_name

            # Récupérer et vérifier les aliases pour cette race
            aliases = self.breeds_registry.get_aliases(breed_name)
            for alias in aliases:
                if alias.lower() in query_lower:
                    logger.debug(f"✅ Breed détecté (alias '{alias}'): {breed_name}")
                    return breed_name

        logger.debug("❌ Aucun breed détecté")
        return None

    def _detect_age_from_query(self, query: str) -> Optional[int]:
        """Détecte l'âge dans le texte de la requête"""
        age_patterns = [
            r"à\s+(\d+)\s+jours?",
            r"(\d+)\s+jours?",
            r"(\d+)\s*j\b",
            r"(\d+)\s+semaines?",
            r"at\s+(\d+)\s+days?",
        ]

        for pattern in age_patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                age = int(match.group(1))
                if "semaine" in pattern.lower() or "week" in pattern.lower():
                    age = age * 7
                return age

        return None

    def _detect_metric_from_query(self, query: str) -> Optional[str]:
        """
        Détecte le type de métrique dans la requête
        VERSION BASIQUE - À utiliser pour compatibilité descendante
        """
        query_lower = query.lower()

        metric_keywords = {
            "weight": ["poids", "weight", "body weight"],
            "feed_conversion": [
                "conversion",
                "fcr",
                "ic",
                "feed conversion",
                "conversion alimentaire",
            ],
            "mortality": ["mortalité", "mortality", "viabilité", "viability"],
        }

        for metric_type, keywords in metric_keywords.items():
            if any(keyword in query_lower for keyword in keywords):
                return metric_type

        return None

    def _auto_detect_metric_type(self, query: str) -> Optional[str]:
        """
        Détecter automatiquement le type de métrique depuis la requête
        VERSION ENRICHIE - Cohérente avec query_preprocessor
        """

        query_lower = query.lower()

        # 🟡 Patterns étendus (cohérents avec query_preprocessor)
        metric_patterns = {
            # Poids
            "poids": "body_weight",
            "weight": "body_weight",
            "poids vif": "body_weight",
            "body weight": "body_weight",
            # Gain
            "gain quotidien": "daily_weight_gain",
            "gain moyen quotidien": "average_daily_gain",
            "gain moyen": "average_daily_gain",
            "gmq": "average_daily_gain",
            "gmo": "average_daily_gain",
            "adg": "average_daily_gain",
            # Consommation
            "consommation cumulée": "cumulative_feed_intake",
            "consommation cumulative": "cumulative_feed_intake",
            "consommation totale": "cumulative_feed_intake",
            "aliment cumulé": "cumulative_feed_intake",
            # Conversion
            "indice de consommation": "feed_conversion_ratio",
            "conversion alimentaire": "feed_conversion_ratio",
            "ic": "feed_conversion_ratio",
            "fcr": "feed_conversion_ratio",
            # Mortalité
            "mortalité": "mortality",
            "taux de mortalité": "mortality",
            "viabilité": "mortality",
            "mortality": "mortality",
        }

        # 🟡 Chercher par ordre de spécificité (plus long d'abord)
        for pattern in sorted(metric_patterns.keys(), key=len, reverse=True):
            if pattern in query_lower:
                detected = metric_patterns[pattern]
                self.logger.debug(
                    f"✅ Métrique auto-détectée: '{pattern}' → {detected}"
                )
                return detected

        self.logger.debug("❌ Aucune métrique détectée automatiquement")
        return None

    def check_data_availability_flexible(
        self, entities: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Vérifie si les données demandées sont disponibles
        Version 3.1: Utilise breeds_registry pour obtenir les plages d'âges
        """
        breed = entities.get("breed", "").lower() if entities.get("breed") else None
        age_days = entities.get("age_days")

        if not breed or not age_days:
            return {"available": True}

        age = int(age_days) if isinstance(age_days, (int, str)) else None
        if not age:
            return {"available": True}

        # Utiliser breeds_registry pour valider la race
        is_valid, canonical_breed = self.breeds_registry.validate_breed(breed)

        if not is_valid:
            return {
                "available": False,
                "error": f"Race non reconnue: {breed}",
                "helpful_response": f"La race '{breed}' n'est pas dans notre base de données.",
            }

        # Plages d'âges génériques par species
        species = self.breeds_registry.get_species(canonical_breed)

        age_ranges = {
            "broiler": (0, 56),
            "layer": (0, 600),  # Layers ont une durée de vie plus longue
            "breeder": (0, 60),
        }

        if species in age_ranges:
            min_age, max_age = age_ranges[species]

            if min_age <= age <= max_age:
                return {"available": True}
            else:
                # Proposer des alternatives
                alternatives = []
                if age < min_age:
                    alternatives.append(f"{min_age} jours (âge minimum)")
                if age > max_age:
                    alternatives.append(f"{max_age} jours (âge maximum)")

                return {
                    "available": False,
                    "alternatives": alternatives,
                    "helpful_response": f"Données non disponibles pour {canonical_breed} à {age} jours. Alternatives : {', '.join(alternatives)}",
                }

        return {"available": True}


# Tests unitaires
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    print("=" * 70)
    print("🧪 TESTS POSTGRESQL VALIDATOR - VERSION FUSION OPENAI")
    print("=" * 70)

    validator = PostgreSQLValidator()

    # Test 1: Détection breed
    print("\n🔍 Test 1: Détection de breed depuis requête")
    test_queries = [
        "Quel est le poids du Cobb 500 à 21 jours ?",
        "FCR ross308 à 35j",
        "Performance ISA Brown",
        "Hubbard classic 42 jours",
    ]

    for query in test_queries:
        detected = validator._detect_breed_from_query(query)
        print(f"  Query: {query}")
        print(f"  → Breed: {detected}")

    # Test 2: Validation avec enrichissement
    print("\n✅ Test 2: Validation et enrichissement")
    test_cases = [
        {
            "query": "Poids à 21 jours pour Cobb 500",
            "entities": {"breed": "cobb 500"},
        },
        {
            "query": "FCR du Ross 308",
            "entities": {},
        },
        {
            "query": "Mortalité",
            "entities": {"age_days": 35},
        },
    ]

    for test in test_cases:
        print(f"\n  Query: {test['query']}")
        print(f"  Input entities: {test['entities']}")

        result = validator.flexible_query_validation(test["query"], test["entities"])

        print(f"  → Status: {result['status']}")
        if "enhanced_entities" in result:
            print(f"  → Enhanced: {result['enhanced_entities']}")

    # 🆕 Test 3: Messages de clarification multilingues
    print("\n🆕 Test 3: Messages de clarification conversationnels")
    test_clarifications = [
        {
            "query": "Quel est le poids d'un poulet de 12 jours ?",
            "entities": {},
            "language": "fr",
        },
        {
            "query": "What is the weight at 12 days?",
            "entities": {},
            "language": "en",
        },
        {
            "query": "¿Cuál es el peso?",
            "entities": {"age_days": 15},
            "language": "es",
        },
    ]

    for test in test_clarifications:
        print(f"\n  Query: {test['query']}")
        print(f"  Language: {test['language']}")

        result = validator.flexible_query_validation(
            test["query"], test["entities"], test["language"]
        )

        print(f"  → Status: {result['status']}")
        if result["status"] == "needs_fallback":
            print(f"  → Question: {result['helpful_message']}")

    # 🆕 Test 4: Fusion avec OpenAI interpretation
    print("\n🆕 Test 4: Fusion avec OpenAI interpretation")
    test_openai_fusion = [
        {
            "query": "Quel est le poids?",
            "entities": {
                "_openai_interpretation": {
                    "breed": "Ross 308",
                    "age_days": 21,
                    "metric_type": "body_weight",
                }
            },
            "language": "fr",
        },
        {
            "query": "FCR comparison",
            "entities": {
                "sex": "male",
                "_openai_interpretation": {"breed": "Cobb 500", "age_days": 35},
            },
            "language": "en",
        },
    ]

    for test in test_openai_fusion:
        print(f"\n  Query: {test['query']}")
        print(f"  Input entities: {test['entities']}")

        result = validator.flexible_query_validation(
            test["query"], test["entities"], test["language"]
        )

        print(f"  → Status: {result['status']}")
        if "enhanced_entities" in result:
            print(f"  → Enhanced: {result['enhanced_entities']}")
            print(f"  → Sex preserved: {result['enhanced_entities'].get('sex')}")

    # 🆕 Test 5: validate_context avec fusion
    print("\n🆕 Test 5: validate_context avec fusion OpenAI")
    test_validate_context = {
        "query": "Compare weight",
        "entities": {
            "sex": "female",
            "_openai_interpretation": {
                "breed": "Ross 308",
                "age_days": 28,
                "metric_type": "body_weight",
            },
        },
        "language": "en",
    }

    print(f"\n  Query: {test_validate_context['query']}")
    print(f"  Input entities: {test_validate_context['entities']}")

    result = validator.validate_context(
        test_validate_context["entities"],
        test_validate_context["query"],
        test_validate_context["language"],
    )

    print(f"  → Status: {result['status']}")
    print(f"  → Missing fields: {result.get('missing_fields', [])}")
    print(f"  → Enhanced entities: {result['enhanced_entities']}")
    print(f"  → Sex preserved: {result['enhanced_entities'].get('sex')}")

    print("\n" + "=" * 70)
    print("✅ TESTS TERMINÉS - PostgreSQL Validator avec Fusion OpenAI")
    print("=" * 70)
