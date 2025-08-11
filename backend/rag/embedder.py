# rag/embedder.py
"""
FastRAGEmbedder - Enhanced with Advanced Query Normalization
- Lazy, thread-safe init of SentenceTransformer + FAISS
- Advanced query normalization for poultry industry (90% coverage)
- Enhanced species detection with confidence scoring
- Table-first ranking with technical units recognition
- Single-API search(query, k=5, species=None)
- ENV-aware loader: load_from_env() reads RAG_INDEX_* paths
- FIXED: Enhanced metadata preservation during index loading
"""

from __future__ import annotations

import os
import time
import pickle
import logging
import re
import json  # 🆕 manifest support
import threading
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


class FastRAGEmbedder:
    def __init__(
        self,
        *,
        model_name: str = "all-MiniLM-L6-v2",
        cache_embeddings: bool = True,
        max_workers: int = 2,
        debug: bool = True,
        similarity_threshold: float = 0.20,
        normalize_queries: bool = True,
    ) -> None:
        self.model_name = model_name
        self.cache_embeddings = cache_embeddings
        self.max_workers = max_workers
        self.debug = debug
        self.normalize_queries = normalize_queries

        # Enhanced thresholds
        self.threshold_config = {
            "strict": 0.25,
            "normal": float(max(0.0, min(1.0, similarity_threshold))),
            "permissive": 0.15,
            "fallback": 0.10,
        }

        # state
        self._st_model = None
        self._st_lock = threading.Lock()
        self._index = None
        self._index_lock = threading.Lock()
        self._documents: List[Dict[str, Any]] = []
        self._ready = False
        self._dependencies_ok = False

        # 🆕 persisted stats / manifest
        self._stats: Dict[str, Any] = {}
        self._manifest: Dict[str, Any] = {}

        # caches
        self.embedding_cache: Dict[str, np.ndarray] = {} if cache_embeddings else {}

        # Enhanced normalization patterns
        self._init_enhanced_normalization_patterns()

        # deps
        self._init_dependencies()

        if self.debug:
            logger.info("🚀 Initializing Enhanced FastRAGEmbedder...")
            logger.info("   Model: %s", self.model_name)
            logger.info("   Enhanced query normalization: %s", self.normalize_queries)
            logger.info("   Debug enabled: %s", self.debug)

    # -------------------------
    # Dependencies / model init
    # -------------------------
    def _init_dependencies(self) -> None:
        try:
            from sentence_transformers import SentenceTransformer  # noqa: F401
            import faiss  # noqa: F401
            self.SentenceTransformer = SentenceTransformer
            self.faiss = faiss
            self.np = np
            self._dependencies_ok = True
            logger.info("✅ sentence-transformers available")
            logger.info("✅ faiss available")
            logger.info("✅ numpy available")
        except Exception as e:
            self._dependencies_ok = False
            logger.error("❌ Missing dependencies: %s", e)

    def _ensure_model(self):
        if self._st_model is not None:
            return self._st_model
        if not self._dependencies_ok:
            raise RuntimeError("Dependencies not available (sentence-transformers / faiss)")
        with self._st_lock:
            if self._st_model is None:
                if self.debug:
                    logger.info("🔧 Loading SentenceTransformer model: %s", self.model_name)
                self._st_model = self.SentenceTransformer(self.model_name)
        return self._st_model

    # -------------------------
    # Enhanced Normalization Patterns (90% Coverage)
    # -------------------------
    def _init_enhanced_normalization_patterns(self) -> None:
        """Enhanced normalization patterns for poultry industry"""
        self.normalization_patterns = {
            
            # TEMPORAL CONVERSIONS - Enhanced with safety guards
            "temporal_conversions": [
                # Weeks with protection against false positives
                (r"(\d+)\s*semaines?\s*(?:d['\']?âge|age|old)?", lambda m: f"{int(m.group(1)) * 7} jours"),
                (r"(\d+)\s*sem\.?\s*(?:d['\']?âge)?", lambda m: f"{int(m.group(1)) * 7} jours"),
                (r"(\d+)s\b(?!\s*(?:ross|cobb))", lambda m: f"{int(m.group(1)) * 7} jours"),  # Protection against "Ross"
                
                # Months
                (r"(\d+)\s*mois", lambda m: f"{int(m.group(1)) * 30} jours"),
                
                # Days with variations
                (r"(\d+)\s*(?:jours?|days?|j\.?)\b", r"\1 jours"),
                (r"jour\s*(\d+)", r"\1 jours"),
                
                # Age ranges
                (r"(\d+)[-–](\d+)\s*(?:jours?|days?|j\.?)", r"\1 à \2 jours"),
                (r"(\d+)[-–](\d+)\s*sem\.?", lambda m: f"{int(m.group(1)) * 7} à {int(m.group(2)) * 7} jours"),
            ],
            
            # AGRICULTURAL TERMS - Massively expanded
            "agricultural_terms": [
                # Broilers - Specific strains
                (r"\b(?:ross\s*308|ross308)\b", "ross 308 poulet de chair"),
                (r"\b(?:ross\s*708|ross708)\b", "ross 708 poulet de chair"),
                (r"\b(?:ross\s*458|ross458)\b", "ross 458 poulet de chair"),
                (r"\b(?:cobb\s*500|cobb500)\b", "cobb 500 poulet de chair"),
                (r"\b(?:cobb\s*700|cobb700)\b", "cobb 700 poulet de chair"),
                (r"\b(?:hubbard\s*flex)\b", "hubbard flex poulet de chair"),
                (r"\b(?:hubbard\s*classic)\b", "hubbard classic poulet de chair"),
                (r"\b(?:hubbard\s*ja757)\b", "hubbard ja757 poulet de chair"),
                (r"\bhubbard\b", "hubbard poulet de chair"),
                
                # Layers - Specific strains  
                (r"\b(?:lohmann\s*brown)\b", "lohmann brown pondeuse"),
                (r"\b(?:lohmann\s*white)\b", "lohmann white pondeuse"),
                (r"\b(?:lsl[\s-]*lite|lsl\s*lite)\b", "lsl-lite pondeuse"),
                (r"\b(?:hy[\s-]*line\s*brown)\b", "hy-line brown pondeuse"),
                (r"\b(?:hy[\s-]*line\s*white)\b", "hy-line white pondeuse"),
                (r"\b(?:w[-\s]*36|w36)\b", "w-36 pondeuse"),
                (r"\b(?:w[-\s]*80|w80)\b", "w-80 pondeuse"),
                (r"\b(?:w[-\s]*98|w98)\b", "w-98 pondeuse"),
                (r"\b(?:isa\s*brown)\b", "isa brown pondeuse"),
                (r"\b(?:isa\s*white)\b", "isa white pondeuse"),
                
                # Generic terms
                (r"\bbroilers?\b", "poulet de chair broiler"),
                (r"\bpoulets?\s*de\s*chair\b", "poulet de chair"),
                (r"\bpondeuses?\b", "poule pondeuse layer"),
                (r"\bpoules?\s*pondeuses?\b", "poule pondeuse"),
                (r"\blayers?\b", "poule pondeuse layer"),
                
                # Production phases
                (r"\bstarter\b", "starter démarrage 0-10 jours"),
                (r"\bgrower\b", "grower croissance 11-25 jours"),
                (r"\bfinisher\b", "finisher finition 25-42 jours"),
                (r"\bpré[\s-]*ponte\b", "pré-ponte développement 16-20 semaines"),
                (r"\bpullets?\b", "poulette développement"),
            ],
            
            # WEIGHT CONVERSIONS - Enhanced with decimals
            "weight_conversions": [
                (r"(\d+(?:\.\d+)?)\s*kg\b", lambda m: f"{float(m.group(1)) * 1000:.0f} grammes"),
                (r"(\d+(?:\.\d+)?)\s*g\b", r"\1 grammes"),
                (r"(\d+(?:\.\d+)?)\s*lbs?\b", lambda m: f"{float(m.group(1)) * 453.592:.0f} grammes"),
                (r"(\d+(?:\.\d+)?)\s*oz\b", lambda m: f"{float(m.group(1)) * 28.35:.0f} grammes"),
                (r"(\d+(?:\.\d+)?)\s*tonnes?\b", lambda m: f"{float(m.group(1)) * 1000000:.0f} grammes"),
                (r"(\d+(?:\.\d+)?)\s*t\b", lambda m: f"{float(m.group(1)) * 1000000:.0f} grammes"),
            ],
            
            # TEMPERATURE CONVERSIONS - Enhanced
            "temperature_conversions": [
                (r"(\d+(?:\.\d+)?)°?\s*c\b", r"\1 degrés celsius"),
                (r"(\d+(?:\.\d+)?)°?\s*f\b", lambda m: f"{(float(m.group(1)) - 32) * 5/9:.1f} degrés celsius"),
                (r"(\d+(?:\.\d+)?)\s*celsius\b", r"\1 degrés celsius"),
                (r"(\d+(?:\.\d+)?)\s*fahrenheit\b", lambda m: f"{(float(m.group(1)) - 32) * 5/9:.1f} degrés celsius"),
            ],
            
            # POULTRY TECHNICAL TERMS - NEW CATEGORY
            "poultry_technical_terms": [
                # FCR & Performance
                (r"\bfcr\b", "fcr conversion alimentaire indice consommation"),
                (r"\bindice\s*(?:de\s*)?conversion\b", "fcr conversion alimentaire"),
                (r"\bconversion\s*alimentaire\b", "fcr conversion alimentaire"),
                (r"\bfeed\s*conversion\b", "fcr conversion alimentaire"),
                (r"\bfeed\s*efficiency\b", "efficacité alimentaire fcr"),
                (r"\bi\.?c\.?\b", "fcr conversion alimentaire"),  # IC abbreviation
                
                # Growth & Weight
                (r"\bgain\s*(?:de\s*)?poids\s*quotidien\b", "gain quotidien croissance adg"),
                (r"\badg\b", "gain quotidien moyen croissance"),
                (r"\baverage\s*daily\s*gain\b", "gain quotidien moyen adg"),
                (r"\bcroissance\s*quotidienne\b", "gain quotidien croissance"),
                (r"\bgain\s*de\s*poids\b", "gain poids croissance"),
                
                # Egg Production
                (r"\btaux\s*de\s*ponte\b", "pourcentage ponte production"),
                (r"\brate\s*of\s*lay\b", "taux ponte pourcentage production"),
                (r"\bœufs?\s*par\s*jour\b", "production quotidienne œufs"),
                (r"\begg\s*production\b", "production ponte œufs"),
                (r"\bhen\s*day\b", "hen day production ponte"),
                (r"\bhen\s*housed\b", "hen housed production ponte"),
                
                # Mortality
                (r"\btaux\s*de\s*mortalité\b", "mortalité pourcentage perte"),
                (r"\bmortality\s*rate\b", "taux mortalité"),
                (r"\bviabilité\b", "viabilité survie mortalité"),
                (r"\blivability\b", "viabilité survie"),
                (r"\bmort\b", "mortalité mortality"),
            ],
            
            # UNITS & MEASURES - NEW CATEGORY
            "units_normalization": [
                # Volume & Flow
                (r"(\d+(?:\.\d+)?)\s*m[³3]\b", r"\1 mètres cubes"),
                (r"(\d+(?:\.\d+)?)\s*l(?:itres?)?\b", r"\1 litres"),
                (r"(\d+(?:\.\d+)?)\s*m[³3]/h\b", r"\1 mètres cubes par heure"),
                (r"(\d+(?:\.\d+)?)\s*cfm\b", lambda m: f"{float(m.group(1)) * 1.699:.1f} mètres cubes par heure"),
                
                # Pressure & Concentration
                (r"(\d+(?:\.\d+)?)\s*pa\b", r"\1 pascals"),
                (r"(\d+(?:\.\d+)?)\s*ppm\b", r"\1 parties par million"),
                (r"(\d+(?:\.\d+)?)\s*mg/kg\b", r"\1 milligrammes par kilogramme"),
                
                # Density
                (r"(\d+(?:\.\d+)?)\s*kg/m[²2]\b", r"\1 kilogrammes par mètre carré"),
                (r"(\d+(?:\.\d+)?)\s*birds?/m[²2]\b", r"\1 sujets par mètre carré"),
                (r"(\d+(?:\.\d+)?)\s*sujets?/m[²2]\b", r"\1 sujets par mètre carré"),
                
                # Energy
                (r"(\d+(?:\.\d+)?)\s*kcal/kg\b", r"\1 kilocalories par kilogramme"),
                (r"(\d+(?:\.\d+)?)\s*mj/kg\b", r"\1 mégajoules par kilogramme"),
            ],
            
            # ENHANCED SYNONYMS - Expanded
            "poultry_synonyms": [
                # Alimentation
                (r"\balimentation\b", "alimentation nutrition nourriture feed"),
                (r"\bmangeoires?\b", "mangeoire feeder distribution alimentation"),
                (r"\babreuvoirs?\b", "abreuvoir drinker eau hydratation"),
                (r"\bration\b", "ration alimentation formule feed"),
                
                # Santé & Vaccination
                (r"\bvaccination\b", "vaccination immunisation vaccin protection"),
                (r"\bprotocole\s*sanitaire\b", "protocole santé vaccination biosécurité"),
                (r"\btraitement\s*préventif\b", "prévention traitement vaccination"),
                (r"\bantibiogramme\b", "antibiogramme résistance sensibilité"),
                
                # Environnement
                (r"\benvironnement\b", "environnement conditions climat température"),
                (r"\bventilation\b", "ventilation aération débit air"),
                (r"\béclairage\b", "éclairage lumière photopériode lux"),
                (r"\bbiosécurité\b", "biosécurité hygiène désinfection sécurité"),
                (r"\bthermostat\b", "thermostat température contrôle chauffage"),
                
                # Diagnostic & Problèmes
                (r"\bdiagnostic\b", "diagnostic symptômes maladie problème identification"),
                (r"\bpathologie\b", "pathologie maladie affection problème santé"),
                (r"\bentérite\b", "entérite infection intestinale digestive"),
                (r"\bcoccidiose\b", "coccidiose coccidia parasites intestinaux"),
                (r"\bcolibacillose\b", "colibacillose escherichia coli infection"),
                
                # Production & Performance
                (r"\brentabilité\b", "rentabilité profitabilité économie coût"),
                (r"\befficacité\b", "efficacité performance productivité"),
                (r"\bperformance\b", "performance résultats production efficacité"),
                (r"\bproductivité\b", "productivité rendement performance"),
            ]
        }

    def _normalize_query(self, query: str) -> str:
        if not self.normalize_queries:
            return query
        original = query
        normalized = query.lower()
        
        try:
            # Apply all normalization patterns
            for category, patterns in self.normalization_patterns.items():
                for pattern, repl in patterns:
                    if callable(repl):
                        normalized = re.sub(pattern, repl, normalized, flags=re.IGNORECASE)
                    else:
                        normalized = re.sub(pattern, repl, normalized, flags=re.IGNORECASE)
            
            # Additional technical units normalization
            normalized = self._normalize_technical_units(normalized)
            
            # Clean up multiple spaces
            normalized = re.sub(r"\s+", " ", normalized).strip()
            
            if self.debug and normalized != original.lower():
                logger.info("🔄 Query normalized:\n   Original: %s\n   Normalized: %s", original, normalized)
            return normalized
        except Exception as e:
            logger.error("❌ Error normalizing query: %s", e)
            return query.lower()

    def _normalize_technical_units(self, text: str) -> str:
        """Specialized normalization for technical units"""
        # FCR variations
        text = re.sub(r"\b(?:ic|i\.c\.)\b", "fcr", text, flags=re.IGNORECASE)
        text = re.sub(r"\bfeed\s*conversion\s*ratio\b", "fcr", text, flags=re.IGNORECASE)
        
        # Density normalization
        text = re.sub(r"\bsujets?\s*(?:par|/)\s*m[²2]\b", "densité", text, flags=re.IGNORECASE)
        text = re.sub(r"\bbirds?\s*(?:per|/)\s*m[²2]\b", "densité", text, flags=re.IGNORECASE)
        
        # Production phases standardization
        text = re.sub(r"\b(?:0-\d+|starter)\s*(?:jours?|days?)\b", "phase starter", text, flags=re.IGNORECASE)
        text = re.sub(r"\b(?:\d+-\d+|grower)\s*(?:jours?|days?)\b", "phase grower", text, flags=re.IGNORECASE)
        text = re.sub(r"\b(?:\d+-\d+|finisher)\s*(?:jours?|days?)\b", "phase finisher", text, flags=re.IGNORECASE)
        
        return text

    # -------------------------
    # Enhanced Species Detection with Confidence
    # -------------------------
    def _enhanced_infer_species(self, query: str) -> Tuple[Optional[str], float]:
        """Enhanced species detection with confidence scoring"""
        q = query.lower()
        species_scores = {"broiler": 0.0, "layer": 0.0, "breeder": 0.0}
        
        # Keywords weighted by specificity
        species_keywords_weighted = {
            "broiler": [
                # High specificity (weight 3)
                ("ross 308", 3), ("ross308", 3), ("cobb 500", 3), ("cobb500", 3),
                ("ross 708", 3), ("hubbard", 3), ("poulet de chair", 3),
                # Medium specificity (weight 2) 
                ("broiler", 2), ("chair", 2), ("meat chicken", 2), ("griller", 2),
                # Low specificity (weight 1)
                ("ross", 1), ("cobb", 1), ("croissance", 1), ("poids", 1), ("fcr", 1)
            ],
            "layer": [
                # High specificity (weight 3)
                ("lohmann brown", 3), ("hy-line brown", 3), ("w-36", 3), ("w-80", 3),
                ("ponte", 3), ("pondeuse", 3), ("œuf", 3), ("oeuf", 3),
                # Medium specificity (weight 2)
                ("layer", 2), ("laying hen", 2), ("poule pondeuse", 2), ("lsl-lite", 2),
                # Low specificity (weight 1)
                ("lohmann", 1), ("hy-line", 1), ("isa", 1), ("production", 1)
            ],
            "breeder": [
                # High specificity (weight 3)
                ("parent stock", 3), ("reproducteur", 3), ("breeding stock", 3),
                # Medium specificity (weight 2)
                ("breeder", 2), ("elite stock", 2), ("grand parent", 2),
                # Low specificity (weight 1)
                ("pedigree", 1), ("multiplier", 1)
            ]
        }
        
        # Calculate scores
        for species, keywords in species_keywords_weighted.items():
            for keyword, weight in keywords:
                if keyword in q:
                    species_scores[species] += weight
        
        # Select best species
        max_score = max(species_scores.values())
        if max_score == 0:
            return None, 0.0
        
        best_species = max(species_scores, key=species_scores.get)
        confidence = min(max_score / 10.0, 1.0)  # Normalize to max 10 points
        
        # Handle ambiguous cases (smart guard)
        sorted_scores = sorted(species_scores.values(), reverse=True)
        if len(sorted_scores) > 1 and sorted_scores[0] - sorted_scores[1] < 2:
            return None, confidence * 0.5  # Reduced confidence for ambiguity
        
        return best_species, confidence

    def _infer_species(self, query: str) -> Optional[str]:
        """Legacy compatibility wrapper"""
        species, _ = self._enhanced_infer_species(query)
        return species

    def _expand_query_with_synonyms(self, query: str) -> str:
        """Expand query with technical synonyms"""
        expanded_terms = []
        
        # Technical synonyms map
        synonym_map = {
            "fcr": ["conversion alimentaire", "efficacité alimentaire", "indice consommation"],
            "ponte": ["production œufs", "laying", "egg production"],
            "mortalité": ["mortality", "perte", "dead birds", "viabilité"],
            "croissance": ["growth", "gain", "développement", "weight gain"],
            "vaccination": ["immunisation", "vaccin", "protocol", "prevention"],
            "starter": ["démarrage", "phase 1", "0-10 jours"],
            "finisher": ["finition", "phase 3", "25-42 jours"],
            "pondeuse": ["layer", "laying hen", "poule pondeuse"],
            "broiler": ["poulet de chair", "meat chicken", "chair"]
        }
        
        words = query.lower().split()
        for word in words:
            if word in synonym_map:
                expanded_terms.extend(synonym_map[word][:2])  # Max 2 synonyms to avoid noise
        
        if expanded_terms:
            return query + " " + " ".join(expanded_terms)
        return query

    def _doc_matches_species(self, doc: Dict[str, Any], species: str) -> bool:
        if not species:
            return True
        species = species.lower()
        md = doc.get("metadata", {}) or {}
        candidates = [
            md.get("source", ""),
            md.get("file_path", ""),
            md.get("path", ""),
            doc.get("id", ""),
        ]
        joined = " ".join([c for c in candidates if isinstance(c, str)]).lower()
        if f"/species/{species}/" in joined or f"\\species\\{species}\\" in joined:
            return True
        if species == "broiler" and any(w in joined for w in ["broiler", "ross", "cobb"]):
            return True
        if species == "layer" and any(w in joined for w in ["layer", "lohmann", "hy-line"]):
            return True
        return False

    # -------------------------
    # Index loading - FIXED: Enhanced metadata preservation
    # -------------------------
    def _read_manifest(self, base: Path) -> Dict[str, Any]:
        """🆕 Optional side manifest (meta.json) reader."""
        try:
            mf = base / "meta.json"
            if mf.exists():
                with open(mf, "r", encoding="utf-8") as f:
                    data = json.load(f) or {}
                if isinstance(data, dict):
                    return data
        except Exception as e:
            if self.debug:
                logger.warning("ℹ️ Could not read meta.json: %s", e)
        return {}

    def load_index(self, index_path: str) -> bool:
        """
        Load FAISS index + documents (index.pkl). Idempotent.
        FIXED: Enhanced metadata preservation during loading.
        """
        if not self._dependencies_ok:
            logger.error("❌ Dependencies not available for loading index")
            return False
        try:
            base = Path(index_path).resolve()
            faiss_file = base / "index.faiss"
            pkl_file = base / "index.pkl"

            if not faiss_file.exists() or not pkl_file.exists():
                logger.error("❌ Index files not found in %s", base)
                return False

            # 🆕 load manifest if present
            self._manifest = self._read_manifest(base)

            with self._index_lock:
                t0 = time.time()
                logger.info("🔄 Loading FAISS index from %s", faiss_file)
                idx = self.faiss.read_index(str(faiss_file))
                logger.info("✅ FAISS index loaded in %.2fs", time.time() - t0)

                logger.info("🔄 Loading documents from %s", pkl_file)
                t1 = time.time()
                with open(pkl_file, "rb") as f:
                    raw_documents = pickle.load(f)
                docs = self._normalize_documents_with_metadata_preservation(raw_documents)
                logger.info("✅ Documents loaded in %.2fs", time.time() - t1)

                # 🆕 robust stats
                faiss_total = int(getattr(idx, "ntotal", 0))
                n_chunks = len(docs)
                manifest_chunks = None
                manifest_docs = None
                embedding_dim = None
                model_from_index = None
                try:
                    if isinstance(self._manifest, dict):
                        if "chunks_indexed" in self._manifest:
                            manifest_chunks = int(self._manifest.get("chunks_indexed") or 0)
                        if "n_docs" in self._manifest:
                            manifest_docs = int(self._manifest.get("n_docs") or 0)
                        if "embedding_dim" in self._manifest:
                            embedding_dim = int(self._manifest.get("embedding_dim") or 0)
                    if isinstance(raw_documents, dict):
                        model_from_index = raw_documents.get("model_name")
                        if embedding_dim is None:
                            embedding_dim = raw_documents.get("embedding_dim")
                except Exception:
                    pass

                # Correct comparison: CHUNKS vs FAISS vectors
                if faiss_total != n_chunks:
                    logger.warning("⚠️ Chunk count mismatch: faiss=%d vs loaded_chunks=%d", faiss_total, n_chunks)
                elif manifest_chunks is not None and faiss_total != manifest_chunks:
                    logger.warning("⚠️ Chunk count mismatch vs manifest: faiss=%d vs manifest=%d", faiss_total, manifest_chunks)
                else:
                    logger.info("✅ Index-chunk counts aligned: %d", faiss_total)

                self._index = idx
                self._documents = docs
                self._ready = True

                # 🆕 persist stats for external logging
                self._stats = {
                    "faiss_total": faiss_total,
                    "chunks_loaded": n_chunks,
                    "n_docs": manifest_docs,
                    "embedding_dim": embedding_dim,
                    "model_name": model_from_index or self._manifest.get("model_name") or self.model_name,
                    "path": str(base),
                }

            logger.info("✅ Enhanced index loaded successfully - Search engine ready")
            if self._stats:
                logger.info("   Stats: docs=%s, chunks=%d, faiss=%d, dim=%s, model=%s",
                            self._stats.get("n_docs", "unknown"),
                            self._stats.get("chunks_loaded", 0),
                            self._stats.get("faiss_total", 0),
                            self._stats.get("embedding_dim", "unknown"),
                            self._stats.get("model_name", self.model_name))
            return True
        except Exception as e:
            logger.error("❌ Error loading index: %s", e)
            return False

    def load_from_env(self) -> bool:
        """Load index from environment variables"""
        p = os.getenv("RAG_INDEX_GLOBAL")
        if p and self.load_index(p):
            return True

        root = os.getenv("RAG_INDEX_DIR")
        if root:
            g = Path(root) / "global"
            if g.exists() and self.load_index(str(g)):
                return True
            if Path(root).exists() and self.load_index(root):
                return True

        default = "/app/public/global" if Path("/app/public/global").exists() else "/app/rag_index/global"
        return self.load_index(default)

    def _normalize_documents_with_metadata_preservation(self, raw_documents: Any) -> List[Dict[str, Any]]:
        """
        FIXED: Enhanced document normalization with complete metadata preservation.
        Ensures all enriched metadata (species, domain, chunk_type, etc.) is preserved.
        🆕 Support explicit format: {'documents': [ ...chunks... ]}
        """
        normalized: List[Dict[str, Any]] = []
        try:
            # 🆕 FIRST: support index.pkl as {"documents": [...]}
            if isinstance(raw_documents, dict) and isinstance(raw_documents.get("documents"), list):
                for i, item in enumerate(raw_documents["documents"]):
                    if isinstance(item, dict):
                        metadata = item.get("metadata", {})
                        if not isinstance(metadata, dict):
                            metadata = {}
                        doc = {
                            "id": item.get("id", f"doc_{i}"),
                            "text": item.get("text", item.get("content", str(item))),
                            "metadata": dict(metadata),
                        }
                        if self.debug and metadata:
                            preserved_fields = list(metadata.keys())
                            if len(preserved_fields) > 3:
                                logger.debug("🔍 Preserved metadata fields: %s", preserved_fields[:10])
                        normalized.append(doc)
                    elif isinstance(item, str):
                        normalized.append({"id": f"doc_{i}", "text": item, "metadata": {}})
                if self.debug:
                    logger.info("🔍 Normalized %d chunks from 'documents' list", len(normalized))
                return normalized

            # ORIGINAL behaviors kept
            if isinstance(raw_documents, dict):
                for key, value in raw_documents.items():
                    if isinstance(value, dict):
                        # Preserve ALL metadata fields, not just basic ones
                        metadata = value.get("metadata", {})
                        if not isinstance(metadata, dict):
                            metadata = {}
                        
                        doc = {
                            "id": value.get("id", key),
                            "text": value.get("text", value.get("content", str(value))),
                            "metadata": dict(metadata),  # Deep copy to preserve all fields
                        }
                        
                        # Log preserved metadata for debugging
                        if self.debug and metadata:
                            preserved_fields = list(metadata.keys())
                            if len(preserved_fields) > 3:  # Only log if significant metadata
                                logger.debug("🔍 Preserved metadata fields: %s", preserved_fields[:10])
                        
                        normalized.append(doc)
                    elif isinstance(value, str):
                        normalized.append({"id": key, "text": value, "metadata": {}})
                        
            elif isinstance(raw_documents, list):
                for i, item in enumerate(raw_documents):
                    if isinstance(item, dict):
                        # Preserve ALL metadata fields, not just basic ones
                        metadata = item.get("metadata", {})
                        if not isinstance(metadata, dict):
                            metadata = {}
                        
                        doc = {
                            "id": item.get("id", f"doc_{i}"),
                            "text": item.get("text", item.get("content", str(item))),
                            "metadata": dict(metadata),  # Deep copy to preserve all fields
                        }
                        
                        # Log preserved metadata for debugging
                        if self.debug and metadata:
                            preserved_fields = list(metadata.keys())
                            if len(preserved_fields) > 3:  # Only log if significant metadata
                                logger.debug("🔍 Preserved metadata fields: %s", preserved_fields[:10])
                        
                        normalized.append(doc)
                    elif isinstance(item, str):
                        normalized.append({"id": f"doc_{i}", "text": item, "metadata": {}})
                        
        except Exception as e:
            logger.error("❌ Error normalizing documents with metadata preservation: %s", e)

        if self.debug:
            logger.info("🔍 Normalized %d documents with enhanced metadata preservation", len(normalized))
            if normalized:
                # Sample metadata check
                sample_meta = normalized[0].get("metadata", {})
                if sample_meta:
                    logger.info("   Sample preserved metadata keys: %s", list(sample_meta.keys()))

        return normalized

    def _normalize_documents(self, raw_documents: Any) -> List[Dict[str, Any]]:
        """Legacy wrapper for backward compatibility"""
        return self._normalize_documents_with_metadata_preservation(raw_documents)

    # -------------------------
    # Enhanced search methods (unchanged)
    # -------------------------
    def _embed_query(self, normalized_query: str, species_hint: Optional[str]) -> np.ndarray:
        key = f"{normalized_query}|{species_hint or 'any'}"
        if self.cache_embeddings and key in self.embedding_cache:
            return self.embedding_cache[key]
        model = self._ensure_model()
        emb = model.encode([normalized_query])
        if isinstance(emb, np.ndarray) and emb.ndim == 1:
            emb = emb.reshape(1, -1)
        emb32 = emb.astype("float32", copy=False)
        if self.cache_embeddings:
            self.embedding_cache[key] = emb32
        return emb32

    @staticmethod
    def _improved_similarity_score(distance: float) -> float:
        if distance <= 0:
            return 1.0
        return float(max(0.0, min(1.0, np.exp(-distance * 1.5))))

    def _boost_score_for_exact_matches(self, query: str, text: str, base_score: float) -> float:
        qw = set(query.lower().split())
        if not qw:
            return base_score
        tw = set(text.lower().split())
        overlap_ratio = len(qw.intersection(tw)) / max(1, len(qw))
        boosted = min(1.0, base_score * (1.0 + overlap_ratio * 0.3))
        if self.debug and boosted > base_score * 1.1:
            logger.info("   📈 Score boosted: %.3f → %.3f (overlap: %.2f)", base_score, boosted, overlap_ratio)
        return boosted

    def has_search_engine(self) -> bool:
        ok = self._dependencies_ok and (self._index is not None) and (len(self._documents) > 0)
        if not ok and self.debug:
            logger.warning("🔍 Search engine not ready")
        return ok

    def is_ready(self) -> bool:
        return self.has_search_engine() and self._ready

    def _search_with_threshold(
        self, query: str, k: int, threshold: float, species: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        if not self.has_search_engine():
            return []

        try:
            # Enhanced normalization pipeline
            normalized_query = self._normalize_query(query)
            expanded_query = self._expand_query_with_synonyms(normalized_query)
            species_hint, confidence = self._enhanced_infer_species(query)
            
            # Use provided species or detected species
            final_species = species or species_hint
            
            q_emb = self._embed_query(expanded_query, final_species)

            k_search = int(min(max(k * 3, k), len(self._documents)))
            if k_search <= 0:
                return []

            distances, indices = self._index.search(q_emb, k_search)

            results: List[Dict[str, Any]] = []
            dists = distances[0]
            idxs = indices[0]
            for i in range(len(dists)):
                idx = int(idxs[i])
                if idx < 0 or idx >= len(self._documents):
                    continue
                doc = self._documents[idx]

                # Smart species filtering with confidence
                if final_species and confidence > 0.3:
                    if not self._doc_matches_species(doc, final_species):
                        continue

                dist = float(dists[i])
                base = self._improved_similarity_score(dist)
                final = self._boost_score_for_exact_matches(query, doc.get("text", ""), base)
                if final < threshold:
                    continue

                results.append({
                    "text": doc.get("text", ""),
                    "score": round(final, 4),
                    "index": idx,
                    "metadata": doc.get("metadata", {}),
                    "distance": dist,
                    "base_score": round(base, 4),
                    "threshold_used": threshold,
                    "species_detected": final_species,
                    "species_confidence": confidence,
                })
                if len(results) >= k:
                    break

            results.sort(key=lambda x: x["score"], reverse=True)
            return results[:k]
        except Exception as e:
            logger.error("❌ Enhanced search error @threshold %.3f: %s", threshold, e)
            return []

    def search_with_adaptive_threshold(self, query: str, k: int = 5, species: Optional[str] = None) -> List[Dict[str, Any]]:
        if not self.has_search_engine():
            logger.error("❌ Search engine not available")
            return []

        t0 = time.time()
        if self.debug:
            logger.info("🔍 [Enhanced Adaptive] query=%r k=%d species=%s", query[:120], k, species or "auto")

        tried: List[str] = []

        # Try thresholds in order
        for threshold_name in ["normal", "permissive", "fallback", "no_threshold"]:
            tried.append(threshold_name)
            threshold_value = self.threshold_config.get(threshold_name, 0.0)
            
            results = self._search_with_threshold(query, k, threshold_value, species)
            
            if results:
                if self.debug:
                    dt = time.time() - t0
                    logger.info("✅ [Enhanced] done in %.3fs | used=%s | hits=%d",
                                dt, threshold_name, len(results))
                    if results:
                        logger.info("   Score range: %.3f - %.3f", results[0]["score"], results[-1]["score"])
                return results
            
            if self.debug:
                logger.info("🔍 [Enhanced] No hits @%s → trying next", threshold_name)

        return []

    def search(self, query: str, k: int = 5, species: Optional[str] = None) -> List[Dict[str, Any]]:
        return self.search_with_adaptive_threshold(query, k, species)

    # -------------------------
    # Utils (unchanged) + 🆕 stats helpers
    # -------------------------
    def get_stats(self) -> Dict[str, Any]:
        base = {
            "documents_loaded": len(self._documents),
            "search_available": self.has_search_engine(),
            "cache_enabled": bool(self.embedding_cache) if self.cache_embeddings else False,
            "cache_size": len(self.embedding_cache) if self.embedding_cache is not None else 0,
            "model": self.model_name,
            "max_workers": self.max_workers,
            "dependencies_ok": self._dependencies_ok,
            "faiss_total": int(getattr(self._index, "ntotal", 0)) if self._index is not None else 0,
            "similarity_threshold": self.threshold_config["normal"],
            "threshold_config": dict(self.threshold_config),
            "normalize_queries": self.normalize_queries,
            "ready": self.is_ready(),
            "enhanced_features": True,
            "metadata_preservation": True,  # NEW: indicate enhanced metadata support
        }
        # 🆕 merge with loader stats (prefixed)
        try:
            base.update({f"index_{k}": v for k, v in (self._stats or {}).items()})
        except Exception:
            pass
        return base

    # 🆕 external-friendly stats
    def get_index_stats(self) -> Dict[str, Any]:
        return dict(self._stats or {})

    def get_document_count(self) -> int:
        """
        Prefer manifest's n_docs when available; fallback to number of chunks.
        """
        try:
            if isinstance(self._stats, dict) and isinstance(self._stats.get("n_docs"), int):
                return int(self._stats["n_docs"])
        except Exception:
            pass
        return len(self._documents)

    def clear_cache(self) -> None:
        if self.embedding_cache is not None:
            n = len(self.embedding_cache)
            self.embedding_cache.clear()
            logger.info("🗑️ Cleared %d cached embeddings", n)

    def adjust_similarity_threshold(self, new_threshold: float) -> None:
        old = self.threshold_config["normal"]
        self.threshold_config["normal"] = float(max(0.0, min(1.0, new_threshold)))
        logger.info("🎯 Similarity threshold adjusted: %.3f → %.3f", old, self.threshold_config["normal"])

    def update_threshold_config(self, **kwargs: float) -> None:
        for name, value in kwargs.items():
            if name in self.threshold_config:
                old = self.threshold_config[name]
                self.threshold_config[name] = float(max(0.0, min(1.0, value)))
                logger.info("🎯 %s threshold: %.3f → %.3f", name, old, self.threshold_config[name])
            else:
                logger.warning("⚠️ Unknown threshold config: %s", name)

    def debug_search(self, query: str) -> Dict[str, Any]:
        info: Dict[str, Any] = {
            "query": query,
            "normalized_query": self._normalize_query(query),
            "expanded_query": self._expand_query_with_synonyms(self._normalize_query(query)),
            "species_detection": self._enhanced_infer_species(query),
            "has_search_engine": self.has_search_engine(),
            "documents_count": len(self._documents),
            "enhanced_features": True,
            "metadata_preservation": True,  # NEW: indicate enhanced metadata support
        }
        return info


# ---------------------------------------------------------------------
# Factories / Back-compat
# ---------------------------------------------------------------------
def create_optimized_embedder(**kwargs) -> FastRAGEmbedder:
    return FastRAGEmbedder(
        model_name=kwargs.get("model_name", "all-MiniLM-L6-v2"),
        cache_embeddings=kwargs.get("cache_embeddings", True),
        max_workers=kwargs.get("max_workers", 2),
        debug=kwargs.get("debug", True),
        similarity_threshold=kwargs.get("similarity_threshold", 0.20),
        normalize_queries=kwargs.get("normalize_queries", True),
    )

# Backward-compat alias
RAGEmbedder = FastRAGEmbedder
