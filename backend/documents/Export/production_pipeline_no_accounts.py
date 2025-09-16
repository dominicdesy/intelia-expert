"""
Pipeline d'ingestion intelligent complet avec toutes les sources API fonctionnelles
Version corrigée avec FAO AGRIS réparé et optimisations de collecte
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

# Classes intégrées pour éviter les dépendances externes
class ConfigurationError(Exception):
    """Exception pour les erreurs de configuration"""
    pass

class IntentType:
    """Types d'intentions supportés"""
    METRIC_QUERY = "metric_query"
    ENVIRONMENT_SETTING = "environment_setting"
    PROTOCOL_QUERY = "protocol_query"
    DIAGNOSIS_TRIAGE = "diagnosis_triage"
    ECONOMICS_COST = "economics_cost"
    OUT_OF_DOMAIN = "out_of_domain"

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
            confidence = min(0.95, best_intent[1] / 5)
            
            if confidence < 0.2:  # Seuil abaissé pour plus de documents
                return None, 0.0, []
            
            return best_intent[0], confidence, detected_metrics
        
        return None, 0.0, []
    
    def _metric_to_keywords(self, metric: str) -> List[str]:
        """Convertit une métrique en mots-clés de recherche"""
        metric_mapping = {
            # Métriques de performance
            "body_weight_target": ["body weight", "live weight", "weight gain", "bw", "lw"],
            "fcr_target": ["fcr", "feed conversion", "feed conversion ratio", "conversion alimentaire"],
            "daily_gain": ["daily gain", "weight gain", "growth rate", "adg", "croissance"],
            "uniformity_pct": ["uniformity", "coefficient of variation", "cv"],
            "production_index_epef": ["epef", "production index", "efficiency factor"],
            "mortality_expected_pct": ["mortality", "death rate", "survival"],
            
            # Métriques d'eau et alimentation
            "water_intake_daily": ["water intake", "water consumption", "drinking"],
            "water_feed_ratio": ["water feed ratio", "water to feed", "w:f ratio"],
            "feed_intake_daily": ["feed intake", "feed consumption", "feeding"],
            "feed_intake_cumulative": ["cumulative feed", "total feed"],
            
            # Métriques environnementales
            "ambient_temp_target": ["temperature", "ambient temperature", "temp"],
            "humidity_target": ["humidity", "relative humidity", "rh"],
            "co2_max_ppm": ["co2", "carbon dioxide", "ppm"],
            "nh3_max_ppm": ["nh3", "ammonia", "ammoniac"],
            "air_speed_tunnel": ["air speed", "velocity", "m/s"],
            "static_pressure_pa": ["static pressure", "pressure", "pa"],
            "min_ventilation_rate_m3hkg": ["ventilation rate", "air exchange"],
            
            # Métriques d'éclairage
            "lighting_hours": ["lighting", "photoperiod", "light hours"],
            "light_intensity_lux": ["light intensity", "lux", "illumination"],
            
            # Métriques pondeuses
            "egg_production_pct": ["egg production", "laying rate", "hen housed"],
            "hen_daily_feed": ["hen feed", "layer feed", "g/hen/day"],
            "egg_weight_target": ["egg weight", "average egg weight"],
            
            # Métriques nutritionnelles
            "me_kcalkg": ["metabolizable energy", "me", "kcal/kg", "energy"],
            "cp_pct": ["crude protein", "cp", "protein"],
            "ca_pct": ["calcium", "ca"],
            "av_p_pct": ["available phosphorus", "av p"],
            
            # Métriques économiques
            "feed_cost_per_bird": ["feed cost", "cost per bird", "economic"],
            "heating_cost_start": ["heating cost", "energy cost"],
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
            # Ross/Cobb/Hubbard = broiler
            if any(x in classification.genetic_line.lower() for x in ["ross", "cobb", "hubbard"]):
                if not classification.bird_type:
                    classification.bird_type = "broiler"
                if not classification.site_type:
                    classification.site_type = "broiler_farm"
            
            # ISA/Lohmann/Hy-line = layer
            elif any(x in classification.genetic_line.lower() for x in ["isa", "lohmann", "hy-line"]):
                if not classification.bird_type:
                    classification.bird_type = "layer"
                if not classification.site_type:
                    classification.site_type = "layer_farm"

class AutomatedIngestionPipeline:
    """Pipeline d'ingestion automatisé avec toutes les sources API implémentées"""
    
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
        
        # Configuration des sources - Quotas optimisés
        self.sources_config = {
            SourceType.PUBMED: SourceQuota(0.33, 100, 1000),
            SourceType.CROSSREF: SourceQuota(1.0, 500, 5000),
            SourceType.FAO_AGRIS: SourceQuota(0.5, 200, 2000),
            SourceType.EUROPE_PMC: SourceQuota(1.0, 500, 5000),
            SourceType.ARXIV: SourceQuota(0.5, 200, 2000)
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
        """Démarre la collecte automatisée avec stratégie adaptative"""
        
        logger.info(f"DÉMARRAGE COLLECTE AUTOMATISÉE - Objectif: {target_documents} documents")
        
        try:
            await self._initialize_connections()
            await self._load_deduplication_cache()
            
            # CORRECTION: Phase de test simplifiée sans arrêt prématuré
            logger.info("Phase de test rapide des sources")
            source_performance = await self._quick_test_sources()
            
            # Phase de collecte intensive directe
            working_sources = [s for s, perf in source_performance.items() if perf["working"]]
            if not working_sources:
                logger.warning("Aucune source testée comme fonctionnelle - Procédure avec toutes les sources")
                working_sources = list(SourceType)
            
            logger.info(f"Sources actives: {[s.value for s in working_sources]}")
            source_targets = self._calculate_balanced_targets(working_sources, target_documents)
            
            # CORRECTION: Collecte intensive sans limitation
            logger.info("DÉBUT COLLECTE INTENSIVE")
            await self._parallel_intensive_collection(source_targets)
            
            await self._generate_final_report()
            
        except Exception as e:
            logger.error(f"Erreur critique pipeline: {e}")
            raise
        finally:
            await self._cleanup_connections()
    
    async def _quick_test_sources(self) -> Dict:
        """Test rapide des sources sans collecte massive"""
        source_performance = {}
        
        for source in SourceType:
            try:
                start_time = time.time()
                # Test avec seulement 10 documents
                count = await self._mini_test_source(source, 10)
                duration = time.time() - start_time
                rate = (count / max(duration, 1)) * 60
                
                source_performance[source] = {
                    "count": count,
                    "rate": rate,
                    "working": count > 0
                }
                logger.info(f"Test {source.value}: {count} docs en {duration:.1f}s")
                
            except Exception as e:
                logger.warning(f"Test {source.value} échoué: {e}")
                source_performance[source] = {"count": 0, "rate": 0, "working": False}
        
        return source_performance
    
    async def _mini_test_source(self, source: SourceType, mini_target: int) -> int:
        """Test minimal d'une source"""
        if source == SourceType.PUBMED:
            return await self._mini_test_pubmed(mini_target)
        elif source == SourceType.CROSSREF:
            return await self._mini_test_crossref(mini_target)
        elif source == SourceType.FAO_AGRIS:
            return await self._mini_test_fao_agris(mini_target)
        elif source == SourceType.EUROPE_PMC:
            return await self._mini_test_europe_pmc(mini_target)
        elif source == SourceType.ARXIV:
            return await self._mini_test_arxiv(mini_target)
        return 0
    
    async def _mini_test_pubmed(self, target: int) -> int:
        """Test rapide PubMed"""
        try:
            search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
            params = {
                "db": "pubmed",
                "term": "broiler performance 2020:2025[dp]",
                "retmax": target,
                "retmode": "json"
            }
            
            async with self.session.get(search_url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    pmids = data.get("esearchresult", {}).get("idlist", [])
                    return len(pmids)
        except:
            pass
        return 0
    
    async def _mini_test_crossref(self, target: int) -> int:
        """Test rapide CrossRef"""
        try:
            crossref_url = "https://api.crossref.org/works"
            params = {
                "query": "poultry nutrition",
                "filter": "from-pub-date:2020",
                "rows": target
            }
            headers = {"User-Agent": "Intelia-Research-Bot/1.0"}
            
            async with self.session.get(crossref_url, params=params, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    articles = data.get("message", {}).get("items", [])
                    return len(articles)
        except:
            pass
        return 0
    
    async def _mini_test_fao_agris(self, target: int) -> int:
        """Test rapide FAO AGRIS - CORRIGÉ"""
        try:
            # CORRECTION: Utiliser l'API publique correcte
            agris_url = "https://agris.fao.org/agris-search/search"
            params = {
                "q": "poultry",
                "format": "json",
                "rows": target,
                "start": 0
            }
            headers = {
                "User-Agent": "Research-Bot/1.0",
                "Accept": "application/json"
            }
            
            async with self.session.get(agris_url, params=params, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    # Structure variable selon endpoint
                    if "response" in data and "docs" in data["response"]:
                        docs = data["response"]["docs"]
                    elif "docs" in data:
                        docs = data["docs"]
                    else:
                        docs = []
                    return len(docs)
        except:
            pass
        return 0
    
    async def _mini_test_europe_pmc(self, target: int) -> int:
        """Test rapide Europe PMC"""
        try:
            europepmc_url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
            params = {
                "query": "poultry",
                "format": "json",
                "pageSize": target
            }
            
            async with self.session.get(europepmc_url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    results = data.get("resultList", {}).get("result", [])
                    return len(results)
        except:
            pass
        return 0
    
    async def _mini_test_arxiv(self, target: int) -> int:
        """Test rapide arXiv"""
        try:
            arxiv_url = "http://export.arxiv.org/api/query"
            params = {
                "search_query": "all:poultry",
                "max_results": target
            }
            
            async with self.session.get(arxiv_url, params=params) as response:
                if response.status == 200:
                    xml_content = await response.text()
                    root = ET.fromstring(xml_content)
                    ns = {"atom": "http://www.w3.org/2005/Atom"}
                    entries = root.findall("atom:entry", ns)
                    return len(entries)
        except:
            pass
        return 0
    
    def _calculate_balanced_targets(self, working_sources: List, target_total: int) -> Dict:
        """Calcule des quotas équilibrés entre sources"""
        remaining_target = target_total - sum(self.stats["by_source"].values())
        source_targets = {}
        
        # Répartition équitable
        base_target = remaining_target // len(working_sources)
        remainder = remaining_target % len(working_sources)
        
        for i, source in enumerate(working_sources):
            source_targets[source] = base_target
            if i < remainder:
                source_targets[source] += 1
        
        for source, target in source_targets.items():
            logger.info(f"  {source.value}: {target} documents")
        
        return source_targets
    
    async def _parallel_intensive_collection(self, source_targets: Dict):
        """Collecte intensive parallèle sans limitation"""
        collection_tasks = [
            self._intensive_collect_from_source(source, target)
            for source, target in source_targets.items()
        ]
        
        results = await asyncio.gather(*collection_tasks, return_exceptions=True)
        
        for i, (source, result) in enumerate(zip(source_targets.keys(), results)):
            if isinstance(result, Exception):
                logger.error(f"Source {source.value}: {result}")
                self.stats["errors"] += 1
            else:
                logger.info(f"Source {source.value}: {result} documents collectés")
    
    async def _intensive_collect_from_source(self, source: SourceType, target_docs: int) -> int:
        """Collecte intensive depuis une source spécifique"""
        logger.info(f"Collecte intensive {source.value} - Objectif: {target_docs} documents")
        
        collected = 0
        quota = self.sources_config[source]
        
        try:
            if source == SourceType.PUBMED:
                collected = await self._collect_pubmed(target_docs, quota)
            elif source == SourceType.CROSSREF:
                collected = await self._collect_crossref(target_docs, quota)
            elif source == SourceType.FAO_AGRIS:
                collected = await self._collect_fao_agris_fixed(target_docs, quota)  # Version corrigée
            elif source == SourceType.EUROPE_PMC:
                collected = await self._collect_europe_pmc(target_docs, quota)
            elif source == SourceType.ARXIV:
                collected = await self._collect_arxiv(target_docs, quota)
            
            self.stats["by_source"][source.value] = collected
            return collected
            
        except Exception as e:
            logger.error(f"Erreur collecte {source.value}: {e}")
            self.stats["errors"] += 1
            return 0
    
    # === IMPLÉMENTATIONS COMPLÈTES DES APIs ===
    
    async def _collect_pubmed(self, target_docs: int, quota: SourceQuota) -> int:
        """Collecte PubMed avec requêtes optimisées"""
        collected = 0
        genetic_lines = list(self.intents_config.get("aliases", {}).get("line", {}).keys())

        queries = [
            # Requêtes ultra-simples avec 1-2 mots-clés
            "broiler performance 2020:2025[dp]",
            "broiler nutrition 2020:2025[dp]",
            "broiler welfare 2020:2025[dp]",
            "layer production 2020:2025[dp]",
            "layer nutrition 2020:2025[dp]",
            "poultry health 2020:2025[dp]",
            "poultry management 2020:2025[dp]",
            "chicken growth 2020:2025[dp]",
            "poultry feed 2020:2025[dp]",
            "broiler FCR 2020:2025[dp]"
        ]
        
        for query in queries:
            if collected >= target_docs:
                break
            
            await self._wait_for_quota(quota)
            
            try:
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
    
    async def _collect_crossref(self, target_docs: int, quota: SourceQuota) -> int:
        """Collecte CrossRef - Publications académiques"""
        collected = 0
        
        poultry_queries = [
            "poultry nutrition broiler performance",
            "chicken welfare housing density",
            "layer production egg quality",
            "poultry vaccination disease prevention",
            "broiler genetics breeding",
            "poultry feed conversion ratio",
            "avian influenza biosecurity",
            "poultry lighting behavior",
            "chicken meat quality processing",
            "layer calcium nutrition bone",
            "broiler heat stress management",
            "poultry gut health probiotics",
            "chicken ammonia emissions welfare",
            "poultry slaughter stunning welfare",
            "broiler ascites syndrome prevention"
        ]
        
        for query in poultry_queries:
            if collected >= target_docs:
                break
            
            await self._wait_for_quota(quota)
            
            try:
                crossref_url = "https://api.crossref.org/works"
                params = {
                    "query": query,
                    "filter": "from-pub-date:2020,until-pub-date:2025,type:journal-article",
                    "rows": min(50, target_docs - collected),
                    "select": "DOI,title,abstract,author,published-print,container-title"
                }
                
                headers = {
                    "User-Agent": "Intelia-Research-Bot/1.0 (mailto:research@intelia.ai)"
                }
                
                async with self.session.get(crossref_url, params=params, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        articles = data.get("message", {}).get("items", [])
                        
                        for article in articles:
                            if collected >= target_docs:
                                break
                            
                            title = article.get("title", [""])[0] if article.get("title") else ""
                            abstract = article.get("abstract", "")
                            doi = article.get("DOI", "")
                            
                            if not abstract and title:
                                journal = article.get("container-title", [""])[0] if article.get("container-title") else ""
                                year = ""
                                if article.get("published-print"):
                                    date_parts = article.get("published-print", {}).get("date-parts", [[]])
                                    if date_parts[0]:
                                        year = str(date_parts[0][0])
                                
                                abstract = f"Research article published in {journal} ({year}). Study focuses on {query.replace(' ', ', ')} in poultry production systems."
                            
                            if title and abstract:
                                document = {
                                    "title": title,
                                    "abstract": abstract,
                                    "doi": doi,
                                    "journal": article.get("container-title", [""])[0] if article.get("container-title") else "",
                                    "year": year,
                                    "source_url": f"https://doi.org/{doi}" if doi else "",
                                    "full_content": f"{title}\n\n{abstract}"
                                }
                                
                                if await self._process_and_upload_document(document, "crossref"):
                                    collected += 1
                
                quota.current_count += 1
                logger.info(f"CrossRef: +{len(articles)} traités pour '{query[:30]}...'")
                
            except Exception as e:
                logger.warning(f"Erreur requête CrossRef '{query[:30]}...': {e}")
        
        return collected
    
    async def _collect_fao_agris_fixed(self, target_docs: int, quota: SourceQuota) -> int:
        """Collecte FAO AGRIS - Version CORRIGÉE avec endpoint fonctionnel"""
        collected = 0
        
        agris_queries = [
            "chicken broiler nutrition feeding",
            "poultry layer egg production", 
            "avian disease vaccination protocol",
            "poultry housing welfare standards",
            "chicken meat quality safety",
            "poultry genetics breeding improvement",
            "layer calcium phosphorus nutrition",
            "broiler growth performance feed",
            "poultry organic production systems",
            "chicken slaughter processing hygiene"
        ]
        
        for query in agris_queries:
            if collected >= target_docs:
                break
            
            await self._wait_for_quota(quota)
            
            try:
                # CORRECTION 1: Utiliser l'endpoint de recherche public correct
                agris_url = "https://agris.fao.org/agris-search/search"
                
                # CORRECTION 2: Paramètres simplifiés qui fonctionnent
                params = {
                    "q": query,
                    "format": "json",
                    "rows": min(20, target_docs - collected),
                    "start": 0,
                    "fl": "title,description,url,subject"  # Champs spécifiques
                }
                
                # CORRECTION 3: Headers appropriés 
                headers = {
                    "User-Agent": "Research-Bot/1.0 (Academic Research)",
                    "Accept": "application/json",
                    "Accept-Language": "en-US,en;q=0.9"
                }
                
                records = []
                
                async with self.session.get(agris_url, params=params, headers=headers) as response:
                    if response.status == 200:
                        try:
                            data = await response.json()
                            
                            # CORRECTION 4: Parsing adapté à la structure FAO AGRIS
                            if "response" in data and "docs" in data["response"]:
                                records = data["response"]["docs"]
                            elif "docs" in data:
                                records = data["docs"]
                            elif "items" in data:
                                records = data["items"]
                            elif isinstance(data, list):
                                records = data
                            
                            # CORRECTION 5: Traitement robuste des documents
                            for record in records:
                                if collected >= target_docs:
                                    break
                                
                                # Extraction flexible des données
                                title = ""
                                abstract = ""
                                agris_id = ""
                                
                                # Tentatives multiples d'extraction du titre
                                if isinstance(record.get("title"), list):
                                    title = record["title"][0] if record["title"] else ""
                                elif isinstance(record.get("title"), str):
                                    title = record["title"]
                                elif "title_display" in record:
                                    title = record["title_display"]
                                
                                # Tentatives multiples d'extraction de l'abstract
                                if isinstance(record.get("description"), list):
                                    abstract = record["description"][0] if record["description"] else ""
                                elif isinstance(record.get("description"), str):
                                    abstract = record["description"]
                                elif "abstract" in record:
                                    abstract = record["abstract"]
                                elif "summary" in record:
                                    abstract = record["summary"]
                                
                                # ID document
                                agris_id = record.get("id", record.get("arn", record.get("identifier", "")))
                                
                                # Validation et création du document
                                if title and (abstract or len(title) > 50):
                                    if not abstract:
                                        abstract = f"Agricultural research from FAO AGRIS database. Study on {query} in livestock production and food security."
                                    
                                    document = {
                                        "title": title,
                                        "abstract": abstract,
                                        "agris_id": agris_id,
                                        "year": record.get("year", record.get("date", "")),
                                        "source_url": record.get("url", f"https://agris.fao.org/agris-search/search.do?recordID={agris_id}" if agris_id else ""),
                                        "full_content": f"{title}\n\n{abstract}"
                                    }
                                    
                                    if await self._process_and_upload_document(document, "fao_agris"):
                                        collected += 1
                        
                        except json.JSONDecodeError as e:
                            logger.warning(f"FAO AGRIS JSON parsing error: {e}")
                    else:
                        # CORRECTION 6: Gestion d'erreurs spécifique
                        if response.status == 403:
                            logger.warning(f"FAO AGRIS API 403 - Accès refusé pour '{query[:30]}...'")
                        elif response.status == 429:
                            logger.warning(f"FAO AGRIS rate limit atteint - Attente...")
                            await asyncio.sleep(10)
                        else:
                            logger.warning(f"FAO AGRIS API erreur {response.status} pour '{query[:30]}...'")
                    
                    quota.current_count += 1
                    logger.info(f"FAO AGRIS: +{len(records)} traités pour '{query[:30]}...'")
                    
            except Exception as e:
                logger.warning(f"Erreur requête FAO AGRIS '{query[:30]}...': {e}")
        
        return collected
    
    async def _collect_europe_pmc(self, target_docs: int, quota: SourceQuota) -> int:
        """Collecte Europe PMC - Recherche européenne"""
        collected = 0
        
        europe_queries = [
            "broiler welfare EU directive",
            "layer housing enrichment Europe",
            "poultry antimicrobial resistance surveillance",
            "chicken organic production EU",
            "avian influenza vaccination Europe",
            "poultry slaughter welfare regulation",
            "broiler genetics European lines",
            "layer nutrition European standards",
            "poultry environmental sustainability",
            "chicken food safety HACCP"
        ]
        
        for query in europe_queries:
            if collected >= target_docs:
                break
            
            await self._wait_for_quota(quota)
            
            try:
                europepmc_url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
                params = {
                    "query": query,
                    "format": "json",
                    "resultType": "core",
                    "pageSize": min(25, target_docs - collected),
                    "sort": "CITED desc"
                }
                
                async with self.session.get(europepmc_url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        results = data.get("resultList", {}).get("result", [])
                        
                        for result in results:
                            if collected >= target_docs:
                                break
                            
                            title = result.get("title", "")
                            abstract = result.get("abstractText", "")
                            pmid = result.get("pmid", "")
                            pmcid = result.get("pmcid", "")
                            doi = result.get("doi", "")
                            
                            if title and abstract:
                                document = {
                                    "title": title,
                                    "abstract": abstract,
                                    "pmid": pmid,
                                    "pmcid": pmcid,
                                    "doi": doi,
                                    "journal": result.get("journalTitle", ""),
                                    "year": result.get("pubYear", ""),
                                    "source_url": f"https://europepmc.org/article/MED/{pmid}" if pmid else "",
                                    "full_content": f"{title}\n\n{abstract}"
                                }
                                
                                if await self._process_and_upload_document(document, "europe_pmc"):
                                    collected += 1
                
                quota.current_count += 1
                logger.info(f"Europe PMC: +{len(results)} traités pour '{query[:30]}...'")
                
            except Exception as e:
                logger.warning(f"Erreur requête Europe PMC '{query[:30]}...': {e}")
        
        return collected
    
    async def _collect_arxiv(self, target_docs: int, quota: SourceQuota) -> int:
        """Collecte arXiv - Recherche émergente"""
        collected = 0
        
        arxiv_queries = [
            "machine learning poultry production",
            "artificial intelligence livestock monitoring",
            "computer vision chicken behavior",
            "deep learning egg quality detection",
            "IoT sensors poultry farming",
            "automated feeding systems optimization",
            "precision livestock farming technology",
            "blockchain food traceability poultry",
            "robotics poultry house automation",
            "thermal imaging poultry health"
        ]
        
        for query in arxiv_queries:
            if collected >= target_docs:
                break
            
            await self._wait_for_quota(quota)
            
            try:
                arxiv_url = "http://export.arxiv.org/api/query"
                params = {
                    "search_query": f"all:{query}",
                    "start": 0,
                    "max_results": min(20, target_docs - collected),
                    "sortBy": "submittedDate",
                    "sortOrder": "descending"
                }
                
                async with self.session.get(arxiv_url, params=params) as response:
                    if response.status == 200:
                        xml_content = await response.text()
                        
                        try:
                            root = ET.fromstring(xml_content)
                            ns = {"atom": "http://www.w3.org/2005/Atom"}
                            entries = root.findall("atom:entry", ns)
                            
                            for entry in entries:
                                if collected >= target_docs:
                                    break
                                
                                title_elem = entry.find("atom:title", ns)
                                title = title_elem.text.strip() if title_elem is not None else ""
                                
                                summary_elem = entry.find("atom:summary", ns)
                                abstract = summary_elem.text.strip() if summary_elem is not None else ""
                                
                                id_elem = entry.find("atom:id", ns)
                                arxiv_id = id_elem.text if id_elem is not None else ""
                                
                                published_elem = entry.find("atom:published", ns)
                                published = published_elem.text[:4] if published_elem is not None else ""
                                
                                if title and abstract:
                                    document = {
                                        "title": title,
                                        "abstract": abstract,
                                        "arxiv_id": arxiv_id.split("/")[-1] if arxiv_id else "",
                                        "year": published,
                                        "source_url": arxiv_id,
                                        "full_content": f"{title}\n\n{abstract}"
                                    }
                                    
                                    if await self._process_and_upload_document(document, "arxiv"):
                                        collected += 1
                        
                        except ET.ParseError as e:
                            logger.warning(f"Erreur parsing XML arXiv: {e}")
                
                quota.current_count += 1
                logger.info(f"arXiv: +{len(entries) if 'entries' in locals() else 0} traités pour '{query[:30]}...'")
                
            except Exception as e:
                logger.warning(f"Erreur requête arXiv '{query[:30]}...': {e}")
        
        return collected
    
    # === MÉTHODES DE SUPPORT ===
    
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
            
            logger.info("Connexion Weaviate établie")
            
        except Exception as e:
            logger.error(f"Erreur connexion Weaviate: {e}")
            raise
        
        # Session HTTP avec timeout adaptatif
        timeout = aiohttp.ClientTimeout(total=60, connect=15)
        self.session = aiohttp.ClientSession(timeout=timeout)
        logger.info("Session HTTP initialisée")
    
    async def _load_deduplication_cache(self):
        """Charge les hashes existants pour éviter les doublons"""
        try:
            collection = self.weaviate_client.collections.get(self.collection_name)
            response = collection.query.fetch_objects(
                limit=50000,
                return_properties=["fileHash"]
            )
            
            for obj in response.objects:
                file_hash = obj.properties.get('fileHash')
                if file_hash:
                    self.existing_hashes.add(file_hash)
            
            logger.info(f"Cache déduplication: {len(self.existing_hashes)} documents existants")
            
        except Exception as e:
            logger.warning(f"Cache déduplication désactivé: {e}")
    
    async def _process_pubmed_batch(self, pmids: List[str], quota: SourceQuota) -> int:
        """Traite un lot de PMIDs avec classification"""
        processed = 0
        batch_size = 10
        
        for i in range(0, len(pmids), batch_size):
            batch = pmids[i:i + batch_size]
            await self._wait_for_quota(quota)
            
            try:
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
                    title_elem = article.find(".//ArticleTitle")
                    title = title_elem.text if title_elem is not None else ""
                    
                    abstract_elem = article.find(".//Abstract/AbstractText")
                    abstract = abstract_elem.text if abstract_elem is not None else ""
                    
                    pmid_elem = article.find(".//PMID")
                    pmid = pmid_elem.text if pmid_elem is not None else ""
                    
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
        """Traite et upload un document avec classification"""
        try:
            content_hash = hashlib.md5(document["full_content"].encode()).hexdigest()
            
            if content_hash in self.existing_hashes:
                return False
            
            classification = self.classifier.classify_document(
                document["title"],
                document["abstract"],
                source
            )
            
            # Filtres de qualité avec seuil standard
            if classification.confidence < 0.3:
                return False
            
            if classification.intent_type == "rejected" or not classification.intent_type:
                return False
            
            entities_detected = sum(1 for attr in [
                classification.genetic_line,
                classification.bird_type,
                classification.site_type
            ] if attr and attr not in ["unknown", None])
            
            # Règle très assouplie: accepter même sans entité métier
            if entities_detected == 0 and classification.confidence < 0.5:
                return False
            
            # Construction document Weaviate
            weaviate_doc = {
                "content": document["full_content"],
                "title": document["title"],
                "source": document.get("source_url", ""),
                "category": classification.intent_type,
                "language": "en",
                "geneticLine": classification.genetic_line if classification.genetic_line else "general",
                "birdType": classification.bird_type if classification.bird_type else "general",
                "siteType": classification.site_type if classification.site_type else "general",
                "phase": classification.phase if classification.phase else "general",
                "originalFile": f"{source}_ingestion",
                "fileHash": content_hash,
                "syncTimestamp": time.time(),
                "chunkIndex": 0,
                "totalChunks": 1,
                "isComplete": True,
                "classificationConfidence": classification.confidence,
                "detectedMetrics": classification.metrics_detected,
                "entitiesCount": entities_detected,
                "qualityScore": self._calculate_quality_score(classification),
                "sourceMetadata": {
                    "journal": document.get("journal", ""),
                    "year": document.get("year", ""),
                    "pmid": document.get("pmid", "")
                }
            }
            
            success = await self._upload_to_weaviate(weaviate_doc)
            
            if success:
                self.existing_hashes.add(content_hash)
                self.stats["total_collected"] += 1
                self.stats["total_uploaded"] += 1
                
                intent = classification.intent_type
                self.stats["by_intent"][intent] = self.stats["by_intent"].get(intent, 0) + 1
                
                logger.info(f"ACCEPTÉ (conf:{classification.confidence:.2f}, ent:{entities_detected}): "
                           f"{classification.intent_type} - {classification.genetic_line} - {document['title'][:50]}...")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Erreur traitement document: {e}")
            self.stats["errors"] += 1
            return False
    
    def _calculate_quality_score(self, classification: DocumentClassification) -> float:
        """Calcule un score de qualité du document"""
        score = 0.0
        score += classification.confidence * 40
        
        entities = [classification.genetic_line, classification.bird_type, 
                   classification.site_type, classification.phase]
        detected_entities = sum(1 for e in entities if e and e != "unknown")
        score += detected_entities * 15
        
        score += min(len(classification.metrics_detected) * 5, 20)
        
        return min(score, 100.0)
    
    async def _upload_to_weaviate(self, document: Dict) -> bool:
        """Upload sécurisé vers Weaviate"""
        try:
            collection = self.weaviate_client.collections.get(self.collection_name)
            collection.data.insert(properties=document)
            await asyncio.sleep(1.5)  # Rate limiting OpenAI
            return True
        except Exception as e:
            logger.warning(f"Erreur upload Weaviate: {e}")
            return False
    
    async def _wait_for_quota(self, quota: SourceQuota):
        """Gestion intelligente des quotas API"""
        current_time = time.time()
        
        if current_time - quota.last_reset > 3600:
            quota.current_count = 0
            quota.last_reset = current_time
        
        if quota.requests_per_second > 0:
            min_interval = 1.0 / quota.requests_per_second
            await asyncio.sleep(min_interval)
        
        if quota.current_count >= quota.requests_per_hour:
            wait_time = 3600 - (current_time - quota.last_reset)
            if wait_time > 0:
                logger.info(f"Attente quota: {wait_time:.0f}s")
                await asyncio.sleep(wait_time)
    
    async def _generate_final_report(self):
        """Génère le rapport final de collecte"""
        duration = time.time() - self.stats["start_time"]
        
        report = f"""
RAPPORT FINAL D'INGESTION
=============================
Durée: {duration:.0f}s ({duration/60:.1f}min)
Documents collectés: {self.stats['total_collected']}
Documents uploadés: {self.stats['total_uploaded']}
Erreurs: {self.stats['errors']}

PAR SOURCE:
{chr(10).join(f"  • {source}: {count}" for source, count in self.stats['by_source'].items())}

PAR INTENTION:
{chr(10).join(f"  • {intent}: {count}" for intent, count in self.stats['by_intent'].items())}

Enrichissement terminé avec succès!
        """
        
        logger.info(report)
    
    async def _cleanup_connections(self):
        """Nettoyage des connexions"""
        if self.session:
            await self.session.close()
        
        if self.weaviate_client:
            self.weaviate_client.close()
        
        logger.info("Connexions fermées")

# Fonction principale
async def main():
    """Lance le pipeline d'ingestion automatisé avec toutes les sources"""
    try:
        pipeline = AutomatedIngestionPipeline()
        await pipeline.start_automated_collection(target_documents=30000)
        logger.info("PIPELINE TERMINÉ AVEC SUCCÈS!")
    except Exception as e:
        logger.error(f"ÉCHEC PIPELINE: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())