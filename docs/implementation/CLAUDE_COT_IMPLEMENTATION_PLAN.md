# Plan d'implémentation: Claude Extended Thinking avec CoT

## 📊 Analyse du système actuel

### Structure du répertoire `llm/`

Le système actuel contient **265 fichiers Python** organisés en modules spécialisés:

```
llm/
├── generation/          # Génération de réponses (CIBLE PRINCIPALE)
├── config/              # Prompts et configuration
├── core/                # RAG engine
├── retrieval/           # Recherche de documents
├── api/                 # Endpoints FastAPI
├── cache/               # Système de cache
├── security/            # Guardrails
└── monitoring/          # Métriques
```

---

## 🎯 Fichiers à modifier (3 fichiers critiques)

### 1. **`llm/generation/generators.py`** (1,306 lignes) - PRIORITÉ 1

**Rôle actuel:**
- Classe principale `EnhancedResponseGenerator`
- Gère la génération avec GPT-4o et modèles O1
- Supporte déjà CoT pour O1 (ligne 567-594)
- CoT pour autres modèles a été **supprimé** (ligne 208-223)

**Modifications requises:**

#### A. Ajouter support Claude Extended Thinking (ligne 567-594)

**Actuellement:**
```python
# Line 567-594
is_o1_model = self.cot_model.startswith("o1-")
if is_o1_model:
    # Special handling for O1: no system msg, no temp, no max_tokens
    messages = [{"role": "user", "content": enhanced_prompt}]
    response = client.chat.completions.create(
        model=self.cot_model,
        messages=messages
    )
else:
    # Standard models (GPT-4o)
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": enhanced_prompt}
    ]
    response = client.chat.completions.create(
        model=self.cot_model,
        messages=messages,
        temperature=0.1,
        max_tokens=4096
    )
```

**Ajouter:**
```python
# Line 567-594 (MODIFIED)
is_o1_model = self.cot_model.startswith("o1-")
is_claude_extended = self.cot_model.startswith("claude-3.") or self.cot_model.startswith("claude-4.")

if is_o1_model:
    # O1 models: native reasoning, no system msg
    messages = [{"role": "user", "content": enhanced_prompt}]
    response = client.chat.completions.create(
        model=self.cot_model,
        messages=messages
    )

elif is_claude_extended:
    # Claude Extended Thinking: NOUVEAU CODE
    import anthropic

    anthropic_client = anthropic.Anthropic(
        api_key=os.getenv("ANTHROPIC_API_KEY")
    )

    # Budget de thinking selon complexité
    thinking_budget = self._calculate_thinking_budget(rag_result, query_intent)

    response = anthropic_client.messages.create(
        model=self.cot_model,
        max_tokens=16000,
        thinking={
            "type": "enabled",
            "budget_tokens": thinking_budget
        },
        messages=[{
            "role": "user",
            "content": f"""{system_prompt}

{enhanced_prompt}"""
        }]
    )

    # Extraire thinking et response
    thinking_content = None
    text_content = None

    for block in response.content:
        if block.type == "thinking":
            thinking_content = block.thinking
        elif block.type == "text":
            text_content = block.text

    # Envelopper dans format compatible OpenAI
    class ClaudeResponse:
        def __init__(self, thinking, text, usage):
            self.choices = [type('obj', (object,), {
                'message': type('obj', (object,), {
                    'content': text
                })()
            })()]
            self.usage = type('obj', (object,), {
                'prompt_tokens': usage.input_tokens,
                'completion_tokens': usage.output_tokens,
                'total_tokens': usage.input_tokens + usage.output_tokens
            })()
            self.thinking = thinking  # NOUVEAU: stocker le CoT

    response = ClaudeResponse(thinking_content, text_content, response.usage)

else:
    # Standard models (GPT-4o)
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": enhanced_prompt}
    ]
    response = client.chat.completions.create(
        model=self.cot_model,
        messages=messages,
        temperature=0.1,
        max_tokens=4096
    )
```

#### B. Ajouter méthode calcul budget thinking (NOUVEAU)

