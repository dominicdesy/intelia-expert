"""
Script d'analyse de qualité des Q&A
Identifie les meilleures conversations pour améliorer le LLM

Usage:
    python scripts/analyze_qa_quality.py [--min-score 8.0] [--limit 50]

Output:
    - Rapport texte des top Q&A candidates
    - Fichier JSON avec les résultats détaillés
    - Pas de modification de la base de données (READ-ONLY)
"""

import sys
import os
from pathlib import Path
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import re
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import get_pg_connection
from psycopg2.extras import RealDictCursor


class QAQualityAnalyzer:
    """Analyseur de qualité des Q&A"""

    def __init__(self):
        self.weights = {
            'feedback': 0.30,
            'confidence': 0.25,
            'popularity': 0.20,
            'freshness': 0.10,
            'completeness': 0.10,
            'clarity': 0.05
        }

    def calculate_feedback_score(self, feedback: Optional[int], feedback_count: int = 1) -> float:
        """
        Score basé sur le feedback utilisateur (0-10)

        Args:
            feedback: 1 (positive), -1 (negative), 0 (neutral), None (no feedback)
            feedback_count: Nombre de feedbacks similaires
        """
        if feedback is None:
            return 5.0  # Neutre positif

        if feedback == 1:  # Thumbs up
            base_score = 10.0
            # Bonus si plusieurs feedbacks positifs
            bonus = min(feedback_count - 1, 5) * 0.5
            return min(base_score + bonus, 10.0)

        elif feedback == -1:  # Thumbs down
            return 0.0  # Éliminatoire

        else:  # Neutral
            return 5.0

    def calculate_confidence_score(self, confidence: Optional[float]) -> float:
        """Score basé sur la confiance du système (0-10)"""
        if confidence is None:
            return 5.0

        if confidence >= 0.9:
            return 10.0
        elif confidence >= 0.8:
            return 8.0
        elif confidence >= 0.7:
            return 6.0
        elif confidence >= 0.6:
            return 4.0
        elif confidence >= 0.5:
            return 2.0
        else:
            return 0.0  # Confidence trop faible

    def calculate_popularity_score(self, occurrence_count: int) -> float:
        """Score basé sur la popularité (0-10)"""
        if occurrence_count >= 10:
            return 10.0
        elif occurrence_count >= 5:
            return 7.0
        elif occurrence_count >= 2:
            return 4.0
        else:
            return 0.0  # Questions uniques = moins prioritaires

    def calculate_freshness_score(self, created_at: datetime) -> float:
        """Score basé sur la fraîcheur (0-5)"""
        now = datetime.now()
        age_days = (now - created_at).days

        if age_days < 30:
            return 5.0
        elif age_days < 90:
            return 4.0
        elif age_days < 180:
            return 3.0
        elif age_days < 365:
            return 2.0
        else:
            return 0.0

    def calculate_completeness_score(self, response: str) -> float:
        """Score basé sur la complétude de la réponse (0-10)"""
        length = len(response)

        # Score de base sur la longueur
        if 200 <= length <= 800:
            base_score = 5.0
        elif 100 <= length < 200:
            base_score = 3.0
        elif length > 800:
            base_score = 3.0
        elif 50 <= length < 100:
            base_score = 1.0
        else:
            return 0.0  # Trop court

        # Bonus: contient des chiffres (données numériques)
        if re.search(r'\d+\.?\d*\s*(kg|g|%|jours?|semaines?)', response, re.IGNORECASE):
            base_score += 2.0

        # Bonus: bien structuré
        if any(marker in response for marker in ['\n-', '\n•', '\n*', '1.', '2.']):
            base_score += 2.0

        # Bonus: mentions de sources
        if any(term in response.lower() for term in ['selon', 'standard', 'norme', 'guide']):
            base_score += 1.0

        return min(base_score, 10.0)

    def calculate_clarity_score(self, question: str) -> float:
        """Score basé sur la clarté de la question (0-5)"""
        length = len(question)

        # Score de base sur la longueur
        if 20 <= length <= 150:
            base_score = 3.0
        elif 10 <= length < 20:
            base_score = 1.0
        elif length > 150:
            base_score = 1.0
        else:
            return 0.0  # Trop court

        # Bonus: formulation interrogative
        if any(marker in question.lower() for marker in ['?', 'quel', 'comment', 'combien', 'quoi', 'pourquoi']):
            base_score += 1.0

        # Bonus: contient des entités spécifiques (race, âge, etc.)
        if re.search(r'(ross|cobb|hubbard|isa|lohmann)', question, re.IGNORECASE):
            base_score += 1.0

        return min(base_score, 5.0)

    def calculate_total_score(self, qa_data: Dict[str, Any]) -> float:
        """Calcule le score total pondéré (0-10)"""
        scores = {
            'feedback': self.calculate_feedback_score(
                qa_data.get('feedback'),
                qa_data.get('feedback_count', 1)
            ),
            'confidence': self.calculate_confidence_score(qa_data.get('response_confidence')),
            'popularity': self.calculate_popularity_score(qa_data.get('occurrence_count', 1)),
            'freshness': self.calculate_freshness_score(qa_data['created_at']),
            'completeness': self.calculate_completeness_score(qa_data['response']),
            'clarity': self.calculate_clarity_score(qa_data['question'])
        }

        # Calcul pondéré
        total = sum(scores[key] * self.weights[key] * 10 for key in scores.keys())

        # Normaliser à 0-10
        normalized = total / 10.0

        return round(normalized, 2), scores

    def should_exclude(self, qa_data: Dict[str, Any]) -> tuple[bool, str]:
        """
        Détermine si une Q&A doit être exclue

        Returns:
            (should_exclude: bool, reason: str)
        """
        # Feedback négatif = exclusion immédiate
        if qa_data.get('feedback') == -1:
            return True, "Feedback négatif"

        # Confidence trop faible
        if qa_data.get('response_confidence', 0) < 0.5:
            return True, f"Confidence trop faible ({qa_data.get('response_confidence', 0):.2f})"

        # Question trop courte
        if len(qa_data['question']) < 10:
            return True, "Question trop courte"

        # Réponse trop courte
        if len(qa_data['response']) < 30:
            return True, "Réponse trop courte"

        # Patterns de spam/test
        spam_patterns = [
            r'^test\s*$',
            r'^hello\s*$',
            r'^bonjour\s*$',
            r'^\d+$',
            r'^[a-z]\s*$'
        ]
        question_lower = qa_data['question'].lower().strip()
        for pattern in spam_patterns:
            if re.match(pattern, question_lower):
                return True, "Pattern spam/test détecté"

        return False, ""

    def fetch_qa_data(self, limit: int = 1000) -> List[Dict[str, Any]]:
        """
        Récupère les données Q&A de la base de données

        Returns:
            Liste de dictionnaires avec question, réponse, metadata
        """
        print("\n[1/4] Récupération des données depuis PostgreSQL...")

        query = """
        WITH user_messages AS (
            SELECT
                m.conversation_id,
                m.content as question,
                m.created_at,
                m.sequence_number
            FROM messages m
            WHERE m.role = 'user'
        ),
        assistant_messages AS (
            SELECT
                m.conversation_id,
                m.content as response,
                m.response_source,
                m.response_confidence,
                m.processing_time_ms,
                m.feedback,
                m.feedback_comment,
                m.sequence_number
            FROM messages m
            WHERE m.role = 'assistant'
        )
        SELECT
            c.id as conversation_id,
            c.session_id,
            c.user_id,
            c.language,
            c.created_at,
            um.question,
            am.response,
            am.response_source,
            am.response_confidence,
            am.processing_time_ms,
            am.feedback,
            am.feedback_comment
        FROM conversations c
        JOIN user_messages um ON c.id = um.conversation_id
        JOIN assistant_messages am ON c.id = am.conversation_id
            AND am.sequence_number = um.sequence_number + 1
        WHERE
            am.response_source IN ('rag_success', 'rag')  -- Seulement les réponses documentées
            AND c.created_at >= NOW() - INTERVAL '6 months'  -- Derniers 6 mois
        ORDER BY c.created_at DESC
        LIMIT %s
        """

        try:
            with get_pg_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(query, (limit,))
                    results = cur.fetchall()

                    # Convert to list of dicts
                    qa_list = [dict(row) for row in results]

                    print(f"   [OK] {len(qa_list)} paires Q&A récupérées")
                    return qa_list

        except Exception as e:
            print(f"   [ERROR] Erreur: {e}")
            return []

    def analyze_qa_quality(self, limit: int = 1000, min_score: float = 7.0) -> Dict[str, Any]:
        """
        Analyse complète de la qualité des Q&A

        Args:
            limit: Nombre max de Q&A à analyser
            min_score: Score minimum pour être considéré comme candidate

        Returns:
            Dictionnaire avec statistiques et top candidates
        """
        # Fetch data
        qa_data = self.fetch_qa_data(limit)

        if not qa_data:
            return {
                "error": "Aucune donnée récupérée",
                "analyzed_count": 0,
                "candidates": []
            }

        print(f"\n[2/4] Analyse de {len(qa_data)} paires Q&A...")

        # Score each Q&A
        scored_qa = []
        excluded_qa = []

        for qa in qa_data:
            # Check exclusion criteria
            should_exclude, reason = self.should_exclude(qa)

            if should_exclude:
                excluded_qa.append({
                    'question': qa['question'][:100],
                    'reason': reason
                })
                continue

            # Calculate score
            total_score, component_scores = self.calculate_total_score(qa)

            scored_qa.append({
                'conversation_id': str(qa['conversation_id']),
                'question': qa['question'],
                'response': qa['response'],
                'language': qa['language'],
                'created_at': qa['created_at'].isoformat(),
                'response_confidence': qa['response_confidence'],
                'feedback': qa['feedback'],
                'feedback_comment': qa['feedback_comment'],
                'processing_time_ms': qa['processing_time_ms'],
                'total_score': total_score,
                'component_scores': component_scores
            })

        print(f"   [OK] {len(scored_qa)} Q&A scored")
        print(f"   [ERROR] {len(excluded_qa)} Q&A exclues")

        # Sort by score
        print(f"\n[3/4] Tri par score...")
        scored_qa.sort(key=lambda x: x['total_score'], reverse=True)

        # Filter by minimum score
        candidates = [qa for qa in scored_qa if qa['total_score'] >= min_score]

        print(f"   [OK] {len(candidates)} candidates (score >= {min_score})")

        # Statistics
        print(f"\n[4/4] Calcul des statistiques...")

        if scored_qa:
            avg_score = sum(qa['total_score'] for qa in scored_qa) / len(scored_qa)
            max_score = scored_qa[0]['total_score']
            min_score_found = scored_qa[-1]['total_score']
        else:
            avg_score = 0
            max_score = 0
            min_score_found = 0

        stats = {
            'total_analyzed': len(qa_data),
            'total_scored': len(scored_qa),
            'total_excluded': len(excluded_qa),
            'total_candidates': len(candidates),
            'avg_score': round(avg_score, 2),
            'max_score': max_score,
            'min_score': min_score_found,
            'exclusion_reasons': self._count_exclusion_reasons(excluded_qa)
        }

        print(f"   [OK] Statistiques calculées")

        return {
            'metadata': {
                'analysis_date': datetime.now().isoformat(),
                'min_score_threshold': min_score,
                'analyzer_version': '1.0.0'
            },
            'statistics': stats,
            'top_candidates': candidates[:50],  # Top 50
            'excluded_sample': excluded_qa[:20]  # Sample of exclusions
        }

    def _count_exclusion_reasons(self, excluded_qa: List[Dict]) -> Dict[str, int]:
        """Compte les raisons d'exclusion"""
        reasons = {}
        for item in excluded_qa:
            reason = item['reason']
            reasons[reason] = reasons.get(reason, 0) + 1
        return reasons

    def generate_report(self, analysis_results: Dict[str, Any], output_file: Optional[str] = None) -> str:
        """
        Génère un rapport texte lisible

        Args:
            analysis_results: Résultats de l'analyse
            output_file: Chemin du fichier de sortie (optionnel)

        Returns:
            Rapport en texte
        """
        stats = analysis_results['statistics']
        candidates = analysis_results['top_candidates']

        report = []
        report.append("=" * 80)
        report.append("RAPPORT D'ANALYSE DE QUALITÉ DES Q&A")
        report.append("=" * 80)
        report.append(f"\nDate: {analysis_results['metadata']['analysis_date']}")
        report.append(f"Version: {analysis_results['metadata']['analyzer_version']}")
        report.append(f"Seuil minimum: {analysis_results['metadata']['min_score_threshold']}/10")

        report.append("\n" + "-" * 80)
        report.append("STATISTIQUES GLOBALES")
        report.append("-" * 80)
        report.append(f"Total analysé:        {stats['total_analyzed']}")
        report.append(f"Total scoré:          {stats['total_scored']}")
        report.append(f"Total exclu:          {stats['total_excluded']}")
        report.append(f"Total candidates:     {stats['total_candidates']}")
        report.append(f"\nScore moyen:          {stats['avg_score']}/10")
        report.append(f"Score maximum:        {stats['max_score']}/10")
        report.append(f"Score minimum:        {stats['min_score']}/10")

        report.append("\n" + "-" * 80)
        report.append("RAISONS D'EXCLUSION")
        report.append("-" * 80)
        for reason, count in sorted(stats['exclusion_reasons'].items(), key=lambda x: x[1], reverse=True):
            report.append(f"{reason:40s} {count:5d}")

        report.append("\n" + "=" * 80)
        report.append(f"TOP {min(20, len(candidates))} CANDIDATES")
        report.append("=" * 80)

        for i, qa in enumerate(candidates[:20], 1):
            report.append(f"\n[{i}] SCORE: {qa['total_score']:.2f}/10")
            report.append("-" * 80)
            report.append(f"Question:    {qa['question']}")
            report.append(f"Réponse:     {qa['response'][:150]}...")
            report.append(f"Langue:      {qa['language']}")
            report.append(f"Confidence:  {qa['response_confidence']:.2f}")
            report.append(f"Feedback:    {self._format_feedback(qa['feedback'])}")
            report.append(f"Date:        {qa['created_at'][:10]}")

            report.append(f"\nScores détaillés:")
            for key, value in qa['component_scores'].items():
                weight = self.weights[key]
                report.append(f"  - {key:15s}: {value:5.2f}/10 (poids: {weight*100:.0f}%)")

        report_text = "\n".join(report)

        # Save to file if specified
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(report_text)
            print(f"\n[OK] Rapport sauvegardé: {output_file}")

        return report_text

    def _format_feedback(self, feedback: Optional[int]) -> str:
        """Formate le feedback pour l'affichage"""
        if feedback is None:
            return "Aucun"
        elif feedback == 1:
            return "Positif (+1)"
        elif feedback == -1:
            return "Négatif (-1)"
        else:
            return "Neutre (0)"


