# QA Quality Monitoring Tool

## 📋 Vue d'ensemble

Outil automatisé d'analyse de la qualité des réponses Q&A utilisant l'IA (OpenAI GPT-3.5-turbo) pour détecter les réponses problématiques et aider à stabiliser le système.

### Objectifs
- ✅ Détecter automatiquement les réponses incorrectes, incomplètes ou hors-sujet
- ✅ Prioriser les Q&A nécessitant une révision manuelle
- ✅ Améliorer progressivement la qualité du système RAG
- ✅ Fournir des métriques de qualité aux administrateurs

---

## 🏗️ Architecture

### Approche Hybride (C)

1. **Analyse en Temps Réel** - Déclenchée automatiquement pour:
   - ✅ Feedback utilisateur négatif
   - ✅ Confiance système très basse (< 0.3)
   - ✅ Source `openai_fallback` avec confiance < 0.5
   - ✅ Source inconnue ou manquante

2. **Analyse en Batch** - Exécutée manuellement ou via cron:
   - ✅ 50-500 Q&A à la fois
   - ✅ Priorité: feedback négatif > faible confiance > anciennes
   - ✅ Évite la ré-analyse (sauf si `force_recheck=true`)

### Technologies
- **AI Model**: GPT-3.5-turbo (économique, ~$0.002 par analyse)
- **Base de données**: PostgreSQL (table `qa_quality_checks`)
- **API**: FastAPI avec endpoints admin-only
- **Frontend**: React/TypeScript (onglet Q&A Stats)

---

## 📊 Base de Données

### Table: `qa_quality_checks`

```sql
CREATE TABLE qa_quality_checks (
    id UUID PRIMARY KEY,
    conversation_id UUID REFERENCES conversations(id),
    message_id UUID REFERENCES messages(id),
    user_id UUID NOT NULL,

    -- Contenu Q&A
    question TEXT NOT NULL,
    response TEXT NOT NULL,
    response_source VARCHAR(50),
    response_confidence DECIMAL(3,2),

    -- Résultats d'analyse
    quality_score DECIMAL(3,1),  -- 0-10
    is_problematic BOOLEAN,
    problem_category VARCHAR(50),  -- incorrect|incomplete|off_topic|generic|contradictory|hallucination
    problems JSONB,  -- Array des problèmes détectés
    recommendation TEXT,
    analysis_confidence DECIMAL(3,2),  -- 0-1

    -- Métadonnées analyse
    analysis_trigger VARCHAR(50),  -- manual|batch|realtime|negative_feedback
    analysis_model VARCHAR(50),
    analysis_prompt_version VARCHAR(20),

    -- Workflow de révision
    analyzed_at TIMESTAMP,
    reviewed BOOLEAN DEFAULT false,
    reviewed_at TIMESTAMP,
    reviewed_by UUID,
    reviewer_notes TEXT,
    false_positive BOOLEAN DEFAULT false
);
```

### Vue: `problematic_qa_with_users`

Join automatique avec `conversations` pour faciliter les requêtes.

---

## 🔌 API Endpoints

Tous les endpoints nécessitent des **droits administrateur**.

### 1. GET `/api/v1/qa-quality/problematic`

Récupère les Q&A problématiques avec pagination et filtres.

**Query Parameters:**
- `page` (int, default=1)
- `limit` (int, default=20, max=100)
- `category` (string, optional): incorrect|incomplete|off_topic|generic|contradictory|hallucination
- `reviewed` (boolean, optional)
- `min_score` (float, optional): 0-10
- `max_score` (float, optional): 0-10

**Response:**
```json
{
  "problematic_qa": [
    {
      "id": "uuid",
      "conversation_id": "uuid",
      "user_email": "user@example.com",
      "user_name": "John Doe",
      "question": "Comment nourrir mes poules?",
      "response": "Les poules mangent des graines...",
      "quality_score": 3.5,
      "problem_category": "incomplete",
      "problems": [
        "Manque de détails sur les quantités",
        "Pas de mention des minéraux essentiels"
      ],
      "recommendation": "Ajouter des informations sur...",
      "analysis_confidence": 0.85,
      "analyzed_at": "2025-10-11T12:00:00",
      "reviewed": false
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 45,
    "pages": 3,
    "has_next": true,
    "has_prev": false
  }
}
```

---

### 2. POST `/api/v1/qa-quality/analyze-batch`

Lance une analyse batch de Q&A.

**Query Parameters:**
- `limit` (int, default=50, max=500): Nombre de Q&A à analyser
- `force_recheck` (boolean, default=false): Ré-analyser les Q&A déjà vérifiées

