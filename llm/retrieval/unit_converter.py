# -*- coding: utf-8 -*-
"""
unit_converter.py - Utilitaire de conversion d'unités imperial ↔ metric

Fournit des fonctions de conversion pour:
- Poids: pounds ↔ kilograms/grams
- Longueur: inches/feet ↔ centimeters/meters
- Température: fahrenheit ↔ celsius
"""

import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


class UnitConverter:
    """Convertisseur d'unités pour données aviculture"""

    # Tables de conversion (multiplicateur vers unité cible)
    CONVERSIONS = {
        # Poids
        ('pounds', 'kilograms'): 0.453592,
        ('pounds', 'grams'): 453.592,
        ('lb', 'kg'): 0.453592,
        ('lb', 'g'): 453.592,
        ('lbs', 'kg'): 0.453592,
        ('lbs', 'grams'): 453.592,
        ('ounces', 'grams'): 28.3495,
        ('oz', 'g'): 28.3495,

        # Inverse poids
        ('kilograms', 'pounds'): 2.20462,
        ('grams', 'pounds'): 0.00220462,
        ('kg', 'lb'): 2.20462,
        ('g', 'lb'): 0.00220462,
        ('grams', 'ounces'): 0.035274,
        ('g', 'oz'): 0.035274,

        # Longueur
        ('inches', 'centimeters'): 2.54,
        ('inch', 'cm'): 2.54,
        ('in', 'cm'): 2.54,
        ('feet', 'meters'): 0.3048,
        ('foot', 'meters'): 0.3048,
        ('ft', 'm'): 0.3048,

        # Inverse longueur
        ('centimeters', 'inches'): 0.393701,
        ('cm', 'in'): 0.393701,
        ('meters', 'feet'): 3.28084,
        ('m', 'ft'): 3.28084,
    }

    @classmethod
    def convert(
        cls, value: float, from_unit: str, to_unit: str
    ) -> Optional[float]:
        """
        Convertit une valeur d'une unité vers une autre.

        Args:
            value: Valeur numérique à convertir
            from_unit: Unité source (ex: 'pounds', 'lb', 'kg')
            to_unit: Unité cible (ex: 'kilograms', 'kg', 'grams')

        Returns:
            Valeur convertie ou None si conversion impossible

        Example:
            >>> UnitConverter.convert(5.0, 'lb', 'kg')
            2.26796
            >>> UnitConverter.convert(2.5, 'kilograms', 'pounds')
            5.51155
        """
        if not value or not from_unit or not to_unit:
            return None

        # Normaliser les unités (lowercase, strip)
        from_unit_norm = from_unit.lower().strip()
        to_unit_norm = to_unit.lower().strip()

        # Si même unité, retourner tel quel
        if from_unit_norm == to_unit_norm:
            return value

        # Cas spécial: température (formule différente)
        if from_unit_norm in ['fahrenheit', 'f', '°f'] and to_unit_norm in ['celsius', 'c', '°c']:
            return cls._fahrenheit_to_celsius(value)
        if from_unit_norm in ['celsius', 'c', '°c'] and to_unit_norm in ['fahrenheit', 'f', '°f']:
            return cls._celsius_to_fahrenheit(value)

        # Chercher dans la table de conversion
        conversion_key = (from_unit_norm, to_unit_norm)
        if conversion_key in cls.CONVERSIONS:
            converted = value * cls.CONVERSIONS[conversion_key]
            logger.debug(
                f"Converted {value} {from_unit} → {converted:.3f} {to_unit} "
                f"(factor: {cls.CONVERSIONS[conversion_key]})"
            )
            return converted

        # Conversion non supportée
        logger.warning(
            f"Conversion not supported: {from_unit} → {to_unit}"
        )
        return None

    @staticmethod
    def _fahrenheit_to_celsius(fahrenheit: float) -> float:
        """Convertit Fahrenheit vers Celsius"""
        return (fahrenheit - 32) * 5 / 9

    @staticmethod
    def _celsius_to_fahrenheit(celsius: float) -> float:
        """Convertit Celsius vers Fahrenheit"""
        return celsius * 9 / 5 + 32

    @classmethod
    def can_convert(cls, from_unit: str, to_unit: str) -> bool:
        """
        Vérifie si une conversion est supportée.

        Args:
            from_unit: Unité source
            to_unit: Unité cible

        Returns:
            True si conversion possible, False sinon
        """
        if not from_unit or not to_unit:
            return False

        from_unit_norm = from_unit.lower().strip()
        to_unit_norm = to_unit.lower().strip()

        # Même unité
        if from_unit_norm == to_unit_norm:
            return True

        # Température
        if from_unit_norm in ['fahrenheit', 'f', '°f'] and to_unit_norm in ['celsius', 'c', '°c']:
            return True
        if from_unit_norm in ['celsius', 'c', '°c'] and to_unit_norm in ['fahrenheit', 'f', '°f']:
            return True

        # Table de conversion
        return (from_unit_norm, to_unit_norm) in cls.CONVERSIONS

    @classmethod
    def get_canonical_unit(cls, unit: str, unit_system: str = "metric") -> Optional[str]:
        """
        Retourne l'unité canonique pour un système donné.

        Args:
            unit: Unité actuelle (ex: 'lb', 'g', 'oz')
            unit_system: Système cible ('metric' ou 'imperial')

        Returns:
            Unité canonique (ex: 'lb' → 'kilograms' si metric)

        Example:
            >>> UnitConverter.get_canonical_unit('lb', 'metric')
            'kilograms'
            >>> UnitConverter.get_canonical_unit('grams', 'imperial')
            'pounds'
        """
        unit_norm = unit.lower().strip()

        if unit_system == "metric":
            # Mapper vers unités métriques
            if unit_norm in ['pounds', 'lb', 'lbs']:
                return 'kilograms'
            if unit_norm in ['ounces', 'oz']:
                return 'grams'
            if unit_norm in ['inches', 'inch', 'in']:
                return 'centimeters'
            if unit_norm in ['feet', 'foot', 'ft']:
                return 'meters'
            if unit_norm in ['fahrenheit', 'f', '°f']:
                return 'celsius'
            # Déjà métrique
            if unit_norm in ['grams', 'g', 'kilograms', 'kg', 'cm', 'mm', 'meters', 'm', 'celsius', 'c', '°c']:
                return unit_norm

        elif unit_system == "imperial":
            # Mapper vers unités impériales
            if unit_norm in ['kilograms', 'kg']:
                return 'pounds'
            if unit_norm in ['grams', 'g']:
                return 'ounces'
            if unit_norm in ['centimeters', 'cm', 'millimeters', 'mm']:
                return 'inches'
            if unit_norm in ['meters', 'm']:
                return 'feet'
            if unit_norm in ['celsius', 'c', '°c']:
                return 'fahrenheit'
            # Déjà impérial
            if unit_norm in ['pounds', 'lb', 'lbs', 'ounces', 'oz', 'inches', 'in', 'feet', 'ft', 'fahrenheit', 'f', '°f']:
                return unit_norm

        # Unités neutres (pourcentage, jours) - pas de conversion
        if unit_norm in ['percentage', '%', 'days', 'day', 'j', 'jours']:
            return unit_norm

        return None

    @classmethod
    def convert_to_preference(
        cls, value: float, current_unit: str, unit_preference: str
    ) -> Tuple[Optional[float], Optional[str]]:
        """
        Convertit une valeur vers le système d'unités préféré de l'utilisateur.

        Args:
            value: Valeur numérique
            current_unit: Unité actuelle
            unit_preference: Système préféré ('metric' ou 'imperial')

        Returns:
            Tuple (valeur convertie, nouvelle unité) ou (None, None) si impossible

        Example:
            >>> UnitConverter.convert_to_preference(5.0, 'lb', 'metric')
            (2.26796, 'kilograms')
            >>> UnitConverter.convert_to_preference(2500, 'grams', 'imperial')
            (5.51155, 'pounds')
        """
        if not value or not current_unit or not unit_preference:
            return None, None

        # Déterminer l'unité cible canonique
        target_unit = cls.get_canonical_unit(current_unit, unit_preference)
        if not target_unit:
            logger.warning(f"No canonical unit for '{current_unit}' in {unit_preference} system")
            return value, current_unit  # Retourner tel quel

        # Si déjà dans la bonne unité
        if current_unit.lower() == target_unit.lower():
            return value, current_unit

        # Convertir
        converted_value = cls.convert(value, current_unit, target_unit)
        if converted_value is not None:
            logger.info(
                f"✅ Converted {value} {current_unit} → {converted_value:.2f} {target_unit} "
                f"(user prefers {unit_preference})"
            )
            return converted_value, target_unit
        else:
            logger.warning(f"Failed to convert {current_unit} → {target_unit}")
            return value, current_unit  # Fallback sur valeur originale
