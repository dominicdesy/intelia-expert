# -*- coding: utf-8 -*-
"""
redis_cache_manager.py - Gestionnaire de cache Redis CORRIGÉ
Version Enhanced avec cache sémantique STRICT - Corrections appliquées
CORRECTIONS MAJEURES:
- Cache sémantique beaucoup plus strict
- Faux positifs éliminés
- Logique de matching améliorée
- Seuils rehaussés
"""

import json
import hashlib
import logging
import time
import os
import re
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import asdict
import pickle
import zlib

# Redis imports
try:
    import redis.asyncio as redis
    import hiredis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None

logger = logging.getLogger(__name__)

class RAGCacheManager:
    """Gestionnaire de cache Redis optimisé avec cache sémantique STRICT - VERSION CORRIGÉE"""
    
    def __init__(self, redis_url: str = None, default_ttl: int = None):
        # Configuration Redis de base
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379")
        self.default_ttl = default_ttl or int(os.getenv("CACHE_DEFAULT_TTL", "3600"))
        self.client = None
        self.enabled = REDIS_AVAILABLE and os.getenv("CACHE_ENABLED", "true").lower() == "true"
        
        # Limites mémoire depuis variables d'environnement
        self.MAX_VALUE_BYTES = int(os.getenv("CACHE_MAX_VALUE_BYTES", "200000"))
        self.MAX_KEYS_PER_NAMESPACE = int(os.getenv("CACHE_MAX_KEYS_PER_NS", "2000"))
        self.TOTAL_MEMORY_LIMIT_MB = int(os.getenv("CACHE_TOTAL_MEMORY_LIMIT_MB", "150"))
        
        # Seuils d'alerte depuis variables d'environnement
        self.WARNING_THRESHOLD_MB = int(os.getenv("CACHE_WARNING_THRESHOLD_MB", "120"))
        self.PURGE_THRESHOLD_MB = int(os.getenv("CACHE_PURGE_THRESHOLD_MB", "130"))
        self.STATS_LOG_INTERVAL = int(os.getenv("CACHE_STATS_LOG_INTERVAL", "600"))
        
        # TTL configurables via variables d'environnement
        self.ttl_config = {
            "embeddings": int(os.getenv("CACHE_TTL_EMBEDDINGS", "3600")),
            "search_results": int(os.getenv("CACHE_TTL_SEARCHES", "1800")),
            "responses": int(os.getenv("CACHE_TTL_RESPONSES", "1800")),
            "intent_results": int(os.getenv("CACHE_TTL_INTENTS", "3600")),
            "verification": int(os.getenv("CACHE_TTL_VERIFICATION", "1800")),
            "normalized": int(os.getenv("CACHE_TTL_NORMALIZED", "3600"))
        }
        
        # Fonctionnalités configurables via variables d'environnement
        self.ENABLE_COMPRESSION = os.getenv("CACHE_ENABLE_COMPRESSION", "false").lower() == "true"
        self.ENABLE_SEMANTIC_CACHE = os.getenv("CACHE_ENABLE_SEMANTIC", "true").lower() == "true"
        self.ENABLE_FALLBACK_KEYS = os.getenv("CACHE_ENABLE_FALLBACK", "true").lower() == "true"
        self.MAX_SEARCH_CONTENT_LENGTH = int(os.getenv("CACHE_MAX_SEARCH_CONTENT", "300"))
        
        # Configuration purge depuis variables d'environnement
        self.LRU_PURGE_RATIO = float(os.getenv("CACHE_LRU_PURGE_RATIO", "0.4"))
        self.ENABLE_AUTO_PURGE = os.getenv("CACHE_ENABLE_AUTO_PURGE", "true").lower() == "true"
        
        # NOUVEAU: Système d'aliases intelligent
        self.aliases = self._load_intent_aliases()
        self.poultry_keywords = self._build_semantic_vocabulary()
        
        # CORRECTION: Seuils beaucoup plus stricts
        self.SEMANTIC_MIN_KEYWORDS = 3  # Au lieu de 1-2
        self.SEMANTIC_CONTEXT_REQUIRED = True  # Contexte obligatoire
        
        # Mots vides (activés seulement si fallback activé)
        self.stopwords = {
            'le', 'la', 'les', 'un', 'une', 'et', 'ou', 'que', 'est', 'pour',
            'the', 'a', 'and', 'or', 'is', 'are', 'for', 'with', 'in', 'on',
            'quel', 'quelle', 'quels', 'quelles', 'combien', 'comment'
        } if self.ENABLE_FALLBACK_KEYS else set()
        
        # Statistiques enrichies
        self.protection_stats = {
            "oversized_rejects": 0,
            "lru_purges": 0,
            "namespace_limits_hit": 0,
            "memory_warnings": 0,
            "auto_purges": 0,
            "semantic_rejections": 0  # NOUVEAU
        }
        
        self.cache_stats = {
            "exact_hits": 0,
            "semantic_hits": 0,
            "fallback_hits": 0,
            "total_requests": 0,
            "saved_operations": 0,
            "alias_normalizations": 0,
            "keyword_extractions": 0,
            "semantic_false_positives_avoided": 0  # NOUVEAU
        }
        
        # Monitoring
        self.last_memory_check = 0
        self.last_stats_log = 0
        
        # NOUVEAU: Tracking du dernier type de hit
        self.hit_type_last = None
    
    def _load_intent_aliases(self) -> Dict:
        """Charge les aliases depuis intents.json avec fallback robuste"""
        try:
            # Chemins possibles pour intents.json
            possible_paths = [
                os.path.join(os.path.dirname(os.path.abspath(__file__)), "intents.json"),
                "/app/intents.json",
                "./intents.json",
                os.path.join(os.getcwd(), "intents.json")
            ]
            
            for path in possible_paths:
                if os.path.exists(path):
                    with open(path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        aliases = data.get("aliases", {})
                        logger.info(f"Aliases chargés depuis {path}: {len(aliases)} catégories")
                        return aliases
            
            logger.warning("intents.json non trouvé dans les chemins standards")
            return self._get_fallback_aliases()
            
        except Exception as e:
            logger.error(f"Erreur chargement intents.json: {e}")
            return self._get_fallback_aliases()
    
    def _get_fallback_aliases(self) -> Dict:
        """Aliases de base si intents.json indisponible"""
        return {
            "line": {
                "ross 308": ["ross308", "ross-308", "r308", "ross"],
                "cobb 500": ["cobb500", "cobb-500", "c500", "cobb"],
                "hubbard classic": ["classic", "hubbard-classic", "hclassic"]
            },
            "phase": {
                "starter": ["démarrage", "demarrage", "start"],
                "grower": ["croissance", "grow"],
                "finisher": ["finition", "finish"]
            }
        }
    
    def _build_semantic_vocabulary(self) -> Set[str]:
        """CORRIGÉ: Construit le vocabulaire sémantique STRICT"""
        vocabulary = set()
        
        # CORRECTION: Vocabulaire beaucoup plus spécifique
        specific_keywords = {
            # Lignées UNIQUEMENT (pas de termes génériques)
            'ross308', 'cobb500', 'hubbard',
            # Métriques SPÉCIFIQUES (pas de génériques)
            'fcr', 'pv', 'gmd', 'epef',
            # Unités CONTEXTUELLES
            '35j', '21j', '42j'
        }
        vocabulary.update(specific_keywords)
        
        # CORRECTION: Enrichissement depuis aliases avec validation
        if self.aliases:
            for category, aliases_dict in self.aliases.items():
                if category in ['line']:  # UNIQUEMENT les lignées
                    # Ajouter seulement les termes normalisés
                    for main_term in aliases_dict.keys():
                        clean_term = self._clean_term(main_term)
                        if len(clean_term) >= 4:  # Minimum 4 caractères
                            vocabulary.add(clean_term)
        
        logger.info(f"Vocabulaire sémantique STRICT construit: {len(vocabulary)} termes")
        return vocabulary
    
    def _clean_term(self, term: str) -> str:
        """Nettoie un terme pour l'indexation sémantique"""
        if not term:
            return ""
        # Supprimer caractères spéciaux et normaliser
        cleaned = re.sub(r'[^\w\s]', '', term.lower().strip())
        # Supprimer espaces multiples
        cleaned = re.sub(r'\s+', '', cleaned)
        return cleaned
    
    def _normalize_text(self, text: str) -> str:
        """CORRIGÉ: Normalisation moins agressive pour éviter les faux positifs"""
        if not text:
            return ""
        
        # Normalisation de base
        normalized = text.lower().strip()
        normalized = re.sub(r'\s+', ' ', normalized)
        normalized = re.sub(r'[?!.]+$', '', normalized)
        
        # CORRECTION: Supprimer mots interrogatifs SANS affecter le sens principal
        question_words = {'quel', 'quelle', 'comment', 'combien', 'what', 'how', 'which'}
        words = normalized.split()
        # Garder au moins 70% des mots originaux
        min_words_to_keep = max(2, int(len(words) * 0.7))
        
        filtered_words = []
        for word in words:
            if word not in question_words or len(filtered_words) < min_words_to_keep:
                filtered_words.append(word)
        
        normalized = ' '.join(filtered_words)
        
        # CORRECTION: Appliquer les aliases SEULEMENT si pertinent
        if self.aliases and len(normalized.split()) >= 2:  # Minimum 2 mots
            normalized = self._apply_aliases_strict(normalized)
            self.cache_stats["alias_normalizations"] += 1
        
        # Normalisation spécifique aviculture RÉDUITE
        normalized = re.sub(r'\bjours?\b', 'j', normalized)
        normalized = re.sub(r'\bross\s*308\b', 'ross308', normalized)
        normalized = re.sub(r'\bcobb\s*500\b', 'cobb500', normalized)
        
        # CORRECTION: Coller les tokens UNIQUEMENT pour les lignées connues
        known_patterns = [
            (r'(ross)\s+(308)', r'\1\2'),
            (r'(cobb)\s+(500)', r'\1\2'),
            (r'(hubbard)\s+(classic)', r'\1\2')
        ]
        
        for pattern, replacement in known_patterns:
            normalized = re.sub(pattern, replacement, normalized)
        
        return normalized.strip()
    
    def _apply_aliases_strict(self, text: str) -> str:
        """CORRIGÉ: Applique les aliases de façon STRICTE"""
        if not self.aliases:
            return text
        
        result = text
        changes_made = 0
        
        # CORRECTION: Appliquer les aliases UNIQUEMENT pour les lignées
        if 'line' in self.aliases:
            for main_line, aliases in self.aliases['line'].items():
                main_normalized = main_line.replace(' ', '').lower()
                
                # Pattern strict pour la lignée principale
                main_pattern = re.escape(main_line.lower())
                if re.search(rf'\b{main_pattern}\b', result):
                    result = re.sub(rf'\b{main_pattern}\b', main_normalized, result)
                    changes_made += 1
                
                # Patterns stricts pour les aliases VALIDÉS
                for alias in aliases:
                    if alias and len(alias) >= 3:  # Minimum 3 caractères
                        alias_pattern = re.escape(alias.lower())
                        if re.search(rf'\b{alias_pattern}\b', result):
                            result = re.sub(rf'\b{alias_pattern}\b', main_normalized, result)
                            changes_made += 1
        
        # CORRECTION: Log des changements pour debug
        if changes_made > 0:
            logger.debug(f"Aliases appliqués: '{text}' -> '{result}' ({changes_made} changements)")
        
        return result
    
    def _generate_key(self, prefix: str, data: Any, use_semantic: bool = False) -> str:
        """CORRIGÉ: Génère une clé de cache avec validation sémantique STRICTE"""
        if isinstance(data, str):
            # CORRECTION: Cache sémantique BEAUCOUP plus strict
            if use_semantic and self.ENABLE_SEMANTIC_CACHE and prefix in ["response", "intent", "embedding"]:
                keywords = self._extract_semantic_keywords_strict(data)
                
                # CORRECTION: Validation stricte avant génération de clé
                if self._validate_semantic_cache_eligibility(keywords, data):
                    semantic_signature = '|'.join(sorted(keywords))
                    hash_obj = hashlib.md5(semantic_signature.encode('utf-8'))
                    logger.debug(f"Clé sémantique générée: {list(keywords)} pour '{data[:30]}...'")
                    return f"intelia_rag:{prefix}:semantic:{hash_obj.hexdigest()}"
                else:
                    # Rejeter le cache sémantique
                    self.protection_stats["semantic_rejections"] += 1
            
            # Cache normalisé standard
            content = self._normalize_text(data)
        elif isinstance(data, dict):
            # Normaliser les dictionnaires contenant des requêtes
            normalized_dict = data.copy()
            if "query" in normalized_dict:
                normalized_dict["query"] = self._normalize_text(normalized_dict["query"])
            content = json.dumps(normalized_dict, sort_keys=True, separators=(',', ':'))
        else:
            content = str(data)
        
        hash_obj = hashlib.md5(content.encode('utf-8'))
        return f"intelia_rag:{prefix}:simple:{hash_obj.hexdigest()}"
    
    def _extract_semantic_keywords_strict(self, text: str) -> Set[str]:
        """CORRIGÉ: Extraction STRICTE des keywords sémantiques"""
        if not self.ENABLE_SEMANTIC_CACHE:
            return set()
        
        self.cache_stats["keyword_extractions"] += 1
        
        text_lower = text.lower()
        
        # CORRECTION: Extraction par catégories STRICTES
        semantic_components = {
            'line': set(),
            'metric': set(), 
            'context': set(),
            'age': set()
        }
        
        # 1. LIGNÉES (obligatoire pour cache sémantique)
        line_detected = False
        if self.aliases and 'line' in self.aliases:
            for main_line, aliases in self.aliases['line'].items():
                main_clean = self._clean_term(main_line)
                
                # Vérification stricte de présence
                for variant in [main_line] + aliases:
                    if variant.lower() in text_lower:
                        semantic_components['line'].add(main_clean)
                        line_detected = True
                        break
        
        # 2. MÉTRIQUES SPÉCIFIQUES (obligatoire)
        metric_patterns = {
            'fcr': ['fcr', 'conversion', 'indice conversion'],
            'poids': ['poids', 'weight'],
            'température': ['température', 'temperature'],
            'mortalité': ['mortalité', 'mortality']
        }
        
        metric_detected = False
        for metric, variants in metric_patterns.items():
            if any(variant in text_lower for variant in variants):
                semantic_components['metric'].add(metric)
                metric_detected = True
        
        # 3. ÂGE/CONTEXTE (obligatoire pour certaines métriques)
        age_pattern = re.search(r'(\d+)\s*(?:j|jour|day|semaine)', text_lower)
        if age_pattern:
            age_value = age_pattern.group(1)
            semantic_components['age'].add(f"{age_value}j")
            semantic_components['context'].add('age_specified')
        
        # 4. VALIDATION STRICTE: Tous les composants requis doivent être présents
        if not (line_detected and metric_detected):
            logger.debug(f"Cache sémantique rejeté (composants manquants): line={line_detected}, metric={metric_detected}")
            return set()
        
        # 5. Construire l'ensemble final
        all_keywords = set()
        for component_set in semantic_components.values():
            all_keywords.update(component_set)
        
        logger.debug(f"Keywords sémantiques STRICTS extraits: {all_keywords} de '{text[:50]}...'")
        return all_keywords
    
    def _validate_semantic_cache_eligibility(self, keywords: Set[str], original_text: str) -> bool:
        """NOUVEAU: Valide l'éligibilité au cache sémantique"""
        
        # Règle 1: Minimum de keywords requis
        if len(keywords) < self.SEMANTIC_MIN_KEYWORDS:
            logger.debug(f"Rejeté: keywords insuffisants ({len(keywords)} < {self.SEMANTIC_MIN_KEYWORDS})")
            return False
        
        # Règle 2: Au moins une lignée ET une métrique
        has_line = any('ross' in kw or 'cobb' in kw or 'hubbard' in kw for kw in keywords)
        has_metric = any(kw in ['fcr', 'poids', 'température', 'mortalité'] for kw in keywords)
        
        if not (has_line and has_metric):
            logger.debug(f"Rejeté: composants manquants - line={has_line}, metric={has_metric}")
            return False
        
        # Règle 3: Cohérence contextuelle
        text_lower = original_text.lower()
        
        # Si c'est une question sur une lignée spécifique + métrique spécifique, c'est bon
        specific_contexts = [
            ('ross308', 'fcr'), ('cobb500', 'fcr'), 
            ('ross308', 'poids'), ('cobb500', 'poids'),
            ('température', 'ross'), ('température', 'cobb')
        ]
        
        has_specific_context = any(
            all(term in text_lower for term in context) 
            for context in specific_contexts
        )
        
        if not has_specific_context:
            logger.debug(f"Rejeté: contexte non spécifique")
            self.cache_stats["semantic_false_positives_avoided"] += 1
            return False
        
        logger.debug(f"Cache sémantique VALIDÉ pour: {keywords}")
        return True
    
    def _generate_fallback_keys(self, primary_key: str, original_data: Any) -> List[str]:
        """CORRIGÉ: Génère des clés de fallback plus conservatrices"""
        if not self.ENABLE_FALLBACK_KEYS:
            return []
        
        fallback_keys = []
        
        if isinstance(original_data, str):
            # CORRECTION: Version avec normalisation minimale seulement
            minimal_normalized = re.sub(r'\s+', ' ', original_data.lower().strip())
            minimal_normalized = re.sub(r'[?!.]+$', '', minimal_normalized)
            
            if minimal_normalized != self._normalize_text(original_data):
                simple_hash = hashlib.md5(minimal_normalized.encode()).hexdigest()
                fallback_keys.append(f"intelia_rag:response:fallback:{simple_hash}")
        
        return fallback_keys[:1]  # CORRECTION: Une seule clé fallback
    
    async def get_semantic_response(self, query: str, language: str = "fr") -> Optional[str]:
        """CORRIGÉ: Lecture sémantique pure avec validation stricte"""
        if not self.enabled or not self.client or not self.ENABLE_SEMANTIC_CACHE:
            return None
        
        try:
            normalized_query = self._normalize_text(query)
            keywords = self._extract_semantic_keywords_strict(normalized_query)
            
            # CORRECTION: Validation stricte obligatoire
            if not self._validate_semantic_cache_eligibility(keywords, query):
                return None
            
            # Générer clé sémantique uniquement
            semantic_signature = '|'.join(sorted(keywords))
            hash_obj = hashlib.md5(semantic_signature.encode('utf-8'))
            semantic_key = f"intelia_rag:response:semantic:{hash_obj.hexdigest()}"
            
            stored = await self.client.get(semantic_key)
            if stored:
                self.hit_type_last = "semantic"
                self.cache_stats["semantic_hits"] += 1
                logger.info(f"Cache HIT (sémantique STRICT): '{query[:30]}...' -> keywords: {list(keywords)}")
                return stored.decode("utf-8")
            
        except Exception as e:
            logger.warning(f"Erreur get_semantic_response: {e}")
        
        return None
    
    # [Tous les autres methods restent identiques - _get_memory_usage_mb, _check_memory_limits, etc.]
    async def _get_memory_usage_mb(self) -> float:
        """Récupère l'usage mémoire Redis en MB"""
        try:
            info = await self.client.info("memory")
            used_memory = info.get("used_memory", 0)
            return used_memory / (1024 * 1024)
        except:
            return 0.0
    
    # [Le reste des méthodes reste identique...]
    
    async def set_response(self, query: str, context_hash: str, 
                          response: str, language: str = "fr"):
        """CORRIGÉ: Met en cache une réponse avec validation sémantique stricte"""
        if not self.enabled or not self.client:
            return
        
        try:
            cache_data = {
                "query": query,
                "context_hash": context_hash,
                "language": language
            }
            
            response_bytes = response.encode('utf-8')
            
            if not await self._check_size_and_namespace_quota("response", response_bytes):
                return
            
            # Stocker avec cache principal
            key = self._generate_key("response", cache_data, use_semantic=False)
            await self.client.setex(
                key,
                self.ttl_config["responses"],
                response_bytes
            )
            
            # CORRECTION: Stocker cache sémantique SEULEMENT si validation stricte réussit
            if self.ENABLE_SEMANTIC_CACHE:
                keywords = self._extract_semantic_keywords_strict(query)
                if self._validate_semantic_cache_eligibility(keywords, query):
                    semantic_key = self._generate_key("response", query, use_semantic=True)
                    if semantic_key != key:  # Éviter duplication
                        await self.client.setex(
                            semantic_key,
                            self.ttl_config["responses"],
                            response_bytes
                        )
                        logger.debug(f"Cache SET (sémantique STRICT): '{query[:30]}...' -> keywords: {list(keywords)}")
                else:
                    logger.debug(f"Cache sémantique rejeté pour SET: '{query[:30]}...'")
            
            logger.debug(f"Cache SET: réponse '{query[:30]}...' ({len(response_bytes)} bytes)")
            
        except Exception as e:
            logger.warning(f"Erreur écriture cache réponse: {e}")
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """CORRIGÉ: Récupère les statistiques avec nouvelles métriques de validation"""
        if not self.enabled or not self.client:
            return {"enabled": False}
        
        try:
            info = await self.client.info("memory")
            memory_usage_mb = await self._get_memory_usage_mb()
            total_keys = await self.client.dbsize()
            
            # Calculer les taux de hit
            total_requests = max(1, self.cache_stats["total_requests"])
            exact_hit_rate = self.cache_stats["exact_hits"] / total_requests
            semantic_hit_rate = self.cache_stats["semantic_hits"] / total_requests
            fallback_hit_rate = self.cache_stats["fallback_hits"] / total_requests
            total_hit_rate = (self.cache_stats["exact_hits"] + self.cache_stats["semantic_hits"] + self.cache_stats["fallback_hits"]) / total_requests
            
            return {
                "enabled": True,
                "approach": "enhanced_semantic_cache_with_strict_validation_v2.1",
                "memory": {
                    "used_mb": round(memory_usage_mb, 2),
                    "used_human": info.get("used_memory_human", "N/A"),
                    "limit_mb": self.TOTAL_MEMORY_LIMIT_MB,
                    "usage_percent": round((memory_usage_mb / self.TOTAL_MEMORY_LIMIT_MB) * 100, 1)
                },
                "keys": {
                    "total": total_keys,
                    "max_per_namespace": self.MAX_KEYS_PER_NAMESPACE
                },
                "hit_statistics": {
                    "total_requests": total_requests,
                    "exact_hits": self.cache_stats["exact_hits"],
                    "semantic_hits": self.cache_stats["semantic_hits"],
                    "fallback_hits": self.cache_stats["fallback_hits"],
                    "exact_hit_rate": round(exact_hit_rate, 3),
                    "semantic_hit_rate": round(semantic_hit_rate, 3),
                    "fallback_hit_rate": round(fallback_hit_rate, 3),
                    "total_hit_rate": round(total_hit_rate, 3)
                },
                "semantic_validation": {
                    "min_keywords_required": self.SEMANTIC_MIN_KEYWORDS,
                    "context_required": self.SEMANTIC_CONTEXT_REQUIRED,
                    "rejections": self.protection_stats["semantic_rejections"],
                    "false_positives_avoided": self.cache_stats["semantic_false_positives_avoided"]
                },
                "configuration": {
                    "max_value_kb": round(self.MAX_VALUE_BYTES / 1024, 1),
                    "ttl_config_minutes": {k: round(v/60, 1) for k, v in self.ttl_config.items()},
                    "compression_enabled": self.ENABLE_COMPRESSION,
                    "semantic_cache_enabled": self.ENABLE_SEMANTIC_CACHE,
                    "fallback_keys_enabled": self.ENABLE_FALLBACK_KEYS,
                    "auto_purge_enabled": self.ENABLE_AUTO_PURGE
                },
                "semantic_enhancements": {
                    "aliases_categories": len(self.aliases),
                    "vocabulary_size": len(self.poultry_keywords),
                    "alias_normalizations": self.cache_stats["alias_normalizations"],
                    "keyword_extractions": self.cache_stats["keyword_extractions"],
                    "stopwords_count": len(self.stopwords)
                },
                "protection_stats": self.protection_stats,
                "performance": {
                    "saved_operations": self.cache_stats["saved_operations"],
                    "features_enabled": {
                        "compression": self.ENABLE_COMPRESSION,
                        "semantic_cache": self.ENABLE_SEMANTIC_CACHE,
                        "fallback_keys": self.ENABLE_FALLBACK_KEYS,
                        "intelligent_aliases": bool(self.aliases),
                        "strict_semantic_validation": True  # NOUVEAU
                    }
                }
            }
            
        except Exception as e:
            logger.warning(f"Erreur stats cache: {e}")
            return {"enabled": True, "error": str(e)}
    
    # [Autres méthodes restent identiques...]
    async def initialize(self):
        """Initialise la connexion Redis avec affichage des optimisations"""
        if not self.enabled:
            logger.warning("Cache Redis désactivé via CACHE_ENABLED=false")
            return
        
        if not REDIS_AVAILABLE:
            logger.warning("Redis non disponible - cache désactivé")
            self.enabled = False
            return
        
        try:
            self.client = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=False,
                socket_keepalive=True,
                socket_keepalive_options={},
                health_check_interval=60
            )
            
            # Test de connexion
            await self.client.ping()
            
            # Log de la configuration avec CORRECTIONS
            logger.info("Cache Redis Enhanced CORRIGÉ initialisé avec validations strictes:")
            logger.info(f"  - Limite valeur: {self.MAX_VALUE_BYTES/1024:.0f} KB")
            logger.info(f"  - Cache sémantique: {self.ENABLE_SEMANTIC_CACHE} (STRICT MODE)")
            logger.info(f"  - Min keywords requis: {self.SEMANTIC_MIN_KEYWORDS}")
            logger.info(f"  - Validation contextuelle: {self.SEMANTIC_CONTEXT_REQUIRED}")
            logger.info(f"  - Aliases chargés: {len(self.aliases)} catégories")
            logger.info(f"  - Vocabulaire sémantique STRICT: {len(self.poultry_keywords)} termes")
            
        except Exception as e:
            logger.warning(f"Erreur connexion Redis: {e} - cache désactivé")
            self.enabled = False


# [Classes wrapper restent identiques...]
class CachedOpenAIEmbedder:
    """Wrapper pour OpenAI Embedder avec cache Redis Enhanced"""
    
    def __init__(self, original_embedder, cache_manager: RAGCacheManager):
        self.original_embedder = original_embedder
        self.cache_manager = cache_manager
    
    async def embed_query(self, text: str) -> List[float]:
        """Embedding avec cache sémantique intelligent"""
        # Essayer le cache d'abord
        cached_embedding = await self.cache_manager.get_embedding(text)
        if cached_embedding:
            return cached_embedding
        
        # Générer si pas en cache
        embedding = await self.original_embedder.embed_query(text)
        
        # Mettre en cache
        if embedding:
            await self.cache_manager.set_embedding(text, embedding)
        
        return embedding