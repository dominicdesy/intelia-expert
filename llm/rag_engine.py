# -*- coding: utf-8 -*-
"""
rag_engine.py - Module RAG hybride pour Intelia Expert
Intégration: Classification NLI + Recherche hybride + Reranking VoyageAI + Génération contextuelle
"""

import os
import re
import json
import asyncio
import logging
import time
from typing import Dict, List, Optional, Tuple, Any, AsyncGenerator
from dataclasses import dataclass
from enum import Enum

import weaviate
import voyageai
from openai import OpenAI
from transformers import pipeline
import numpy as np
from sentence_transformers import SentenceTransformer

# Import du nouveau module
from intent_processor import create_intent_processor, IntentType, IntentResult

logger = logging.getLogger(__name__)

# Configuration par variables d'environnement
RAG_ENABLED = os.getenv("RAG_ENABLED", "true").lower() == "true"
WEAVIATE_URL = os.getenv("WEAVIATE_URL", "http://localhost:8080")
WEAVIATE_API_KEY = os.getenv("WEAVIATE_API_KEY")
VOYAGE_API_KEY = os.getenv("VOYAGE_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
NLI_MODEL_PATH = os.getenv("NLI_MODEL_PATH", "MoritzLaurer/deberta-v3-base-zeroshot-v2")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
RAG_SEARCH_LIMIT = int(os.getenv("RAG_SEARCH_LIMIT", "20"))
RAG_RERANK_TOP_K = int(os.getenv("RAG_RERANK_TOP_K", "5"))
RAG_CONFIDENCE_THRESHOLD = float(os.getenv("RAG_CONFIDENCE_THRESHOLD", "0.7"))
RAG_CONTEXT_WINDOW = int(os.getenv("RAG_CONTEXT_WINDOW", "4000"))

class RAGSource(Enum):
    """Sources de réponse possibles"""
    RAG_KNOWLEDGE = "rag_knowledge"
    OOD_FILTERED = "ood_filtered"
    FALLBACK_NEEDED = "fallback_needed"
    ERROR = "error"

@dataclass
class RAGResult:
    """Résultat du pipeline RAG"""
    source: RAGSource
    answer: Optional[str] = None
    confidence: float = 0.0
    context_docs: List[Dict] = None
    processing_time: float = 0.0
    metadata: Dict = None
    
    def __post_init__(self):
        if self.context_docs is None:
            self.context_docs = []
        if self.metadata is None:
            self.metadata = {}

@dataclass
class SearchResult:
    """Résultat de recherche unifié"""
    content: str
    score: float
    metadata: Dict
    source: str = "hybrid"

class InDomainClassifier:
    """Classification NLI pour filtrage hors-domaine (économique)"""
    
    def __init__(self):
        self.classifier = None
        self.is_loaded = False
        self.domain_labels = [
            "agriculture, élevage et aviculture",
            "technologie, informatique et cryptomonnaies", 
            "médecine humaine et santé",
            "finances personnelles et investissements",
            "autres sujets généraux"
        ]
        self.target_label = self.domain_labels[0]
    
    async def load_model(self):
        """Chargement asynchrone du modèle NLI"""
        if self.is_loaded:
            return
        
        try:
            logger.info(f"Chargement du modèle NLI: {NLI_MODEL_PATH}")
            loop = asyncio.get_event_loop()
            self.classifier = await loop.run_in_executor(
                None,
                lambda: pipeline(
                    "zero-shot-classification",
                    model=NLI_MODEL_PATH,
                    device=-1  # CPU pour économiser les ressources
                )
            )
            self.is_loaded = True
            logger.info("Modèle NLI chargé avec succès")
        except Exception as e:
            logger.error(f"Erreur chargement modèle NLI: {e}")
            self.is_loaded = False
    
    async def classify_question(self, question: str, threshold: float = 0.45) -> Tuple[bool, float]:
        """
        Classifie si une question est dans le domaine agricole
        Returns: (is_in_domain, confidence_score)
        """
        if not self.is_loaded:
            await self.load_model()
        
        if not self.classifier:
            # Fallback simple si modèle non disponible
            agri_keywords = [
                'poulet', 'poule', 'aviculture', 'élevage', 'volaille',
                'aliment', 'vaccination', 'maladie', 'production',
                'chicken', 'poultry', 'broiler', 'layer', 'feed'
            ]
            has_keywords = any(keyword in question.lower() for keyword in agri_keywords)
            return has_keywords, 0.8 if has_keywords else 0.2
        
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self.classifier(question, self.domain_labels)
            )
            
            # Vérifier si la catégorie la plus probable est agriculture
            top_label = result['labels'][0]
            top_score = result['scores'][0]
            
            is_agriculture = (top_label == self.target_label) and (top_score >= threshold)
            
            logger.debug(f"Classification NLI: {top_label} ({top_score:.3f}) -> {'IN' if is_agriculture else 'OUT'}")
            
            return is_agriculture, top_score
            
        except Exception as e:
            logger.error(f"Erreur classification NLI: {e}")
            # Fallback conservatif
            return True, 0.5

