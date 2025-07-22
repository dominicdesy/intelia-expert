"""Enhanced translation manager with performance-based templates."""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Union

logger = logging.getLogger(__name__)

# Global current language
current_language = "en"

# Performance-based translation templates
INTELLIGENT_TEMPLATES = {
    "en": {
        "pdf": {
            "insights": {
                "excellent": {
                    "performance": "Barn {barn_id} demonstrates excellent performance with a score of {score:.1f}/100",
                    "maintenance": "Continue current management practices to maintain optimal results",
                    "optimization": "Focus on fine-tuning operations for maximum efficiency"
                },
                "good": {
                    "performance": "Barn {barn_id} shows good performance with a score of {score:.1f}/100",
                    "improvement": "Small adjustments could elevate performance to excellent levels",
                    "monitoring": "Monitor key indicators to prevent performance decline"
                },
                "attention": {
                    "performance": "Barn {barn_id} requires attention with a score of {score:.1f}/100",
                    "intervention": "Immediate management interventions are recommended",
                    "urgency": "Address identified issues promptly to prevent further decline"
                },
                "critical": {
                    "performance": "Barn {barn_id} shows critical performance with a score of {score:.1f}/100",
                    "immediate_action": "Urgent action required to address performance issues",
                    "support": "Consider consulting veterinary and technical support"
                }
            },
            "recommendations": {
                "excellent": {
                    "maintenance_items": [
                        "Maintain current feeding schedule and nutrition quality",
                        "Continue optimal temperature and ventilation management",
                        "Keep current biosecurity protocols at high standards",
                        "Monitor for any emerging health indicators"
                    ],
                    "optimization_items": [
                        "Fine-tune feed conversion efficiency tracking",
                        "Optimize lighting programs for maximum growth",
                        "Consider performance benchmarking with similar operations",
                        "Document best practices for future flocks"
                    ],
                    "monitoring_items": [
                        "Daily performance monitoring to maintain excellence",
                        "Weekly environmental data analysis",
                        "Regular equipment calibration and maintenance"
                    ]
                },
                "good": {
                    "improvement_items": [
                        "Review and adjust feed formulation if needed",
                        "Optimize environmental control settings",
                        "Enhance water quality management",
                        "Fine-tune vaccination and health programs"
                    ],
                    "prevention_items": [
                        "Increase monitoring frequency for key parameters",
                        "Strengthen biosecurity measures",
                        "Review and update standard operating procedures",
                        "Ensure proper equipment maintenance schedules"
                    ],
                    "monitoring_items": [
                        "Daily weight and performance tracking",
                        "Environmental monitoring with data logging",
                        "Weekly flock health assessments"
                    ]
                },
                "attention": {
                    "immediate_items": [
                        "Review and adjust feeding program immediately",
                        "Check and optimize environmental controls",
                        "Assess water system functionality and quality",
                        "Evaluate flock health status with veterinarian"
                    ],
                    "corrective_items": [
                        "Implement corrective feeding strategies",
                        "Adjust ventilation and temperature controls",
                        "Review and strengthen health protocols",
                        "Increase monitoring frequency to twice daily"
                    ],
                    "management_items": [
                        "Staff training on proper management protocols",
                        "Equipment inspection and maintenance",
                        "Review of biosecurity procedures",
                        "Documentation of all corrective actions taken"
                    ]
                },
                "critical": {
                    "emergency_items": [
                        "Immediate veterinary consultation required",
                        "Emergency feed and water system checks",
                        "Critical environmental parameter adjustments",
                        "Immediate health intervention protocols"
                    ],
                    "intervention_items": [
                        "Implement emergency management protocols",
                        "Consider therapeutic interventions as advised",
                        "Adjust nutrition to recovery formulations",
                        "Modify environmental conditions for recovery"
                    ],
                    "support_items": [
                        "Engage technical support team immediately",
                        "Consider specialist veterinary consultation",
                        "Review and revise all management protocols",
                        "Implement intensive monitoring and reporting"
                    ]
                },
                "specific_title": "Specific Recommendations for Your Barn",
                "critical_issues": "Critical Issues Requiring Immediate Attention",
                "maintenance_title": "Maintenance Recommendations",
                "optimization_title": "Optimization Opportunities",
                "monitoring_title": "Monitoring Requirements",
                "improvement_title": "Performance Improvements",
                "prevention_title": "Preventive Measures",
                "immediate_title": "Immediate Actions",
                "corrective_title": "Corrective Measures",
                "management_title": "Management Adjustments",
                "emergency_title": "Emergency Actions",
                "intervention_title": "Required Interventions",
                "support_title": "Support Requirements"
            }
        }
    },
    "fr": {
        "pdf": {
            "insights": {
                "excellent": {
                    "performance": "Le bâtiment {barn_id} démontre une performance excellente avec un score de {score:.1f}/100",
                    "maintenance": "Continuez les pratiques actuelles pour maintenir les résultats optimaux",
                    "optimization": "Concentrez-vous sur l'optimisation fine des opérations"
                },
                "good": {
                    "performance": "Le bâtiment {barn_id} montre une bonne performance avec un score de {score:.1f}/100",
                    "improvement": "De petits ajustements pourraient élever la performance à un niveau excellent",
                    "monitoring": "Surveillez les indicateurs clés pour prévenir la baisse de performance"
                },
                "attention": {
                    "performance": "Le bâtiment {barn_id} nécessite de l'attention avec un score de {score:.1f}/100",
                    "intervention": "Des interventions de gestion immédiates sont recommandées",
                    "urgency": "Adressez rapidement les problèmes identifiés pour prévenir une détérioration"
                },
                "critical": {
                    "performance": "Le bâtiment {barn_id} montre une performance critique avec un score de {score:.1f}/100",
                    "immediate_action": "Action urgente requise pour adresser les problèmes de performance",
                    "support": "Considérez consulter un support vétérinaire et technique"
                }
            },
            "recommendations": {
                "excellent": {
                    "maintenance_items": [
                        "Maintenir l'horaire d'alimentation et la qualité nutritionnelle actuels",
                        "Continuer la gestion optimale de température et ventilation",
                        "Garder les protocoles de biosécurité à des standards élevés",
                        "Surveiller les indicateurs de santé émergents"
                    ],
                    "optimization_items": [
                        "Affiner le suivi d'efficacité de conversion alimentaire",
                        "Optimiser les programmes d'éclairage pour croissance maximale",
                        "Considérer l'étalonnage avec des opérations similaires",
                        "Documenter les meilleures pratiques pour les futurs lots"
                    ],
                    "monitoring_items": [
                        "Surveillance quotidienne pour maintenir l'excellence",
                        "Analyse hebdomadaire des données environnementales",
                        "Calibration et maintenance régulières des équipements"
                    ]
                },
                "good": {
                    "improvement_items": [
                        "Réviser et ajuster la formulation alimentaire si nécessaire",
                        "Optimiser les paramètres de contrôle environnemental",
                        "Améliorer la gestion de qualité de l'eau",
                        "Affiner les programmes de vaccination et santé"
                    ],
                    "prevention_items": [
                        "Augmenter la fréquence de surveillance des paramètres clés",
                        "Renforcer les mesures de biosécurité",
                        "Réviser et mettre à jour les procédures opérationnelles",
                        "Assurer les horaires de maintenance des équipements"
                    ],
                    "monitoring_items": [
                        "Suivi quotidien du poids et performance",
                        "Surveillance environnementale avec enregistrement",
                        "Évaluations hebdomadaires de santé du troupeau"
                    ]
                },
                "attention": {
                    "immediate_items": [
                        "Réviser et ajuster immédiatement le programme alimentaire",
                        "Vérifier et optimiser les contrôles environnementaux",
                        "Évaluer la fonctionnalité et qualité du système d'eau",
                        "Évaluer l'état de santé avec le vétérinaire"
                    ],
                    "corrective_items": [
                        "Implémenter des stratégies alimentaires correctives",
                        "Ajuster les contrôles de ventilation et température",
                        "Réviser et renforcer les protocoles de santé",
                        "Augmenter la fréquence de surveillance à deux fois par jour"
                    ],
                    "management_items": [
                        "Formation du personnel sur les protocoles appropriés",
                        "Inspection et maintenance des équipements",
                        "Révision des procédures de biosécurité",
                        "Documentation de toutes les actions correctives"
                    ]
                },
                "critical": {
                    "emergency_items": [
                        "Consultation vétérinaire immédiate requise",
                        "Vérifications d'urgence des systèmes alimentaire et d'eau",
                        "Ajustements critiques des paramètres environnementaux",
                        "Protocoles d'intervention sanitaire immédiate"
                    ],
                    "intervention_items": [
                        "Implémenter les protocoles de gestion d'urgence",
                        "Considérer les interventions thérapeutiques conseillées",
                        "Ajuster la nutrition aux formulations de récupération",
                        "Modifier les conditions environnementales pour récupération"
                    ],
                    "support_items": [
                        "Engager l'équipe de support technique immédiatement",
                        "Considérer une consultation vétérinaire spécialisée",
                        "Réviser tous les protocoles de gestion",
                        "Implémenter surveillance et rapport intensifs"
                    ]
                },
                "specific_title": "Recommandations Spécifiques pour Votre Bâtiment",
                "critical_issues": "Problèmes Critiques Nécessitant Attention Immédiate",
                "maintenance_title": "Recommandations de Maintenance",
                "optimization_title": "Opportunités d'Optimisation",
                "monitoring_title": "Exigences de Surveillance",
                "improvement_title": "Améliorations de Performance",
                "prevention_title": "Mesures Préventives",
                "immediate_title": "Actions Immédiates",
                "corrective_title": "Mesures Correctives",
                "management_title": "Ajustements de Gestion",
                "emergency_title": "Actions d'Urgence",
                "intervention_title": "Interventions Requises",
                "support_title": "Exigences de Support"
            }
        }
    },
    "es": {
        "pdf": {
            "insights": {
                "excellent": {
                    "performance": "El galpón {barn_id} demuestra un rendimiento excelente con una puntuación de {score:.1f}/100",
                    "maintenance": "Continúe las prácticas actuales para mantener resultados óptimos",
                    "optimization": "Enfóquese en el ajuste fino de operaciones para máxima eficiencia"
                },
                "good": {
                    "performance": "El galpón {barn_id} muestra un buen rendimiento con una puntuación de {score:.1f}/100",
                    "improvement": "Pequeños ajustes podrían elevar el rendimiento a niveles excelentes",
                    "monitoring": "Monitoree indicadores clave para prevenir decline del rendimiento"
                },
                "attention": {
                    "performance": "El galpón {barn_id} requiere atención con una puntuación de {score:.1f}/100",
                    "intervention": "Se recomiendan intervenciones de manejo inmediatas",
                    "urgency": "Aborde los problemas identificados rápidamente para prevenir mayor deterioro"
                },
                "critical": {
                    "performance": "El galpón {barn_id} muestra rendimiento crítico con una puntuación de {score:.1f}/100",
                    "immediate_action": "Se requiere acción urgente para abordar problemas de rendimiento",
                    "support": "Considere consultar soporte veterinario y técnico"
                }
            },
            "recommendations": {
                "excellent": {
                    "maintenance_items": [
                        "Mantener horario actual de alimentación y calidad nutricional",
                        "Continuar manejo óptimo de temperatura y ventilación",
                        "Mantener protocolos de bioseguridad en estándares altos",
                        "Monitorear cualquier indicador de salud emergente"
                    ],
                    "optimization_items": [
                        "Afinar seguimiento de eficiencia de conversión alimenticia",
                        "Optimizar programas de iluminación para crecimiento máximo",
                        "Considerar benchmarking con operaciones similares",
                        "Documentar mejores prácticas para futuros lotes"
                    ],
                    "monitoring_items": [
                        "Monitoreo diario de rendimiento para mantener excelencia",
                        "Análisis semanal de datos ambientales",
                        "Calibración y mantenimiento regular de equipos"
                    ]
                },
                "good": {
                    "improvement_items": [
                        "Revisar y ajustar formulación de alimento si es necesario",
                        "Optimizar configuraciones de control ambiental",
                        "Mejorar manejo de calidad del agua",
                        "Afinar programas de vacunación y salud"
                    ],
                    "prevention_items": [
                        "Aumentar frecuencia de monitoreo para parámetros clave",
                        "Fortalecer medidas de bioseguridad",
                        "Revisar y actualizar procedimientos operativos estándar",
                        "Asegurar horarios apropiados de mantenimiento de equipos"
                    ],
                    "monitoring_items": [
                        "Seguimiento diario de peso y rendimiento",
                        "Monitoreo ambiental con registro de datos",
                        "Evaluaciones semanales de salud del lote"
                    ]
                },
                "attention": {
                    "immediate_items": [
                        "Revisar y ajustar programa de alimentación inmediatamente",
                        "Verificar y optimizar controles ambientales",
                        "Evaluar funcionalidad y calidad del sistema de agua",
                        "Evaluar estado de salud del lote con veterinario"
                    ],
                    "corrective_items": [
                        "Implementar estrategias alimenticias correctivas",
                        "Ajustar controles de ventilación y temperatura",
                        "Revisar y fortalecer protocolos de salud",
                        "Aumentar frecuencia de monitoreo a dos veces por día"
                    ],
                    "management_items": [
                        "Entrenamiento de personal en protocolos apropiados",
                        "Inspección y mantenimiento de equipos",
                        "Revisión de procedimientos de bioseguridad",
                        "Documentación de todas las acciones correctivas tomadas"
                    ]
                },
                "critical": {
                    "emergency_items": [
                        "Consulta veterinaria inmediata requerida",
                        "Verificaciones de emergencia de sistemas de alimento y agua",
                        "Ajustes críticos de parámetros ambientales",
                        "Protocolos de intervención de salud inmediata"
                    ],
                    "intervention_items": [
                        "Implementar protocolos de manejo de emergencia",
                        "Considerar intervenciones terapéuticas según se aconseje",
                        "Ajustar nutrición a formulaciones de recuperación",
                        "Modificar condiciones ambientales para recuperación"
                    ],
                    "support_items": [
                        "Involucrar equipo de soporte técnico inmediatamente",
                        "Considerar consulta veterinaria especializada",
                        "Revisar y revisar todos los protocolos de manejo",
                        "Implementar monitoreo y reporte intensivo"
                    ]
                },
                "specific_title": "Recomendaciones Específicas para Su Galpón",
                "critical_issues": "Problemas Críticos que Requieren Atención Inmediata",
                "maintenance_title": "Recomendaciones de Mantenimiento",
                "optimization_title": "Oportunidades de Optimización",
                "monitoring_title": "Requisitos de Monitoreo",
                "improvement_title": "Mejoras de Rendimiento",
                "prevention_title": "Medidas Preventivas",
                "immediate_title": "Acciones Inmediatas",
                "corrective_title": "Medidas Correctivas",
                "management_title": "Ajustes de Manejo",
                "emergency_title": "Acciones de Emergencia",
                "intervention_title": "Intervenciones Requeridas",
                "support_title": "Requisitos de Soporte"
            }
        }
    }
}

