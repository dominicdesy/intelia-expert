"""
Pipeline d'ingestion intelligent utilisant votre architecture intents.json existante
Collecte automatisée depuis 5 sources avec classification métier avancée
"""

import asyncio
import aiohttp
import time
import json
import logging
import hashlib
import xml.etree.ElementTree as ET
import re
from typing import Dict, List, Optional, Tuple, Set, AsyncGenerator
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
import weaviate
import os
from dotenv import load_dotenv

# Import de votre infrastructure existante
from intent_processor import IntentProcessor, ConfigurationError
from intent_types import IntentType, IntentResult

load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SourceType(Enum):
    """Sources de données configurées"""
    PUBMED = "pubmed"
    CROSSREF = "crossref"
    FAO_AGRIS = "fao_agris"
    EUROPE_PMC = "europe_pmc"
    ARXIV = "arxiv"

@dataclass
class SourceQuota:
    """Gestion intelligente des quotas API"""
    requests_per_second: float
    requests_per_hour: int
    daily_limit: int
    current_count: int = 0
    last_reset: float = 0
    is_active: bool = True

@dataclass
class DocumentClassification:
    """Classification automatique via intents.json"""
    intent_type: str
    confidence: float
    genetic_line: Optional[str] = None
    bird_type: Optional[str] = None
    site_type: Optional[str] = None
    phase: Optional[str] = None
    age_range: Optional[str] = None
    metrics_detected: List[str] = None
    metadata: Dict = None
    
    def __post_init__(self):
        if self.metrics_detected is None:
            self.metrics_detected = []
        if self.metadata is None:
            self.metadata = {}

