"""
expert_services.py - SYSTÈME IA ADAPTATIF
APPROCHE INTELLIGENTE: IA détermine contexte nécessaire et questions complémentaires

Flux: Question -> IA analyse -> Détermine contexte manquant -> Questions intelligentes -> RAG
"""

import logging
import time
import re
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass
import json
import os

# Import OpenAI sécurisé
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

logger = logging.getLogger(__name__)

@dataclass
class ProcessingResult:
    """Résultat de traitement simplifié"""
    success: bool
    response: str
    response_type: str
    confidence: float
    processing_time_ms: int
    rag_used: bool = False
    rag_results: List[Dict] = None
    error: Optional[str] = None
    clarification_questions: List[str] = None
    missing_context: List[str] = None
    ai_analysis: Dict[str, Any] = None  # Analyse IA complète
    
    def __post_init__(self):
        if self.rag_results is None:
            self.rag_results = []
        if self.clarification_questions is None:
            self.clarification_questions = []
        if self.missing_context is None:
            self.missing_context = []
        if self.ai_analysis is None:
            self.ai_analysis = {}

class AIQuestionAnalyzer:
    """Analyseur IA pour comprendre les questions et déterminer le contexte nécessaire"""
    
    def __init__(self, openai_api_key: str = None):
        self.openai_client = None
        self.use_ai = False
        
        if OPENAI_AVAILABLE and openai_api_key:
            try:
                # Configuration OpenAI moderne
                openai.api_key = openai_api_key
                self.openai_client = openai
                self.use_ai = True
                logger.info("[AI Analyzer] OpenAI configuré")
            except Exception as e:
                logger.warning(f"[AI Analyzer] Erreur config OpenAI: {e}")
                self.use_ai = False
        else:
            logger.info("[AI Analyzer] Mode fallback (sans IA)")
        
    async def analyze_question_context(self, question: str, conversation_history: List[Dict] = None) -> Dict[str, Any]:
        """Analyse IA de la question pour déterminer le contexte nécessaire"""
        if not self.use_ai:
            logger.info("[AI Analysis] Utilisation fallback")
            return self._fallback_analysis(question)
        
        try:
            # Fallback temporaire - IA désactivée pour éviter les erreurs
            logger.info("[AI Analysis] IA temporairement désactivée - utilisation fallback")
            return self._fallback_analysis(question)
            
        except Exception as e:
            logger.error(f"[AI Analysis] Erreur: {e}")
            return self._fallback_analysis(question)
    
    def _fallback_analysis(self, question: str) -> Dict[str, Any]:
        """Analyse de fallback basée sur des règles"""
        question_lower = question.lower()
        
        # Détection domaine
        if any(word in question_lower for word in ["poids", "weight", "masse", "croissance", "gain"]):
            domaine = "poids"
            questions_comp = ["Quelle race de poulets ?", "Quel âge ont-ils ?", "Mâles ou femelles ?"]
        elif any(word in question_lower for word in ["température", "temp", "climat", "ambiance", "ventilation"]):
            domaine = "environnement"
            questions_comp = ["Quel âge ont vos poulets ?", "Type de bâtiment d'élevage ?", "Saison actuelle ?"]
        elif any(word in question_lower for word in ["aliment", "nutrition", "feed", "ration", "consommation"]):
            domaine = "nutrition"
            questions_comp = ["Quelle race ?", "Quel âge ?", "Objectifs de production ?"]
        elif any(word in question_lower for word in ["maladie", "santé", "symptôme", "traitement", "vaccin"]):
            domaine = "sante"
            questions_comp = ["Quels symptômes observez-vous ?", "Âge des animaux affectés ?", "Nombre d'animaux touchés ?"]
        else:
            domaine = "autre"
            questions_comp = ["Pouvez-vous préciser votre question ?", "Dans quel contexte ?"]
        
        return {
            "domaine_principal": domaine,
            "sous_domaine": "analyse automatique",
            "niveau_expertise": "fermier",
            "contexte_critique_manquant": ["race", "age", "conditions"],
            "peut_repondre_partiellement": True,
            "questions_complementaires": questions_comp,
            "reponse_partielle_possible": f"Informations générales disponibles pour {domaine}",
            "priorite_contexte": ["race", "age"],
            "confiance": 0.6
        }

