"""
Pipeline de production automatisé - Configuration sans comptes
4 sources: PubMed, CrossRef, arXiv, Europe PMC (quotas réduits)
"""

import asyncio
import aiohttp
import time
import json
import logging
import hashlib
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, AsyncGenerator
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
import weaviate

# Configuration logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ingestion.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class ProductionConfig:
    """Configuration optimisée pour déploiement sans comptes"""
    
    # Sources activées (sans FAO AGRIS)
    enabled_sources = ["pubmed", "crossref", "arxiv", "europepmc"]
    
    # Objectifs réalistes sans inscriptions
    target_documents = {
        "pubmed": 12000,      # Articles scientifiques (priorité)
        "crossref": 15000,    # Publications techniques (le plus large)
        "arxiv": 800,         # Recherche émergente (étendu)
        "europepmc": 3000     # Européen (quota réduit sans API key)
    }
    
    # Configuration performance
    batch_size = 30           # Batch plus petit pour stabilité
    max_retries = 3
    timeout_seconds = 15
    
    # Quotas conservateurs sans API keys
    api_quotas = {
        "pubmed": {"rps": 2.5, "burst": 5},        # Légèrement sous 3/sec
        "crossref": {"rps": 45.0, "burst": 50},    # Sous 50/sec par sécurité
        "arxiv": {"rps": 0.25, "burst": 1},        # 1 req/4sec (conservateur)
        "europepmc": {"rps": 8.0, "burst": 10}     # Sans API key: 500/min = 8.3/sec
    }