class HybridSearchEngine:
    """Moteur de recherche hybride (vectoriel + BM25) avec Weaviate"""
    
    def __init__(self):
        self.client = None
        self.embedding_model = None
        self.is_connected = False
        self.class_name = "InteliaKnowledge"
    
    async def initialize(self):
        """Initialisation de la connexion Weaviate et du modèle d'embedding"""
        if self.is_connected:
            return
        
        try:
            # Configuration client Weaviate
            auth_config = None
            if WEAVIATE_API_KEY:
                auth_config = weaviate.AuthApiKey(api_key=WEAVIATE_API_KEY)
            
            self.client = weaviate.Client(
                url=WEAVIATE_URL,
                auth_client_secret=auth_config
            )
            
            # Test de connexion
            if self.client.is_ready():
                logger.info("Connexion Weaviate établie")
                self.is_connected = True
                
                # Créer le schéma si nécessaire
                await self._ensure_schema_exists()
            else:
                logger.warning("Weaviate non disponible, recherche désactivée")
                
        except Exception as e:
            logger.error(f"Erreur connexion Weaviate: {e}")
            self.is_connected = False
    
    async def _ensure_schema_exists(self):
        """Crée le schéma Weaviate si nécessaire"""
        try:
            # Vérifier si la classe existe
            if not self.client.schema.exists(self.class_name):
                schema = {
                    "class": self.class_name,
                    "description": "Base de connaissances Intelia Expert en aviculture",
                    "vectorizer": "text2vec-openai",
                    "moduleConfig": {
                        "text2vec-openai": {
                            "model": "ada",
                            "modelVersion": "002",
                            "type": "text",
                            "apiKey": OPENAI_API_KEY
                        }
                    },
                    "properties": [
                        {
                            "name": "content",
                            "dataType": ["text"],
                            "description": "Contenu principal du document"
                        },
                        {
                            "name": "title",
                            "dataType": ["string"],
                            "description": "Titre du document"
                        },
                        {
                            "name": "category",
                            "dataType": ["string"],
                            "description": "Catégorie thématique"
                        },
                        {
                            "name": "language",
                            "dataType": ["string"],
                            "description": "Langue du document"
                        },
                        {
                            "name": "source",
                            "dataType": ["string"],
                            "description": "Source d'origine"
                        },
                        {
                            "name": "confidence_score",
                            "dataType": ["number"],
                            "description": "Score de confiance du contenu"
                        }
                    ]
                }
                self.client.schema.create_class(schema)
                logger.info(f"Schéma {self.class_name} créé")
        except Exception as e:
            logger.error(f"Erreur création schéma: {e}")
    
    async def search(self, query: str, language: str = "fr", limit: int = None) -> List[SearchResult]:
        """
        Recherche hybride vectorielle + BM25
        """
        if not self.is_connected or not self.client:
            logger.warning("Weaviate non disponible pour la recherche")
            return []
        
        if limit is None:
            limit = RAG_SEARCH_LIMIT
        
        try:
            # Recherche hybride Weaviate
            result = (
                self.client.query
                .get(self.class_name, ["content", "title", "category", "source", "confidence_score"])
                .with_hybrid(query=query, alpha=0.7)  # 0.7 = plus vectoriel, 0.3 = plus BM25
                .with_limit(limit)
                .with_additional(["score", "distance"])
                .do()
            )
            
            # Traitement des résultats
            search_results = []
            if "data" in result and "Get" in result["data"]:
                documents = result["data"]["Get"].get(self.class_name, [])
                
                for doc in documents:
                    search_results.append(SearchResult(
                        content=doc.get("content", ""),
                        score=doc.get("_additional", {}).get("score", 0.0),
                        metadata={
                            "title": doc.get("title", ""),
                            "category": doc.get("category", ""),
                            "source": doc.get("source", ""),
                            "confidence_score": doc.get("confidence_score", 1.0),
                            "distance": doc.get("_additional", {}).get("distance", 1.0)
                        },
                        source="weaviate_hybrid"
                    ))
            
            logger.info(f"Recherche hybride: {len(search_results)} résultats pour '{query[:50]}...'")
            return search_results
            
        except Exception as e:
            logger.error(f"Erreur recherche Weaviate: {e}")
            return []
    
    async def add_documents(self, documents: List[Dict]) -> bool:
        """Ajouter des documents à l'index"""
        if not self.is_connected:
            await self.initialize()
        
        if not self.is_connected:
            return False
        
        try:
            with self.client.batch as batch:
                batch.batch_size = 100
                
                for doc in documents:
                    batch.add_data_object(
                        data_object={
                            "content": doc.get("content", ""),
                            "title": doc.get("title", ""),
                            "category": doc.get("category", "general"),
                            "language": doc.get("language", "fr"),
                            "source": doc.get("source", "manual"),
                            "confidence_score": doc.get("confidence_score", 1.0)
                        },
                        class_name=self.class_name
                    )
            
            logger.info(f"Ajouté {len(documents)} documents à l'index")
            return True
            
        except Exception as e:
            logger.error(f"Erreur ajout documents: {e}")
            return False

