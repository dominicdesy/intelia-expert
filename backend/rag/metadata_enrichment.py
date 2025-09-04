# rag/metadata_enrichment.py
import re
import os
from typing import Dict, Optional, Tuple, List
from rag.metadata_schema import ChunkMeta

# ===============================
# MOTS-CLÉS ÉTENDUS (95% Coverage Target)
# ===============================

ENHANCED_SPECIES_KEYWORDS = {
    "broiler": [
        # Souches principales Ross
        "ross", "ross 308", "ross308", "ross 708", "ross708", "ross 458", 
        "ross 458/708", "ross ap95", "ross pm3",
        
        # Souches Cobb
        "cobb", "cobb 500", "cobb500", "cobb 700", "cobb700", "cobb avian48",
        "cobb mx", "cobb sasso",
        
        # Autres souches
        "hubbard", "hubbard flex", "hubbard classic", "hubbard jv",
        "peterson", "arbor acres", "aa plus", "aa+",
        
        # Termes génériques
        "broiler", "poulet de chair", "chair", "meat chicken",
        "griller", "fryer", "fast growing", "slow growing",
        "standard broiler", "alternative broiler", "label rouge"
    ],
    
    "layer": [
        # Hy-Line
        "layer", "pondeuse", "egg layer", "laying hen", "poule pondeuse",
        "hy-line", "hyline", "hy line", "hy-line brown", "hy-line white",
        "hy-line w36", "hy-line w80", "hy-line w98", "hy-line soto",
        "w-36", "w36", "w-80", "w80", "w-98", "w98", "w-77", "w77",
        
        # Lohmann
        "lohmann", "lohmann brown", "lohmann white", "lohmann lsl", 
        "lsl-lite", "lsl classic", "lohmann tradition", "lohmann sandy",
        
        # ISA et autres
        "isa", "isa brown", "isa white", "bovans", "bovans brown", "bovans white",
        "shaver", "tetra", "hisex", "babcock", "dekalb", "hendrix"
    ],
    
    "breeder": [
        "breeder", "reproducteur", "parent stock", "ps", "elite stock",
        "breeding stock", "pedigree", "pure line", "grand parent",
        "great grand parent", "ggp", "gp", "multiplier"
    ],
    
    "duck": [
        "duck", "canard", "peking duck", "muscovy", "mulard", "cherry valley"
    ],
    
    "turkey": [
        "turkey", "dinde", "but", "hybrid", "nicholas", "broad breasted"
    ]
}

# Patterns regex pour détection de souches spécifiques
STRAIN_PATTERNS = {
    r"ross\s*(\d+)": "Ross {strain}",
    r"cobb\s*(\d+)": "Cobb {strain}",
    r"w[-\s]*(\d+)": "W-{strain}",
    r"lohmann\s+(brown|white|lsl|sandy|tradition)": "Lohmann {strain}",
    r"hy[-\s]*line\s+(brown|white|w\d+)": "Hy-Line {strain}",
    r"isa\s+(brown|white)": "ISA {strain}",
    r"bovans\s+(brown|white)": "Bovans {strain}"
}

# 🆕 DÉTECTION SEXE AMÉLIORÉE
SEX_KEYWORDS = {
    "male": [
        "male", "mâle", "males", "mâles", "cock", "coq", "cockerel",
        "rooster", "male birds", "male chicken", "masculine"
    ],
    "female": [
        "female", "femelle", "females", "femelles", "hen", "poule", 
        "pullet", "poulette", "female birds", "female chicken", "feminine"
    ],
    "mixed": [
        "mixed", "mixte", "both sexes", "straight run", "unsexed",
        "as hatched", "mixed sex", "both male and female"
    ]
}

