"""
unified_response_generator.py - GÉNÉRATEUR AVEC SUPPORT CONTEXTUAL_ANSWER

🎯 AMÉLIORATIONS AJOUTÉES:
- ✅ Support du type CONTEXTUAL_ANSWER
- ✅ Utilisation des weight_data calculées par le classifier
- ✅ Génération de réponses précises Ross 308 mâle 12j
- ✅ Interpolation automatique des âges intermédiaires
- ✅ Templates spécialisés pour réponses contextuelles

Nouveau flux:
1. Classification → CONTEXTUAL_ANSWER avec weight_data
2. Response Generator → Utilise weight_data pour réponse précise
3. Output → "Ross 308 mâle à 12 jours : 380-420g" 🎯
"""

import logging
import re
from typing import Dict, Any, Optional, List
from datetime import datetime

# Import des fonctions de calcul de poids
from .intelligent_system_config import get_weight_range, validate_weight_range

logger = logging.getLogger(__name__)

class ResponseData:
    """Structure pour les données de réponse"""
    def __init__(self, response: str, response_type: str, confidence: float = 0.8, 
                 precision_offer: str = None, examples: List[str] = None,
                 weight_data: Dict[str, Any] = None):
        self.response = response
        self.response_type = response_type
        self.confidence = confidence
        self.precision_offer = precision_offer
        self.examples = examples or []
        self.weight_data = weight_data or {}
        self.generated_at = datetime.now().isoformat()