class VoyageReranker:
    """Reranker utilisant l'API VoyageAI (gratuit jusqu'à 200M tokens)"""
    
    def __init__(self):
        self.client = None
        self.is_available = bool(VOYAGE_API_KEY)
        
        if self.is_available:
            try:
                self.client = voyageai.Client(api_key=VOYAGE_API_KEY)
                logger.info("VoyageAI Reranker initialisé")
            except Exception as e:
                logger.error(f"Erreur init VoyageAI: {e}")
                self.is_available = False
    
    async def rerank(self, query: str, results: List[SearchResult], top_k: int = None) -> List[SearchResult]:
        """
        Rerank les résultats avec VoyageAI
        """
        if not self.is_available or not results:
            return results[:top_k] if top_k else results
        
        if top_k is None:
            top_k = RAG_RERANK_TOP_K
        
        try:
            # Préparer les documents pour le reranking
            documents = [result.content for result in results]
            
            # Appel API VoyageAI (asynchrone simulé)
            loop = asyncio.get_event_loop()
            rerank_result = await loop.run_in_executor(
                None,
                lambda: self.client.rerank(
                    query=query,
                    documents=documents,
                    model="rerank-2",
                    top_k=min(top_k, len(documents))
                )
            )
            
            # Réorganiser selon les scores
            reranked_results = []
            for item in rerank_result.results:
                original_result = results[item.index]
                # Mise à jour du score avec celui de VoyageAI
                original_result.score = item.relevance_score
                original_result.metadata["voyage_score"] = item.relevance_score
                original_result.source = "voyage_reranked"
                reranked_results.append(original_result)
            
            logger.info(f"Reranking VoyageAI: {len(reranked_results)}/{len(results)} résultats")
            return reranked_results
            
        except Exception as e:
            logger.error(f"Erreur reranking VoyageAI: {e}")
            # Fallback sans reranking
            return results[:top_k]