**Response:**
```json
{
  "status": "completed",
  "analyzed_count": 50,
  "problematic_found": 8,
  "errors": 0,
  "timestamp": "2025-10-11T12:00:00"
}
```

**Coûts estimés:**
- 50 Q&A: ~$0.10
- 100 Q&A: ~$0.20
- 500 Q&A: ~$1.00

---

### 3. PATCH `/api/v1/qa-quality/{check_id}/review`

Marque une Q&A comme reviewée ou faux positif.

**Body:**
```json
{
  "reviewed": true,
  "false_positive": false,
  "reviewer_notes": "Réponse correcte après vérification manuelle"
}
```

**Response:**
```json
{
  "id": "uuid",
  "reviewed": true,
  "false_positive": false,
  "message": "QA check updated successfully"
}
```

---

### 4. GET `/api/v1/qa-quality/stats`

Statistiques globales de qualité Q&A.

**Query Parameters:**
- `days` (int, default=30, max=365)

**Response:**
```json
{
  "period_days": 30,
  "total_analyzed": 456,
  "total_problematic": 78,
  "problematic_rate": 17.1,
  "total_reviewed": 45,
  "total_false_positives": 5,
  "avg_quality_score": 7.2,
  "avg_confidence": 0.82,
  "category_distribution": {
    "incomplete": 32,
    "incorrect": 18,
    "generic": 15,
    "off_topic": 8,
    "contradictory": 3,
    "hallucination": 2
  },
  "timeline": [
    {
      "date": "2025-10-11",
      "total": 25,
      "problematic": 4
    }
  ]
}
```

---

## 🤖 Service d'Analyse

### QAQualityAnalyzer Class

**Fichier**: `backend/app/services/qa_quality_analyzer.py`

**Méthode principale**: `analyze_qa()`

**Paramètres:**
- `question` (str): Question utilisateur
- `response` (str): Réponse du système
- `response_source` (str, optional): rag|openai_fallback|table_lookup
- `response_confidence` (float, optional): 0-1
- `context_docs` (list, optional): Documents de contexte utilisés
- `trigger` (str): manual|batch|realtime|negative_feedback

**Retour:**
```python
{
    "quality_score": 7.5,  # 0-10
    "is_problematic": False,
    "problem_category": "none",
    "problems": [],
    "recommendation": "Réponse satisfaisante",
    "analysis_confidence": 0.85,
    "scores_detail": {
        "accuracy": 8,
        "relevance": 9,
        "completeness": 7,
        "coherence": 8
    },
    "reasoning": "La réponse est techniquement correcte...",
    "tokens_used": 650,
    "cost_estimate": 0.0007
}
```

---

## 🎯 Critères de Détection

### is_problematic = true SI:

1. **Score global < 5/10**
2. **Informations incorrectes** - Erreurs factuelles, conseils dangereux
3. **Hors sujet** - Réponse ne correspond pas à la question
4. **Réponse générique** - < 100 caractères ou trop vague
5. **Informations manquantes** - Éléments critiques omis
6. **Contradictions** - Affirmations contradictoires
7. **Hallucination** - Invente des faits non vérifiables

### Catégories de Problèmes

- `incorrect`: Informations factuellement fausses
- `incomplete`: Manque d'informations essentielles
- `off_topic`: Réponse ne correspond pas à la question
- `generic`: Trop vague, pas spécifique à l'aviculture
- `contradictory`: Contradictions internes
- `hallucination`: Invention de faits/statistiques

---

## 💰 Coûts et Optimisations

### Modèle GPT-3.5-turbo

**Prix:** ~$0.002 par analyse (1000 tokens)

**Estimations mensuelles:**
- 100 Q&A/jour: ~$6/mois
- 500 Q&A/jour: ~$30/mois
- 1000 Q&A/jour: ~$60/mois

### Optimisations

1. **Analyse sélective** (Approche Hybride C):
   - Temps réel uniquement pour cas suspects
   - Batch pour analyse systématique
   - Évite la ré-analyse inutile

2. **Utilisation de GPT-3.5-turbo**:
   - 10x moins cher que GPT-4
   - Suffisant pour la détection de qualité
   - Peut passer à GPT-4 pour cas complexes

3. **Cache des résultats**:
   - Ne ré-analyse pas les Q&A déjà vérifiées
   - Sauf si `force_recheck=true`

---

## 🚀 Utilisation

### 1. Migration de la Base de Données