```python
# Ajouter après ligne 700
def _calculate_thinking_budget(
    self,
    rag_result: Optional[RAGResult],
    query_intent: Optional[Dict[str, Any]]
) -> int:
    """
    Calcule le budget de thinking tokens selon la complexité de la requête

    Returns:
        int: Budget entre 2000-16000 tokens
    """
    base_budget = 4000  # Budget de base

    # Facteurs augmentant la complexité
    complexity_factors = []

    # 1. Source des données (RAG = plus complexe)
    if rag_result:
        source = rag_result.get("source", RAGSource.UNKNOWN)
        if source == RAGSource.WEAVIATE:
            complexity_factors.append(2000)  # RAG documents
        elif source == RAGSource.POSTGRESQL:
            complexity_factors.append(1000)  # Données structurées

    # 2. Nombre de documents
    if rag_result and rag_result.get("documents"):
        doc_count = len(rag_result["documents"])
        if doc_count > 5:
            complexity_factors.append(2000)  # Beaucoup de contexte
        elif doc_count > 2:
            complexity_factors.append(1000)

    # 3. Type de requête (intent)
    if query_intent:
        intent_type = query_intent.get("intent_type", "")
        if intent_type in ["comparative", "temporal", "multi_step"]:
            complexity_factors.append(3000)  # Requêtes complexes
        elif intent_type in ["calculation", "analysis"]:
            complexity_factors.append(2000)

    # 4. Longueur du contexte
    if rag_result:
        context_length = len(str(rag_result.get("documents", "")))
        if context_length > 5000:
            complexity_factors.append(2000)  # Beaucoup de contexte

    # Calculer budget final
    total_budget = base_budget + sum(complexity_factors)

    # Limiter entre 2000 et 16000
    return min(max(total_budget, 2000), 16000)
```

#### C. Modifier retour de `generate_response()` pour inclure CoT (ligne 479-631)

**Actuellement (ligne 625-631):**
```python
return {
    "answer": final_answer,
    "source": source_label,
    "context_summary": context_summary,
    "documents": rag_result.documents if rag_result else [],
    "metrics": metrics,
    "cache_hit": cache_hit,
}
```

**Modifier en:**
```python
# Line 625-631 (MODIFIED)
result = {
    "answer": final_answer,
    "source": source_label,
    "context_summary": context_summary,
    "documents": rag_result.documents if rag_result else [],
    "metrics": metrics,
    "cache_hit": cache_hit,
}

# NOUVEAU: Ajouter thinking si disponible
if hasattr(response, 'thinking') and response.thinking:
    result["cot_thinking"] = response.thinking
    result["cot_model"] = self.cot_model
    logger.info(f"✅ CoT thinking included ({len(response.thinking)} chars)")

return result
```

#### D. Configuration modèle (ligne 70)

**Actuellement:**
```python
self.cot_model = os.getenv("COT_MODEL", "gpt-4o")
```

**Modifier en:**
```python
self.cot_model = os.getenv("COT_MODEL", "claude-3-7-sonnet-20250219")
# Options supportées:
# - gpt-4o, gpt-4o-2024-08-06 (OpenAI standard)
# - o1-preview, o1-mini (OpenAI reasoning)
# - claude-3-7-sonnet-20250219 (Claude Extended Thinking)
# - claude-sonnet-4-5-20250929 (Claude 4.5 Extended Thinking)
```

---

### 2. **`llm/generation/llm_router.py`** (150 lignes) - PRIORITÉ 2

**Rôle actuel:**
- Route les requêtes vers le meilleur LLM (DeepSeek/Claude/GPT-4o)
- Basé sur la complexité et la source de données

**Modifications requises:**

#### A. Ajouter option Extended Thinking (ligne 26-28)

**Actuellement:**
```python
class LLMProvider(str, Enum):
    GPT4O = "gpt4o"
    CLAUDE = "claude"
    DEEPSEEK = "deepseek"
```