class IntelligentTranslationManager:
    """Enhanced translation manager with performance-based templates."""
    
    def __init__(self):
        """Initialize translation manager with intelligent templates."""
        self.translations = INTELLIGENT_TEMPLATES.copy()
        self.current_language = "en"
        self.fallback_language = "en"
        
        # Try to load existing translation files
        self._load_existing_translations()
        
        logger.info("Intelligent translation manager initialized")
    
    def _load_existing_translations(self):
        """Load existing translation files and merge with intelligent templates."""
        translations_dir = Path("core/notifications/translations/locales")
        
        if not translations_dir.exists():
            logger.info("No existing translation directory found, using intelligent templates only")
            return
        
        for lang_code in ["en", "fr", "es"]:
            lang_file = translations_dir / f"{lang_code}.json"
            if lang_file.exists():
                try:
                    with open(lang_file, 'r', encoding='utf-8') as f:
                        existing_translations = json.load(f)
                    
                    # Merge existing with intelligent templates
                    if lang_code not in self.translations:
                        self.translations[lang_code] = {}
                    
                    self._deep_merge(self.translations[lang_code], existing_translations)
                    logger.info(f"Merged existing translations for {lang_code}")
                    
                except Exception as e:
                    logger.warning(f"Failed to load existing translations for {lang_code}: {e}")
    
    def _deep_merge(self, target: Dict, source: Dict):
        """Deep merge two dictionaries."""
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._deep_merge(target[key], value)
            else:
                target[key] = value
    
    def set_language(self, language: str):
        """Set current language."""
        if language in self.translations:
            self.current_language = language
            global current_language
            current_language = language
            logger.debug(f"Language set to: {language}")
        else:
            logger.warning(f"Language {language} not available, using {self.fallback_language}")
            self.current_language = self.fallback_language
    
    def get(self, key: str, language: Optional[str] = None) -> Union[str, List[str], Dict]:
        """Get translation for key with intelligent fallbacks."""
        target_language = language or self.current_language
        
        # Try target language first
        result = self._get_nested_value(self.translations.get(target_language, {}), key)
        
        # Fallback to default language if not found
        if result == key and target_language != self.fallback_language:
            result = self._get_nested_value(self.translations.get(self.fallback_language, {}), key)
        
        # Fallback to intelligent defaults for specific patterns
        if result == key:
            result = self._get_intelligent_fallback(key)
        
        return result
    
    def _get_nested_value(self, data: Dict, key: str):
        """Get nested value using dot notation."""
        try:
            keys = key.split('.')
            current = data
            
            for k in keys:
                if isinstance(current, dict) and k in current:
                    current = current[k]
                else:
                    return key  # Key not found, return original
            
            return current
        except Exception:
            return key
    
    def _get_intelligent_fallback(self, key: str) -> str:
        """Provide intelligent fallbacks for missing keys."""
        fallbacks = {
            "pdf.title": "Broiler Performance Report",
            "pdf.barn_label": "Barn",
            "pdf.report_info": "Report Information",
            "pdf.report_date": "Report Date",
            "pdf.flock_age": "Flock Age",
            "pdf.breed": "Breed",
            "pdf.insights": "Key Insights",
            "pdf.status_overview": "Status Overview",
            "pdf.sections.performance_metrics": "Performance Metrics",
            "pdf.sections.environmental_conditions": "Environmental Conditions",
            "pdf.sections.recommendations": "Recommendations",
            "pdf.current_weight": "Current Weight",
            "pdf.daily_gain": "Daily Gain",
            "pdf.performance_ratio": "Performance Ratio",
            "pdf.barn_temperature": "Barn Temperature",
            "pdf.barn_humidity": "Barn Humidity",
            "pdf.external_temperature": "External Temperature",
            "common.deviation": "Deviation",
            "common.status": "Status",
            "common.range": "Range",
            "common.average_24h": "24h Average",
            "pdf.legal.generated_by": "Generated: {timestamp}",
            "pdf.legal.report_id": "Report ID: {barn_id}_{timestamp}",
            "pdf.legal.copyright": "© 2025 Intelia Systems",
            "pdf.legal.warning": "For veterinary guidance only"
        }
        
        return fallbacks.get(key, key)
    
    def get_performance_recommendations(self, performance_level: str, language: Optional[str] = None) -> Dict[str, List[str]]:
        """Get recommendations for specific performance level."""
        target_language = language or self.current_language
        
        base_key = f"pdf.recommendations.{performance_level}"
        recommendations = {}
        
        # Define recommendation categories by performance level
        categories = {
            'excellent': ['maintenance_items', 'optimization_items', 'monitoring_items'],
            'good': ['improvement_items', 'prevention_items', 'monitoring_items'],
            'attention': ['immediate_items', 'corrective_items', 'management_items'],
            'critical': ['emergency_items', 'intervention_items', 'support_items']
        }
        
        for category in categories.get(performance_level, ['general_items']):
            key = f"{base_key}.{category}"
            items = self.get(key, target_language)
            
            if isinstance(items, list):
                recommendations[category.replace('_items', '')] = items
            elif isinstance(items, str) and items != key:
                recommendations[category.replace('_items', '')] = [items]
        
        return recommendations
    
    def save_enhanced_translations(self, output_dir: Optional[str] = None):
        """Save enhanced translations to files."""
        if output_dir is None:
            output_dir = "core/notifications/translations/locales"
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        for lang_code, translations in self.translations.items():
            lang_file = output_path / f"{lang_code}.json"
            
            try:
                with open(lang_file, 'w', encoding='utf-8') as f:
                    json.dump(translations, f, indent=2, ensure_ascii=False)
                
                logger.info(f"Saved enhanced translations for {lang_code} to {lang_file}")
                
            except Exception as e:
                logger.error(f"Failed to save translations for {lang_code}: {e}")
    
    def validate_performance_templates(self) -> Dict[str, Any]:
        """Validate that all performance templates are available."""
        validation = {
            "valid": True,
            "missing_templates": [],
            "languages_checked": [],
            "performance_levels": ["excellent", "good", "attention", "critical"]
        }
        
        for lang_code in ["en", "fr", "es"]:
            validation["languages_checked"].append(lang_code)
            
            for level in validation["performance_levels"]:
                # Check insights
                insight_key = f"pdf.insights.{level}.performance"
                if self.get(insight_key, lang_code) == insight_key:
                    validation["missing_templates"].append(f"{lang_code}: {insight_key}")
                
                # Check recommendations
                rec_categories = {
                    'excellent': ['maintenance_items', 'optimization_items'],
                    'good': ['improvement_items', 'prevention_items'],
                    'attention': ['immediate_items', 'corrective_items'],
                    'critical': ['emergency_items', 'intervention_items']
                }
                
                for category in rec_categories.get(level, []):
                    rec_key = f"pdf.recommendations.{level}.{category}"
                    if not isinstance(self.get(rec_key, lang_code), list):
                        validation["missing_templates"].append(f"{lang_code}: {rec_key}")
        
        validation["valid"] = len(validation["missing_templates"]) == 0
        return validation


