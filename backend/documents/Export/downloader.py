"""
Pipeline de téléchargement de PDFs depuis sources open access
Télécharge les textes intégraux pour enrichissement Weaviate
"""

import asyncio
import aiohttp
import aiofiles
import os
import json
import hashlib
import time
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Set
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse
import logging
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class PDFDocument:
    """Document PDF avec métadonnées"""
    title: str
    authors: List[str]
    abstract: str
    pdf_url: str
    doi: str
    pmcid: str
    source: str
    year: str
    journal: str
    file_path: str = ""
    download_status: str = "pending"
    file_size: int = 0

class PDFDownloader:
    """Téléchargeur de PDFs depuis sources open access"""
    
    def __init__(self, download_dir: str = "./downloaded_pdfs", intents_config_path: str = "intents.json"):
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(exist_ok=True)
        
        # Charger la configuration intents.json pour définir les requêtes
        self.intents_config = self._load_intents_config(intents_config_path)
        
        # Créer sous-dossiers par source
        (self.download_dir / "pmc").mkdir(exist_ok=True)
        (self.download_dir / "arxiv").mkdir(exist_ok=True)
        (self.download_dir / "doaj").mkdir(exist_ok=True)
        (self.download_dir / "hal").mkdir(exist_ok=True)
        
        # Cache de déduplication avancé
        self.downloaded_hashes = self._load_existing_hashes()
        self.downloaded_titles = self._load_existing_titles()
        self.downloaded_dois = self._load_existing_dois()
        
        # Statistiques
        self.stats = {
            "total_found": 0,
            "total_downloaded": 0,
            "duplicates_skipped": 0,
            "by_source": {},
            "errors": 0,
            "start_time": time.time()
        }
        
        # Session HTTP
        self.session = None
    
    def _load_intents_config(self, config_path: str) -> Dict:
        """Charge la configuration intents.json pour définir les requêtes spécialisées"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                logger.info(f"Configuration intents.json chargée: {config.get('version', 'unknown')}")
                return config
        except FileNotFoundError:
            logger.warning(f"Fichier intents.json non trouvé à {config_path}, utilisation requêtes par défaut")
            return {}
        except Exception as e:
            logger.error(f"Erreur chargement intents.json: {e}")
            return {}
    
    def _load_existing_hashes(self) -> Set[str]:
        """Charge les hashes des PDFs existants"""
        hashes = set()
        for metadata_file in self.download_dir.rglob("*_metadata.json"):
            try:
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                    content_hash = self._calculate_content_hash(
                        metadata.get('title', ''),
                        metadata.get('abstract', ''),
                        metadata.get('doi', '')
                    )
                    hashes.add(content_hash)
            except:
                continue
        logger.info(f"Hashes PDFs existants: {len(hashes)}")
        return hashes
    
    def _load_existing_titles(self) -> Set[str]:
        """Charge les titres normalisés des PDFs existants"""
        titles = set()
        for metadata_file in self.download_dir.rglob("*_metadata.json"):
            try:
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                    normalized_title = self._normalize_title(metadata.get('title', ''))
                    if normalized_title:
                        titles.add(normalized_title)
            except:
                continue
        logger.info(f"Titres PDFs existants: {len(titles)}")
        return titles
    
    def _load_existing_dois(self) -> Set[str]:
        """Charge les DOIs des PDFs existants"""
        dois = set()
        for metadata_file in self.download_dir.rglob("*_metadata.json"):
            try:
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                    doi = metadata.get('doi', '').strip()
                    if doi:
                        dois.add(doi.lower())
            except:
                continue
        logger.info(f"DOIs PDFs existants: {len(dois)}")
        return dois
    
    def _calculate_content_hash(self, title: str, abstract: str, doi: str) -> str:
        """Calcule un hash de contenu pour détecter les doublons"""
        content = f"{title.lower().strip()}{abstract.lower().strip()}{doi.lower().strip()}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def _normalize_title(self, title: str) -> str:
        """Normalise un titre pour la détection de doublons"""
        if not title:
            return ""
        # Supprimer ponctuation, espaces multiples, mettre en minuscules
        normalized = re.sub(r'[^\w\s]', '', title.lower())
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        return normalized
    
    def _is_duplicate(self, doc: PDFDocument) -> bool:
        """Vérifie si un document est un doublon"""
        # Vérification par DOI
        if doc.doi and doc.doi.lower() in self.downloaded_dois:
            return True
        
        # Vérification par titre normalisé
        normalized_title = self._normalize_title(doc.title)
        if normalized_title and normalized_title in self.downloaded_titles:
            return True
        
        # Vérification par hash de contenu
        content_hash = self._calculate_content_hash(doc.title, doc.abstract, doc.doi)
        if content_hash in self.downloaded_hashes:
            return True
        
        return False
    
    def _generate_targeted_queries(self) -> List[str]:
        """Génère des requêtes ultra-ciblées basées sur intents.json avec terminologie scientifique"""
        queries = []
        
        if not self.intents_config:
            # Requêtes par défaut si pas d'intents.json
            return [
                "broiler performance feed conversion",
                "layer egg production housing",
                "poultry nutrition requirements",
                "chicken welfare management"
            ]
        
        # Extraire les métriques depuis intents.json
        all_metrics = set()
        for intent_name, intent_config in self.intents_config.get("intents", {}).items():
            metrics = intent_config.get("metrics", {})
            all_metrics.update(metrics.keys())
        
        # Requêtes basées sur types d'oiseaux (scientifiquement correct)
        broiler_queries = [
            "broiler performance growth rate",
            "broiler feed conversion efficiency",
            "broiler body weight development",
            "broiler nutrition amino acids",
            "broiler welfare housing density",
            "broiler meat quality carcass",
            "broiler heat stress management",
            "broiler lighting program welfare",
            "broiler ventilation air quality",
            "broiler slaughter processing"
        ]
        
        layer_queries = [
            "layer hen egg production rate",
            "layer nutrition calcium phosphorus",
            "layer housing enrichment welfare", 
            "layer lighting photoperiod",
            "layer feed intake energy",
            "layer egg quality shell strength",
            "layer bone health osteoporosis",
            "layer feather pecking behavior",
            "layer aviary systems welfare",
            "layer pullet rearing management"
        ]
        
        queries.extend(broiler_queries)
        queries.extend(layer_queries)
        
        # Requêtes basées sur métriques métier (sans noms de lignées)
        priority_metrics = [
            "body_weight_target", "fcr_target", "daily_gain", "uniformity_pct",
            "water_intake_daily", "feed_intake_daily", "egg_production_pct",
            "ambient_temp_target", "lighting_hours", "stocking_density_kgm2"
        ]
        
        for metric in priority_metrics:
            if metric in all_metrics:
                readable_query = self._metric_to_search_query(metric)
                if readable_query:
                    queries.append(readable_query)
        
        # Requêtes par site_type (terminologie scientifique)
        site_queries = [
            "poultry farm management practices",
            "commercial broiler production systems",
            "layer housing welfare standards", 
            "hatchery biosecurity protocols",
            "broiler processing plant hygiene",
            "poultry breeding farm management"
        ]
        queries.extend(site_queries)
        
        # Requêtes par phase d'élevage (sans lignées)
        phase_queries = [
            "broiler starter phase nutrition",
            "broiler grower phase management", 
            "broiler finisher phase performance",
            "layer pullet rearing nutrition",
            "layer production phase feeding",
            "poultry pre-starter feeding program"
        ]
        queries.extend(phase_queries)
        
        # Requêtes spécialisées aviculture
        specialized_queries = [
            "poultry gut microbiome probiotics",
            "avian influenza vaccination protocols",
            "poultry antimicrobial resistance",
            "chicken behavior welfare assessment",
            "poultry precision livestock farming",
            "broiler ascites syndrome prevention",
            "layer keel bone fractures welfare",
            "poultry heat stress mitigation",
            "chicken slaughter stunning welfare",
            "poultry environmental sustainability"
        ]
        queries.extend(specialized_queries)
        
        logger.info(f"Requêtes scientifiques générées: {len(queries)}")
        return queries[:60]  # Limiter pour éviter surcharge
    
    def _metric_to_search_query(self, metric: str) -> str:
        """Convertit une métrique métier en requête de recherche"""
        metric_mapping = {
            "body_weight_target": "broiler body weight target performance",
            "fcr_target": "feed conversion ratio broiler efficiency",
            "daily_gain": "daily weight gain poultry performance",
            "uniformity_pct": "flock uniformity poultry management",
            "water_intake_daily": "water consumption poultry drinking",
            "feed_intake_daily": "feed intake poultry nutrition",
            "egg_production_pct": "egg production rate layer performance",
            "ambient_temp_target": "broiler house temperature management",
            "lighting_hours": "lighting program poultry welfare",
            "stocking_density_kgm2": "stocking density broiler welfare"
        }
        return metric_mapping.get(metric, "")
    
    async def start_download_session(self, target_pdfs: int = 100):
        """Démarre une session de téléchargement"""
        logger.info(f"DÉMARRAGE TÉLÉCHARGEMENT - Objectif: {target_pdfs} PDFs")
        
        try:
            await self._initialize_session()
            
            # Phase 1: PMC Open Access (priorité maximale)
            logger.info("Phase 1: PMC Open Access")
            pmc_docs = await self._collect_pmc_open_access(target_pdfs // 2)
            
            # Phase 2: arXiv 
            logger.info("Phase 2: arXiv")
            arxiv_docs = await self._collect_arxiv_pdfs(target_pdfs // 4)
            
            # Combinaison et téléchargement
            all_docs = pmc_docs + arxiv_docs
            logger.info(f"Total documents trouvés: {len(all_docs)}")
            
            # Téléchargement parallèle
            downloaded_count = await self._download_pdfs_parallel(all_docs[:target_pdfs])
            
            await self._generate_summary_report(downloaded_count)
            
        except Exception as e:
            logger.error(f"Erreur pipeline téléchargement: {e}")
            raise
        finally:
            await self._cleanup_session()
    
    async def _initialize_session(self):
        """Initialise la session HTTP"""
        timeout = aiohttp.ClientTimeout(total=300, connect=30)  # 5 min pour gros PDFs
        self.session = aiohttp.ClientSession(
            timeout=timeout,
            headers={
                "User-Agent": "Academic-Research-Bot/1.0 (mailto:research@intelia.ai)"
            }
        )
        logger.info("Session HTTP initialisée pour téléchargement PDFs")
    
    async def _collect_pmc_open_access(self, target: int) -> List[PDFDocument]:
        """Collecte PMC Open Access avec requêtes ciblées depuis intents.json"""
        docs = []
        
        # Utiliser les requêtes générées depuis intents.json
        targeted_queries = self._generate_targeted_queries()
        
        for query in targeted_queries:
            if len(docs) >= target:
                break
            
            try:
                # Recherche PMC Open Access avec filtres stricts
                search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
                params = {
                    "db": "pmc",
                    "term": f"({query}) AND open access[filter] AND 2015:2025[pdat]",
                    "retmax": min(20, target - len(docs)),
                    "retmode": "json"
                }
                
                async with self.session.get(search_url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        pmcids = data.get("esearchresult", {}).get("idlist", [])
                        
                        if pmcids:
                            batch_docs = await self._process_pmc_batch(pmcids)
                            # Filtrer les doublons
                            new_docs = [doc for doc in batch_docs if not self._is_duplicate(doc)]
                            skipped = len(batch_docs) - len(new_docs)
                            
                            docs.extend(new_docs)
                            if skipped > 0:
                                self.stats["duplicates_skipped"] += skipped
                                logger.info(f"PMC: +{len(new_docs)} nouveaux, {skipped} doublons évités pour '{query[:30]}...'")
                            else:
                                logger.info(f"PMC: +{len(new_docs)} PDFs pour '{query[:30]}...'")
                
                await asyncio.sleep(0.5)  # Rate limiting
                
            except Exception as e:
                logger.warning(f"Erreur requête PMC '{query[:30]}...': {e}")
        
        self.stats["by_source"]["pmc"] = len(docs)
        return docs
    
    async def _process_pmc_batch(self, pmcids: List[str]) -> List[PDFDocument]:
        """Traite un lot de PMCIDs pour récupérer métadonnées et URLs PDF"""
        docs = []
        
        try:
            # Récupération métadonnées
            fetch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
            params = {
                "db": "pmc",
                "id": ",".join(pmcids[:10]),  # Limite par batch
                "retmode": "xml"
            }
            
            async with self.session.get(fetch_url, params=params) as response:
                if response.status == 200:
                    xml_content = await response.text()
                    docs = self._parse_pmc_xml(xml_content)
        
        except Exception as e:
            logger.warning(f"Erreur traitement batch PMC: {e}")
        
        return docs
    
    def _parse_pmc_xml(self, xml_content: str) -> List[PDFDocument]:
        """Parse XML PMC vers documents PDF"""
        docs = []
        
        try:
            root = ET.fromstring(xml_content)
            
            for article in root.findall(".//article"):
                try:
                    # Métadonnées de base
                    title_elem = article.find(".//article-title")
                    title = title_elem.text if title_elem is not None else ""
                    
                    abstract_elem = article.find(".//abstract")
                    abstract = ""
                    if abstract_elem is not None:
                        abstract = " ".join(abstract_elem.itertext())
                    
                    # PMCID
                    pmcid_elem = article.find(".//article-id[@pub-id-type='pmc']")
                    pmcid = pmcid_elem.text if pmcid_elem is not None else ""
                    
                    # DOI
                    doi_elem = article.find(".//article-id[@pub-id-type='doi']")
                    doi = doi_elem.text if doi_elem is not None else ""
                    
                    # Journal et année
                    journal_elem = article.find(".//journal-title")
                    journal = journal_elem.text if journal_elem is not None else ""
                    
                    year_elem = article.find(".//pub-date/year")
                    year = year_elem.text if year_elem is not None else ""
                    
                    # Auteurs
                    authors = []
                    for contrib in article.findall(".//contrib[@contrib-type='author']"):
                        surname = contrib.find(".//surname")
                        given_names = contrib.find(".//given-names")
                        if surname is not None:
                            author = surname.text
                            if given_names is not None:
                                author = f"{given_names.text} {author}"
                            authors.append(author)
                    
                    # Construction URL PDF PMC
                    if pmcid:
                        pdf_url = f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmcid}/pdf/"
                        
                        doc = PDFDocument(
                            title=title,
                            authors=authors,
                            abstract=abstract,
                            pdf_url=pdf_url,
                            doi=doi,
                            pmcid=pmcid,
                            source="pmc",
                            year=year,
                            journal=journal
                        )
                        docs.append(doc)
                
                except Exception:
                    continue
        
        except ET.ParseError as e:
            logger.warning(f"Erreur parsing XML PMC: {e}")
        
        return docs
    
    async def _collect_arxiv_pdfs(self, target: int) -> List[PDFDocument]:
        """Collecte arXiv avec URLs PDF directes"""
        docs = []
        
        arxiv_queries = [
            "precision livestock farming",
            "poultry artificial intelligence", 
            "animal behavior computer vision",
            "livestock monitoring sensors",
            "agricultural automation"
        ]
        
        for query in arxiv_queries:
            if len(docs) >= target:
                break
            
            try:
                arxiv_url = "http://export.arxiv.org/api/query"
                params = {
                    "search_query": f"all:{query}",
                    "start": 0,
                    "max_results": min(20, target - len(docs)),
                    "sortBy": "submittedDate",
                    "sortOrder": "descending"
                }
                
                async with self.session.get(arxiv_url, params=params) as response:
                    if response.status == 200:
                        xml_content = await response.text()
                        batch_docs = self._parse_arxiv_xml(xml_content)
                        docs.extend(batch_docs)
                        logger.info(f"arXiv: +{len(batch_docs)} PDFs pour '{query}'")
                
                await asyncio.sleep(1)  # Rate limiting
                
            except Exception as e:
                logger.warning(f"Erreur requête arXiv '{query}': {e}")
        
        self.stats["by_source"]["arxiv"] = len(docs)
        return docs
    
    def _parse_arxiv_xml(self, xml_content: str) -> List[PDFDocument]:
        """Parse XML arXiv vers documents PDF"""
        docs = []
        
        try:
            root = ET.fromstring(xml_content)
            ns = {"atom": "http://www.w3.org/2005/Atom"}
            
            for entry in root.findall("atom:entry", ns):
                try:
                    title_elem = entry.find("atom:title", ns)
                    title = title_elem.text.strip() if title_elem is not None else ""
                    
                    summary_elem = entry.find("atom:summary", ns)
                    abstract = summary_elem.text.strip() if summary_elem is not None else ""
                    
                    id_elem = entry.find("atom:id", ns)
                    arxiv_id = id_elem.text if id_elem is not None else ""
                    
                    published_elem = entry.find("atom:published", ns)
                    year = published_elem.text[:4] if published_elem is not None else ""
                    
                    # Auteurs
                    authors = []
                    for author in entry.findall("atom:author", ns):
                        name_elem = author.find("atom:name", ns)
                        if name_elem is not None:
                            authors.append(name_elem.text)
                    
                    # URL PDF arXiv
                    if arxiv_id:
                        arxiv_code = arxiv_id.split("/")[-1]
                        pdf_url = f"https://arxiv.org/pdf/{arxiv_code}.pdf"
                        
                        doc = PDFDocument(
                            title=title,
                            authors=authors,
                            abstract=abstract,
                            pdf_url=pdf_url,
                            doi="",
                            pmcid="",
                            source="arxiv",
                            year=year,
                            journal="arXiv preprint"
                        )
                        docs.append(doc)
                
                except Exception:
                    continue
        
        except ET.ParseError as e:
            logger.warning(f"Erreur parsing XML arXiv: {e}")
        
        return docs
    
    async def _download_pdfs_parallel(self, documents: List[PDFDocument]) -> int:
        """Télécharge les PDFs en parallèle"""
        logger.info(f"Téléchargement de {len(documents)} PDFs...")
        
        # Filtrer les documents déjà téléchargés avec détection avancée de doublons
        to_download = []
        duplicates_found = 0
        
        for doc in documents:
            if self._is_duplicate(doc):
                duplicates_found += 1
                logger.info(f"Doublon détecté: {doc.title[:50]}...")
            else:
                to_download.append(doc)
        
        self.stats["duplicates_skipped"] += duplicates_found
        logger.info(f"Documents à télécharger: {len(to_download)}, doublons évités: {duplicates_found}")
        
        # Téléchargement par petits lots pour éviter la surcharge
        downloaded_count = 0
        batch_size = 3  # 3 téléchargements simultanés
        
        for i in range(0, len(to_download), batch_size):
            batch = to_download[i:i + batch_size]
            
            tasks = [self._download_single_pdf(doc) for doc in batch]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, bool) and result:
                    downloaded_count += 1
                elif isinstance(result, Exception):
                    self.stats["errors"] += 1
            
            # Pause entre lots
            if i + batch_size < len(to_download):
                await asyncio.sleep(2)
        
        self.stats["total_downloaded"] = downloaded_count
        return downloaded_count
    
    async def _download_single_pdf(self, doc: PDFDocument) -> bool:
        """Télécharge un PDF unique"""
        try:
            safe_filename = self._make_safe_filename(doc.title, doc.source)
            file_path = self.download_dir / doc.source / f"{safe_filename}.pdf"
            
            logger.info(f"Téléchargement: {doc.title[:50]}...")
            
            async with self.session.get(doc.pdf_url) as response:
                if response.status == 200:
                    content = await response.read()
                    
                    # Vérifier que c'est bien un PDF
                    if content.startswith(b'%PDF'):
                        async with aiofiles.open(file_path, 'wb') as f:
                            await f.write(content)
                        
                        doc.file_path = str(file_path)
                        doc.download_status = "success"
                        doc.file_size = len(content)
                        
                        # Sauvegarder métadonnées JSON
                        await self._save_metadata(doc, safe_filename)
                        
                        logger.info(f"Téléchargé: {safe_filename} ({len(content)} bytes)")
                        return True
                    else:
                        logger.warning(f"Contenu non-PDF reçu pour: {doc.title[:50]}")
                        return False
                else:
                    logger.warning(f"Erreur HTTP {response.status} pour: {doc.title[:50]}")
                    return False
        
        except Exception as e:
            logger.error(f"Erreur téléchargement {doc.title[:50]}: {e}")
            return False
    
    def _make_safe_filename(self, title: str, source: str) -> str:
        """Crée un nom de fichier sécurisé"""
        # Nettoyer le titre
        safe_title = re.sub(r'[^\w\s-]', '', title)
        safe_title = re.sub(r'\s+', '_', safe_title)
        safe_title = safe_title[:100]  # Limiter longueur
        
        # Ajouter hash pour unicité
        title_hash = hashlib.md5(title.encode()).hexdigest()[:8]
        
        return f"{source}_{safe_title}_{title_hash}"
    
    async def _save_metadata(self, doc: PDFDocument, filename: str):
        """Sauvegarde les métadonnées du document"""
        metadata = {
            "title": doc.title,
            "authors": doc.authors,
            "abstract": doc.abstract,
            "pdf_url": doc.pdf_url,
            "doi": doc.doi,
            "pmcid": doc.pmcid,
            "source": doc.source,
            "year": doc.year,
            "journal": doc.journal,
            "file_path": doc.file_path,
            "file_size": doc.file_size,
            "download_timestamp": time.time()
        }
        
        metadata_path = self.download_dir / doc.source / f"{filename}_metadata.json"
        
        async with aiofiles.open(metadata_path, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(metadata, indent=2, ensure_ascii=False))
    
    async def _generate_summary_report(self, downloaded_count: int):
        """Génère le rapport final de téléchargement"""
        duration = time.time() - self.stats["start_time"]
        
        report = f"""
