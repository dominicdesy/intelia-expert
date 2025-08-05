"""
app/api/v1/expert_clarification_service.py - SERVICE D'AUTO-CLARIFICATION AMÉLIORÉ

🔧 NOUVELLES FONCTIONNALITÉS IMPLÉMENTÉES:
✅ Détection automatique du sujet par GPT-4o-mini (économique + précis)
✅ Sélection dynamique de templates (generic vs specific)
✅ Adaptation selon le nombre d'entités manquantes
✅ Templates contextualisés pour une meilleure pertinence
✅ Validation renforcée des questions générées
✅ Fallback intelligent avec extraction de patterns malformés
✅ Système de scoring qualité multicritères
✅ Vérification de couverture complète des entités
✅ Normalisation avancée des questions
"""

import logging
import re
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
import json

# Import sécurisé au niveau module pour éviter les imports circulaires
try:
    from .expert_models import EnhancedExpertResponse, DynamicClarification
    from .openai_service import OpenAIService
except ImportError as e:
    logger = logging.getLogger(__name__)
    logger.error(f"❌ Import error: {e}")
    # Définir des classes mock si nécessaire
    class EnhancedExpertResponse:
        pass
    class DynamicClarification:
        pass
    class OpenAIService:
        def __init__(self):
            pass

logger = logging.getLogger(__name__)

# =============================================================================
# PROMPT DE DÉTECTION AUTOMATIQUE DE SUJET AVEC GPT
# =============================================================================

TOPIC_DETECTION_PROMPT = {
    "fr": """Tu es un expert vétérinaire avicole. Analyse cette question et identifie le sujet principal en UN SEUL MOT français.

Question: "{question}"

Choisis UNIQUEMENT parmi ces 7 sujets (réponds par le mot exact):
- santé (maladie, mortalité, symptômes, diagnostic, traitement)
- nutrition (alimentation, eau, compléments, ration, vitamines)
- croissance (poids, développement, performance, GMQ, standards)
- reproduction (ponte, incubation, fertilité, couvaison, œufs)
- environnement (température, ventilation, litière, densité, bâtiment)
- vaccination (protocole, programme, immunité, prévention)
- général (autre sujet ou question trop vague)

Retourne uniquement le mot choisi, sans explication.""",

    "en": """You are a poultry veterinary expert. Analyze this question and identify the main topic in ONE ENGLISH WORD.

Question: "{question}"

Choose ONLY from these 7 topics (respond with the exact word):
- health (disease, mortality, symptoms, diagnosis, treatment)
- nutrition (feeding, water, supplements, ration, vitamins)
- growth (weight, development, performance, ADG, standards)
- reproduction (laying, incubation, fertility, brooding, eggs)
- environment (temperature, ventilation, litter, density, housing)
- vaccination (protocol, program, immunity, prevention)
- general (other topic or too vague question)

Return only the chosen word, without explanation.""",

    "es": """Eres un experto veterinario avícola. Analiza esta pregunta e identifica el tema principal en UNA SOLA PALABRA en español.

Pregunta: "{question}"

Elige ÚNICAMENTE entre estos 7 temas (responde con la palabra exacta):
- salud (enfermedad, mortalidad, síntomas, diagnóstico, tratamiento)
- nutrición (alimentación, agua, suplementos, ración, vitaminas)
- crecimiento (peso, desarrollo, rendimiento, GMD, estándares)
- reproducción (puesta, incubación, fertilidad, empollado, huevos)
- ambiente (temperatura, ventilación, cama, densidad, alojamiento)
- vacunación (protocolo, programa, inmunidad, prevención)
- general (otro tema o pregunta muy vaga)

Devuelve solo la palabra elegida, sin explicación."""
}

# =============================================================================
# TEMPLATES DE CLARIFICATION DYNAMIQUES AMÉLIORÉS
# =============================================================================

CLARIFICATION_TEMPLATES = {
    "generic": {
        "fr": """Tu es un expert vétérinaire spécialisé en volaille. L'utilisateur a posé une question qui manque de contexte important.

Question utilisateur: "{user_question}"
Contexte conversation: {conversation_context}
Entités manquantes détectées: {missing_entities}

Génère exactement 3-4 questions de clarification courtes et précises pour obtenir les informations manquantes. Les questions doivent être:
- Spécifiques au domaine aviaire
- Courtes (maximum 15 mots)
- Directes et pratiques
- En français
- Chacune doit couvrir une entité manquante différente

Retourne uniquement un JSON avec la liste des questions:
{{"questions": ["question 1", "question 2", "question 3"]}}""",

        "en": """You are a veterinary expert specialized in poultry. The user asked a question that lacks important context.

User question: "{user_question}"
Conversation context: {conversation_context}
Missing entities detected: {missing_entities}

Generate exactly 3-4 short and precise clarification questions to obtain the missing information. Questions should be:
- Specific to poultry domain
- Short (maximum 15 words)
- Direct and practical
- In English
- Each should cover a different missing entity

Return only JSON with the list of questions:
{{"questions": ["question 1", "question 2", "question 3"]}}""",

        "es": """Eres un experto veterinario especializado en aves de corral. El usuario hizo una pregunta que carece de contexto importante.

Pregunta del usuario: "{user_question}"
Contexto de conversación: {conversation_context}
Entidades faltantes detectadas: {missing_entities}

Genera exactamente 3-4 preguntas de aclaración cortas y precisas para obtener la información faltante. Las preguntas deben ser:
- Específicas al dominio avícola
- Cortas (máximo 15 palabras)
- Directas y prácticas
- En español
- Cada una debe cubrir una entidad faltante diferente

Devuelve solo JSON con la lista de preguntas:
{{"questions": ["pregunta 1", "pregunta 2", "pregunta 3"]}}"""
    },
    
    "specific": {
        "fr": """Tu es un expert vétérinaire spécialisé en volaille, particulièrement en {topic}.

Question utilisateur: "{user_question}"
Sujet détecté: {topic}
Contexte conversation: {conversation_context}
Informations spécifiques manquantes: {missing_entities}

Génère exactement 2-3 questions de clarification très ciblées pour ce sujet spécifique. Les questions doivent être:
- Hyper-spécialisées en {topic} aviaire
- Techniques et précises
- Courtes (maximum 12 mots)
- Orientées solution pratique
- En français
- Essentielles pour donner un conseil expert en {topic}

Retourne uniquement un JSON avec la liste des questions:
{{"questions": ["question 1", "question 2"]}}""",

        "en": """You are a veterinary expert specialized in poultry, particularly in {topic}.

User question: "{user_question}"
Detected topic: {topic}
Conversation context: {conversation_context}
Specific missing information: {missing_entities}

Generate exactly 2-3 highly targeted clarification questions for this specific topic. Questions should be:
- Hyper-specialized in poultry {topic}
- Technical and precise
- Short (maximum 12 words)
- Solution-oriented practical
- In English
- Essential to provide expert {topic} advice

Return only JSON with the list of questions:
{{"questions": ["question 1", "question 2"]}}""",

        "es": """Eres un experto veterinario especializado en aves de corral, particularmente en {topic}.

Pregunta del usuario: "{user_question}"
Tema detectado: {topic}
Contexto de conversación: {conversation_context}
Información específica faltante: {missing_entities}

Genera exactamente 2-3 preguntas de aclaración muy específicas para este tema. Las preguntas deben ser:
- Hiper-especializadas en {topic} avícola
- Técnicas y precisas
- Cortas (máximo 12 palabras)
- Orientadas a solución práctica
- En español
- Esenciales para dar consejo experto en {topic}

Devuelve solo JSON con la lista de preguntas:
{{"questions": ["pregunta 1", "pregunta 2"]}}"""
    }
}