def main():
    """Point d'entrée principal"""
    import argparse

    parser = argparse.ArgumentParser(description='Analyse de qualité des Q&A')
    parser.add_argument('--min-score', type=float, default=7.0,
                       help='Score minimum pour être considéré comme candidate (default: 7.0)')
    parser.add_argument('--limit', type=int, default=1000,
                       help='Nombre max de Q&A à analyser (default: 1000)')
    parser.add_argument('--output', type=str, default=None,
                       help='Fichier de sortie pour le rapport (default: auto-generate)')

    args = parser.parse_args()

    print("\n" + "=" * 80)
    print("ANALYSEUR DE QUALITÉ Q&A - VERSION 1.0.0")
    print("=" * 80)
    print("\nMode: READ-ONLY (aucune modification de la base de données)")
    print(f"Paramètres:")
    print(f"  - Score minimum: {args.min_score}/10")
    print(f"  - Limite analyse: {args.limit} Q&A")

    # Initialize analyzer
    analyzer = QAQualityAnalyzer()

    # Run analysis
    results = analyzer.analyze_qa_quality(
        limit=args.limit,
        min_score=args.min_score
    )

    # Generate output filename if not specified
    if not args.output:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        args.output = f'qa_analysis_{timestamp}.txt'

    # Generate report
    print("\n" + "=" * 80)
    print("GÉNÉRATION DU RAPPORT")
    print("=" * 80)

    report = analyzer.generate_report(results, args.output)

    # Save JSON results
    json_output = args.output.replace('.txt', '.json')
    with open(json_output, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"[OK] Résultats JSON sauvegardés: {json_output}")

    print("\n" + "=" * 80)
    print("ANALYSE TERMINÉE")
    print("=" * 80)
    print(f"\n {results['statistics']['total_candidates']} candidates identifiées")
    print(f" Rapports générés:")
    print(f"   - {args.output} (texte)")
    print(f"   - {json_output} (JSON)")

    if results['statistics']['total_candidates'] > 0:
        print(f"\n Prochaines étapes:")
        print(f"   1. Review les top candidates dans le rapport")
        print(f"   2. Valider manuellement les Q&A de qualité")
        print(f"   3. Utiliser pour cache warming ou few-shot examples")
    else:
        print(f"\n[WARNING]  Aucune candidate trouvée avec score >= {args.min_score}")
        print(f"   Essayez avec --min-score plus bas (ex: --min-score 6.0)")

    print("")


if __name__ == "__main__":
    main()