# 🆕 DÉTECTION LINE/LIGNÉE AVANCÉE
LINE_DETECTION_PATTERNS = {
    # Ross patterns
    r"ross\s*(308|708|458|ap95|pm3)": "Ross {0}",
    
    # Cobb patterns  
    r"cobb\s*(500|700|mx|avian48|sasso)": "Cobb {0}",
    
    # Lohmann patterns
    r"lohmann\s*(brown|white|lsl|tradition|sandy)": "Lohmann {0}",
    
    # Hy-Line patterns
    r"hy[-\s]*line\s*(brown|white|w-?36|w-?80|w-?98|soto)": "Hy-Line {0}",
    
    # ISA patterns
    r"isa\s*(brown|white)": "ISA {0}",
    
    # Bovans patterns
    r"bovans\s*(brown|white)": "Bovans {0}",
    
    # Hubbard patterns
    r"hubbard\s*(flex|classic|jv|f15)": "Hubbard {0}",
}

PRODUCTION_PHASE_KEYWORDS = {
    "starter": [
        "starter", "démarrage", "start", "0-10", "0-21", "day-old", 
        "chick", "poussin", "chick starter", "pre-starter"
    ],
    "grower": [
        "grower", "croissance", "growing", "development", "10-25", 
        "11-25", "21-35", "grower feed", "développement"
    ],
    "finisher": [
        "finisher", "finition", "finishing", "25-42", "35-42", 
        "final", "finisher feed", "withdrawal"
    ],
    "pre_lay": [
        "pre-lay", "pré-ponte", "pullet", "poulette", "16-20", 
        "développement", "pre-production", "developer"
    ],
    "layer_phase1": [
        "peak", "pic", "ponte", "laying", "production", "20-40", 
        "layer feed", "phase 1", "early lay"
    ],
    "layer_phase2": [
        "post-peak", "après-pic", "end-lay", "fin ponte", "40-80", 
        "phase 2", "late lay", "extended production"
    ]
}

ENHANCED_DOMAIN_KEYWORDS = {
    "performance": [
        # Poids & croissance
        "weight", "poids", "bw", "body weight", "live weight", "gain", "growth",
        "daily gain", "adg", "average daily gain", "croissance quotidienne",
        "weekly gain", "growth rate", "growth curve",
        
        # FCR & efficacité
        "fcr", "feed conversion", "conversion alimentaire", "feed efficiency",
        "feed intake", "consommation", "efficiency", "efficacité",
        "feed consumption", "consumption", "intake",
        
        # Mortalité & viabilité
        "mortality", "mortalité", "livability", "viabilité", "survival",
        "condemnation", "culling", "réforme", "death", "mort",
        
        # Production œufs
        "egg production", "ponte", "laying rate", "hen housed", "hen day",
        "eggs per hen", "œufs par poule", "production rate"
    ],
    
    "nutrition": [
        # Macronutriments
        "protein", "protéine", "crude protein", "cp", "energy", "énergie",
        "metabolizable energy", "me", "em", "fat", "lipid", "carbohydrate",
        "fiber", "fibre", "ash", "cendre",
        
        # Acides aminés
        "lysine", "methionine", "threonine", "tryptophan", "arginine",
        "cystine", "leucine", "isoleucine", "valine", "histidine",
        "amino acid", "acide aminé", "digestible", "digestible",
        
        # Minéraux & vitamines
        "calcium", "phosphorus", "sodium", "chloride", "potassium",
        "vitamin", "vitamine", "mineral", "trace element", "oligo-élément",
        "salt", "sel", "limestone", "calcaire", "dcp"
    ],
    
    "health": [
        # Vaccinations
        "vaccine", "vaccin", "vaccination", "immunization", "immunisation",
        "newcastle", "gumboro", "bronchitis", "marek", "salmonella",
        "avian influenza", "fowl pox", "laryngotracheitis",
        
        # Traitements
        "treatment", "traitement", "antibiotic", "antibiotique", "medication",
        "coccidiostat", "anticoccidien", "probiotic", "prebiotics",
        "organic acid", "acide organique", "essential oil",
        
        # Pathologies
        "disease", "maladie", "infection", "pathogen", "virus", "bacteria",
        "coccidiosis", "necrotic enteritis", "enteritis", "respiratory",
        "e.coli", "clostridium", "campylobacter", "ascites"
    ],
    
    "environment": [
        # Climat
        "temperature", "température", "humidity", "humidité", "ventilation",
        "air quality", "qualité air", "co2", "nh3", "ammonia", "ammoniac",
        "thermostat", "heating", "chauffage", "cooling",
        
        # Éclairage
        "light", "éclairage", "lighting", "photoperiod", "photopériode",
        "lux", "intensity", "intensité", "led", "incandescent",
        "dimming", "gradation", "daylight", "artificial light",
        
        # Densité & espace
        "density", "densité", "stocking", "space", "espace", "allowance",
        "feeder", "drinker", "mangeoire", "abreuvoir", "water system",
        "feeding system", "nipple", "bell drinker"
    ],
    
    "biosecurity": [
        "biosecurity", "biosécurité", "hygiene", "hygiène", "disinfection",
        "désinfection", "ppe", "visitor", "visiteur", "quarantine",
        "rodent control", "pest control", "cleaning", "nettoyage",
        "footbath", "pediluve", "shower", "douche", "barrier"
    ],
    
    "genetics": [
        "genetics", "génétique", "breeding", "sélection", "heritability",
        "héritabilité", "genetic improvement", "amélioration génétique",
        "breeding value", "valeur génétique", "selection", "trait"
    ],
    
    "welfare": [
        "welfare", "bien-être", "animal welfare", "stress", "behavior",
        "comportement", "enrichment", "enrichissement", "comfort",
        "confort", "feather pecking", "picage", "cannibalism"
    ]
}