# =============================================================================
# FONCTION DE DÉTECTION AUTOMATIQUE AVEC GPT-4O-MINI
# =============================================================================

def detect_topic_with_gpt(user_question: str, language: str = "fr") -> str:
    """
    Détecte automatiquement le sujet de la question avec GPT-4o-mini (économique + précis)
    
    Args:
        user_question: Question de l'utilisateur
        language: Langue de détection
    
    Returns:
        str: Le sujet détecté ("santé", "nutrition", "croissance", etc.)
    """
    
    try:
        # Initialiser le service OpenAI
        openai_service = OpenAIService()
        
        # Préparer le prompt de détection selon la langue
        detection_prompt = TOPIC_DETECTION_PROMPT.get(language, TOPIC_DETECTION_PROMPT["fr"])
        prompt = detection_prompt.format(question=user_question)
        
        # Appeler GPT-4o-mini pour détection (économique et efficace)
        response = openai_service.generate_completion(
            prompt=prompt,
            max_tokens=10,  # Un seul mot attendu
            temperature=0.1,  # Très déterministe
            model="gpt-4o-mini"  # Modèle économique mais performant
        )
        
        if response and response.strip():
            detected_topic = response.strip().lower()
            
            # Validation des sujets autorisés par langue
            valid_topics = {
                "fr": ["santé", "nutrition", "croissance", "reproduction", "environnement", "vaccination", "général"],
                "en": ["health", "nutrition", "growth", "reproduction", "environment", "vaccination", "general"],
                "es": ["salud", "nutrición", "crecimiento", "reproducción", "ambiente", "vacunación", "general"]
            }
            
            language_topics = valid_topics.get(language, valid_topics["fr"])
            
            if detected_topic in language_topics:
                logger.info(f"✅ [GPT Topic Detection] Sujet détecté: {detected_topic}")
                return detected_topic
            else:
                logger.warning(f"⚠️ [GPT Topic Detection] Sujet invalide: {detected_topic} - fallback")
                return language_topics[-1]  # "général" / "general"
        
    except Exception as e:
        logger.error(f"❌ [GPT Topic Detection] Erreur: {e}")
    
    # Fallback : détection par mots-clés si GPT échoue
    return _detect_topic_fallback(user_question, language)

def _detect_topic_fallback(user_question: str, language: str = "fr") -> str:
    """Détection de sujet par mots-clés en fallback si GPT échoue"""
    
    try:
        question_lower = user_question.lower()
        
        # Mots-clés étendus par sujet et langue
        topic_keywords = {
            "fr": {
                "santé": ["maladie", "mort", "mortalité", "symptôme", "infection", "virus", "bactérie", 
                         "diagnostic", "soigner", "traitement", "antibiotique", "médicament", "vétérinaire"],
                "nutrition": ["alimentation", "aliment", "eau", "boire", "manger", "ration", "complément", 
                             "protéine", "énergie", "vitamines", "minéraux", "calcium", "phosphore"],
                "croissance": ["poids", "pèse", "croissance", "développement", "performance", "gmq", "gain", 
                              "référence", "standard", "courbe", "objectif", "indice"],
                "reproduction": ["ponte", "œuf", "incubation", "fertilité", "couvaison", "reproduction", 
                                "poussin", "éclosion", "reproducteur", "incubateur"],
                "environnement": ["température", "ventilation", "litière", "densité", "bâtiment", "chauffage", 
                                 "humidité", "espace", "luminosité", "stress", "ambiance"],
                "vaccination": ["vaccin", "vaccination", "protocole", "immunité", "programme", "rappel", 
                               "protection", "anticorps", "immunisation", "prévention"]
            },
            "en": {
                "health": ["disease", "death", "mortality", "symptom", "infection", "virus", "bacteria", 
                          "diagnosis", "treat", "treatment", "antibiotic", "medicine", "veterinary"],
                "nutrition": ["feed", "feeding", "water", "drink", "eat", "ration", "supplement", 
                             "protein", "energy", "vitamins", "minerals", "calcium", "phosphorus"],
                "growth": ["weight", "weigh", "growth", "development", "performance", "adg", "gain", 
                          "reference", "standard", "curve", "target", "index"],
                "reproduction": ["laying", "egg", "incubation", "fertility", "brooding", "reproduction", 
                                "chick", "hatching", "breeder", "incubator"],
                "environment": ["temperature", "ventilation", "litter", "density", "building", "heating", 
                               "humidity", "space", "lighting", "stress", "atmosphere"],
                "vaccination": ["vaccine", "vaccination", "protocol", "immunity", "program", "booster", 
                               "protection", "antibody", "immunization", "prevention"]
            },
            "es": {
                "salud": ["enfermedad", "muerte", "mortalidad", "síntoma", "infección", "virus", "bacteria", 
                         "diagnóstico", "tratar", "tratamiento", "antibiótico", "medicina", "veterinario"],
                "nutrición": ["alimento", "alimentación", "agua", "beber", "comer", "ración", "suplemento", 
                             "proteína", "energía", "vitaminas", "minerales", "calcio", "fósforo"],
                "crecimiento": ["peso", "pesa", "crecimiento", "desarrollo", "rendimiento", "gmd", "ganancia", 
                               "referencia", "estándar", "curva", "objetivo", "índice"],
                "reproducción": ["puesta", "huevo", "incubación", "fertilidad", "empollado", "reproducción", 
                                "pollito", "eclosión", "reproductor", "incubadora"],
                "ambiente": ["temperatura", "ventilación", "cama", "densidad", "edificio", "calefacción", 
                            "humedad", "espacio", "iluminación", "estrés", "ambiente"],
                "vacunación": ["vacuna", "vacunación", "protocolo", "inmunidad", "programa", "refuerzo", 
                              "protección", "anticuerpo", "inmunización", "prevención"]
            }
        }
        
        language_keywords = topic_keywords.get(language, topic_keywords["fr"])
        
        # Compter les correspondances pour chaque sujet
        topic_scores = {}
        for topic, keywords in language_keywords.items():
            score = sum(1 for keyword in keywords if keyword in question_lower)
            if score > 0:
                topic_scores[topic] = score
        
        # Retourner le sujet avec le plus de correspondances
        if topic_scores:
            best_topic = max(topic_scores, key=topic_scores.get)
            logger.info(f"✅ [Keyword Fallback] Sujet détecté: {best_topic} (score: {topic_scores[best_topic]})")
            return best_topic
        
    except Exception as e:
        logger.error(f"❌ [Topic Fallback] Erreur: {e}")
    
    # Fallback ultime
    fallback_topics = {"fr": "général", "en": "general", "es": "general"}
    return fallback_topics.get(language, "général")