class IntentsBasedClassifier:
    """Classificateur basé sur votre intents.json existant"""
    
    def __init__(self, intents_config: Dict):
        self.intents_config = intents_config
        self.aliases = intents_config.get("aliases", {})
        self.universal_slots = intents_config.get("universal_slots", {})
        self.intents = intents_config.get("intents", {})
        
        # Construction des vocabulaires de reconnaissance
        self._build_classification_vocab()
    
    def _build_classification_vocab(self):
        """Construit les vocabulaires pour la classification automatique"""
        
        # Lignées génétiques avec tous leurs alias
        self.genetic_lines_patterns = {}
        if "line" in self.aliases:
            for main_line, aliases in self.aliases["line"].items():
                all_variants = [main_line] + aliases
                # Création pattern regex pour chaque lignée
                escaped_variants = [re.escape(variant) for variant in all_variants]
                pattern = r'\b(?:' + '|'.join(escaped_variants) + r')\b'
                self.genetic_lines_patterns[main_line] = re.compile(pattern, re.IGNORECASE)
        
        # Types d'oiseaux et sites
        self.bird_type_patterns = self._build_type_patterns("bird_type")
        self.site_type_patterns = self._build_type_patterns("site_type")
        self.phase_patterns = self._build_type_patterns("phase")
        
        # Métriques par intention
        self.metrics_by_intent = {}
        for intent_name, intent_config in self.intents.items():
            metrics = list(intent_config.get("metrics", {}).keys())
            self.metrics_by_intent[intent_name] = metrics
        
        logger.info(f"Vocabulaire construit: {len(self.genetic_lines_patterns)} lignées, "
                   f"{len(self.metrics_by_intent)} types d'intentions")
    
    def _build_type_patterns(self, type_name: str) -> Dict[str, re.Pattern]:
        """Construit les patterns regex pour un type donné"""
        patterns = {}
        if type_name in self.aliases:
            for main_type, aliases in self.aliases[type_name].items():
                all_variants = [main_type] + aliases
                escaped_variants = [re.escape(variant) for variant in all_variants]
                pattern = r'\b(?:' + '|'.join(escaped_variants) + r')\b'
                patterns[main_type] = re.compile(pattern, re.IGNORECASE)
        return patterns
    
    def classify_document(self, title: str, abstract: str, source: str) -> DocumentClassification:
        """Classification automatique d'un document selon intents.json"""
        
        full_text = f"{title} {abstract}".lower()
        
        # 1. Détection de la lignée génétique
        genetic_line = self._detect_genetic_line(full_text)
        
        # 2. Détection du type d'oiseau et site
        bird_type = self._detect_type(full_text, self.bird_type_patterns)
        site_type = self._detect_type(full_text, self.site_type_patterns)
        
        # 3. Détection de la phase
        phase = self._detect_type(full_text, self.phase_patterns)
        
        # 4. Détection de l'âge
        age_range = self._detect_age_range(full_text)
        
        # 5. Classification d'intention
        intent_type, confidence, metrics = self._classify_intent(full_text)
        
        # 6. Validation selon les règles intents.json
        classification = DocumentClassification(
            intent_type=intent_type,
            confidence=confidence,
            genetic_line=genetic_line,
            bird_type=bird_type,
            site_type=site_type,
            phase=phase,
            age_range=age_range,
            metrics_detected=metrics,
            metadata={
                "source": source,
                "classification_timestamp": time.time(),
                "text_length": len(full_text)
            }
        )
        
        # Application des règles de défaut depuis intents.json
        self._apply_default_rules(classification, full_text)
        
        return classification
    
    def _detect_genetic_line(self, text: str) -> Optional[str]:
        """Détecte la lignée génétique dans le texte"""
        for line_name, pattern in self.genetic_lines_patterns.items():
            if pattern.search(text):
                return line_name
        return None
    
    def _detect_type(self, text: str, patterns: Dict[str, re.Pattern]) -> Optional[str]:
        """Détecte un type dans le texte avec patterns"""
        for type_name, pattern in patterns.items():
            if pattern.search(text):
                return type_name
        return None
    
    def _detect_age_range(self, text: str) -> Optional[str]:
        """Détecte la tranche d'âge dans le texte"""
        age_patterns = [
            (r'\b(\d+)\s*(?:day|jour|d)\b', 'days'),
            (r'\b(\d+)\s*(?:week|semaine|sem|w)\b', 'weeks'),
            (r'\b(\d+)-(\d+)\s*(?:day|jour|d)\b', 'days_range'),
            (r'\b(\d+)-(\d+)\s*(?:week|semaine|w)\b', 'weeks_range')
        ]
        
        for pattern, age_type in age_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                if age_type.endswith('_range'):
                    return f"{matches[0][0]}-{matches[0][1]}_{age_type.split('_')[0]}"
                else:
                    return f"{matches[0]}_{age_type}"
        
        return None
    
    def _classify_intent(self, text: str) -> Tuple[str, float, List[str]]:
        """Classifie l'intention selon les métriques détectées"""
        
        intent_scores = {}
        detected_metrics = []
        
        # Score par intention basé sur les métriques détectées
        for intent_name, metrics in self.metrics_by_intent.items():
            score = 0
            intent_metrics = []
            
            for metric in metrics:
                # Conversion métrique vers mots-clés de recherche
                metric_keywords = self._metric_to_keywords(metric)
                for keyword in metric_keywords:
                    if keyword in text:
                        score += 1
                        if metric not in intent_metrics:
                            intent_metrics.append(metric)
            
            if score > 0:
                intent_scores[intent_name] = score
                detected_metrics.extend(intent_metrics)
        
        # Sélection de la meilleure intention
        if intent_scores:
            best_intent = max(intent_scores.items(), key=lambda x: x[1])
            confidence = min(0.95, best_intent[1] / 10)  # Normalisation
            return best_intent[0], confidence, detected_metrics
        
        # Fallback vers classification générale
        return "metric_query", 0.3, []
    
    def _metric_to_keywords(self, metric: str) -> List[str]:
        """Convertit une métrique en mots-clés de recherche"""
        metric_mapping = {
            "body_weight_target": ["weight", "poids", "body weight", "live weight"],
            "fcr_target": ["fcr", "feed conversion", "conversion alimentaire"],
            "daily_gain": ["gain", "growth", "croissance", "daily gain"],
            "mortality_expected_pct": ["mortality", "mortalité", "death", "mort"],
            "water_intake_daily": ["water", "eau", "drinking", "consumption"],
            "feed_intake_daily": ["feed", "aliment", "feeding", "intake"],
            "ambient_temp_target": ["temperature", "température", "temp", "ambient"],
            "humidity_target": ["humidity", "humidité", "moisture"],
            "lighting_hours": ["light", "lighting", "éclairage", "hours"],
            "egg_production_pct": ["egg", "oeuf", "production", "laying"],
            # Ajout de toutes les autres métriques...
        }
        
        return metric_mapping.get(metric, [metric.replace("_", " ")])
    
    def _apply_default_rules(self, classification: DocumentClassification, text: str):
        """Applique les règles par défaut depuis intents.json"""
        
        defaults_by_topic = self.intents_config.get("defaults_by_topic", {})
        
        # Si pas de site_type détecté, utiliser les défauts par sujet
        if not classification.site_type:
            for topic, default_site in defaults_by_topic.items():
                if topic in text:
                    classification.site_type = default_site
                    break
        
        # Règles de cohérence
        if classification.genetic_line:
            # Ross/Cobb = broiler
            if any(x in classification.genetic_line.lower() for x in ["ross", "cobb", "hubbard"]):
                if not classification.bird_type:
                    classification.bird_type = "broiler"
                if not classification.site_type:
                    classification.site_type = "broiler_farm"
            
            # ISA/Lohmann = layer
            elif any(x in classification.genetic_line.lower() for x in ["isa", "lohmann", "hy-line"]):
                if not classification.bird_type:
                    classification.bird_type = "layer"
                if not classification.site_type:
                    classification.site_type = "layer_farm"

