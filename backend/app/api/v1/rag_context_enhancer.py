# Module amélioré: rag_context_enhancer.py
# Améliore le contexte conversationnel pour le RAG avec sélection multi-variantes
# VERSION CORRIGÉE - Errors fixed and improvements added

import re
import logging
from typing import Dict, List, Optional, Tuple, Any, Set

logger = logging.getLogger(__name__)

class RAGContextEnhancer:
    """Améliore le contexte conversationnel pour optimiser les requêtes RAG avec sélection multi-variantes"""
    
    def __init__(self):
        # Patterns pour détecter les références contextuelles - CORRIGÉ
        self.pronoun_patterns = {
            "fr": [
                r'\b(son|sa|ses|leur|leurs)\s+(poids|âge|croissance|développement)',
                r'\b(ils|elles)\s+(pèsent|grandissent|se\s+développent)',
                r'\b(qu\'?est-ce\s+que|quel\s+est)\s+(son|sa|ses|leur)',
                r'\b(combien)\s+(pèsent-ils|font-ils|mesurent-ils)',
                r'\b(ces|cette|ce)\s+(poulets?|animaux)',
                r'\b(ma|mes)\s+(poules?|poulets?|animaux)'
            ],
            "en": [
                r'\b(their|its)\s+(weight|age|growth|development)',
                r'\b(they)\s+(weigh|grow|develop)',
                r'\b(what\s+is|how\s+much\s+is)\s+(their|its)',
                r'\b(how\s+much\s+do\s+they)\s+(weigh|measure)',
                r'\b(these|this)\s+(chickens?|animals?)',
                r'\b(my)\s+(chickens?|animals?)'
            ],
            "es": [
                r'\b(su|sus)\s+(peso|edad|crecimiento|desarrollo)',
                r'\b(ellos|ellas)\s+(pesan|crecen|se\s+desarrollan)',
                r'\b(cuál\s+es|cuánto\s+es)\s+(su|sus)',
                r'\b(cuánto)\s+(pesan|miden)',
                r'\b(estos|estas|este|esta)\s+(pollos?|animales?)',
                r'\b(mis?)\s+(pollos?|animales?)'
            ]
        }
        
        # Entités importantes à extraire du contexte
        self.key_entities = ["breed", "age", "weight", "housing", "symptoms", "feed", "environment"]
        
        # AJOUT: Cache pour les patterns compilés (optimisation performance)
        self._compiled_patterns = {}
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Compile les patterns regex pour améliorer les performances"""
        for language, patterns in self.pronoun_patterns.items():
            self._compiled_patterns[language] = []
            for pattern in patterns:
                try:
                    compiled = re.compile(pattern, re.IGNORECASE)
                    self._compiled_patterns[language].append(compiled)
                except re.error as e:
                    logger.warning(f"Pattern regex invalide pour {language}: {pattern} - Erreur: {e}")
    
    def enhance_question_for_rag(
        self, 
        question: str, 
        conversation_context: str, 
        language: str = "fr",
        missing_entities: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Améliore une question pour le RAG en utilisant le contexte conversationnel
        Génère plusieurs variantes et sélectionne la meilleure
        
        Args:
            question: Question originale
            conversation_context: Contexte conversationnel
            language: Langue (doit être dans ['fr', 'en', 'es'])
            missing_entities: Liste des entités manquantes (optionnel)
        
        Returns:
            Dict contenant:
            - question: Meilleure question optimisée pour RAG
            - missing_entities: Liste des entités manquantes identifiées
            - context_entities: Dictionnaire des entités extraites du contexte
            - enhancement_info: Métadonnées sur les améliorations appliquées
        """
        
        # VALIDATION des entrées - AJOUT
        if not question or not isinstance(question, str):
            logger.error("Question invalide fournie")
            return self._get_empty_result(question or "")
        
        if not isinstance(conversation_context, str):
            conversation_context = str(conversation_context) if conversation_context else ""
        
        if language not in ['fr', 'en', 'es']:
            logger.warning(f"Langue non supportée: {language}, utilisation de 'fr' par défaut")
            language = 'fr'
        
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
        
        try:
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
            
        except Exception as e:
            logger.error(f"Erreur lors de l'amélioration de la question: {e}")
            # Retourner un résultat de fallback sécurisé
            result["question"] = question
            result["enhancement_info"]["variants_tested"] = [question]
            result["enhancement_info"]["error"] = str(e)
        
        return result
    
    def _get_empty_result(self, question: str) -> Dict[str, Any]:
        """Retourne un résultat vide sécurisé en cas d'erreur"""
        return {
            "question": question,
            "missing_entities": [],
            "context_entities": {},
            "enhancement_info": {
                "pronoun_detected": False,
                "question_enriched": False,
                "original_question": question,
                "technical_context_added": False,
                "missing_context_added": False,
                "variants_tested": [question] if question else [],
                "best_variant_score": 0.0,
                "variant_selection_method": "fallback"
            }
        }
    
    def _generate_question_variants(
        self, 
        question: str, 
        context_entities: Dict[str, str], 
        language: str,
        missing_entities: List[str]
    ) -> List[str]:
        """Génère plusieurs variantes enrichies de la question"""
        
        if not question:
            return []
        
        variants = []
        
        try:
            # Variante 1: Question originale (baseline)
            variants.append(question)
            
            # Variante 2: Question enrichie avec remplacement des pronoms
            if context_entities:
                enriched_question = self._build_enriched_question(question, context_entities, language)
                if enriched_question and enriched_question != question:
                    variants.append(enriched_question)
            
            # Variante 3: Question + contexte technique inline
            technical_context = self._build_technical_context(context_entities, language)
            if technical_context:
                inline_variant = f"{question} - Infos: {technical_context}"
                variants.append(inline_variant)
            
            # Variante 4: Question avec entités entre parenthèses
            if context_entities:
                entity_values = [v for v in context_entities.values() if v and isinstance(v, str)]
                if entity_values:
                    parentheses_variant = f"{question} ({', '.join(entity_values)})"
                    variants.append(parentheses_variant)
            
            # Variante 5: Question avec contexte technique séparé
            if technical_context:
                separated_variant = f"{question}\n\nContexte: {technical_context}"
                variants.append(separated_variant)
            
            # Variante 6: Question enrichie + informations manquantes
            missing_context = self._build_missing_entities_context(missing_entities, language)
            if missing_context:
                missing_variant = f"{question}\n\n{missing_context}"
                variants.append(missing_variant)
            
            # Variante 7: Question complètement restructurée avec tout le contexte
            if context_entities and technical_context:
                full_context_question = self._build_full_context_question(
                    question, context_entities, technical_context, language
                )
                if full_context_question and full_context_question != question:
                    variants.append(full_context_question)
            
            # Variante 8: Question avec focus entités clés
            key_entities_context = self._build_key_entities_focus(context_entities, language)
            if key_entities_context:
                focus_variant = f"{key_entities_context}: {question}"
                variants.append(focus_variant)
            
            # Supprimer les doublons tout en préservant l'ordre
            seen: Set[str] = set()
            unique_variants = []
            for variant in variants:
                if variant and variant not in seen:
                    seen.add(variant)
                    unique_variants.append(variant)
            
            return unique_variants
            
        except Exception as e:
            logger.error(f"Erreur lors de la génération des variantes: {e}")
            return [question]  # Fallback sécurisé
    
    def _select_best_variant(self, variants: List[str], context_entities: Dict[str, str]) -> str:
        """Sélectionne la meilleure variante basée sur le scoring"""
        
        if not variants:
            return ""
        
        if len(variants) == 1:
            return variants[0]
        
        try:
            # Calculer le score de chaque variante
            scores = {}
            for variant in variants:
                if variant:  # Vérifier que la variante n'est pas vide
                    scores[variant] = self._score_variant(variant, context_entities)
            
            if not scores:
                return variants[0]  # Fallback
            
            # Sélectionner la variante avec le meilleur score
            best_variant = max(scores, key=scores.get)
            
            # Log des scores pour debug
            logger.debug(f"🎯 [RAG Context] Scores des variantes:")
            for variant, score in scores.items():
                truncated = variant[:100] + ('...' if len(variant) > 100 else '')
                logger.debug(f"  Score {score:.2f}: '{truncated}'")
            
            return best_variant
            
        except Exception as e:
            logger.error(f"Erreur lors de la sélection de la meilleure variante: {e}")
            return variants[0]  # Fallback sécurisé
    
    def _score_variant(self, variant: str, context_entities: Dict[str, str]) -> float:
        """
        Score une variante basée sur la couverture des entités et d'autres facteurs
        
        Args:
            variant: Variante à scorer
            context_entities: Entités du contexte
        
        Returns:
            Score entre 0.0 et 2.0
        """
        
        if not variant or not isinstance(variant, str):
            return 0.0
        
        try:
            variant_lower = variant.lower()
            score = 0.0
            
            # 1. Score de base: couverture des entités (40% du score)
            entity_coverage = 0.0
            if context_entities:
                entities_found = 0
                total_entities = 0
                for entity_value in context_entities.values():
                    if entity_value and isinstance(entity_value, str) and entity_value.strip():
                        total_entities += 1
                        if entity_value.lower() in variant_lower:
                            entities_found += 1
                
                if total_entities > 0:
                    entity_coverage = entities_found / total_entities
            
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
            
            # Malus pour répétitions excessives - CORRIGÉ
            words = variant_lower.split()
            if words and len(words) > 0:
                unique_words = set(words)
                if len(words) != len(unique_words):  # Il y a des répétitions
                    repetition_ratio = (len(words) - len(unique_words)) / len(words)
                    word_repetition = 1.0 - repetition_ratio
                    readability_score *= word_repetition
            
            readability_score = min(1.0, max(0.0, readability_score))
            score += readability_score * 0.1
            
            # 5. Bonus spéciaux (10% du score)
            bonus_score = 0.0
            
            # Bonus pour mentions d'entités critiques
            critical_entities = ["ross 308", "cobb 500", "jour", "day", "kg", "gram"]
            for entity in critical_entities:
                if entity in variant_lower:
                    bonus_score += 0.1
            
            # Bonus pour questions bien structurées
            if variant.strip().endswith("?"):
                bonus_score += 0.05
            
            # Bonus pour contexte multilingue approprié
            language_indicators = {
                "fr": ["âge", "poids", "jour"], 
                "en": ["age", "weight", "day"], 
                "es": ["edad", "peso", "día"]
            }
            for lang, indicators in language_indicators.items():
                if any(indicator in variant_lower for indicator in indicators):
                    bonus_score += 0.05
                    break
            
            bonus_score = min(1.0, max(0.0, bonus_score))
            score += bonus_score * 0.1
            
            # Assurer que le score reste dans une plage raisonnable
            final_score = min(2.0, max(0.0, score))
            
            return final_score
            
        except Exception as e:
            logger.error(f"Erreur lors du scoring de la variante: {e}")
            return 0.0  # Score de fallback
    
    def _build_full_context_question(
        self, 
        question: str, 
        context_entities: Dict[str, str], 
        technical_context: str, 
        language: str
    ) -> str:
        """Construit une question complètement restructurée avec tout le contexte"""
        
        if not question or not technical_context:
            return question
        
        try:
            # Templates pour questions complètes
            templates = {
                "fr": "Contexte: {technical_context}\n\nQuestion: {question}",
                "en": "Context: {technical_context}\n\nQuestion: {question}",
                "es": "Contexto: {technical_context}\n\nPregunta: {question}"
            }
            
            template = templates.get(language, templates["fr"])
            return template.format(technical_context=technical_context, question=question)
            
        except Exception as e:
            logger.error(f"Erreur lors de la construction de la question complète: {e}")
            return question
    
    def _build_key_entities_focus(self, context_entities: Dict[str, str], language: str) -> str:
        """Construit un focus sur les entités clés les plus importantes"""
        
        if not context_entities:
            return ""
        
        try:
            # Ordre de priorité des entités par importance
            priority_order = ["breed", "age", "weight", "symptoms"]
            
            # Sélectionner les 2-3 entités les plus importantes présentes
            key_entities = []
            for entity in priority_order:
                if entity in context_entities and context_entities[entity]:
                    if isinstance(context_entities[entity], str) and context_entities[entity].strip():
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
            
        except Exception as e:
            logger.error(f"Erreur lors de la construction du focus entités: {e}")
            return ""
    
    def _detect_contextual_references(self, question: str, language: str) -> bool:
        """Détecte si la question contient des pronoms/références contextuelles"""
        
        if not question or language not in self._compiled_patterns:
            return False
        
        try:
            question_lower = question.lower()
            
            for pattern in self._compiled_patterns[language]:
                if pattern.search(question_lower):
                    logger.debug(f"🎯 [RAG Context] Pattern trouvé: {pattern.pattern}")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Erreur lors de la détection des références contextuelles: {e}")
            return False
    
    def _extract_context_entities(self, context: str) -> Dict[str, str]:
        """Extrait les entités importantes du contexte conversationnel"""
        
        if not context or not isinstance(context, str):
            return {}
        
        try:
            entities = {}
            context_lower = context.lower()
            
            # Extraire race - CORRIGÉ: patterns plus robustes
            breed_patterns = [
                r'race[:\s]+([a-zA-Z0-9\s]+?)(?:\n|,|\.|\s*$)',
                r'breed[:\s]+([a-zA-Z0-9\s]+?)(?:\n|,|\.|\s*$)', 
                r'(ross\s*308|cobb\s*500|hubbard|arbor\s*acres)',
                r'poulets?\s+(ross\s*308|cobb\s*500)',
                r'chickens?\s+(ross\s*308|cobb\s*500)'
            ]
            
            for pattern in breed_patterns:
                try:
                    match = re.search(pattern, context_lower, re.IGNORECASE | re.MULTILINE)
                    if match:
                        breed_value = match.group(1).strip()
                        if breed_value and len(breed_value) > 0:
                            entities["breed"] = breed_value
                            break
                except (re.error, IndexError) as e:
                    logger.debug(f"Erreur pattern breed: {e}")
                    continue
            
            # Extraire âge - CORRIGÉ: meilleure capture
            age_patterns = [
                r'âge[:\s]+(\d+\s*(?:jour|semaine|day|week)s?)',
                r'age[:\s]+(\d+\s*(?:jour|semaine|day|week)s?)',
                r'(\d+)\s*(?:jour|day)s?(?:\s|$|,|\.)',
                r'(\d+)\s*(?:semaine|week)s?(?:\s|$|,|\.)'
            ]
            
            for pattern in age_patterns:
                try:
                    match = re.search(pattern, context_lower, re.IGNORECASE)
                    if match:
                        age_value = match.group(1).strip()
                        if age_value and len(age_value) > 0:
                            entities["age"] = age_value
                            break
                except (re.error, IndexError) as e:
                    logger.debug(f"Erreur pattern age: {e}")
                    continue
            
            # Extraire poids - CORRIGÉ: patterns plus précis
            weight_patterns = [
                r'poids[:\s]+(\d+(?:\.\d+)?\s*[gk]?g?)',
                r'weight[:\s]+(\d+(?:\.\d+)?\s*[gk]?g?)',
                r'(\d+(?:\.\d+)?)\s*(?:gramme|gram|kg)s?(?:\s|$|,|\.)'
            ]
            
            for pattern in weight_patterns:
                try:
                    match = re.search(pattern, context_lower, re.IGNORECASE)
                    if match:
                        weight_value = match.group(1).strip()
                        if weight_value and len(weight_value) > 0:
                            entities["weight"] = weight_value
                            break
                except (re.error, IndexError) as e:
                    logger.debug(f"Erreur pattern weight: {e}")
                    continue
            
            # Extraire conditions d'hébergement - CORRIGÉ
            housing_patterns = [
                r'hébergement[:\s]+([^.\n]+)',
                r'housing[:\s]+([^.\n]+)',
                r'logement[:\s]+([^.\n]+)',
                r'barn[:\s]+([^.\n]+)'
            ]
            
            for pattern in housing_patterns:
                try:
                    match = re.search(pattern, context_lower, re.IGNORECASE)
                    if match:
                        housing_value = match.group(1).strip()
                        if housing_value and len(housing_value) > 0:
                            entities["housing"] = housing_value
                            break
                except (re.error, IndexError) as e:
                    logger.debug(f"Erreur pattern housing: {e}")
                    continue
            
            # Extraire symptômes - CORRIGÉ
            symptoms_patterns = [
                r'symptômes?[:\s]+([^.\n]+)',
                r'symptoms?[:\s]+([^.\n]+)',
                r'problème[:\s]+([^.\n]+)',
                r'problem[:\s]+([^.\n]+)'
            ]
            
            for pattern in symptoms_patterns:
                try:
                    match = re.search(pattern, context_lower, re.IGNORECASE)
                    if match:
                        symptoms_value = match.group(1).strip()
                        if symptoms_value and len(symptoms_value) > 0:
                            entities["symptoms"] = symptoms_value
                            break
                except (re.error, IndexError) as e:
                    logger.debug(f"Erreur pattern symptoms: {e}")
                    continue
            
            return entities
            
        except Exception as e:
            logger.error(f"Erreur lors de l'extraction des entités du contexte: {e}")
            return {}
    
    def _identify_missing_entities(
        self, 
        question: str, 
        context_entities: Dict[str, str], 
        language: str
    ) -> List[str]:
        """Identifie automatiquement les entités manquantes pertinentes pour la question"""
        
        if not question:
            return []
        
        try:
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
                if entity not in context_entities or not context_entities[entity]:  # Entité absente du contexte
                    # Vérifier si des mots-clés relatifs sont in la question
                    if any(keyword in question_lower for keyword in keywords):
                        missing.append(entity)
            
            # Entités toujours utiles pour certains types de questions
            diagnostic_keywords = ["problème", "problem", "malade", "sick", "diagnostic", "symptom"]
            if any(keyword in question_lower for keyword in diagnostic_keywords):
                # Pour les questions de diagnostic, ces entités sont souvent importantes
                for entity in ["breed", "age", "symptoms"]:
                    if (entity not in context_entities or not context_entities[entity]) and entity not in missing:
                        missing.append(entity)
            
            performance_keywords = ["croissance", "growth", "poids", "weight", "développement", "development"]
            if any(keyword in question_lower for keyword in performance_keywords):
                # Pour les questions de performance, ces entités sont importantes
                for entity in ["breed", "age", "feed"]:
                    if (entity not in context_entities or not context_entities[entity]) and entity not in missing:
                        missing.append(entity)
            
            return missing
            
        except Exception as e:
            logger.error(f"Erreur lors de l'identification des entités manquantes: {e}")
            return []
    
    def _build_enriched_question(
        self, 
        question: str, 
        context_entities: Dict[str, str], 
        language: str
    ) -> str:
        """Construit une question enrichie en remplaçant les pronoms par les entités contextuelles"""
        
        if not question or not context_entities:
            return question
        
        try:
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
            
            # Vérifier que les entités ne sont pas vides - CORRECTION
            valid_entities = {k: v for k, v in context_entities.items() if v and isinstance(v, str) and v.strip()}
            
            if all(k in valid_entities for k in ["breed", "age", "weight"]):
                context_prefix = template_set["full_context"].format(**valid_entities)
            elif "breed" in valid_entities and "age" in valid_entities:
                context_prefix = template_set["breed_age"].format(**valid_entities)
            elif "breed" in valid_entities:
                context_prefix = template_set["breed_only"].format(breed=valid_entities["breed"])
            elif "age" in valid_entities:
                context_prefix = template_set["age_only"].format(age=valid_entities["age"])
            
            if context_prefix:
                # Remplacer ou préfixer selon la structure de la question
                pronoun_words = ["son", "sa", "ses", "leur", "leurs", "their", "its", "su", "sus"]
                if any(word in question.lower() for word in pronoun_words):
                    enriched = f"{context_prefix}, {question.lower()}"
                else:
                    enriched = f"{context_prefix}: {question}"
            
            return enriched
            
        except Exception as e:
            logger.error(f"Erreur lors de la construction de la question enrichie: {e}")
            return question
    
    def _build_technical_context(self, entities: Dict[str, str], language: str) -> str:
        """Construit un contexte technique pour aider le RAG"""
        
        if not entities:
            return ""
        
        try:
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
                if entity in entities and entities[entity]:
                    if isinstance(entities[entity], str) and entities[entity].strip():
                        label = labels.get(entity, entity.capitalize())
                        context_parts.append(f"{label}: {entities[entity]}")
            
            return " | ".join(context_parts)
            
        except Exception as e:
            logger.error(f"Erreur lors de la construction du contexte technique: {e}")
            return ""
    
    def _build_missing_entities_context(self, missing_entities: List[str], language: str) -> str:
        """Construit un contexte indiquant les entités manquantes pour guider le RAG"""
        
        if not missing_entities:
            return ""
        
        try:
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
            
        except Exception as e:
            logger.error(f"Erreur lors de la construction du contexte des entités manquantes: {e}")
            return ""

# Instance globale
rag_context_enhancer = RAGContextEnhancer()

def enhance_question_for_rag(
    question: str, 
    conversation_context: str, 
    language: str = "fr",
    missing_entities: Optional[List[str]] = None
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