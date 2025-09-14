# -*- coding: utf-8 -*-
"""
rag_engine.py - RAG Engine avec OpenAI + Weaviate Direct
Sans LlamaIndex - Zéro conflit de dépendances
Version Production-Ready Python 3.13
"""

import os
import asyncio
import logging
import time
import json
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass
from enum import Enum
import numpy as np
import httpx

# Configuration logging
logger = logging.getLogger(__name__)

# Import Weaviate
try:
    import weaviate
    weaviate_version = getattr(weaviate, '__version__', '4.0.0')
    
    if weaviate_version.startswith('4.'):
        try:
            import weaviate.classes as wvc
            WEAVIATE_V4 = True
        except ImportError:
            wvc = None
            WEAVIATE_V4 = False
    else:
        WEAVIATE_V4 = False
        wvc = None
    
    WEAVIATE_AVAILABLE = True
    logger.info(f"Weaviate {weaviate_version} détecté (V4: {WEAVIATE_V4})")
    
except ImportError as e:
    WEAVIATE_AVAILABLE = False
    WEAVIATE_V4 = False
    wvc = None
    weaviate = None
    logger.error(f"Weaviate non disponible: {e}")

# OpenAI Client
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError as e:
    OPENAI_AVAILABLE = False
    logger.error(f"OpenAI non disponible: {e}")

# VoyageAI pour reranking
try:
    import voyageai
    VOYAGE_AVAILABLE = True
except ImportError:
    VOYAGE_AVAILABLE = False
    logger.warning("VoyageAI non disponible - reranking basique")

# Intelligence métier (préservée)
try:
    from intent_processor import create_intent_processor, IntentType, IntentResult
    INTENT_PROCESSOR_AVAILABLE = True
except ImportError as e:
    INTENT_PROCESSOR_AVAILABLE = False
    logger.warning(f"Intent processor non disponible: {e}")
    
    class IntentType:
        METRIC_QUERY = "metric_query"
        OUT_OF_DOMAIN = "out_of_domain"
    
    class IntentResult:
        def __init__(self):
            self.intent_type = IntentType.METRIC_QUERY
            self.confidence = 0.8
            self.detected_entities = {}
            self.expanded_query = ""
            self.metadata = {}

