# -*- coding: utf-8 -*-
"""
breeds_registry.py - Gestionnaire centralisé du registre des races
Charge et utilise intents.json comme source unique de vérité
Version: 1.0.0
"""

import json
import logging
from pathlib import Path
from typing import Optional, List, Dict, Tuple, Set
from functools import lru_cache

logger = logging.getLogger(__name__)


class BreedsRegistry:
    """
    Gestionnaire centralisé pour toutes les informations sur les races
    Source unique de vérité basée sur intents.json

    Fonctionnalités:
    - Normalisation des noms de races
    - Classification par species (broiler/layer/breeder)
    - Validation de compatibilité pour comparaisons
    - Conversion vers noms de base de données
    - Gestion des aliases
    """

    def __init__(self, intents_path: str = "config/intents.json"):
        """
        Initialise le registre depuis intents.json

        Args:
            intents_path: Chemin vers le fichier intents.json
        """
        self.intents_path = Path(intents_path)
        self.config = self._load_config()
        self.breed_registry = self.config.get("breed_registry", {})
        self.aliases = self.config.get("aliases", {}).get("line", {})
        self.db_mapping = self.breed_registry.get("db_name_mapping", {})
        self.comparison_rules = self.breed_registry.get("comparison_rules", {})

        # Index inversés pour recherche rapide O(1)
        self._species_index = self._build_species_index()
        self._alias_index = self._build_alias_index()

        logger.info(
            f"✅ BreedsRegistry chargé: {len(self.aliases)} races principales, "
            f"{len(self._species_index)} avec species, "
            f"{len(self._alias_index)} aliases totaux"
        )

    def _load_config(self) -> Dict:
        """Charge intents.json avec gestion d'erreurs"""
        try:
            with open(self.intents_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                logger.debug(f"Configuration chargée depuis {self.intents_path}")
                return config
        except FileNotFoundError:
            logger.error(f"❌ Fichier non trouvé: {self.intents_path}")
            return {}
        except json.JSONDecodeError as e:
            logger.error(f"❌ Erreur JSON dans {self.intents_path}: {e}")
            return {}
        except Exception as e:
            logger.error(f"❌ Erreur chargement {self.intents_path}: {e}")
            return {}

    def _build_species_index(self) -> Dict[str, str]:
        """
        Construit un index breed_name → species pour lookup O(1)

        Returns:
            {"ross 308": "broiler", "hy-line brown": "layer", ...}
        """
        index = {}

        for species in ["broilers", "layers", "breeders"]:
            breeds_list = self.breed_registry.get(species, [])
            species_singular = species.rstrip("s")  # broilers → broiler

            for breed in breeds_list:
                index[breed.lower()] = species_singular

        logger.debug(f"Species index construit: {len(index)} entrées")
        return index

    def _build_alias_index(self) -> Dict[str, str]:
        """
        Construit un index alias → canonical_name pour normalisation rapide

        Returns:
            {"ross308": "ross 308", "c500": "cobb 500", ...}
        """
        index = {}

        for canonical, alias_list in self.aliases.items():
            # Ajouter le nom canonique lui-même
            index[canonical.lower()] = canonical

            # Ajouter tous les aliases
            for alias in alias_list:
                alias_lower = alias.lower()
                if alias_lower not in index:
                    index[alias_lower] = canonical
                else:
                    # Log si un alias pointe vers plusieurs canonicals (conflit)
                    if index[alias_lower] != canonical:
                        logger.warning(
                            f"⚠️ Alias en conflit: '{alias}' → "
                            f"'{index[alias_lower]}' et '{canonical}'"
                        )

        logger.debug(f"Alias index construit: {len(index)} entrées")
        return index

    @lru_cache(maxsize=512)
    def get_species(self, breed_input: str) -> Optional[str]:
        """
        Retourne l'espèce d'une race (broiler, layer, breeder)

        Args:
            breed_input: "Ross 308", "ross308", "Cobb 500", etc.

        Returns:
            "broiler", "layer", "breeder", ou None si inconnu

        Examples:
            >>> registry = BreedsRegistry()
            >>> registry.get_species("Ross 308")
            'broiler'
            >>> registry.get_species("Hy-Line Brown")
            'layer'
            >>> registry.get_species("unknown breed")
            None
        """
        if not breed_input:
            return None

        # Normaliser l'input vers le nom canonique
        breed_normalized = self.normalize_breed_name(breed_input)
        if not breed_normalized:
            # Essayer directement avec l'input
            breed_normalized = breed_input

        # Chercher dans l'index species
        species = self._species_index.get(breed_normalized.lower())

        if species:
            logger.debug(f"Species: '{breed_input}' → '{species}'")
        else:
            logger.debug(f"Species inconnue pour: '{breed_input}'")

        return species

    @lru_cache(maxsize=512)
    def normalize_breed_name(self, breed_input: str) -> Optional[str]:
        """
        Normalise n'importe quelle variante vers le nom canonique

        Args:
            breed_input: "ross308", "c500", "Ross 308", etc.

        Returns:
            Nom canonique: "ross 308", "cobb 500", etc. ou None

        Examples:
            >>> registry = BreedsRegistry()
            >>> registry.normalize_breed_name("ross308")
            'ross 308'
            >>> registry.normalize_breed_name("c-500")
            'cobb 500'
            >>> registry.normalize_breed_name("unknown")
            None
        """
        if not breed_input:
            return None

        breed_lower = breed_input.lower().strip()

        # Chercher dans l'index d'aliases
        canonical = self._alias_index.get(breed_lower)

        if canonical:
            logger.debug(f"Breed normalisé: '{breed_input}' → '{canonical}'")
            return canonical

        logger.debug(f"Breed inconnu: '{breed_input}'")
        return None

    @lru_cache(maxsize=512)
    def get_db_name(self, breed_input: str) -> Optional[str]:
        """
        Convertit un nom de race vers le nom utilisé en BD PostgreSQL

        Args:
            breed_input: "Ross 308", "Cobb 500", etc.

        Returns:
            Nom BD: "308/308 FF", "500", etc. ou None

        Examples:
            >>> registry = BreedsRegistry()
            >>> registry.get_db_name("Ross 308")
            '308/308 FF'
            >>> registry.get_db_name("Cobb 500")
            '500'
            >>> registry.get_db_name("ross308")
            '308/308 FF'
        """
        # Normaliser d'abord vers le nom canonique
        breed_normalized = self.normalize_breed_name(breed_input)
        if not breed_normalized:
            logger.warning(f"Impossible de normaliser: '{breed_input}'")
            return None

        # Chercher le mapping DB
        db_name = self.db_mapping.get(breed_normalized)

        if db_name:
            logger.debug(f"DB name: '{breed_input}' → '{db_name}'")
        else:
            # Fallback: utiliser le nom normalisé si pas de mapping explicite
            logger.debug(
                f"Pas de DB mapping pour '{breed_normalized}', "
                f"utilisation nom normalisé"
            )
            db_name = breed_normalized

        return db_name

    def get_aliases(self, breed_canonical: str) -> List[str]:
        """
        Retourne tous les aliases d'une race canonique

        Args:
            breed_canonical: Nom canonique (ex: "ross 308")

        Returns:
            Liste des aliases
        """
        return self.aliases.get(breed_canonical, [])

    def are_comparable(self, breed1: str, breed2: str) -> Tuple[bool, str]:
        """
        Vérifie si deux races peuvent être comparées (même species)

        Args:
            breed1: Première race
            breed2: Deuxième race

        Returns:
            (compatible: bool, raison: str)

        Examples:
            >>> registry = BreedsRegistry()
            >>> registry.are_comparable("Ross 308", "Cobb 500")
            (True, "Both are broiler")
            >>> registry.are_comparable("Ross 308", "Hy-Line Brown")
            (False, "Cannot compare broiler with layer")
        """
        species1 = self.get_species(breed1)
        species2 = self.get_species(breed2)

        if not species1:
            return (False, f"Unknown breed: {breed1}")
        if not species2:
            return (False, f"Unknown breed: {breed2}")

        # Vérifier règles de compatibilité
        allow_cross_species = self.comparison_rules.get("allow_cross_species", False)

        if not allow_cross_species:
            if species1 == species2:
                return (True, f"Both are {species1}")
            else:
                error_msg = self.comparison_rules.get("error_messages", {}).get(
                    "cross_species_en", f"Cannot compare {species1} with {species2}"
                )
                return (False, error_msg)

        # Vérifier groupes compatibles si cross-species autorisé
        compatible_groups = self.comparison_rules.get("compatible_groups", {})
        species1_group = compatible_groups.get(species1, [species1])

        if species2 in species1_group:
            return (True, f"Compatible species: {species1} and {species2}")
        else:
            return (False, f"Incompatible species: {species1} and {species2}")

    def get_all_breeds_by_species(self, species: str) -> List[str]:
        """
        Liste toutes les races pour une espèce donnée

        Args:
            species: "broiler", "layer", ou "breeder"

        Returns:
            Liste des noms canoniques

        Examples:
            >>> registry = BreedsRegistry()
            >>> broilers = registry.get_all_breeds_by_species("broiler")
            >>> "ross 308" in broilers
            True
        """
        # Normaliser species (broiler → broilers)
        species_plural = species if species.endswith("s") else species + "s"
        breeds = self.breed_registry.get(species_plural, [])

        logger.debug(f"Races {species}: {len(breeds)} trouvées")
        return breeds

    def get_all_breeds(self) -> Set[str]:
        """
        Retourne toutes les races connues (tous species confondus)

        Returns:
            Set des noms canoniques
        """
        all_breeds = set()
        for species in ["broilers", "layers", "breeders"]:
            all_breeds.update(self.breed_registry.get(species, []))
        return all_breeds

    def get_breeds_summary(self) -> Dict[str, int]:
        """
        Retourne un résumé des races par espèce

        Returns:
            Dict avec compteurs par species
        """
        return {
            "broilers": len(self.breed_registry.get("broilers", [])),
            "layers": len(self.breed_registry.get("layers", [])),
            "breeders": len(self.breed_registry.get("breeders", [])),
            "total": len(self._species_index),
            "aliases_total": len(self._alias_index),
        }

    def validate_breed(self, breed_input: str) -> Tuple[bool, Optional[str]]:
        """
        Valide qu'une race existe dans le registre

        Args:
            breed_input: Nom de race à valider

        Returns:
            (valide: bool, nom_canonique: Optional[str])
        """
        canonical = self.normalize_breed_name(breed_input)
        if canonical:
            return (True, canonical)
        else:
            return (False, None)

    def get_comparison_error_message(self, language: str = "en") -> str:
        """
        Retourne le message d'erreur pour comparaison incompatible

        Args:
            language: "fr" ou "en"

        Returns:
            Message d'erreur traduit
        """
        messages = self.comparison_rules.get("error_messages", {})
        key = f"cross_species_{language}"
        return messages.get(key, "Cannot compare breeds of different species")


# ============================================================================
# SINGLETON GLOBAL
# ============================================================================

_global_registry: Optional[BreedsRegistry] = None


def get_breeds_registry(
    intents_path: str = "config/intents.json", force_reload: bool = False
) -> BreedsRegistry:
    """
    Factory pour obtenir l'instance globale du registre (singleton)

    Args:
        intents_path: Chemin vers intents.json
        force_reload: Si True, recharge le registre même s'il existe

    Returns:
        Instance BreedsRegistry

    Examples:
        >>> registry = get_breeds_registry()
        >>> species = registry.get_species("Ross 308")
    """
    global _global_registry

    if _global_registry is None or force_reload:
        _global_registry = BreedsRegistry(intents_path)

    return _global_registry


# ============================================================================
# TESTS UNITAIRES
# ============================================================================

if __name__ == "__main__":
    import sys

    # Configuration logging pour tests
    logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")

    print("=" * 70)
    print("🧪 TESTS BREEDS REGISTRY")
    print("=" * 70)

    # Initialiser le registre
    try:
        registry = get_breeds_registry()
    except Exception as e:
        print(f"❌ Erreur initialisation: {e}")
        sys.exit(1)

    # Test 1: Résumé
    print("\n📊 Test 1: Résumé du registre")
    summary = registry.get_breeds_summary()
    print(f"  Broilers: {summary['broilers']}")
    print(f"  Layers: {summary['layers']}")
    print(f"  Breeders: {summary['breeders']}")
    print(f"  Total races: {summary['total']}")
    print(f"  Total aliases: {summary['aliases_total']}")

    # Test 2: Normalisation
    print("\n🔄 Test 2: Normalisation des noms")
    test_cases = [
        ("ross308", "ross 308"),
        ("Ross 308", "ross 308"),
        ("c500", "cobb 500"),
        ("Cobb-500", "cobb 500"),
        ("hy-line brown", "hy-line brown"),
    ]

    for input_name, expected in test_cases:
        result = registry.normalize_breed_name(input_name)
        status = "✅" if result == expected else "❌"
        print(f"  {status} '{input_name}' → '{result}' (attendu: '{expected}')")

    # Test 3: Species
    print("\n🐔 Test 3: Détection species")
    test_species = [
        ("Ross 308", "broiler"),
        ("Cobb 500", "broiler"),
        ("Hy-Line Brown", "layer"),
        ("ISA Brown", "layer"),
        ("Ross 308 PS", "breeder"),
    ]

    for breed, expected in test_species:
        result = registry.get_species(breed)
        status = "✅" if result == expected else "❌"
        print(f"  {status} '{breed}' → '{result}' (attendu: '{expected}')")

    # Test 4: DB Names
    print("\n💾 Test 4: Conversion vers noms BD")
    test_db = [
        ("Ross 308", "308/308 FF"),
        ("ross308", "308/308 FF"),
        ("Cobb 500", "500"),
        ("c500", "500"),
    ]

    for breed, expected in test_db:
        result = registry.get_db_name(breed)
        status = "✅" if result == expected else "❌"
        print(f"  {status} '{breed}' → '{result}' (attendu: '{expected}')")

    # Test 5: Comparabilité
    print("\n⚖️  Test 5: Validation comparaisons")
    test_comparisons = [
        ("Ross 308", "Cobb 500", True),  # Broiler vs Broiler
        ("Ross 308", "Hy-Line Brown", False),  # Broiler vs Layer
        ("ISA Brown", "Lohmann Brown", True),  # Layer vs Layer
        ("Cobb 500 PS", "Ross 308", False),  # Breeder vs Broiler
    ]

    for breed1, breed2, should_be_compatible in test_comparisons:
        compatible, reason = registry.are_comparable(breed1, breed2)
        status = "✅" if compatible == should_be_compatible else "❌"
        print(f"  {status} '{breed1}' vs '{breed2}' → {compatible} ({reason})")

    # Test 6: Validation
    print("\n✔️  Test 6: Validation de races")
    test_validation = [
        ("Ross 308", True),
        ("cobb500", True),
        ("UnknownBreed", False),
        ("invalid", False),
    ]

    for breed, should_be_valid in test_validation:
        is_valid, canonical = registry.validate_breed(breed)
        status = "✅" if is_valid == should_be_valid else "❌"
        print(f"  {status} '{breed}' → valide={is_valid}, canonical='{canonical}'")

    print("\n" + "=" * 70)
    print("✅ TESTS TERMINÉS")
    print("=" * 70)