**Ajouter:**
```python
class LLMProvider(str, Enum):
    GPT4O = "gpt4o"
    CLAUDE = "claude"
    CLAUDE_EXTENDED = "claude-extended"  # NOUVEAU
    DEEPSEEK = "deepseek"
    O1 = "o1"  # NOUVEAU
```

#### B. Modifier règles de routing (ligne 101-150)

**Ajouter règle pour Extended Thinking:**

```python
def route_query(
    self,
    query: str,
    rag_result: Optional[RAGResult],
    query_intent: Optional[Dict[str, Any]]
) -> LLMProvider:
    """Route query to optimal LLM"""

    # PostgreSQL direct hit → DeepSeek (simple)
    if rag_result and rag_result.source == RAGSource.POSTGRESQL:
        if rag_result.documents and rag_result.documents[0].score > 0.9:
            return LLMProvider.DEEPSEEK

    # NOUVEAU: Requêtes complexes → Claude Extended Thinking
    if query_intent and query_intent.get("intent_type") in [
        "comparative", "temporal", "multi_step", "synthesis"
    ]:
        return LLMProvider.CLAUDE_EXTENDED

    # NOUVEAU: RAG multi-documents → Claude Extended Thinking
    if rag_result and rag_result.source == RAGSource.WEAVIATE:
        if rag_result.documents and len(rag_result.documents) >= 3:
            return LLMProvider.CLAUDE_EXTENDED

    # Weaviate RAG → Claude standard
    if rag_result and rag_result.source == RAGSource.WEAVIATE:
        return LLMProvider.CLAUDE

    # Default → GPT-4o
    return LLMProvider.GPT4O
```

#### C. Mapping modèle → nom (ligne 40-50)

**Ajouter:**
```python
PROVIDER_TO_MODEL = {
    LLMProvider.GPT4O: "gpt-4o",
    LLMProvider.CLAUDE: "claude-3-5-sonnet-20241022",
    LLMProvider.CLAUDE_EXTENDED: "claude-3-7-sonnet-20250219",  # NOUVEAU
    LLMProvider.DEEPSEEK: "deepseek-chat",
    LLMProvider.O1: "o1-mini",  # NOUVEAU
}
```

---

### 3. **`llm/config/system_prompts.py`** (100 lignes) - PRIORITÉ 3

**Rôle actuel:**
- Charge `system_prompts.json`
- Gère prompts hiérarchiques (PostgreSQL/Weaviate/General)

**Modifications requises:**

#### A. Ajouter prompts spécifiques Extended Thinking

**Fichier: `llm/config/system_prompts.json`**

**Ajouter section:**
```json
{
  "base_prompts": { ... },
  "specialized_prompts": { ... },
  "hierarchical_rag": { ... },

  "extended_thinking": {
    "general": {
      "en": "You are an expert poultry farming advisor with deep reasoning capabilities. When analyzing this question:\n\n1. Break down the question into components\n2. Consider multiple perspectives and approaches\n3. Evaluate evidence from provided context\n4. Reason through implications and trade-offs\n5. Synthesize a comprehensive answer\n\nUse your extended thinking to provide thorough, well-reasoned responses.",

      "fr": "Vous êtes un conseiller expert en aviculture avec des capacités de raisonnement avancées. Pour analyser cette question:\n\n1. Décomposez la question en composantes\n2. Considérez plusieurs perspectives et approches\n3. Évaluez les preuves du contexte fourni\n4. Raisonnez sur les implications et compromis\n5. Synthétisez une réponse complète\n\nUtilisez votre réflexion approfondie pour fournir des réponses complètes et bien raisonnées."
    },

    "comparative": {
      "en": "You are comparing multiple options or approaches. In your extended thinking:\n\n1. Identify key comparison criteria\n2. Analyze strengths and weaknesses of each option\n3. Consider context-specific factors\n4. Evaluate trade-offs systematically\n5. Provide evidence-based recommendations",

      "fr": "Vous comparez plusieurs options ou approches. Dans votre réflexion:\n\n1. Identifiez les critères de comparaison clés\n2. Analysez les forces et faiblesses de chaque option\n3. Considérez les facteurs contextuels\n4. Évaluez les compromis systématiquement\n5. Fournissez des recommandations basées sur les preuves"
    },

    "synthesis": {
      "en": "You are synthesizing information from multiple sources. In your extended thinking:\n\n1. Identify key themes and patterns\n2. Resolve conflicting information\n3. Build coherent understanding\n4. Connect insights across sources\n5. Create comprehensive synthesis",

      "fr": "Vous synthétisez des informations de plusieurs sources. Dans votre réflexion:\n\n1. Identifiez les thèmes et motifs clés\n2. Résolvez les informations contradictoires\n3. Construisez une compréhension cohérente\n4. Reliez les insights entre les sources\n5. Créez une synthèse complète"
    }
  }
}
```

