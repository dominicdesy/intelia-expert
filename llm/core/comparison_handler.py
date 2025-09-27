# -*- coding: utf-8 -*-
"""
comparison_handler.py - Gestion des requêtes comparatives
Orchestre les requêtes multiples et calculs pour les comparaisons
"""

import logging
from typing import Dict, List, Any, Optional
from .metric_calculator import MetricCalculator

logger = logging.getLogger(__name__)


class ComparisonHandler:
    """Gère les requêtes comparatives avec requêtes multiples et calculs"""
    
    def __init__(self, postgresql_system):
        """
        Args:
            postgresql_system: Instance de PostgreSQLSystem pour exécuter les requêtes
        """
        self.postgresql_system = postgresql_system
        self.calculator = MetricCalculator()
    
    async def handle_comparative_query(
        self,
        query: str,
        preprocessed: Dict[str, Any],
        top_k: int = 10
    ) -> Dict[str, Any]:
        """
        Traite une requête comparative
        
        Args:
            query: Requête utilisateur originale
            preprocessed: Résultat du preprocessing avec comparative_info
            top_k: Nombre de résultats par requête
        
        Returns:
            {
                'results': List[Dict],  # Résultats de chaque requête
                'comparison': ComparisonResult,
                'success': bool,
                'error': Optional[str]
            }
        """
        try:
            comparative_info = preprocessed.get('comparative_info', {})
            comparison_entities = preprocessed.get('comparison_entities', [])
            
            if not comparison_entities:
                logger.warning("No comparison entities found")
                return {
                    'success': False,
                    'error': 'No entities to compare',
                    'results': [],
                    'comparison': None
                }
            
            logger.info(
                f"Handling comparative query with {len(comparison_entities)} entity sets"
            )
            
            # Exécuter une requête pour chaque jeu d'entités
            results = []
            for entity_set in comparison_entities:
                result = await self._execute_single_query(
                    query, entity_set, top_k
                )
                if result:
                    results.append(result)
            
            if len(results) < 2:
                return {
                    'success': False,
                    'error': f'Insufficient results: found {len(results)}, need 2',
                    'results': results,
                    'comparison': None
                }
            
            # Calculer la comparaison
            comparison = self.calculator.calculate_comparison(results)
            
            logger.info(
                f"Comparison successful: {comparison.label1} vs {comparison.label2}"
            )
            
            return {
                'success': True,
                'results': results,
                'comparison': comparison,
                'operation': comparative_info.get('operation'),
                'comparison_type': comparative_info.get('type')
            }
            
        except Exception as e:
            logger.error(f"Error handling comparative query: {e}")
            return {
                'success': False,
                'error': str(e),
                'results': [],
                'comparison': None
            }
    
    async def _execute_single_query(
        self,
        query: str,
        entities: Dict[str, Any],
        top_k: int
    ) -> Optional[Dict[str, Any]]:
        """
        Exécute une requête PostgreSQL avec un jeu d'entités spécifique
        
        Args:
            query: Requête originale
            entities: Jeu d'entités pour cette requête
            top_k: Nombre de résultats
        
        Returns:
            {
                'sex': str,  # ou autre label
                'label': str,
                'data': List[Dict],  # Résultats bruts
                'best_metric': Dict  # Meilleur résultat
            }
        """
        try:
            # Extraire le label de comparaison
            comparison_label = entities.get('_comparison_label', 'unknown')
            comparison_dimension = entities.get('_comparison_dimension', 'sex')
            
            # Créer une copie sans les métadonnées internes
            clean_entities = {
                k: v for k, v in entities.items() 
                if not k.startswith('_')
            }
            
            logger.debug(
                f"Executing query for {comparison_dimension}={comparison_label}"
            )
            
            # Appel au système PostgreSQL avec strict_sex_match=True
            result = await self.postgresql_system.search_metrics(
                query=query,
                entities=clean_entities,
                top_k=top_k,
                strict_sex_match=True  # Mode strict pour comparaisons
            )
            
            # Vérifier si on a des résultats
            if not result or not hasattr(result, 'context_docs'):
                logger.warning(f"No results for {comparison_label}")
                return None
            
            context_docs = result.context_docs
            if not context_docs or len(context_docs) == 0:
                logger.warning(f"Empty context_docs for {comparison_label}")
                return None
            
            # Convertir les documents en format exploitable
            metrics = self._extract_metrics_from_docs(context_docs)
            
            if not metrics:
                logger.warning(f"No metrics extracted for {comparison_label}")
                return None
            
            # Sélectionner le meilleur résultat
            best_metric = self._select_best_metric(metrics, entities)
            
            return {
                comparison_dimension: comparison_label,
                'label': comparison_label,
                'data': [best_metric],  # Format attendu par calculator
                'all_metrics': metrics,
                'entity_set': clean_entities
            }
            
        except Exception as e:
            logger.error(f"Error executing single query: {e}")
            return None
    
    def _extract_metrics_from_docs(
        self, 
        context_docs: List[Dict]
    ) -> List[Dict[str, Any]]:
        """Extrait les métriques des documents de contexte"""
        metrics = []
        
        # Debug: inspecter le premier document
        if context_docs and len(context_docs) > 0:
            first_doc = context_docs[0]
            logger.debug(f"First doc type: {type(first_doc)}")
            if isinstance(first_doc, dict):
                logger.debug(f"First doc keys: {list(first_doc.keys())}")
                if 'metadata' in first_doc:
                    logger.debug(f"Metadata keys: {list(first_doc['metadata'].keys())}")
                if 'content' in first_doc:
                    logger.debug(f"Content preview: {first_doc['content'][:200]}")
        
        for doc in context_docs:
            if not isinstance(doc, dict):
                logger.warning(f"Skipping non-dict doc: {type(doc)}")
                continue
            
            metadata = doc.get('metadata', {})
            content = doc.get('content', '')
            
            # Extraire les infos du metadata
            metric_name = metadata.get('metric_name', '')
            unit = ''
            value_numeric = None
            
            # Parser le content pour extraire value_numeric et unit
            # Le format attendu est quelque chose comme:
            # "**metric_name**\nStrain: 500\nSex: male\nValue: 1.081 ratio\nAge: 17 days"
            
            if content:
                # Chercher pattern "Value: <number> <unit>"
                import re
                value_match = re.search(r'Value:\s*([0-9.]+)\s*(\w*)', content)
                if value_match:
                    try:
                        value_numeric = float(value_match.group(1))
                        unit = value_match.group(2) if value_match.group(2) else ''
                        
                        metrics.append({
                            'value_numeric': value_numeric,
                            'unit': unit,
                            'metric_name': metric_name,
                            'metadata': metadata
                        })
                        logger.debug(f"Extracted: {metric_name} = {value_numeric} {unit}")
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Failed to parse value from: {value_match.group(1)}, error: {e}")
                else:
                    logger.debug(f"No value pattern found in content: {content[:100]}")
        
        logger.info(f"Successfully extracted {len(metrics)} metrics from {len(context_docs)} docs")
        return metrics
    
    def _select_best_metric(
        self, 
        metrics: List[Dict], 
        entities: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Sélectionne la meilleure métrique selon les critères"""
        if not metrics:
            return {}
        
        # Pour l'instant, prendre la première (déjà triée par pertinence)
        # TODO: Améliorer la sélection si nécessaire
        best = metrics[0]
        
        logger.debug(
            f"Selected best metric: {best.get('metric_name')} = "
            f"{best.get('value_numeric')} {best.get('unit')}"
        )
        
        return best
    
    async def generate_comparative_response(
        self,
        query: str,
        comparison_result: Dict[str, Any],
        language: str = "fr"
    ) -> str:
        """
        Génère une réponse naturelle pour une comparaison
        
        Args:
            query: Requête originale
            comparison_result: Résultat de handle_comparative_query
            language: Langue de la réponse
        
        Returns:
            Texte de réponse formaté
        """
        if not comparison_result.get('success'):
            error = comparison_result.get('error', 'Unknown error')
            if language == "fr":
                return f"Impossible de comparer: {error}"
            else:
                return f"Cannot compare: {error}"
        
        comparison = comparison_result['comparison']
        results = comparison_result['results']
        
        # Déterminer le nom de la métrique
        metric_name = "métrique"
        if results and len(results) > 0:
            first_result = results[0]
            if 'data' in first_result and len(first_result['data']) > 0:
                metric_name = first_result['data'][0].get('metric_name', metric_name)
        
        # Utiliser le formatter du calculator
        formatted_text = self.calculator.format_comparison_text(
            comparison, metric_name, language
        )
        
        # Ajouter contexte additionnel
        if language == "fr":
            formatted_text += "\n\n*Source: Données techniques avicoles*"
        else:
            formatted_text += "\n\n*Source: Poultry technical data*"
        
        return formatted_text


# Tests unitaires
if __name__ == "__main__":
    import asyncio
    
    async def test_comparison_handler():
        """Test avec des données mockées"""
        
        # Mock PostgreSQL System
        class MockPostgreSQLSystem:
            async def search_metrics(self, query, entities, top_k, strict_sex_match=False):
                # Simuler des résultats différents selon le sexe
                sex = entities.get('sex', 'male')
                
                class MockResult:
                    def __init__(self, sex_val):
                        self.context_docs = [{
                            'metadata': {
                                'value_numeric': 1.081 if sex_val == 'male' else 1.045,
                                'unit': 'ratio',
                                'metric_name': 'feed_conversion_ratio'
                            }
                        }]
                
                return MockResult(sex)
        
        mock_system = MockPostgreSQLSystem()
        handler = ComparisonHandler(mock_system)
        
        # Simuler un preprocessing comparatif
        preprocessed = {
            'comparative_info': {
                'is_comparative': True,
                'type': 'difference',
                'operation': 'subtract'
            },
            'comparison_entities': [
                {'sex': 'male', '_comparison_label': 'male', '_comparison_dimension': 'sex'},
                {'sex': 'female', '_comparison_label': 'female', '_comparison_dimension': 'sex'}
            ]
        }
        
        result = await handler.handle_comparative_query(
            "Quelle est la différence entre mâle et femelle ?",
            preprocessed
        )
        
        print("Comparison Result:")
        print(f"  Success: {result['success']}")
        if result['success']:
            comp = result['comparison']
            print(f"  {comp.label1}: {comp.value1}")
            print(f"  {comp.label2}: {comp.value2}")
            print(f"  Difference: {comp.absolute_difference:.3f}")
            
            # Générer la réponse
            response = await handler.generate_comparative_response(
                "Test query", result, "fr"
            )
            print("\nGenerated Response:")
            print(response)
    
    asyncio.run(test_comparison_handler())