```bash
psql -d your_database -f backend/migrations/create_qa_quality_checks.sql
```

### 2. Configuration

Variables d'environnement requises:
```bash
OPENAI_API_KEY=sk-...
DATABASE_URL=postgresql://...
```

### 3. Analyse Manuelle (Batch)

Via API:
```bash
curl -X POST "https://api.intelia.com/api/v1/qa-quality/analyze-batch?limit=100" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

Via Python:
```python
from app.services.qa_quality_analyzer import qa_analyzer

result = await qa_analyzer.analyze_qa(
    question="Comment nourrir mes poules?",
    response="Les poules mangent des graines...",
    response_source="rag",
    response_confidence=0.7
)

print(f"Score: {result['quality_score']}")
print(f"Problématique: {result['is_problematic']}")
```

### 4. Intégration Temps Réel

Dans votre flux de génération de réponses:

```python
# Après génération de la réponse
if qa_analyzer.should_analyze_realtime(
    response_source=response_source,
    response_confidence=confidence,
    feedback=user_feedback
):
    # Analyse asynchrone
    analysis = await qa_analyzer.analyze_qa(
        question=user_question,
        response=generated_response,
        response_source=response_source,
        response_confidence=confidence,
        trigger="realtime"
    )

    # Sauvegarder en DB
    save_quality_check(analysis)
```

---

## 📈 Métriques de Succès

### KPIs à Suivre

1. **Taux de problèmes** (target: < 10%)
2. **Score qualité moyen** (target: > 7/10)
3. **Taux de faux positifs** (target: < 5%)
4. **Temps de révision** moyen
5. **Distribution des catégories** de problèmes

### Amélioration Continue

1. Analyser les patterns de problèmes récurrents
2. Ajuster les prompts du RAG
3. Améliorer les documents sources
4. Affiner les critères de détection
5. Former le système sur les vrais/faux positifs

---

## 🔧 Maintenance

### Batch Analysis Cron Job

Recommandation: Analyser les nouvelles Q&A quotidiennement

```cron
# Tous les jours à 2h du matin
0 2 * * * curl -X POST "https://api.intelia.com/api/v1/qa-quality/analyze-batch?limit=200"
```

### Nettoyage

Archiver les analyses > 6 mois:
```sql
-- Archiver les anciennes analyses
DELETE FROM qa_quality_checks
WHERE analyzed_at < NOW() - INTERVAL '6 months'
  AND reviewed = true;
```

---

## 🎨 Frontend (À implémenter)

### Nouvel Onglet "Quality Issues"

**Emplacement**: `frontend/app/chat/components/QualityIssuesTab.tsx`

**Fonctionnalités:**
- ✅ Tableau paginé des Q&A problématiques
- ✅ Filtres par catégorie, score, statut révision
- ✅ Détails complets (question, réponse, problèmes, recommandation)
- ✅ Actions: Marquer comme revu / Faux positif
- ✅ Statistiques globales (graphiques)

**Colonnes du tableau:**
1. User
2. Question (tronquée, cliquer pour détails)
3. Score
4. Catégorie
5. Date
6. Statut (Revu / Non revu)
7. Actions

---

## 📝 Notes Importantes

1. **Sécurité**: Tous les endpoints nécessitent des droits admin
2. **Coûts**: Surveiller l'utilisation OpenAI via le dashboard
3. **Performance**: L'analyse batch est asynchrone
4. **Faux positifs**: Prévoir un workflow de révision manuelle
5. **Privacy**: Les Q&A sont stockées pour analyse, respecter RGPD

---

## 🐛 Troubleshooting

### Erreur: "OPENAI_API_KEY not set"
```bash
export OPENAI_API_KEY=sk-...
```

### Analyse trop lente
- Réduire le `limit` du batch
- Utiliser l'analyse temps réel seulement pour cas suspects

### Trop de faux positifs
- Ajuster `QUALITY_THRESHOLD` dans `qa_quality_analyzer.py`
- Affiner le prompt d'analyse
- Marquer les faux positifs pour améliorer le système

---

## 📚 Ressources

- **OpenAI Pricing**: https://openai.com/pricing
- **GPT-3.5-turbo Docs**: https://platform.openai.com/docs/models/gpt-3-5-turbo
- **FastAPI Docs**: https://fastapi.tiangolo.com/
- **PostgreSQL JSONB**: https://www.postgresql.org/docs/current/datatype-json.html

---

**Version**: 1.0.0
**Date**: 2025-10-11
**Auteur**: Claude Code + Intelia Team
