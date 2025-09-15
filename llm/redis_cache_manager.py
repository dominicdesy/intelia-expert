# -*- coding: utf-8 -*-
"""
redis_cache_manager.py - Gestionnaire de cache Redis optimisé pour performance
Version Enhanced avec intégration des aliases d'intents.json
CORRECTIONS APPLIQUÉES: Cache sémantique STRICT + toutes les fonctionnalités conservées
AMÉLIORATIONS AJOUTÉES:
- Initialisation Redis asynchrone sécurisée avec statut
- Fallback sémantique "line+metric (sans âge)" avec TTL réduit  
- Normalisation étendue pour variantes R-308, C-500
- Métriques fallback_semantic distinctes
"""

import json
import hashlib
import logging
import time
import os
import re
import asyncio
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
    """Gestionnaire de cache Redis optimisé avec cache sémantique intelligent STRICT + Fallback"""
    
    def __init__(self, redis_url: str = None, default_ttl: int = None):
        # Configuration Redis de base
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379")
        self.default_ttl = default_ttl or int(os.getenv("CACHE_DEFAULT_TTL", "3600"))
        self.client = None
        self.enabled = REDIS_AVAILABLE and os.getenv("CACHE_ENABLED", "true").lower() == "true"
        
        # NOUVEAU: Statut d'initialisation pour éviter les accès prématurés
        self.initialized = False
        
        # Limites mémoire depuis variables d'environnement
        self.MAX_VALUE_BYTES = int(os.getenv("CACHE_MAX_VALUE_BYTES", "200000"))
        self.MAX_KEYS_PER_NAMESPACE = int(os.getenv("CACHE_MAX_KEYS_PER_NS", "2000"))
        self.TOTAL_MEMORY_LIMIT_MB = int(os.getenv("CACHE_TOTAL_MEMORY_LIMIT_MB", "150"))
        
        # Seuils d'alerte depuis variables d'environnement
        self.WARNING_THRESHOLD_MB = int(os.getenv("CACHE_WARNING_THRESHOLD_MB", "120"))
        self.PURGE_THRESHOLD_MB = int(os.getenv("CACHE_PURGE_THRESHOLD_MB", "130"))
        self.STATS_LOG_INTERVAL = int(os.getenv("CACHE_STATS_LOG_INTERVAL", "600"))
        
        # TTL configurables via variables d'environnement + NOUVEAU TTL fallback
        self.ttl_config = {
            "embeddings": int(os.getenv("CACHE_TTL_EMBEDDINGS", "3600")),
            "search_results": int(os.getenv("CACHE_TTL_SEARCHES", "1800")),
            "responses": int(os.getenv("CACHE_TTL_RESPONSES", "1800")),
            "intent_results": int(os.getenv("CACHE_TTL_INTENTS", "3600")),
            "verification": int(os.getenv("CACHE_TTL_VERIFICATION", "1800")),
            "normalized": int(os.getenv("CACHE_TTL_NORMALIZED", "3600")),
            "semantic_fallback": int(os.getenv("CACHE_TTL_SEMANTIC_FALLBACK", "900"))  # NOUVEAU: 15min
        }
        
        # Fonctionnalités configurables via variables d'environnement
        self.ENABLE_COMPRESSION = os.getenv("CACHE_ENABLE_COMPRESSION", "false").lower() == "true"
        self.ENABLE_SEMANTIC_CACHE = os.getenv("CACHE_ENABLE_SEMANTIC", "true").lower() == "true"
        self.ENABLE_FALLBACK_KEYS = os.getenv("CACHE_ENABLE_FALLBACK", "true").lower() == "true"
        self.MAX_SEARCH_CONTENT_LENGTH = int(os.getenv("CACHE_MAX_SEARCH_CONTENT", "300"))
        
        # NOUVEAU: Fallback sémantique line+metric sans âge
        self.ENABLE_SEMANTIC_FALLBACK = os.getenv("CACHE_ENABLE_SEMANTIC_FALLBACK", "true").lower() == "true"
        
        # Configuration purge depuis variables d'environnement
        self.LRU_PURGE_RATIO = float(os.getenv("CACHE_LRU_PURGE_RATIO", "0.4"))
        self.ENABLE_AUTO_PURGE = os.getenv("CACHE_ENABLE_AUTO_PURGE", "true").lower() == "true"
        
        # NOUVEAU: Système d'aliases intelligent
        self.aliases = self._load_intent_aliases()
        self.poultry_keywords = self._build_semantic_vocabulary()
        
        # CORRECTION: Seuils beaucoup plus stricts pour validation sémantique
        self.SEMANTIC_MIN_KEYWORDS = int(os.getenv("CACHE_SEMANTIC_MIN_KW", "2"))
        self.SEMANTIC_CONTEXT_REQUIRED = True
        
        # AMÉLIORÉ: Patterns de normalisation étendus pour variantes
        self.extended_line_patterns = {
            # Ross 308 variants
            r'\b(?:ross[\s\-_]*308|r[\s\-_]*308)\b': 'ross308',
            r'\brosse?[\s\-_]*308\b': 'ross308',
            
            # Cobb 500 variants  
            r'\b(?:cobb[\s\-_]*500|c[\s\-_]*500)\b': 'cobb500',
            r'\bcob[\s\-_]*500\b': 'cobb500',
            
            # Hubbard variants
            r'\bhubbard[\s\-_]*classic\b': 'hubbardclassic',
            r'\bhub[\s\-_]*classic\b': 'hubbardclassic'
        }
        
        # Mots vides (activés seulement si fallback activé)
        self.stopwords = {
            'le', 'la', 'les', 'un', 'une', 'et', 'ou', 'que', 'est', 'pour',
            'the', 'a', 'and', 'or', 'is', 'are', 'for', 'with', 'in', 'on',
            'quel', 'quelle', 'quels', 'quelles', 'combien', 'comment'
        } if self.ENABLE_FALLBACK_KEYS else set()
        
        # Statistiques enrichies avec métriques fallback sémantique
        self.protection_stats = {
            "oversized_rejects": 0,
            "lru_purges": 0,
            "namespace_limits_hit": 0,
            "memory_warnings": 0,
            "auto_purges": 0,
            "semantic_rejections": 0,
            "init_failures": 0  # NOUVEAU
        }
        
        self.cache_stats = {
            "exact_hits": 0,
            "semantic_hits": 0,
            "semantic_fallback_hits": 0,  # NOUVEAU
            "fallback_hits": 0,
            "total_requests": 0,
            "saved_operations": 0,
            "alias_normalizations": 0,
            "keyword_extractions": 0,
            "semantic_false_positives_avoided": 0,
            "init_attempts": 0  # NOUVEAU
        }
        
        # Monitoring
        self.last_memory_check = 0
        self.last_stats_log = 0
        
        # Tracking du dernier type de hit
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
                "ross 308": ["ross308", "ross-308", "r308", "ross", "r-308"],
                "cobb 500": ["cobb500", "cobb-500", "c500", "cobb", "c-500"],
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
            'ross308', 'cobb500', 'hubbardclassic',
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
        """AMÉLIORÉ: Nettoie un terme avec garde-fous renforcés"""
        if not term or len(term) < 3:  # NOUVEAU: Garde-fou longueur minimale
            return ""
        
        # Supprimer caractères spéciaux et normaliser
        cleaned = re.sub(r'[^\w\s]', '', term.lower().strip())
        # Supprimer espaces multiples
        cleaned = re.sub(r'\s+', '', cleaned)
        
        # NOUVEAU: Éviter les collisions sur termes trop courts
        if len(cleaned) < 3:
            return ""
            
        return cleaned
    
    async def initialize(self):
        """AMÉLIORÉ: Initialise la connexion Redis avec validation robuste"""
        self.cache_stats["init_attempts"] += 1
        
        if not self.enabled:
            logger.warning("Cache Redis désactivé via CACHE_ENABLED=false")
            self.initialized = False
            return False
        
        if not REDIS_AVAILABLE:
            logger.warning("Redis non disponible - cache désactivé")
            self.enabled = False
            self.initialized = False
            return False
        
        try:
            self.client = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=False,
                socket_keepalive=True,
                socket_keepalive_options={},
                health_check_interval=60,
                socket_connect_timeout=5,  # NOUVEAU: Timeout connexion
                socket_timeout=5           # NOUVEAU: Timeout socket
            )
            
            # Test de connexion avec timeout
            await asyncio.wait_for(self.client.ping(), timeout=3.0)
            
            # NOUVEAU: Marquer comme initialisé
            self.initialized = True
            
            # Log de la configuration avec AMÉLIORATIONS
            logger.info("Cache Redis Enhanced STRICT + Fallback initialisé:")
            logger.info(f"  - Limite valeur: {self.MAX_VALUE_BYTES/1024:.0f} KB")
            logger.info(f"  - Cache sémantique: {self.ENABLE_SEMANTIC_CACHE} (STRICT MODE)")
            logger.info(f"  - Fallback sémantique: {self.ENABLE_SEMANTIC_FALLBACK} (TTL: {self.ttl_config['semantic_fallback']}s)")
            logger.info(f"  - Min keywords requis: {self.SEMANTIC_MIN_KEYWORDS}")
            logger.info(f"  - Patterns lignées étendus: {len(self.extended_line_patterns)}")
            logger.info(f"  - Aliases chargés: {len(self.aliases)} catégories")
            logger.info(f"  - Vocabulaire sémantique: {len(self.poultry_keywords)} termes")
            
            return True
            
        except Exception as e:
            logger.warning(f"Erreur connexion Redis: {e} - cache désactivé")
            self.enabled = False
            self.initialized = False
            self.protection_stats["init_failures"] += 1
            return False
    
    def _is_initialized(self) -> bool:
        """NOUVEAU: Vérifie l'état d'initialisation"""
        return self.enabled and self.initialized and self.client is not None
    
    def _normalize_text_extended(self, text: str) -> str:
        """AMÉLIORÉ: Normalisation avec patterns étendus pour variantes"""
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
        
        # NOUVEAU: Appliquer patterns étendus AVANT les aliases
        for pattern, replacement in self.extended_line_patterns.items():
            normalized = re.sub(pattern, replacement, normalized, flags=re.IGNORECASE)
        
        # CORRECTION: Appliquer les aliases SEULEMENT si pertinent
        if self.aliases and len(normalized.split()) >= 2:  # Minimum 2 mots
            normalized = self._apply_aliases_strict(normalized)
            self.cache_stats["alias_normalizations"] += 1
        
        # Normalisation spécifique aviculture RÉDUITE
        normalized = re.sub(r'\bjours?\b', 'j', normalized)
        
        return normalized.strip()
    
    def _normalize_text(self, text: str) -> str:
        """Wrapper pour compatibilité - utilise la version étendue"""
        return self._normalize_text_extended(text)
    
    def _apply_aliases_strict(self, text: str) -> str:
        """CORRIGÉ: Applique les aliases de façon STRICTE avec garde-fous"""
        if not self.aliases:
            return text
        
        result = text
        changes_made = 0
        
        # CORRECTION: Appliquer les aliases UNIQUEMENT pour les lignées
        if 'line' in self.aliases:
            for main_line, aliases in self.aliases['line'].items():
                main_normalized = main_line.replace(' ', '').lower()
                
                # NOUVEAU: Validation longueur avant application
                if len(main_normalized) < 3:
                    continue
                
                # Pattern strict pour la lignée principale
                main_pattern = re.escape(main_line.lower())
                if re.search(rf'\b{main_pattern}\b', result):
                    result = re.sub(rf'\b{main_pattern}\b', main_normalized, result)
                    changes_made += 1
                
                # Patterns stricts pour les aliases VALIDÉS
                for alias in aliases:
                    if alias and len(alias) >= 3:  # RENFORCÉ: Minimum 3 caractères
                        alias_pattern = re.escape(alias.lower())
                        if re.search(rf'\b{alias_pattern}\b', result):
                            result = re.sub(rf'\b{alias_pattern}\b', main_normalized, result)
                            changes_made += 1
        
        # CORRECTION: Log des changements pour debug
        if changes_made > 0:
            logger.debug(f"Aliases appliqués: '{text}' -> '{result}' ({changes_made} changements)")
        
        return result
    
    def _extract_semantic_keywords_strict(self, text: str) -> Set[str]:
        """CORRIGÉ: Extraction STRICTE des keywords sémantiques"""
        if not self.ENABLE_SEMANTIC_CACHE:
            return set()
        
        self.cache_stats["keyword_extractions"] += 1
        
        text_lower = self._normalize_text_extended(text).lower()
        
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
        
        # 3. ÂGE/CONTEXTE (requis pour strict, optionnel pour fallback)
        age_pattern = re.search(r'(\d+)\s*(?:j|jours?|day|days?|semaines?|semaine|wk|w)', text_lower)
        age_detected = False
        if age_pattern:
            age_value = age_pattern.group(1)
            semantic_components['age'].add(f"{age_value}j")
            semantic_components['context'].add('age_specified')
            age_detected = True
        
        # 4. VALIDATION STRICTE vs FALLBACK
        if not (line_detected and metric_detected):
            logger.debug(f"Cache sémantique rejeté (composants manquants): line={line_detected}, metric={metric_detected}")
            return set()
        
        # 5. Construire l'ensemble final avec métadonnées
        all_keywords = set()
        for component_set in semantic_components.values():
            all_keywords.update(component_set)
        
        # NOUVEAU: Ajouter métadonnée pour fallback
        if not age_detected and line_detected and metric_detected:
            all_keywords.add('_fallback_eligible')
        
        logger.debug(f"Keywords sémantiques STRICTS extraits: {all_keywords} de '{text[:50]}...'")
        return all_keywords
    
    def _extract_semantic_fallback_keywords(self, text: str) -> Set[str]:
        """NOUVEAU: Extraction pour fallback sémantique (line+metric sans âge)"""
        keywords = self._extract_semantic_keywords_strict(text)
        
        # Filtrer pour garder seulement line+metric
        fallback_keywords = set()
        for kw in keywords:
            if any(line in kw for line in ['ross', 'cobb', 'hubbard']):
                fallback_keywords.add(kw)
            elif kw in ['fcr', 'poids', 'température', 'mortalité']:
                fallback_keywords.add(kw)
        
        # Valider minimum line+metric
        has_line = any('ross' in kw or 'cobb' in kw or 'hubbard' in kw for kw in fallback_keywords)
        has_metric = any(kw in ['fcr', 'poids', 'température', 'mortalité'] for kw in fallback_keywords)
        
        if has_line and has_metric:
            fallback_keywords.add('_fallback_mode')
            return fallback_keywords
        
        return set()
    
    def _validate_semantic_cache_eligibility(self, keywords: Set[str], original_text: str) -> bool:
        """NOUVEAU: Valide l'éligibilité au cache sémantique STRICT"""
        
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
        
        # Règle 3: Pour le strict, l'âge est REQUIS (sinon fallback)
        has_age = any('j' in kw and kw != '_fallback_eligible' for kw in keywords)
        
        if not has_age:
            logger.debug(f"Rejeté: âge requis pour cache strict")
            return False  # Sera traité par fallback
        
        # Règle 4: Cohérence contextuelle
        text_lower = self._normalize_text_extended(original_text).lower()
        
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
    
    def _generate_key(self, prefix: str, data: Any, use_semantic: bool = False, 
                     fallback_semantic: bool = False) -> str:
        """AMÉLIORÉ: Génère une clé avec support fallback sémantique"""
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
            
            # NOUVEAU: Cache fallback sémantique (line+metric sans âge)
            if fallback_semantic and self.ENABLE_SEMANTIC_FALLBACK:
                fallback_keywords = self._extract_semantic_fallback_keywords(data)
                
                if len(fallback_keywords) >= 2:  # line + metric minimum
                    fallback_signature = '|'.join(sorted(fallback_keywords))
                    hash_obj = hashlib.md5(fallback_signature.encode('utf-8'))
                    logger.debug(f"Clé fallback sémantique générée: {list(fallback_keywords)} pour '{data[:30]}...'")
                    return f"intelia_rag:{prefix}:semantic_fb:{hash_obj.hexdigest()}"
            
            # Cache normalisé standard
            content = self._normalize_text_extended(data)
        elif isinstance(data, dict):
            # Normaliser les dictionnaires contenant des requêtes
            normalized_dict = data.copy()
            if "query" in normalized_dict:
                normalized_dict["query"] = self._normalize_text_extended(normalized_dict["query"])
            content = json.dumps(normalized_dict, sort_keys=True, separators=(',', ':'))
        else:
            content = str(data)
        
        hash_obj = hashlib.md5(content.encode('utf-8'))
        return f"intelia_rag:{prefix}:simple:{hash_obj.hexdigest()}"
    
    def _generate_fallback_keys(self, primary_key: str, original_data: Any) -> List[str]:
        """CORRIGÉ: Génère des clés de fallback plus conservatrices"""
        if not self.ENABLE_FALLBACK_KEYS:
            return []
        
        fallback_keys = []
        
        if isinstance(original_data, str):
            # CORRECTION: Version avec normalisation minimale seulement
            minimal_normalized = re.sub(r'\s+', ' ', original_data.lower().strip())
            minimal_normalized = re.sub(r'[?!.]+$', '', minimal_normalized)
            
            if minimal_normalized != self._normalize_text_extended(original_data):
                simple_hash = hashlib.md5(minimal_normalized.encode()).hexdigest()
                fallback_keys.append(f"intelia_rag:response:fallback:{simple_hash}")
        
        return fallback_keys[:1]  # CORRECTION: Une seule clé fallback
    
    # CORRECTION 1: Méthode get_semantic_response() dédiée (lookup "pur")
    async def get_semantic_response(self, query: str, language: str = "fr") -> Optional[str]:
        """CORRIGÉ: Lecture sémantique pure avec validation stricte"""
        if not self._is_initialized() or not self.ENABLE_SEMANTIC_CACHE:
            return None
        
        try:
            normalized_query = self._normalize_text_extended(query)
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
    
    async def _get_memory_usage_mb(self) -> float:
        """Récupère l'usage mémoire Redis en MB"""
        try:
            info = await self.client.info("memory")
            used_memory = info.get("used_memory", 0)
            return used_memory / (1024 * 1024)
        except:
            return 0.0
    
    async def _check_memory_limits(self) -> bool:
        """Vérification mémoire avec fréquence configurable"""
        now = time.time()
        
        # Vérifier selon la fréquence configurée
        if now - self.last_memory_check < 60:
            return True
        
        self.last_memory_check = now
        
        try:
            memory_usage_mb = await self._get_memory_usage_mb()
            
            # Log périodique selon l'intervalle configuré
            if now - self.last_stats_log > self.STATS_LOG_INTERVAL:
                self.last_stats_log = now
                logger.info(f"Cache Redis Enhanced: {memory_usage_mb:.1f}MB utilisés / {self.TOTAL_MEMORY_LIMIT_MB}MB limite")
                logger.info(f"Stats sémantiques: {self.cache_stats['semantic_hits']} hits, {self.cache_stats['keyword_extractions']} extractions")
            
            # Alertes selon seuils configurés
            if memory_usage_mb > self.WARNING_THRESHOLD_MB:
                self.protection_stats["memory_warnings"] += 1
                logger.warning(f"Cache Redis proche de la limite: {memory_usage_mb:.1f}MB / {self.TOTAL_MEMORY_LIMIT_MB}MB")
            
            # Purge automatique selon seuil configuré
            if memory_usage_mb > self.PURGE_THRESHOLD_MB and self.ENABLE_AUTO_PURGE:
                self.protection_stats["auto_purges"] += 1
                logger.warning(f"Purge automatique déclenchée: {memory_usage_mb:.1f}MB > {self.PURGE_THRESHOLD_MB}MB")
                
                for namespace in ["response", "search", "intent", "embedding"]:
                    await self._purge_namespace_lru(namespace, int(self.MAX_KEYS_PER_NAMESPACE * self.LRU_PURGE_RATIO))
                
                return True
            
            # Rejet si dépassement critique
            if memory_usage_mb > self.TOTAL_MEMORY_LIMIT_MB:
                logger.error(f"Cache Redis saturé: {memory_usage_mb:.1f}MB > {self.TOTAL_MEMORY_LIMIT_MB}MB")
                return False
            
            return True
            
        except Exception as e:
            logger.warning(f"Erreur vérification mémoire Redis: {e}")
            return True
    
    async def _check_size_and_namespace_quota(self, namespace: str, serialized_data: bytes) -> bool:
        """Vérification taille et quota selon configuration"""
        data_size = len(serialized_data)
        
        # Vérification taille maximale configurée
        if data_size > self.MAX_VALUE_BYTES:
            self.protection_stats["oversized_rejects"] += 1
            logger.warning(f"Valeur rejetée (trop large): {data_size/1024:.1f}KB > {self.MAX_VALUE_BYTES/1024:.1f}KB")
            return False
        
        if not await self._check_memory_limits():
            return False
        
        # Vérification quota namespace configuré
        try:
            key_count = 0
            pattern = f"intelia_rag:{namespace}:*"
            
            cursor = 0
            scan_count = 0
            while cursor != 0 or scan_count == 0:
                cursor, keys = await self.client.scan(cursor, match=pattern, count=100)
                key_count += len(keys)
                scan_count += 1
                
                if scan_count > 10:
                    break
            
            if key_count >= self.MAX_KEYS_PER_NAMESPACE:
                self.protection_stats["namespace_limits_hit"] += 1
                logger.info(f"Quota namespace {namespace} atteint ({key_count}/{self.MAX_KEYS_PER_NAMESPACE}) - Purge LRU")
                
                purge_count = int(self.MAX_KEYS_PER_NAMESPACE * self.LRU_PURGE_RATIO)
                purged_count = await self._purge_namespace_lru(namespace, purge_count)
                self.protection_stats["lru_purges"] += purged_count
                
                if purged_count == 0:
                    logger.warning(f"Échec purge LRU namespace {namespace}")
                    return False
        
        except Exception as e:
            logger.warning(f"Erreur vérification quota namespace {namespace}: {e}")
            return True
        
        return True
    
    async def _purge_namespace_lru(self, namespace: str, target_purge_count: int) -> int:
        """Purge LRU avec ratio configuré"""
        try:
            keys_to_delete = []
            pattern = f"intelia_rag:{namespace}:*"
            
            cursor = 0
            scan_count = 0
            while cursor != 0 or scan_count == 0:
                cursor, keys = await self.client.scan(cursor, match=pattern, count=50)
                
                if keys:
                    pipeline = self.client.pipeline()
                    for key in keys:
                        pipeline.ttl(key)
                    ttls = await pipeline.execute()
                    
                    for key, ttl in zip(keys, ttls):
                        keys_to_delete.append((key, ttl if ttl >= 0 else 0))
                
                scan_count += 1
                if scan_count > 5 or len(keys_to_delete) >= target_purge_count * 2:
                    break
            
            if not keys_to_delete:
                return 0
            
            keys_to_delete.sort(key=lambda x: x[1])
            final_keys = [key for key, _ in keys_to_delete[:target_purge_count]]
            
            if final_keys:
                deleted_count = await self.client.delete(*final_keys)
                logger.info(f"Purge LRU namespace {namespace}: {deleted_count} clés supprimées")
                return deleted_count
            
            return 0
            
        except Exception as e:
            logger.error(f"Erreur purge LRU namespace {namespace}: {e}")
            return 0
    
    def _compress_data(self, data: bytes) -> bytes:
        """Compression selon configuration"""
        if not self.ENABLE_COMPRESSION:
            return data
        
        try:
            compressed = zlib.compress(data, level=1)
            self.cache_stats["saved_operations"] += 1
            return compressed
        except:
            return data
    
    def _decompress_data(self, data: bytes) -> bytes:
        """Décompression selon configuration"""
        if not self.ENABLE_COMPRESSION:
            return data
        
        try:
            return zlib.decompress(data)
        except:
            return data
    
    async def get_embedding(self, text: str) -> Optional[List[float]]:
        """Récupère un embedding avec cache sémantique intelligent"""
        if not self._is_initialized():
            return None
        
        self.cache_stats["total_requests"] += 1
        
        try:
            # Essayer d'abord cache sémantique
            if self.ENABLE_SEMANTIC_CACHE:
                semantic_key = self._generate_key("embedding", text, use_semantic=True)
                cached = await self.client.get(semantic_key)
                
                if cached:
                    decompressed = self._decompress_data(cached)
                    embedding = pickle.loads(decompressed)
                    self.cache_stats["semantic_hits"] += 1
                    logger.debug(f"Cache HIT (sémantique): embedding pour '{text[:30]}...'")
                    return embedding
            
            # Essayer cache simple
            key = self._generate_key("embedding", text, use_semantic=False)
            cached = await self.client.get(key)
            
            if cached:
                decompressed = self._decompress_data(cached)
                embedding = pickle.loads(decompressed)
                self.cache_stats["exact_hits"] += 1
                logger.debug(f"Cache HIT: embedding pour '{text[:30]}...'")
                return embedding
            
            # Essayer fallback keys si activé
            if self.ENABLE_FALLBACK_KEYS:
                fallback_keys = self._generate_fallback_keys(key, text)
                for fallback_key in fallback_keys:
                    cached = await self.client.get(fallback_key)
                    if cached:
                        decompressed = self._decompress_data(cached)
                        embedding = pickle.loads(decompressed)
                        self.cache_stats["fallback_hits"] += 1
                        logger.debug(f"Cache HIT (fallback): embedding pour '{text[:30]}...'")
                        return embedding
            
            logger.debug(f"Cache MISS: embedding pour '{text[:30]}...'")
                
        except Exception as e:
            logger.warning(f"Erreur lecture cache embedding: {e}")
        
        return None
    
    async def set_embedding(self, text: str, embedding: List[float]):
        """Met en cache un embedding avec stockage sémantique intelligent"""
        if not self._is_initialized():
            return
        
        try:
            serialized = pickle.dumps(embedding, protocol=pickle.HIGHEST_PROTOCOL)
            compressed = self._compress_data(serialized)
            
            if not await self._check_size_and_namespace_quota("embedding", compressed):
                return
            
            # Stocker avec clé principale
            key = self._generate_key("embedding", text, use_semantic=False)
            await self.client.setex(
                key, 
                self.ttl_config["embeddings"], 
                compressed
            )
            
            # CORRECTION: Stocker cache sémantique SEULEMENT si validation stricte réussit
            if self.ENABLE_SEMANTIC_CACHE:
                keywords = self._extract_semantic_keywords_strict(text)
                if self._validate_semantic_cache_eligibility(keywords, text):
                    semantic_key = self._generate_key("embedding", text, use_semantic=True)
                    if semantic_key != key:  # Éviter duplication
                        await self.client.setex(
                            semantic_key,
                            self.ttl_config["embeddings"],
                            compressed
                        )
                        logger.debug(f"Cache SET (sémantique STRICT): embedding '{text[:30]}...' -> keywords: {list(keywords)}")
            
            logger.debug(f"Cache SET: embedding pour '{text[:30]}...' ({len(compressed)} bytes)")
            
        except Exception as e:
            logger.warning(f"Erreur écriture cache embedding: {e}")
    
    async def get_response(self, query: str, context_hash: str, 
                          language: str = "fr") -> Optional[str]:
        """AMÉLIORÉ: Récupère une réponse avec cascade strict → fallback → simple"""
        if not self._is_initialized():
            return None
        
        self.cache_stats["total_requests"] += 1
        
        try:
            cache_data = {
                "query": query,
                "context_hash": context_hash,
                "language": language
            }
            
            # 1. Essayer cache sémantique STRICT en premier
            if self.ENABLE_SEMANTIC_CACHE:
                semantic_key = self._generate_key("response", query, use_semantic=True)
                cached = await self.client.get(semantic_key)
                
                if cached:
                    response = cached.decode('utf-8')
                    self.cache_stats["semantic_hits"] += 1
                    self.hit_type_last = "semantic_strict"
                    logger.info(f"Cache HIT (sémantique STRICT): '{query[:30]}...'")
                    return response
            
            # 2. NOUVEAU: Essayer cache fallback sémantique (line+metric sans âge)
            if self.ENABLE_SEMANTIC_FALLBACK:
                fallback_semantic_key = self._generate_key("response", query, fallback_semantic=True)
                cached = await self.client.get(fallback_semantic_key)
                
                if cached:
                    response = cached.decode('utf-8')
                    self.cache_stats["semantic_fallback_hits"] += 1
                    self.hit_type_last = "semantic_fallback"
                    logger.info(f"Cache HIT (sémantique FALLBACK): '{query[:30]}...'")
                    return response
            
            # 3. Essayer cache exact
            key = self._generate_key("response", cache_data, use_semantic=False)
            cached = await self.client.get(key)
            
            if cached:
                response = cached.decode('utf-8')
                self.cache_stats["exact_hits"] += 1
                self.hit_type_last = "exact"
                logger.info(f"Cache HIT (exact): '{query[:30]}...'")
                return response
            
            # 4. Essayer fallback keys traditionnel
            if self.ENABLE_FALLBACK_KEYS:
                fallback_keys = self._generate_fallback_keys(key, query)
                for fallback_key in fallback_keys:
                    cached = await self.client.get(fallback_key)
                    if cached:
                        response = cached.decode('utf-8')
                        self.cache_stats["fallback_hits"] += 1
                        self.hit_type_last = "fallback"
                        logger.info(f"Cache HIT (fallback traditionnel): '{query[:30]}...'")
                        return response
            
            logger.info(f"Cache MISS: '{query[:30]}...'")
                
        except Exception as e:
            logger.warning(f"Erreur lecture cache réponse: {e}")
        
        return None
    
    async def set_response(self, query: str, context_hash: str, 
                          response: str, language: str = "fr"):
        """AMÉLIORÉ: Met en cache avec support fallback sémantique"""
        if not self._is_initialized():
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
            
            # Cache sémantique STRICT (avec âge requis)
            if self.ENABLE_SEMANTIC_CACHE:
                keywords = self._extract_semantic_keywords_strict(query)
                if self._validate_semantic_cache_eligibility(keywords, query):
                    semantic_key = self._generate_key("response", query, use_semantic=True)
                    if semantic_key != key:
                        await self.client.setex(
                            semantic_key,
                            self.ttl_config["responses"],
                            response_bytes
                        )
                        logger.debug(f"Cache SET (sémantique STRICT): '{query[:30]}...' -> keywords: {list(keywords)}")
            
            # NOUVEAU: Cache fallback sémantique (line+metric sans âge, TTL réduit)
            if self.ENABLE_SEMANTIC_FALLBACK:
                fallback_keywords = self._extract_semantic_fallback_keywords(query)
                if len(fallback_keywords) >= 2:
                    fallback_semantic_key = self._generate_key("response", query, fallback_semantic=True)
                    if fallback_semantic_key not in [key, semantic_key if 'semantic_key' in locals() else None]:
                        await self.client.setex(
                            fallback_semantic_key,
                            self.ttl_config["semantic_fallback"],  # TTL réduit (15min)
                            response_bytes
                        )
                        logger.debug(f"Cache SET (sémantique FALLBACK): '{query[:30]}...' -> keywords: {list(fallback_keywords)}")
            
            logger.debug(f"Cache SET: réponse '{query[:30]}...' ({len(response_bytes)} bytes)")
            
        except Exception as e:
            logger.warning(f"Erreur écriture cache réponse: {e}")
    
    async def get_search_results(self, query_vector: List[float], 
                               where_filter: Dict = None, 
                               top_k: int = 10) -> Optional[List[Dict]]:
        """Récupère des résultats de recherche depuis le cache"""
        if not self._is_initialized():
            return None
        
        try:
            vector_hash = hashlib.md5(str(query_vector[:5]).encode()).hexdigest()
            cache_data = {
                "vector_hash": vector_hash,
                "where_filter": where_filter,
                "top_k": top_k
            }
            
            key = self._generate_key("search", cache_data, use_semantic=False)
            cached = await self.client.get(key)
            
            if cached:
                decompressed = self._decompress_data(cached)
                results = pickle.loads(decompressed)
                logger.debug("Cache HIT: résultats de recherche")
                return results
                
        except Exception as e:
            logger.warning(f"Erreur lecture cache recherche: {e}")
        
        return None
    
    async def set_search_results(self, query_vector: List[float], 
                               where_filter: Dict, top_k: int, 
                               results: List[Dict]):
        """Met en cache des résultats de recherche"""
        if not self._is_initialized():
            return
        
        try:
            vector_hash = hashlib.md5(str(query_vector[:5]).encode()).hexdigest()
            cache_data = {
                "vector_hash": vector_hash,
                "where_filter": where_filter,
                "top_k": top_k
            }
            
            limited_results = [
                {
                    "content": r.get("content", "")[:self.MAX_SEARCH_CONTENT_LENGTH],
                    "metadata": {
                        "title": r.get("metadata", {}).get("title", ""),
                        "source": r.get("metadata", {}).get("source", "")
                    },
                    "score": round(r.get("score", 0.0), 3)
                }
                for r in results[:top_k]
            ]
            
            serialized = pickle.dumps(limited_results, protocol=pickle.HIGHEST_PROTOCOL)
            compressed = self._compress_data(serialized)
            
            if not await self._check_size_and_namespace_quota("search", compressed):
                return
            
            key = self._generate_key("search", cache_data, use_semantic=False)
            await self.client.setex(
                key,
                self.ttl_config["search_results"],
                compressed
            )
            logger.debug(f"Cache SET: {len(results)} résultats de recherche ({len(compressed)} bytes)")
            
        except Exception as e:
            logger.warning(f"Erreur écriture cache recherche: {e}")
    
    async def get_intent_result(self, query: str) -> Optional[Dict]:
        """Récupère un résultat d'analyse d'intention avec cache sémantique"""
        if not self._is_initialized():
            return None
        
        try:
            # Cache sémantique en premier si activé
            if self.ENABLE_SEMANTIC_CACHE:
                semantic_key = self._generate_key("intent", query, use_semantic=True)
                cached = await self.client.get(semantic_key)
                
                if cached:
                    decompressed = self._decompress_data(cached)
                    intent_result = pickle.loads(decompressed)
                    self.cache_stats["semantic_hits"] += 1
                    logger.debug(f"Cache HIT (sémantique): intention pour '{query[:30]}...'")
                    return intent_result
            
            # Cache simple
            key = self._generate_key("intent", query, use_semantic=False)
            cached = await self.client.get(key)
            
            if cached:
                decompressed = self._decompress_data(cached)
                intent_result = pickle.loads(decompressed)
                self.cache_stats["exact_hits"] += 1
                logger.debug(f"Cache HIT: analyse d'intention pour '{query[:30]}...'")
                return intent_result
                
        except Exception as e:
            logger.warning(f"Erreur lecture cache intention: {e}")
        
        return None
    
    async def set_intent_result(self, query: str, intent_result: Any):
        """Met en cache un résultat d'analyse d'intention"""
        if not self._is_initialized():
            return
        
        try:
            if hasattr(intent_result, '__dict__'):
                data = {
                    "intent_type": getattr(intent_result, 'intent_type', 'unknown'),
                    "confidence": round(getattr(intent_result, 'confidence', 0.0), 3),
                    "detected_entities": getattr(intent_result, 'detected_entities', {}),
                    "expanded_query": getattr(intent_result, 'expanded_query', "")[:200]
                }
            else:
                data = intent_result
            
            serialized = pickle.dumps(data, protocol=pickle.HIGHEST_PROTOCOL)
            compressed = self._compress_data(serialized)
            
            if not await self._check_size_and_namespace_quota("intent", compressed):
                return
            
            # Stocker cache principal
            key = self._generate_key("intent", query, use_semantic=False)
            await self.client.setex(
                key,
                self.ttl_config["intent_results"],
                compressed
            )
            
            # CORRECTION: Stocker cache sémantique SEULEMENT si validation stricte réussit
            if self.ENABLE_SEMANTIC_CACHE:
                keywords = self._extract_semantic_keywords_strict(query)
                if self._validate_semantic_cache_eligibility(keywords, query):
                    semantic_key = self._generate_key("intent", query, use_semantic=True)
                    if semantic_key != key:
                        await self.client.setex(
                            semantic_key,
                            self.ttl_config["intent_results"],
                            compressed
                        )
            
            logger.debug(f"Cache SET: analyse d'intention '{query[:30]}...' ({len(compressed)} bytes)")
            
        except Exception as e:
            logger.warning(f"Erreur écriture cache intention: {e}")
    
    def generate_context_hash(self, documents: List[Dict]) -> str:
        """Génère un hash du contexte pour le cache"""
        try:
            content_summary = []
            for doc in documents[:2]:
                summary = {
                    "source": doc.get("source", "")[:50],
                    "score_rounded": round(doc.get("score", 0.0), 1)
                }
                content_summary.append(summary)
            
            return hashlib.md5(
                json.dumps(content_summary, sort_keys=True, separators=(',', ':')).encode()
            ).hexdigest()
            
        except Exception as e:
            logger.warning(f"Erreur génération hash contexte: {e}")
            return "fallback_hash"
    
    async def invalidate_pattern(self, pattern: str):
        """Invalide les clés correspondant à un pattern"""
        if not self._is_initialized():
            return
        
        try:
            keys = []
            cursor = 0
            scan_count = 0
            while cursor != 0 or scan_count == 0:
                cursor, batch_keys = await self.client.scan(cursor, match=f"intelia_rag:{pattern}:*", count=100)
                keys.extend(batch_keys)
                scan_count += 1
                if scan_count > 10:
                    break
            
            if keys:
                batch_size = 50
                deleted_total = 0
                for i in range(0, len(keys), batch_size):
                    batch = keys[i:i + batch_size]
                    deleted = await self.client.delete(*batch)
                    deleted_total += deleted
                
                logger.info(f"Invalidé {deleted_total} clés pour pattern {pattern}")
                
        except Exception as e:
            logger.warning(f"Erreur invalidation pattern: {e}")
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """AMÉLIORÉ: Récupère les statistiques avec métriques fallback sémantique"""
        if not self._is_initialized():
            return {"enabled": False, "initialized": False}
        
        try:
            info = await self.client.info("memory")
            memory_usage_mb = await self._get_memory_usage_mb()
            total_keys = await self.client.dbsize()
            
            # Calculer les taux de hit avec fallback sémantique
            total_requests = max(1, self.cache_stats["total_requests"])
            exact_hit_rate = self.cache_stats["exact_hits"] / total_requests
            semantic_hit_rate = self.cache_stats["semantic_hits"] / total_requests
            semantic_fallback_hit_rate = self.cache_stats["semantic_fallback_hits"] / total_requests
            fallback_hit_rate = self.cache_stats["fallback_hits"] / total_requests
            
            total_hit_rate = (
                self.cache_stats["exact_hits"] + 
                self.cache_stats["semantic_hits"] + 
                self.cache_stats["semantic_fallback_hits"] +
                self.cache_stats["fallback_hits"]
            ) / total_requests
            
            return {
                "enabled": True,
                "initialized": self.initialized,
                "approach": "enhanced_semantic_cache_with_strict_validation_and_fallback_v2.2",
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
                    "semantic_fallback_hits": self.cache_stats["semantic_fallback_hits"],  # NOUVEAU
                    "fallback_hits": self.cache_stats["fallback_hits"],
                    "exact_hit_rate": round(exact_hit_rate, 3),
                    "semantic_hit_rate": round(semantic_hit_rate, 3),
                    "semantic_fallback_hit_rate": round(semantic_fallback_hit_rate, 3),  # NOUVEAU
                    "fallback_hit_rate": round(fallback_hit_rate, 3),
                    "total_hit_rate": round(total_hit_rate, 3),
                    "last_hit_type": self.hit_type_last
                },
                "semantic_validation": {
                    "min_keywords_required": self.SEMANTIC_MIN_KEYWORDS,
                    "context_required": self.SEMANTIC_CONTEXT_REQUIRED,
                    "rejections": self.protection_stats["semantic_rejections"],
                    "false_positives_avoided": self.cache_stats["semantic_false_positives_avoided"],
                    "fallback_enabled": self.ENABLE_SEMANTIC_FALLBACK,
                    "extended_patterns": len(self.extended_line_patterns)
                },
                "configuration": {
                    "max_value_kb": round(self.MAX_VALUE_BYTES / 1024, 1),
                    "ttl_config_minutes": {k: round(v/60, 1) for k, v in self.ttl_config.items()},
                    "compression_enabled": self.ENABLE_COMPRESSION,
                    "semantic_cache_enabled": self.ENABLE_SEMANTIC_CACHE,
                    "semantic_fallback_enabled": self.ENABLE_SEMANTIC_FALLBACK,
                    "fallback_keys_enabled": self.ENABLE_FALLBACK_KEYS,
                    "auto_purge_enabled": self.ENABLE_AUTO_PURGE
                },
                "semantic_enhancements": {
                    "aliases_categories": len(self.aliases),
                    "vocabulary_size": len(self.poultry_keywords),
                    "alias_normalizations": self.cache_stats["alias_normalizations"],
                    "keyword_extractions": self.cache_stats["keyword_extractions"],
                    "stopwords_count": len(self.stopwords),
                    "extended_line_patterns": len(self.extended_line_patterns)
                },
                "protection_stats": self.protection_stats,
                "performance": {
                    "saved_operations": self.cache_stats["saved_operations"],
                    "init_attempts": self.cache_stats["init_attempts"],
                    "features_enabled": {
                        "compression": self.ENABLE_COMPRESSION,
                        "semantic_cache": self.ENABLE_SEMANTIC_CACHE,
                        "semantic_fallback": self.ENABLE_SEMANTIC_FALLBACK,
                        "fallback_keys": self.ENABLE_FALLBACK_KEYS,
                        "intelligent_aliases": bool(self.aliases),
                        "strict_semantic_validation": True,
                        "extended_normalization": True
                    }
                }
            }
            
        except Exception as e:
            logger.warning(f"Erreur stats cache: {e}")
            return {"enabled": True, "initialized": self.initialized, "error": str(e)}
    
    async def debug_semantic_extraction(self, query: str) -> Dict[str, Any]:
        """Debug de l'extraction sémantique pour une requête"""
        try:
            # Normalisation étapes par étapes
            original = query
            normalized = self._normalize_text_extended(query)
            keywords = self._extract_semantic_keywords_strict(query)
            fallback_keywords = self._extract_semantic_fallback_keywords(query)
            
            # Test génération clés
            semantic_key = self._generate_key("response", query, use_semantic=True)
            fallback_semantic_key = self._generate_key("response", query, fallback_semantic=True)
            simple_key = self._generate_key("response", query, use_semantic=False)
            
            # Test existence cache
            semantic_exists = False
            fallback_semantic_exists = False
            simple_exists = False
            if self.client:
                try:
                    semantic_cached = await self.client.get(semantic_key)
                    fallback_semantic_cached = await self.client.get(fallback_semantic_key)
                    simple_cached = await self.client.get(simple_key)
                    semantic_exists = semantic_cached is not None
                    fallback_semantic_exists = fallback_semantic_cached is not None
                    simple_exists = simple_cached is not None
                except:
                    pass
            
            return {
                "original_query": original,
                "normalized_query": normalized,
                "extracted_keywords": list(keywords),
                "fallback_keywords": list(fallback_keywords),
                "keyword_count": len(keywords),
                "fallback_keyword_count": len(fallback_keywords),
                "vocabulary_size": len(self.poultry_keywords),
                "aliases_loaded": len(self.aliases),