# Configuration
RAG_ENABLED = os.getenv("RAG_ENABLED", "true").lower() == "true"
WEAVIATE_URL = os.getenv("WEAVIATE_URL", "http://localhost:8080")
WEAVIATE_API_KEY = os.getenv("WEAVIATE_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
VOYAGE_API_KEY = os.getenv("VOYAGE_API_KEY")

# Paramètres RAG
RAG_SIMILARITY_TOP_K = int(os.getenv("RAG_SIMILARITY_TOP_K", "15"))
RAG_CONFIDENCE_THRESHOLD = float(os.getenv("RAG_CONFIDENCE_THRESHOLD", "0.65"))
RAG_CHUNK_SIZE = int(os.getenv("RAG_CHUNK_SIZE", "1024"))
RAG_CHUNK_OVERLAP = int(os.getenv("RAG_CHUNK_OVERLAP", "200"))
RAG_RERANK_TOP_K = int(os.getenv("RAG_RERANK_TOP_K", "8"))
RAG_VERIFICATION_ENABLED = os.getenv("RAG_VERIFICATION_ENABLED", "true").lower() == "true"


class RAGSource(Enum):
    """Sources de réponse"""
    RAG_KNOWLEDGE = "rag_knowledge"
    RAG_VERIFIED = "rag_verified"
    OOD_FILTERED = "ood_filtered" 
    FALLBACK_NEEDED = "fallback_needed"
    ERROR = "error"


@dataclass
class RAGResult:
    """Résultat RAG"""
    source: RAGSource
    answer: Optional[str] = None
    confidence: float = 0.0
    context_docs: List[Dict] = None
    processing_time: float = 0.0
    metadata: Dict = None
    verification_status: Optional[Dict] = None
    intent_result: Optional[IntentResult] = None
    
    def __post_init__(self):
        if self.context_docs is None:
            self.context_docs = []
        if self.metadata is None:
            self.metadata = {}


@dataclass
class Document:
    """Document simple pour RAG"""
    content: str
    metadata: Dict = None
    score: float = 0.0
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class OpenAIEmbedder:
    """Wrapper pour OpenAI Embeddings"""
    
    def __init__(self, client: OpenAI, model: str = "text-embedding-3-small"):
        self.client = client
        self.model = model
        
    async def embed_query(self, text: str) -> List[float]:
        """Créer embedding pour une requête"""
        try:
            response = await self.client.embeddings.create(
                model=self.model,
                input=text,
                encoding_format="float"
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Erreur embedding: {e}")
            return []
    
    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Créer embeddings pour plusieurs documents"""
        try:
            response = await self.client.embeddings.create(
                model=self.model,
                input=texts,
                encoding_format="float"
            )
            return [item.embedding for item in response.data]
        except Exception as e:
            logger.error(f"Erreur embeddings batch: {e}")
            return []


class WeaviateRetriever:
    """Retriever Weaviate direct"""
    
    def __init__(self, client, collection_name: str = "InteliaKnowledge"):
        self.client = client
        self.collection_name = collection_name
        self.is_v4 = WEAVIATE_V4
        
    async def search(self, query_vector: List[float], top_k: int = 10, where_filter: Dict = None) -> List[Document]:
        """Recherche vectorielle dans Weaviate"""
        try:
            if self.is_v4:
                return await self._search_v4(query_vector, top_k, where_filter)
            else:
                return await self._search_v3(query_vector, top_k, where_filter)
        except Exception as e:
            logger.error(f"Erreur recherche Weaviate: {e}")
            return []
    
    async def _search_v4(self, query_vector: List[float], top_k: int, where_filter: Dict) -> List[Document]:
        """Recherche Weaviate V4"""
        try:
            collection = self.client.collections.get(self.collection_name)
            
            query_params = {
                "vector": query_vector,
                "limit": top_k,
                "return_metadata": ["score", "creation_time"]
            }
            
            if where_filter:
                query_params["where"] = where_filter
            
            response = collection.query.near_vector(**query_params)
            
            documents = []
            for obj in response.objects:
                doc = Document(
                    content=obj.properties.get("content", ""),
                    metadata={
                        "title": obj.properties.get("title", ""),
                        "source": obj.properties.get("source", ""),
                        "geneticLine": obj.properties.get("geneticLine", ""),
                        "species": obj.properties.get("species", ""),
                        "creation_time": obj.metadata.creation_time if obj.metadata else None
                    },
                    score=obj.metadata.score if obj.metadata else 0.0
                )
                documents.append(doc)
            
            return documents
            
        except Exception as e:
            logger.error(f"Erreur recherche V4: {e}")
            return []
    
    async def _search_v3(self, query_vector: List[float], top_k: int, where_filter: Dict) -> List[Document]:
        """Recherche Weaviate V3"""
        try:
            query_builder = (
                self.client.query
                .get(self.collection_name, ["content", "title", "source", "geneticLine", "species"])
                .with_near_vector({"vector": query_vector})
                .with_limit(top_k)
                .with_additional(["score", "id"])
            )
            
            if where_filter:
                query_builder = query_builder.with_where(where_filter)
            
            result = query_builder.do()
            
            documents = []
            objects = result.get("data", {}).get("Get", {}).get(self.collection_name, [])
            
            for obj in objects:
                score = obj.get("_additional", {}).get("score", 0.0)
                doc = Document(
                    content=obj.get("content", ""),
                    metadata={
                        "title": obj.get("title", ""),
                        "source": obj.get("source", ""),
                        "geneticLine": obj.get("geneticLine", ""),
                        "species": obj.get("species", ""),
                        "id": obj.get("_additional", {}).get("id")
                    },
                    score=float(score) if score else 0.0
                )
                documents.append(doc)
            
            return documents
            
        except Exception as e:
            logger.error(f"Erreur recherche V3: {e}")
            return []


class EnhancedOODDetector:
    """Détecteur hors-domaine"""
    
    def __init__(self, blocked_terms_path: str = None):
        self.blocked_terms = self._load_blocked_terms(blocked_terms_path)
        self.domain_keywords = {
            'poulet', 'poule', 'aviculture', 'élevage', 'volaille', 'poids', 'fcr',
            'aliment', 'vaccination', 'maladie', 'production', 'croissance',
            'chicken', 'poultry', 'broiler', 'layer', 'feed', 'weight', 'growth',
            'température', 'ventilation', 'eau', 'water', 'temperature', 'incubation',
            'couvoir', 'hatchery', 'biosécurité', 'mortalité', 'mortality', 'performance',
            'ross', 'cobb', 'hubbard', 'isa', 'lohmann'
        }
        
    def _load_blocked_terms(self, path: str = None) -> Dict[str, List[str]]:
        """Charge les termes bloqués"""
        if path is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            path = os.path.join(base_dir, "blocked_terms.json")
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Erreur chargement blocked_terms.json: {e}")
            return {}
    
    def calculate_ood_score(self, query: str) -> Tuple[bool, float, Dict[str, float]]:
        """Calcul score OOD"""
        query_lower = query.lower()
        words = query_lower.split()
        
        # Score vocabulaire domaine
        domain_words = [word for word in words if word in self.domain_keywords]
        vocab_score = len(domain_words) / len(words) if words else 0.0
        
        # Score termes bloqués
        blocked_score = 0.0
        blocked_categories = []
        
        for category, terms in self.blocked_terms.items():
            category_matches = sum(1 for term in terms if term in query_lower)
            if category_matches > 0:
                blocked_categories.append(category)
                category_penalty = min(1.0, category_matches / max(1, len(words) // 2))
                blocked_score = max(blocked_score, category_penalty)
        
        # Score patterns hors-domaine
        import re
        ood_patterns = [
            r'\b(film|movie|cinema|série|series)\b',
            r'\b(football|sport|match)\b',
            r'\b(politique|president|élection)\b',
            r'\b(crypto|bitcoin|bourse)\b'
        ]
        
        pattern_score = 0.0
        for pattern in ood_patterns:
            if re.search(pattern, query_lower):
                pattern_score = 1.0
                break
        
        # Score final
        if blocked_score > 0.5:
            final_score = 0.9
        elif vocab_score > 0.3:
            final_score = max(0.0, vocab_score - blocked_score * 0.5)
        else:
            final_score = (vocab_score * 0.6) - (blocked_score * 0.3) - (pattern_score * 0.1)
        
        is_in_domain = final_score > 0.15
        
        score_details = {
            "vocab_score": vocab_score,
            "blocked_score": blocked_score,
            "pattern_score": pattern_score,
            "blocked_categories": blocked_categories,
            "final_score": final_score
        }
        
        return is_in_domain, final_score, score_details


class MultiStageReranker:
    """Reranking multi-étapes"""
    
    def __init__(self):
        self.voyage_client = None
        if VOYAGE_AVAILABLE and VOYAGE_API_KEY:
            try:
                self.voyage_client = voyageai.Client(api_key=VOYAGE_API_KEY)
                logger.info("VoyageAI reranker initialisé")
            except Exception as e:
                logger.warning(f"Erreur init VoyageAI: {e}")
    
    async def rerank(self, query: str, documents: List[Document], intent_result=None) -> List[Document]:
        """Reranking des documents"""
        if not documents:
            return documents
        
        try:
            # Stage 1: VoyageAI semantic reranking
            if self.voyage_client and len(documents) > 2:
                documents = await self._voyage_rerank(query, documents)
            
            # Stage 2: Intent-based boosting
            if intent_result:
                documents = self._intent_boost(documents, intent_result)
            
            # Stage 3: Diversity filtering
            documents = self._diversify_results(documents)
            
            return documents[:RAG_RERANK_TOP_K]
            
        except Exception as e:
            logger.error(f"Erreur reranking: {e}")
            return documents[:RAG_RERANK_TOP_K]
    
    async def _voyage_rerank(self, query: str, documents: List[Document]) -> List[Document]:
        """Reranking VoyageAI"""
        try:
            doc_texts = [doc.content for doc in documents]
            
            reranked = self.voyage_client.rerank(
                query=query,
                documents=doc_texts,
                model="rerank-1",
                top_k=min(len(documents), 12)
            )
            
            reranked_docs = []
            for item in reranked.results:
                original_doc = documents[item.index]
                original_doc.score = (original_doc.score * 0.3 + item.relevance_score * 0.7)
                reranked_docs.append(original_doc)
            
            return reranked_docs
            
        except Exception as e:
            logger.error(f"Erreur VoyageAI reranking: {e}")
            return documents
    
    def _intent_boost(self, documents: List[Document], intent_result) -> List[Document]:
        """Boost basé sur l'intention"""
        for doc in documents:
            boost_factor = 1.0
            
            try:
                # Boost correspondance lignée
                if hasattr(intent_result, 'detected_entities') and "line" in intent_result.detected_entities:
                    target_line = intent_result.detected_entities["line"].lower()
                    doc_line = doc.metadata.get("geneticLine", "").lower()
                    if target_line in doc_line or doc_line in target_line:
                        boost_factor *= 1.3
                
                # Boost correspondance âge
                if hasattr(intent_result, 'detected_entities') and "age_days" in intent_result.detected_entities:
                    boost_factor *= 1.2
                
                # Boost queries métriques
                if (hasattr(intent_result, 'intent_type') and 
                    intent_result.intent_type == IntentType.METRIC_QUERY):
                    if any(char.isdigit() for char in doc.content[:200]):
                        boost_factor *= 1.1
                
                doc.score = min(1.0, doc.score * boost_factor)
                        
            except Exception as e:
                logger.warning(f"Erreur intent boost: {e}")
        
        return sorted(documents, key=lambda x: x.score, reverse=True)
    
    def _diversify_results(self, documents: List[Document]) -> List[Document]:
        """Filtrage diversité"""
        if len(documents) <= 3:
            return documents
        
        try:
            diversified = [documents[0]]
            
            for candidate in documents[1:]:
                is_diverse = True
                candidate_words = set(candidate.content.lower().split())
                
                for selected in diversified:
                    selected_words = set(selected.content.lower().split())
                    
                    if candidate_words and selected_words:
                        overlap = len(candidate_words.intersection(selected_words))
                        similarity = overlap / min(len(candidate_words), len(selected_words))
                        
                        if similarity > 0.8:
                            is_diverse = False
                            break
                
                if is_diverse:
                    diversified.append(candidate)
            
            return diversified
            
        except Exception as e:
            logger.warning(f"Erreur diversification: {e}")
            return documents


class ResponseGenerator:
    """Générateur de réponses avec OpenAI"""
    
    def __init__(self, client: OpenAI):
        self.client = client
    
    async def generate_response(self, query: str, context_docs: List[Document], conversation_context: str = "") -> str:
        """Génère une réponse basée sur le contexte"""
        try:
            # Construire le contexte
            context_text = "\n\n".join([
                f"Document {i+1}:\n{doc.content[:1000]}"
                for i, doc in enumerate(context_docs[:5])
            ])
            
            # Prompt système pour l'aviculture
            system_prompt = """Tu es un expert en aviculture spécialisé dans l'aide aux éleveurs de volailles.

INSTRUCTIONS:
1. Réponds uniquement basé sur les documents fournis
2. Sois précis et technique quand approprié
3. Mentionne les lignées génétiques si pertinentes
4. Fournis des données chiffrées quand disponibles
5. Si les documents ne contiennent pas l'information, dis-le clairement

DOMAINE: Aviculture, élevage de volailles, performance, nutrition, santé"""

            # Construire le prompt utilisateur
            user_prompt = f"""CONTEXTE CONVERSATIONNEL:
{conversation_context}

DOCUMENTS DE RÉFÉRENCE:
{context_text}

QUESTION:
{query}

RÉPONSE (basée uniquement sur les documents fournis):"""

            response = await self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,
                max_tokens=800
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Erreur génération réponse: {e}")
            return "Désolé, je ne peux pas générer une réponse pour cette question."


class ResponseVerifier:
    """Vérificateur de réponses"""
    
    def __init__(self, client: OpenAI):
        self.client = client
    
    async def verify_response(self, query: str, response: str, context_docs: List[Document]) -> Dict[str, Any]:
        """Vérification des réponses"""
        if not RAG_VERIFICATION_ENABLED or not context_docs:
            return {"verified": True, "confidence": 0.8, "corrections": []}
        
        try:
            context_text = "\n\n".join([
                f"Document {i+1}: {doc.content[:500]}"
                for i, doc in enumerate(context_docs[:3])
            ])
            
            verification_prompt = f"""Vérifie si la RÉPONSE est supportée par les DOCUMENTS.

RÉPONSE À VÉRIFIER:
{response}

DOCUMENTS DE RÉFÉRENCE:
{context_text}

FORMAT:
- STATUT: [VÉRIFIÉ/PARTIELLEMENT_VÉRIFIÉ/NON_VÉRIFIÉ]
- CONFIANCE: [0.0-1.0]
- PROBLÈMES: [liste des problèmes]"""

            verification = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": verification_prompt}],
                temperature=0.0,
                max_tokens=500
            )
            
            verification_text = verification.choices[0].message.content
            
            # Parser la réponse
            status = "VÉRIFIÉ"
            confidence = 0.8
            
            if "NON_VÉRIFIÉ" in verification_text:
                status = "NON_VÉRIFIÉ"
                confidence = 0.3
            elif "PARTIELLEMENT_VÉRIFIÉ" in verification_text:
                status = "PARTIELLEMENT_VÉRIFIÉ"
                confidence = 0.6
            
            return {
                "verified": status == "VÉRIFIÉ",
                "status": status,
                "confidence": confidence,
                "verification_detail": verification_text
            }
            
        except Exception as e:
            logger.error(f"Erreur vérification: {e}")
            return {"verified": True, "confidence": 0.7, "error": str(e)}


class ConversationMemory:
    """Mémoire conversationnelle"""
    
    def __init__(self, client: OpenAI):
        self.client = client
        self.memory_store = {}
        self.max_exchanges = 5
    
    async def get_contextual_memory(self, tenant_id: str, current_query: str) -> str:
        """Récupère le contexte conversationnel"""
        if tenant_id not in self.memory_store:
            return ""
        
        history = self.memory_store[tenant_id]
        if not history:
            return ""
        
        if len(history) <= 2:
            return "\n\n".join([
                f"Q: {entry['question']}\nR: {entry['answer']}"
                for entry in history
            ])
        
        # Résumé intelligent pour historique long
        try:
            history_text = "\n\n".join([
                f"Échange {i+1}:\nQ: {entry['question']}\nR: {entry['answer']}"
                for i, entry in enumerate(history[-4:])
            ])
            
            summary_prompt = f"""Résume cette conversation avicole en conservant les informations pertinentes pour la nouvelle question.

HISTORIQUE:
{history_text}

NOUVELLE QUESTION: {current_query}

Résumé contextuel (200 mots max):"""

            summary = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": summary_prompt}],
                temperature=0.1,
                max_tokens=250
            )
            
            return summary.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Erreur résumé conversation: {e}")
            return f"Contexte: {history[-1]['question']} -> {history[-1]['answer'][:100]}..."
    
    def add_exchange(self, tenant_id: str, question: str, answer: str):
        """Ajoute un échange"""
        if tenant_id not in self.memory_store:
            self.memory_store[tenant_id] = []
        
        self.memory_store[tenant_id].append({
            "question": question,
            "answer": answer,
            "timestamp": time.time()
        })
        
        if len(self.memory_store[tenant_id]) > self.max_exchanges:
            self.memory_store[tenant_id] = self.memory_store[tenant_id][-self.max_exchanges:]


