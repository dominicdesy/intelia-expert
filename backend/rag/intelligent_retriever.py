"""
Intelligent Retrieval System with Query Expansion and Contextual Ranking
Enhanced RAG retrieval with domain-specific optimization for broiler management
"""

import re
import logging
import numpy as np
from typing import List, Dict, Any, Optional, Tuple, Set
from dataclasses import dataclass
from collections import defaultdict
import math

logger = logging.getLogger(__name__)


@dataclass
class QueryContext:
    """Extracted context from user query."""
    original_query: str
    breed: Optional[str] = None
    age_phase: Optional[str] = None
    data_type: Optional[str] = None
    urgency: Optional[str] = None
    environmental_factors: List[str] = None
    metrics: List[str] = None
    language: str = "en"
    
    def __post_init__(self):
        if self.environmental_factors is None:
            self.environmental_factors = []
        if self.metrics is None:
            self.metrics = []


@dataclass
class ExpandedQuery:
    """Query expansion result."""
    original_query: str
    expanded_queries: List[str]
    synonym_expansions: List[str]
    context_expansions: List[str]
    technical_expansions: List[str]


@dataclass
class RankedResult:
    """Enhanced search result with ranking scores."""
    document: Dict[str, Any]
    base_score: float
    contextual_score: float
    diversity_score: float
    final_score: float
    ranking_factors: Dict[str, float]
    metadata: Dict[str, Any]


