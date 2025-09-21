# -*- coding: utf-8 -*-
"""
rag/extractors/extractor_factory.py - Factory pour créer les extracteurs appropriés
Version 1.0 - Gestion centralisée des extracteurs par lignée génétique
"""

import logging
from typing import Dict, List, Optional, Type, Any

from .base_extractor import BaseExtractor
from .ross_extractor import RossExtractor
from ..models.enums import GeneticLine, DocumentType
from ..models.json_models import JSONDocument


# Import des autres extracteurs (à implémenter)
class CobbExtractor(BaseExtractor):
    """Extracteur Cobb - Implémentation simplifiée pour l'exemple"""

    def __init__(self, genetic_line: GeneticLine = GeneticLine.COBB_500):
        super().__init__()
        self.genetic_line = genetic_line

    def get_supported_genetic_lines(self) -> List[GeneticLine]:
        return [GeneticLine.COBB_500, GeneticLine.COBB_700]

    def extract_performance_data(self, json_document: JSONDocument) -> List:
        # Implémentation simplifiée - à développer
        self.log_extraction_progress("Extracteur Cobb - Implémentation en cours")
        return []


class HubbardExtractor(BaseExtractor):
    """Extracteur Hubbard - Implémentation simplifiée pour l'exemple"""

    def __init__(self, genetic_line: GeneticLine = GeneticLine.HUBBARD_CLASSIC):
        super().__init__()
        self.genetic_line = genetic_line

    def get_supported_genetic_lines(self) -> List[GeneticLine]:
        return [GeneticLine.HUBBARD_CLASSIC, GeneticLine.HUBBARD_FLEX]

    def extract_performance_data(self, json_document: JSONDocument) -> List:
        # Implémentation simplifiée - à développer
        self.log_extraction_progress("Extracteur Hubbard - Implémentation en cours")
        return []