class UnifiedResponseGenerator:
    """Générateur unique pour tous les types de réponse avec support contextuel"""
    
    def __init__(self):
        # Configuration des fourchettes de poids par race et âge (garde pour compatibilité)
        self.weight_ranges = {
            "ross_308": {
                7: {"male": (180, 220), "female": (160, 200), "mixed": (170, 210)},
                14: {"male": (450, 550), "female": (400, 500), "mixed": (425, 525)},
                21: {"male": (850, 1050), "female": (750, 950), "mixed": (800, 1000)},
                28: {"male": (1400, 1700), "female": (1200, 1500), "mixed": (1300, 1600)},
                35: {"male": (2000, 2400), "female": (1800, 2200), "mixed": (1900, 2300)}
            },
            "cobb_500": {
                7: {"male": (175, 215), "female": (155, 195), "mixed": (165, 205)},
                14: {"male": (440, 540), "female": (390, 490), "mixed": (415, 515)},
                21: {"male": (830, 1030), "female": (730, 930), "mixed": (780, 980)},
                28: {"male": (1380, 1680), "female": (1180, 1480), "mixed": (1280, 1580)},
                35: {"male": (1980, 2380), "female": (1780, 2180), "mixed": (1880, 2280)}
            },
            "hubbard": {
                7: {"male": (170, 210), "female": (150, 190), "mixed": (160, 200)},
                14: {"male": (420, 520), "female": (370, 470), "mixed": (395, 495)},
                21: {"male": (800, 1000), "female": (700, 900), "mixed": (750, 950)},
                28: {"male": (1350, 1650), "female": (1150, 1450), "mixed": (1250, 1550)},
                35: {"male": (1950, 2350), "female": (1750, 2150), "mixed": (1850, 2250)}
            },
            "standard": {
                7: {"male": (160, 200), "female": (140, 180), "mixed": (150, 190)},
                14: {"male": (400, 500), "female": (350, 450), "mixed": (375, 475)},
                21: {"male": (750, 950), "female": (650, 850), "mixed": (700, 900)},
                28: {"male": (1250, 1550), "female": (1050, 1350), "mixed": (1150, 1450)},
                35: {"male": (1850, 2250), "female": (1650, 2050), "mixed": (1750, 2150)}
            }
        }

    def generate(self, question: str, entities: Dict[str, Any], classification_result) -> ResponseData:
        """
        POINT D'ENTRÉE UNIQUE - Génère la réponse selon la classification
        
        Args:
            question: Question originale
            entities: Entités extraites
            classification_result: Résultat du classifier
            
        Returns:
            ResponseData avec la réponse générée
        """
        try:
            logger.info(f"🎨 [Response Generator] Type: {classification_result.response_type.value}")
            
            # NOUVEAU: Support du type CONTEXTUAL_ANSWER
            if classification_result.response_type.value == "contextual_answer":
                return self._generate_contextual_answer(question, classification_result)
            
            elif classification_result.response_type.value == "precise_answer":
                return self._generate_precise(question, entities)
            
            elif classification_result.response_type.value == "general_answer":
                base_response = self._generate_general(question, entities)
                precision_offer = self._generate_precision_offer(entities, classification_result.missing_entities)
                
                # Combiner réponse + offre de précision
                if precision_offer:
                    full_response = f"{base_response}\n\n💡 **Pour plus de précision**: {precision_offer}"
                else:
                    full_response = base_response
                
                return ResponseData(
                    response=full_response,
                    response_type="general_with_offer",
                    confidence=0.8,
                    precision_offer=precision_offer
                )
            
            else:  # needs_clarification
                return self._generate_clarification(question, entities, classification_result.missing_entities)
                
        except Exception as e:
            logger.error(f"❌ [Response Generator] Erreur génération: {e}")
            return self._generate_fallback_response(question)

    def _generate_contextual_answer(self, question: str, classification_result) -> ResponseData:
        """NOUVEAU: Génère une réponse contextuelle basée sur les données fusionnées"""
        
        merged_entities = classification_result.merged_entities
        weight_data = classification_result.weight_data
        
        logger.info(f"🔗 [Contextual] Génération réponse avec données: {weight_data}")
        
        # Si on a des données de poids précalculées, les utiliser
        if weight_data and 'weight_range' in weight_data:
            return self._generate_contextual_weight_response(merged_entities, weight_data)
        
        # Sinon, générer une réponse contextuelle standard
        else:
            return self._generate_contextual_standard_response(merged_entities)

    def _generate_contextual_weight_response(self, entities: Dict[str, Any], weight_data: Dict[str, Any]) -> ResponseData:
        """Génère une réponse de poids contextuelle avec données précises"""
        
        breed = weight_data.get('breed', 'Race non spécifiée')
        age_days = weight_data.get('age_days', 0)
        sex = weight_data.get('sex', 'mixed')
        min_weight, max_weight = weight_data.get('weight_range', (0, 0))
        target_weight = weight_data.get('target_weight', (min_weight + max_weight) // 2)
        
        # Conversion du sexe pour affichage
        sex_display = {
            'male': 'mâle',
            'female': 'femelle', 
            'mixed': 'mixte'
        }.get(sex, sex)
        
        # Indicateurs d'héritage contextuel
        context_indicators = []
        if entities.get('age_context_inherited'):
            context_indicators.append("âge du contexte")
        if entities.get('breed_context_inherited'):
            context_indicators.append("race du contexte")
        if entities.get('sex_context_inherited'):
            context_indicators.append("sexe du contexte")
        
        context_info = ""
        if context_indicators:
            context_info = f"\n🔗 **Contexte utilisé** : {', '.join(context_indicators)}"
        
        response = f"""**Poids cible pour {breed} {sex_display} à {age_days} jours :**

🎯 **Fourchette précise** : **{min_weight}-{max_weight} grammes**

📊 **Détails spécifiques** :
• Poids minimum : {min_weight}g
• Poids cible optimal : {target_weight}g  
• Poids maximum : {max_weight}g

⚡ **Surveillance recommandée** :
• Pesée hebdomadaire d'un échantillon représentatif
• Vérification de l'homogénéité du troupeau
• Ajustement alimentaire si écart >15%

🚨 **Signaux d'alerte** :
• <{weight_data.get('alert_thresholds', {}).get('low', int(min_weight * 0.85))}g : Retard de croissance
• >{weight_data.get('alert_thresholds', {}).get('high', int(max_weight * 1.15))}g : Croissance excessive{context_info}

💡 **Standards basés sur** : Données de référence {breed} officielles"""

        return ResponseData(
            response=response,
            response_type="contextual_weight_precise",
            confidence=0.95,
            weight_data=weight_data
        )

    def _generate_contextual_standard_response(self, entities: Dict[str, Any]) -> ResponseData:
        """Génère une réponse contextuelle standard (sans données de poids)"""
        
        breed = entities.get('breed_specific', 'Race spécifiée')
        age = entities.get('age_days', 'Âge spécifié')
        sex = entities.get('sex', 'Sexe spécifié')
        
        # Indicateurs d'héritage contextuel
        context_parts = []
        if entities.get('age_context_inherited'):
            context_parts.append(f"âge ({age} jours)")
        if entities.get('breed_context_inherited'):
            context_parts.append(f"race ({breed})")
        if entities.get('sex_context_inherited'):
            context_parts.append(f"sexe ({sex})")
        
        if context_parts:
            context_info = f"En me basant sur le contexte de notre conversation ({', '.join(context_parts)}), "
        else:
            context_info = f"Pour {breed} {sex} à {age} jours, "
        
        response = f"""**Réponse contextuelle basée sur votre clarification :**

{context_info}voici les informations demandées :

🔗 **Contexte de conversation détecté** :
• Race : {breed}
• Sexe : {sex}  
• Âge : {age} jours
• Type de question : Performance/Poids

📊 **Recommandations générales** :
• Surveillance des standards de croissance
• Ajustement selon les performances observées
• Consultation spécialisée si écarts significatifs

💡 **Pour des valeurs précises**, consultez les standards de votre souche spécifique ou votre vétérinaire avicole."""

        return ResponseData(
            response=response,
            response_type="contextual_standard",
            confidence=0.8
        )

    def _generate_precise(self, question: str, entities: Dict[str, Any]) -> ResponseData:
        """Génère une réponse précise avec données spécifiques (méthode existante améliorée)"""
        
        breed = entities.get('breed_specific', '').lower().replace(' ', '_')
        age_days = entities.get('age_days')
        sex = entities.get('sex', 'mixed').lower()
        
        # Normaliser le sexe
        if sex in ['mâle', 'male', 'coq']:
            sex = 'male'
        elif sex in ['femelle', 'female', 'poule']:
            sex = 'female'
        else:
            sex = 'mixed'
        
        # Questions de poids
        if any(word in question.lower() for word in ['poids', 'weight', 'gramme', 'cible']):
            # NOUVEAU: Utiliser la fonction de config au lieu des données locales
            try:
                weight_range = get_weight_range(breed, age_days, sex)
                min_weight, max_weight = weight_range
                
                return self._generate_precise_weight_response_enhanced(breed, age_days, sex, weight_range)
                
            except Exception as e:
                logger.error(f"❌ [Precise] Erreur calcul poids: {e}")
                return self._generate_precise_weight_response(breed, age_days, sex)
        
        # Questions de croissance
        elif any(word in question.lower() for word in ['croissance', 'développement', 'grandir']):
            return self._generate_precise_growth_response(breed, age_days, sex)
        
        # Fallback général précis
        else:
            return ResponseData(
                response=f"Pour un {breed.replace('_', ' ').title()} {sex} de {age_days} jours, "
                        f"les paramètres normaux dépendent du contexte spécifique. "
                        f"Consultez les standards de la race pour des valeurs précises.",
                response_type="precise_general",
                confidence=0.7
            )

    def _generate_precise_weight_response_enhanced(self, breed: str, age_days: int, sex: str, weight_range: tuple) -> ResponseData:
        """NOUVEAU: Génère réponse précise avec données de la config"""
        
        min_weight, max_weight = weight_range
        target_weight = (min_weight + max_weight) // 2
        
        # Calculer les seuils d'alerte
        alert_low = int(min_weight * 0.85)
        alert_high = int(max_weight * 1.15)
        
        breed_name = breed.replace('_', ' ').title()
        sex_str = {'male': 'mâles', 'female': 'femelles', 'mixed': 'mixtes'}[sex]
        
        response = f"""**Poids cible pour {breed_name} {sex_str} à {age_days} jours :**

🎯 **Fourchette officielle** : **{min_weight}-{max_weight} grammes**

📊 **Détails spécifiques** :
• Poids minimum acceptable : {min_weight}g
• Poids cible optimal : {target_weight}g  
• Poids maximum normal : {max_weight}g

⚡ **Surveillance recommandée** :
• Pesée hebdomadaire d'échantillon représentatif (10-20 sujets)
• Vérification homogénéité du troupeau
• Ajustement alimentaire si nécessaire

🚨 **Signaux d'alerte** :
• <{alert_low}g : Retard de croissance - Vérifier alimentation et santé
• >{alert_high}g : Croissance excessive - Contrôler distribution alimentaire
• Hétérogénéité >20% : Problème de gestion du troupeau

💡 **Standards basés sur** : Données de référence {breed_name} officielles avec interpolation précise"""

        return ResponseData(
            response=response,
            response_type="precise_weight_enhanced",
            confidence=0.95,
            weight_data={
                "breed": breed_name,
                "age_days": age_days,
                "sex": sex,
                "weight_range": weight_range,
                "target_weight": target_weight,
                "alert_thresholds": {"low": alert_low, "high": alert_high}
            }
        )

    def _generate_precise_weight_response(self, breed: str, age_days: int, sex: str) -> ResponseData:
        """Génère réponse précise pour le poids (méthode existante de fallback)"""
        
        # Trouver la tranche d'âge la plus proche
        closest_age = self._find_closest_age(age_days)
        
        # Obtenir les données de poids
        breed_data = self.weight_ranges.get(breed, self.weight_ranges['standard'])
        weight_range = breed_data.get(closest_age, {}).get(sex, (300, 500))
        
        min_weight, max_weight = weight_range
        
        # Ajuster pour l'âge exact si différent
        if age_days != closest_age:
            adjustment_factor = age_days / closest_age
            min_weight = int(min_weight * adjustment_factor)
            max_weight = int(max_weight * adjustment_factor)
        
        breed_name = breed.replace('_', ' ').title()
        sex_str = {'male': 'mâles', 'female': 'femelles', 'mixed': 'mixtes'}[sex]
        
        response = f"""**Poids cible pour {breed_name} {sex_str} à {age_days} jours :**

🎯 **Fourchette normale** : {min_weight}-{max_weight} grammes

📊 **Détails spécifiques** :
• Poids minimum acceptable : {min_weight}g
• Poids optimal : {int((min_weight + max_weight) / 2)}g  
• Poids maximum normal : {max_weight}g

⚡ **Surveillance recommandée** :
• Pesée hebdomadaire du troupeau
• Alerte si écart >15% de la fourchette
• Ajustement alimentaire si nécessaire

🩺 **Action si hors fourchette** :
• <{min_weight}g : Vérifier alimentation et santé
• >{max_weight}g : Contrôler la distribution alimentaire"""

        return ResponseData(
            response=response,
            response_type="precise_weight",
            confidence=0.95
        )

    def _generate_general(self, question: str, entities: Dict[str, Any]) -> str:
        """Génère une réponse générale utile (méthode existante conservée)"""
        
        question_lower = question.lower()
        age_days = entities.get('age_days')
        
        # Questions de poids
        if any(word in question_lower for word in ['poids', 'weight', 'gramme', 'cible']):
            return self._generate_general_weight_response(age_days)
        
        # Questions de croissance
        elif any(word in question_lower for word in ['croissance', 'développement', 'grandir']):
            return self._generate_general_growth_response(age_days)
        
        # Questions de santé
        elif any(word in question_lower for word in ['malade', 'symptôme', 'problème', 'santé']):
            return self._generate_general_health_response(age_days)
        
        # Questions d'alimentation
        elif any(word in question_lower for word in ['alimentation', 'nourrir', 'aliment', 'nutrition']):
            return self._generate_general_feeding_response(age_days)
        
        # Réponse générale par défaut
        else:
            return self._generate_general_default_response(age_days)

    def _generate_general_weight_response(self, age_days: int) -> str:
        """Réponse générale pour questions de poids (méthode existante conservée)"""
        
        if not age_days:
            return """**Poids des poulets - Standards généraux :**

📊 **Fourchettes par âge** :
• 7 jours : 150-220g selon la race
• 14 jours : 350-550g selon la race  
• 21 jours : 650-1050g selon la race
• 28 jours : 1050-1700g selon la race

📈 **Facteurs influençant le poids** :
• **Race** : Races lourdes (Ross 308, Cobb 500) vs races standard
• **Sexe** : Mâles 10-15% plus lourds que les femelles
• **Alimentation** : Qualité et quantité de l'aliment
• **Conditions d'élevage** : Température, densité, stress

🎯 **Surveillance recommandée** :
• Pesée hebdomadaire représentative du troupeau
• Suivi de la courbe de croissance
• Consultation vétérinaire si écart significatif"""
        
        # Trouver la tranche d'âge
        closest_age = self._find_closest_age(age_days)
        
        # Calculer fourchettes pour cet âge
        ross_range = self.weight_ranges['ross_308'][closest_age]['mixed']
        cobb_range = self.weight_ranges['cobb_500'][closest_age]['mixed'] 
        standard_range = self.weight_ranges['standard'][closest_age]['mixed']
        
        return f"""**Poids normal à {age_days} jours :**

📊 **Fourchettes par race** :
• **Ross 308** : {ross_range[0]}-{ross_range[1]}g (races lourdes)
• **Cobb 500** : {cobb_range[0]}-{cobb_range[1]}g (races lourdes)
• **Races standard** : {standard_range[0]}-{standard_range[1]}g

⚖️ **Différences mâles/femelles** :
• **Mâles** : +10-15% par rapport aux moyennes ci-dessus
• **Femelles** : -10-15% par rapport aux moyennes ci-dessus

🎯 **Surveillance à {age_days} jours** :
• Pesée d'échantillon représentatif (10-20 sujets)
• Vérification homogénéité du troupeau
• Ajustement alimentaire si nécessaire

⚠️ **Signaux d'alerte** :
• Poids <{int(standard_range[0] * 0.85)}g : Retard de croissance
• Poids >{int(ross_range[1] * 1.15)}g : Croissance excessive
• Hétérogénéité >20% : Problème de gestion"""

    def _generate_precision_offer(self, entities: Dict[str, Any], missing_entities: List[str]) -> str:
        """Génère l'offre de précision selon les entités manquantes (méthode existante conservée)"""
        
        if not missing_entities:
            return ""
        
        offers = []
        
        if 'breed' in missing_entities:
            offers.append("**race/souche** (Ross 308, Cobb 500, Hubbard...)")
        
        if 'sex' in missing_entities:
            offers.append("**sexe** (mâles, femelles, ou troupeau mixte)")
        
        if 'age' in missing_entities:
            offers.append("**âge précis** (en jours ou semaines)")
        
        if len(offers) == 1:
            return f"Précisez la {offers[0]} pour une réponse plus spécifique."
        elif len(offers) == 2:
            return f"Précisez la {offers[0]} et le {offers[1]} pour une réponse plus spécifique."
        elif len(offers) >= 3:
            return f"Précisez la {', la '.join(offers[:-1])} et le {offers[-1]} pour une réponse plus spécifique."
        
        return ""

    def _generate_clarification(self, question: str, entities: Dict[str, Any], missing_entities: List[str]) -> ResponseData:
        """Génère une demande de clarification ciblée (méthode existante conservée)"""
        
        question_lower = question.lower()
        
        # Clarifications spécialisées selon le type de question
        if any(word in question_lower for word in ['poids', 'croissance', 'cible']):
            return self._generate_performance_clarification(missing_entities)
        
        elif any(word in question_lower for word in ['malade', 'symptôme', 'problème']):
            return self._generate_health_clarification(missing_entities)
        
        elif any(word in question_lower for word in ['alimentation', 'nourrir']):
            return self._generate_feeding_clarification(missing_entities)
        
        else:
            return self._generate_general_clarification(missing_entities)

    def _generate_performance_clarification(self, missing_entities: List[str]) -> ResponseData:
        """Clarification pour questions de performance/poids (méthode existante conservée)"""
        
        clarification = """Pour vous donner des informations précises sur les performances, j'ai besoin de :

🔍 **Informations nécessaires** :"""
        
        if 'breed' in missing_entities:
            clarification += "\n• **Race/souche** : Ross 308, Cobb 500, Hubbard, etc."
        
        if 'age' in missing_entities:
            clarification += "\n• **Âge** : En jours ou semaines (ex: 21 jours, 3 semaines)"
        
        if 'sex' in missing_entities:
            clarification += "\n• **Sexe** : Mâles, femelles, ou troupeau mixte"
        
        clarification += """

💡 **Exemples de questions complètes** :
• "Quel est le poids normal d'un Ross 308 mâle à 21 jours ?"
• "Croissance normale pour Cobb 500 femelles à 3 semaines ?"
• "Poids cible Hubbard mixte à 28 jours ?\""""
        
        return ResponseData(
            response=clarification,
            response_type="clarification_performance",
            confidence=0.9,
            examples=["Ross 308 mâles 21 jours", "Cobb 500 femelles 3 semaines"]
        )

    def _find_closest_age(self, age_days: int) -> int:
        """Trouve l'âge le plus proche dans les données de référence (méthode existante conservée)"""
        available_ages = [7, 14, 21, 28, 35]
        
        if age_days <= 7:
            return 7
        elif age_days <= 10:
            return 7 if abs(age_days - 7) < abs(age_days - 14) else 14
        elif age_days <= 17:
            return 14 if abs(age_days - 14) < abs(age_days - 21) else 21
        elif age_days <= 24:
            return 21 if abs(age_days - 21) < abs(age_days - 28) else 28
        elif age_days <= 31:
            return 28 if abs(age_days - 28) < abs(age_days - 35) else 35
        else:
            return 35

    def _generate_fallback_response(self, question: str) -> ResponseData:
        """Génère une réponse de fallback en cas d'erreur (méthode existante conservée)"""
        return ResponseData(
            response="Je rencontre une difficulté pour analyser votre question. "
                    "Pouvez-vous la reformuler en précisant le contexte (race, âge, problème spécifique) ?",
            response_type="fallback",
            confidence=0.3
        )

    # Méthodes additionnelles pour autres types de réponses générales (conservées)
    def _generate_general_growth_response(self, age_days: int) -> str:
        """Réponse générale pour croissance"""
        return f"""**Croissance normale des poulets** {"à " + str(age_days) + " jours" if age_days else ""} :

📈 **Indicateurs de croissance saine** :
• Gain de poids régulier et progressif
• Activité normale et appétit constant  
• Développement harmonieux du plumage
• Comportement social adapté

⚠️ **Signaux d'alerte** :
• Stagnation ou perte de poids
• Apathie ou refus alimentaire
• Hétérogénéité excessive du troupeau
• Mortalité anormale

🎯 **Suivi recommandé** :
• Pesée hebdomadaire d'échantillons
• Observation quotidienne du comportement
• Contrôle des conditions d'ambiance"""

    def _generate_general_health_response(self, age_days: int) -> str:
        """Réponse générale pour santé"""
        return """**Santé des poulets - Surveillance générale** :

🩺 **Signes de bonne santé** :
• Activité normale et vivacité
• Appétit régulier et consommation d'eau normale
• Fientes normales (consistance et couleur)
• Plumage propre et bien développé

⚠️ **Signaux d'alerte** :
• Apathie, isolement du groupe
• Refus alimentaire ou baisse de consommation
• Diarrhée, fientes anormales
• Difficultés respiratoires, boiteries

🚨 **Action immédiate** :
• Isoler les sujets malades
• Consulter un vétérinaire rapidement  
• Renforcer les mesures d'hygiène
• Surveiller l'évolution du troupeau"""

    def _generate_general_feeding_response(self, age_days: int) -> str:
        """Réponse générale pour alimentation"""
        age_info = f" à {age_days} jours" if age_days else ""
        
        return f"""**Alimentation des poulets{age_info}** :

🌾 **Besoins nutritionnels** :
• Protéines adaptées au stade de croissance
• Énergie suffisante pour le développement
• Vitamines et minéraux équilibrés
• Eau propre et fraîche en permanence

📊 **Consommation normale** :
• Augmentation progressive avec l'âge
• Répartition sur 24h avec pics d'activité
• Adaptation selon température ambiante

🎯 **Bonnes pratiques** :
• Aliment adapté au stade physiologique
• Distribution régulière et homogène
• Hygiène des mangeoires et abreuvoirs
• Ajustement selon les performances"""

    def _generate_general_default_response(self, age_days: int) -> str:
        """Réponse générale par défaut"""
        return """**Élevage de poulets - Conseils généraux** :

🏠 **Conditions d'élevage optimales** :
• Température adaptée au stade
• Ventilation suffisante sans courants d'air
• Densité appropriée (confort animal)
• Litière propre et sèche

📊 **Surveillance quotidienne** :
• Comportement et activité du troupeau
• Consommation alimentaire et hydrique
• État sanitaire général
• Conditions d'ambiance

🎯 **Suivi des performances** :
• Pesées régulières
• Contrôle de la croissance
• Indices de consommation
• Suivi sanitaire"""

    def _generate_health_clarification(self, missing_entities: List[str]) -> ResponseData:
        """Clarification pour questions de santé"""
        return ResponseData(
            response="""Pour vous aider efficacement avec un problème de santé, décrivez :

🩺 **Symptômes observés** :
• Comportement anormal (apathie, isolement...)
• Symptômes physiques (diarrhée, boiterie, difficultés respiratoires...)
• Évolution dans le temps

📋 **Contexte du troupeau** :
• Âge des animaux affectés
• Nombre de sujets touchés
• Race/souche si connue
• Conditions d'élevage récentes

⏰ **Urgence** : En cas de mortalité ou symptômes graves, consultez immédiatement un vétérinaire.""",
            response_type="clarification_health",
            confidence=0.9
        )

    def _generate_feeding_clarification(self, missing_entities: List[str]) -> ResponseData:
        """Clarification pour questions d'alimentation"""
        return ResponseData(
            response="""Pour des conseils nutritionnels adaptés, précisez :

🌾 **Informations sur vos animaux** :
• Âge ou stade physiologique
• Race/souche (chair, ponte, mixte)
• Effectif du troupeau

🎯 **Objectif recherché** :
• Croissance optimale, préparation ponte, maintien...
• Problème spécifique à résoudre
• Performance attendue

💡 **Exemple de question précise** :
"Quel aliment pour Ross 308 de 3 semaines pour optimiser la croissance ?\"""",
            response_type="clarification_feeding",
            confidence=0.9
        )

    def _generate_general_clarification(self, missing_entities: List[str]) -> ResponseData:
        """Clarification générale"""
        return ResponseData(
            response="""Pour vous donner une réponse adaptée, pouvez-vous préciser :

📋 **Votre situation** :
• Type de volailles (poulets de chair, pondeuses...)
• Âge ou stade d'élevage
• Problème ou objectif spécifique

🎯 **Exemples de questions précises** :
• "Poids normal Ross 308 mâles à 21 jours ?"
• "Symptômes diarrhée chez pondeuses 25 semaines"
• "Alimentation optimale Cobb 500 démarrage"

💡 Plus votre question est précise, plus ma réponse sera adaptée à votre situation !""",
            response_type="clarification_general",
            confidence=0.7
        )

    def _generate_precise_growth_response(self, breed: str, age_days: int, sex: str) -> ResponseData:
        """Génère réponse précise pour la croissance"""
        
        breed_name = breed.replace('_', ' ').title()
        sex_str = {'male': 'mâles', 'female': 'femelles', 'mixed': 'mixtes'}[sex]
        
        # Calculs de gain quotidien selon l'âge
        if age_days <= 7:
            daily_gain_range = "3-8g"
            growth_phase = "Démarrage critique"
        elif age_days <= 14:
            daily_gain_range = "25-35g"
            growth_phase = "Croissance initiale"
        elif age_days <= 21:
            daily_gain_range = "45-65g"
            growth_phase = "Croissance rapide"
        elif age_days <= 28:
            daily_gain_range = "65-85g"
            growth_phase = "Croissance intensive"
        else:
            daily_gain_range = "70-95g"
            growth_phase = "Finition"
        
        response = f"""**Croissance {breed_name} {sex_str} à {age_days} jours :**

🎯 **Phase actuelle** : {growth_phase}

📈 **Gain quotidien attendu** : {daily_gain_range} par jour

📊 **Indicateurs de performance** :
• Homogénéité du troupeau >85%
• Activité normale et appétit constant
• Absence de retards de croissance
• Développement harmonieux du plumage

⚡ **Surveillance spécifique** :
• Pesée bi-hebdomadaire représentative
• Contrôle de la courbe de croissance
• Ajustement nutritionnel selon gains observés

🚨 **Signaux d'alerte** :
• Gain <{daily_gain_range.split('-')[0]} : Retard de croissance
• Stagnation >2 jours : Problème sanitaire potentiel
• Hétérogénéité >15% : Gestion à réviser"""

        return ResponseData(
            response=response,
            response_type="precise_growth",
            confidence=0.9
        )

# =============================================================================
# FONCTIONS UTILITAIRES
# =============================================================================

def quick_generate(question: str, entities: Dict[str, Any], response_type: str) -> str:
    """Génération rapide pour usage simple"""
    generator = UnifiedResponseGenerator()
    
    # Créer un objet de classification simulé
    class MockClassification:
        def __init__(self, resp_type):
            from .smart_classifier import ResponseType
            self.response_type = ResponseType(resp_type)
            self.missing_entities = []
            self.merged_entities = entities
            self.weight_data = {}
    
    classification = MockClassification(response_type)
    result = generator.generate(question, entities, classification)
    
    return result.response

# =============================================================================
# TESTS INTÉGRÉS AVEC CONTEXTUAL_ANSWER
# =============================================================================

def test_generator_contextual():
    """Tests du générateur avec support CONTEXTUAL_ANSWER"""
    generator = UnifiedResponseGenerator()
    
    print("🧪 Test générateur avec support CONTEXTUAL_ANSWER")
    print("=" * 60)
    
    # Test CONTEXTUAL_ANSWER avec données de poids
    class MockContextualClassification:
        def __init__(self):
            from .smart_classifier import ResponseType
            self.response_type = ResponseType.CONTEXTUAL_ANSWER
            self.merged_entities = {
                'breed_specific': 'Ross 308',
                'age_days': 12,
                'sex': 'mâle',
                'context_type': 'performance',
                'age_context_inherited': True
            }
            self.weight_data = {
                'breed': 'Ross 308',
                'age_days': 12,
                'sex': 'male',
                'weight_range': (380, 420),
                'target_weight': 400,
                'alert_thresholds': {'low': 323, 'high': 483},
                'confidence': 0.95
            }
    
    # Test génération contextuelle
    question = "Pour un Ross 308 male"
    entities = {'breed_specific': 'Ross 308', 'sex': 'mâle'}
    classification = MockContextualClassification()
    
    result = generator.generate(question, entities, classification)
    
    print(f"Question: {question}")
    print(f"Type de réponse: {result.response_type}")
    print(f"Confiance: {result.confidence}")
    print(f"Données de poids: {result.weight_data}")
    print(f"Aperçu réponse: {result.response[:200]}...")
    
    # Vérifier que la réponse contient les bonnes données
    if "380-420" in result.response and "Ross 308" in result.response:
        print("✅ SUCCESS: Réponse contextuelle avec données précises générée!")
    else:
        print("❌ FAILED: Données Ross 308 mâle 12j non trouvées dans la réponse")

if __name__ == "__main__":
    test_generator_contextual()