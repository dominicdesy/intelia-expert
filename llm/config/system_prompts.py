# -*- coding: utf-8 -*-
"""
system_prompts.py - Helper pour charger et utiliser les prompts système
Version: 1.1.0 - Résolution de chemin robuste
"""

import json
import logging
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)


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
        Récupère un prompt spécialisé par type d'intention

        Args:
            intent_type: "metric_query", "environment_setting", etc.
            language: "fr" ou "en"

        Returns:
            Prompt string ou None

        Examples:
            >>> manager = SystemPromptsManager()
            >>> prompt = manager.get_specialized_prompt("metric_query", "fr")
        """
        specialized = self.prompts.get("specialized_prompts", {})
        intent_prompts = specialized.get(intent_type, {})

        prompt = intent_prompts.get(language)

        if not prompt:
            logger.warning(
                f"Prompt non trouvé: intent_type={intent_type}, language={language}"
            )

        return prompt

    def get_base_prompt(self, key: str, language: str = "fr") -> Optional[str]:
        """
        Récupère un prompt de base

        Args:
            key: Clé du prompt (ex: "expert_identity", "response_guidelines")
            language: "fr" ou "en"

        Returns:
            Prompt string ou None
        """
        base_prompts = self.prompts.get("base_prompts", {})
        prompt_key = f"{key}_{language}"

        prompt = base_prompts.get(prompt_key)

        if not prompt:
            logger.warning(f"Base prompt non trouvé: {prompt_key}")

        return prompt

    def get_normalization_prompt(
        self, language: str = "fr", is_comparative: bool = False
    ) -> str:
        """
        Récupère le prompt de normalisation de requête

        Args:
            language: "fr" ou "en"
            is_comparative: Si True, inclut les instructions comparatives

        Returns:
            Prompt complet de normalisation
        """
        normalization = self.prompts.get("query_normalization", {})

        # Récupérer le prompt principal
        prompt_key = f"normalization_prompt_{language}"
        base_prompt = normalization.get(prompt_key, "")

        # Ajouter instructions comparatives si nécessaire
        comparative_instructions = ""
        if is_comparative:
            comp_key = f"comparative_instructions_{language}"
            comparative_instructions = normalization.get(comp_key, "")

        # Substituer la variable {comparative_instructions}
        return base_prompt.replace(
            "{comparative_instructions}", comparative_instructions
        )

    def get_synthesis_prompt(
        self, synthesis_type: str, language: str = "fr", **kwargs
    ) -> str:
        """
        Récupère un prompt de synthèse avec substitution de variables

        Args:
            synthesis_type: "multi_metric", "comparative", "diagnostic"
            language: "fr" ou "en"
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
        prompt_key = f"{synthesis_type}_synthesis_{language}"

        prompt_template = synthesis_prompts.get(prompt_key, "")

        if not prompt_template:
            logger.warning(f"Synthesis prompt non trouvé: {prompt_key}")
            return ""

        # Substituer les variables
        try:
            return prompt_template.format(**kwargs)
        except KeyError as e:
            logger.error(f"Variable manquante dans le prompt: {e}")
            return prompt_template

    def get_error_message(self, error_type: str, language: str = "fr", **kwargs) -> str:
        """
        Récupère un message d'erreur traduit

        Args:
            error_type: "species_mismatch", "unknown_breed", etc.
            language: "fr" ou "en"
            **kwargs: Variables à substituer

        Returns:
            Message d'erreur formaté
        """
        error_messages = self.prompts.get("error_messages", {})
        msg_key = f"{error_type}_{language}"

        message = error_messages.get(msg_key, "")

        if not message:
            logger.warning(f"Message d'erreur non trouvé: {msg_key}")
            return f"Error: {error_type}"

        try:
            return message.format(**kwargs)
        except KeyError as e:
            logger.error(f"Variable manquante dans message erreur: {e}")
            return message

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


# ============================================================================
# TESTS
# ============================================================================

if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")

    print("=" * 70)
    print("TESTS SYSTEM PROMPTS MANAGER")
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

    print("\n" + "=" * 70)
    print("TESTS TERMINÉS")
    print("=" * 70)