# 🆕 DÉTECTION TYPE DE DOCUMENT AVANCÉE
DOCUMENT_TYPE_PATTERNS = {
    "guide": [
        "guide", "management guide", "breeding guide", "nutrition guide",
        "guide d'élevage", "guide nutritionnel", "manuel", "manual"
    ],
    "specification": [
        "specification", "specs", "spécification", "nutrition specification",
        "performance objectives", "objectifs", "standards", "requirements"
    ],
    "research": [
        "research", "étude", "study", "trial", "essai", "experiment",
        "recherche", "investigation", "analysis", "analyse"
    ],
    "technical_sheet": [
        "technical sheet", "fiche technique", "datasheet", "fact sheet",
        "product information", "technical data", "données techniques"
    ],
    "presentation": [
        "presentation", "présentation", "slide", "conference", "webinar",
        "seminar", "séminaire", "training", "formation"
    ]
}

# 🆕 DÉTECTION TABLE_TYPE SPÉCIALISÉE
TABLE_TYPE_PATTERNS = {
    "perf_targets": [
        # Patterns pour objectifs de performance
        r"(?:target|objective|objectif)\s*(?:weight|poids|bw|performance)",
        r"(?:age|day|week|jour|semaine)\s*(?:weight|poids|bw)",
        r"(?:growth|croissance)\s*(?:curve|courbe|target|objectif)",
        r"(?:performance|perf)\s*(?:standard|objective|target)",
        r"body\s*weight\s*(?:target|objective|standard)",
        r"weekly\s*(?:weight|gain|poids|gain)",
        r"fcr\s*(?:target|objective|standard)"
    ],
    "nutrition_specs": [
        r"(?:nutrition|nutritional)\s*(?:specification|requirement)",
        r"(?:feed|aliment)\s*(?:specification|composition)",
        r"(?:protein|energy|lysine|calcium)\s*(?:level|requirement)",
        r"amino\s*acid\s*(?:requirement|profile)",
        r"mineral\s*(?:requirement|specification)"
    ],
    "vaccination_schedule": [
        r"(?:vaccination|vaccine)\s*(?:program|schedule|programme)",
        r"immunization\s*(?:schedule|program)",
        r"vaccine\s*(?:timing|calendar|calendrier)"
    ],
    "feeding_program": [
        r"(?:feeding|feed)\s*(?:program|programme|schedule)",
        r"feed\s*(?:phase|transition)",
        r"nutritional\s*(?:program|phase)"
    ]
}

