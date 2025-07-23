# RAG Index Directory

Structure créée automatiquement le 2025-06-30 15:52:58

## Répertoires:
- `index/` - Index FAISS pour les embeddings
- `documents/` - Documents source pour l'analyse experte  
- `embeddings/` - Cache des embeddings vectoriels
- `cache/` - Cache des requêtes fréquentes

## Fichiers de configuration:
- `config.ini` - Configuration RAG
- `README.md` - Cette documentation

## Variables d'environnement:
- RAG_INDEX_PATH="C:\broiler_agent\rag_index"
- RAG_MODE="local"

## Mode de fonctionnement:
- Si l'index n'est pas trouvé → Mode fallback activé
- Mode fallback → Utilise le système de traduction pour les réponses
- Aucune erreur bloquante → L'application fonctionne toujours

## Pour activer le RAG complet:
1. Placer les documents experts dans `documents/`
2. Construire l'index avec le script de construction
3. L'application détectera automatiquement l'index