class IntentsAwareClassifier:
    """Classificateur simplifié pour le déploiement"""
    
    def __init__(self, intents_config: Dict):
        self.intents = intents_config
        self.aliases = intents_config["aliases"]
        self._build_patterns()
    
    def _build_patterns(self):
        """Build detection patterns from intents.json"""
        import re
        
        # Genetic lines patterns
        self.genetic_patterns = {}
        for canonical, aliases in self.aliases["line"].items():
            all_variants = [canonical] + aliases
            pattern = r'\b(?:' + '|'.join(re.escape(v) for v in all_variants) + r')\b'
            self.genetic_patterns[canonical] = re.compile(pattern, re.IGNORECASE)
        
        # Bird types
        self.bird_patterns = {}
        for canonical, aliases in self.aliases["bird_type"].items():
            all_variants = [canonical] + aliases
            pattern = r'\b(?:' + '|'.join(re.escape(v) for v in all_variants) + r')\b'
            self.bird_patterns[canonical] = re.compile(pattern, re.IGNORECASE)
        
        # Phases
        self.phase_patterns = {}
        for canonical, aliases in self.aliases["phase"].items():
            all_variants = [canonical] + aliases
            pattern = r'\b(?:' + '|'.join(re.escape(v) for v in all_variants) + r')\b'
            self.phase_patterns[canonical] = re.compile(pattern, re.IGNORECASE)
    
    def classify_document(self, title: str, content: str, source: str) -> Dict:
        """Classify document according to intents structure"""
        
        text = f"{title} {content}".lower()
        
        # Detect genetic line
        genetic_line = None
        genetic_confidence = 0.0
        for canonical, pattern in self.genetic_patterns.items():
            if pattern.search(text):
                genetic_line = canonical
                genetic_confidence = 0.8
                break
        
        # Detect bird type
        bird_type = None
        for canonical, pattern in self.bird_patterns.items():
            if pattern.search(text):
                bird_type = canonical
                break
        
        # Detect phase
        phase = None
        for canonical, pattern in self.phase_patterns.items():
            if pattern.search(text):
                phase = canonical
                break
        
        # Extract age
        age_days, age_weeks = self._extract_age(text)
        
        # Determine intent
        intent_type = self._determine_intent(text)
        
        # Determine site type using defaults
        site_type = self._determine_site_type(text)
        
        return {
            "line": genetic_line,
            "bird_type": bird_type,
            "phase": phase,
            "age_days": age_days,
            "age_weeks": age_weeks,
            "intent_type": intent_type,
            "site_type": site_type,
            "confidence": genetic_confidence + (0.2 if bird_type else 0) + (0.1 if phase else 0),
            "source": source
        }
    
    def _extract_age(self, text: str):
        """Extract age in days/weeks"""
        import re
        
        # Days
        days_match = re.search(r'\b(\d{1,3})\s*(?:days?|jours?|d)\b', text)
        age_days = int(days_match.group(1)) if days_match and 0 <= int(days_match.group(1)) <= 120 else None
        
        # Weeks  
        weeks_match = re.search(r'\b(\d{1,3})\s*(?:weeks?|semaines?|w)\b', text)
        age_weeks = int(weeks_match.group(1)) if weeks_match and 0 <= int(weeks_match.group(1)) <= 600 else None
        
        return age_days, age_weeks
    
    def _determine_intent(self, text: str) -> str:
        """Determine intent from content"""
        
        # Metric keywords
        if any(word in text for word in ['fcr', 'weight', 'gain', 'performance', 'intake']):
            return 'metric_query'
        
        # Environment keywords
        elif any(word in text for word in ['temperature', 'ventilation', 'lighting', 'housing']):
            return 'environment_setting'
        
        # Protocol keywords
        elif any(word in text for word in ['vaccination', 'protocol', 'biosecurity', 'treatment']):
            return 'protocol_query'
        
        # Diagnosis keywords
        elif any(word in text for word in ['disease', 'mortality', 'symptoms', 'diagnosis']):
            return 'diagnosis_triage'
        
        # Economics keywords
        elif any(word in text for word in ['cost', 'economic', 'price', 'profit']):
            return 'economics_cost'
        
        else:
            return 'metric_query'  # Default to most common
    
    def _determine_site_type(self, text: str) -> str:
        """Determine site type with defaults"""
        
        defaults = self.intents.get("defaults_by_topic", {})
        
        # Check content for topic hints
        if any(word in text for word in ['performance', 'weight', 'growth']):
            return defaults.get('performance', 'broiler_farm')
        elif any(word in text for word in ['temperature', 'ventilation']):
            return defaults.get('temperature', 'broiler_farm')
        elif any(word in text for word in ['feed', 'nutrition']):
            return defaults.get('feed', 'feed_mill')
        elif any(word in text for word in ['vaccination', 'hatch']):
            return defaults.get('vaccination', 'hatchery')
        elif any(word in text for word in ['egg', 'laying']):
            return 'layer_farm'
        else:
            return 'broiler_farm'  # Default