# ===============================
# FONCTIONS D'AMÉLIORATION ÉTENDUES
# ===============================

def enhanced_detect_species(text: str, filename: str) -> Tuple[Optional[str], float]:
    """
    Détection espèce avec score de confiance
    Returns: (species, confidence_score)
    """
    combined = (filename + " " + text).lower()
    best_species = None
    best_score = 0.0
    
    for species, keywords in ENHANCED_SPECIES_KEYWORDS.items():
        score = 0.0
        matches = 0
        
        for keyword in keywords:
            if keyword in combined:
                matches += 1
                # Score pondéré selon longueur et spécificité
                weight = len(keyword) / 10 + (1 if len(keyword) > 5 else 0.5)
                score += weight
        
        # Normalisation
        if len(keywords) > 0:
            confidence = min(score / len(keywords) * 2, 1.0)
        else:
            confidence = 0.0
        
        if confidence > best_score:
            best_score = confidence
            best_species = species
    
    return best_species, best_score

def enhanced_detect_line(text: str, filename: str) -> Optional[str]:
    """
    🆕 Détection lignée/line avec patterns regex avancés
    """
    combined = (filename + " " + text).lower()
    
    # Essayer les patterns regex d'abord (plus précis)
    for pattern, format_template in LINE_DETECTION_PATTERNS.items():
        match = re.search(pattern, combined, re.IGNORECASE)
        if match:
            try:
                return format_template.format(match.group(1).upper())
            except:
                continue
    
    # Fallback: recherche dans les mots-clés d'espèces pour souches spécifiques
    for species_keywords in ENHANCED_SPECIES_KEYWORDS.values():
        for keyword in species_keywords:
            # Seulement les mots-clés longs qui indiquent une lignée spécifique
            if len(keyword) > 8 and any(num in keyword for num in ['308', '500', '708', 'brown', 'white']):
                if keyword in combined:
                    return keyword.title()
    
    return None

def enhanced_detect_sex(text: str, filename: str) -> Optional[str]:
    """
    🆕 Détection du sexe avec patterns avancés
    """
    combined = (filename + " " + text).lower()
    
    sex_scores = {}
    for sex, keywords in SEX_KEYWORDS.items():
        score = 0
        for keyword in keywords:
            if keyword in combined:
                # Pondération selon la spécificité
                weight = 2 if len(keyword) > 4 else 1
                score += weight
        
        if score > 0:
            sex_scores[sex] = score
    
    if not sex_scores:
        return None
    
    # Retourner le sexe avec le meilleur score
    best_sex = max(sex_scores.keys(), key=lambda x: sex_scores[x])
    return best_sex

def detect_strain(text: str, filename: str) -> Optional[str]:
    """Détection souche spécifique via regex patterns (fonction existante améliorée)"""
    # Utiliser la nouvelle fonction enhanced_detect_line qui est plus avancée
    return enhanced_detect_line(text, filename)

def detect_production_phase(text: str) -> Optional[str]:
    """Détection phase de production"""
    text_lower = text.lower()
    best_phase = None
    best_matches = 0
    
    for phase, keywords in PRODUCTION_PHASE_KEYWORDS.items():
        matches = sum(1 for kw in keywords if kw in text_lower)
        if matches > best_matches:
            best_matches = matches
            best_phase = phase
    
    return best_phase if best_matches > 0 else None