# =============================================================================
# DÉTECTION D'ENTITÉS MANQUANTES AMÉLIORÉE
# =============================================================================

def detect_missing_entities(user_question: str, language: str = "fr") -> List[str]:
    """
    Détecte les entités importantes manquantes dans la question avec patterns étendus
    
    Args:
        user_question: Question de l'utilisateur
        language: Langue pour les patterns
    
    Returns:
        List[str]: Liste des entités manquantes
    """
    
    try:
        question_lower = user_question.lower()
        missing_entities = []
        
        # Patterns de détection d'entités étendus
        entity_patterns = {
            "fr": {
                "race": [
                    r'\b(ross\s*308|cobb\s*500|hubbard|arbor\s*acres)\b',
                    r'\brace\b', r'\bsouche\b', r'\blignée\b'
                ],
                "âge": [
                    r'\d+\s*(?:jour|semaine|mois)s?',
                    r'\bâge\b', r'\bvieux\b', r'\bjeune\b'
                ],
                "sexe": [
                    r'\b(mâle|femelle|coq|poule|mixte)s?\b',
                    r'\bsexe\b'
                ],
                "nombre": [
                    r'\d+\s*(?:poulet|volaille|animal|tête)s?',
                    r'\btroupeau\b', r'\blot\b', r'\beffectif\b'
                ],
                "symptômes": [
                    r'\bsymptôme\b', r'\bsigne\b', r'\bobserve\b',
                    r'\bcomportement\b', r'\bproblème\b'
                ],
                "conditions": [
                    r'\btempérature\b', r'\benvironnement\b', r'\bcondition\b',
                    r'\bambiance\b', r'\bventilation\b'
                ],
                "poids": [
                    r'\d+\s*(?:g|kg|gramme|kilo)s?',
                    r'\bpoids\b', r'\bpèse\b', r'\blourd\b'
                ],
                "durée": [
                    r'\bdepuis\b', r'\bpendant\b', r'\bdurée\b',
                    r'\bcombien\s+de\s+temps\b'
                ]
            },
            "en": {
                "breed": [
                    r'\b(ross\s*308|cobb\s*500|hubbard|arbor\s*acres)\b',
                    r'\bbreed\b', r'\bstrain\b', r'\bline\b'
                ],
                "age": [
                    r'\d+\s*(?:day|week|month)s?',
                    r'\bage\b', r'\bold\b', r'\byoung\b'
                ],
                "sex": [
                    r'\b(male|female|rooster|hen|mixed)\b',
                    r'\bsex\b', r'\bgender\b'
                ],
                "number": [
                    r'\d+\s*(?:chicken|bird|animal|head)s?',
                    r'\bflock\b', r'\bbatch\b', r'\bnumber\b'
                ],
                "symptoms": [
                    r'\bsymptom\b', r'\bsign\b', r'\bobserve\b',
                    r'\bbehavior\b', r'\bproblem\b'
                ],
                "conditions": [
                    r'\btemperature\b', r'\benvironment\b', r'\bcondition\b',
                    r'\batmosphere\b', r'\bventilation\b'
                ],
                "weight": [
                    r'\d+\s*(?:g|kg|gram|kilo)s?',
                    r'\bweight\b', r'\bweigh\b', r'\bheavy\b'
                ],
                "duration": [
                    r'\bsince\b', r'\bfor\b', r'\bduration\b',
                    r'\bhow\s+long\b'
                ]
            },
            "es": {
                "raza": [
                    r'\b(ross\s*308|cobb\s*500|hubbard|arbor\s*acres)\b',
                    r'\braza\b', r'\bcepa\b', r'\blínea\b'
                ],
                "edad": [
                    r'\d+\s*(?:día|semana|mes)s?',
                    r'\bedad\b', r'\bviejo\b', r'\bjoven\b'
                ],
                "sexo": [
                    r'\b(macho|hembra|gallo|gallina|mixto)s?\b',
                    r'\bsexo\b'
                ],
                "número": [
                    r'\d+\s*(?:pollo|ave|animal|cabeza)s?',
                    r'\blote\b', r'\bgrupo\b', r'\bnúmero\b'
                ],
                "síntomas": [
                    r'\bsíntoma\b', r'\bsigno\b', r'\bobserva\b',
                    r'\bcomportamiento\b', r'\bproblema\b'
                ],
                "condiciones": [
                    r'\btemperatura\b', r'\bambiente\b', r'\bcondición\b',
                    r'\batmósfera\b', r'\bventilación\b'
                ],
                "peso": [
                    r'\d+\s*(?:g|kg|gramo|kilo)s?',
                    r'\bpeso\b', r'\bpesa\b', r'\bpesado\b'
                ],
                "duración": [
                    r'\bdesde\b', r'\bpor\b', r'\bduración\b',
                    r'\bcuánto\s+tiempo\b'
                ]
            }
        }
        
        patterns = entity_patterns.get(language, entity_patterns["fr"])
        
        # Vérifier chaque type d'entité avec patterns multiples
        for entity_type, regex_patterns in patterns.items():
            found = False
            for pattern in regex_patterns:
                try:
                    if re.search(pattern, question_lower, re.IGNORECASE):
                        found = True
                        break
                except re.error as e:
                    logger.warning(f"⚠️ [Entity Detection] Regex error: {e}")
                    continue
            
            if not found:
                missing_entities.append(entity_type)
        
        # Logging avec détails
        logger.info(f"🔍 [Entity Detection] Question: {user_question[:50]}...")
        logger.info(f"🔍 [Entity Detection] Entités manquantes: {missing_entities}")
        
        return missing_entities
        
    except Exception as e:
        logger.error(f"❌ [Entity Detection] Erreur: {e}")
        return ["contexte", "précisions"]  # Fallback sécurisé

# =============================================================================
# SÉLECTION DE TEMPLATE INTELLIGENTE
# =============================================================================