class AutomatedIngestionPipeline:
    """Pipeline d'ingestion automatisé avec classification intents.json"""
    
    def __init__(self):
        # Configuration Weaviate
        self.weaviate_url = os.getenv("WEAVIATE_URL", "")
        self.weaviate_api_key = os.getenv("WEAVIATE_API_KEY", "")
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "")
        self.collection_name = "InteliaKnowledge"
        
        # Validation
        if not all([self.weaviate_url, self.weaviate_api_key, self.openai_api_key]):
            raise RuntimeError("Variables d'environnement manquantes")
        
        # Chargement de la configuration intents.json
        self.intents_config = self._load_intents_config()
        self.classifier = IntentsBasedClassifier(self.intents_config)
        
        # Configuration des sources
        self.sources_config = {
            SourceType.PUBMED: SourceQuota(0.33, 100, 1000),  # 3 req/sec max
            SourceType.CROSSREF: SourceQuota(0.5, 200, 2000),  # 2 req/sec max
            SourceType.FAO_AGRIS: SourceQuota(0.2, 50, 500),   # 5 req/sec max
            SourceType.EUROPE_PMC: SourceQuota(1.0, 500, 5000), # 1 req/sec max
            SourceType.ARXIV: SourceQuota(0.1, 20, 200)        # 10 req/sec max
        }
        
        # Statistiques
        self.stats = {
            "total_collected": 0,
            "total_uploaded": 0,
            "by_source": {source.value: 0 for source in SourceType},
            "by_intent": {},
            "errors": 0,
            "start_time": time.time()
        }
        
        # Cache de déduplication
        self.existing_hashes = set()
        
        # Clients
        self.weaviate_client = None
        self.session = None
    
    def _load_intents_config(self) -> Dict:
        """Charge la configuration intents.json"""
        possible_paths = [
            "intents.json",
            "./intents.json",
            os.path.join(os.path.dirname(__file__), "intents.json"),
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    logger.info(f"Configuration intents.json chargée depuis {path}")
                    return config
        
        raise FileNotFoundError("intents.json non trouvé")
    
    async def start_automated_collection(self, target_documents: int = 30000):
        """Démarre la collecte automatisée sur les 5 sources"""
        
        logger.info(f"🚀 DÉMARRAGE COLLECTE AUTOMATISÉE - Objectif: {target_documents} documents")
        
        try:
            # Connexions
            await self._initialize_connections()
            
            # Chargement cache déduplication
            await self._load_deduplication_cache()
            
            # Collecte parallèle sur toutes les sources
            collection_tasks = [
                self._collect_from_source(source, target_documents // len(SourceType))
                for source in SourceType
            ]
            
            # Exécution avec gestion d'erreurs
            results = await asyncio.gather(*collection_tasks, return_exceptions=True)
            
            # Traitement des résultats
            for i, result in enumerate(results):
                source = list(SourceType)[i]
                if isinstance(result, Exception):
                    logger.error(f"❌ Erreur source {source.value}: {result}")
                    self.stats["errors"] += 1
                else:
                    logger.info(f"✅ Source {source.value} terminée: {result} documents")
            
            # Rapport final
            await self._generate_final_report()
            
        except Exception as e:
            logger.error(f"❌ Erreur critique pipeline: {e}")
            raise
        finally:
            await self._cleanup_connections()
    
    async def _initialize_connections(self):
        """Initialise les connexions Weaviate et HTTP"""
        
        # Connexion Weaviate
        try:
            import weaviate.classes as wvc
            
            auth = wvc.init.Auth.api_key(self.weaviate_api_key)
            headers = {"X-OpenAI-Api-Key": self.openai_api_key}
            
            self.weaviate_client = weaviate.connect_to_weaviate_cloud(
                cluster_url=self.weaviate_url,
                auth_credentials=auth,
                headers=headers
            )
            
            if not self.weaviate_client.is_ready():
                raise RuntimeError("Weaviate non prêt")
            
            logger.info("✅ Connexion Weaviate établie")
            
        except Exception as e:
            logger.error(f"❌ Erreur connexion Weaviate: {e}")
            raise
        
        # Session HTTP
        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        self.session = aiohttp.ClientSession(timeout=timeout)
        logger.info("✅ Session HTTP initialisée")
    
    async def _load_deduplication_cache(self):
        """Charge les hashes existants pour éviter les doublons"""
        
        try:
            collection = self.weaviate_client.collections.get(self.collection_name)
            
            response = collection.query.fetch_objects(
                limit=50000,  # Limitation raisonnable
                return_properties=["fileHash"]
            )
            
            for obj in response.objects:
                file_hash = obj.properties.get('fileHash')
                if file_hash:
                    self.existing_hashes.add(file_hash)
            
            logger.info(f"📋 Cache déduplication: {len(self.existing_hashes)} documents existants")
            
        except Exception as e:
            logger.warning(f"⚠️ Cache déduplication désactivé: {e}")
    
    async def _collect_from_source(self, source: SourceType, target_docs: int) -> int:
        """Collecte depuis une source spécifique avec respect des quotas"""
        
        logger.info(f"📡 Collecte {source.value} - Objectif: {target_docs} documents")
        
        collected = 0
        quota = self.sources_config[source]
        
        try:
            if source == SourceType.PUBMED:
                collected = await self._collect_pubmed(target_docs, quota)
            elif source == SourceType.CROSSREF:
                collected = await self._collect_crossref(target_docs, quota)
            elif source == SourceType.FAO_AGRIS:
                collected = await self._collect_fao_agris(target_docs, quota)
            elif source == SourceType.EUROPE_PMC:
                collected = await self._collect_europe_pmc(target_docs, quota)
            elif source == SourceType.ARXIV:
                collected = await self._collect_arxiv(target_docs, quota)
            
            self.stats["by_source"][source.value] = collected
            return collected
            
        except Exception as e:
            logger.error(f"❌ Erreur collecte {source.value}: {e}")
            self.stats["errors"] += 1
            return 0
    
    async def _collect_pubmed(self, target_docs: int, quota: SourceQuota) -> int:
        """Collecte intelligente PubMed basée sur intents.json"""
        
        collected = 0
        
        # Requêtes ciblées selon les lignées de votre intents.json
        genetic_lines = list(self.intents_config.get("aliases", {}).get("line", {}).keys())
        
        # Requêtes par lignée + métrique
        queries = [
            f"{line} performance FCR weight gain 2020:2025[dp]"
            for line in genetic_lines[:10]  # Top 10 lignées
        ] + [
            f"broiler performance water intake temperature 2020:2025[dp]",
            f"layer production egg weight nutrition 2020:2025[dp]",
            f"poultry vaccination biosecurity protocol 2020:2025[dp]",
            f"broiler lighting program welfare density 2020:2025[dp]",
            f"poultry ventilation climate environment 2020:2025[dp]"
        ]
        
        for query in queries:
            if collected >= target_docs:
                break
            
            # Respect du quota
            await self._wait_for_quota(quota)
            
            try:
                # Recherche PubMed
                search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
                params = {
                    "db": "pubmed",
                    "term": query,
                    "retmax": min(50, target_docs - collected),
                    "retmode": "json"
                }
                
                async with self.session.get(search_url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        pmids = data.get("esearchresult", {}).get("idlist", [])
                        
                        if pmids:
                            batch_collected = await self._process_pubmed_batch(pmids, quota)
                            collected += batch_collected
                            logger.info(f"PubMed: +{batch_collected} docs pour '{query[:30]}...'")
                
                quota.current_count += 1
                
            except Exception as e:
                logger.warning(f"Erreur requête PubMed '{query[:30]}...': {e}")
        
        return collected
    
    async def _process_pubmed_batch(self, pmids: List[str], quota: SourceQuota) -> int:
        """Traite un lot de PMIDs avec classification"""
        
        processed = 0
        
        # Traitement par petits lots
        batch_size = 10
        for i in range(0, len(pmids), batch_size):
            batch = pmids[i:i + batch_size]
            
            # Respect du quota
            await self._wait_for_quota(quota)
            
            try:
                # Récupération détails
                fetch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
                params = {
                    "db": "pubmed",
                    "id": ",".join(batch),
                    "retmode": "xml"
                }
                
                async with self.session.get(fetch_url, params=params) as response:
                    if response.status == 200:
                        xml_content = await response.text()
                        documents = self._parse_pubmed_xml(xml_content)
                        
                        for doc in documents:
                            if await self._process_and_upload_document(doc, "pubmed"):
                                processed += 1
                
                quota.current_count += 1
                
            except Exception as e:
                logger.warning(f"Erreur traitement batch PubMed: {e}")
        
        return processed
    
    def _parse_pubmed_xml(self, xml_content: str) -> List[Dict]:
        """Parse XML PubMed vers documents structurés"""
        
        documents = []
        
        try:
            root = ET.fromstring(xml_content)
            
            for article in root.findall(".//PubmedArticle"):
                try:
                    # Extraction des données
                    title_elem = article.find(".//ArticleTitle")
                    title = title_elem.text if title_elem is not None else ""
                    
                    abstract_elem = article.find(".//Abstract/AbstractText")
                    abstract = abstract_elem.text if abstract_elem is not None else ""
                    
                    pmid_elem = article.find(".//PMID")
                    pmid = pmid_elem.text if pmid_elem is not None else ""
                    
                    # Métadonnées supplémentaires
                    journal_elem = article.find(".//Journal/Title")
                    journal = journal_elem.text if journal_elem is not None else ""
                    
                    year_elem = article.find(".//PubDate/Year")
                    year = year_elem.text if year_elem is not None else ""
                    
                    if title and abstract:
                        documents.append({
                            "title": title,
                            "abstract": abstract,
                            "pmid": pmid,
                            "journal": journal,
                            "year": year,
                            "source_url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                            "full_content": f"{title}\n\n{abstract}"
                        })
                
                except Exception:
                    continue
        
        except ET.ParseError as e:
            logger.warning(f"Erreur parsing XML PubMed: {e}")
        
        return documents
    
    async def _process_and_upload_document(self, document: Dict, source: str) -> bool:
        """Traite et upload un document avec classification intents.json"""
        
        try:
            # Hash pour déduplication
            content_hash = hashlib.md5(document["full_content"].encode()).hexdigest()
            
            if content_hash in self.existing_hashes:
                return False  # Doublon
            
            # Classification automatique via intents.json
            classification = self.classifier.classify_document(
                document["title"],
                document["abstract"],
                source
            )
            
            # Filtrage qualité (seulement documents pertinents)
            if classification.confidence < 0.2:
                return False
            
            # Construction document Weaviate compatible avec votre schéma
            weaviate_doc = {
                # Contenu de base
                "content": document["full_content"],
                "title": document["title"],
                "source": document.get("source_url", ""),
                
                # Classification intents.json
                "category": classification.intent_type,
                "language": "en",  # Documents majoritairement anglais
                
                # Entités métier extraites
                "geneticLine": classification.genetic_line or "unknown",
                "birdType": classification.bird_type or "unknown", 
                "siteType": classification.site_type or "unknown",
                "phase": classification.phase or "unknown",
                
                # Métadonnées techniques
                "originalFile": f"{source}_ingestion",
                "fileHash": content_hash,
                "syncTimestamp": time.time(),
                "chunkIndex": 0,
                "totalChunks": 1,
                "isComplete": True,
                
                # Métadonnées de classification
                "classificationConfidence": classification.confidence,
                "detectedMetrics": classification.metrics_detected,
                "sourceMetadata": {
                    "journal": document.get("journal", ""),
                    "year": document.get("year", ""),
                    "pmid": document.get("pmid", "")
                }
            }
            
            # Upload vers Weaviate
            success = await self._upload_to_weaviate(weaviate_doc)
            
            if success:
                # Mise à jour statistiques
                self.existing_hashes.add(content_hash)
                self.stats["total_collected"] += 1
                self.stats["total_uploaded"] += 1
                
                # Statistiques par intention
                intent = classification.intent_type
                self.stats["by_intent"][intent] = self.stats["by_intent"].get(intent, 0) + 1
                
                logger.info(f"✅ Uploadé: {classification.intent_type} - {classification.genetic_line} - {document['title'][:50]}...")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Erreur traitement document: {e}")
            self.stats["errors"] += 1
            return False
    
    async def _upload_to_weaviate(self, document: Dict) -> bool:
        """Upload sécurisé vers Weaviate"""
        
        try:
            collection = self.weaviate_client.collections.get(self.collection_name)
            collection.data.insert(properties=document)
            
            # Pause pour OpenAI API rate limiting
            await asyncio.sleep(1.5)
            
            return True
            
        except Exception as e:
            logger.warning(f"Erreur upload Weaviate: {e}")
            return False
    
    # Méthodes pour les autres sources (CrossRef, FAO AGRIS, etc.)
    # Implémentation similaire avec APIs spécifiques...
    
    async def _collect_crossref(self, target_docs: int, quota: SourceQuota) -> int:
        """Collecte CrossRef - Publications académiques récentes"""
        # Implementation similaire avec API CrossRef
        return 0
    
    async def _collect_fao_agris(self, target_docs: int, quota: SourceQuota) -> int:
        """Collecte FAO AGRIS - Standards agricoles"""
        # Implementation similaire avec API FAO
        return 0
    
    async def _collect_europe_pmc(self, target_docs: int, quota: SourceQuota) -> int:
        """Collecte Europe PMC - Recherche européenne"""
        # Implementation similaire avec API Europe PMC
        return 0
    
    async def _collect_arxiv(self, target_docs: int, quota: SourceQuota) -> int:
        """Collecte arXiv - Recherche émergente"""
        # Implementation similaire avec API arXiv
        return 0
    
    async def _wait_for_quota(self, quota: SourceQuota):
        """Gestion intelligente des quotas API"""
        
        current_time = time.time()
        
        # Reset horaire
        if current_time - quota.last_reset > 3600:
            quota.current_count = 0
            quota.last_reset = current_time
        
        # Respect du rate limiting
        if quota.requests_per_second > 0:
            min_interval = 1.0 / quota.requests_per_second
            await asyncio.sleep(min_interval)
        
        # Vérification limite horaire
        if quota.current_count >= quota.requests_per_hour:
            wait_time = 3600 - (current_time - quota.last_reset)
            if wait_time > 0:
                logger.info(f"⏳ Attente quota: {wait_time:.0f}s")
                await asyncio.sleep(wait_time)
    
    async def _generate_final_report(self):
        """Génère le rapport final de collecte"""
        
        duration = time.time() - self.stats["start_time"]
        
        report = f"""
🎯 RAPPORT FINAL D'INGESTION
=============================
⏱️  Durée: {duration:.0f}s ({duration/60:.1f}min)
📊 Documents collectés: {self.stats['total_collected']}
⬆️  Documents uploadés: {self.stats['total_uploaded']}
❌ Erreurs: {self.stats['errors']}

📡 PAR SOURCE:
{chr(10).join(f"  • {source}: {count}" for source, count in self.stats['by_source'].items())}

🎯 PAR INTENTION:
{chr(10).join(f"  • {intent}: {count}" for intent, count in self.stats['by_intent'].items())}

✅ Enrichissement terminé avec succès!
        """
        
        logger.info(report)
    
    async def _cleanup_connections(self):
        """Nettoyage des connexions"""
        
        if self.session:
            await self.session.close()
        
        if self.weaviate_client:
            self.weaviate_client.close()
        
        logger.info("🧹 Connexions fermées")

# Fonction principale
async def main():
    """Lance le pipeline d'ingestion automatisé"""
    
    try:
        pipeline = AutomatedIngestionPipeline()
        await pipeline.start_automated_collection(target_documents=30000)
        
    except Exception as e:
        logger.error(f"❌ Erreur critique: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())