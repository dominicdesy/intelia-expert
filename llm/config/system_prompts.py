# -*- coding: utf-8 -*-
"""
system_prompts.py - Helper pour charger et utiliser les prompts système
Version: 5.0.0 - English-only prompts with dynamic language injection
"""

import json
import logging
from pathlib import Path
from utils.types import Dict, Optional, List

logger = logging.getLogger(__name__)

# Language code to display name mapping
LANGUAGE_DISPLAY_NAMES = {
    "fr": "French",
    "en": "English",
    "es": "Spanish",
    "de": "German",
    "it": "Italian",
    "pt": "Portuguese",
    "ar": "Arabic",
    "zh": "Chinese",
    "ja": "Japanese",
    "ko": "Korean",
    "th": "Thai",
    "vi": "Vietnamese",
}


class SystemPromptsManager:
    """
    Gestionnaire centralisé pour les prompts système
    Charge depuis system_prompts.json avec résolution de chemin robuste
    """

    def __init__(self, prompts_path: Optional[str] = None):
        """
        Initialise le gestionnaire de prompts

        Args:
            prompts_path: Chemin vers system_prompts.json (optionnel)
                         Si None, utilise une résolution automatique
        """
        self.prompts_path = self._resolve_config_path(prompts_path)
        self.prompts = self._load_prompts()

        # Log conditionnel pour éviter messages contradictoires
        if self.prompts:
            logger.info(f"✅ SystemPromptsManager chargé depuis {self.prompts_path}")
        else:
            logger.error(
                "❌ SystemPromptsManager non chargé - fichier absent ou invalide"
            )

    def _resolve_config_path(self, prompts_path: Optional[str]) -> Path:
        """
        Résolution robuste du chemin de configuration

        Args:
            prompts_path: Chemin fourni par l'utilisateur ou None

        Returns:
            Path résolu et validé

        Raises:
            FileNotFoundError: Si aucun fichier valide n'est trouvé
        """
        # Si un chemin est fourni, l'utiliser en priorité
        if prompts_path:
            path = Path(prompts_path)
            if path.exists():
                return path.resolve()

        # Chemins à tester par ordre de priorité
        alternative_paths = [
            # 1. Même dossier que ce fichier Python
            Path(__file__).parent / "system_prompts.json",
            # 2. Depuis la racine du projet
            Path.cwd() / "config" / "system_prompts.json",
            # 3. Ancien chemin pour compatibilité
            Path.cwd() / "llm" / "config" / "system_prompts.json",
            # 4. Chemin absolu si déployé dans /app
            Path("/app/config/system_prompts.json"),
        ]

        # Tester chaque chemin
        for alt_path in alternative_paths:
            if alt_path.exists():
                logger.info(f"Fichier trouvé: {alt_path}")
                return alt_path.resolve()

        # Si aucun fichier trouvé, lever une exception explicite
        tested_paths = [prompts_path] if prompts_path else []
        tested_paths.extend([str(p) for p in alternative_paths])

        raise FileNotFoundError(
            "system_prompts.json introuvable.\n"
            "Chemins testés:\n" + "\n".join(f"  - {p}" for p in tested_paths)
        )

    def _load_prompts(self) -> Dict:
        """Charge system_prompts.json avec gestion d'erreurs"""
        try:
            with open(self.prompts_path, "r", encoding="utf-8") as f:
                prompts = json.load(f)
                logger.debug(f"Prompts chargés: {list(prompts.keys())}")
                return prompts
        except FileNotFoundError:
            logger.error(f"❌ Fichier non trouvé: {self.prompts_path}")
            return {}
        except json.JSONDecodeError as e:
            logger.error(f"❌ Erreur JSON dans {self.prompts_path}: {e}")
            return {}
        except Exception as e:
            logger.error(f"❌ Erreur chargement {self.prompts_path}: {e}")
            return {}

    def get_specialized_prompt(
        self, intent_type: str, language: str = "fr"
    ) -> Optional[str]:
        """
        Récupère un prompt spécialisé par type d'intention (avec injection de langue)

        Args:
            intent_type: "metric_query", "environment_setting", etc.
            language: "fr", "en", "es", etc.

        Returns:
            Prompt string avec {language_name} remplacé, ou None

        Examples:
            >>> manager = SystemPromptsManager()
            >>> prompt = manager.get_specialized_prompt("metric_query", "fr")
            >>> "French" in prompt
            True
        """
        specialized = self.prompts.get("specialized_prompts", {})
        prompt_template = specialized.get(intent_type)

        if not prompt_template:
            logger.warning(
                f"Prompt template not found: intent_type={intent_type}"
            )
            return None

        # Inject language_name dynamically
        language_name = LANGUAGE_DISPLAY_NAMES.get(language, language.upper())

        try:
            prompt = prompt_template.format(language_name=language_name)
            return prompt
        except KeyError as e:
            logger.error(f"Missing placeholder in prompt template: {e}")
            return prompt_template

    def get_base_prompt(self, key: str, language: str = "fr") -> Optional[str]:
        """
        Récupère un prompt de base (avec injection de langue)

        Args:
            key: Clé du prompt (ex: "expert_identity", "response_guidelines")
            language: "fr", "en", "es", etc.

        Returns:
            Prompt string avec {language_name} remplacé, ou None
        """
        base_prompts = self.prompts.get("base_prompts", {})
        prompt_template = base_prompts.get(key)

        if not prompt_template:
            logger.warning(f"Base prompt template not found: {key}")
            return None

        # Inject language_name dynamically
        language_name = LANGUAGE_DISPLAY_NAMES.get(language, language.upper())

        try:
            prompt = prompt_template.format(language_name=language_name)
            return prompt
        except KeyError as e:
            logger.error(f"Missing placeholder in base prompt: {e}")
            return prompt_template

    def get_normalization_prompt(
        self, language: str = "fr", is_comparative: bool = False
    ) -> str:
        """
        Récupère le prompt de normalisation de requête (avec injection de langue)

        Args:
            language: "fr", "en", "es", etc.
            is_comparative: Si True, inclut les instructions comparatives

        Returns:
            Prompt complet de normalisation
        """
        normalization = self.prompts.get("query_normalization", {})
        language_name = LANGUAGE_DISPLAY_NAMES.get(language, language.upper())

        # Récupérer le prompt principal
        base_prompt = normalization.get("normalization_prompt", "")

        # Ajouter instructions comparatives si nécessaire
        comparative_instructions = ""
        if is_comparative:
            comparative_instructions = normalization.get("comparative_instructions", "")

        # Substituer les variables
        try:
            prompt = base_prompt.replace(
                "{comparative_instructions}", comparative_instructions
            )
            prompt = prompt.format(language_name=language_name)
            return prompt
        except KeyError as e:
            logger.error(f"Missing placeholder in normalization prompt: {e}")
            return base_prompt

    def get_synthesis_prompt(
        self, synthesis_type: str, language: str = "fr", **kwargs
    ) -> str:
        """
        Récupère un prompt de synthèse avec substitution de variables (avec injection de langue)

        Args:
            synthesis_type: "multi_metric", "comparative", "diagnostic"
            language: "fr", "en", "es", etc.
            **kwargs: Variables à substituer (query, context_by_metric, etc.)

        Returns:
            Prompt avec variables substituées

        Examples:
            >>> prompt = manager.get_synthesis_prompt(
            ...     "multi_metric",
            ...     language="fr",
            ...     query="Quelle est la FCR?",
            ...     context_by_metric="FCR: 1.5"
            ... )
        """
        synthesis_prompts = self.prompts.get("synthesis_prompts", {})
        prompt_template = synthesis_prompts.get(f"{synthesis_type}_synthesis", "")
        language_name = LANGUAGE_DISPLAY_NAMES.get(language, language.upper())

        if not prompt_template:
            logger.warning(f"Synthesis prompt template not found: {synthesis_type}_synthesis")
            return ""

        # Substituer les variables
        try:
            # Inject language_name first
            kwargs_with_lang = {**kwargs, "language_name": language_name}
            return prompt_template.format(**kwargs_with_lang)
        except KeyError as e:
            logger.error(f"Variable manquante dans le prompt: {e}")
            return prompt_template

    def get_error_message(self, error_type: str, language: str = "fr", **kwargs) -> str:
        """
        Récupère un message d'erreur traduit (avec injection de langue)

        Args:
            error_type: "species_mismatch", "unknown_breed", etc.
            language: "fr", "en", "es", etc.
            **kwargs: Variables à substituer

        Returns:
            Message d'erreur formaté
        """
        error_messages = self.prompts.get("error_messages", {})
        message_template = error_messages.get(error_type, "")
        language_name = LANGUAGE_DISPLAY_NAMES.get(language, language.upper())

        if not message_template:
            logger.warning(f"Error message template not found: {error_type}")
            return f"Error: {error_type}"

        try:
            # Inject language_name
            kwargs_with_lang = {**kwargs, "language_name": language_name}
            return message_template.format(**kwargs_with_lang)
        except KeyError as e:
            logger.error(f"Variable manquante dans message erreur: {e}")
            return message_template

    # 🆕 ================================================================
    # NOUVELLES MÉTHODES POUR CONTEXTUALISATION
    # ================================================================

    def get_clarification_template(
        self,
        missing_field: str,
        language: str = "fr",
        suggestions: Optional[List[str]] = None,
    ) -> str:
        """
        🆕 Récupère un template de question de clarification (avec injection de langue)

        Args:
            missing_field: Champ manquant ("breed", "age_days", "sex", etc.)
            language: Langue de la question
            suggestions: Liste de suggestions à inclure (optionnel)

        Returns:
            Question de clarification formatée

        Examples:
            >>> manager = SystemPromptsManager()
            >>> question = manager.get_clarification_template(
            ...     "breed",
            ...     "fr",
            ...     suggestions=["Ross 308", "Cobb 500"]
            ... )
        """
        clarifications = self.prompts.get("clarification_prompts", {})

        # Get template by missing_field key only (language-independent)
        template_key = f"missing_{missing_field}"
        template = clarifications.get(template_key)

        if not template:
            logger.warning(f"Template de clarification non trouvé: {template_key}")
            # Fallback générique
            if language == "fr":
                template = f"Pourriez-vous préciser {missing_field} ?"
            else:
                template = f"Could you specify {missing_field}?"

        # Ajouter suggestions si fournies
        if suggestions and len(suggestions) > 0:
            suggestions_text = ", ".join(suggestions[:5])  # Max 5 suggestions
            if language == "fr":
                template += f"\n\nSuggestions : {suggestions_text}"
            else:
                template += f"\n\nSuggestions: {suggestions_text}"

        return template

    def get_multiple_clarifications_template(
        self, missing_fields: List[str], language: str = "fr"
    ) -> str:
        """
        🆕 Génère un template pour plusieurs champs manquants (avec injection de langue)

        Args:
            missing_fields: Liste des champs manquants
            language: Langue

        Returns:
            Question de clarification combinée
        """
        clarifications = self.prompts.get("clarification_prompts", {})

        # Template pour plusieurs champs (language-independent)
        multi_template = clarifications.get("multiple", "")

        if not multi_template:
            if language == "fr":
                multi_template = "Pour vous aider au mieux, j'ai besoin de quelques précisions :\n{details}"
            else:
                multi_template = (
                    "To help you best, I need a few clarifications:\n{details}"
                )

        # Construire la liste des questions
        details = []
        for field in missing_fields:
            # Récupérer template individuel sans suggestions
            field_question = self.get_clarification_template(field, language)
            # Extraire juste la question (avant les suggestions)
            main_question = field_question.split("\n\n")[0]
            details.append(f"- {main_question}")

        details_text = "\n".join(details)

        return multi_template.format(details=details_text)

    def get_clarification_confirmation(self, language: str = "fr") -> str:
        """
        🆕 Message de confirmation après clarification (avec injection de langue)

        Args:
            language: Langue

        Returns:
            Message de confirmation
        """
        clarifications = self.prompts.get("clarification_prompts", {})

        # Get confirmation template (language-independent)
        confirmation = clarifications.get("confirmation")

        if not confirmation:
            if language == "fr":
                confirmation = (
                    "Merci pour ces précisions ! Je peux maintenant vous répondre."
                )
            else:
                confirmation = (
                    "Thank you for the clarification! I can now answer your question."
                )

        return confirmation

    # ================================================================

    def build_complete_prompt(
        self,
        intent_type: str,
        language: str = "fr",
        include_base_guidelines: bool = True,
    ) -> str:
        """
        Construit un prompt complet avec identité expert + guidelines + spécialisé

        Args:
            intent_type: Type d'intention
            language: Langue
            include_base_guidelines: Inclure les guidelines de base

        Returns:
            Prompt complet combiné
        """
        parts = []

        # 1. Identité expert
        expert_identity = self.get_base_prompt("expert_identity", language)
        if expert_identity:
            parts.append(expert_identity)

        # 2. Prompt spécialisé
        specialized = self.get_specialized_prompt(intent_type, language)
        if specialized:
            parts.append(specialized)

        # 3. Guidelines générales (optionnel)
        if include_base_guidelines:
            guidelines = self.get_base_prompt("response_guidelines", language)
            if guidelines:
                parts.append(guidelines)

        return "\n\n".join(parts)