class ExtractorFactory:
    """Factory pour créer et gérer les extracteurs de données avicoles"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

        # Registre des extracteurs disponibles
        self._extractor_registry: Dict[GeneticLine, Type[BaseExtractor]] = {
            # Extracteurs Ross
            GeneticLine.ROSS_308: RossExtractor,
            GeneticLine.ROSS_708: RossExtractor,
            # Extracteurs Cobb (à implémenter complètement)
            GeneticLine.COBB_500: CobbExtractor,
            GeneticLine.COBB_700: CobbExtractor,
            # Extracteurs Hubbard (à implémenter complètement)
            GeneticLine.HUBBARD_CLASSIC: HubbardExtractor,
            GeneticLine.HUBBARD_FLEX: HubbardExtractor,
        }

        # Cache des instances d'extracteurs
        self._extractor_cache: Dict[GeneticLine, BaseExtractor] = {}

        # Statistiques d'utilisation
        self.usage_stats = {
            "extractors_created": 0,
            "extractions_performed": 0,
            "cache_hits": 0,
            "errors": 0,
        }

    def create_extractor(
        self, genetic_line: GeneticLine, use_cache: bool = True
    ) -> BaseExtractor:
        """Crée un extracteur pour la lignée génétique spécifiée"""

        try:
            # Vérifier la disponibilité
            if genetic_line not in self._extractor_registry:
                available_lines = list(self._extractor_registry.keys())
                raise ValueError(
                    f"Aucun extracteur disponible pour {genetic_line}. "
                    f"Lignées supportées: {[gl.value for gl in available_lines]}"
                )

            # Utiliser le cache si demandé
            if use_cache and genetic_line in self._extractor_cache:
                self.usage_stats["cache_hits"] += 1
                self.logger.debug(f"Extracteur {genetic_line.value} récupéré du cache")
                return self._extractor_cache[genetic_line]

            # Créer nouvelle instance
            extractor_class = self._extractor_registry[genetic_line]
            extractor = extractor_class(genetic_line)

            # Mettre en cache
            if use_cache:
                self._extractor_cache[genetic_line] = extractor

            self.usage_stats["extractors_created"] += 1
            self.logger.info(
                f"Extracteur créé: {extractor_class.__name__} pour {genetic_line.value}"
            )

            return extractor

        except Exception as e:
            self.usage_stats["errors"] += 1
            self.logger.error(f"Erreur création extracteur pour {genetic_line}: {e}")
            raise

    def auto_detect_and_create_extractor(
        self, json_document: JSONDocument
    ) -> Optional[BaseExtractor]:
        """Détecte automatiquement la lignée et crée l'extracteur approprié"""

        try:
            # Méthode 1: Lignée explicite dans les métadonnées
            if json_document.metadata.genetic_line != GeneticLine.UNKNOWN:
                genetic_line = json_document.metadata.genetic_line
                self.logger.info(f"Lignée explicite détectée: {genetic_line.value}")
                return self.create_extractor(genetic_line)

            # Méthode 2: Détection depuis le contenu
            detected_line = self._detect_genetic_line_from_content(json_document)

            if detected_line != GeneticLine.UNKNOWN:
                self.logger.info(f"Lignée auto-détectée: {detected_line.value}")
                # Mettre à jour les métadonnées
                json_document.metadata.genetic_line = detected_line
                json_document.metadata.auto_detected_genetic_line = True
                return self.create_extractor(detected_line)

            # Méthode 3: Extracteur générique ou échec
            self.logger.warning("Aucune lignée détectée - extraction impossible")
            return None

        except Exception as e:
            self.logger.error(f"Erreur auto-détection extracteur: {e}")
            return None

    def _detect_genetic_line_from_content(
        self, json_document: JSONDocument
    ) -> GeneticLine:
        """Détecte la lignée génétique depuis le contenu du document"""

        content = f"{json_document.title} {json_document.text}".lower()

        # Ajouter le contexte des tableaux pour améliorer la détection
        for table in json_document.tables:
            content += f" {table.context} {' '.join(table.headers)}"

        # Patterns de détection avec scoring
        detection_patterns = {
            GeneticLine.ROSS_308: [
                ("ross 308", 10),
                ("ross-308", 10),
                ("ross308", 8),
                ("r308", 6),
                ("ross broiler", 5),
                ("broiler ross", 5),
            ],
            GeneticLine.ROSS_708: [
                ("ross 708", 10),
                ("ross-708", 10),
                ("ross708", 8),
                ("r708", 6),
            ],
            GeneticLine.COBB_500: [
                ("cobb 500", 10),
                ("cobb-500", 10),
                ("cobb500", 8),
                ("c500", 6),
                ("cobb broiler", 5),
            ],
            GeneticLine.COBB_700: [
                ("cobb 700", 10),
                ("cobb-700", 10),
                ("cobb700", 8),
                ("c700", 6),
            ],
            GeneticLine.HUBBARD_CLASSIC: [
                ("hubbard classic", 10),
                ("classic hubbard", 8),
                ("hubbard", 4),
            ],
            GeneticLine.HUBBARD_FLEX: [
                ("hubbard flex", 10),
                ("flex hubbard", 8),
                ("hubbard f", 6),
            ],
            GeneticLine.ISA_BROWN: [("isa brown", 10), ("brown isa", 8), ("isa", 3)],
            GeneticLine.LOHMANN_BROWN: [
                ("lohmann brown", 10),
                ("brown lohmann", 8),
                ("lohmann", 4),
            ],
            GeneticLine.HY_LINE: [("hy-line", 10), ("hyline", 8), ("hy line", 8)],
        }

        # Calcul des scores
        line_scores = {}
        for genetic_line, patterns in detection_patterns.items():
            score = 0
            for pattern, weight in patterns:
                count = content.count(pattern)
                score += count * weight

            if score > 0:
                line_scores[genetic_line] = score

        # Retourner la lignée avec le meilleur score
        if line_scores:
            best_line = max(line_scores, key=line_scores.get)
            best_score = line_scores[best_line]

            # Seuil minimum pour confirmer la détection
            min_score = 5
            if best_score >= min_score:
                self.logger.debug(
                    f"Lignée détectée: {best_line.value} (score: {best_score})"
                )
                return best_line

        return GeneticLine.UNKNOWN

    def extract_from_document(
        self, json_document: JSONDocument, genetic_line: Optional[GeneticLine] = None
    ) -> List[Any]:
        """Extraction complète depuis un document avec gestion automatique"""

        try:
            # Déterminer l'extracteur à utiliser
            if genetic_line:
                extractor = self.create_extractor(genetic_line)
            else:
                extractor = self.auto_detect_and_create_extractor(json_document)

            if not extractor:
                self.logger.warning("Aucun extracteur disponible pour ce document")
                return []

            # Extraction
            self.usage_stats["extractions_performed"] += 1
            records = extractor.extract_performance_data(json_document)

            self.logger.info(
                f"Extraction terminée: {len(records)} enregistrements "
                f"avec {extractor.__class__.__name__}"
            )

            return records

        except Exception as e:
            self.usage_stats["errors"] += 1
            self.logger.error(f"Erreur extraction document: {e}")
            return []

    def get_available_extractors(self) -> Dict[GeneticLine, str]:
        """Retourne la liste des extracteurs disponibles"""

        return {
            genetic_line: extractor_class.__name__
            for genetic_line, extractor_class in self._extractor_registry.items()
        }

    def get_supported_genetic_lines(self) -> List[GeneticLine]:
        """Retourne toutes les lignées génétiques supportées"""

        return list(self._extractor_registry.keys())

    def is_genetic_line_supported(self, genetic_line: GeneticLine) -> bool:
        """Vérifie si une lignée génétique est supportée"""

        return genetic_line in self._extractor_registry

    def register_extractor(
        self, genetic_line: GeneticLine, extractor_class: Type[BaseExtractor]
    ) -> None:
        """Enregistre un nouvel extracteur"""

        if not issubclass(extractor_class, BaseExtractor):
            raise ValueError("L'extracteur doit hériter de BaseExtractor")

        self._extractor_registry[genetic_line] = extractor_class

        # Invalider le cache pour cette lignée
        if genetic_line in self._extractor_cache:
            del self._extractor_cache[genetic_line]

        self.logger.info(
            f"Extracteur enregistré: {extractor_class.__name__} pour {genetic_line.value}"
        )

    def clear_cache(self) -> None:
        """Vide le cache des extracteurs"""

        self._extractor_cache.clear()
        self.logger.info("Cache des extracteurs vidé")

    def get_usage_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques d'utilisation"""

        stats = self.usage_stats.copy()
        stats["cached_extractors"] = len(self._extractor_cache)
        stats["registered_extractors"] = len(self._extractor_registry)
        stats["cache_hit_rate"] = self.usage_stats["cache_hits"] / max(
            1, self.usage_stats["extractors_created"]
        )

        return stats

    def create_batch_extractor(self, documents: List[JSONDocument]) -> Dict[str, Any]:
        """Traitement par lots de documents"""

        results = {
            "total_documents": len(documents),
            "successful_extractions": 0,
            "failed_extractions": 0,
            "total_records": 0,
            "extractor_usage": {},
            "errors": [],
        }

        for i, document in enumerate(documents):
            try:
                self.logger.info(
                    f"Traitement document {i+1}/{len(documents)}: {document.title}"
                )

                records = self.extract_from_document(document)

                if records:
                    results["successful_extractions"] += 1
                    results["total_records"] += len(records)

                    # Compter l'utilisation des extracteurs
                    genetic_line = document.metadata.genetic_line.value
                    if genetic_line not in results["extractor_usage"]:
                        results["extractor_usage"][genetic_line] = 0
                    results["extractor_usage"][genetic_line] += 1

                else:
                    results["failed_extractions"] += 1

            except Exception as e:
                results["failed_extractions"] += 1
                error_msg = f"Document {i+1} ({document.title}): {str(e)}"
                results["errors"].append(error_msg)
                self.logger.error(error_msg)

        # Statistiques finales
        results["success_rate"] = results["successful_extractions"] / max(
            1, results["total_documents"]
        )
        results["avg_records_per_document"] = results["total_records"] / max(
            1, results["successful_extractions"]
        )

        self.logger.info(
            f"Traitement par lots terminé: {results['successful_extractions']}/{results['total_documents']} "
            f"documents traités avec succès, {results['total_records']} enregistrements extraits"
        )

        return results

    def validate_extractor_compatibility(
        self, genetic_line: GeneticLine, document: JSONDocument
    ) -> Dict[str, Any]:
        """Valide la compatibilité entre un extracteur et un document"""

        validation_result = {
            "compatible": False,
            "confidence_score": 0.0,
            "reasons": [],
            "recommendations": [],
        }

        try:
            if not self.is_genetic_line_supported(genetic_line):
                validation_result["reasons"].append(
                    f"Lignée {genetic_line.value} non supportée"
                )
                validation_result["recommendations"].append("Utiliser l'auto-détection")
                return validation_result

            # Créer l'extracteur pour test
            extractor = self.create_extractor(genetic_line, use_cache=False)

            # Vérifier la compatibilité
            if genetic_line in extractor.get_supported_genetic_lines():
                validation_result["compatible"] = True
                validation_result["confidence_score"] += 0.5
                validation_result["reasons"].append("Lignée officiellement supportée")

            # Vérifier la présence de données exploitables
            has_tables = len(document.tables) > 0
            if has_tables:
                validation_result["confidence_score"] += 0.3
                validation_result["reasons"].append(
                    f"{len(document.tables)} tableau(x) détecté(s)"
                )
            else:
                validation_result["reasons"].append("Aucun tableau détecté")
                validation_result["recommendations"].append(
                    "Vérifier la structure des données"
                )

            # Vérifier la cohérence du contenu
            content_score = self._calculate_content_compatibility_score(
                document, genetic_line
            )
            validation_result["confidence_score"] += content_score * 0.2

            if content_score > 0.5:
                validation_result["reasons"].append("Contenu cohérent avec la lignée")
            else:
                validation_result["reasons"].append(
                    "Contenu peu cohérent avec la lignée"
                )
                validation_result["recommendations"].append(
                    "Vérifier la lignée ou utiliser auto-détection"
                )

            # Verdict final
            validation_result["compatible"] = (
                validation_result["confidence_score"] > 0.6
            )

        except Exception as e:
            validation_result["reasons"].append(f"Erreur validation: {str(e)}")
            self.logger.error(f"Erreur validation compatibilité: {e}")

        return validation_result

    def _calculate_content_compatibility_score(
        self, document: JSONDocument, genetic_line: GeneticLine
    ) -> float:
        """Calcule un score de compatibilité du contenu avec la lignée"""

        content = f"{document.title} {document.text}".lower()

        # Patterns spécifiques par lignée
        genetic_patterns = {
            GeneticLine.ROSS_308: ["ross", "308", "broiler"],
            GeneticLine.ROSS_708: ["ross", "708", "broiler"],
            GeneticLine.COBB_500: ["cobb", "500", "broiler"],
            GeneticLine.COBB_700: ["cobb", "700", "broiler"],
            GeneticLine.HUBBARD_CLASSIC: ["hubbard", "classic"],
            GeneticLine.HUBBARD_FLEX: ["hubbard", "flex"],
            GeneticLine.ISA_BROWN: ["isa", "brown", "layer"],
            GeneticLine.LOHMANN_BROWN: ["lohmann", "brown", "layer"],
            GeneticLine.HY_LINE: ["hy-line", "hyline", "layer"],
        }

        if genetic_line not in genetic_patterns:
            return 0.0

        patterns = genetic_patterns[genetic_line]
        matches = sum(1 for pattern in patterns if pattern in content)

        return min(1.0, matches / len(patterns))

    def get_extraction_recommendations(self, document: JSONDocument) -> Dict[str, Any]:
        """Fournit des recommandations pour l'extraction d'un document"""

        recommendations = {
            "recommended_extractor": None,
            "confidence": 0.0,
            "alternatives": [],
            "preprocessing_suggestions": [],
            "quality_assessment": {},
        }

        try:
            # Auto-détection
            detected_line = self._detect_genetic_line_from_content(document)

            if detected_line != GeneticLine.UNKNOWN:
                recommendations["recommended_extractor"] = detected_line.value
                recommendations["confidence"] = 0.8

            # Évaluer toutes les options
            all_scores = {}
            for genetic_line in self.get_supported_genetic_lines():
                compatibility = self.validate_extractor_compatibility(
                    genetic_line, document
                )
                all_scores[genetic_line.value] = compatibility["confidence_score"]

            # Trier par score
            sorted_options = sorted(
                all_scores.items(), key=lambda x: x[1], reverse=True
            )
            recommendations["alternatives"] = sorted_options[:3]  # Top 3

            # Évaluation de la qualité du document
            quality = self._assess_document_quality(document)
            recommendations["quality_assessment"] = quality

            # Suggestions de préprocessing
            if quality["table_quality"] < 0.5:
                recommendations["preprocessing_suggestions"].append(
                    "Améliorer la structure des tableaux"
                )

            if quality["content_clarity"] < 0.5:
                recommendations["preprocessing_suggestions"].append(
                    "Enrichir les métadonnées ou le contexte"
                )

            if not document.tables:
                recommendations["preprocessing_suggestions"].append(
                    "Vérifier la présence de données tabulaires"
                )

        except Exception as e:
            self.logger.error(f"Erreur génération recommandations: {e}")

        return recommendations

    def _assess_document_quality(self, document: JSONDocument) -> Dict[str, float]:
        """Évalue la qualité d'un document pour l'extraction"""

        quality = {
            "overall": 0.0,
            "content_clarity": 0.0,
            "table_quality": 0.0,
            "metadata_completeness": 0.0,
            "data_richness": 0.0,
        }

        # Clarté du contenu
        if document.title and len(document.title) > 10:
            quality["content_clarity"] += 0.3
        if document.text and len(document.text) > 100:
            quality["content_clarity"] += 0.4
        if document.metadata.genetic_line != GeneticLine.UNKNOWN:
            quality["content_clarity"] += 0.3

        # Qualité des tableaux
        if document.tables:
            valid_tables = sum(1 for table in document.tables if table.is_valid)
            quality["table_quality"] = valid_tables / len(document.tables)

        # Complétude des métadonnées
        metadata_fields = [
            document.metadata.genetic_line != GeneticLine.UNKNOWN,
            document.metadata.document_type != DocumentType.UNKNOWN,
            bool(document.metadata.source),
            bool(document.metadata.language),
        ]
        quality["metadata_completeness"] = sum(metadata_fields) / len(metadata_fields)

        # Richesse des données
        total_cells = sum(
            len(table.headers) * len(table.rows) for table in document.tables
        )
        if total_cells > 50:
            quality["data_richness"] = min(1.0, total_cells / 200)

        # Score global
        quality["overall"] = (
            quality["content_clarity"] * 0.3
            + quality["table_quality"] * 0.4
            + quality["metadata_completeness"] * 0.2
            + quality["data_richness"] * 0.1
        )

        return quality

    def generate_extractor_report(self) -> Dict[str, Any]:
        """Génère un rapport complet sur l'état des extracteurs"""

        report = {
            "timestamp": str(
                self.logger.handlers[0].formatter.formatTime(
                    self.logger.handlers[0].formatter.converter(None)
                )
                if self.logger.handlers
                else "N/A"
            ),
            "factory_stats": self.get_usage_stats(),
            "available_extractors": {},
            "genetic_lines": {
                "supported": len(self.get_supported_genetic_lines()),
                "total_known": len(GeneticLine),
                "coverage": len(self.get_supported_genetic_lines()) / len(GeneticLine),
            },
            "recommendations": [],
        }

        # Détails par extracteur
        for genetic_line in self.get_supported_genetic_lines():
            try:
                extractor = self.create_extractor(genetic_line, use_cache=False)
                extractor_info = {
                    "class": extractor.__class__.__name__,
                    "supported_lines": [
                        gl.value for gl in extractor.get_supported_genetic_lines()
                    ],
                    "stats": extractor.get_extraction_summary(),
                }
                report["available_extractors"][genetic_line.value] = extractor_info
            except Exception as e:
                report["available_extractors"][genetic_line.value] = {"error": str(e)}

        # Recommandations d'amélioration
        if report["genetic_lines"]["coverage"] < 1.0:
            missing_lines = set(GeneticLine) - set(self.get_supported_genetic_lines())
            report["recommendations"].append(
                f"Implémenter les extracteurs manquants: {[gl.value for gl in missing_lines]}"
            )

        if self.usage_stats["errors"] > 0:
            error_rate = self.usage_stats["errors"] / max(
                1, self.usage_stats["extractions_performed"]
            )
            if error_rate > 0.1:
                report["recommendations"].append(
                    f"Taux d'erreur élevé ({error_rate:.1%}) - Revoir la robustesse des extracteurs"
                )

        return report


