"""
app/api/v1/concision_service.py - SERVICE GÉNÉRATION RESPONSE_VERSIONS

🚀 NOUVEAU v3.7.0: Service pour générer toutes les versions de concision
Compatible avec l'architecture existante expert_services.py
"""

import logging
import time
import hashlib
import json
import re
from typing import Dict, Optional, Any, List
from datetime import datetime, timedelta

import openai

from .expert_models import ConcisionLevel, ConcisionMetrics

logger = logging.getLogger(__name__)

class ConcisionService:
    """Service pour générer différentes versions de réponses selon le niveau de concision"""
    
    def __init__(self):
        self.cache = {}  # Cache simple en mémoire (remplacer par Redis en prod)
        self.cache_ttl = 3600  # 1 heure
        
        # Templates de prompts pour chaque niveau
        self.concision_prompts = {
            ConcisionLevel.ULTRA_CONCISE: {
                "instruction": """
                Réponds en maximum 10-15 mots. Donne uniquement la donnée essentielle.
                Pour une question de poids : réponds juste "XXX-YYYg" ou "XXXg"
                Pour une température : réponds juste "XX°C"
                Pour un oui/non : réponds juste "Oui" ou "Non"
                Pour une quantité : réponds juste le chiffre avec l'unité
                """,
                "max_tokens": 25,
                "temperature": 0.1
            },
            
            ConcisionLevel.CONCISE: {
                "instruction": """
                Réponds en 1-2 phrases courtes maximum. Donne l'information principale avec un minimum de contexte.
                Évite les conseils non demandés.
                Exemple : "Le poids normal est de 350-400g à cet âge."
                """,
                "max_tokens": 80,
                "temperature": 0.2
            },
            
            ConcisionLevel.STANDARD: {
                "instruction": """
                Réponds de manière équilibrée en 2-4 phrases. Donne l'information principale plus quelques conseils pratiques essentiels.
                Évite les répétitions et les conseils génériques excessifs.
                Garde un ton professionnel mais accessible.
                """,
                "max_tokens": 200,
                "temperature": 0.3
            },
            
            ConcisionLevel.DETAILED: {
                "instruction": """
                Réponds de manière complète et détaillée. Inclus les explications, les conseils approfondis,
                les considérations techniques et les recommandations précises.
                C'est la version de référence complète.
                """,
                "max_tokens": 500,
                "temperature": 0.3
            }
        }
    
    async def generate_all_versions(
        self, 
        question: str, 
        base_response: str, 
        context: Dict[str, Any],
        requested_level: ConcisionLevel = ConcisionLevel.CONCISE
    ) -> Dict[str, Any]:
        """
        Génère toutes les versions de concision pour une réponse
        
        Args:
            question: Question originale
            base_response: Réponse de base (généralement la version detailed)
            context: Contexte (language, user_id, etc.)
            requested_level: Niveau demandé pour la réponse principale
            
        Returns:
            Dict avec {
                "versions": {"ultra_concise": "...", "concise": "...", ...},
                "selected_response": "...",
                "metrics": ConcisionMetrics
            }
        """
        start_time = time.time()
        
        try:
            logger.info("🚀 [ConcisionService] Génération versions pour question")
            logger.info(f"   - Question: {question[:50]}...")
            logger.info(f"   - Niveau demandé: {requested_level}")
            logger.info(f"   - Réponse base: {len(base_response)} caractères")
            
            # Vérifier le cache
            cache_key = self._generate_cache_key(question, base_response, context)
            cached_result = self._get_from_cache(cache_key)
            
            if cached_result:
                logger.info("✅ [ConcisionService] Versions récupérées depuis le cache")
                cached_result["metrics"].cache_hit = True
                
                # Sélectionner la réponse selon le niveau demandé
                selected_response = cached_result["versions"].get(
                    requested_level.value, 
                    cached_result["versions"].get("detailed", base_response)
                )
                
                return {
                    "versions": cached_result["versions"],
                    "selected_response": selected_response,
                    "metrics": cached_result["metrics"]
                }
            
            # Génération des versions
            versions = {}
            generation_errors = []
            
            # 1. Version DETAILED = réponse de base
            versions[ConcisionLevel.DETAILED.value] = base_response
            
            # 2. Générer les autres versions
            for level in [ConcisionLevel.STANDARD, ConcisionLevel.CONCISE, ConcisionLevel.ULTRA_CONCISE]:
                try:
                    logger.info(f"🎯 [ConcisionService] Génération niveau: {level.value}")
                    
                    version_response = await self._generate_version(
                        question=question,
                        base_response=base_response,
                        level=level,
                        context=context
                    )
                    
                    versions[level.value] = version_response.strip()
                    logger.info(f"   ✅ {level.value}: {len(version_response)} caractères")
                    
                except Exception as e:
                    logger.warning(f"⚠️ [ConcisionService] Erreur génération {level.value}: {e}")
                    generation_errors.append(f"{level.value}: {str(e)}")
                    
                    # Fallback vers traitement règles simples
                    fallback_response = self._fallback_concision(base_response, level)
                    versions[level.value] = fallback_response
                    logger.info(f"   🔄 {level.value}: fallback utilisé")
            
            # Calculer métriques
            generation_time_ms = int((time.time() - start_time) * 1000)
            
            metrics = ConcisionMetrics(
                generation_time_ms=generation_time_ms,
                versions_generated=len(versions),
                cache_hit=False,
                fallback_used=len(generation_errors) > 0,
                compression_ratios={
                    level: len(content) / len(base_response) 
                    for level, content in versions.items()
                },
                quality_scores={}  # Peut être enrichi plus tard
            )
            
            # Sélectionner la réponse principale
            selected_response = versions.get(
                requested_level.value, 
                versions.get("detailed", base_response)
            )
            
            # Mettre en cache
            cache_data = {
                "versions": versions,
                "metrics": metrics,
                "timestamp": datetime.now().isoformat()
            }
            self._put_in_cache(cache_key, cache_data)
            
            logger.info("✅ [ConcisionService] Génération terminée:")
            logger.info(f"   - Versions: {len(versions)}")
            logger.info(f"   - Temps: {generation_time_ms}ms")
            logger.info(f"   - Erreurs: {len(generation_errors)}")
            logger.info(f"   - Niveau sélectionné: {requested_level.value}")
            
            return {
                "versions": versions,
                "selected_response": selected_response,
                "metrics": metrics
            }
            
        except Exception as e:
            logger.error(f"❌ [ConcisionService] Erreur critique génération versions: {e}")
            
            # Fallback complet
            fallback_versions = self._create_fallback_versions(base_response)
            
            return {
                "versions": fallback_versions,
                "selected_response": fallback_versions.get(
                    requested_level.value, 
                    base_response
                ),
                "metrics": ConcisionMetrics(
                    generation_time_ms=int((time.time() - start_time) * 1000),
                    versions_generated=len(fallback_versions),
                    cache_hit=False,
                    fallback_used=True,
                    compression_ratios={},
                    quality_scores={}
                )
            }
    
    async def _generate_version(
        self,
        question: str,
        base_response: str,
        level: ConcisionLevel,
        context: Dict[str, Any]
    ) -> str:
        """Génère une version spécifique via LLM"""
        
        config = self.concision_prompts[level]
        
        # Construire le prompt
        prompt = f"""Question originale: {question}

Réponse complète à transformer:
{base_response}

{config["instruction"]}

Réécris la réponse selon le niveau {level.value}:"""
        
        try:
            # Appel OpenAI
            response = await openai.ChatCompletion.acreate(
                model="gpt-4o",  # ou le modèle configuré dans expert_services
                messages=[{
                    "role": "user", 
                    "content": prompt
                }],
                max_tokens=config["max_tokens"],
                temperature=config["temperature"]
            )
            
            generated_text = response.choices[0].message.content.strip()
            
            # Validation de base
            if not generated_text or len(generated_text) < 3:
                raise ValueError(f"Réponse générée trop courte: '{generated_text}'")
            
            return generated_text
            
        except Exception as e:
            logger.warning(f"⚠️ [ConcisionService] Erreur LLM {level.value}: {e}")
            raise
    
    def _fallback_concision(self, base_response: str, level: ConcisionLevel) -> str:
        """Fallback avec règles simples si LLM échoue"""
        
        sentences = [s.strip() for s in base_response.split('.') if s.strip()]
        
        if level == ConcisionLevel.ULTRA_CONCISE:
            # Extraire première donnée numérique ou première phrase courte
            for sentence in sentences:
                # Chercher poids
                weight_match = re.search(r'(\d+(?:-\d+)?)\s*(?:grammes?|g\b)', sentence, re.IGNORECASE)
                if weight_match:
                    return f"{weight_match.group(1)}g"
                
                # Chercher température
                temp_match = re.search(r'(\d+(?:-\d+)?)\s*°?C', sentence, re.IGNORECASE)
                if temp_match:
                    return f"{temp_match.group(1)}°C"
                
                # Première phrase courte
                if len(sentence) < 50:
                    return sentence + "."
            
            return sentences[0][:50] + "." if sentences else base_response[:50]
        
        elif level == ConcisionLevel.CONCISE:
            # 1-2 premières phrases, éviter conseils génériques
            good_sentences = []
            for sentence in sentences[:3]:
                if not self._is_generic_advice(sentence):
                    good_sentences.append(sentence)
                if len(good_sentences) >= 2:
                    break
            
            return '. '.join(good_sentences) + "." if good_sentences else sentences[0] + "."
        
        elif level == ConcisionLevel.STANDARD:
            # Enlever seulement les conseils très génériques
            filtered_sentences = []
            for sentence in sentences:
                if not self._is_very_generic_advice(sentence):
                    filtered_sentences.append(sentence)
            
            return '. '.join(filtered_sentences[:4]) + "."
        
        else:  # DETAILED
            return base_response
    
    def _is_generic_advice(self, sentence: str) -> bool:
        """Détecte les conseils génériques à supprimer"""
        generic_patterns = [
            "n'hésitez pas à", "contactez votre vétérinaire", "il est important de",
            "assurez-vous de", "veillez à", "pensez à", "don't hesitate",
            "contact your veterinarian", "make sure to"
        ]
        sentence_lower = sentence.lower()
        return any(pattern in sentence_lower for pattern in generic_patterns)
    
    def _is_very_generic_advice(self, sentence: str) -> bool:
        """Détecte seulement les conseils très génériques"""
        very_generic_patterns = [
            "n'hésitez pas à contacter", "pour plus d'informations",
            "consultez un professionnel", "en cas de doute"
        ]
        sentence_lower = sentence.lower()
        return any(pattern in sentence_lower for pattern in very_generic_patterns)
    
    def _create_fallback_versions(self, base_response: str) -> Dict[str, str]:
        """Crée des versions fallback avec règles simples"""
        
        versions = {}
        
        # Version detailed = base
        versions[ConcisionLevel.DETAILED.value] = base_response
        
        # Autres versions avec fallback
        for level in [ConcisionLevel.STANDARD, ConcisionLevel.CONCISE, ConcisionLevel.ULTRA_CONCISE]:
            versions[level.value] = self._fallback_concision(base_response, level)
        
        return versions
    
    def _generate_cache_key(self, question: str, base_response: str, context: Dict[str, Any]) -> str:
        """Génère une clé de cache unique"""
        content = f"{question}_{base_response}_{context.get('language', 'fr')}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def _get_from_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Récupère depuis le cache simple (remplacer par Redis)"""
        if cache_key in self.cache:
            cached_data = self.cache[cache_key]
            
            # Vérifier TTL
            cache_time = datetime.fromisoformat(cached_data["timestamp"])
            if datetime.now() - cache_time < timedelta(seconds=self.cache_ttl):
                return cached_data
            else:
                # Supprimer entrée expirée
                del self.cache[cache_key]
        
        return None
    
    def _put_in_cache(self, cache_key: str, data: Dict[str, Any]):
        """Met en cache (simple dict, remplacer par Redis)"""
        # Nettoyer cache si trop gros
        if len(self.cache) > 1000:
            # Supprimer les 100 plus anciens
            sorted_keys = sorted(
                self.cache.keys(), 
                key=lambda k: self.cache[k]["timestamp"]
            )
            for key in sorted_keys[:100]:
                del self.cache[key]
        
        self.cache[cache_key] = data
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Statistiques du cache"""
        return {
            "cache_size": len(self.cache),
            "cache_ttl_seconds": self.cache_ttl,
            "oldest_entry": min(
                (self.cache[k]["timestamp"] for k in self.cache), 
                default=None
            ),
            "newest_entry": max(
                (self.cache[k]["timestamp"] for k in self.cache), 
                default=None
            )
        }

# Instance globale du service
concision_service = ConcisionService()

logger.info("✅ [ConcisionService] Service de génération response_versions initialisé")
logger.info("🚀 [ConcisionService] Fonctionnalités:")
logger.info("   - Génération 4 niveaux: ultra_concise, concise, standard, detailed")
logger.info("   - Cache intelligent pour performance")
logger.info("   - Fallback automatique si erreur LLM")
logger.info("   - Métriques détaillées de génération")
logger.info("   - Compatible avec architecture expert_services existante")