class ContextualGenerator:
    """Générateur de réponses avec contexte RAG"""
    
    def __init__(self, openai_client: OpenAI):
        self.client = openai_client
    
    def _build_context_prompt(self, query: str, context_docs: List[SearchResult], language: str) -> str:
        """Construit le prompt avec contexte"""
        
        # Limiter le contexte pour rester dans la fenêtre
        context_parts = []
        total_length = 0
        
        for i, doc in enumerate(context_docs):
            doc_text = f"[Document {i+1}]\nTitre: {doc.metadata.get('title', 'N/A')}\nContenu: {doc.content}\n"
            
            if total_length + len(doc_text) > RAG_CONTEXT_WINDOW:
                break
                
            context_parts.append(doc_text)
            total_length += len(doc_text)
        
        context = "\n".join(context_parts)
        
        # Prompt système multilingue
        system_prompts = {
            "fr": """Tu es un expert en aviculture utilisant une base de connaissances spécialisée. 

INSTRUCTIONS:
- Réponds UNIQUEMENT basé sur les documents fournis ci-dessous
- Si l'information n'est pas dans les documents, dis clairement "Cette information n'est pas disponible dans ma base de connaissances"
- Sois précis, technique et factuel
- Cite les documents pertinents dans ta réponse
- Réponds en français""",
            
            "en": """You are a poultry expert using a specialized knowledge base.

INSTRUCTIONS:
- Answer ONLY based on the documents provided below
- If information is not in documents, clearly state "This information is not available in my knowledge base"
- Be precise, technical and factual
- Cite relevant documents in your response  
- Respond in English""",
            
            "es": """Eres un experto en avicultura usando una base de conocimientos especializada.

INSTRUCCIONES:
- Responde ÚNICAMENTE basado en los documentos proporcionados abajo
- Si la información no está en los documentos, di claramente "Esta información no está disponible en mi base de conocimientos"
- Sé preciso, técnico y factual
- Cita los documentos pertinentes en tu respuesta
- Responde en español"""
        }
        
        system_prompt = system_prompts.get(language, system_prompts["fr"])
        
        return f"""{system_prompt}

DOCUMENTOS DE CONTEXTO:
{context}

PREGUNTA DEL USUARIO: {query}

RESPUESTA BASADA EN LOS DOCUMENTOS:"""
    
    async def generate_answer(self, query: str, context_docs: List[SearchResult], language: str = "fr", specialized_prompt: str = None) -> Dict:
        """Génère une réponse contextuelle avec prompt optionnel spécialisé"""
        
        if not context_docs:
            return {
                "answer": None,
                "confidence": 0.0,
                "context_used": []
            }
        
        try:
            if specialized_prompt:
                # Utiliser le prompt spécialisé si fourni
                prompt = self._build_specialized_context_prompt(query, context_docs, language, specialized_prompt)
            else:
                # Utiliser le prompt générique standard
                prompt = self._build_context_prompt(query, context_docs, language)
            
            # Génération avec OpenAI
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",  # Économique et performant
                messages=[
                    {"role": "user", "content": prompt}
                ],
                max_tokens=800,
                temperature=0.1,  # Factuel et cohérent
                top_p=0.9
            )
            
            answer = response.choices[0].message.content.strip()
            
            # Calculer un score de confiance basique
            confidence = min(0.9, sum(doc.score for doc in context_docs) / len(context_docs))
            
            return {
                "answer": answer,
                "confidence": confidence,
                "context_used": [
                    {
                        "title": doc.metadata.get("title", ""),
                        "score": doc.score,
                        "source": doc.metadata.get("source", "")
                    }
                    for doc in context_docs
                ]
            }
            
        except Exception as e:
            logger.error(f"Erreur génération contextuelle: {e}")
            return {
                "answer": None,
                "confidence": 0.0,
                "context_used": []
            }
    
    def _build_specialized_context_prompt(self, query: str, context_docs: List[SearchResult], language: str, specialized_prompt: str) -> str:
        """Construit un prompt avec expertise spécialisée"""
        
        # Limiter le contexte pour rester dans la fenêtre
        context_parts = []
        total_length = 0
        
        for i, doc in enumerate(context_docs):
            doc_text = f"[Document {i+1}]\nTitre: {doc.metadata.get('title', 'N/A')}\nContenu: {doc.content}\n"
            
            if total_length + len(doc_text) > RAG_CONTEXT_WINDOW:
                break
                
            context_parts.append(doc_text)
            total_length += len(doc_text)
        
        context = "\n".join(context_parts)
        
        return f"""{specialized_prompt}

DOCUMENTS DE RÉFÉRENCE:
{context}

QUESTION: {query}

RÉPONSE EXPERTE:"""