def select_clarification_prompt(user_question: str, missing_entities: List[str], 
                               context: str, language: str = "fr") -> str:
    """
    Sélectionne dynamiquement le template de clarification approprié
    
    Args:
        user_question: Question de l'utilisateur
        missing_entities: Liste des entités manquantes
        context: Contexte de la conversation
        language: Langue de réponse
    
    Returns:
        str: Le prompt formaté pour GPT
    """
    
    try:
        # Détection automatique du sujet avec GPT-4o-mini
        topic = detect_topic_with_gpt(user_question, language)
        
        # Logique de sélection du template
        if len(missing_entities) > 3 or topic == "général":
            # Template générique pour questions complexes ou vagues
            template_type = "generic"
            template = CLARIFICATION_TEMPLATES["generic"][language]
            
            prompt = template.format(
                user_question=user_question,
                conversation_context=context or "Aucun contexte précédent",
                missing_entities=", ".join(missing_entities) if missing_entities else "informations contextuelles"
            )
            
            logger.info(f"📋 [Template Selection] GÉNÉRIQUE sélectionné - {len(missing_entities)} entités, sujet: {topic}")
            
        else:
            # Template spécifique pour questions ciblées avec sujet identifié
            template_type = "specific"
            template = CLARIFICATION_TEMPLATES["specific"][language]
            
            prompt = template.format(
                user_question=user_question,
                topic=topic,
                conversation_context=context or "Aucun contexte précédent",
                missing_entities=", ".join(missing_entities) if missing_entities else "détails techniques"
            )
            
            logger.info(f"🎯 [Template Selection] SPÉCIFIQUE sélectionné - Sujet: {topic}, {len(missing_entities)} entités")
        
        return prompt
        
    except Exception as e:
        logger.error(f"❌ [Template Selection] Erreur: {e}")
        # Fallback vers template générique sécurisé
        fallback_template = CLARIFICATION_TEMPLATES["generic"][language]
        return fallback_template.format(
            user_question=user_question,
            conversation_context=context or "Aucun contexte",
            missing_entities=", ".join(missing_entities) if missing_entities else "informations contextuelles"
        )

# =============================================================================
# GÉNÉRATION ET VALIDATION AMÉLIORÉES
# =============================================================================

def _generate_clarification_questions_with_dynamic_prompt(prompt: str, language: str = "fr") -> List[str]:
    """
    Génère questions avec le prompt dynamique sélectionné et gestion d'erreurs robuste
    
    Args:
        prompt: Prompt formaté pour GPT
        language: Langue de génération
    
    Returns:
        List[str]: Questions générées et validées
    """
    
    try:
        # Initialiser le service OpenAI
        openai_service = OpenAIService()
        
        # Appeler GPT-4o avec le prompt sélectionné
        response = openai_service.generate_completion(
            prompt=prompt,
            max_tokens=400,  # Plus de tokens pour des réponses complètes
            temperature=0.3,  # Équilibre créativité/déterminisme
            model="gpt-4o"  # Utiliser GPT-4o pour la qualité maximale
        )
        
        if response:
            # Tentative de parsing JSON propre
            try:
                response_clean = response.strip()
                response_data = json.loads(response_clean)
                questions = response_data.get("questions", [])
                
                if questions and isinstance(questions, list) and len(questions) > 0:
                    logger.info(f"✅ [Dynamic Generation] {len(questions)} questions générées par GPT-4o")
                    return questions
                else:
                    logger.warning("⚠️ [Dynamic Generation] Réponse JSON valide mais vide")
                
            except json.JSONDecodeError as e:
                logger.warning(f"⚠️ [Dynamic Generation] JSON malformé: {e}")
                logger.debug(f"Réponse GPT brute: {response}")
                
                # Tentative d'extraction de questions depuis réponse malformée
                extracted_questions = _extract_questions_from_malformed_response(response, language)
                if extracted_questions:
                    logger.info(f"✅ [Dynamic Generation] {len(extracted_questions)} questions extraites en mode dégradé")
                    return extracted_questions
        
    except Exception as e:
        logger.error(f"❌ [Dynamic Generation] Erreur GPT: {e}")
    
    # Retourner liste vide pour déclencher fallback
    return []

def _extract_questions_from_malformed_response(response: str, language: str = "fr") -> List[str]:
    """
    Extrait intelligemment les questions d'une réponse GPT malformée
    
    Args:
        response: Réponse GPT brute
        language: Langue pour les patterns
    
    Returns:
        List[str]: Questions extraites
    """
    
    try:
        # Patterns d'extraction selon la langue et format
        question_patterns = {
            "fr": [
                r'(?:^|\n)\s*(?:\d+[\.\)]\s*)?([^.!?\n]{5,}?\?)\s*(?:\n|$)',  # Questions numérotées
                r'(?:^|\n)\s*[•\-\*]\s*([^.!?\n]{5,}?\?)\s*(?:\n|$)',  # Questions avec puces
                r'"([^"]{5,}?\?)"',  # Questions entre guillemets
                r"'([^']{5,}?\?)'",  # Questions entre apostrophes
                r'(?:questions?[^\n]*:.*?)([A-Z][^.!?\n]{5,}?\?)',  # Questions après "questions:"
            ],
            "en": [
                r'(?:^|\n)\s*(?:\d+[\.\)]\s*)?([^.!?\n]{5,}?\?)\s*(?:\n|$)',
                r'(?:^|\n)\s*[•\-\*]\s*([^.!?\n]{5,}?\?)\s*(?:\n|$)',
                r'"([^"]{5,}?\?)"',
                r"'([^']{5,}?\?)'",
                r'(?:questions?[^\n]*:.*?)([A-Z][^.!?\n]{5,}?\?)',
            ],
            "es": [
                r'(?:^|\n)\s*(?:\d+[\.\)]\s*)?([^.!?\n]{5,}?\?)\s*(?:\n|$)',
                r'(?:^|\n)\s*[•\-\*]\s*([^.!?\n]{5,}?\?)\s*(?:\n|$)',
                r'"([^"]{5,}?\?)"',
                r"'([^']{5,}?\?)'",
                r'(?:preguntas?[^\n]*:.*?)([A-Z][^.!?\n]{5,}?\?)',
            ]
        }
        
        patterns = question_patterns.get(language, question_patterns["fr"])
        extracted_questions = []
        
        # Essayer chaque pattern dans l'ordre de priorité
        for pattern in patterns:
            try:
                matches = re.findall(pattern, response, re.MULTILINE | re.IGNORECASE)
                for match in matches:
                    question = match.strip()
                    # Validation qualité basique
                    if (len(question.split()) >= 4 and  # Au moins 4 mots
                        question not in extracted_questions and  # Pas de doublon
                        len(question) <= 150):  # Pas trop long
                        extracted_questions.append(question)
                        
                if extracted_questions:
                    break  # Arrêter au premier pattern qui fonctionne
                    
            except re.error as e:
                logger.error(f"❌ [Question Extraction] Erreur regex: {e}")
                continue
        
        # Limiter et déduplication finale
        unique_questions = []
        for q in extracted_questions[:4]:  # Max 4 questions
            if q not in unique_questions:
                unique_questions.append(q)
        
        return unique_questions
        
    except Exception as e:
        logger.error(f"❌ [Question Extraction] Erreur: {e}")
        return []