# ============================================================================
# SINGLETON GLOBAL
# ============================================================================

_global_prompts_manager: Optional[SystemPromptsManager] = None


def get_prompts_manager(
    prompts_path: Optional[str] = None, force_reload: bool = False
) -> SystemPromptsManager:
    """
    Factory pour obtenir l'instance globale du gestionnaire (singleton)

    Args:
        prompts_path: Chemin vers system_prompts.json (optionnel)
        force_reload: Si True, recharge même si existe

    Returns:
        Instance SystemPromptsManager

    Examples:
        >>> manager = get_prompts_manager()
        >>> prompt = manager.get_specialized_prompt("metric_query", "fr")
    """
    global _global_prompts_manager

    if _global_prompts_manager is None or force_reload:
        _global_prompts_manager = SystemPromptsManager(prompts_path)

    return _global_prompts_manager


# ============================================================================
# FONCTIONS HELPER SIMPLIFIÉES
# ============================================================================


def load_system_prompts(prompts_path: Optional[str] = None) -> Dict:
    """
    Charge directement le fichier JSON (pour compatibilité)

    Args:
        prompts_path: Chemin vers system_prompts.json (optionnel)

    Returns:
        Dict complet des prompts
    """
    manager = get_prompts_manager(prompts_path)
    return manager.prompts