# Instance globale du factory (singleton)
_extractor_factory_instance = None


def get_extractor_factory() -> ExtractorFactory:
    """Récupère l'instance globale du factory (pattern singleton)"""
    global _extractor_factory_instance

    if _extractor_factory_instance is None:
        _extractor_factory_instance = ExtractorFactory()

    return _extractor_factory_instance


# Fonctions utilitaires pour l'usage simple


def extract_from_json_data(
    json_data: Dict[str, Any], genetic_line: Optional[GeneticLine] = None
) -> List[Any]:
    """Fonction utilitaire pour extraction simple depuis des données JSON"""

    from ..models.json_models import JSONDocument

    # Conversion en document
    document = JSONDocument.from_dict(json_data)

    # Extraction
    factory = get_extractor_factory()
    return factory.extract_from_document(document, genetic_line)


def auto_extract_from_json_data(json_data: Dict[str, Any]) -> Dict[str, Any]:
    """Extraction automatique avec détection de lignée et rapport"""

    from ..models.json_models import JSONDocument

    document = JSONDocument.from_dict(json_data)
    factory = get_extractor_factory()

    # Recommandations
    recommendations = factory.get_extraction_recommendations(document)

    # Extraction
    records = factory.extract_from_document(document)

    return {
        "records": records,
        "document_info": {
            "title": document.title,
            "genetic_line": document.metadata.genetic_line.value,
            "tables_count": len(document.tables),
            "auto_detected": document.metadata.auto_detected_genetic_line,
        },
        "extraction_info": {"records_count": len(records), "success": len(records) > 0},
        "recommendations": recommendations,
    }


# Export des classes et fonctions principales
__all__ = [
    "ExtractorFactory",
    "get_extractor_factory",
    "extract_from_json_data",
    "auto_extract_from_json_data",
    "RossExtractor",
    "CobbExtractor",
    "HubbardExtractor",
]
