# app/api/v1/pipeline/clarification_manager.py - VERSION AMÉLIORÉE
from __future__ import annotations

import logging
from typing import Iterable, List, Dict, Optional, Tuple
from .intent_registry import get_intent_spec, is_urgent_intent, critical_slots

logger = logging.getLogger(__name__)

class SmartClarificationManager:
    """
    Génère des questions de clarification contextuelles et intelligentes.
    VERSION AMÉLIORÉE avec:
    - Questions adaptées à l'intention détectée
    - Priorisation dynamique selon urgence
    - Options de choix multiples
    - Contextualisation selon extraction partielle
    """

    def __init__(self, max_questions_per_round: int = 3) -> None:
        self.max_questions_per_round = max_questions_per_round
        
        # Templates de questions par domaine d'intention
        self._intent_specific_questions = {
            # PERFORMANCE
            "performance.weight_target": {
                "line": "Quelle lignée génétique ? (Ross 308, Cobb 500, Hubbard, etc.)",
                "age_days": "À quel âge précis en jours ?",
                "sex": "Mâles, femelles ou lot mixte ?",
                "species": "Poulets de chair ou pondeuses ?"
            },
            "performance.fcr_target": {
                "line": "Quelle lignée ? (Ross 308, Cobb 500, etc.)",
                "age_days": "À quel âge voulez-vous évaluer le FCR ?",
                "phase": "Quelle phase d'élevage ? (starter, grower, finisher)"
            },
            "performance.production_rate": {
                "line": "Quelle lignée de pondeuses ? (ISA Brown, Lohmann, Hy-Line)",
                "age_days": "Âge en semaines de ponte ?",
                "housing_system": "Système d'élevage ? (sol, volière, cage)"
            },
            
            # NUTRITION
            "nutrition.protein_requirements": {
                "phase": "Quelle phase ? (starter 0-10j, grower 11-25j, finisher 26j+)",
                "species": "Poulets de chair ou pondeuses ?",
                "objective": "Objectif ? (croissance max, économique, label)"
            },
            "nutrition.feed_consumption": {
                "age_days": "Âge actuel du lot en jours ?",
                "temperature": "Température ambiante moyenne (°C) ?",
                "housing_type": "Type de bâtiment ? (sol, cages, plein air)"
            },
            
            # DIAGNOSTIC
            "diagnosis.performance_issue": {
                "problem_type": "Type de problème ? (croissance, ponte, mortalité, FCR)",
                "duration": "Depuis quand observé ? (jours/semaines)",
                "affected_count": "Combien d'oiseaux affectés ?",
                "symptoms": "Symptômes observés ?"
            },
            "diagnosis.health_issue": {
                "symptoms": "Symptômes principaux ? (diarrhée, respiratoire, nerveux, boiterie)",
                "timeline": "Évolution ? (soudaine, progressive)",
                "mortality_rate": "Taux de mortalité observé (%/jour) ?",
                "age_days": "Âge du lot affecté ?"
            },
            "diagnosis.production_drop": {
                "current_rate": "Taux de ponte actuel (%) ?",
                "previous_rate": "Taux de ponte précédent (%) ?",
                "duration": "Depuis quand la baisse ?",
                "other_symptoms": "Autres symptômes ? (coquilles molles, œufs déformés)"
            },
            
            # ENVIRONNEMENT
            "environment.temperature_control": {
                "age_days": "Âge des oiseaux en jours ?",
                "season": "Saison ? (été, hiver, mi-saison)",
                "housing_type": "Type de bâtiment ? (tunnel, statique, ouvert)",
                "problem": "Problème rencontré ? (trop chaud, trop froid, irrégulier)"
            },
            "environment.ventilation": {
                "building_size": "Dimensions du bâtiment (m x m) ?",
                "effectif": "Effectif total ?",
                "age_days": "Âge moyen du lot ?",
                "problem": "Problème ? (ammoniaque, humidité, température)"
            },
            
            # ÉQUIPEMENTS
            "equipment.feeders": {
                "effectif": "Effectif du lot ?",
                "age_days": "Âge actuel (jours) ?",
                "feeder_type": "Type préféré ? (chaîne, assiettes, autre)",
                "space_available": "Espace disponible (mètres linéaires) ?"
            },
            "equipment.drinkers": {
                "effectif": "Nombre d'oiseaux ?",
                "age_days": "Âge (jours) ?",
                "system_type": "Système souhaité ? (nipples, cloches, autre)",
                "water_pressure": "Pression d'eau disponible (bars) ?"
            },
            
            # ÉCONOMIE
            "economics.iep_calculation": {
                "age_days": "Âge à l'abattage (jours) ?",
                "avg_weight_kg": "Poids vif moyen (kg) ?",
                "fcr": "FCR observé ?",
                "livability_pct": "Taux de viabilité (%) ?"
            },
            "economics.cost_analysis": {
                "feed_price": "Prix aliment actuel (€/tonne) ?",
                "production_system": "Système ? (standard, label, bio)",
                "target_weight": "Poids cible (kg) ?"
            }
        }

        # Questions génériques par champ (fallback)
        self._generic_questions = {
            "species": "Quel type d'élevage ? (poulets de chair, pondeuses, reproducteurs)",
            "line": "Quelle lignée génétique ? (Ross 308, Cobb 500, ISA Brown, Lohmann, etc.)",
            "race": "Quelle race/lignée ? (Ross, Cobb, Hubbard, ISA, Lohmann)",
            "sex": "Quel sexe ? (mâles, femelles, mixte)",
            "sexe": "Mâles, femelles ou lot mixte ?",
            "age_days": "Âge en jours ?",
            "age_jours": "Quel âge en jours ?",
            "phase": "Quelle phase d'élevage ? (starter, grower, finisher)",
            "effectif": "Effectif du lot (nombre d'oiseaux) ?",
            "temperature": "Température ambiante (°C) ?",
            "problem_type": "Type de problème observé ?",
            "symptoms": "Quels symptômes observez-vous ?",
            "duration": "Depuis quand ce problème ?",
            "housing_type": "Type de bâtiment d'élevage ?",
            "feed_type": "Type d'aliment utilisé ?",
            "objective": "Quel est votre objectif ?",
            "jurisdiction": "Dans quel pays/région ?",
            "label": "Quel label/certification ? (Label Rouge, Bio, etc.)"
        }

        # Questions avec choix multiples pour améliorer UX
        self._multiple_choice_questions = {
            "species": {
                "question": "Quel type d'élevage ?",
                "options": ["Poulets de chair (broilers)", "Pondeuses (layers)", "Reproducteurs"]
            },
            "line": {
                "question": "Quelle lignée ?",
                "options": ["Ross 308", "Ross 500", "Cobb 500", "Hubbard", "ISA Brown", "Lohmann", "Hy-Line", "Autre"]
            },
            "sex": {
                "question": "Composition du lot ?",
                "options": ["Mâles uniquement", "Femelles uniquement", "Lot mixte"]
            },
            "phase": {
                "question": "Phase d'élevage ?",
                "options": ["Démarrage (0-10j)", "Croissance (11-25j)", "Finition (26j+)", "Ponte"]
            },
            "problem_type": {
                "question": "Type de problème ?",
                "options": ["Croissance insuffisante", "Baisse de ponte", "Mortalité élevée", "FCR dégradé", "Problème sanitaire"]
            },
            "housing_type": {
                "question": "Type de bâtiment ?",
                "options": ["Tunnel ventilé", "Statique", "Semi-ouvert", "Plein air"]
            }
        }

    # ----------------------------------------------------------------------------
    # PUBLIC API
    # ----------------------------------------------------------------------------
    
    def generate_contextual_questions(
        self,
        missing_fields: Iterable[str],
        intent: str,
        partial_context: Dict,
        question_original: str = "",
        round_number: int = 1,
        use_multiple_choice: bool = True
    ) -> List[Dict[str, any]]:
        """
        Génère des questions contextuelles intelligentes.
        
        Returns:
            List[Dict] avec format: [{"question": str, "field": str, "type": str, "options": List[str]}, ...]
        """
        
        fields = self._normalize_and_prioritize_fields(
            missing_fields, intent, partial_context, question_original
        )
        
        if not fields:
            return []

        questions = []
        intent_questions = self._intent_specific_questions.get(intent, {})
        
        for field in fields[:self.max_questions_per_round]:
            question_obj = self._build_question_object(
                field, intent, intent_questions, use_multiple_choice, partial_context
            )
            if question_obj:
                questions.append(question_obj)
        
        # Adapter le nombre selon urgence
        if is_urgent_intent(intent):
            questions = questions[:2]  # Limiter pour urgences
        
        logger.debug("🤔 Clarifications générées: %d questions pour intent=%s", len(questions), intent)
        return questions

    def generate_simple_questions(
        self,
        missing_fields: Iterable[str],
        intent: str = "general",
        language: Optional[str] = None
    ) -> List[str]:
        """
        Génère des questions simples (format texte) pour compatibilité.
        """
        contextual = self.generate_contextual_questions(missing_fields, intent, {})
        return [q["question"] for q in contextual]

    # ----------------------------------------------------------------------------
    # PRIVATE METHODS
    # ----------------------------------------------------------------------------
    
    def _normalize_and_prioritize_fields(
        self,
        missing_fields: Iterable[str],
        intent: str,
        partial_context: Dict,
        question_original: str
    ) -> List[str]:
        """Normalise et priorise les champs selon l'intention et le contexte"""
        
        fields = list(set(str(f).strip().lower() for f in missing_fields if f))
        if not fields:
            return []

        # Récupérer champs critiques pour cette intention
        critical = set(critical_slots(intent))
        
        # Priorisation intelligente
        prioritized = []
        
        # 1. Champs critiques d'abord
        critical_missing = [f for f in fields if f in critical]
        prioritized.extend(critical_missing)
        
        # 2. Champs liés à l'espèce si manquants (fondamentaux)
        species_fields = ["species", "line", "race"]
        for field in species_fields:
            if field in fields and field not in prioritized:
                prioritized.append(field)
        
        # 3. Champs contextuels selon intention
        if intent.startswith("performance"):
            context_order = ["age_days", "sex", "phase"]
        elif intent.startswith("diagnosis"):
            context_order = ["symptoms", "problem_type", "duration", "age_days"]
        elif intent.startswith("nutrition"):
            context_order = ["phase", "age_days", "objective"]
        elif intent.startswith("equipment"):
            context_order = ["effectif", "age_days"]
        else:
            context_order = ["age_days", "phase"]
        
        for field in context_order:
            if field in fields and field not in prioritized:
                prioritized.append(field)
        
        # 4. Autres champs restants
        remaining = [f for f in fields if f not in prioritized]
        prioritized.extend(remaining)
        
        # 5. Filtrage selon contexte existant
        prioritized = self._filter_by_existing_context(prioritized, partial_context)
        
        return prioritized

    def _filter_by_existing_context(self, fields: List[str], context: Dict) -> List[str]:
        """Filtre les questions selon le contexte déjà disponible"""
        filtered = []
        
        for field in fields:
            # Ne pas redemander ce qui est déjà connu
            if field in context and context[field]:
                continue
            
            # Logique métier : ne pas demander certains champs selon contexte
            if field == "sex" and context.get("species") == "layer":
                continue  # Sexe moins critique pour pondeuses
            
            if field == "phase" and context.get("age_days"):
                continue  # Phase déductible de l'âge
            
            if field in ["race", "breed"] and context.get("line"):
                continue  # Redondant avec lignée
            
            filtered.append(field)
        
        return filtered

    def _build_question_object(
        self,
        field: str,
        intent: str,
        intent_questions: Dict[str, str],
        use_multiple_choice: bool,
        partial_context: Dict
    ) -> Optional[Dict[str, any]]:
        """Construit un objet question complet"""
        
        # Question spécifique à l'intention en priorité
        question_text = intent_questions.get(field)
        
        # Fallback sur question générique
        if not question_text:
            question_text = self._generic_questions.get(field)
        
        # Dernière chance : question basique
        if not question_text:
            question_text = f"Pouvez-vous préciser '{field}' ?"
        
        # Structure de base
        question_obj = {
            "question": question_text,
            "field": field,
            "type": "text",
            "required": True,
            "options": None
        }
        
        # Ajouter choix multiples si disponibles et souhaités
        if use_multiple_choice and field in self._multiple_choice_questions:
            mc = self._multiple_choice_questions[field]
            question_obj.update({
                "type": "multiple_choice",
                "question": mc["question"],
                "options": mc["options"]
            })
            
            # Adapter options selon contexte
            question_obj["options"] = self._adapt_options_to_context(
                field, mc["options"], partial_context
            )
        
        # Ajouter métadonnées
        question_obj["metadata"] = {
            "intent": intent,
            "criticality": "high" if field in critical_slots(intent) else "normal",
            "domain": intent.split('.')[0] if '.' in intent else "general"
        }
        
        return question_obj

    def _adapt_options_to_context(
        self,
        field: str,
        default_options: List[str],
        context: Dict
    ) -> List[str]:
        """Adapte les options selon le contexte existant"""
        
        # Adapter lignées selon espèce connue
        if field == "line" and "species" in context:
            species = context["species"]
            if species == "broiler":
                return ["Ross 308", "Ross 500", "Cobb 500", "Cobb 700", "Hubbard", "Autre"]
            elif species == "layer":
                return ["ISA Brown", "Lohmann Brown", "Hy-Line Brown", "Lohmann White", "Autre"]
        
        # Adapter phases selon espèce
        if field == "phase" and "species" in context:
            species = context["species"]
            if species == "broiler":
                return ["Démarrage (0-10j)", "Croissance (11-25j)", "Finition (26j+)"]
            elif species == "layer":
                return ["Élevage (0-16 sem)", "Pré-ponte (17-20 sem)", "Ponte (21+ sem)"]
        
        return default_options

    # ----------------------------------------------------------------------------
    # QUESTION GENERATION FOR SPECIFIC SCENARIOS
    # ----------------------------------------------------------------------------
    
    def generate_diagnostic_questions(
        self,
        partial_context: Dict,
        urgency_level: str = "normal"
    ) -> List[Dict[str, any]]:
        """Génère des questions spécialisées pour diagnostic"""
        
        questions = []
        
        # Questions urgentes pour diagnostic de santé
        if urgency_level in ["high", "critical"]:
            urgent_fields = ["symptoms", "timeline", "affected_count", "mortality_rate"]
            
            for field in urgent_fields:
                if field not in partial_context:
                    if field == "symptoms":
                        questions.append({
                            "question": "Symptômes observés ?",
                            "field": "symptoms",
                            "type": "multiple_choice",
                            "options": [
                                "Diarrhée/problèmes digestifs",
                                "Problèmes respiratoires",
                                "Troubles neurologiques", 
                                "Boiteries/problèmes locomoteurs",
                                "Picage/cannibalisme",
                                "Mortalité sans symptômes"
                            ],
                            "required": True
                        })
                    elif field == "timeline":
                        questions.append({
                            "question": "Évolution du problème ?",
                            "field": "timeline", 
                            "type": "multiple_choice",
                            "options": [
                                "Apparition soudaine (quelques heures)",
                                "Développement rapide (1-2 jours)",
                                "Évolution progressive (plusieurs jours)",
                                "Problème chronique (semaines)"
                            ],
                            "required": True
                        })
        
        return questions[:3]  # Limiter pour ne pas submerger

    def generate_follow_up_questions(
        self,
        intent: str,
        current_context: Dict
    ) -> List[str]:
        """Génère des questions de suivi selon l'intention et contexte"""
        
        follow_ups = []
        
        if intent.startswith("performance"):
            if "line" in current_context and "age_days" in current_context:
                follow_ups.extend([
                    "Souhaitez-vous aussi connaître le FCR recommandé ?",
                    "Voulez-vous les recommandations nutritionnelles correspondantes ?"
                ])
        
        elif intent.startswith("diagnosis"):
            follow_ups.extend([
                "Avez-vous observé d'autres symptômes ?",
                "Y a-t-il eu des changements récents (aliment, environnement) ?"
            ])
        
        elif intent.startswith("nutrition"):
            follow_ups.extend([
                "Souhaitez-vous optimiser pour la croissance ou l'économie ?",
                "Y a-t-il des contraintes de formulation ?"
            ])
        
        return follow_ups[:2]

    # ----------------------------------------------------------------------------
    # LEGACY COMPATIBILITY
    # ----------------------------------------------------------------------------
    
    def generate(
        self,
        missing_fields: Iterable[str],
        round_number: int = 1,
        language: Optional[str] = None,
        intent: Optional[str] = None,
    ) -> List[str]:
        """Méthode de compatibilité avec l'ancien système"""
        return self.generate_simple_questions(missing_fields, intent or "general", language)


# Alias pour compatibilité
ClarificationManager = SmartClarificationManager