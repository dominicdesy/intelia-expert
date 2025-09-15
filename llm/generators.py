# -*- coding: utf-8 -*-
"""
generators.py - Générateurs de réponses enrichis avec entités et cache externe
"""

import logging
import time
from typing import List, Tuple
from data_models import Document
from config import ENTITY_CONTEXTS
from utilities import METRICS

logger = logging.getLogger(__name__)

class EnhancedResponseGenerator:
    """Générateur avec enrichissement d'entités et cache externe + instrumentation sémantique"""
    
    def __init__(self, client, cache_manager = None):
        self.client = client
        self.cache_manager = cache_manager
        self.entity_contexts = ENTITY_CONTEXTS
    
    async def generate_response(self, query: str, context_docs: List[Document], 
                              conversation_context: str = "", language: str = "fr",
                              intent_result=None) -> str:
        """Génère une réponse enrichie avec cache externe + instrumentation sémantique"""
        try:
            # Vérifier le cache externe
            cache_hit_details = {"semantic_reasoning": "", "cache_type": ""}
            if self.cache_manager and self.cache_manager.enabled:
                context_hash = self.cache_manager.generate_context_hash(
                    [self._doc_to_dict(doc) for doc in context_docs]
                )
                cached_response = await self.cache_manager.get_response(
                    query, context_hash, language
                )
                if cached_response:
                    METRICS.cache_hit("response")
                    # MODIFICATION: Tracer le type de cache hit
                    if hasattr(self.cache_manager, 'get_last_cache_details'):
                        try:
                            cache_hit_details = await self.cache_manager.get_last_cache_details()
                            if cache_hit_details.get("semantic_fallback_used"):
                                METRICS.semantic_fallback_used()
                            else:
                                METRICS.semantic_cache_hit("exact")
                        except:
                            pass
                    return cached_response
                METRICS.cache_miss("response")
            
            # Construire enrichissement
            enrichment = self._build_entity_enrichment(intent_result) if intent_result else None
            
            # Générer le prompt enrichi
            system_prompt, user_prompt = self._build_enhanced_prompt(
                query, context_docs, enrichment, conversation_context, language
            )
            
            # Génération
            response = await self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,
                max_tokens=900
            )
            
            generated_response = response.choices[0].message.content.strip()
            
            # MODIFICATION: Mettre en cache avec métadonnées enrichies
            if self.cache_manager and self.cache_manager.enabled:
                context_hash = self.cache_manager.generate_context_hash(
                    [self._doc_to_dict(doc) for doc in context_docs]
                )
                await self.cache_manager.set_response(
                    query, context_hash, generated_response, language,
                    metadata={
                        "generation_time": time.time(),
                        "enrichment_used": bool(enrichment),
                        "conversation_context_used": bool(conversation_context),
                        "intent_detected": str(intent_result.intent_type) if intent_result else None,
                        "entities_found": getattr(intent_result, 'detected_entities', {}) if intent_result else {}
                    }
                )
            
            return generated_response
            
        except Exception as e:
            logger.error(f"Erreur génération réponse enrichie: {e}")
            return "Désolé, je ne peux pas générer une réponse pour cette question."
    
    def _doc_to_dict(self, doc: Document) -> dict:
        """Convertit Document en dict pour cache"""
        result = {
            "content": doc.content,
            "title": doc.metadata.get("title", ""),
            "source": doc.metadata.get("source", ""),
            "score": doc.score
        }
        if doc.explain_score:
            result["explain_score"] = doc.explain_score
        return result
    
    def _build_entity_enrichment(self, intent_result):
        """Construit l'enrichissement basé sur les entités"""
        try:
            entities = getattr(intent_result, 'detected_entities', {})
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
            
            return "; ".join(entity_contexts) if entity_contexts else ""
            
        except Exception as e:
            logger.warning(f"Erreur construction enrichissement: {e}")
            return ""
    
    def _build_enhanced_prompt(self, query: str, context_docs: List[Document], 
                              enrichment: str, conversation_context: str, 
                              language: str) -> Tuple[str, str]:
        """Construit un prompt enrichi"""
        
        context_text = "\n\n".join([
            f"Document {i+1} ({doc.metadata.get('geneticLine', 'N/A')} - {doc.metadata.get('species', 'N/A')}):\n{doc.content[:1000]}"
            for i, doc in enumerate(context_docs[:5])
        ])
        
        system_prompt = f"""Tu es un expert en aviculture spécialisé dans l'accompagnement technique des éleveurs.

CONTEXTE MÉTIER DÉTECTÉ:
{enrichment or 'Contexte général aviculture'}

DIRECTIVES DE RÉPONSE:
1. Base ta réponse UNIQUEMENT sur les documents fournis
2. Intègre le contexte métier détecté dans ta réponse
3. Adapte le niveau technique au contexte (éleveur professionnel)
4. Fournis des valeurs chiffrées quand disponibles
5. Mentionne les spécificités de lignée/phase si pertinentes

RÈGLE LINGUISTIQUE: Réponds STRICTEMENT en {language}

Si les documents ne contiennent pas l'information demandée, dis-le clairement."""

        # MODIFICATION: Contexte conversationnel augmenté
        from config import MAX_CONVERSATION_CONTEXT
        limited_context = conversation_context[:MAX_CONVERSATION_CONTEXT] if conversation_context else ""
        
        user_prompt = f"""CONTEXTE CONVERSATIONNEL:
{limited_context}

DOCUMENTS TECHNIQUES (avec métadonnées):
{context_text}

QUESTION ORIGINALE:
{query}

RÉPONSE TECHNIQUE (intégrant le contexte métier détecté):"""

        return system_prompt, user_prompt