# =============================================================================
# VALIDATION MULTICRITÈRES RENFORCÉE
# =============================================================================

def validate_dynamic_questions(questions: List[str], user_question: str = "", language: str = "fr", 
                              missing_entities: List[str] = None) -> Tuple[float, List[str]]:
    """
    Valide la qualité des questions générées avec système de scoring multicritères renforcé
    
    Args:
        questions: Liste des questions à valider
        user_question: Question originale de l'utilisateur
        language: Langue pour les critères de validation
        missing_entities: Entités manquantes à couvrir
    
    Returns:
        Tuple[float, List[str]]: (score_qualité_global, questions_validées)
    """
    
    # Validation d'entrée stricte
    if not questions or not isinstance(questions, list):
        logger.warning("🔧 [Question Validation Enhanced] Format invalide ou liste vide")
        return 0.0, []
    
    # Normaliser missing_entities
    if missing_entities is None:
        missing_entities = []
    
    logger.info(f"🔧 [Question Validation Enhanced] Début validation - {len(questions)} questions, {len(missing_entities)} entités manquantes")
    
    # Critères de validation par langue avec patterns étendus
    quality_criteria = {
        "fr": {
            "min_words": 4,
            "max_length": 120,
            "avoid_words": ["exemple", "par exemple", "etc", "quelque chose", "généralement", "habituellement", "souvent", "parfois"],
            "generic_phrases": ["pouvez-vous préciser", "pourriez-vous dire", "voulez-vous expliquer", "est-ce que vous"],
            "required_pattern": r'\?$',  # Doit finir par un point d'interrogation
            "domain_words": ["race", "souche", "âge", "poids", "température", "symptôme", "alimentation", "poulet", "volaille", "élevage", "troupeau"],
            "normalization_patterns": [
                (r'\s+', ' '),  # Espaces multiples → espace simple
                (r'\.+$', ''),  # Points finaux superflus
                (r'\s*\?\s*$', '?'),  # Normaliser point d'interrogation
                (r'^\s*-\s*', ''),  # Tirets en début
                (r'^\s*\d+\.\s*', ''),  # Numérotation en début
                (r'^\s*[•\-\*]\s*', '')  # Puces en début
            ],
            "entity_keywords": {
                "race": ["race", "souche", "lignée", "ross", "cobb", "hubbard", "breed", "strain", "ligne génétique"],
                "âge": ["âge", "jour", "semaine", "mois", "vieux", "jeune", "ancienneté", "stade", "période"],
                "sexe": ["sexe", "mâle", "femelle", "coq", "poule", "mixte", "genre", "reproduction"],
                "poids": ["poids", "gramme", "kilo", "pèse", "lourd", "masse", "pesée", "balance"],
                "symptômes": ["symptôme", "signe", "maladie", "problème", "observation", "comportement", "anomalie"],
                "conditions": ["température", "condition", "environnement", "bâtiment", "ambiance", "climat", "ventilation"],
                "nombre": ["nombre", "combien", "quantité", "troupeau", "lot", "effectif", "densité"],
                "durée": ["depuis", "pendant", "durée", "combien de temps", "chronologie", "temporalité"]
            }
        },
        "en": {
            "min_words": 4,
            "max_length": 120,
            "avoid_words": ["example", "for example", "etc", "something", "generally", "usually", "often", "sometimes"],
            "generic_phrases": ["could you specify", "can you tell", "would you explain", "do you"],
            "required_pattern": r'\?$',
            "domain_words": ["breed", "strain", "age", "weight", "temperature", "symptom", "feeding", "chicken", "poultry", "farming", "flock"],
            "normalization_patterns": [
                (r'\s+', ' '),
                (r'\.+$', ''),
                (r'\s*\?\s*$', '?'),
                (r'^\s*-\s*', ''),
                (r'^\s*\d+\.\s*', ''),
                (r'^\s*[•\-\*]\s*', '')
            ],
            "entity_keywords": {
                "breed": ["breed", "strain", "line", "ross", "cobb", "hubbard", "genetic line", "variety"],
                "age": ["age", "day", "week", "month", "old", "young", "stage", "period", "time"],
                "sex": ["sex", "male", "female", "rooster", "hen", "mixed", "gender", "breeding"],
                "weight": ["weight", "gram", "kilo", "weigh", "heavy", "mass", "weighing", "scale"],
                "symptoms": ["symptom", "sign", "disease", "problem", "observation", "behavior", "anomaly"],
                "conditions": ["temperature", "condition", "environment", "building", "atmosphere", "climate", "ventilation"],
                "number": ["number", "how many", "quantity", "flock", "batch", "density", "count"],
                "duration": ["since", "for", "duration", "how long", "chronology", "temporality"]
            }
        },
        "es": {
            "min_words": 4,
            "max_length": 120,
            "avoid_words": ["ejemplo", "por ejemplo", "etc", "algo", "generalmente", "usualmente", "a menudo", "a veces"],
            "generic_phrases": ["podría especificar", "puede decir", "querría explicar", "está usted"],
            "required_pattern": r'\?$',
            "domain_words": ["raza", "cepa", "edad", "peso", "temperatura", "síntoma", "alimentación", "pollo", "ave", "cría", "lote"],
            "normalization_patterns": [
                (r'\s+', ' '),
                (r'\.+$', ''),
                (r'\s*\?\s*$', '?'),
                (r'^\s*-\s*', ''),
                (r'^\s*\d+\.\s*', ''),
                (r'^\s*[•\-\*]\s*', '')
            ],
            "entity_keywords": {
                "raza": ["raza", "cepa", "línea", "ross", "cobb", "hubbard", "línea genética", "variedad"],
                "edad": ["edad", "día", "semana", "mes", "viejo", "joven", "etapa", "período", "tiempo"],
                "sexo": ["sexo", "macho", "hembra", "gallo", "gallina", "mixto", "género", "reproducción"],
                "peso": ["peso", "gramo", "kilo", "pesa", "pesado", "masa", "pesaje", "balanza"],
                "síntomas": ["síntoma", "signo", "enfermedad", "problema", "observación", "comportamiento", "anomalía"],
                "condiciones": ["temperatura", "condición", "ambiente", "edificio", "atmósfera", "clima", "ventilación"],
                "número": ["número", "cuántos", "cantidad", "lote", "grupo", "densidad", "conteo"],
                "duración": ["desde", "por", "duración", "cuánto tiempo", "cronología", "temporalidad"]
            }
        }
    }
    
    criteria = quality_criteria.get(language, quality_criteria["fr"])
    
    # ÉTAPE 1: Nettoyage et normalisation avancée
    def normalize_question(question: str) -> str:
        """Normalise une question selon les patterns définis"""
        if not isinstance(question, str):
            return ""
        
        # Trim initial
        normalized = question.strip()
        
        # Appliquer les patterns de normalisation dans l'ordre
        for pattern, replacement in criteria["normalization_patterns"]:
            try:
                normalized = re.sub(pattern, replacement, normalized)
            except re.error as e:
                logger.warning(f"⚠️ [Normalization] Erreur pattern {pattern}: {e}")
                continue
        
        # Trim final et vérification
        normalized = normalized.strip()
        
        # S'assurer qu'elle finit par un point d'interrogation
        if normalized and not normalized.endswith('?'):
            normalized += '?'
        
        return normalized
    
    cleaned_questions = []
    seen_normalized = set()
    
    for i, question in enumerate(questions):
        try:
            if not isinstance(question, str):
                logger.debug(f"🔧 [Normalization] Question {i} n'est pas une string: {type(question)}")
                continue
            
            # Normalisation complète
            q_normalized = normalize_question(question)
            
            if not q_normalized or len(q_normalized) < 3:
                logger.debug(f"🔧 [Normalization] Question {i} trop courte après normalisation")
                continue
            
            # Vérification unicité (insensible à la casse et espaces)
            q_comparison = re.sub(r'\s+', ' ', q_normalized.lower().strip())
            
            if q_comparison in seen_normalized:
                logger.debug(f"🔧 [Normalization] Doublon détecté: {q_normalized}")
                continue
            
            # Filtrage de base
            word_count = len(q_normalized.split())
            if word_count < criteria["min_words"] or len(q_normalized) > criteria["max_length"]:
                logger.debug(f"🔧 [Normalization] Question {i} hors limites: {word_count} mots, {len(q_normalized)} chars")
                continue
            
            # Éviter phrases trop génériques
            q_lower = q_normalized.lower()
            if any(phrase in q_lower for phrase in criteria["generic_phrases"]):
                logger.debug(f"🔧 [Normalization] Question {i} trop générique: {q_normalized}")
                continue
            
            seen_normalized.add(q_comparison)
            cleaned_questions.append(q_normalized)
            
        except Exception as e:
            logger.error(f"❌ [Normalization] Erreur question {i}: {e}")
            continue
    
    logger.info(f"🔧 [Normalization] Après nettoyage: {len(cleaned_questions)}/{len(questions)} questions")
    
    # ÉTAPE 2: Scoring multicritères avec couverture d'entités
    def calculate_entity_coverage(question: str, missing_entities: List[str]) -> Tuple[float, List[str]]:
        """Calcule la couverture des entités manquantes par une question"""
        if not missing_entities:
            return 1.0, []  # Score parfait si pas d'entités spécifiques
        
        question_lower = question.lower()
        covered_entities = []
        
        for entity in missing_entities:
            entity_keywords = criteria["entity_keywords"].get(entity, [entity])
            if any(keyword in question_lower for keyword in entity_keywords):
                covered_entities.append(entity)
        
        coverage_score = len(covered_entities) / len(missing_entities) if missing_entities else 1.0
        return coverage_score, covered_entities
    
    scored_questions = []
    all_covered_entities = set()
    
    for question in cleaned_questions:
        try:
            score = 0.0
            question_lower = question.lower()
            
            # Critère 1: Structure de question valide (20%)
            if re.search(criteria["required_pattern"], question):
                score += 0.20
            
            # Critère 2: Absence de mots vagues (15%)
            if not any(word in question_lower for word in criteria["avoid_words"]):
                score += 0.15
            
            # Critère 3: Présence de mots du domaine (20%)
            domain_word_count = sum(1 for word in criteria["domain_words"] if word in question_lower)
            if domain_word_count > 0:
                score += min(0.20, domain_word_count * 0.05)
            
            # Critère 4: Couverture des entités manquantes (35% - RENFORCÉ)
            entity_coverage, covered_entities = calculate_entity_coverage(question, missing_entities)
            score += entity_coverage * 0.35
            
            # Tracking des entités couvertes globalement
            all_covered_entities.update(covered_entities)
            
            # Critère 5: Bonus qualité linguistique (10%)
            if (len(question.split()) >= 6 and  # Question détaillée
                any(char.isupper() for char in question) and  # Majuscules présentes
                not any(bad_word in question_lower for bad_word in ["quelque chose", "something", "algo"])):
                score += 0.10
            
            scored_questions.append((question, min(score, 1.0), covered_entities))
            
        except Exception as e:
            logger.error(f"❌ [Scoring] Erreur: {e}")
            continue
    
    # ÉTAPE 3: Vérification couverture globale des entités
    uncovered_entities = set(missing_entities) - all_covered_entities
    coverage_penalty = 0.0
    
    if missing_entities and uncovered_entities:
        coverage_rate = len(all_covered_entities) / len(missing_entities)
        coverage_penalty = (1 - coverage_rate) * 0.3  # Pénalité jusqu'à 30%
        logger.warning(f"⚠️ [Entity Coverage] Entités non couvertes: {uncovered_entities}")
        logger.info(f"📊 [Entity Coverage] Taux couverture: {coverage_rate:.2f} ({len(all_covered_entities)}/{len(missing_entities)})")
    else:
        logger.info(f"✅ [Entity Coverage] Toutes les entités couvertes: {all_covered_entities}")
    
    # ÉTAPE 4: Sélection et optimisation finale
    scored_questions.sort(key=lambda x: x[1], reverse=True)
    
    # Si couverture incomplète, prioriser questions couvrant entités manquantes
    if uncovered_entities:
        logger.info("🔄 [Optimization] Réorganisation pour maximiser couverture entités")
        
        # Séparer questions par couverture d'entités non couvertes
        covering_uncovered = []
        others = []
        
        for question, score, covered in scored_questions:
            if any(entity in uncovered_entities for entity in covered):
                covering_uncovered.append((question, score, covered))
            else:
                others.append((question, score, covered))
        
        # Prioriser celles qui couvrent les entités manquantes
        scored_questions = covering_uncovered + others
        logger.info(f"🔄 [Optimization] {len(covering_uncovered)} questions prioritaires pour entités manquantes")
    
    # Filtrer par seuil de qualité ajusté selon couverture
    base_threshold = 0.55
    adjusted_threshold = max(0.35, base_threshold - coverage_penalty)  # Seuil plus souple si couverture partielle
    
    high_quality_questions = [(q, s, c) for q, s, c in scored_questions if s >= adjusted_threshold]
    
    # Limiter à 4 questions maximum en optimisant la diversité d'entités
    final_questions = []
    final_covered_entities = set()
    
    for question, score, covered in high_quality_questions:
        if len(final_questions) >= 4:
            break
        
        # Ajouter si apporte une nouvelle entité ou si moins de 2 questions
        brings_new_entity = any(entity not in final_covered_entities for entity in covered)
        if len(final_questions) < 2 or brings_new_entity:
            final_questions.append(question)
            final_covered_entities.update(covered)
    
    # Calculer score global avec pénalité de couverture
    if high_quality_questions:
        base_score = sum(score for _, score, _ in high_quality_questions[:len(final_questions)]) / len(final_questions)
        global_score = max(0.0, base_score - coverage_penalty)
    else:
        global_score = 0.0
    
    # Logging détaillé des résultats
    logger.info(f"✅ [Validation Enhanced] "
               f"Score global: {global_score:.2f} (base: {base_score:.2f}, pénalité: {coverage_penalty:.2f}), "
               f"Questions finales: {len(final_questions)}/{len(questions)}")
    
    if missing_entities:
        logger.info(f"📊 [Entity Analysis] "
                   f"Entités requises: {missing_entities}, "
                   f"Entités couvertes: {list(final_covered_entities)}, "
                   f"Taux final: {len(final_covered_entities)/len(missing_entities):.2f}")
    
    if final_questions:
        for i, q in enumerate(final_questions, 1):
            logger.debug(f"  Question {i}: {q}")
    
    return global_score, final_questions