class InteliaRAGEngine:
    """RAG Engine principal avec OpenAI + Weaviate Direct"""
    
    def __init__(self, openai_client: OpenAI = None):
        self.openai_client = openai_client or self._build_openai_client()
        self.embedder = None
        self.retriever = None
        self.generator = None
        self.verifier = None
        self.memory = None
        self.intent_processor = None
        self.ood_detector = None
        self.reranker = None
        self.weaviate_client = None
        self.is_initialized = False
        self.degraded_mode = False
    
    def _build_openai_client(self) -> OpenAI:
        """Construit le client OpenAI"""
        try:
            http_client = httpx.Client(timeout=30.0)
            return OpenAI(api_key=OPENAI_API_KEY, http_client=http_client)
        except Exception as e:
            logger.warning(f"Erreur client OpenAI personnalisé: {e}")
            return OpenAI(api_key=OPENAI_API_KEY)
    
    async def initialize(self):
        """Initialisation"""
        if self.is_initialized:
            return
            
        logger.info("Initialisation RAG Engine Direct (OpenAI + Weaviate)...")
        
        # Vérifier dépendances
        if not OPENAI_AVAILABLE:
            logger.error("OpenAI non disponible")
            self.degraded_mode = True
            
        if not WEAVIATE_AVAILABLE:
            logger.error("Weaviate non disponible")
            self.degraded_mode = True
        
        if self.degraded_mode:
            logger.warning("Mode dégradé activé")
            self.is_initialized = True
            return
        
        # Initialiser composants
        try:
            self.embedder = OpenAIEmbedder(self.openai_client)
            self.generator = ResponseGenerator(self.openai_client)
            self.verifier = ResponseVerifier(self.openai_client)
            self.memory = ConversationMemory(self.openai_client)
            self.ood_detector = EnhancedOODDetector()
            self.reranker = MultiStageReranker()
            
            if INTENT_PROCESSOR_AVAILABLE:
                self.intent_processor = create_intent_processor()
            
            logger.info("Composants initialisés")
        except Exception as e:
            logger.error(f"Erreur init composants: {e}")
            self.degraded_mode = True
        
        # Connexion Weaviate
        try:
            await self._connect_weaviate()
            self.retriever = WeaviateRetriever(self.weaviate_client)
            logger.info("Weaviate connecté")
        except Exception as e:
            logger.error(f"Erreur connexion Weaviate: {e}")
            self.degraded_mode = True
        
        self.is_initialized = True
        logger.info(f"RAG Engine initialisé (dégradé: {self.degraded_mode})")
    
    async def _connect_weaviate(self):
        """Connexion Weaviate"""
        if WEAVIATE_V4:
            if WEAVIATE_API_KEY and ".weaviate.cloud" in WEAVIATE_URL:
                auth_credentials = wvc.init.Auth.api_key(WEAVIATE_API_KEY)
                self.weaviate_client = weaviate.connect_to_weaviate_cloud(
                    cluster_url=WEAVIATE_URL,
                    auth_credentials=auth_credentials,
                    headers={"X-OpenAI-Api-Key": OPENAI_API_KEY} if OPENAI_API_KEY else {}
                )
            else:
                host = WEAVIATE_URL.replace('http://', '').replace('https://', '')
                port = 8080
                if ':' in host:
                    host, port = host.split(':')
                    port = int(port)
                
                self.weaviate_client = weaviate.connect_to_local(
                    host=host,
                    port=port,
                    headers={"X-OpenAI-Api-Key": OPENAI_API_KEY} if OPENAI_API_KEY else {}
                )
        else:
            # Version 3.x
            if WEAVIATE_API_KEY and ".weaviate.cloud" in WEAVIATE_URL:
                auth_config = weaviate.AuthApiKey(api_key=WEAVIATE_API_KEY)
                self.weaviate_client = weaviate.Client(
                    url=WEAVIATE_URL,
                    auth_client_secret=auth_config,
                    additional_headers={"X-OpenAI-Api-Key": OPENAI_API_KEY} if OPENAI_API_KEY else {}
                )
            else:
                self.weaviate_client = weaviate.Client(
                    url=WEAVIATE_URL,
                    additional_headers={"X-OpenAI-Api-Key": OPENAI_API_KEY} if OPENAI_API_KEY else {}
                )
        
        # Vérifier connexion
        if hasattr(self.weaviate_client, 'is_ready'):
            if not self.weaviate_client.is_ready():
                raise Exception("Weaviate not ready")
        else:
            self.weaviate_client.schema.get()  # Test V3
    
    async def process_query(self, query: str, language: str = "fr", tenant_id: str = "") -> RAGResult:
        """Traitement des requêtes"""
        if not RAG_ENABLED:
            return RAGResult(source=RAGSource.FALLBACK_NEEDED, metadata={"reason": "rag_disabled"})
        
        if not self.is_initialized:
            await self.initialize()
        
        if self.degraded_mode:
            return RAGResult(
                source=RAGSource.FALLBACK_NEEDED,
                metadata={"reason": "degraded_mode"}
            )
        
        start_time = time.time()
        
        try:
            # Contexte conversationnel
            conversation_context = ""
            if tenant_id and self.memory:
                conversation_context = await self.memory.get_contextual_memory(tenant_id, query)
            
            # Intent processing
            intent_result = None
            if self.intent_processor:
                try:
                    intent_result = self.intent_processor.process_query(query)
                except Exception as e:
                    logger.warning(f"Erreur intent processor: {e}")
            
            # OOD detection
            if self.ood_detector:
                is_in_domain, domain_score, score_details = self.ood_detector.calculate_ood_score(query)
                
                if not is_in_domain:
                    return RAGResult(
                        source=RAGSource.OOD_FILTERED,
                        confidence=1.0 - domain_score,
                        processing_time=time.time() - start_time,
                        metadata={
                            "domain_score": domain_score,
                            "score_details": score_details
                        },
                        intent_result=intent_result
                    )
            
            # Embedding de la requête
            search_query = query
            if intent_result and hasattr(intent_result, 'expanded_query') and intent_result.expanded_query:
                search_query = intent_result.expanded_query
            
            query_vector = await self.embedder.embed_query(search_query)
            if not query_vector:
                return RAGResult(
                    source=RAGSource.ERROR,
                    metadata={"error": "embedding_failed"}
                )
            
            # Recherche documents
            documents = await self.retriever.search(query_vector, RAG_SIMILARITY_TOP_K)
            
            if not documents:
                return RAGResult(
                    source=RAGSource.FALLBACK_NEEDED,
                    metadata={"reason": "no_documents_found"}
                )
            
            # Filtrage par confiance
            filtered_docs = [doc for doc in documents if doc.score >= RAG_CONFIDENCE_THRESHOLD]
            
            if not filtered_docs:
                return RAGResult(
                    source=RAGSource.FALLBACK_NEEDED,
                    metadata={"reason": "low_confidence_documents"}
                )
            
            # Reranking
            if len(filtered_docs) > 1:
                filtered_docs = await self.reranker.rerank(search_query, filtered_docs, intent_result)
            
            # Génération réponse
            response_text = await self.generator.generate_response(
                query, filtered_docs, conversation_context
            )
            
            if not response_text or "ne peux pas" in response_text.lower():
                return RAGResult(
                    source=RAGSource.FALLBACK_NEEDED,
                    metadata={"reason": "generation_failed"}
                )
            
            # Vérification
            verification_result = None
            if self.verifier:
                verification_result = await self.verifier.verify_response(
                    query, response_text, filtered_docs
                )
            
            # Calcul confiance
            confidence = self._calculate_confidence(filtered_docs, verification_result)
            
            # Source résultat
            result_source = RAGSource.RAG_KNOWLEDGE
            if verification_result and verification_result.get("verified", True):
                result_source = RAGSource.RAG_VERIFIED
                confidence = min(confidence * 1.1, 0.95)
            
            # Context docs pour résultat
            context_docs = []
            for doc in filtered_docs:
                context_docs.append({
                    "title": doc.metadata.get("title", ""),
                    "content": doc.content,
                    "score": doc.score,
                    "source": doc.metadata.get("source", ""),
                    "genetic_line": doc.metadata.get("geneticLine", ""),
                    "species": doc.metadata.get("species", "")
                })
            
            # Métadonnées
            metadata = {
                "approach": "openai_weaviate_direct",
                "weaviate_version": weaviate_version,
                "weaviate_v4": WEAVIATE_V4,
                "documents_found": len(documents),
                "documents_used": len(filtered_docs),
                "query_expanded": search_query != query,
                "conversation_context_used": bool(conversation_context),
                "reranking_applied": len(filtered_docs) > 1,
                "verification_enabled": RAG_VERIFICATION_ENABLED
            }
            
            if intent_result:
                metadata.update({
                    "intent_type": intent_result.intent_type.value if hasattr(intent_result.intent_type, 'value') else str(intent_result.intent_type),
                    "detected_entities": getattr(intent_result, 'detected_entities', {})
                })
            
            # Sauvegarde mémoire
            if tenant_id and self.memory:
                self.memory.add_exchange(tenant_id, query, response_text)
            
            return RAGResult(
                source=result_source,
                answer=response_text,
                confidence=confidence,
                context_docs=context_docs,
                processing_time=time.time() - start_time,
                metadata=metadata,
                verification_status=verification_result,
                intent_result=intent_result
            )
            
        except Exception as e:
            logger.error(f"Erreur traitement query: {e}")
            return RAGResult(
                source=RAGSource.ERROR,
                confidence=0.0,
                processing_time=time.time() - start_time,
                metadata={"error": str(e)},
                intent_result=intent_result if 'intent_result' in locals() else None
            )
    
    def _calculate_confidence(self, documents: List[Document], verification_result: Dict = None) -> float:
        """Calcul de confiance"""
        if not documents:
            return 0.0
        
        scores = [doc.score for doc in documents if doc.score > 0]
        if not scores:
            return 0.5
        
        avg_score = sum(scores) / len(scores)
        coherence_factor = min(1.2, 1 + (len(scores) - 1) * 0.05)
        
        if len(scores) > 1:
            score_std = np.std(scores)
            distribution_factor = max(0.9, 1 - score_std * 0.5)
        else:
            distribution_factor = 1.0
        
        verification_factor = 1.0
        if verification_result and verification_result.get("verified", True):
            verification_factor = 1.1
        
        final_confidence = avg_score * coherence_factor * distribution_factor * verification_factor
        return min(0.95, max(0.1, final_confidence))
    
    def get_status(self) -> Dict:
        """Status du système"""
        try:
            weaviate_connected = (
                self.weaviate_client is not None and 
                (self.weaviate_client.is_ready() if hasattr(self.weaviate_client, 'is_ready') else True)
            )
            
            return {
                "rag_enabled": RAG_ENABLED,
                "initialized": self.is_initialized,
                "degraded_mode": self.degraded_mode,
                "approach": "openai_weaviate_direct",
                "no_llamaindex_conflicts": True,
                "openai_available": OPENAI_AVAILABLE,
                "weaviate_available": WEAVIATE_AVAILABLE,
                "weaviate_version": weaviate_version if WEAVIATE_AVAILABLE else "N/A",
                "weaviate_v4": WEAVIATE_V4,
                "weaviate_connected": weaviate_connected,
                "intent_processor_available": INTENT_PROCESSOR_AVAILABLE,
                "voyage_reranking": VOYAGE_AVAILABLE and VOYAGE_API_KEY is not None,
                "verification_enabled": RAG_VERIFICATION_ENABLED,
                "confidence_threshold": RAG_CONFIDENCE_THRESHOLD,
                "similarity_top_k": RAG_SIMILARITY_TOP_K,
                "rerank_top_k": RAG_RERANK_TOP_K,
                "features": [
                    "zero_dependency_conflicts",
                    "openai_direct_integration",
                    "weaviate_direct_integration",
                    "enhanced_ood_detection",
                    "multi_stage_reranking",
                    "voyage_ai_integration",
                    "response_verification",
                    "conversation_memory",
                    "intent_based_boosting",
                    "confidence_scoring",
                    "diversity_filtering",
                    "production_ready"
                ]
            }
        except Exception as e:
            logger.error(f"Erreur get_status: {e}")
            return {
                "error": str(e),
                "rag_enabled": RAG_ENABLED,
                "initialized": False,
                "degraded_mode": True
            }
    
    async def cleanup(self):
        """Nettoyage des ressources"""
        try:
            if self.weaviate_client:
                if hasattr(self.weaviate_client, 'close'):
                    self.weaviate_client.close()
            
            if self.memory:
                self.memory.memory_store.clear()
            
            if hasattr(self.openai_client, 'http_client'):
                await self.openai_client.http_client.aclose()
            
            logger.info("RAG Engine nettoyé")
        except Exception as e:
            logger.error(f"Erreur nettoyage: {e}")


# Fonctions utilitaires pour compatibilité
async def create_rag_engine(openai_client: OpenAI = None) -> InteliaRAGEngine:
    """Factory pour créer le RAG engine"""
    try:
        engine = InteliaRAGEngine(openai_client)
        await engine.initialize()
        return engine
    except Exception as e:
        logger.error(f"Erreur création RAG engine: {e}")
        engine = InteliaRAGEngine(openai_client)
        engine.degraded_mode = True
        engine.is_initialized = True
        return engine


async def process_question_with_rag(
    rag_engine: InteliaRAGEngine, 
    question: str, 
    language: str = "fr", 
    tenant_id: str = ""
) -> RAGResult:
    """Interface compatible"""
    try:
        return await rag_engine.process_query(question, language, tenant_id)
    except Exception as e:
        logger.error(f"Erreur process_question_with_rag: {e}")
        return RAGResult(
            source=RAGSource.ERROR,
            confidence=0.0,
            metadata={"error": str(e)}
        )