#### B. Modifier `system_prompts.py` pour charger Extended Thinking

**Ajouter méthode:**
```python
def get_extended_thinking_prompt(
    self,
    query_type: str = "general",
    language: str = "en"
) -> str:
    """
    Get Extended Thinking specific prompt

    Args:
        query_type: "general", "comparative", "synthesis", etc.
        language: Language code

    Returns:
        Extended Thinking system prompt
    """
    try:
        prompts = self.prompts.get("extended_thinking", {})
        type_prompts = prompts.get(query_type, prompts.get("general", {}))
        return type_prompts.get(language, type_prompts.get("en", ""))
    except Exception as e:
        logger.warning(f"Failed to load Extended Thinking prompt: {e}")
        return ""
```

---

## 📦 Fichiers supplémentaires (modifications mineures)

### 4. **`llm/requirements.txt`** - Vérifier version Anthropic

**Actuellement:**
```
anthropic>=0.40.0
```

**Vérifier que Extended Thinking est supporté:**
```
anthropic>=0.40.0  # Supporte Extended Thinking (ok)
```

Si version trop ancienne, mettre à jour:
```
anthropic>=0.48.0  # Version avec Extended Thinking stable
```

---

### 5. **`llm/generation/llm_ensemble.py`** - Ajouter Claude Extended dans ensemble

**Ligne 45-60 (AJOUTER option):**

```python
def generate_with_ensemble(
    self,
    query: str,
    context: str,
    mode: str = "BEST_OF_N"  # BEST_OF_N, FUSION, VOTING
) -> Dict[str, Any]:
    """Generate responses from multiple LLMs in parallel"""

    # MODIFIER: Ajouter Claude Extended Thinking
    llm_configs = [
        {"provider": "claude-extended", "model": "claude-3-7-sonnet-20250219"},
        {"provider": "gpt4", "model": "gpt-4o"},
        {"provider": "deepseek", "model": "deepseek-chat"},
    ]

    # ... reste du code ...
```

---

## 🗄️ Base de données: Nouvelle colonne pour CoT

### Migration SQL

**Fichier: `backend/sql/migrations/30_add_cot_thinking.sql`**

```sql
-- Add Chain of Thought (CoT) columns to messages table
ALTER TABLE messages
ADD COLUMN IF NOT EXISTS cot_thinking TEXT,
ADD COLUMN IF NOT EXISTS cot_model VARCHAR(100),
ADD COLUMN IF NOT EXISTS cot_tokens INTEGER;

-- Add index for querying CoT messages
CREATE INDEX IF NOT EXISTS idx_messages_cot_model
ON messages(cot_model) WHERE cot_model IS NOT NULL;

-- Comment
COMMENT ON COLUMN messages.cot_thinking IS 'Chain of Thought reasoning from Claude Extended Thinking';
COMMENT ON COLUMN messages.cot_model IS 'Model used for CoT generation (e.g., claude-3-7-sonnet)';
COMMENT ON COLUMN messages.cot_tokens IS 'Number of thinking tokens used';
```

### Modifier backend pour sauvegarder CoT

**Fichier: `backend/app/api/v1/chat.py`** (approximativement ligne 400-500)

**Ajouter lors de la sauvegarde du message:**