class BroilerQueryExpander:
    """Domain-specific query expansion for broiler management."""
    
    # Breed synonyms and variants
    BREED_SYNONYMS = {
        'ross': ['ross 308', 'ross308', 'ross-308', 'aviagen ross'],
        'ross308': ['ross 308', 'ross-308', 'aviagen ross 308'],
        'cobb': ['cobb 500', 'cobb500', 'cobb-500'],
        'cobb500': ['cobb 500', 'cobb-500'],
        'aviagen': ['aviagen plus', 'aviagen+', 'aviagen-plus'],
        'hubbard': ['hubbard flex', 'hubbard-flex'],
        'broiler': ['chicken', 'poultry', 'bird', 'broilers'],
        'chicken': ['broiler', 'poultry', 'bird', 'chickens']
    }
    
    # Performance metrics synonyms
    METRIC_SYNONYMS = {
        'weight': ['body weight', 'live weight', 'target weight', 'bodyweight'],
        'fcr': ['feed conversion', 'feed efficiency', 'conversion ratio', 'feed conversion ratio'],
        'gain': ['weight gain', 'daily gain', 'growth rate', 'weight increase'],
        'growth': ['development', 'gain', 'weight increase', 'growing'],
        'feed': ['nutrition', 'diet', 'feeding', 'intake'],
        'intake': ['consumption', 'feed intake', 'daily intake'],
        'mortality': ['death rate', 'deaths', 'losses', 'dead birds'],
        'performance': ['results', 'achievement', 'targets', 'standards']
    }
    
    # Environmental synonyms
    ENVIRONMENTAL_SYNONYMS = {
        'temperature': ['temp', 'heat', 'thermal', 'heating', 'cooling'],
        'humidity': ['moisture', 'relative humidity', 'rh', 'dampness'],
        'ventilation': ['airflow', 'air circulation', 'ventilation rate', 'air quality'],
        'heating': ['warming', 'heat source', 'brooding', 'temperature control'],
        'cooling': ['air conditioning', 'evaporative cooling', 'heat removal']
    }
    
    # Management action synonyms
    ACTION_SYNONYMS = {
        'adjust': ['modify', 'change', 'alter', 'fine-tune', 'regulate'],
        'monitor': ['check', 'observe', 'track', 'watch', 'measure'],
        'control': ['manage', 'regulate', 'maintain', 'govern'],
        'optimize': ['improve', 'enhance', 'maximize', 'perfect'],
        'prevent': ['avoid', 'stop', 'preclude', 'forestall'],
        'treat': ['address', 'handle', 'manage', 'remedy']
    }
    
    # Age phase patterns
    AGE_PHASES = {
        'week_1': ['day 1-7', 'first week', 'starter phase', 'early phase'],
        'week_2': ['day 8-14', 'second week', 'early grower'],
        'week_3': ['day 15-21', 'third week', 'rapid growth'],
        'week_4': ['day 22-28', 'fourth week', 'grower phase'],
        'week_5': ['day 29-35', 'fifth week', 'peak growth'],
        'week_6': ['day 36-42', 'sixth week', 'finisher phase'],
        'starter': ['week 1', 'day 1-7', 'chick phase', 'brooding'],
        'grower': ['week 2-4', 'growing phase', 'development'],
        'finisher': ['week 5+', 'finishing phase', 'market weight']
    }
    
    # Technical context patterns
    TECHNICAL_CONTEXTS = {
        'disease': ['health', 'illness', 'pathology', 'symptoms', 'diagnosis'],
        'nutrition': ['feeding', 'diet', 'supplements', 'vitamins', 'minerals'],
        'environment': ['housing', 'barn', 'facility', 'conditions'],
        'management': ['procedures', 'protocols', 'practices', 'operations'],
        'production': ['efficiency', 'productivity', 'output', 'yields']
    }
    
    def expand_query(self, query: str, context: Optional[QueryContext] = None) -> ExpandedQuery:
        """Expand query with domain-specific synonyms and context."""
        original_query = query.strip()
        query_lower = original_query.lower()
        
        expanded_queries = [original_query]
        synonym_expansions = []
        context_expansions = []
        technical_expansions = []
        
        # Breed expansion
        breed_expansions = self._expand_breeds(query_lower)
        expanded_queries.extend(breed_expansions)
        synonym_expansions.extend(breed_expansions)
        
        # Metric expansion
        metric_expansions = self._expand_metrics(query_lower)
        expanded_queries.extend(metric_expansions)
        synonym_expansions.extend(metric_expansions)
        
        # Environmental expansion
        env_expansions = self._expand_environmental(query_lower)
        expanded_queries.extend(env_expansions)
        synonym_expansions.extend(env_expansions)
        
        # Action expansion
        action_expansions = self._expand_actions(query_lower)
        expanded_queries.extend(action_expansions)
        synonym_expansions.extend(action_expansions)
        
        # Context-based expansion
        if context:
            ctx_expansions = self._expand_with_context(query_lower, context)
            expanded_queries.extend(ctx_expansions)
            context_expansions.extend(ctx_expansions)
        
        # Technical domain expansion
        tech_expansions = self._expand_technical_context(query_lower)
        expanded_queries.extend(tech_expansions)
        technical_expansions.extend(tech_expansions)
        
        # Remove duplicates while preserving order
        unique_expansions = []
        seen = set()
        for query_exp in expanded_queries:
            if query_exp.lower() not in seen:
                unique_expansions.append(query_exp)
                seen.add(query_exp.lower())
        
        logger.debug(f"Expanded query from 1 to {len(unique_expansions)} variants")
        
        return ExpandedQuery(
            original_query=original_query,
            expanded_queries=unique_expansions,
            synonym_expansions=synonym_expansions,
            context_expansions=context_expansions,
            technical_expansions=technical_expansions
        )
    
    def _expand_breeds(self, query: str) -> List[str]:
        """Expand breed-related terms."""
        expansions = []
        for breed, synonyms in self.BREED_SYNONYMS.items():
            if breed in query:
                for synonym in synonyms:
                    expanded = query.replace(breed, synonym)
                    if expanded != query:
                        expansions.append(expanded)
        return expansions
    
    def _expand_metrics(self, query: str) -> List[str]:
        """Expand performance metric terms."""
        expansions = []
        for metric, synonyms in self.METRIC_SYNONYMS.items():
            if metric in query:
                for synonym in synonyms:
                    expanded = query.replace(metric, synonym)
                    if expanded != query:
                        expansions.append(expanded)
        return expansions
    
    def _expand_environmental(self, query: str) -> List[str]:
        """Expand environmental terms."""
        expansions = []
        for env_term, synonyms in self.ENVIRONMENTAL_SYNONYMS.items():
            if env_term in query:
                for synonym in synonyms:
                    expanded = query.replace(env_term, synonym)
                    if expanded != query:
                        expansions.append(expanded)
        return expansions
    
    def _expand_actions(self, query: str) -> List[str]:
        """Expand management action terms."""
        expansions = []
        for action, synonyms in self.ACTION_SYNONYMS.items():
            if action in query:
                for synonym in synonyms:
                    expanded = query.replace(action, synonym)
                    if expanded != query:
                        expansions.append(expanded)
        return expansions
    
    def _expand_with_context(self, query: str, context: QueryContext) -> List[str]:
        """Expand query using extracted context."""
        expansions = []
        
        # Add breed context
        if context.breed:
            breed_query = f"{context.breed} {query}"
            if breed_query not in expansions:
                expansions.append(breed_query)
        
        # Add age phase context
        if context.age_phase:
            phase_synonyms = self.AGE_PHASES.get(context.age_phase, [])
            for synonym in phase_synonyms:
                phase_query = f"{query} {synonym}"
                expansions.append(phase_query)
        
        # Add data type context
        if context.data_type:
            data_query = f"{context.data_type} {query}"
            expansions.append(data_query)
        
        return expansions
    
    def _expand_technical_context(self, query: str) -> List[str]:
        """Expand with technical domain context."""
        expansions = []
        
        for domain, contexts in self.TECHNICAL_CONTEXTS.items():
            domain_score = sum(1 for ctx in contexts if ctx in query)
            if domain_score > 0:
                # Add domain-specific expansions
                for ctx in contexts:
                    if ctx not in query:
                        ctx_query = f"{query} {ctx}"
                        expansions.append(ctx_query)
        
        return expansions


