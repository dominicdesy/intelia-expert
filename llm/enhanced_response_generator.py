# -*- coding: utf-8 -*-
"""
enhanced_response_generator.py - Générateur de réponses enrichi avec entités métier
Utilise les entités détectées pour contextualiser et affiner les réponses
"""

import logging
from typing import Dict, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class ContextEnrichment:
    """Enrichissement du contexte basé sur les entités détectées"""
    entity_context: str
    metric_focus: str
    temporal_context: str
    species_focus: str
    performance_indicators: List[str]
    confidence_boosters: List[str]

class EnhancedResponseGenerator:
    """Générateur de réponses enrichi avec contextualisation par entités"""
    
    def __init__(self, client, cache_manager=None):
        self.client = client
        self.cache_manager = cache_manager
        
        # Mapping des entités vers des contextes métier
        self.entity_contexts = {
            "line": {
                "ross": "lignée à croissance rapide, optimisée pour le rendement carcasse",
                "cobb": "lignée équilibrée performance/robustesse, bonne conversion alimentaire", 
                "hubbard": "lignée rustique, adaptée à l'élevage extensif et labels qualité",
                "isa": "lignée ponte, optimisée pour la production d'œufs",
                "lohmann": "lignée ponte, excellence en persistance de ponte"
            },
            "species": {
                "broiler": "poulet de chair, objectifs: poids vif, FCR, rendement carcasse",
                "layer": "poule pondeuse, objectifs: intensité de ponte, qualité œuf, persistance",
                "breeder": "reproducteur, objectifs: fertilité, éclosabilité, viabilité descendance"
            },
            "phase": {
                "starter": "phase démarrage (0-10j), croissance critique, thermorégulation",
                "grower": "phase croissance (11-24j), développement squelettique et musculaire", 
                "finisher": "phase finition (25j+), optimisation du poids final et FCR",
                "laying": "phase ponte, maintien de la production et qualité œuf",
                "breeding": "phase reproduction, optimisation fertilité et éclosabilité"
            }
        }
        
        # Métriques clés par contexte
        self.performance_metrics = {
            "weight": ["poids vif", "gain de poids", "homogénéité", "courbe de croissance"],
            "fcr": ["indice de consommation", "efficacité alimentaire", "coût alimentaire"],
            "mortality": ["mortalité", "viabilité", "causes de mortalité", "prévention"],
            "production": ["intensité de ponte", "pic de ponte", "persistance", "qualité œuf"],
            "feed": ["consommation", "appétence", "digestibilité", "conversion"]
        }
    
    def _build_entity_enrichment(self, intent_result) -> ContextEnrichment:
        """Construit l'enrichissement basé sur les entités détectées"""
        try:
            entities = getattr(intent_result, 'detected_entities', {})
            
            # Contexte des entités
            entity_contexts = []
            
            if "line" in entities:
                line = entities["line"].lower()
                if line in self.entity_contexts["line"]:
                    entity_contexts.append(f"Lignée {entities['line']}: {self.entity_contexts['line'][line]}")
            
            if "species" in entities:
                species = entities["species"].lower()
                if species in self.entity_contexts["species"]:
                    entity_contexts.append(f"Type {entities['species']}: {self.entity_contexts['species'][species]}")
            
            if "phase" in entities:
                phase = entities["phase"].lower()
                if phase in self.entity_contexts["phase"]:
                    entity_contexts.append(f"Phase {entities['phase']}: {self.entity_contexts['phase'][phase]}")
            
            # Focus métrique
            metric_focus = ""
            detected_metrics = []
            for metric, keywords in self.performance_metrics.items():
                if metric in entities or any(kw in intent_result.expanded_query.lower() if hasattr(intent_result, 'expanded_query') else False for kw in keywords):
                    detected_metrics.extend(keywords)
            
            if detected_metrics:
                metric_focus = f"Focus métriques: {', '.join(detected_metrics[:3])}"
            
            # Contexte temporel
            temporal_context = ""
            if "age_days" in entities:
                age = entities["age_days"]
                if isinstance(age, (int, float)):
                    if age <= 7:
                        temporal_context = "Période critique première semaine - Focus thermorégulation et démarrage"
                    elif age <= 21:
                        temporal_context = "Phase de croissance rapide - Développement osseux et musculaire"
                    elif age <= 35:
                        temporal_context = "Phase d'optimisation - Maximisation du gain de poids"
                    else:
                        temporal_context = "Phase de finition - Optimisation FCR et qualité carcasse"
            
            # Focus espèce
            species_focus = ""
            if "species" in entities:
                species = entities["species"].lower()
                if "broiler" in species or "chair" in species:
                    species_focus = "Objectifs chair: poids vif, FCR, rendement, qualité carcasse"
                elif "layer" in species or "ponte" in species:
                    species_focus = "Objectifs ponte: intensité, persistance, qualité œuf, viabilité"
            
            # Indicateurs de performance attendus
            performance_indicators = []
            if "weight" in entities or "poids" in intent_result.expanded_query.lower() if hasattr(intent_result, 'expanded_query') else False:
                performance_indicators.extend(["poids vif", "gain quotidien", "homogénéité du lot"])
            if "fcr" in entities or any(term in intent_result.expanded_query.lower() if hasattr(intent_result, 'expanded_query') else False for term in ["conversion", "indice"]):
                performance_indicators.extend(["FCR", "consommation", "efficacité alimentaire"])
            
            # Éléments de confiance
            confidence_boosters = []
            if entity_contexts:
                confidence_boosters.append("Contexte lignée/espèce identifié")
            if temporal_context:
                confidence_boosters.append("Phase d'élevage précisée")
            if metric_focus:
                confidence_boosters.append("Métriques cibles identifiées")
            
            return ContextEnrichment(
                entity_context="; ".join(entity_contexts),
                metric_focus=metric_focus,
                temporal_context=temporal_context,
                species_focus=species_focus,
                performance_indicators=performance_indicators,
                confidence_boosters=confidence_boosters
            )
            
        except Exception as e:
            logger.warning(f"Erreur construction enrichissement: {e}")
            return ContextEnrichment("", "", "", "", [], [])
    
    def _build_enhanced_prompt(self, query: str, context_docs: List[Dict], 
                              enrichment: ContextEnrichment, 
                              conversation_context: str = "", 
                              language: str = "fr") -> str:
        """Construit un prompt enrichi avec les entités détectées"""
        
        # Contexte documentaire
        context_text = "\n\n".join([
            f"Document {i+1} ({doc.get('genetic_line', 'N/A')} - {doc.get('species', 'N/A')}):\n{doc.get('content', '')[:1000]}"
            for i, doc in enumerate(context_docs[:5])
        ])
        
        # Construction du prompt système enrichi
        system_prompt = f"""Tu es un expert en aviculture spécialisé dans l'accompagnement technique des éleveurs.

CONTEXTE MÉTIER DÉTECTÉ:
{enrichment.entity_context}
{enrichment.species_focus}
{enrichment.temporal_context}
{enrichment.metric_focus}

DIRECTIVES DE RÉPONSE:
1. Base ta réponse UNIQUEMENT sur les documents fournis
2. Intègre le contexte métier détecté dans ta réponse
3. Priorise les métriques identifiées: {', '.join(enrichment.performance_indicators[:3]) if enrichment.performance_indicators else 'N/A'}
4. Adapte le niveau technique au contexte (éleveur professionnel)
5. Fournis des valeurs chiffrées quand disponibles
6. Mentionne les spécificités de lignée/phase si pertinentes

RÈGLE LINGUISTIQUE: Réponds STRICTEMENT en {language}

Si les documents ne contiennent pas l'information demandée, dis-le clairement et suggère des éléments connexes disponibles."""

        # Prompt utilisateur enrichi
        limited_context = conversation_context[:1500] if conversation_context else ""
        
        user_prompt = f"""CONTEXTE CONVERSATIONNEL:
{limited_context}

DOCUMENTS TECHNIQUES (avec métadonnées):
{context_text}

ENRICHISSEMENT DÉTECTÉ:
- Entités métier: {enrichment.entity_context or 'Non spécifiées'}
- Focus performance: {', '.join(enrichment.performance_indicators) if enrichment.performance_indicators else 'Général'}
- Contexte temporel: {enrichment.temporal_context or 'Non spécifié'}

QUESTION ORIGINALE:
{query}

RÉPONSE TECHNIQUE (intégrant le contexte métier détecté):"""

        return system_prompt, user_prompt
    
    async def generate_response(self, query: str, context_docs: List[Dict], 
                              conversation_context: str = "", 
                              language: str = "fr",
                              intent_result=None) -> str:
        """Génère une réponse enrichie avec les entités détectées"""
        try:
            # Vérifier le cache si disponible
            if self.cache_manager:
                context_hash = self.cache_manager.generate_context_hash(context_docs)
                cached_response = await self.cache_manager.get_response(
                    query, context_hash, language
                )
                if cached_response:
                    logger.debug("Cache hit: réponse enrichie")
                    return cached_response
            
            # Construire l'enrichissement
            enrichment = ContextEnrichment("", "", "", "", [], [])
            if intent_result:
                enrichment = self._build_entity_enrichment(intent_result)
            
            # Construire le prompt enrichi
            system_prompt, user_prompt = self._build_enhanced_prompt(
                query, context_docs, enrichment, conversation_context, language
            )
            
            # Génération avec OpenAI
            response = await self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,
                max_tokens=900  # Augmenté pour les réponses enrichies
            )
            
            generated_response = response.choices[0].message.content.strip()
            
            # Post-traitement pour intégrer les éléments manqués
            enhanced_response = self._post_process_response(
                generated_response, enrichment, context_docs
            )
            
            # Mettre en cache si disponible
            if self.cache_manager and enhanced_response:
                context_hash = self.cache_manager.generate_context_hash(context_docs)
                await self.cache_manager.set_response(
                    query, context_hash, enhanced_response, language
                )
            
            return enhanced_response
            
        except Exception as e:
            logger.error(f"Erreur génération réponse enrichie: {e}")
            return "Désolé, je ne peux pas générer une réponse pour cette question."
    
    def _post_process_response(self, response: str, enrichment: ContextEnrichment, 
                              context_docs: List[Dict]) -> str:
        """Post-traitement pour enrichir la réponse"""
        try:
            # Ajouter un résumé de confiance si de bons indicateurs
            confidence_elements = []
            
            # Vérifier si la lignée est mentionnée dans la réponse
            mentioned_lines = []
            for doc in context_docs[:3]:
                line = doc.get('genetic_line', '').lower()
                if line and line in response.lower():
                    mentioned_lines.append(doc.get('genetic_line'))
            
            if mentioned_lines:
                confidence_elements.append(f"Données spécifiques lignée {mentioned_lines[0]}")
            
            # Vérifier si des métriques numériques sont présentes
            import re
            numbers = re.findall(r'\d+[.,]?\d*\s*(?:g|kg|%|j|jour)', response.lower())
            if len(numbers) >= 2:
                confidence_elements.append("Valeurs chiffrées disponibles")
            
            # Ajouter une note de confiance discrète si pertinent
            if len(confidence_elements) >= 2 and len(response) > 200:
                confidence_note = f"\n\n*Réponse basée sur: {', '.join(confidence_elements[:2])}*"
                response += confidence_note
            
            return response
            
        except Exception as e:
            logger.warning(f"Erreur post-traitement: {e}")
            return response


# Fonction utilitaire pour intégration
def create_enhanced_generator(openai_client, cache_manager=None):
    """Factory pour créer le générateur enrichi"""
    return EnhancedResponseGenerator(openai_client, cache_manager)