RAPPORT TÉLÉCHARGEMENT PDFs
===========================
Durée: {duration:.0f}s ({duration/60:.1f}min)
PDFs téléchargés: {downloaded_count}
Doublons évités: {self.stats['duplicates_skipped']}
Erreurs: {self.stats['errors']}

PAR SOURCE:
{chr(10).join(f"  • {source}: {count}" for source, count in self.stats['by_source'].items())}

Dossier de téléchargement: {self.download_dir}
Taille moyenne: {self._calculate_average_size()} MB
        """
        
        logger.info(report)
    
    def _calculate_average_size(self) -> float:
        """Calcule la taille moyenne des PDFs téléchargés"""
        total_size = 0
        count = 0
        
        for pdf_file in self.download_dir.rglob("*.pdf"):
            try:
                total_size += pdf_file.stat().st_size
                count += 1
            except:
                continue
        
        return (total_size / count / 1024 / 1024) if count > 0 else 0
    
    async def _cleanup_session(self):
        """Nettoie la session HTTP"""
        if self.session:
            await self.session.close()
        logger.info("Session de téléchargement fermée")

# Fonction principale
async def main():
    """Lance le téléchargeur de PDFs"""
    try:
        downloader = PDFDownloader(download_dir="./downloaded_pdfs")
        await downloader.start_download_session(target_pdfs=50)  # Test avec 50 PDFs
        logger.info("TÉLÉCHARGEMENT TERMINÉ AVEC SUCCÈS!")
    except Exception as e:
        logger.error(f"ÉCHEC TÉLÉCHARGEMENT: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())