class ProductionPipeline:
    """Pipeline de production optimisé sans comptes"""
    
    def __init__(self, weaviate_url: str, intents_config_path: str):
        self.config = ProductionConfig()
        self.weaviate_url = weaviate_url
        
        # Load intents config
        with open(intents_config_path, 'r', encoding='utf-8') as f:
            self.intents_config = json.load(f)
        
        self.classifier = IntentsAwareClassifier(self.intents_config)
        
        # Statistics
        self.stats = {
            "total_collected": 0,
            "total_uploaded": 0,
            "by_source": {source: 0 for source in self.config.enabled_sources},
            "by_intent": {},
            "errors": [],
            "start_time": time.time()
        }
        
        # Batch management
        self.current_batch = []
        
        # Rate limiting tracking
        self.last_request_times = {source: 0 for source in self.config.enabled_sources}
    
    async def start_collection(self):
        """Start the complete collection process"""
        
        logger.info("🚀 Démarrage pipeline de production")
        logger.info(f"📊 Objectif: {sum(self.config.target_documents.values())} documents")
        logger.info(f"📡 Sources: {', '.join(self.config.enabled_sources)}")
        
        # Setup HTTP session
        timeout = aiohttp.ClientTimeout(total=self.config.timeout_seconds)
        connector = aiohttp.TCPConnector(limit=10, limit_per_host=5)
        
        async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
            self.session = session
            
            # Setup Weaviate connection
            self.weaviate_client = weaviate.connect_to_url(self.weaviate_url)
            
            try:
                # Run collection tasks in parallel
                tasks = []
                
                # Start monitoring task
                monitor_task = asyncio.create_task(self._monitor_progress())
                tasks.append(monitor_task)
                
                # Start collection tasks
                for source in self.config.enabled_sources:
                    target = self.config.target_documents[source]
                    task = asyncio.create_task(self._collect_source(source, target))
                    tasks.append(task)
                
                # Wait for all tasks
                await asyncio.gather(*tasks, return_exceptions=True)
                
                # Upload final batch
                if self.current_batch:
                    await self._upload_batch()
                
                # Final report
                self._print_final_report()
                
            finally:
                if hasattr(self, 'weaviate_client'):
                    self.weaviate_client.close()
    
    async def _collect_source(self, source: str, target: int):
        """Collect from a specific source"""
        
        logger.info(f"📡 Début collecte {source} - Objectif: {target}")
        
        try:
            if source == "pubmed":
                await self._collect_pubmed(target)
            elif source == "crossref":
                await self._collect_crossref(target)
            elif source == "arxiv":
                await self._collect_arxiv(target)
            elif source == "europepmc":
                await self._collect_europepmc(target)
            
            logger.info(f"✅ Collecte {source} terminée")
            
        except Exception as e:
            logger.error(f"❌ Erreur collecte {source}: {e}")
            self.stats["errors"].append(f"{source}: {e}")
    
    async def _collect_pubmed(self, target: int):
        """Collect from PubMed with optimized queries"""
        
        # Optimized queries focusing on your intents
        queries = [
            # Performance metrics (metric_query)
            "Ross 308 broiler performance 2020:2025[dp]",
            "Cobb 500 FCR feed conversion 2020:2025[dp]", 
            "broiler body weight gain 2020:2025[dp]",
            "poultry production index EPEF 2020:2025[dp]",
            
            # Layer performance
            "ISA Brown layer production 2020:2025[dp]",
            "Lohmann Brown egg production 2020:2025[dp]",
            "layer feed intake efficiency 2020:2025[dp]",
            
            # Environment (environment_setting)
            "broiler housing temperature optimal 2020:2025[dp]",
            "poultry ventilation system design 2020:2025[dp]",
            "LED lighting broiler layer 2020:2025[dp]",
            
            # Nutrition metrics
            "broiler amino acid requirements 2020:2025[dp]",
            "poultry metabolizable energy 2020:2025[dp]",
            "layer calcium phosphorus nutrition 2020:2025[dp]",
            
            # Water and welfare
            "broiler water intake daily 2020:2025[dp]",
            "poultry stocking density welfare 2020:2025[dp]",
            
            # Protocols
            "poultry vaccination schedule 2020:2025[dp]",
            "broiler biosecurity measures 2020:2025[dp]"
        ]
        
        collected = 0
        for query in queries:
            if collected >= target:
                break
                
            query_collected = 0
            async for doc in self._pubmed_search_generator(query, max_per_query=1000):
                if collected >= target or query_collected >= 1000:
                    break
                    
                await self._process_and_batch_document(doc, "pubmed")
                collected += 1
                query_collected += 1
                
                # Rate limiting
                await self._wait_for_rate_limit("pubmed")
    
    async def _pubmed_search_generator(self, query: str, max_per_query: int = 1000):
        """Generator for PubMed documents with pagination"""
        
        retstart = 0
        retmax = 50  # Smaller batches for stability
        
        while retstart < max_per_query:
            try:
                # Search for IDs
                search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
                search_params = {
                    "db": "pubmed",
                    "term": query,
                    "retstart": retstart,
                    "retmax": retmax,
                    "retmode": "json"
                }
                
                async with self.session.get(search_url, params=search_params) as response:
                    if response.status != 200:
                        logger.warning(f"PubMed search failed: {response.status}")
                        break
                    
                    data = await response.json()
                    pmids = data.get("esearchresult", {}).get("idlist", [])
                    
                    if not pmids:
                        break
                
                # Wait before next request
                await self._wait_for_rate_limit("pubmed")
                
                # Fetch details
                fetch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
                fetch_params = {
                    "db": "pubmed",
                    "id": ",".join(pmids),
                    "retmode": "xml"
                }
                
                async with self.session.get(fetch_url, params=fetch_params) as response:
                    if response.status == 200:
                        xml_content = await response.text()
                        documents = self._parse_pubmed_xml(xml_content)
                        
                        for doc in documents:
                            if self._is_poultry_relevant(doc["content"]):
                                yield doc
                
                retstart += retmax
                
            except Exception as e:
                logger.warning(f"PubMed pagination error: {e}")
                break
    
    def _parse_pubmed_xml(self, xml_content: str) -> List[Dict]:
        """Parse PubMed XML response"""
        documents = []
        
        try:
            root = ET.fromstring(xml_content)
            
            for article in root.findall(".//PubmedArticle"):
                try:
                    # Extract title
                    title_elem = article.find(".//ArticleTitle")
                    title = title_elem.text if title_elem is not None else ""
                    
                    # Extract abstract
                    abstract_elem = article.find(".//Abstract/AbstractText")
                    abstract = abstract_elem.text if abstract_elem is not None else ""
                    
                    # PMID
                    pmid_elem = article.find(".//PMID")
                    pmid = pmid_elem.text if pmid_elem is not None else ""
                    
                    # Year
                    year_elem = article.find(".//PubDate/Year")
                    year = year_elem.text if year_elem is not None else "2020"
                    
                    if title and abstract:  # Only include if we have both
                        documents.append({
                            "title": title,
                            "content": f"{title}\n\n{abstract}",
                            "source_url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                            "publication_year": year,
                            "source": "pubmed"
                        })
                
                except Exception as e:
                    continue  # Skip problematic articles
        
        except ET.ParseError:
            logger.warning("XML parsing error in PubMed response")
        
        return documents
    
    async def _collect_crossref(self, target: int):
        """Collect from CrossRef"""
        
        queries = [
            "poultry genetics broiler performance",
            "chicken breeding commercial lines",
            "layer production efficiency",
            "broiler nutrition optimization",
            "poultry housing management",
            "avian disease control",
            "feed conversion ratio poultry",
            "egg production quality"
        ]
        
        collected = 0
        for query in queries:
            if collected >= target:
                break
            
            query_collected = 0
            async for doc in self._crossref_search_generator(query, max_per_query=2500):
                if collected >= target or query_collected >= 2500:
                    break
                
                if self._is_poultry_relevant(doc["content"]):
                    await self._process_and_batch_document(doc, "crossref")
                    collected += 1
                    query_collected += 1
                
                await self._wait_for_rate_limit("crossref")
    
    async def _crossref_search_generator(self, query: str, max_per_query: int = 2500):
        """Generator for CrossRef documents"""
        
        offset = 0
        rows = 100
        
        while offset < max_per_query:
            try:
                url = "https://api.crossref.org/works"
                params = {
                    "query.bibliographic": query,
                    "filter": "from-pub-date:2020-01-01,until-pub-date:2025-12-31",
                    "offset": offset,
                    "rows": rows
                }
                
                async with self.session.get(url, params=params) as response:
                    if response.status != 200:
                        break
                    
                    data = await response.json()
                    items = data.get("message", {}).get("items", [])
                    
                    if not items:
                        break
                    
                    for item in items:
                        title = item.get("title", [""])[0] if item.get("title") else ""
                        abstract = item.get("abstract", "")
                        doi = item.get("DOI", "")
                        
                        if title:
                            yield {
                                "title": title,
                                "content": f"{title}\n\n{abstract}",
                                "source_url": f"https://doi.org/{doi}",
                                "publication_year": self._extract_crossref_year(item),
                                "source": "crossref"
                            }
                
                offset += rows
                
            except Exception as e:
                logger.warning(f"CrossRef error: {e}")
                break
    
    async def _collect_arxiv(self, target: int):
        """Collect from arXiv"""
        
        queries = [
            "poultry AND (optimization OR machine learning)",
            "chicken AND (genetics OR breeding)",
            "broiler AND (performance OR efficiency)", 
            "layer AND (production OR management)",
            "avian AND (nutrition OR welfare)"
        ]
        
        collected = 0
        for query in queries:
            if collected >= target:
                break
            
            async for doc in self._arxiv_search_generator(query, max_per_query=200):
                if collected >= target:
                    break
                
                if self._is_poultry_relevant(doc["content"]):
                    await self._process_and_batch_document(doc, "arxiv")
                    collected += 1
                
                await self._wait_for_rate_limit("arxiv")
    
    async def _arxiv_search_generator(self, query: str, max_per_query: int = 200):
        """Generator for arXiv documents"""
        
        start = 0
        max_results = 50
        
        while start < max_per_query:
            try:
                url = "http://export.arxiv.org/api/query"
                params = {
                    "search_query": query,
                    "start": start,
                    "max_results": max_results,
                    "submittedDate": "[20200101 TO 20251231]"
                }
                
                async with self.session.get(url, params=params) as response:
                    if response.status != 200:
                        break
                    
                    xml_content = await response.text()
                    documents = self._parse_arxiv_xml(xml_content)
                    
                    if not documents:
                        break
                    
                    for doc in documents:
                        yield doc
                
                start += max_results
                
            except Exception as e:
                logger.warning(f"arXiv error: {e}")
                break
    
    def _parse_arxiv_xml(self, xml_content: str) -> List[Dict]:
        """Parse arXiv XML response"""
        documents = []
        
        try:
            # arXiv uses Atom namespace
            root = ET.fromstring(xml_content)
            ns = {'atom': 'http://www.w3.org/2005/Atom'}
            
            for entry in root.findall('atom:entry', ns):
                try:
                    title_elem = entry.find('atom:title', ns)
                    title = title_elem.text if title_elem is not None else ""
                    
                    summary_elem = entry.find('atom:summary', ns)
                    summary = summary_elem.text if summary_elem is not None else ""
                    
                    id_elem = entry.find('atom:id', ns)
                    arxiv_id = id_elem.text if id_elem is not None else ""
                    
                    if title and summary:
                        documents.append({
                            "title": title.strip(),
                            "content": f"{title.strip()}\n\n{summary.strip()}",
                            "source_url": arxiv_id,
                            "publication_year": "2020",  # Default for arXiv
                            "source": "arxiv"
                        })
                
                except Exception:
                    continue
        
        except ET.ParseError:
            logger.warning("XML parsing error in arXiv response")
        
        return documents
    
    async def _collect_europepmc(self, target: int):
        """Collect from Europe PMC (without API key)"""
        
        queries = [
            "poultry genetics performance",
            "broiler management efficiency", 
            "layer production optimization",
            "chicken welfare housing",
            "avian nutrition requirements"
        ]
        
        collected = 0
        for query in queries:
            if collected >= target:
                break
            
            async for doc in self._europepmc_search_generator(query, max_per_query=800):
                if collected >= target:
                    break
                
                if self._is_poultry_relevant(doc["content"]):
                    await self._process_and_batch_document(doc, "europepmc")
                    collected += 1
                
                await self._wait_for_rate_limit("europepmc")
    
    async def _europepmc_search_generator(self, query: str, max_per_query: int = 800):
        """Generator for Europe PMC documents"""
        
        page = 1
        page_size = 50
        
        while (page - 1) * page_size < max_per_query:
            try:
                url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
                params = {
                    "query": f"{query} PUB_YEAR:[2020 TO 2025]",
                    "format": "json",
                    "pageSize": page_size,
                    "page": page
                }
                
                async with self.session.get(url, params=params) as response:
                    if response.status != 200:
                        break
                    
                    data = await response.json()
                    results = data.get("resultList", {}).get("result", [])
                    
                    if not results:
                        break
                    
                    for item in results:
                        title = item.get("title", "")
                        abstract = item.get("abstractText", "")
                        pmid = item.get("pmid", "")
                        
                        if title and abstract:
                            yield {
                                "title": title,
                                "content": f"{title}\n\n{abstract}",
                                "source_url": f"https://europepmc.org/article/MED/{pmid}",
                                "publication_year": str(item.get("pubYear", "2020")),
                                "source": "europepmc"
                            }
                
                page += 1
                
            except Exception as e:
                logger.warning(f"Europe PMC error: {e}")
                break
    
    def _is_poultry_relevant(self, content: str) -> bool:
        """Check if content is poultry-related"""
        
        content_lower = content.lower()
        poultry_keywords = [
            "poultry", "chicken", "broiler", "layer", "hen", "rooster",
            "ross", "cobb", "hubbard", "isa", "lohmann", "avian",
            "egg", "fcr", "feed conversion"
        ]
        
        return any(keyword in content_lower for keyword in poultry_keywords)
    
    def _extract_crossref_year(self, item: Dict) -> str:
        """Extract publication year from CrossRef item"""
        try:
            date_parts = item.get("published-print", {}).get("date-parts", [[]])[0]
            if not date_parts:
                date_parts = item.get("published-online", {}).get("date-parts", [[]])[0]
            return str(date_parts[0]) if date_parts else "2020"
        except:
            return "2020"
    
    async def _process_and_batch_document(self, document: Dict, source: str):
        """Process document and add to batch"""
        
        try:
            # Classify document
            classification = self.classifier.classify_document(
                document["title"],
                document["content"], 
                source
            )
            
            # Only proceed if minimum confidence
            if classification["confidence"] >= 0.2:
                
                # Create Weaviate document
                weaviate_doc = {
                    "content": document["content"],
                    "title": document["title"],
                    "source": document["source_url"],
                    
                    # Your schema fields
                    "geneticLine": classification["line"] or "",
                    "species": classification["bird_type"] or "",
                    "phase": classification["phase"] or "",
                    "age_band": self._convert_age_to_band(classification["age_days"], classification["age_weeks"]),
                    "site_type": classification["site_type"] or "",
                    
                    # Additional metadata
                    "intent_type": classification["intent_type"],
                    "publication_year": document.get("publication_year", ""),
                    "ingestion_source": source,
                    "classification_confidence": classification["confidence"],
                    "ingestion_date": datetime.now().isoformat()
                }
                
                # Add to batch
                self.current_batch.append(weaviate_doc)
                
                # Upload if batch is full
                if len(self.current_batch) >= self.config.batch_size:
                    await self._upload_batch()
                
                # Update stats
                self.stats["total_collected"] += 1
                self.stats["by_source"][source] += 1
                
                intent = classification["intent_type"]
                self.stats["by_intent"][intent] = self.stats["by_intent"].get(intent, 0) + 1
        
        except Exception as e:
            logger.warning(f"Document processing error: {e}")
    
    def _convert_age_to_band(self, age_days: Optional[int], age_weeks: Optional[int]) -> str:
        """Convert age to band format"""
        
        if age_days:
            if 0 <= age_days <= 7:
                return "0-7"
            elif 8 <= age_days <= 21:
                return "8-21"
            elif 22 <= age_days <= 35:
                return "22-35"
            elif 36 <= age_days <= 42:
                return "36-42"
        
        return ""
    
    async def _upload_batch(self):
        """Upload current batch to Weaviate"""
        
        if not self.current_batch:
            return
        
        try:
            collection = self.weaviate_client.collections.get("InteliaKnowledge")
            
            # Upload with error handling
            for doc in self.current_batch:
                try:
                    collection.data.insert(doc)
                    self.stats["total_uploaded"] += 1
                except Exception as e:
                    logger.warning(f"Failed to upload document: {e}")
                    self.stats["errors"].append(f"Upload: {e}")
            
            logger.info(f"✅ Uploaded batch: {len(self.current_batch)} documents")
            
            # Clear batch
            self.current_batch = []
            
        except Exception as e:
            logger.error(f"❌ Batch upload failed: {e}")
            self.stats["errors"].append(f"Batch upload: {e}")
    
    async def _wait_for_rate_limit(self, source: str):
        """Wait to respect rate limits"""
        
        quota = self.config.api_quotas[source]
        current_time = time.time()
        time_since_last = current_time - self.last_request_times[source]
        
        min_interval = 1.0 / quota["rps"]
        
        if time_since_last < min_interval:
            sleep_time = min_interval - time_since_last
            await asyncio.sleep(sleep_time)
        
        self.last_request_times[source] = time.time()
    
    async def _monitor_progress(self):
        """Monitor progress and log stats"""
        
        while True:
            await asyncio.sleep(60)  # Log every minute
            
            elapsed = time.time() - self.stats["start_time"]
            rate = self.stats["total_collected"] / elapsed * 3600 if elapsed > 0 else 0
            
            logger.info(f"📊 Progress: {self.stats['total_collected']} collected, "
                       f"{self.stats['total_uploaded']} uploaded, "
                       f"{rate:.0f} docs/h")
            
            # Log by source
            source_info = ", ".join([f"{src}: {count}" 
                                   for src, count in self.stats["by_source"].items() 
                                   if count > 0])
            if source_info:
                logger.info(f"📡 By source: {source_info}")
    
    def _print_final_report(self):
        """Print final collection report"""
        
        elapsed = time.time() - self.stats["start_time"]
        
        print("=" * 60)
        print("🎉 COLLECTE TERMINÉE - RAPPORT FINAL")
        print("=" * 60)
        print(f"📊 Documents collectés: {self.stats['total_collected']}")
        print(f"📤 Documents uploadés: {self.stats['total_uploaded']}")
        print(f"⏱️ Durée totale: {elapsed/3600:.1f} heures")
        print(f"⚡ Taux moyen: {self.stats['total_collected']/elapsed*3600:.0f} docs/h")
        
        print("\n📡 Répartition par source:")
        for source, count in self.stats["by_source"].items():
            if count > 0:
                pct = count / self.stats["total_collected"] * 100
                print(f"  {source}: {count} ({pct:.1f}%)")
        
        print("\n🎯 Répartition par intent:")
        for intent, count in self.stats["by_intent"].items():
            pct = count / self.stats["total_collected"] * 100
            print(f"  {intent}: {count} ({pct:.1f}%)")
        
        if self.stats["errors"]:
            print(f"\n⚠️ Erreurs: {len(self.stats['errors'])}")
        
        print("=" * 60)

# Main execution function
async def main():
    """Main execution function"""
    
    # Configuration
    WEAVIATE_URL = input("Entrez votre URL Weaviate: ").strip()
    INTENTS_CONFIG_PATH = "intents.json"
    
    # Verify intents.json exists
    if not Path(INTENTS_CONFIG_PATH).exists():
        print(f"❌ Fichier {INTENTS_CONFIG_PATH} introuvable")
        return
    
    print("🚀 Démarrage du pipeline de production")
    print("📊 Configuration: 4 sources sans inscription")
    print("🎯 Objectif: ~30,800 documents")
    print("-" * 40)
    
    # Create and run pipeline
    pipeline = ProductionPipeline(WEAVIATE_URL, INTENTS_CONFIG_PATH)
    await pipeline.start_collection()

if __name__ == "__main__":
    asyncio.run(main())