def get_prompt(
    intent_type: str, language: str = "fr", prompt_type: str = "specialized"
) -> Optional[str]:
    """
    Fonction helper simplifiée pour récupérer un prompt

    Args:
        intent_type: Type d'intention ou clé du prompt
        language: Langue
        prompt_type: "specialized", "base", "synthesis"

    Returns:
        Prompt string

    Examples:
        >>> prompt = get_prompt("metric_query", "fr", "specialized")
    """
    manager = get_prompts_manager()

    if prompt_type == "specialized":
        return manager.get_specialized_prompt(intent_type, language)
    elif prompt_type == "base":
        return manager.get_base_prompt(intent_type, language)
    elif prompt_type == "synthesis":
        return manager.get_synthesis_prompt(intent_type, language)
    else:
        logger.warning(f"Type de prompt inconnu: {prompt_type}")
        return None


def get_clarification_question(
    missing_field: str, language: str = "fr", suggestions: Optional[List[str]] = None
) -> str:
    """
    🆕 Helper simplifié pour générer une question de clarification

    Args:
        missing_field: Champ manquant
        language: Langue
        suggestions: Suggestions optionnelles

    Returns:
        Question de clarification

    Examples:
        >>> question = get_clarification_question("breed", "fr", ["Ross 308", "Cobb 500"])
    """
    manager = get_prompts_manager()
    return manager.get_clarification_template(missing_field, language, suggestions)