# =============================================================================
# FONCTION PRINCIPALE D'AUTO-CLARIFICATION
# =============================================================================

def auto_clarify_if_needed(question: str, conversation_context: str, language: str = "fr") -> Optional[Dict[str, Any]]:
    """
    Fonction centralisée pour l'auto-clarification avec sélection dynamique et validation renforcée
    
    Args:
        question: Question de l'utilisateur
        conversation_context: Contexte de la conversation
        language: Langue de traitement
    
    Returns:
        Dict si clarification nécessaire avec métadonnées complètes, None sinon
    """
    
    try:
        # Calculer score de complétude de base
        completeness_score = _calculate_basic_completeness_score(question, conversation_context, language)
        
        logger.info(f"🔧 [Auto Clarify] Score complétude: {completeness_score:.2f}")
        
        # Seuil pour déclencher clarification (ajusté)
        if completeness_score < 0.6:
            logger.info("🔧 [Auto Clarify] Clarification nécessaire - génération questions")
            
            # Détecter entités manquantes avec patterns étendus
            missing_entities = detect_missing_entities(question, language)
            
            # Sélectionner le template approprié avec détection GPT
            prompt = select_clarification_prompt(question, missing_entities, conversation_context, language)
            
            # Tenter génération dynamique avec template sélectionné
            questions = _generate_clarification_questions_with_dynamic_prompt(prompt, language)
            
            # Validation renforcée avec scoring multicritères
            score, validated_questions = validate_dynamic_questions(questions, question, language, missing_entities)
            
            if score >= 0.55 and validated_questions:
                return {
                    "type": "clarification_needed",
                    "message": _get_clarification_intro_message(language),
                    "questions": validated_questions,
                    "completeness_score": completeness_score,
                    "generation_method": "dynamic_template_selection_validated",
                    "missing_entities": missing_entities,
                    "template_used": "specific" if len(missing_entities) <= 3 else "generic",
                    "validation_score": score,
                    "questions_filtered": len(questions) - len(validated_questions) if questions else 0,
                    "ai_topic_detection": True,
                    "processing_quality": "high"
                }
            else:
                logger.warning(f"🔧 [Auto Clarify] Score validation insuffisant ({score:.2f}) - fallback")
                
                # Fallback avec questions statiques optimisées
                fallback_questions = _get_fallback_questions_by_type(question, language)
                fallback_score, validated_fallback = validate_dynamic_questions(
                    fallback_questions, question, language, missing_entities
                )
                
                if validated_fallback:
                    return {
                        "type": "clarification_needed", 
                        "message": _get_clarification_intro_message(language),
                        "questions": validated_fallback,
                        "completeness_score": completeness_score,
                        "generation_method": "fallback_with_validation",
                        "missing_entities": missing_entities,
                        "template_used": "fallback",
                        "validation_score": fallback_score,
                        "ai_topic_detection": False,
                        "processing_quality": "fallback"
                    }
                else:
                    logger.warning("🔧 [Auto Clarify] Même le fallback a échoué")
                
    except Exception as e:
        logger.error(f"❌ [Auto Clarify] Erreur génération questions: {e}")
    
    return None