```python
# Sauvegarder message assistant
assistant_message = {
    "conversation_id": conversation_id,
    "role": "assistant",
    "content": answer,
    "metadata": {
        "source": result.get("source"),
        "context_summary": result.get("context_summary"),
        # NOUVEAU: Ajouter CoT
        "cot_thinking": result.get("cot_thinking"),
        "cot_model": result.get("cot_model"),
    }
}

# Si CoT disponible, sauvegarder dans colonne dédiée
if result.get("cot_thinking"):
    # Calculer tokens (approximatif: 1 token ≈ 4 chars)
    cot_tokens = len(result["cot_thinking"]) // 4

    # SQL avec colonnes CoT
    cursor.execute("""
        INSERT INTO messages (
            conversation_id, role, content, metadata,
            cot_thinking, cot_model, cot_tokens
        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (
        conversation_id,
        "assistant",
        answer,
        json.dumps(assistant_message["metadata"]),
        result["cot_thinking"],
        result["cot_model"],
        cot_tokens
    ))
```

---

## 🎨 Frontend: Afficher le CoT

### Modifier composant Message

**Fichier: `frontend/app/chat/components/MessageBubble.tsx`** (ou similaire)

**Ajouter section CoT:**

```tsx
interface Message {
  role: "user" | "assistant";
  content: string;
  metadata?: {
    source?: string;
    cot_thinking?: string;
    cot_model?: string;
  };
}

export function MessageBubble({ message }: { message: Message }) {
  const [showCoT, setShowCoT] = useState(false);
  const hasCot = message.metadata?.cot_thinking;

  return (
    <div className="message-bubble">
      {/* Message content */}
      <div className="message-content">
        {message.content}
      </div>

      {/* CoT section (si disponible) */}
      {hasCot && (
        <div className="mt-3 border-t border-gray-200 pt-3">
          <button
            onClick={() => setShowCoT(!showCoT)}
            className="flex items-center gap-2 text-sm text-gray-600 hover:text-gray-800"
          >
            <Brain className="w-4 h-4" />
            {showCoT ? "Masquer" : "Voir"} le raisonnement
            {message.metadata.cot_model && (
              <span className="text-xs text-gray-400">
                ({message.metadata.cot_model})
              </span>
            )}
          </button>

          {showCoT && (
            <div className="mt-2 p-3 bg-blue-50 rounded-lg">
              <div className="text-xs font-semibold text-blue-700 mb-2">
                🧠 Chain of Thought (Réflexion du modèle)
              </div>
              <pre className="text-xs text-gray-700 whitespace-pre-wrap font-mono">
                {message.metadata.cot_thinking}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
```

---

## ⚙️ Variables d'environnement

### Backend `.env`

**Ajouter:**
```bash
# Claude Extended Thinking
ANTHROPIC_API_KEY=sk-ant-...
COT_MODEL=claude-3-7-sonnet-20250219
ENABLE_EXTENDED_THINKING=true

# Thinking budget (optionnel, défaut selon complexité)
DEFAULT_THINKING_BUDGET=8000
MAX_THINKING_BUDGET=16000
MIN_THINKING_BUDGET=2000

# Router
ENABLE_LLM_ROUTING=true
DEFAULT_LLM_PROVIDER=claude-extended
```

---

## 📊 Résumé des modifications

| Fichier | Lignes modifiées | Type de modification | Complexité |
|---------|------------------|----------------------|------------|
| `generators.py` | 567-594, 70, 625-631, +100 (nouvelle méthode) | Logique génération | ⭐⭐⭐ Élevée |
| `llm_router.py` | 26-28, 40-50, 101-150 | Routing | ⭐⭐ Moyenne |
| `system_prompts.py` | +30 lignes | Configuration prompts | ⭐ Faible |
| `system_prompts.json` | +60 lignes JSON | Prompts Extended Thinking | ⭐ Faible |
| `requirements.txt` | 1 ligne | Version Anthropic | ⭐ Faible |
| `llm_ensemble.py` | 45-60 | Ajout option ensemble | ⭐⭐ Moyenne |
| `30_add_cot_thinking.sql` | Nouveau fichier | Migration DB | ⭐ Faible |
| `chat.py` (backend) | +20 lignes | Sauvegarde CoT | ⭐⭐ Moyenne |
| `MessageBubble.tsx` | +40 lignes | UI affichage CoT | ⭐⭐ Moyenne |

