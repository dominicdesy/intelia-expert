# -*- coding: utf-8 -*-
"""
cache_semantic.py - Module de cache sémantique intelligent
Gestion de l'extraction de mots-clés, normalisation et cache sémantique
"""

import os
import re
import json
import hashlib
import logging
import pickle
from typing import Dict, List, Optional, Any, Set, Tuple

logger = logging.getLogger(__name__)

class SemanticCacheManager:
    """Gestionnaire du cache sémantique avec normalisation intelligente"""
    
    def __init__(self, core_cache):
        self.core = core_cache
        
        # Configuration sémantique
        self._load_semantic_config()
        
        # Système d'aliases et vocabulaire
        self.aliases = self._load_intent_aliases()
        self.poultry_keywords = self._build_semantic_vocabulary()
        
        # Patterns de normalisation étendus
        self._load_normalization_patterns()
        
        # Statistiques
        self.cache_stats = {
            "exact_hits": 0,
            "semantic_hits": 0,
            "semantic_fallback_hits": 0,
            "fallback_hits": 0,
            "total_requests": 0,
            "saved_operations": 0,
            "alias_normalizations": 0,
            "keyword_extractions": 0,
            "semantic_false_positives_avoided": 0,
            "init_attempts": 0
        }
        
        # Tracking du dernier type de hit
        self.hit_type_last = None
    
    def _load_semantic_config(self):
        """Charge la configuration sémantique"""
        self.ENABLE_SEMANTIC_CACHE = os.getenv("CACHE_ENABLE_SEMANTIC", "true").lower() == "true"
        self.ENABLE_FALLBACK_KEYS = os.getenv("CACHE_ENABLE_FALLBACK", "true").lower() == "true"
        self.ENABLE_SEMANTIC_FALLBACK = os.getenv("CACHE_ENABLE_SEMANTIC_FALLBACK", "true").lower() == "true"
        self.SEMANTIC_MIN_KEYWORDS = int(os.getenv("CACHE_SEMANTIC_MIN_KW", "2"))
        self.SEMANTIC_CONTEXT_REQUIRED = True
        
        # Mots vides (activés seulement si fallback activé)
        self.stopwords = {
            'le', 'la', 'les', 'un', 'une', 'et', 'ou', 'que', 'est', 'pour',
            'the', 'a', 'and', 'or', 'is', 'are', 'for', 'with', 'in', 'on',
            'quel', 'quelle', 'quels', 'quelles', 'combien', 'comment'
        } if self.ENABLE_FALLBACK_KEYS else set()
    
    def _load_normalization_patterns(self):
        """Charge les patterns de normalisation étendus"""
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
    
    def _load_intent_aliases(self) -> Dict:
        """Charge les aliases depuis intents.json avec fallback robuste"""
        try:
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
        """Construit le vocabulaire sémantique STRICT"""
        vocabulary = set()
        
        # Vocabulaire spécifique
        specific_keywords = {
            # Lignées UNIQUEMENT
            'ross308', 'cobb500', 'hubbardclassic',
            # Métriques SPÉCIFIQUES
            'fcr', 'pv', 'gmd', 'epef',
            # Unités CONTEXTUELLES
            '35j', '21j', '42j'
        }
        vocabulary.update(specific_keywords)
        
        # Enrichissement depuis aliases avec validation
        if self.aliases:
            for category, aliases_dict in self.aliases.items():
                if category in ['line']:  # UNIQUEMENT les lignées
                    for main_term in aliases_dict.keys():
                        clean_term = self._clean_term(main_term)
                        if len(clean_term) >= 4:  # Minimum 4 caractères
                            vocabulary.add(clean_term)
        
        logger.info(f"Vocabulaire sémantique STRICT construit: {len(vocabulary)} termes")
        return vocabulary
    
    def _clean_term(self, term: str) -> str:
        """Nettoie un terme avec garde-fous renforcés"""
        if not term or len(term) < 3:
            return ""
        
        # Supprimer caractères spéciaux et normaliser
        cleaned = re.sub(r'[^\w\s]', '', term.lower().strip())
        # Supprimer espaces multiples
        cleaned = re.sub(r'\s+', '', cleaned)
        
        # Éviter les collisions sur termes trop courts
        if len(cleaned) < 3:
            return ""
            
        return cleaned
    
    def _normalize_text_extended(self, text: str) -> str:
        """Normalisation avec patterns étendus pour variantes"""
        if not text:
            return ""
        
        # Normalisation de base
        normalized = text.lower().strip()
        normalized = re.sub(r'\s+', ' ', normalized)
        normalized = re.sub(r'[?!.]+$', '', normalized)
        
        # Supprimer mots interrogatifs SANS affecter le sens principal
        question_words = {'quel', 'quelle', 'comment', 'combien', 'what', 'how', 'which'}
        words = normalized.split()
        min_words_to_keep = max(2, int(len(words) * 0.7))
        
        filtered_words = []
        for word in words:
            if word not in question_words or len(filtered_words) < min_words_to_keep:
                filtered_words.append(word)
        
        normalized = ' '.join(filtered_words)
        
        # Appliquer patterns étendus AVANT les aliases
        for pattern, replacement in self.extended_line_patterns.items():
            normalized = re.sub(pattern, replacement, normalized, flags=re.IGNORECASE)
        
        # Appliquer les aliases SEULEMENT si pertinent
        if self.aliases and len(normalized.split()) >= 2:
            normalized = self._apply_aliases_strict(normalized)
            self.cache_stats["alias_normalizations"] += 1
        
        # Normalisation spécifique aviculture
        normalized = re.sub(r'\bjours?\b', 'j', normalized)
        
        return normalized.strip()
    
    def _apply_aliases_strict(self, text: str) -> str:
        """Applique les aliases de façon STRICTE avec garde-fous"""
        if not self.aliases:
            return text
        
        result = text
        changes_made = 0
        
        # Appliquer les aliases UNIQUEMENT pour les lignées
        if 'line' in self.aliases:
            for main_line, aliases in self.aliases['line'].items():
                main_normalized = main_line.replace(' ', '').lower()
                
                if len(main_normalized) < 3:
                    continue
                
                # Pattern strict pour la lignée principale
                main_pattern = re.escape(main_line.lower())
                if re.search(rf'\b{main_pattern}\b', result):
                    result = re.sub(rf'\b{main_pattern}\b', main_normalized, result)
                    changes_made += 1
                
                # Patterns stricts pour les aliases VALIDÉS
                for alias in aliases:
                    if alias and len(alias) >= 3:
                        alias_pattern = re.escape(alias.lower())
                        if re.search(rf'\b{alias_pattern}\b', result):
                            result = re.sub(rf'\b{alias_pattern}\b', main_normalized, result)
                            changes_made += 1
        
        if changes_made > 0:
            logger.debug(f"Aliases appliqués: '{text}' -> '{result}' ({changes_made} changements)")
        
        return result
    
    def _extract_semantic_keywords_strict(self, text: str) -> Set[str]:
        """Extraction STRICTE des keywords sémantiques"""
        if not self.ENABLE_SEMANTIC_CACHE:
            return set()
        
        self.cache_stats["keyword_extractions"] += 1
        
        text_lower = self._normalize_text_extended(text).lower()
        
        # Extraction par catégories STRICTES
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
        
        # 3. ÂGE/CONTEXTE
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
        
        # 5. Construire l'ensemble final
        all_keywords = set()
        for component_set in semantic_components.values():
            all_keywords.update(component_set)
        
        # Ajouter métadonnée pour fallback
        if not age_detected and line_detected and metric_detected:
            all_keywords.add('_fallback_eligible')
        
        logger.debug(f"Keywords sémantiques STRICTS extraits: {all_keywords} de '{text[:50]}...'")
        return all_keywords
    
    def _extract_semantic_fallback_keywords(self, text: str) -> Set[str]:
        """Extraction pour fallback sémantique (line+metric sans âge)"""
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
        """Valide l'éligibilité au cache sémantique STRICT"""
        
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
        
        # Règle 3: Pour le strict, l'âge est REQUIS
        has_age = any('j' in kw and kw != '_fallback_eligible' for kw in keywords)
        
        if not has_age:
            logger.debug(f"Rejeté: âge requis pour cache strict")
            return False
        
        # Règle 4: Cohérence contextuelle
        text_lower = self._normalize_text_extended(original_text).lower()
        
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
        """Génère une clé avec support fallback sémantique"""
        if isinstance(data, str):
            # Cache sémantique STRICT
            if use_semantic and self.ENABLE_SEMANTIC_CACHE and prefix in ["response", "intent", "embedding"]:
                keywords = self._extract_semantic_keywords_strict(data)
                
                if self._validate_semantic_cache_eligibility(keywords, data):
                    semantic_signature = '|'.join(sorted(keywords))
                    hash_obj = hashlib.md5(semantic_signature.encode('utf-8'))
                    logger.debug(f"Clé sémantique générée: {list(keywords)} pour '{data[:30]}...'")
                    return f"intelia_rag:{prefix}:semantic:{hash_obj.hexdigest()}"
                else:
                    self.core.protection_stats["semantic_rejections"] += 1
            
            # Cache fallback sémantique
            if fallback_semantic and self.ENABLE_SEMANTIC_FALLBACK:
                fallback_keywords = self._extract_semantic_fallback_keywords(data)
                
                if len(fallback_keywords) >= 2:
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
        """Génère des clés de fallback plus conservatrices"""
        if not self.ENABLE_FALLBACK_KEYS:
            return []
        
        fallback_keys = []
        
        if isinstance(original_data, str):
            # Version avec normalisation minimale seulement
            minimal_normalized = re.sub(r'\s+', ' ', original_data.lower().strip())
            minimal_normalized = re.sub(r'[?!.]+$', '', minimal_normalized)
            
            if minimal_normalized != self._normalize_text_extended(original_data):
                simple_hash = hashlib.md5(minimal_normalized.encode()).hexdigest()
                fallback_keys.append(f"intelia_rag:response:fallback:{simple_hash}")
        
        return fallback_keys[:1]
    
    # === MÉTHODES PUBLIQUES ===
    
    async def get_embedding(self, text: str) -> Optional[List[float]]:
        """Récupère un embedding avec cache sémantique intelligent"""
        if not self.core._is_initialized():
            return None
        
        self.cache_stats["total_requests"] += 1
        
        try:
            # Essayer cache sémantique
            if self.ENABLE_SEMANTIC_CACHE:
                semantic_key = self._generate_key("embedding", text, use_semantic=True)
                cached = await self.core.client.get(semantic_key)
                
                if cached:
                    decompressed = self.core._decompress_data(cached)
                    embedding = pickle.loads(decompressed)
                    self.cache_stats["semantic_hits"] += 1
                    logger.debug(f"Cache HIT (sémantique): embedding pour '{text[:30]}...'")
                    return embedding
            
            # Essayer cache simple
            key = self._generate_key("embedding", text, use_semantic=False)
            cached = await self.core.client.get(key)
            
            if cached:
                decompressed = self.core._decompress_data(cached)
                embedding = pickle.loads(decompressed)
                self.cache_stats["exact_hits"] += 1
                logger.debug(f"Cache HIT: embedding pour '{text[:30]}...'")
                return embedding
            
            # Essayer fallback keys
            if self.ENABLE_FALLBACK_KEYS:
                fallback_keys = self._generate_fallback_keys(key, text)
                for fallback_key in fallback_keys:
                    cached = await self.core.client.get(fallback_key)
                    if cached:
                        decompressed = self.core._decompress_data(cached)
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
        if not self.core._is_initialized():
            return
        
        try:
            serialized = pickle.dumps(embedding, protocol=pickle.HIGHEST_PROTOCOL)
            compressed = self.core._compress_data(serialized)
            
            if not await self.core._check_size_and_namespace_quota("embedding", compressed):
                return
            
            # Stocker avec clé principale
            key = self._generate_key("embedding", text, use_semantic=False)
            await self.core.client.setex(
                key, 
                self.core.ttl_config["embeddings"], 
                compressed
            )
            
            # Stocker cache sémantique SEULEMENT si validation stricte réussit
            if self.ENABLE_SEMANTIC_CACHE:
                keywords = self._extract_semantic_keywords_strict(text)
                if self._validate_semantic_cache_eligibility(keywords, text):
                    semantic_key = self._generate_key("embedding", text, use_semantic=True)
                    if semantic_key != key:
                        await self.core.client.setex(
                            semantic_key,
                            self.core.ttl_config["embeddings"],
                            compressed
                        )
                        logger.debug(f"Cache SET (sémantique STRICT): embedding '{text[:30]}...' -> keywords: {list(keywords)}")
            
            logger.debug(f"Cache SET: embedding pour '{text[:30]}...' ({len(compressed)} bytes)")
            
        except Exception as e:
            logger.warning(f"Erreur écriture cache embedding: {e}")
    
    async def get_response(self, query: str, context_hash: str, 
                          language: str = "fr") -> Optional[str]:
        """Récupère une réponse avec cascade strict → fallback → simple"""
        if not self.core._is_initialized():
            return None
        
        self.cache_stats["total_requests"] += 1
        
        try:
            cache_data = {
                "query": query,
                "context_hash": context_hash,
                "language": language
            }
            
            # 1. Cache sémantique STRICT
            if self.ENABLE_SEMANTIC_CACHE:
                semantic_key = self._generate_key("response", query, use_semantic=True)
                cached = await self.core.client.get(semantic_key)
                
                if cached:
                    response = cached.decode('utf-8')
                    self.cache_stats["semantic_hits"] += 1
                    self.hit_type_last = "semantic_strict"
                    logger.info(f"Cache HIT (sémantique STRICT): '{query[:30]}...'")
                    return response
            
            # 2. Cache fallback sémantique
            if self.ENABLE_SEMANTIC_FALLBACK:
                fallback_semantic_key = self._generate_key("response", query, fallback_semantic=True)
                cached = await self.core.client.get(fallback_semantic_key)
                
                if cached:
                    response = cached.decode('utf-8')
                    self.cache_stats["semantic_fallback_hits"] += 1
                    self.hit_type_last = "semantic_fallback"
                    logger.info(f"Cache HIT (sémantique FALLBACK): '{query[:30]}...'")
                    return response
            
            # 3. Cache exact
            key = self._generate_key("response", cache_data, use_semantic=False)
            cached = await self.core.client.get(key)
            
            if cached:
                response = cached.decode('utf-8')
                self.cache_stats["exact_hits"] += 1
                self.hit_type_last = "exact"
                logger.info(f"Cache HIT (exact): '{query[:30]}...'")
                return response
            
            # 4. Fallback keys traditionnel
            if self.ENABLE_FALLBACK_KEYS:
                fallback_keys = self._generate_fallback_keys(key, query)
                for fallback_key in fallback_keys:
                    cached = await self.core.client.get(fallback_key)
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
        """Met en cache avec support fallback sémantique"""
        if not self.core._is_initialized():
            return
        
        try:
            cache_data = {
                "query": query,
                "context_hash": context_hash,
                "language": language
            }
            
            response_bytes = response.encode('utf-8')
            
            if not await self.core._check_size_and_namespace_quota("response", response_bytes):
                return
            
            # Stocker avec cache principal
            key = self._generate_key("response", cache_data, use_semantic=False)
            await self.core.client.setex(
                key,
                self.core.ttl_config["responses"],
                response_bytes
            )
            
            # Cache sémantique STRICT
            if self.ENABLE_SEMANTIC_CACHE:
                keywords = self._extract_semantic_keywords_strict(query)
                if self._validate_semantic_cache_eligibility(keywords, query):
                    semantic_key = self._generate_key("response", query, use_semantic=True)
                    if semantic_key != key:
                        await self.core.client.setex(
                            semantic_key,
                            self.core.ttl_config["responses"],
                            response_bytes
                        )
                        logger.debug(f"Cache SET (sémantique STRICT): '{query[:30]}...' -> keywords: {list(keywords)}")
            
            # Cache fallback sémantique
            if self.ENABLE_SEMANTIC_FALLBACK:
                fallback_keywords = self._extract_semantic_fallback_keywords(query)
                if len(fallback_keywords) >= 2:
                    fallback_semantic_key = self._generate_key("response", query, fallback_semantic=True)
                    if fallback_semantic_key not in [key, semantic_key if 'semantic_key' in locals() else None]:
                        await self.core.client.setex(
                            fallback_semantic_key,
                            self.core.ttl_config["semantic_fallback"],
                            response_bytes
                        )
                        logger.debug(f"Cache SET (sémantique FALLBACK): '{query[:30]}...' -> keywords: {list(fallback_keywords)}")
            
            logger.debug(f"Cache SET: réponse '{query[:30]}...' ({len(response_bytes)} bytes)")
            
        except Exception as e:
            logger.warning(f"Erreur écriture cache réponse: {e}")
    
    async def get_intent_result(self, query: str) -> Optional[Dict]:
        """Récupère un résultat d'analyse d'intention avec cache sémantique"""
        if not self.core._is_initialized():
            return None
        
        try:
            # Cache sémantique en premier
            if self.ENABLE_SEMANTIC_CACHE:
                semantic_key = self._generate_key("intent", query, use_semantic=True)
                cached = await self.core.client.get(semantic_key)
                
                if cached:
                    decompressed = self.core._decompress_data(cached)
                    intent_result = pickle.loads(decompressed)
                    self.cache_stats["semantic_hits"] += 1
                    logger.debug(f"Cache HIT (sémantique): intention pour '{query[:30]}...'")
                    return intent_result
            
            # Cache simple
            key = self._generate_key("intent", query, use_semantic=False)
            cached = await self.core.client.get(key)
            
            if cached:
                decompressed = self.core._decompress_data(cached)
                intent_result = pickle.loads(decompressed)
                self.cache_stats["exact_hits"] += 1
                logger.debug(f"Cache HIT: analyse d'intention pour '{query[:30]}...'")
                return intent_result
                
        except Exception as e:
            logger.warning(f"Erreur lecture cache intention: {e}")
        
        return None
    
    async def set_intent_result(self, query: str, intent_result: Any):
        """Met en cache un résultat d'analyse d'intention"""
        if not self.core._is_initialized():
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
            compressed = self.core._compress_data(serialized)
            
            if not await self.core._check_size_and_namespace_quota("intent", compressed):
                return
            
            # Stocker cache principal
            key = self._generate_key("intent", query, use_semantic=False)
            await self.core.client.setex(
                key,
                self.core.ttl_config["intent_results"],
                compressed
            )
            
            # Stocker cache sémantique SEULEMENT si validation stricte réussit
            if self.ENABLE_SEMANTIC_CACHE:
                keywords = self._extract_semantic_keywords_strict(query)
                if self._validate_semantic_cache_eligibility(keywords, query):
                    semantic_key = self._generate_key("intent", query, use_semantic=True)
                    if semantic_key != key:
                        await self.core.client.setex(
                            semantic_key,
                            self.core.ttl_config["intent_results"],
                            compressed
                        )
            
            logger.debug(f"Cache SET: analyse d'intention '{query[:30]}...' ({len(compressed)} bytes)")
            
        except Exception as e:
            logger.warning(f"Erreur écriture cache intention: {e}")
    
    async def debug_semantic_extraction(self, query: str) -> Dict[str, Any]:
        """Debug de l'extraction sémantique pour une requête"""
        try:
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
            if self.core.client:
                try:
                    semantic_cached = await self.core.client.get(semantic_key)
                    fallback_semantic_cached = await self.core.client.get(fallback_semantic_key)
                    simple_cached = await self.core.client.get(simple_key)
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
                "semantic_key": semantic_key,
                "fallback_semantic_key": fallback_semantic_key,
                "simple_key": simple_key,
                "semantic_cache_exists": semantic_exists,
                "fallback_semantic_cache_exists": fallback_semantic_exists,
                "simple_cache_exists": simple_exists,
                "is_semantic_eligible": self._validate_semantic_cache_eligibility(keywords, original),
                "validation": {
                    "has_line": any('ross' in kw or 'cobb' in kw or 'hubbard' in kw for kw in keywords),
                    "has_metric": any(kw in ['fcr', 'poids', 'température', 'mortalité'] for kw in keywords),
                    "has_age": any('j' in kw and kw != '_fallback_eligible' for kw in keywords),
                    "min_keywords_met": len(keywords) >= self.SEMANTIC_MIN_KEYWORDS
                },
                "extended_patterns_applied": bool(self.extended_line_patterns),
                "semantic_cache_enabled": self.ENABLE_SEMANTIC_CACHE,
                "semantic_fallback_enabled": self.ENABLE_SEMANTIC_FALLBACK
            }
            
        except Exception as e:
            return {
                "error": str(e),
                "original_query": query,
                "extraction_failed": True
            }