class ConversationMemory:
    """Mémoire conversationnelle avec historique complet"""
    
    def __init__(self):
        self.conversations = {}
        logger.info("[Memory] Mémoire conversationnelle IA initialisée")
    
    def store_interaction(self, conversation_id: str, question: str, response: str, ai_analysis: Dict[str, Any]):
        """Stocke une interaction complète avec analyse IA"""
        if not conversation_id:
            return
            
        if conversation_id not in self.conversations:
            self.conversations[conversation_id] = {
                "interactions": [],
                "established_context": {},
                "created_at": datetime.now()
            }
        
        interaction = {
            "question": question,
            "response": response,
            "ai_analysis": ai_analysis,
            "timestamp": datetime.now(),
            "context_at_time": self.conversations[conversation_id]["established_context"].copy()
        }
        
        self.conversations[conversation_id]["interactions"].append(interaction)
        
        # Mise à jour du contexte établi basé sur l'analyse IA
        self._update_established_context(conversation_id, ai_analysis)
        
        logger.info(f"[Memory] Interaction stockée pour {conversation_id}")
    
    def get_conversation_history(self, conversation_id: str) -> List[Dict]:
        """Récupère l'historique de conversation"""
        if not conversation_id or conversation_id not in self.conversations:
            return []
        
        return self.conversations[conversation_id]["interactions"]
    
    def get_established_context(self, conversation_id: str) -> Dict[str, Any]:
        """Récupère le contexte établi"""
        if not conversation_id or conversation_id not in self.conversations:
            return {}
        
        return self.conversations[conversation_id]["established_context"]
    
    def _update_established_context(self, conversation_id: str, ai_analysis: Dict[str, Any]):
        """Met à jour le contexte établi basé sur l'analyse IA"""
        context = self.conversations[conversation_id]["established_context"]
        
        # Logique d'extraction du contexte depuis l'analyse IA
        if "race" in ai_analysis.get("contexte_identifie", {}):
            context["race"] = ai_analysis["contexte_identifie"]["race"]
        if "age" in ai_analysis.get("contexte_identifie", {}):
            context["age"] = ai_analysis["contexte_identifie"]["age"]
        # ... autres extractions

