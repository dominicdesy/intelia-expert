# Module amélioré: rag_context_enhancer.py
# Améliore le contexte conversationnel pour le RAG avec sélection multi-variantes

import re
import logging
from typing import Dict, List, Optional, Tuple, Any

logger = logging.getLogger(__name__)

class RAGContextEnhancer:
    """Améliore le contexte conversationnel pour optimiser les requêtes RAG avec sélection multi-variantes"""
    
    def __init__(self):
        # Patterns pour détecter les références contextuelles
        self.pronoun_patterns = {
            "fr": [
                r'\b(son|sa|ses|leur|leurs)\s+(poids|âge|croissance|développement)',
                r'\b(ils|elles)\s+(pèsent|grandissent|se développent)',
                r'\b(qu\'?est-ce que|quel est)\s+(son|sa|ses|leur)',
                r'\b(combien)\s+(pèsent-ils|font-ils|mesurent-ils)'
            ],
            "en": [
                r'\b(their|its)\s+(weight|age|growth|development)',
                r'\b(they)\s+(weigh|grow|develop)',
                r'\b(what is|how much is)\s+(their|its)',
                r'\b(how much do they)\s+(weigh|measure)'
            ],
            "es": [
                r'\b(su|sus)\s+(peso|edad|crecimiento|desarrollo)',
                r'\b(ellos|ellas)\s+(pesan|crecen|se desarrollan)',
                r'\b(cuál es|cuánto es)\s+(su|sus)',
                r'\b(cuánto)\s+(pesan|miden)'
            ]
        }
        
        # Entités importantes à extraire du contexte
        self.key_entities = ["breed", "age", "weight", "housing", "symptoms", "feed", "environment"]
    
    def enhance_question_for_rag(
        self, 
        question: str, 
        conversation_context: str, 
        language: str = "fr",
        missing_entities: List[str] = None
    ) -> Dict[str, Any]:
        """
        Améliore une question pour le RAG en utilisant le contexte conversationnel
        Génère plusieurs variantes et sélectionne la meilleure
        
        Args:
            question: Question originale
            conversation_context: Contexte conversationnel
            language: Langue
            missing_entities: Liste des entités manquantes (optionnel)
        
        Returns:
            Dict contenant:
            - question: Meilleure question optimisée pour RAG
            - missing_entities: Liste des entités manquantes identifiées
            - context_entities: Dictionnaire des entités extraites du contexte
            - enhancement_info: Métadonnées sur les améliorations appliquées
        """
        
        # Initialiser le résultat structuré
        result = {
            "question": question,  # Sera remplacée par la meilleure variante
            "missing_entities": missing_entities or [],
            "context_entities": {},
            "enhancement_info": {
                "pronoun_detected": False,
                "question_enriched": False,
                "original_question": question,
                "technical_context_added": False,
                "missing_context_added": False,
                "variants_tested": [],
                "best_variant_score": 0.0,
                "variant_selection_method": "entity_coverage"
            }
        }
        
        # 1. Détecter les pronoms/références contextuelles
        has_pronouns = self._detect_contextual_references(question, language)
        if has_pronouns:
            result["enhancement_info"]["pronoun_detected"] = True
            logger.info(f"🔍 [RAG Context] Pronoms détectés dans: '{question}'")
        
        # 2. Extraire entités du contexte
        context_entities = self._extract_context_entities(conversation_context)
        result["context_entities"] = context_entities
        
        if context_entities:
            logger.info(f"📊 [RAG Context] Entités contextuelles: {context_entities}")
        
        # 3. Identifier entités manquantes automatiquement si non spécifiées
        if not result["missing_entities"]:
            result["missing_entities"] = self._identify_missing_entities(
                question, context_entities, language
            )
        
        # 4. Générer plusieurs variantes enrichies
        variants = self._generate_question_variants(
            question, context_entities, language, result["missing_entities"]
        )
        
        result["enhancement_info"]["variants_tested"] = variants
        logger.info(f"🎯 [RAG Context] {len(variants)} variantes générées")
        
        # 5. Sélectionner la meilleure variante
        if variants:
            best_variant = self._select_best_variant(variants, context_entities)
            best_score = self._score_variant(best_variant, context_entities)
            
            result["question"] = best_variant
            result["enhancement_info"]["question_enriched"] = (best_variant != question)
            result["enhancement_info"]["best_variant_score"] = best_score
            
            logger.info(f"✨ [RAG Context] Meilleure variante sélectionnée (score: {best_score:.2f}): '{best_variant}'")
        else:
            # Fallback si aucune variante générée
            result["question"] = question
            result["enhancement_info"]["variants_tested"] = [question]
        
        return result
    
    def _generate_question_variants(
        self, 
        question: str, 
        context_entities: Dict[str, str], 
        language: str,
        missing_entities: List[str]
    ) -> List[str]:
        """Génère plusieurs variantes enrichies de la question"""
        
        variants = []
        
        # Variante 1: Question originale (baseline)
        variants.append(question)
        
        # Variante 2: Question enrichie avec remplacement des pronoms
        if context_entities:
            enriched_question = self._build_enriched_question(question, context_entities, language)
            if enriched_question != question:
                variants.append(enriched_question)
        
        # Variante 3: Question + contexte technique inline
        technical_context = self._build_technical_context(context_entities, language)
        if technical_context:
            variants.append(f"{question} - Infos: {technical_context}")
        
        # Variante 4: Question avec entités entre parenthèses
        if context_entities:
            entity_values = [v for v in context_entities.values() if v]
            if entity_values:
                variants.append(f"{question} ({', '.join(entity_values)})")
        
        # Variante 5: Question avec contexte technique séparé
        if technical_context:
            variants.append(f"{question}\n\nContexte: {technical_context}")
        
        # Variante 6: Question enrichie + informations manquantes
        missing_context = self._build_missing_entities_context(missing_entities, language)
        if missing_context:
            variants.append(f"{question}\n\n{missing_context}")
        
        # Variante 7: Question complètement restructurée avec tout le contexte
        if context_entities and technical_context:
            full_context_question = self._build_full_context_question(
                question, context_entities, technical_context, language
            )
            if full_context_question != question:
                variants.append(full_context_question)
        
        # Variante 8: Question avec focus entités clés
        key_entities_context = self._build_key_entities_focus(context_entities, language)
        if key_entities_context:
            variants.append(f"{key_entities_context}: {question}")
        
        # Supprimer les doublons tout en préservant l'ordre
        seen = set()
        unique_variants = []
        for variant in variants:
            if variant not in seen:
                seen.add(variant)
                unique_variants.append(variant)
        
        return unique_variants
    
    def _select_best_variant(self, variants: List[str], context_entities: Dict[str, str]) -> str:
        """Sélectionne la meilleure variante basée sur le scoring"""
        
        if not variants:
            return ""
        
        if len(variants) == 1:
            return variants[0]
        
        # Calculer le score de chaque variante
        scores = {variant: self._score_variant(variant, context_entities) for variant in variants}
        
        # Sélectionner la variante avec le meilleur score
        best_variant = max(scores, key=scores.get)
        
        # Log des scores pour debug
        logger.debug(f"🎯 [RAG Context] Scores des variantes:")
        for variant, score in scores.items():
            logger.debug(f"  Score {score:.2f}: '{variant[:100]}{'...' if len(variant) > 100 else ''}'")
        
        return best_variant
    
    def _score_variant(self, variant: str, context_entities: Dict[str, str]) -> float:
        """
        Score une variante basée sur la couverture des entités et d'autres facteurs
        
        Args:
            variant: Variante à scorer
            context_entities: Entités du contexte
        
        Returns:
            Score entre 0.0 et 1.0+ (peut dépasser 1.0 avec bonus)
        """
        
        if not variant:
            return 0.0
        
        variant_lower = variant.lower()
        score = 0.0
        
        # 1. Score de base: couverture des entités (40% du score)
        entity_coverage = 0.0
        if context_entities:
            entities_found = sum(1 for entity_value in context_entities.values() 
                               if entity_value and entity_value.lower() in variant_lower)
            entity_coverage = entities_found / len(context_entities)
        
        score += entity_coverage * 0.4
        
        # 2. Longueur optimale (20% du score)
        # Longueur idéale entre 100-300 caractères
        length_score = 0.0
        variant_length = len(variant)
        if 100 <= variant_length <= 300:
            length_score = 1.0
        elif variant_length < 100:
            length_score = variant_length / 100.0
        else:  # > 300
            length_score = max(0.0, 1.0 - (variant_length - 300) / 200.0)
        
        score += length_score * 0.2
        
        # 3. Présence de mots-clés techniques importants (20% du score)
        technical_keywords = [
            "race", "breed", "raza", "âge", "age", "edad", "poids", "weight", "peso",
            "jour", "day", "día", "semaine", "week", "semana", "gram", "kg",
            "symptôme", "symptom", "síntoma", "problème", "problem", "problema"
        ]
        
        keywords_found = sum(1 for keyword in technical_keywords if keyword in variant_lower)
        keyword_score = min(1.0, keywords_found / 5.0)  # Normalisé sur 5 mots-clés max
        
        score += keyword_score * 0.2
        
        # 4. Structure et lisibilité (10% du score)
        readability_score = 0.0
        
        # Bonus pour contexte structuré
        if "contexte:" in variant_lower or "infos:" in variant_lower:
            readability_score += 0.3
        
        # Bonus pour séparation claire
        if "\n\n" in variant:
            readability_score += 0.2
        
        # Bonus pour parenthèses informationnelles
        if "(" in variant and ")" in variant:
            readability_score += 0.1
        
        # Malus pour répétitions excessives
        words = variant_lower.split()
        if len(words) != len(set(words)):  # Il y a des répétitions
            word_repetition = 1.0 - (len(words) - len(set(words))) / len(words)
            readability_score *= word_repetition
        
        readability_score = min(1.0, readability_score)
        score += readability_score * 0.1
        
        # 5. Bonus spéciaux (10% du score)
        bonus_score = 0.0
        
        # Bonus pour mentions d'entités critiques
        critical_entities = ["ross 308", "cobb 500", "jour", "day", "kg", "gram"]
        for entity in critical_entities:
            if entity in variant_lower:
                bonus_score += 0.1
        
        # Bonus pour questions bien structurées
        if variant.endswith("?"):
            bonus_score += 0.05
        
        # Bonus pour contexte multilingue approprié
        language_indicators = {"fr": ["âge", "poids", "jour"], "en": ["age", "weight", "day"], "es": ["edad", "peso", "día"]}
        for lang, indicators in language_indicators.items():
            if any(indicator in variant_lower for indicator in indicators):
                bonus_score += 0.05
                break
        
        bonus_score = min(1.0, bonus_score)
        score += bonus_score * 0.1
        
        # Assurer que le score reste dans une plage raisonnable
        final_score = min(2.0, max(0.0, score))  # Entre 0.0 et 2.0
        
        return final_score
    
    def _build_full_context_question(
        self, 
        question: str, 
        context_entities: Dict[str, str], 
        technical_context: str, 
        language: str
    ) -> str:
        """Construit une question complètement restructurée avec tout le contexte"""
        
        # Templates pour questions complètes
        templates = {
            "fr": "Contexte: {technical_context}\n\nQuestion: {question}",
            "en": "Context: {technical_context}\n\nQuestion: {question}",
            "es": "Contexto: {technical_context}\n\nPregunta: {question}"
        }
        
        template = templates.get(language, templates["fr"])
        return template.format(technical_context=technical_context, question=question)
    
    def _build_key_entities_focus(self, context_entities: Dict[str, str], language: str) -> str:
        """Construit un focus sur les entités clés les plus importantes"""
        
        if not context_entities:
            return ""
        
        # Ordre de priorité des entités par importance
        priority_order = ["breed", "age", "weight", "symptoms"]
        
        # Sélectionner les 2-3 entités les plus importantes présentes
        key_entities = []
        for entity in priority_order:
            if entity in context_entities and context_entities[entity]:
                key_entities.append(context_entities[entity])
                if len(key_entities) >= 3:  # Limiter à 3 entités max
                    break
        
        if not key_entities:
            return ""
        
        # Templates par langue
        templates = {
            "fr": "Pour: {entities}",
            "en": "For: {entities}",
            "es": "Para: {entities}"
        }
        
        template = templates.get(language, templates["fr"])
        return template.format(entities=", ".join(key_entities))
    
    def _detect_contextual_references(self, question: str, language: str) -> bool:
        """Détecte si la question contient des pronoms/références contextuelles"""
        
        patterns = self.pronoun_patterns.get(language, self.pronoun_patterns["fr"])
        question_lower = question.lower()
        
        for pattern in patterns:
            if re.search(pattern, question_lower, re.IGNORECASE):
                logger.debug(f"🎯 [RAG Context] Pattern trouvé: {pattern}")
                return True
        
        return False
    
    def _extract_context_entities(self, context: str) -> Dict[str, str]:
        """Extrait les entités importantes du contexte conversationnel"""
        
        if not context:
            return {}
        
        entities = {}
        context_lower = context.lower()
        
        # Extraire race
        breed_patterns = [
            r'race[:\s]+([a-zA-Z0-9\s]+?)(?:\n|,|\.|\s|$)',
            r'breed[:\s]+([a-zA-Z0-9\s]+?)(?:\n|,|\.|\s|$)', 
            r'(ross\s*308|cobb\s*500|hubbard|arbor\s*acres)',
            r'poulets?\s+(ross\s*308|cobb\s*500)',
            r'chickens?\s+(ross\s*308|cobb\s*500)'
        ]
        
        for pattern in breed_patterns:
            match = re.search(pattern, context_lower, re.IGNORECASE)
            if match:
                entities["breed"] = match.group(1).strip()
                break
        
        # Extraire âge
        age_patterns = [
            r'âge[:\s]+(\d+\s*(?:jour|semaine|day|week)s?)',
            r'age[:\s]+(\d+\s*(?:jour|semaine|day|week)s?)',
            r'(\d+)\s*(?:jour|day)s?',
            r'(\d+)\s*(?:semaine|week)s?'
        ]
        
        for pattern in age_patterns:
            match = re.search(pattern, context_lower, re.IGNORECASE)
            if match:
                entities["age"] = match.group(1).strip()
                break
        
        # Extraire poids
        weight_patterns = [
            r'poids[:\s]+(\d+(?:\.\d+)?\s*[gk]?g?)',
            r'weight[:\s]+(\d+(?:\.\d+)?\s*[gk]?g?)',
            r'(\d+(?:\.\d+)?)\s*(?:gramme|gram|kg)s?'
        ]
        
        for pattern in weight_patterns:
            match = re.search(pattern, context_lower, re.IGNORECASE)
            if match:
                entities["weight"] = match.group(1).strip()
                break
        
        # Extraire conditions d'hébergement
        housing_patterns = [
            r'hébergement[:\s]+([^.\n]+)',
            r'housing[:\s]+([^.\n]+)',
            r'logement[:\s]+([^.\n]+)',
            r'barn[:\s]+([^.\n]+)'
        ]
        
        for pattern in housing_patterns:
            match = re.search(pattern, context_lower, re.IGNORECASE)
            if match:
                entities["housing"] = match.group(1).strip()
                break
        
        # Extraire symptômes
        symptoms_patterns = [
            r'symptômes?[:\s]+([^.\n]+)',
            r'symptoms?[:\s]+([^.\n]+)',
            r'problème[:\s]+([^.\n]+)',
            r'problem[:\s]+([^.\n]+)'
        ]
        
        for pattern in symptoms_patterns:
            match = re.search(pattern, context_lower, re.IGNORECASE)
            if match:
                entities["symptoms"] = match.group(1).strip()
                break
        
        return entities
    
    def _identify_missing_entities(
        self, 
        question: str, 
        context_entities: Dict[str, str], 
        language: str
    ) -> List[str]:
        """Identifie automatiquement les entités manquantes pertinentes pour la question"""
        
        missing = []
        question_lower = question.lower()
        
        # Mots-clés qui suggèrent le besoin de certaines entités
        entity_keywords = {
            "breed": ["race", "breed", "poulet", "chicken", "pollo", "type"],
            "age": ["âge", "age", "edad", "jour", "day", "semaine", "week", "old"],
            "weight": ["poids", "weight", "peso", "gram", "kg", "lourd", "heavy"],
            "housing": ["barn", "hébergement", "logement", "housing", "condition"],
            "symptoms": ["problème", "problem", "symptôme", "symptom", "malade", "sick"],
            "feed": ["alimentation", "feed", "alimento", "nutrition", "nourriture"],
            "environment": ["température", "temperature", "humidité", "humidity", "climat"]
        }
        
        # Vérifier quelles entités sont mentionnées dans la question mais absentes du contexte
        for entity, keywords in entity_keywords.items():
            if entity not in context_entities:  # Entité absente du contexte
                # Vérifier si des mots-clés relatifs sont dans la question
                if any(keyword in question_lower for keyword in keywords):
                    missing.append(entity)
        
        # Entités toujours utiles pour certains types de questions
        diagnostic_keywords = ["problème", "problem", "malade", "sick", "diagnostic", "symptom"]
        if any(keyword in question_lower for keyword in diagnostic_keywords):
            # Pour les questions de diagnostic, ces entités sont souvent importantes
            for entity in ["breed", "age", "symptoms"]:
                if entity not in context_entities and entity not in missing:
                    missing.append(entity)
        
        performance_keywords = ["croissance", "growth", "poids", "weight", "développement", "development"]
        if any(keyword in question_lower for keyword in performance_keywords):
            # Pour les questions de performance, ces entités sont importantes
            for entity in ["breed", "age", "feed"]:
                if entity not in context_entities and entity not in missing:
                    missing.append(entity)
        
        return missing
    
    def _build_enriched_question(
        self, 
        question: str, 
        context_entities: Dict[str, str], 
        language: str
    ) -> str:
        """Construit une question enrichie en remplaçant les pronoms par les entités contextuelles"""
        
        enriched = question
        
        # Templates par langue
        templates = {
            "fr": {
                "breed_age": "Pour des {breed} de {age}",
                "breed_only": "Pour des {breed}",
                "age_only": "Pour des poulets de {age}",
                "full_context": "Pour des {breed} de {age} pesant {weight}"
            },
            "en": {
                "breed_age": "For {breed} chickens at {age}",
                "breed_only": "For {breed} chickens", 
                "age_only": "For chickens at {age}",
                "full_context": "For {breed} chickens at {age} weighing {weight}"
            },
            "es": {
                "breed_age": "Para pollos {breed} de {age}",
                "breed_only": "Para pollos {breed}",
                "age_only": "Para pollos de {age}",
                "full_context": "Para pollos {breed} de {age} pesando {weight}"
            }
        }
        
        template_set = templates.get(language, templates["fr"])
        
        # Construire le préfixe contextuel (priorité au template le plus complet)
        context_prefix = ""
        if all(k in context_entities for k in ["breed", "age", "weight"]):
            context_prefix = template_set["full_context"].format(**context_entities)
        elif "breed" in context_entities and "age" in context_entities:
            context_prefix = template_set["breed_age"].format(**context_entities)
        elif "breed" in context_entities:
            context_prefix = template_set["breed_only"].format(breed=context_entities["breed"])
        elif "age" in context_entities:
            context_prefix = template_set["age_only"].format(age=context_entities["age"])
        
        if context_prefix:
            # Remplacer ou préfixer selon la structure de la question
            pronoun_words = ["son", "sa", "ses", "leur", "leurs", "their", "its", "su", "sus"]
            if any(word in question.lower() for word in pronoun_words):
                enriched = f"{context_prefix}, {question.lower()}"
            else:
                enriched = f"{context_prefix}: {question}"
        
        return enriched
    
    def _build_technical_context(self, entities: Dict[str, str], language: str) -> str:
        """Construit un contexte technique pour aider le RAG"""
        
        if not entities:
            return ""
        
        context_parts = []
        
        # Ordre de priorité pour l'affichage
        entity_order = ["breed", "age", "weight", "housing", "symptoms", "feed", "environment"]
        
        entity_labels = {
            "fr": {
                "breed": "Race", "age": "Âge", "weight": "Poids",
                "housing": "Hébergement", "symptoms": "Symptômes", 
                "feed": "Alimentation", "environment": "Environnement"
            },
            "en": {
                "breed": "Breed", "age": "Age", "weight": "Weight",
                "housing": "Housing", "symptoms": "Symptoms",
                "feed": "Feed", "environment": "Environment"
            },
            "es": {
                "breed": "Raza", "age": "Edad", "weight": "Peso",
                "housing": "Alojamiento", "symptoms": "Síntomas",
                "feed": "Alimentación", "environment": "Ambiente"
            }
        }
        
        labels = entity_labels.get(language, entity_labels["fr"])
        
        for entity in entity_order:
            if entity in entities:
                label = labels.get(entity, entity.capitalize())
                context_parts.append(f"{label}: {entities[entity]}")
        
        return " | ".join(context_parts)
    
    def _build_missing_entities_context(self, missing_entities: List[str], language: str) -> str:
        """Construit un contexte indiquant les entités manquantes pour guider le RAG"""
        
        if not missing_entities:
            return ""
        
        # Templates par langue pour indiquer les informations manquantes
        templates = {
            "fr": {
                "prefix": "Informations manquantes qui pourraient être pertinentes:",
                "entities": {
                    "breed": "race des animaux",
                    "age": "âge des animaux", 
                    "weight": "poids des animaux",
                    "housing": "conditions d'hébergement",
                    "symptoms": "symptômes observés",
                    "feed": "type d'alimentation",
                    "environment": "conditions environnementales"
                }
            },
            "en": {
                "prefix": "Missing information that could be relevant:",
                "entities": {
                    "breed": "animal breed",
                    "age": "animal age",
                    "weight": "animal weight", 
                    "housing": "housing conditions",
                    "symptoms": "observed symptoms",
                    "feed": "feed type",
                    "environment": "environmental conditions"
                }
            },
            "es": {
                "prefix": "Información faltante que podría ser relevante:",
                "entities": {
                    "breed": "raza de los animales",
                    "age": "edad de los animales",
                    "weight": "peso de los animales",
                    "housing": "condiciones de alojamiento", 
                    "symptoms": "síntomas observados",
                    "feed": "tipo de alimentación",
                    "environment": "condiciones ambientales"
                }
            }
        }
        
        template_set = templates.get(language, templates["fr"])
        prefix = template_set["prefix"]
        entity_names = template_set["entities"]
        
        # Construire la liste des entités manquantes
        missing_list = []
        for entity in missing_entities:
            if entity in entity_names:
                missing_list.append(entity_names[entity])
            else:
                missing_list.append(entity)  # Fallback au nom original
        
        if missing_list:
            return f"{prefix} {', '.join(missing_list)}"
        
        return ""

# Instance globale
rag_context_enhancer = RAGContextEnhancer()

def enhance_question_for_rag(
    question: str, 
    conversation_context: str, 
    language: str = "fr",
    missing_entities: List[str] = None
) -> Dict[str, Any]:
    """
    Fonction utilitaire pour améliorer une question pour le RAG
    Génère plusieurs variantes et retourne la meilleure
    
    Returns:
        Dict contenant:
        - question: Meilleure question optimisée pour RAG
        - missing_entities: Liste des entités manquantes identifiées
        - context_entities: Dictionnaire des entités extraites du contexte
        - enhancement_info: Métadonnées sur les améliorations appliquées (incluant variants_tested)
    """
    return rag_context_enhancer.enhance_question_for_rag(
        question, conversation_context, language, missing_entities
    )