def enhanced_detect_domain(text: str, filename: str) -> Tuple[Optional[str], float]:
    """
    Détection domaine avec score de confiance amélioré
    Returns: (domain, confidence_score)
    """
    combined = (filename + " " + text).lower()
    domain_scores = {}
    
    for domain, keywords in ENHANCED_DOMAIN_KEYWORDS.items():
        score = 0.0
        matches = 0
        
        for keyword in keywords:
            if keyword in combined:
                matches += 1
                # Score pondéré selon spécificité du mot-clé
                weight = len(keyword) / 8 + (1 if len(keyword) > 6 else 0.5)
                score += weight
        
        if matches > 0:
            domain_scores[domain] = score / len(keywords)
    
    if not domain_scores:
        return None, 0.0
    
    best_domain = max(domain_scores.keys(), key=lambda x: domain_scores[x])
    confidence = min(domain_scores[best_domain] * 2, 1.0)
    
    return best_domain, confidence

def enhanced_detect_document_type(text: str, filename: str) -> Optional[str]:
    """
    🆕 Détection du type de document
    """
    combined = (filename + " " + text).lower()
    
    type_scores = {}
    for doc_type, keywords in DOCUMENT_TYPE_PATTERNS.items():
        score = 0
        for keyword in keywords:
            if keyword in combined:
                # Pondération spéciale pour filename vs contenu
                weight = 2 if keyword in filename.lower() else 1
                score += weight
        
        if score > 0:
            type_scores[doc_type] = score
    
    if not type_scores:
        return None
    
    return max(type_scores.keys(), key=lambda x: type_scores[x])

def enhanced_detect_table_type(text: str, chunk_type: str) -> Optional[str]:
    """
    🆕 Détection spécialisée du type de tableau
    """
    if chunk_type != "table":
        return None
    
    text_lower = text.lower()
    
    for table_type, patterns in TABLE_TYPE_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return table_type
    
    return None

def detect_language(text: str) -> str:
    """Détection de langue améliorée"""
    if re.search(r"[éèàùç]", text):
        return "fr"
    elif re.search(r"[ñáéíóú]", text):
        return "es"
    elif re.search(r"[äöüß]", text):
        return "de"
    else:
        return "en"

def detect_age_range(text: str) -> Optional[str]:
    """Détection de tranches d'âge"""
    # Patterns pour différents formats d'âge
    age_patterns = [
        r"(\d+)[-–]\s*(\d+)\s*days?",
        r"(\d+)[-–]\s*(\d+)\s*weeks?",
        r"(\d+)[-–]\s*(\d+)\s*jours?",
        r"(\d+)[-–]\s*(\d+)\s*semaines?",
        r"day\s*(\d+)[-–]\s*(\d+)",
        r"week\s*(\d+)[-–]\s*(\d+)"
    ]
    
    text_lower = text.lower()
    for pattern in age_patterns:
        match = re.search(pattern, text_lower)
        if match:
            start, end = match.groups()
            if "week" in pattern or "semaine" in pattern:
                return f"{start}-{end} weeks"
            else:
                return f"{start}-{end} days"
    
    return None

def extract_page_number(metadata: Dict) -> Optional[int]:
    """
    🆕 Extraction robuste du numéro de page depuis différentes sources de métadonnées
    """
    # Sources possibles du numéro de page
    page_fields = ["page", "page_number", "page_num", "pagenum"]
    
    for field in page_fields:
        if field in metadata:
            try:
                return int(metadata[field])
            except (ValueError, TypeError):
                continue
    
    return None

# ===============================
# FONCTION PRINCIPALE AMÉLIORÉE
# ===============================

