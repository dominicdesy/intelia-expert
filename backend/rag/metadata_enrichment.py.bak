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

# ===============================
# FONCTIONS D'AMÉLIORATION
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


def detect_strain(text: str, filename: str) -> Optional[str]:
    """Détection souche spécifique via regex patterns"""
    combined = (filename + " " + text).lower()
    
    for pattern, format_str in STRAIN_PATTERNS.items():
        match = re.search(pattern, combined, re.IGNORECASE)
        if match:
            if "{strain}" in format_str:
                strain_value = match.group(1) if match.groups() else match.group(0)
                return format_str.format(strain=strain_value)
            else:
                return format_str.format(**match.groupdict())
    
    # Recherche de souches complètes dans les mots-clés
    for species_keywords in ENHANCED_SPECIES_KEYWORDS.values():
        for keyword in species_keywords:
            if len(keyword) > 8 and keyword in combined:  # Souches spécifiques
                return keyword.title()
    
    return None


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


# ===============================
# FONCTIONS PRINCIPALES
# ===============================

def enhanced_enrich_metadata(
    file_path: str, 
    text: str, 
    chunk_type: str = "text", 
    domain: Optional[str] = None,
    additional_context: Optional[Dict] = None
) -> ChunkMeta:
    """
    Version améliorée de l'enrichissement des métadonnées
    """
    filename = os.path.basename(file_path)
    
    # Détection des espèces avec confiance
    species, species_confidence = enhanced_detect_species(text, filename)
    
    # Détection des souches
    strain = detect_strain(text, filename)
    
    # Détection du domaine avec confiance
    if not domain:
        domain, domain_confidence = enhanced_detect_domain(text, filename)
    else:
        domain_confidence = 1.0  # Confiance maximale si fourni explicitement
    
    # Détections additionnelles
    production_phase = detect_production_phase(text)
    language = detect_language(text)
    age_range = detect_age_range(text)
    
    # Construction des métadonnées
    metadata: ChunkMeta = {
        "source": filename,
        "chunk_type": chunk_type,
        "language": language,
    }
    
    # Ajout conditionnel des métadonnées détectées
    if species:
        metadata["species"] = species
    if strain:
        metadata["strain"] = strain
    if domain:
        metadata["domain"] = domain
        metadata["domain_confidence"] = domain_confidence
    if production_phase:
        metadata["production_phase"] = production_phase
    if age_range:
        metadata["age_range"] = age_range
    
    # Ajout du contexte additionnel
    if additional_context:
        for key, value in additional_context.items():
            if key in ChunkMeta.__annotations__ and value is not None:
                metadata[key] = value
    
    return metadata


# ===============================
# COMPATIBILITÉ ARRIÈRE
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
    combined = (filename + " " + text).lower()
    for sp, kws in SPECIES_KEYWORDS.items():
        if any(k in combined for k in kws):
            return sp
    return None

def detect_domain(text: str, filename: str) -> Optional[str]:
    """Fonction originale conservée pour compatibilité"""
    combined = (filename + " " + text).lower()
    for dom, kws in DOMAIN_KEYWORDS.items():
        if any(k in combined for k in kws):
            return dom
    return None

def enrich_metadata(file_path: str, text: str, chunk_type: str = "text", domain: Optional[str] = None) -> ChunkMeta:
    """Fonction originale conservée pour compatibilité"""
    filename = os.path.basename(file_path)
    species = detect_species(text, filename)
    if not domain:
        domain = detect_domain(text, filename)
    return {
        "source": filename,
        "species": species,
        "strain": None,
        "domain": domain or "general",
        "chunk_type": chunk_type,
        "language": "fr" if re.search(r"[éèàù]", text) else "en",
    }