# Global translation manager instance
_intelligent_translation_manager = None

def get_translation_manager() -> IntelligentTranslationManager:
    """Get global intelligent translation manager instance."""
    global _intelligent_translation_manager
    if _intelligent_translation_manager is None:
        _intelligent_translation_manager = IntelligentTranslationManager()
    return _intelligent_translation_manager

def set_language(language: str):
    """Set current language globally."""
    manager = get_translation_manager()
    manager.set_language(language)

def t(key: str, language: Optional[str] = None) -> Union[str, List[str], Dict]:
    """Translation function alias."""
    manager = get_translation_manager()
    return manager.get(key, language)

def get_performance_recommendations(performance_level: str, language: Optional[str] = None) -> Dict[str, List[str]]:
    """Get performance-based recommendations."""
    manager = get_translation_manager()
    return manager.get_performance_recommendations(performance_level, language)

def validate_intelligent_translations() -> Dict[str, Any]:
    """Validate intelligent translation templates."""
    manager = get_translation_manager()
    return manager.validate_performance_templates()

def save_intelligent_translations(output_dir: Optional[str] = None):
    """Save intelligent translations to files."""
    manager = get_translation_manager()
    manager.save_enhanced_translations(output_dir)

if __name__ == "__main__":
    # Test intelligent translation manager
    try:
        print("Testing Intelligent Translation Manager...")
        
        manager = get_translation_manager()
        
        # Test validation
        validation = validate_intelligent_translations()
        print(f"Validation result: {'✅ PASS' if validation['valid'] else '❌ FAIL'}")
        print(f"Languages checked: {validation['languages_checked']}")
        
        if validation['missing_templates']:
            print("Missing templates:")
            for missing in validation['missing_templates'][:5]:  # Show first 5
                print(f"  - {missing}")
        
        # Test performance recommendations
        for level in ["excellent", "good", "attention", "critical"]:
            for lang in ["en", "fr", "es"]:
                recommendations = get_performance_recommendations(level, lang)
                print(f"{level.upper()} ({lang}): {len(recommendations)} categories")
        
        # Test save functionality
        save_intelligent_translations("temp_translations")
        print("✅ Save test completed")
        
        print("🎉 Intelligent Translation Manager test passed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()