def enhanced_enrich_metadata(
    chunks: List[Dict[str, Any]], 
    species: Optional[str] = None,
    additional_context: Optional[Dict] = None
) -> List[Dict[str, Any]]:
    """
    🆕 Version complètement révisée pour garantir toutes les métadonnées requises
    
    GARANTIT :
    - species, line, sex (si détectable)
    - document_type, chunk_type, table_type
    - page_number (si disponible)
    - Tous les champs requis pour le filtrage RAG
    """
    
    enriched_chunks = []
    
    for chunk in chunks:
        text = chunk.get("text", "")
        existing_meta = chunk.get("metadata", {})
        
        # Extraire les infos de base
        source_file = existing_meta.get("source_file", existing_meta.get("source", ""))
        filename = os.path.basename(source_file) if source_file else ""
        
        # ===== DÉTECTIONS AVANCÉES =====
        
        # Espèce (priorité : param > existant > détecté)
        detected_species = species
        if not detected_species:
            detected_species = existing_meta.get("species")
        if not detected_species:
            detected_species, _ = enhanced_detect_species(text, filename)
        
        # Lignée/Line (nouveau)
        detected_line = existing_meta.get("line") or existing_meta.get("strain")
        if not detected_line:
            detected_line = enhanced_detect_line(text, filename)
        
        # Sexe (nouveau)
        detected_sex = existing_meta.get("sex")
        if not detected_sex:
            detected_sex = enhanced_detect_sex(text, filename)
        
        # Type de document
        detected_doc_type = existing_meta.get("document_type")
        if not detected_doc_type:
            detected_doc_type = enhanced_detect_document_type(text, filename)
        
        # Type de chunk (priorité : existant > détecté)
        chunk_type = existing_meta.get("chunk_type", "text")
        
        # Type de table (seulement si chunk_type = "table")
        table_type = existing_meta.get("table_type")
        if chunk_type == "table" and not table_type:
            table_type = enhanced_detect_table_type(text, chunk_type)
        
        # Domaine
        detected_domain = existing_meta.get("domain")
        if not detected_domain:
            detected_domain, _ = enhanced_detect_domain(text, filename)
        
        # Phase de production
        detected_phase = existing_meta.get("production_phase")
        if not detected_phase:
            detected_phase = detect_production_phase(text)
        
        # Langue
        detected_language = existing_meta.get("language")
        if not detected_language:
            detected_language = detect_language(text)
        
        # Tranche d'âge
        detected_age_range = existing_meta.get("age_range")
        if not detected_age_range:
            detected_age_range = detect_age_range(text)
        
        # Numéro de page
        page_number = extract_page_number(existing_meta)
        
        # ===== CONSTRUCTION MÉTADONNÉES ENRICHIES =====
        
        enriched_metadata: ChunkMeta = {
            "source": filename or source_file or "unknown",
            "chunk_type": chunk_type,
            "language": detected_language or "en",
        }
        
        # Ajout conditionnel des métadonnées détectées
        if detected_species:
            enriched_metadata["species"] = detected_species
        
        if detected_line:
            enriched_metadata["line"] = detected_line  # 🆕 Nouveau champ
        
        if detected_sex:
            enriched_metadata["sex"] = detected_sex  # 🆕 Nouveau champ
        
        if detected_doc_type:
            enriched_metadata["document_type"] = detected_doc_type  # 🆕 Nouveau champ
        
        if table_type:
            enriched_metadata["table_type"] = table_type  # 🆕 Nouveau champ
        
        if detected_domain:
            enriched_metadata["domain"] = detected_domain
        
        if detected_phase:
            enriched_metadata["production_phase"] = detected_phase
        
        if detected_age_range:
            enriched_metadata["age_range"] = detected_age_range
        
        if page_number:
            enriched_metadata["page_number"] = page_number  # 🆕 Nouveau champ
        
        # ===== PRÉSERVATION MÉTADONNÉES EXISTANTES =====
        
        # Préserver les métadonnées existantes non remplacées
        for key, value in existing_meta.items():
            if key not in enriched_metadata and value is not None:
                # Mapper les anciens noms vers les nouveaux
                key_mapping = {
                    "strain": "line",
                    "page": "page_number",
                    "source_file": "source"
                }
                mapped_key = key_mapping.get(key, key)
                
                # Ajouter seulement si c'est un champ valide du schéma
                if mapped_key in ChunkMeta.__annotations__:
                    enriched_metadata[mapped_key] = value
        
        # ===== CONTEXTE ADDITIONNEL =====
        
        if additional_context:
            for key, value in additional_context.items():
                if key in ChunkMeta.__annotations__ and value is not None:
                    # Ne pas écraser les valeurs déjà détectées
                    if key not in enriched_metadata:
                        enriched_metadata[key] = value
        
        # ===== VALIDATION ET AJOUT =====
        
        enriched_chunk = {
            "text": text,
            "metadata": enriched_metadata
        }
        
        enriched_chunks.append(enriched_chunk)
    
    return enriched_chunks