**Total estimé: ~300 lignes de code ajoutées/modifiées**

---

## 🚀 Ordre d'implémentation recommandé

### Phase 1: Core (Backend)
1. ✅ Ajouter migration SQL `30_add_cot_thinking.sql`
2. ✅ Modifier `generators.py` (Extended Thinking support)
3. ✅ Ajouter méthode `_calculate_thinking_budget()`
4. ✅ Modifier retour `generate_response()` pour inclure CoT
5. ✅ Tester génération avec Claude Extended Thinking

### Phase 2: Routing & Configuration
6. ✅ Modifier `llm_router.py` (nouvelle option CLAUDE_EXTENDED)
7. ✅ Ajouter prompts dans `system_prompts.json`
8. ✅ Modifier `system_prompts.py` (méthode `get_extended_thinking_prompt()`)
9. ✅ Configurer variables d'environnement

### Phase 3: Sauvegarde & UI
10. ✅ Modifier `chat.py` backend pour sauvegarder CoT
11. ✅ Créer composant frontend pour afficher CoT
12. ✅ Tester end-to-end

### Phase 4: Optimisations (optionnel)
13. ⚠️ Ajouter Claude Extended dans `llm_ensemble.py`
14. ⚠️ Ajouter métriques CoT (tokens, latence)
15. ⚠️ Optimiser calcul budget thinking

---

## 🧪 Tests recommandés

### Test 1: Génération simple
```python
from llm.generation.generators import EnhancedResponseGenerator

generator = EnhancedResponseGenerator()
result = generator.generate_response(
    query="Comment améliorer la production d'œufs?",
    rag_result=None,
    language="fr"
)

print("Answer:", result["answer"])
print("CoT:", result.get("cot_thinking", "N/A"))
```

### Test 2: Génération avec RAG complexe
```python
# Avec plusieurs documents Weaviate
result = generator.generate_response(
    query="Comparez les systèmes d'alimentation pour pondeuses",
    rag_result=rag_result_with_5_docs,
    language="fr"
)

# Devrait utiliser budget thinking élevé (>8000 tokens)
```

### Test 3: Routing
```python
from llm.generation.llm_router import LLMRouter

router = LLMRouter()
provider = router.route_query(
    query="Analyse comparative de 3 races de poules",
    rag_result=complex_rag_result,
    query_intent={"intent_type": "comparative"}
)

assert provider == LLMProvider.CLAUDE_EXTENDED
```

---

## 💰 Estimation des coûts

### Claude 3.7 Sonnet Extended Thinking
- **Input**: $3 / 1M tokens
- **Output**: $15 / 1M tokens
- **Thinking tokens**: Comptés comme output (4x plus cher que input)

### Exemple de coût par requête
```
Input: 1000 tokens (prompt + context)     = $0.003
Thinking: 8000 tokens (CoT reasoning)     = $0.120
Output: 500 tokens (réponse finale)       = $0.0075
----------------------------------------------------
Total par requête: ~$0.13
```

**Comparaison:**
- GPT-4o: $0.02 par requête (sans CoT)
- O1-mini: $0.05 par requête (CoT caché)
- Claude Extended: $0.13 par requête (CoT visible)

**Recommandation:** Utiliser Extended Thinking pour **requêtes complexes uniquement** (via router intelligent).

---

## ✅ Checklist de déploiement

- [ ] Migration SQL exécutée
- [ ] Variables d'environnement configurées
- [ ] Tests unitaires passent
- [ ] Tests d'intégration passent
- [ ] Métriques Anthropic activées
- [ ] Monitoring des coûts configuré
- [ ] Documentation utilisateur mise à jour
- [ ] Backend redémarré en production
- [ ] Frontend déployé
- [ ] Tests end-to-end en production

---

**Dernière mise à jour:** 2025-10-22
**Auteur:** Claude Code
**Statut:** 📋 Plan prêt pour implémentation