class QueryContextExtractor:
    """Extract semantic context from user queries."""
    
    # Breed detection patterns
    BREED_PATTERNS = {
        'ross_308': [r'ross\s*308', r'ross-308', r'aviagen\s+ross'],
        'cobb_500': [r'cobb\s*500', r'cobb-500'],
        'aviagen_plus': [r'aviagen\s*plus', r'aviagen\+'],
        'hubbard_flex': [r'hubbard\s*flex', r'hubbard-flex']
    }
    
    # Age phase detection patterns
    AGE_PATTERNS = {
        'week_1': [r'week\s*1', r'day\s*[1-7]', r'starter', r'chick'],
        'week_2': [r'week\s*2', r'day\s*[8-9]|1[0-4]'],
        'week_3': [r'week\s*3', r'day\s*1[5-9]|2[0-1]'],
        'week_4': [r'week\s*4', r'day\s*2[2-8]'],
        'week_5': [r'week\s*5', r'day\s*2[9-9]|3[0-5]'],
        'week_6': [r'week\s*6', r'day\s*3[6-9]|4[0-2]', r'finisher']
    }
    
    # Data type detection patterns
    DATA_TYPE_PATTERNS = {
        'performance': [r'weight', r'fcr', r'gain', r'performance', r'target'],
        'temperature': [r'temperature', r'heat', r'cooling', r'thermal'],
        'nutrition': [r'feed', r'nutrition', r'diet', r'protein', r'energy'],
        'management': [r'management', r'protocol', r'procedure', r'guideline'],
        'health': [r'disease', r'health', r'illness', r'mortality', r'symptom']
    }
    
    # Urgency detection patterns
    URGENCY_PATTERNS = {
        'high': [r'urgent', r'emergency', r'critical', r'immediate', r'crisis'],
        'medium': [r'important', r'priority', r'soon', r'attention'],
        'low': [r'routine', r'general', r'information', r'background']
    }
    
    def extract_context(self, query: str) -> QueryContext:
        """Extract semantic context from query."""
        query_lower = query.lower()
        
        return QueryContext(
            original_query=query,
            breed=self._extract_breed(query_lower),
            age_phase=self._extract_age_phase(query_lower),
            data_type=self._extract_data_type(query_lower),
            urgency=self._extract_urgency(query_lower),
            environmental_factors=self._extract_environmental_factors(query_lower),
            metrics=self._extract_metrics(query_lower),
            language=self._detect_language(query)
        )
    
    def _extract_breed(self, query: str) -> Optional[str]:
        """Extract breed information from query."""
        for breed, patterns in self.BREED_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, query, re.IGNORECASE):
                    return breed
        
        # Generic detection
        if any(term in query for term in ['broiler', 'chicken', 'poultry']):
            return 'generic_broiler'
        
        return None
    
    def _extract_age_phase(self, query: str) -> Optional[str]:
        """Extract age phase from query."""
        for phase, patterns in self.AGE_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, query, re.IGNORECASE):
                    return phase
        return None
    
    def _extract_data_type(self, query: str) -> Optional[str]:
        """Extract data type focus from query."""
        type_scores = {}
        for data_type, patterns in self.DATA_TYPE_PATTERNS.items():
            score = sum(1 for pattern in patterns if re.search(pattern, query, re.IGNORECASE))
            if score > 0:
                type_scores[data_type] = score
        
        if type_scores:
            return max(type_scores.items(), key=lambda x: x[1])[0]
        return None
    
    def _extract_urgency(self, query: str) -> Optional[str]:
        """Extract urgency level from query."""
        for urgency, patterns in self.URGENCY_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, query, re.IGNORECASE):
                    return urgency
        return 'medium'  # Default urgency
    
    def _extract_environmental_factors(self, query: str) -> List[str]:
        """Extract environmental factors mentioned in query."""
        factors = []
        env_terms = ['temperature', 'humidity', 'ventilation', 'heating', 'cooling', 'lighting']
        
        for term in env_terms:
            if term in query:
                factors.append(term)
        
        return factors
    
    def _extract_metrics(self, query: str) -> List[str]:
        """Extract performance metrics mentioned in query."""
        metrics = []
        metric_terms = ['weight', 'fcr', 'gain', 'mortality', 'feed', 'conversion']
        
        for term in metric_terms:
            if term in query:
                metrics.append(term)
        
        return metrics
    
    def _detect_language(self, query: str) -> str:
        """Detect query language (basic detection)."""
        # Simple language detection based on common words
        french_indicators = ['le', 'la', 'et', 'de', 'du', 'des', 'température', 'poids']
        spanish_indicators = ['el', 'la', 'y', 'de', 'del', 'temperatura', 'peso']
        
        query_lower = query.lower()
        
        french_score = sum(1 for word in french_indicators if word in query_lower)
        spanish_score = sum(1 for word in spanish_indicators if word in query_lower)
        
        if french_score > 0:
            return 'fr'
        elif spanish_score > 0:
            return 'es'
        else:
            return 'en'