def _calculate_basic_completeness_score(question: str, conversation_context: str, language: str = "fr") -> float:
    """Calcule un score de complétude avec critères étendus"""
    
    try:
        score = 0.0
        
        if not isinstance(question, str) or len(question.strip()) == 0:
            return 0.0
        
        question_clean = question.strip()
        question_lower = question_clean.lower()
        
        # Score de base selon la longueur (30%)
        question_length = len(question_clean)
        if question_length > 80:
            score += 0.30
        elif question_length > 40:
            score += 0.20
        elif question_length > 20:
            score += 0.10
        
        # Présence de race spécifique (25%)
        specific_breeds = ["ross 308", "cobb 500", "hubbard", "arbor acres"]
        if any(breed in question_lower for breed in specific_breeds):
            score += 0.25
        elif any(word in question_lower for word in ["poulet", "chicken", "pollo", "volaille", "poultry", "ave"]):
            score += 0.10
        
        # Présence d'âge précis (20%)
        age_patterns = [r'\d+\s*(?:jour|day|día)s?', r'\d+\s*(?:semaine|week|semana)s?']
        if any(re.search(pattern, question_lower) for pattern in age_patterns):
            score += 0.20
        
        # Présence de données numériques (10%)
        if re.search(r'\d+', question_clean):
            score += 0.10
        
        # Présence de contexte spécialisé (10%)
        specialized_terms = {
            "fr": ["symptôme", "diagnostic", "protocole", "ration", "vaccination", "incubation"],
            "en": ["symptom", "diagnosis", "protocol", "ration", "vaccination", "incubation"],
            "es": ["síntoma", "diagnóstico", "protocolo", "ración", "vacunación", "incubación"]
        }
        
        terms = specialized_terms.get(language, specialized_terms["fr"])
        if any(term in question_lower for term in terms):
            score += 0.10
        
        # Contexte conversationnel disponible (5%)
        if conversation_context and isinstance(conversation_context, str) and len(conversation_context.strip()) > 30:
            score += 0.05
        
        return min(score, 1.0)
        
    except Exception as e:
        logger.error(f"❌ [Completeness Score] Erreur calcul: {e}")
        return 0.0