# ============================================================================
# TESTS
# ============================================================================

if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")

    print("=" * 70)
    print("TESTS SYSTEM PROMPTS MANAGER v4.2")
    print("=" * 70)

    # Test 1: Chargement
    print("\nTest 1: Chargement du gestionnaire")
    try:
        manager = get_prompts_manager()
        print("  OK Gestionnaire chargé")
        print(f"  Sections disponibles: {list(manager.prompts.keys())}")
    except Exception as e:
        print(f"  ERREUR: {e}")
        sys.exit(1)

    # Test 2: Prompts spécialisés
    print("\nTest 2: Prompts spécialisés")
    intent_types = ["metric_query", "environment_setting", "diagnosis_triage"]

    for intent in intent_types:
        prompt_fr = manager.get_specialized_prompt(intent, "fr")
        prompt_en = manager.get_specialized_prompt(intent, "en")

        status_fr = "OK" if prompt_fr else "MANQUANT"
        status_en = "OK" if prompt_en else "MANQUANT"

        print(
            f"  {status_fr} {intent} (FR): {len(prompt_fr) if prompt_fr else 0} chars"
        )
        print(
            f"  {status_en} {intent} (EN): {len(prompt_en) if prompt_en else 0} chars"
        )

    # Test 3: Prompts de base
    print("\nTest 3: Prompts de base")
    base_keys = ["expert_identity", "response_guidelines"]

    for key in base_keys:
        prompt_fr = manager.get_base_prompt(key, "fr")
        status = "OK" if prompt_fr else "MANQUANT"
        print(f"  {status} {key} (FR): {len(prompt_fr) if prompt_fr else 0} chars")

    # Test 4: Normalisation
    print("\nTest 4: Prompt de normalisation")
    norm_prompt = manager.get_normalization_prompt("fr", is_comparative=True)
    status = "OK" if norm_prompt and len(norm_prompt) > 100 else "MANQUANT"
    print(f"  {status} Normalisation comparative (FR): {len(norm_prompt)} chars")

    # Test 5: Messages d'erreur
    print("\nTest 5: Messages d'erreur")
    error_msg = manager.get_error_message(
        "species_mismatch",
        "fr",
        breed1="Ross 308",
        species1="broiler",
        breed2="Hy-Line Brown",
        species2="layer",
    )
    status = "OK" if error_msg else "MANQUANT"
    print(f"  {status} Message erreur: {error_msg[:80]}...")

    # Test 6: Prompt complet
    print("\nTest 6: Construction prompt complet")
    complete = manager.build_complete_prompt("metric_query", "fr")
    status = "OK" if complete and len(complete) > 200 else "MANQUANT"
    print(f"  {status} Prompt complet: {len(complete)} chars")

    # 🆕 Test 7: Templates de clarification
    print("\nTest 7: Templates de clarification (NOUVEAU)")

    # Test clarification simple
    clarif_breed = manager.get_clarification_template(
        "breed", "fr", suggestions=["Ross 308", "Cobb 500", "Hubbard"]
    )
    status = "OK" if clarif_breed else "MANQUANT"
    print(f"  {status} Clarification breed (FR):")
    print(f"    {clarif_breed[:100]}...")

    # Test clarification multiple
    clarif_multi = manager.get_multiple_clarifications_template(
        ["breed", "age_days"], "fr"
    )
    status = "OK" if clarif_multi else "MANQUANT"
    print(f"  {status} Clarification multiple (FR):")
    print(f"    {clarif_multi[:100]}...")

    # Test confirmation
    confirmation = manager.get_clarification_confirmation("fr")
    status = "OK" if confirmation else "MANQUANT"
    print(f"  {status} Confirmation: {confirmation}")

    # 🆕 Test 8: Helper function
    print("\nTest 8: Helper function get_clarification_question")
    question = get_clarification_question("breed", "en", ["Ross 308", "Cobb 500"])
    status = "OK" if question else "MANQUANT"
    print(f"  {status} Helper result: {question[:80]}...")

    print("\n" + "=" * 70)
    print("TESTS TERMINÉS - Version 4.2 avec contextualisation")
    print("=" * 70)