class ContextualReranker:
    """Rerank search results based on domain context and relevance."""
    
    def __init__(self):
        """Initialize contextual reranker."""
        self.breed_boost = {
            'ross_308': 1.4,
            'cobb_500': 1.3,
            'aviagen_plus': 1.2,
            'generic_broiler': 1.0
        }
        
        self.data_type_boost = {
            'performance': 1.3,
            'temperature': 1.2,
            'nutrition': 1.2,
            'management': 1.1,
            'health': 1.1
        }
        
        self.urgency_boost = {
            'high': 1.5,
            'medium': 1.0,
            'low': 0.8
        }
    
    def rerank_results(self, results: List[Tuple], query_context: QueryContext) -> List[RankedResult]:
        """Rerank search results with contextual scoring."""
        if not results:
            return []
        
        ranked_results = []
        
        for i, (document, base_score) in enumerate(results):
            # Extract document metadata
            metadata = document.get('metadata', {}) if isinstance(document, dict) else {}
            
            # Calculate contextual scores
            breed_score = self._calculate_breed_score(metadata, query_context)
            data_type_score = self._calculate_data_type_score(metadata, query_context)
            phase_score = self._calculate_phase_score(metadata, query_context)
            urgency_score = self._calculate_urgency_score(metadata, query_context)
            recency_score = self._calculate_recency_score(metadata)
            
            # Calculate diversity penalty
            diversity_score = self._calculate_diversity_score(document, ranked_results)
            
            # Combine scores
            contextual_score = (
                breed_score * 0.3 +
                data_type_score * 0.25 +
                phase_score * 0.2 +
                urgency_score * 0.15 +
                recency_score * 0.1
            )
            
            final_score = base_score * contextual_score * diversity_score
            
            ranking_factors = {
                'base_score': base_score,
                'breed_score': breed_score,
                'data_type_score': data_type_score,
                'phase_score': phase_score,
                'urgency_score': urgency_score,
                'recency_score': recency_score,
                'diversity_score': diversity_score
            }
            
            ranked_result = RankedResult(
                document=document,
                base_score=base_score,
                contextual_score=contextual_score,
                diversity_score=diversity_score,
                final_score=final_score,
                ranking_factors=ranking_factors,
                metadata=metadata
            )
            
            ranked_results.append(ranked_result)
        
        # Sort by final score
        ranked_results.sort(key=lambda x: x.final_score, reverse=True)
        
        logger.debug(f"Reranked {len(ranked_results)} results with contextual scoring")
        return ranked_results
    
    def _calculate_breed_score(self, metadata: Dict[str, Any], context: QueryContext) -> float:
        """Calculate breed matching score."""
        doc_breed = metadata.get('breed', '').lower()
        query_breed = context.breed
        
        if not query_breed or not doc_breed:
            return 1.0
        
        # Exact match
        if doc_breed == query_breed:
            return self.breed_boost.get(query_breed, 1.4)
        
        # Family match (e.g., ross variants)
        if any(breed_part in doc_breed for breed_part in query_breed.split('_')):
            return 1.2
        
        return 0.8
    
    def _calculate_data_type_score(self, metadata: Dict[str, Any], context: QueryContext) -> float:
        """Calculate data type relevance score."""
        doc_type = metadata.get('document_type', '').lower()
        query_type = context.data_type
        
        if not query_type:
            return 1.0
        
        # Direct match
        if query_type in doc_type:
            return self.data_type_boost.get(query_type, 1.2)
        
        # Related types
        related_types = {
            'performance': ['growth', 'weight', 'standards'],
            'temperature': ['environmental', 'climate', 'management'],
            'nutrition': ['feed', 'diet', 'formulation'],
            'management': ['protocol', 'procedure', 'guideline'],
            'health': ['disease', 'mortality', 'wellness']
        }
        
        if query_type in related_types:
            for related in related_types[query_type]:
                if related in doc_type:
                    return 1.1
        
        return 0.9
    
    def _calculate_phase_score(self, metadata: Dict[str, Any], context: QueryContext) -> float:
        """Calculate growth phase relevance score."""
        doc_phases = metadata.get('applicable_phases', [])
        query_phase = context.age_phase
        
        if not query_phase or not doc_phases:
            return 1.0
        
        # Convert phase to week number for comparison
        phase_weeks = {
            'week_1': 1, 'week_2': 2, 'week_3': 3,
            'week_4': 4, 'week_5': 5, 'week_6': 6
        }
        
        query_week = phase_weeks.get(query_phase)
        if not query_week:
            return 1.0
        
        # Check if any document phase matches
        for phase_name in doc_phases:
            if isinstance(phase_name, str) and f'week {query_week}' in phase_name.lower():
                return 1.3
        
        return 1.0
    
    def _calculate_urgency_score(self, metadata: Dict[str, Any], context: QueryContext) -> float:
        """Calculate urgency-based score."""
        query_urgency = context.urgency
        
        if not query_urgency:
            return 1.0
        
        # Boost recent documents for urgent queries
        if query_urgency == 'high':
            doc_age = self._get_document_age(metadata)
            if doc_age is not None and doc_age < 30:  # Less than 30 days
                return 1.3
        
        return self.urgency_boost.get(query_urgency, 1.0)
    
    def _calculate_recency_score(self, metadata: Dict[str, Any]) -> float:
        """Calculate document recency score."""
        doc_age = self._get_document_age(metadata)
        
        if doc_age is None:
            return 1.0
        
        # Exponential decay for document age
        if doc_age <= 7:
            return 1.2
        elif doc_age <= 30:
            return 1.1
        elif doc_age <= 90:
            return 1.0
        else:
            return 0.9
    
    def _calculate_diversity_score(self, document: Dict[str, Any], existing_results: List[RankedResult]) -> float:
        """Calculate diversity penalty to avoid duplicate content."""
        if not existing_results:
            return 1.0
        
        doc_content = document.get('content', '') if isinstance(document, dict) else str(document)
        doc_source = document.get('metadata', {}).get('source_file', '') if isinstance(document, dict) else ''
        
        diversity_penalty = 1.0
        
        for existing in existing_results:
            existing_content = existing.document.get('content', '') if isinstance(existing.document, dict) else str(existing.document)
            existing_source = existing.metadata.get('source_file', '')
            
            # Same source file penalty
            if doc_source and existing_source and doc_source == existing_source:
                diversity_penalty *= 0.8
            
            # Content similarity penalty (simple overlap check)
            if doc_content and existing_content:
                overlap = self._calculate_content_overlap(doc_content, existing_content)
                if overlap > 0.7:
                    diversity_penalty *= 0.6
        
        return max(diversity_penalty, 0.3)  # Minimum diversity score
    
    def _calculate_content_overlap(self, content1: str, content2: str) -> float:
        """Calculate content overlap between two documents."""
        if not content1 or not content2:
            return 0.0
        
        # Simple word-based overlap calculation
        words1 = set(content1.lower().split())
        words2 = set(content2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return intersection / union if union > 0 else 0.0
    
    def _get_document_age(self, metadata: Dict[str, Any]) -> Optional[int]:
        """Get document age in days."""
        try:
            from datetime import datetime
            
            # Try different date fields
            date_fields = ['created_date', 'modified_date', 'file_date', 'last_modified']
            
            for field in date_fields:
                date_value = metadata.get(field)
                if date_value:
                    if isinstance(date_value, str):
                        # Parse date string
                        try:
                            doc_date = datetime.fromisoformat(date_value.replace('Z', '+00:00'))
                        except:
                            continue
                    elif hasattr(date_value, 'timestamp'):
                        doc_date = date_value
                    else:
                        continue
                    
                    age_days = (datetime.now() - doc_date).days
                    return max(age_days, 0)
            
            return None
            
        except Exception as e:
            logger.debug(f"Error calculating document age: {e}")
            return None


class IntelligentRetriever:
    """Enhanced retrieval system with query expansion and contextual ranking."""
    
    def __init__(self, vector_store, config: Optional[Dict[str, Any]] = None):
        """Initialize intelligent retriever."""
        self.vector_store = vector_store
        self.config = config or {}
        
        self.query_expander = BroilerQueryExpander()
        self.context_extractor = QueryContextExtractor()
        self.reranker = ContextualReranker()
        
        # Retrieval configuration
        self.max_expanded_queries = self.config.get('max_expanded_queries', 5)
        self.base_k_multiplier = self.config.get('base_k_multiplier', 3)
        self.similarity_threshold = self.config.get('similarity_threshold', 0.3)
        
        logger.info("Intelligent retriever initialized with query expansion and contextual ranking")
    
    def retrieve(self, query: str, k: int = 5, filters: Optional[Dict[str, Any]] = None) -> List[RankedResult]:
        """Enhanced retrieval with query expansion and contextual ranking."""
        try:
            # Extract query context
            query_context = self.context_extractor.extract_context(query)
            logger.debug(f"Extracted context: breed={query_context.breed}, phase={query_context.age_phase}")
            
            # Expand query
            expanded_query = self.query_expander.expand_query(query, query_context)
            logger.debug(f"Generated {len(expanded_query.expanded_queries)} query variants")
            
            # Multi-query retrieval
            all_results = self._multi_query_search(
                expanded_query.expanded_queries[:self.max_expanded_queries],
                k * self.base_k_multiplier,
                filters,
                query_context
            )
            
            # Rerank results
            ranked_results = self.reranker.rerank_results(all_results, query_context)
            
            # Return top k results
            final_results = ranked_results[:k]
            
            logger.info(f"Retrieved {len(final_results)} optimized results for query: {query[:50]}...")
            return final_results
            
        except Exception as e:
            logger.error(f"Enhanced retrieval failed: {e}")
            return []
    
    def _multi_query_search(self, queries: List[str], k: int, 
                           filters: Optional[Dict[str, Any]], 
                           context: QueryContext) -> List[Tuple]:
        """Perform search across multiple expanded queries."""
        all_results = []
        seen_docs = set()
        
        for i, query_variant in enumerate(queries):
            try:
                # Adjust k for each query to get diverse results
                query_k = max(k // len(queries), 2)
                if i == 0:  # Original query gets more weight
                    query_k = k // 2
                
                # Create query embedding
                query_embedding = self._create_query_embedding(query_variant)
                if query_embedding is None:
                    continue
                
                # Search with filters
                results = self.vector_store.search_with_filters(
                    query_embedding,
                    k=query_k,
                    filters=filters,
                    similarity_threshold=self.similarity_threshold
                )
                
                # Add unique results
                for result in results:
                    doc_id = self._get_document_id(result.document)
                    if doc_id not in seen_docs:
                        # Add query variant info to result
                        result_tuple = (result.document, result.score)
                        all_results.append(result_tuple)
                        seen_docs.add(doc_id)
                
                logger.debug(f"Query variant {i+1} found {len(results)} results")
                
            except Exception as e:
                logger.warning(f"Search failed for query variant '{query_variant}': {e}")
                continue
        
        logger.debug(f"Multi-query search found {len(all_results)} unique results")
        return all_results
    
    def _create_query_embedding(self, query: str) -> Optional[np.ndarray]:
        """Create embedding for query text."""
        try:
            # This should integrate with your embedding model
            # For now, return a placeholder
            logger.debug(f"Creating embedding for query: {query[:50]}...")
            
            # Check if vector store has embedding capability
            if hasattr(self.vector_store, 'create_query_embedding'):
                return self.vector_store.create_query_embedding(query)
            
            # Fallback: return None and let vector store handle it
            return None
            
        except Exception as e:
            logger.error(f"Failed to create query embedding: {e}")
            return None
    
    def _get_document_id(self, document: Dict[str, Any]) -> str:
        """Get unique identifier for document."""
        if isinstance(document, dict):
            # Try different ID fields
            for id_field in ['id', 'doc_id', 'chunk_id', 'source_file']:
                doc_id = document.get('metadata', {}).get(id_field)
                if doc_id:
                    return str(doc_id)
            
            # Use content hash as fallback
            content = document.get('content', '') or document.get('page_content', '')
            if content:
                return str(hash(content[:100]))
        
        return str(hash(str(document)))
    
    def get_query_suggestions(self, partial_query: str, limit: int = 5) -> List[str]:
        """Generate query suggestions based on partial input."""
        suggestions = []
        partial_lower = partial_query.lower()
        
        # Breed-based suggestions
        if any(breed in partial_lower for breed in ['ross', 'cobb', 'aviagen', 'hubbard']):
            suggestions.extend([
                f"{partial_query} performance targets",
                f"{partial_query} weight standards",
                f"{partial_query} temperature management",
                f"{partial_query} feed requirements"
            ])
        
        # Performance-based suggestions
        if any(metric in partial_lower for metric in ['weight', 'fcr', 'gain', 'growth']):
            suggestions.extend([
                f"{partial_query} week 3",
                f"{partial_query} targets",
                f"{partial_query} optimization",
                f"{partial_query} standards"
            ])
        
        # Problem-based suggestions
        if any(issue in partial_lower for issue in ['problem', 'issue', 'low', 'high', 'poor']):
            suggestions.extend([
                f"{partial_query} solutions",
                f"{partial_query} management",
                f"{partial_query} troubleshooting",
                f"{partial_query} recommendations"
            ])
        
        # Environmental suggestions
        if any(env in partial_lower for env in ['temperature', 'humidity', 'ventilation']):
            suggestions.extend([
                f"{partial_query} control",
                f"{partial_query} optimization",
                f"{partial_query} management",
                f"{partial_query} guidelines"
            ])
        
        # Remove duplicates and limit
        unique_suggestions = []
        seen = set()
        for suggestion in suggestions:
            if suggestion.lower() not in seen and suggestion != partial_query:
                unique_suggestions.append(suggestion)
                seen.add(suggestion.lower())
                if len(unique_suggestions) >= limit:
                    break
        
        return unique_suggestions
    
    def explain_results(self, query: str, results: List[RankedResult]) -> Dict[str, Any]:
        """Provide explanation of why specific results were returned."""
        if not results:
            return {'explanation': 'No results found', 'factors': {}}
        
        context = self.context_extractor.extract_context(query)
        expanded = self.query_expander.expand_query(query, context)
        
        explanation = {
            'query_analysis': {
                'original_query': query,
                'detected_breed': context.breed,
                'detected_phase': context.age_phase,
                'detected_data_type': context.data_type,
                'urgency_level': context.urgency,
                'expansions_used': len(expanded.expanded_queries)
            },
            'ranking_explanation': [],
            'top_factors': {},
            'diversity_applied': False
        }
        
        # Analyze top 3 results
        for i, result in enumerate(results[:3]):
            result_explanation = {
                'rank': i + 1,
                'base_score': result.base_score,
                'final_score': result.final_score,
                'boost_factors': [],
                'penalty_factors': []
            }
            
            factors = result.ranking_factors
            
            # Identify significant boosts
            if factors.get('breed_score', 1.0) > 1.2:
                result_explanation['boost_factors'].append(f"Breed match boost: {factors['breed_score']:.2f}")
            
            if factors.get('data_type_score', 1.0) > 1.1:
                result_explanation['boost_factors'].append(f"Data type relevance: {factors['data_type_score']:.2f}")
            
            if factors.get('phase_score', 1.0) > 1.1:
                result_explanation['boost_factors'].append(f"Growth phase match: {factors['phase_score']:.2f}")
            
            if factors.get('recency_score', 1.0) > 1.05:
                result_explanation['boost_factors'].append(f"Recent document: {factors['recency_score']:.2f}")
            
            # Identify penalties
            if factors.get('diversity_score', 1.0) < 0.9:
                result_explanation['penalty_factors'].append(f"Diversity penalty: {factors['diversity_score']:.2f}")
                explanation['diversity_applied'] = True
            
            explanation['ranking_explanation'].append(result_explanation)
        
        # Aggregate top factors
        all_factors = defaultdict(list)
        for result in results[:5]:
            for factor, score in result.ranking_factors.items():
                if factor != 'base_score':
                    all_factors[factor].append(score)
        
        for factor, scores in all_factors.items():
            avg_score = sum(scores) / len(scores)
            explanation['top_factors'][factor] = round(avg_score, 3)
        
        return explanation
    
    def get_retrieval_stats(self) -> Dict[str, Any]:
        """Get retrieval performance statistics."""
        stats = {
            'config': {
                'max_expanded_queries': self.max_expanded_queries,
                'base_k_multiplier': self.base_k_multiplier,
                'similarity_threshold': self.similarity_threshold
            }
        }
        
        # Add vector store stats if available
        if hasattr(self.vector_store, 'get_performance_stats'):
            stats['vector_store'] = self.vector_store.get_performance_stats()
        
        return stats
    
    def optimize_retrieval_params(self, feedback_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Optimize retrieval parameters based on user feedback."""
        if not feedback_data:
            return {'status': 'no_feedback_data'}
        
        # Analyze feedback patterns
        positive_feedback = [item for item in feedback_data if item.get('rating', 0) >= 4]
        negative_feedback = [item for item in feedback_data if item.get('rating', 0) <= 2]
        
        optimization_results = {
            'analyzed_feedback': len(feedback_data),
            'positive_samples': len(positive_feedback),
            'negative_samples': len(negative_feedback),
            'optimizations': []
        }
        
        # Adjust similarity threshold
        if len(negative_feedback) > len(positive_feedback):
            if self.similarity_threshold < 0.6:
                self.similarity_threshold += 0.1
                optimization_results['optimizations'].append("Increased similarity threshold")
        elif len(positive_feedback) > len(negative_feedback) * 2:
            if self.similarity_threshold > 0.2:
                self.similarity_threshold -= 0.05
                optimization_results['optimizations'].append("Decreased similarity threshold for broader results")
        
        # Adjust expansion count
        avg_results_per_query = sum(item.get('results_count', 0) for item in feedback_data) / len(feedback_data)
        
        if avg_results_per_query < 3 and self.max_expanded_queries < 8:
            self.max_expanded_queries += 1
            optimization_results['optimizations'].append("Increased query expansions")
        elif avg_results_per_query > 10 and self.max_expanded_queries > 3:
            self.max_expanded_queries -= 1
            optimization_results['optimizations'].append("Reduced query expansions")
        
        logger.info(f"Optimized retrieval parameters based on {len(feedback_data)} feedback samples")
        return optimization_results


class HybridSearchEngine:
    """Hybrid search combining vector and keyword search with intelligent fusion."""
    
    def __init__(self, vector_store, config: Optional[Dict[str, Any]] = None):
        """Initialize hybrid search engine."""
        self.vector_store = vector_store
        self.config = config or {}
        self.intelligent_retriever = IntelligentRetriever(vector_store, config)
        
        # Try to initialize BM25 for keyword search
        self.bm25_available = self._initialize_bm25()
        
        # Fusion weights
        self.vector_weight = self.config.get('vector_weight', 0.7)
        self.keyword_weight = self.config.get('keyword_weight', 0.3)
        
        logger.info(f"Hybrid search initialized (BM25 available: {self.bm25_available})")
    
    def _initialize_bm25(self) -> bool:
        """Initialize BM25 keyword search if available."""
        try:
            from rank_bm25 import BM25Okapi
            self.bm25_class = BM25Okapi
            self.bm25_index = None
            self.bm25_corpus = []
            return True
        except ImportError:
            logger.warning("rank_bm25 not available - keyword search disabled")
            return False
    
    def build_keyword_index(self, documents: List[Dict[str, Any]]) -> bool:
        """Build BM25 keyword index from documents."""
        if not self.bm25_available:
            return False
        
        try:
            # Extract text content and tokenize
            corpus = []
            self.bm25_corpus = []
            
            for doc in documents:
                content = doc.get('content', '') or doc.get('page_content', '')
                if content:
                    tokens = self._tokenize_text(content)
                    corpus.append(tokens)
                    self.bm25_corpus.append(doc)
            
            # Build BM25 index
            if corpus:
                self.bm25_index = self.bm25_class(corpus)
                logger.info(f"Built BM25 index with {len(corpus)} documents")
                return True
            
        except Exception as e:
            logger.error(f"Failed to build BM25 index: {e}")
        
        return False
    
    def _tokenize_text(self, text: str) -> List[str]:
        """Tokenize text for BM25 indexing."""
        # Simple tokenization - can be enhanced
        import re
        text = text.lower()
        tokens = re.findall(r'\b\w+\b', text)
        return tokens
    
    def hybrid_search(self, query: str, k: int = 5, 
                     filters: Optional[Dict[str, Any]] = None) -> List[RankedResult]:
        """Perform hybrid search combining vector and keyword approaches."""
        try:
            # Vector search with intelligent retrieval
            vector_results = self.intelligent_retriever.retrieve(query, k * 2, filters)
            
            # Keyword search if available
            keyword_results = []
            if self.bm25_available and self.bm25_index:
                keyword_results = self._bm25_search(query, k * 2)
            
            # Fuse results
            if keyword_results:
                fused_results = self._fuse_results(vector_results, keyword_results, k)
            else:
                fused_results = vector_results[:k]
            
            logger.info(f"Hybrid search returned {len(fused_results)} results")
            return fused_results
            
        except Exception as e:
            logger.error(f"Hybrid search failed: {e}")
            return []
    
    def _bm25_search(self, query: str, k: int) -> List[RankedResult]:
        """Perform BM25 keyword search."""
        if not self.bm25_index or not self.bm25_corpus:
            return []
        
        try:
            query_tokens = self._tokenize_text(query)
            scores = self.bm25_index.get_scores(query_tokens)
            
            # Get top k results
            top_indices = np.argsort(scores)[::-1][:k]
            
            results = []
            for idx in top_indices:
                if scores[idx] > 0:  # Only include positive scores
                    doc = self.bm25_corpus[idx]
                    
                    # Create RankedResult compatible object
                    result = RankedResult(
                        document=doc,
                        base_score=float(scores[idx]),
                        contextual_score=1.0,
                        diversity_score=1.0,
                        final_score=float(scores[idx]),
                        ranking_factors={'bm25_score': float(scores[idx])},
                        metadata=doc.get('metadata', {})
                    )
                    results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"BM25 search failed: {e}")
            return []
    
    def _fuse_results(self, vector_results: List[RankedResult], 
                     keyword_results: List[RankedResult], k: int) -> List[RankedResult]:
        """Fuse vector and keyword search results."""
        # Create document ID mapping
        vector_docs = {self._get_doc_id(r.document): r for r in vector_results}
        keyword_docs = {self._get_doc_id(r.document): r for r in keyword_results}
        
        # Normalize scores
        vector_scores = self._normalize_scores([r.final_score for r in vector_results])
        keyword_scores = self._normalize_scores([r.final_score for r in keyword_results])
        
        # Fuse scores
        fused_results = {}
        
        # Add vector results with normalized scores
        for i, result in enumerate(vector_results):
            doc_id = self._get_doc_id(result.document)
            normalized_vector_score = vector_scores[i] if i < len(vector_scores) else 0
            
            fused_score = normalized_vector_score * self.vector_weight
            
            # Add keyword score if available
            if doc_id in keyword_docs:
                keyword_idx = list(keyword_docs.keys()).index(doc_id)
                normalized_keyword_score = keyword_scores[keyword_idx] if keyword_idx < len(keyword_scores) else 0
                fused_score += normalized_keyword_score * self.keyword_weight
            
            # Update result with fused score
            result.final_score = fused_score
            result.ranking_factors['fused_score'] = fused_score
            result.ranking_factors['vector_component'] = normalized_vector_score * self.vector_weight
            
            fused_results[doc_id] = result
        
        # Add keyword-only results
        for i, result in enumerate(keyword_results):
            doc_id = self._get_doc_id(result.document)
            if doc_id not in fused_results:
                normalized_keyword_score = keyword_scores[i] if i < len(keyword_scores) else 0
                fused_score = normalized_keyword_score * self.keyword_weight
                
                result.final_score = fused_score
                result.ranking_factors['fused_score'] = fused_score
                result.ranking_factors['keyword_component'] = fused_score
                
                fused_results[doc_id] = result
        
        # Sort and return top k
        sorted_results = sorted(fused_results.values(), key=lambda x: x.final_score, reverse=True)
        return sorted_results[:k]
    
    def _normalize_scores(self, scores: List[float]) -> List[float]:
        """Normalize scores to 0-1 range."""
        if not scores:
            return []
        
        min_score = min(scores)
        max_score = max(scores)
        
        if max_score == min_score:
            return [1.0] * len(scores)
        
        return [(score - min_score) / (max_score - min_score) for score in scores]
    
    def _get_doc_id(self, document: Dict[str, Any]) -> str:
        """Get document ID for fusion."""
        if isinstance(document, dict):
            # Try different ID fields
            for id_field in ['id', 'doc_id', 'chunk_id']:
                doc_id = document.get(id_field) or document.get('metadata', {}).get(id_field)
                if doc_id:
                    return str(doc_id)
            
            # Use content hash as fallback
            content = document.get('content', '') or document.get('page_content', '')
            if content:
                return str(hash(content[:100]))
        
        return str(hash(str(document)))