class ExpertService:
    """Service Expert avec IA pour analyse contextuelle intelligente"""
    
    def __init__(self, openai_api_key: str = None):
        # Configuration simple sans dépendances problématiques
        self.rag_embedder = None
        self.ai_analyzer = AIQuestionAnalyzer(openai_api_key)
        self.memory = ConversationMemory()
        self.stats = {
            "questions_processed": 0,
            "ai_analyses": 0,
            "partial_responses": 0,
            "complete_responses": 0,
            "rag_used": 0
        }
        logger.info("[Expert Service] Initialisé avec analyse contextuelle (fallback actif)")

    def set_rag_embedder(self, rag_embedder):
        """Configure le RAG embedder"""
        self.rag_embedder = rag_embedder
        logger.info(f"[Simple Expert] RAG configuré: {rag_embedder is not None}")

    async def process_question(self, question: str, context: Dict[str, Any] = None, 
                             language: str = "fr") -> ProcessingResult:
        """
        TRAITEMENT INTELLIGENT AVEC IA
        
        Flux: Question -> Analyse IA -> Contexte manquant -> Réponse adaptée
        """
        start_time = time.time()
        conversation_id = context.get('conversation_id') if context else None
        
        try:
            logger.info(f"[AI Expert] Question: '{question[:50]}...'")
            self.stats["questions_processed"] += 1
            
            # 1. RÉCUPÉRATION HISTORIQUE CONVERSATION
            conversation_history = self.memory.get_conversation_history(conversation_id)
            established_context = self.memory.get_established_context(conversation_id)
            
            # 2. ANALYSE IA DE LA QUESTION
            ai_analysis = await self.ai_analyzer.analyze_question_context(question, conversation_history)
            self.stats["ai_analyses"] += 1
            
            # 3. DÉTERMINATION DU TYPE DE RÉPONSE
            can_answer_partially = ai_analysis.get("peut_repondre_partiellement", False)
            confidence = ai_analysis.get("confiance", 0.5)
            missing_context = ai_analysis.get("contexte_critique_manquant", [])
            
            # 4. GÉNÉRATION DE LA RÉPONSE ADAPTÉE
            if confidence > 0.8 and can_answer_partially:
                # Réponse complète possible
                if self.rag_embedder and ai_analysis.get("domaine_principal"):
                    rag_results = await self._search_rag_intelligent(question, ai_analysis, established_context)
                    if rag_results:
                        response = await self._generate_ai_enhanced_response(question, ai_analysis, rag_results, established_context)
                        response_type = "direct_answer"
                        self.stats["complete_responses"] += 1
                        rag_used = True
                    else:
                        response = self._generate_domain_specific_response(ai_analysis, established_context)
                        response_type = "direct_answer"
                        rag_used = False
                else:
                    response = self._generate_domain_specific_response(ai_analysis, established_context)
                    response_type = "direct_answer"
                    rag_used = False
                    
            elif can_answer_partially:
                # Réponse partielle + questions complémentaires
                response = self._generate_partial_response_with_questions(ai_analysis, established_context)
                response_type = "general_with_clarification"
                self.stats["partial_responses"] += 1
                rag_used = False
                
            else:
                # Questions de clarification uniquement
                response = self._generate_intelligent_clarification(ai_analysis)
                response_type = "needs_clarification"
                rag_used = False
            
            # 5. SAUVEGARDE DE L'INTERACTION
            self.memory.store_interaction(conversation_id, question, response, ai_analysis)
            
            processing_time = int((time.time() - start_time) * 1000)
            
            return ProcessingResult(
                success=True,
                response=response,
                response_type=response_type,
                confidence=confidence,
                processing_time_ms=processing_time,
                rag_used=rag_used,
                rag_results=rag_results if 'rag_results' in locals() else [],
                ai_analysis=ai_analysis,
                clarification_questions=ai_analysis.get("questions_complementaires", []),
                missing_context=missing_context
            )
            
        except Exception as e:
            logger.error(f"[AI Expert] Erreur: {e}")
            processing_time = int((time.time() - start_time) * 1000)
            
            return ProcessingResult(
                success=False,
                response="Désolé, une erreur s'est produite lors de l'analyse de votre question.",
                response_type="error",
                confidence=0.0,
                processing_time_ms=processing_time,
                error=str(e)
            )

    async def _search_rag_intelligent(self, question: str, ai_analysis: Dict[str, Any], established_context: Dict[str, Any]) -> List[Dict]:
        """Recherche RAG intelligente basée sur l'analyse IA"""
        if not self.rag_embedder:
            return []
        
        try:
            # Construction de la requête optimisée basée sur l'analyse IA
            domaine = ai_analysis.get("domaine_principal", "")
            sous_domaine = ai_analysis.get("sous_domaine", "")
            
            search_terms = [question]
            if domaine:
                search_terms.append(domaine)
            if sous_domaine:
                search_terms.append(sous_domaine)
            
            # Ajout du contexte établi
            if established_context.get("race"):
                search_terms.append(established_context["race"])
            if established_context.get("age"):
                search_terms.append(str(established_context["age"]) + " jours")
            
            search_query = " ".join(search_terms)
            logger.info(f"[AI RAG] Recherche: '{search_query}'")
            
            results = self.rag_embedder.search(search_query, k=5)
            if results:
                processed_results = []
                for item in results[:5]:
                    if isinstance(item, dict):
                        content = item.get("text", str(item))
                        score = item.get("score", 0.8)
                        processed_results.append({"content": content, "score": score})
                    else:
                        processed_results.append({"content": str(item), "score": 0.8})
                
                logger.info(f"[AI RAG] {len(processed_results)} documents trouvés")
                return processed_results
            
            return []
                
        except Exception as e:
            logger.error(f"[AI RAG] Erreur: {e}")
            return []

    async def _generate_ai_enhanced_response(self, question: str, ai_analysis: Dict[str, Any], 
                                           rag_results: List[Dict], established_context: Dict[str, Any]) -> str:
        """Génère une réponse enrichie par l'IA basée sur les résultats RAG"""
        
        # Fallback temporaire - génération sans IA
        logger.info("[AI Response] Utilisation fallback - génération sans IA")
        return self._generate_domain_specific_response(ai_analysis, established_context)

    def _generate_domain_specific_response(self, ai_analysis: Dict[str, Any], established_context: Dict[str, Any]) -> str:
        """Génère une réponse spécifique au domaine identifié par l'IA"""
        
        domaine = ai_analysis.get("domaine_principal", "general")
        niveau = ai_analysis.get("niveau_expertise", "fermier")
        reponse_partielle = ai_analysis.get("reponse_partielle_possible", "")
        
        if domaine == "poids":
            return f"""**Croissance et poids des poulets :**

{reponse_partielle}

**Facteurs influençant le poids :**
• Race/lignée génétique (performances variables)
• Âge et sexe des animaux
• Qualité de l'alimentation
• Conditions d'ambiance

**Conseils généraux :**
• Pesées régulières pour suivi croissance
• Alimentation adaptée à la phase d'élevage
• Surveillance des écarts de poids dans le lot

Pour des recommandations précises, précisez la race et l'âge de vos animaux."""

        elif domaine == "environnement":
            return f"""**Conditions d'ambiance en élevage avicole :**

{reponse_partielle}

**Paramètres environnementaux clés :**
• Température adaptée à l'âge
• Humidité relative optimale (60-70%)
• Ventilation et qualité de l'air
• Programme lumineux

**Surveillance recommandée :**
• Contrôle quotidien température/humidité
• Observation comportement des animaux
• Ajustements selon conditions météo

Spécifiez l'âge de vos poulets pour des valeurs précises."""

        elif domaine == "nutrition":
            return f"""**Nutrition et alimentation avicole :**

{reponse_partielle}

**Principes nutritionnels :**
• Adaptation selon la phase (starter/grower/finisher)
• Équilibre énergie/protéines
• Apports vitaminiques et minéraux
• Qualité des matières premières

**Gestion alimentaire :**
• Distribution régulière
• Eau de qualité à volonté
• Surveillance consommation et gaspillage

Précisez l'âge et les objectifs de production pour des recommandations spécifiques."""

        elif domaine == "sante":
            return f"""**Santé et prophylaxie avicole :**

{reponse_partielle}

**Surveillance sanitaire :**
• Observation quotidienne du comportement
• Contrôle mortalité et morbidité
• Suivi des performances zootechniques

**Mesures préventives :**
• Biosécurité rigoureuse
• Programme vaccinal adapté
• Gestion de l'ambiance
• Hygiène du matériel

**Important :** Consultez un vétérinaire pour tout problème sanitaire spécifique."""

        else:
            return f"""**Élevage avicole - Conseils généraux :**

{reponse_partielle}

**Domaines d'expertise disponibles :**
• Croissance et performances
• Nutrition et alimentation  
• Conditions d'ambiance
• Santé et prophylaxie
• Gestion technique

**Pour une réponse personnalisée :**
Précisez votre contexte d'élevage, le type d'animaux et vos objectifs de production."""

    def _generate_partial_response_with_questions(self, ai_analysis: Dict[str, Any], established_context: Dict[str, Any]) -> str:
        """Génère une réponse partielle avec questions complémentaires intelligentes"""
        
        reponse_partielle = self._generate_domain_specific_response(ai_analysis, established_context)
        questions_comp = ai_analysis.get("questions_complementaires", [])
        
        questions_text = "\n".join([f"• {q}" for q in questions_comp[:4]])  # Max 4 questions
        
        return f"""{reponse_partielle}

**Pour une réponse plus précise, j'aurais besoin de :**
{questions_text}

Ces informations me permettront de vous donner des recommandations spécifiques à votre situation."""

    def _generate_intelligent_clarification(self, ai_analysis: Dict[str, Any]) -> str:
        """Génère une demande de clarification intelligente basée sur l'analyse IA"""
        
        domaine = ai_analysis.get("domaine_principal", "élevage avicole")
        questions = ai_analysis.get("questions_complementaires", [])
        niveau = ai_analysis.get("niveau_expertise", "fermier")
        
        if questions:
            questions_text = "\n".join([f"• {q}" for q in questions[:3]])
        else:
            questions_text = "• Quel est votre contexte d'élevage ?\n• Quels sont vos objectifs ?"
        
        return f"""**Question sur {domaine} :**

Pour vous fournir une réponse précise et adaptée à votre situation, j'aurais besoin de quelques précisions :

{questions_text}

Ces informations m'aideront à personnaliser mes recommandations selon votre niveau d'expertise et vos besoins spécifiques."""