# ===============================
# FONCTIONS DE VALIDATION ET DEBUG
# ===============================

def validate_required_metadata(chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    🆕 Valide que les chunks contiennent les métadonnées requises pour le filtrage RAG
    """
    required_for_filtering = ["species", "line", "sex", "document_type", "chunk_type"]
    
    stats = {
        "total_chunks": len(chunks),
        "coverage": {},
        "missing_combinations": []
    }
    
    for field in required_for_filtering:
        with_field = sum(1 for chunk in chunks if chunk.get("metadata", {}).get(field))
        stats["coverage"][field] = {
            "count": with_field,
            "percentage": (with_field / len(chunks) * 100) if chunks else 0
        }
    
    # Analyse des combinaisons manquantes critiques
    critical_missing = 0
    for chunk in chunks:
        meta = chunk.get("metadata", {})
        if not meta.get("species") or not meta.get("chunk_type"):
            critical_missing += 1
    
    stats["critical_missing"] = critical_missing
    stats["critical_coverage"] = ((len(chunks) - critical_missing) / len(chunks) * 100) if chunks else 0
    
    return stats

def analyze_table_detection(chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    🆕 Analyse la qualité de détection des tables et de leur type
    """
    tables = [chunk for chunk in chunks if chunk.get("metadata", {}).get("chunk_type") == "table"]
    
    table_types = {}
    for chunk in tables:
        t_type = chunk.get("metadata", {}).get("table_type", "unspecified")
        table_types[t_type] = table_types.get(t_type, 0) + 1
    
    return {
        "total_chunks": len(chunks),
        "tables_detected": len(tables),
        "table_percentage": (len(tables) / len(chunks) * 100) if chunks else 0,
        "table_types": table_types,
        "perf_targets_tables": table_types.get("perf_targets", 0)
    }

# ===============================
# COMPATIBILITÉ ARRIÈRE (conservation fonctions originales)
# ===============================

# Conservation des fonctions originales pour compatibilité
SPECIES_KEYWORDS = {
    "broiler": ["ross", "cobb", "broiler"],
    "layer": ["hy-line", "lohmann", "isa", "layer"],
}

DOMAIN_KEYWORDS = {
    "performance": ["weight", "fcr", "mortality", "performance"],
    "nutrition": ["protein", "energy", "lysine", "calcium", "phosphorus", "feed"],
    "health": ["vaccine", "treatment", "dose", "protocol", "disease"],
    "environment": ["temperature", "humidity", "ventilation", "lux", "density"],
    "biosecurity": ["biosecurity", "hygiene", "disinfection", "ppe", "visitor"],
}

def detect_species(text: str, filename: str) -> Optional[str]:
    """Fonction originale conservée pour compatibilité"""
    species, _ = enhanced_detect_species(text, filename)
    return species

def detect_domain(text: str, filename: str) -> Optional[str]:
    """Fonction originale conservée pour compatibilité"""
    domain, _ = enhanced_detect_domain(text, filename)
    return domain

def enrich_metadata(file_path: str, text: str, chunk_type: str = "text", domain: Optional[str] = None) -> ChunkMeta:
    """Fonction originale conservée pour compatibilité"""
    filename = os.path.basename(file_path)
    species = detect_species(text, filename)
    if not domain:
        domain = detect_domain(text, filename)
    return {
        "source": filename,
        "species": species,
        "strain": None,  # Mappé vers "line" dans enhanced
        "domain": domain or "general",
        "chunk_type": chunk_type,
        "language": "fr" if re.search(r"[éèàù]", text) else "en",
    }