def _get_fallback_questions_by_type(question: str, language: str = "fr") -> List[str]:
    """Questions de fallback optimisées selon le type détecté"""
    
    try:
        if not isinstance(question, str):
            return []
        
        question_lower = question.lower()
        
        # Détection améliorée du type de question
        is_weight = any(word in question_lower for word in ["poids", "weight", "peso", "pèse", "weigh", "pesa"])
        is_health = any(word in question_lower for word in ["maladie", "disease", "enfermedad", "mort", "death", "muerte", "symptôme", "symptom", "síntoma"])
        is_growth = any(word in question_lower for word in ["croissance", "growth", "crecimiento", "développement", "development", "desarrollo"])
        is_feeding = any(word in question_lower for word in ["alimentation", "feeding", "alimentación", "nourriture", "food", "comida"])
        
        fallback_questions = {
            "fr": {
                "weight": [
                    "Quelle race ou souche spécifique élevez-vous (Ross 308, Cobb 500, etc.) ?",
                    "Quel âge ont actuellement vos poulets (en jours précis) ?",
                    "S'agit-il de mâles, femelles, ou d'un troupeau mixte ?",
                    "Dans quelles conditions d'élevage sont-ils (température, densité) ?"
                ],
                "health": [
                    "Quelle race ou souche élevez-vous ?",
                    "Quel âge ont vos volailles actuellement ?",
                    "Quels symptômes spécifiques observez-vous ?",
                    "Depuis combien de temps ces problèmes sont-ils apparus ?"
                ],
                "growth": [
                    "Quelle race ou souche spécifique élevez-vous ?",
                    "Quel âge ont-ils actuellement en jours ?",
                    "Quelles sont les conditions d'élevage actuelles ?",
                    "Quelle est leur alimentation actuelle ?"
                ],
                "feeding": [
                    "Quel âge ont vos volailles ?",
                    "Quelle race ou souche élevez-vous ?",
                    "Quel type d'aliment utilisez-vous actuellement ?",
                    "Quels sont vos objectifs de performance ?"
                ],
                "general": [
                    "Pouvez-vous préciser la race ou souche de vos volailles ?",
                    "Quel âge ont actuellement vos animaux ?",
                    "Dans quel contexte d'élevage vous trouvez-vous ?",
                    "Quel est votre objectif ou problème principal ?"
                ]
            },
            "en": {
                "weight": [
                    "What specific breed or strain are you raising (Ross 308, Cobb 500, etc.)?",
                    "What is the current age of your chickens (in precise days)?",
                    "Are these males, females, or a mixed flock?",
                    "What are the current housing conditions (temperature, density)?"
                ],
                "health": [
                    "What breed or strain are you raising?",
                    "What is the current age of your poultry?",
                    "What specific symptoms are you observing?",
                    "How long have these problems been present?"
                ],
                "growth": [
                    "What specific breed or strain are you raising?",
                    "What is their current age in days?",
                    "What are the current housing conditions?",
                    "What is their current feeding program?"
                ],
                "feeding": [
                    "What age are your birds?",
                    "What breed or strain are you raising?",
                    "What type of feed are you currently using?",
                    "What are your performance objectives?"
                ],
                "general": [
                    "Could you specify the breed or strain of your poultry?",
                    "What age are your animals currently?",
                    "What farming context are you in?",
                    "What is your main objective or problem?"
                ]
            },
            "es": {
                "weight": [
                    "¿Qué raza o cepa específica está criando (Ross 308, Cobb 500, etc.)?",
                    "¿Cuál es la edad actual de sus pollos (en días precisos)?",
                    "¿Son machos, hembras, o un lote mixto?",
                    "¿Cuáles son las condiciones actuales de alojamiento (temperatura, densidad)?"
                ],
                "health": [
                    "¿Qué raza o cepa está criando?",
                    "¿Cuál es la edad actual de sus aves?",
                    "¿Qué síntomas específicos está observando?",
                    "¿Desde cuándo están presentes estos problemas?"
                ],
                "growth": [
                    "¿Qué raza o cepa específica está criando?",
                    "¿Cuál es su edad actual en días?",
                    "¿Cuáles son las condiciones actuales de alojamiento?",
                    "¿Cuál es su programa de alimentación actual?"
                ],
                 "feeding": [
                    "¿Qué edad tienen sus aves?",
                    "¿Qué raza o cepa está criando?",
                    "¿Qué tipo de alimento está usando actualmente?",
                    "¿Cuáles son sus objetivos de rendimiento?"
                ],
                "general": [
                    "¿Podría especificar la raza o cepa de sus aves?",
                    "¿Qué edad tienen actualmente sus animales?",
                    "¿En qué contexto de cría se encuentra?",
                    "¿Cuál es su objetivo o problema principal?"
                ]
            }
        }
        
        # Déterminer le type de question et retourner les questions appropriées
        if is_weight:
            return fallback_questions[language]["weight"]
        elif is_health:
            return fallback_questions[language]["health"]
        elif is_growth:
            return fallback_questions[language]["growth"]
        elif is_feeding:
            return fallback_questions[language]["feeding"]
        else:
            return fallback_questions[language]["general"]
            
    except Exception as e:
        logger.error(f"❌ [Fallback Questions] Erreur: {e}")
        return [
            _get_clarification_intro_message(language),
            "Pouvez-vous préciser votre question ?",
            "Quel est le contexte exact ?",
            "Quelles informations manquent ?"
        ]

def _get_clarification_intro_message(language: str = "fr") -> str:
    """Messages d'introduction pour clarification selon la langue"""
    
    intro_messages = {
        "fr": "Pour vous donner une réponse précise, j'ai besoin de quelques précisions :",
        "en": "To give you a precise answer, I need some clarifications:",
        "es": "Para darle una respuesta precisa, necesito algunas aclaraciones:"
    }
    
    return intro_messages.get(language, intro_messages["fr"])

# =============================================================================
# FONCTION DE TEST ET VALIDATION
# =============================================================================

def test_clarification_system():
    """Fonction de test pour vérifier le bon fonctionnement du système"""
    try:
        logger.info("🧪 [Test Clarification System] Début des tests")
        
        # Test détection sujet
        test_questions = [
            "Mes poulets Ross 308 de 21 jours perdent du poids",
            "My laying hens stopped producing eggs",
            "Mis pollos están enfermos"
        ]
        
        for question in test_questions:
            try:
                topic = detect_topic_with_gpt(question, "fr")
                logger.info(f"✅ [Test] Question: '{question}' → Sujet: {topic}")
            except Exception as e:
                logger.error(f"❌ [Test] Erreur: {e}")
        
        logger.info("🧪 [Test Clarification System] Tests terminés")
        return True
        
    except Exception as e:
        logger.error(f"❌ [Test Clarification System] Erreur: {e}")
        return False

# =============================================================================
# INITIALISATION ET EXPORT
# =============================================================================

# Test du système au chargement du module
if __name__ == "__main__":
    test_clarification_system()

logger.info("✅ [Expert Clarification Service] Module chargé avec succès")
logger.info("🔧 [Expert Clarification Service] Fonctions disponibles:")
logger.info("   - detect_topic_with_gpt()")
logger.info("   - detect_missing_entities()")
logger.info("   - select_clarification_prompt()")
logger.info("   - auto_clarify_if_needed()")
logger.info("   - validate_dynamic_questions()")

# Export des fonctions principales
__all__ = [
    'detect_topic_with_gpt',
    'detect_missing_entities', 
    'select_clarification_prompt',
    'auto_clarify_if_needed',
    'validate_dynamic_questions',
    'TOPIC_DETECTION_PROMPT',
    'CLARIFICATION_TEMPLATES'
]