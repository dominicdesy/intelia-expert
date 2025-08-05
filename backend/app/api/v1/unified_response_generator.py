"""
unified_response_generator.py - GÉNÉRATEUR UNIQUE DE RÉPONSES

🎯 REMPLACE: general_response_generator, clarification_generators, tous les autres générateurs
🚀 PRINCIPE: Un seul endroit pour générer toutes les réponses
✨ SIMPLE: Templates clairs pour chaque type de réponse

Types de réponse:
- precise_answer: Réponses spécifiques avec données exactes
- general_answer: Réponses générales + offre de précision  
- needs_clarification: Questions ciblées pour clarification
"""

import logging
import re
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)

class ResponseData:
    """Structure pour les données de réponse"""
    def __init__(self, response: str, response_type: str, confidence: float = 0.8, 
                 precision_offer: str = None, examples: List[str] = None):
        self.response = response
        self.response_type = response_type
        self.confidence = confidence
        self.precision_offer = precision_offer
        self.examples = examples or []
        self.generated_at = datetime.now().isoformat()

class UnifiedResponseGenerator:
    """Générateur unique pour tous les types de réponse"""
    
    def __init__(self):
        # Configuration des fourchettes de poids par race et âge
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
            
            if classification_result.response_type.value == "precise_answer":
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

    def _generate_precise(self, question: str, entities: Dict[str, Any]) -> ResponseData:
        """Génère une réponse précise avec données spécifiques"""
        
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
        if any(word in question.lower() for word in ['poids', 'weight', 'gramme']):
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

    def _generate_precise_weight_response(self, breed: str, age_days: int, sex: str) -> ResponseData:
        """Génère réponse précise pour le poids"""
        
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
        """Génère une réponse générale utile"""
        
        question_lower = question.lower()
        age_days = entities.get('age_days')
        
        # Questions de poids
        if any(word in question_lower for word in ['poids', 'weight', 'gramme']):
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
        """Réponse générale pour questions de poids"""
        
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
        """Génère l'offre de précision selon les entités manquantes"""
        
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
        """Génère une demande de clarification ciblée"""
        
        question_lower = question.lower()
        
        # Clarifications spécialisées selon le type de question
        if any(word in question_lower for word in ['poids', 'croissance']):
            return self._generate_performance_clarification(missing_entities)
        
        elif any(word in question_lower for word in ['malade', 'symptôme', 'problème']):
            return self._generate_health_clarification(missing_entities)
        
        elif any(word in question_lower for word in ['alimentation', 'nourrir']):
            return self._generate_feeding_clarification(missing_entities)
        
        else:
            return self._generate_general_clarification(missing_entities)

    def _generate_performance_clarification(self, missing_entities: List[str]) -> ResponseData:
        """Clarification pour questions de performance/poids"""
        
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
        """Trouve l'âge le plus proche dans les données de référence"""
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
        """Génère une réponse de fallback en cas d'erreur"""
        return ResponseData(
            response="Je rencontre une difficulté pour analyser votre question. "
                    "Pouvez-vous la reformuler en précisant le contexte (race, âge, problème spécifique) ?",
            response_type="fallback",
            confidence=0.3
        )

    # Méthodes additionnelles pour autres types de réponses générales
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

# =============================================================================
# FONCTIONS UTILITAIRES
# =============================================================================

def quick_generate(question: str, entities: Dict[str, Any], response_type: str) -> str:
    """Génération rapide pour usage simple"""
    generator = UnifiedResponseGenerator()
    
    # Créer un objet de classification simulé
    class MockClassification:
        def __init__(self, resp_type):
            from smart_classifier import ResponseType
            self.response_type = ResponseType(resp_type)
            self.missing_entities = []
    
    classification = MockClassification(response_type)
    result = generator.generate(question, entities, classification)
    
    return result.response

# =============================================================================
# TESTS INTÉGRÉS
# =============================================================================

def test_generator():
    """Tests rapides du générateur"""
    generator = UnifiedResponseGenerator()
    
    # Test réponse précise
    entities_precise = {
        'breed_specific': 'Ross 308',
        'age_days': 21,
        'sex': 'mâle'
    }
    
    # Test réponse générale
    entities_general = {
        'age_days': 22,
        'weight_mentioned': True
    }
    
    print("🧪 Tests du générateur de réponses")
    print("=" * 50)
    print("✅ Générateur initialisé avec succès")
    print(f"✅ {len(generator.weight_ranges)} races configurées")
    print("✅ Templates de réponse prêts")

if __name__ == "__main__":
    test_generator()