class RAGEngine:
    """Pipeline RAG principal - orchestrateur de tous les composants"""
    
    def __init__(self, openai_client: OpenAI):
        self.classifier = InDomainClassifier()
        self.search_engine = HybridSearchEngine()
        self.reranker = VoyageReranker()
        self.generator = ContextualGenerator(openai_client)
        self.intent_processor = None  # Processeur d'intentions métier
        self.is_initialized = False
    
    async def initialize(self):
        """Initialisation de tous les composants"""
        if self.is_initialized:
            return
        
        logger.info("Initialisation RAG Engine...")
        
        # Initialisation du processeur d'intentions
        try:
            self.intent_processor = create_intent_processor()
            logger.info("Processeur d'intentions initialisé")
        except Exception as e:
            logger.error(f"Erreur init processeur intentions: {e}")
            self.intent_processor = None
        
        # Initialisation parallèle des composants
        await asyncio.gather(
            self.classifier.load_model(),
            self.search_engine.initialize()
        )
        
        self.is_initialized = True
        logger.info("RAG Engine initialisé avec succès")
    
    async def process_query(self, query: str, language: str = "fr", tenant_id: str = "") -> RAGResult:
        """
        Pipeline RAG complet avec processeur d'intentions
        1. Analyse d'intention métier
        2. Classification OOD renforcée
        3. Recherche hybride avec expansion
        4. Reranking
        5. Génération contextuelle avec prompt spécialisé
        """
        if not RAG_ENABLED:
            return RAGResult(source=RAGSource.FALLBACK_NEEDED)
        
        if not self.is_initialized:
            await self.initialize()
        
        start_time = time.time()
        
        try:
            # Étape 1: Analyse d'intention métier
            intent_result = None
            classification_method = "nli_only"
            
            if self.intent_processor:
                try:
                    intent_result = self.intent_processor.process_query(query)
                    
                    # Si détecté comme hors-domaine par le vocabulaire métier, court-circuiter
                    if intent_result.intent_type == IntentType.OUT_OF_DOMAIN:
                        logger.info(f"Question hors-domaine détectée par vocabulaire métier: {query[:50]}...")
                        return RAGResult(
                            source=RAGSource.OOD_FILTERED,
                            confidence=intent_result.confidence,
                            processing_time=time.time() - start_time,
                            metadata={
                                "classification_method": "vocabulary_filter",
                                "intent_type": intent_result.intent_type.value,
                                "vocab_confidence": intent_result.confidence,
                                "detected_entities": intent_result.detected_entities
                            }
                        )
                    
                    classification_method = "vocabulary_enhanced"
                    logger.info(f"Intent détecté: {intent_result.intent_type.value}, entités: {intent_result.detected_entities}")
                    
                except Exception as e:
                    logger.error(f"Erreur processeur intentions: {e}")
                    intent_result = None
            
            # Étape 2: Classification NLI (fallback ou complément)
            if intent_result and intent_result.intent_type != IntentType.OUT_OF_DOMAIN:
                # Vocabulaire métier confirme que c'est avicole, accepter
                is_in_domain = True
                classification_confidence = intent_result.confidence
            else:
                # Fallback vers classification NLI
                is_in_domain, classification_confidence = await self.classifier.classify_question(query)
                classification_method = "nli_fallback"
            
            if not is_in_domain:
                logger.info(f"Question hors-domaine (méthode: {classification_method}): {query[:50]}...")
                return RAGResult(
                    source=RAGSource.OOD_FILTERED,
                    confidence=classification_confidence,
                    processing_time=time.time() - start_time,
                    metadata={
                        "classification_method": classification_method,
                        "classification_score": classification_confidence
                    }
                )
            
            # Étape 3: Recherche hybride avec expansion de requête
            search_query = query
            if intent_result and intent_result.expanded_query != query:
                search_query = intent_result.expanded_query
                logger.info(f"Requête expansée: '{query}' -> '{search_query}'")
            
            search_results = await self.search_engine.search(search_query, language)
            
            if not search_results:
                logger.info(f"Aucun résultat de recherche pour: {search_query[:50]}...")
                return RAGResult(
                    source=RAGSource.FALLBACK_NEEDED,
                    confidence=0.0,
                    processing_time=time.time() - start_time,
                    metadata={
                        "classification_method": classification_method,
                        "search_results_count": 0,
                        "query_expanded": search_query != query
                    }
                )
            
            # Étape 4: Reranking avec VoyageAI
            reranked_results = await self.reranker.rerank(search_query, search_results)
            
            # Filtrer par seuil de confiance
            high_confidence_results = [
                r for r in reranked_results 
                if r.score >= RAG_CONFIDENCE_THRESHOLD
            ]
            
            if not high_confidence_results:
                logger.info(f"Résultats sous seuil de confiance ({RAG_CONFIDENCE_THRESHOLD})")
                return RAGResult(
                    source=RAGSource.FALLBACK_NEEDED,
                    confidence=max(r.score for r in reranked_results) if reranked_results else 0.0,
                    processing_time=time.time() - start_time,
                    metadata={
                        "classification_method": classification_method,
                        "search_results_count": len(search_results),
                        "reranked_count": len(reranked_results),
                        "max_score": max(r.score for r in reranked_results) if reranked_results else 0.0,
                        "query_expanded": search_query != query
                    }
                )
            
            # Étape 5: Génération contextuelle avec prompt spécialisé
            specialized_prompt = None
            if intent_result and self.intent_processor:
                specialized_prompt = self.intent_processor.get_specialized_prompt(intent_result)
            
            generation_result = await self.generator.generate_answer(
                query, high_confidence_results[:5], language, specialized_prompt
            )
            
            if not generation_result["answer"]:
                return RAGResult(
                    source=RAGSource.FALLBACK_NEEDED,
                    confidence=0.0,
                    processing_time=time.time() - start_time
                )
            
            processing_time = time.time() - start_time
            
            # Métadonnées enrichies
            metadata = {
                "classification_method": classification_method,
                "classification_score": classification_confidence,
                "search_results_count": len(search_results),
                "reranked_count": len(reranked_results),
                "high_confidence_count": len(high_confidence_results),
                "generation_model": "gpt-4o-mini",
                "query_expanded": search_query != query,
                "specialized_prompt_used": specialized_prompt is not None
            }
            
            # Ajouter les métadonnées d'intention si disponibles
            if intent_result:
                metadata.update({
                    "intent_type": intent_result.intent_type.value,
                    "detected_entities": intent_result.detected_entities,
                    "vocab_confidence": intent_result.metadata.get("vocab_score", 0.0)
                })
            
            logger.info(f"RAG réussi: {len(high_confidence_results)} docs, conf: {generation_result['confidence']:.3f}, temps: {processing_time:.2f}s")
            
            return RAGResult(
                source=RAGSource.RAG_KNOWLEDGE,
                answer=generation_result["answer"],
                confidence=generation_result["confidence"],
                context_docs=generation_result["context_used"],
                processing_time=processing_time,
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Erreur pipeline RAG: {e}")
            return RAGResult(
                source=RAGSource.ERROR,
                confidence=0.0,
                processing_time=time.time() - start_time,
                metadata={"error": str(e)}
            )
    
    async def add_knowledge(self, documents: List[Dict]) -> bool:
        """Ajouter des documents à la base de connaissances"""
        if not self.is_initialized:
            await self.initialize()
        
        return await self.search_engine.add_documents(documents)
    
    def get_status(self) -> Dict:
        """Status des composants RAG"""
        status = {
            "rag_enabled": RAG_ENABLED,
            "initialized": self.is_initialized,
            "classifier_loaded": self.classifier.is_loaded,
            "search_connected": self.search_engine.is_connected,
            "reranker_available": self.reranker.is_available,
            "weaviate_url": WEAVIATE_URL,
            "voyage_api_configured": bool(VOYAGE_API_KEY),
            "nli_model": NLI_MODEL_PATH
        }
        
        # Ajouter le status du processeur d'intentions
        if self.intent_processor:
            status["intent_processor_loaded"] = True
            status["intent_vocabulary_size"] = len(self.intent_processor.vocabulary_extractor.poultry_keywords)
        else:
            status["intent_processor_loaded"] = False
        
        return status

# Fonctions utilitaires pour l'intégration dans main.py
async def create_rag_engine(openai_client: OpenAI) -> RAGEngine:
    """Factory pour créer et initialiser le RAG Engine"""
    engine = RAGEngine(openai_client)
    await engine.initialize()
    return engine

async def process_question_with_rag(
    rag_engine: RAGEngine, 
    question: str, 
    language: str = "fr", 
    tenant_id: str = ""
) -> RAGResult:
    """Interface simple pour traiter une question via RAG"""
    return await rag_engine.process_query(question, language, tenant_id)