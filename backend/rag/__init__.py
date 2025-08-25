from pathlib import Path
from typing import Optional

def __init__(
    self,
    index_dir: str | Path,
    method_override: Optional[str] = None,
    model_name: Optional[str] = None,
    enhanced_query_normalization: bool = True,
    debug: bool = True,
    # 👇 Compat rétro : on accepte ces options si l’app les passe (même si on ne les utilise pas)
    cache_embeddings: Optional[bool] = None,
    cache_max_entries: Optional[int] = None,
    max_workers: Optional[int] = None,
    # 👇 Et on accepte silencieusement tout autre kwarg inconnu pour ne pas casser l’appelant
    **_ignored_kwargs,
) -> None:
    """
    FastRAGEmbedder constructor.

    Args:
        index_dir: Répertoire de l’index (FAISS, etc.).
        method_override: Force la méthode d’embedding (si fournie).
        model_name: Nom du modèle d’embedding (si applicable).
        enhanced_query_normalization: Active les normalisations avancées.
        debug: Active le mode verbeux.
        cache_embeddings (compat): Option ignorée (acceptée pour compatibilité).
        cache_max_entries (compat): Option ignorée (acceptée pour compatibilité).
        max_workers (compat): Option ignorée (acceptée pour compatibilité).
        **_ignored_kwargs: Toute autre option inconnue (acceptée/ignorée pour compatibilité).
    """

    # ===== Attributs de base =====
    self.index_dir = Path(index_dir)
    self.method_override = method_override
    self.model_name = model_name
    self.enhanced_query_normalization = bool(enhanced_query_normalization)
    self.debug = bool(debug)

    # ===== Compatibilité ascendante : on accepte/ignore certaines options =====
    # (Permet d’éviter l’erreur: unexpected keyword argument 'cache_embeddings')
    self._cache_embeddings = bool(cache_embeddings) if cache_embeddings is not None else False
    self._cache_max_entries = int(cache_max_entries) if cache_max_entries is not None else 0
    self._max_workers = int(max_workers) if max_workers is not None else 0

    # Logger “best effort” (sans présumer que 'logger' existe déjà dans le module)
    try:
        logger  # type: ignore[name-defined]
    except Exception:
        import logging
        logger = logging.getLogger(__name__)
    if _ignored_kwargs:
        logger.info("ℹ️ FastRAGEmbedder: options ignorées: %s", sorted(_ignored_kwargs.keys()))

    # ===== Initialisation spécifique de ton embedder =====
    # Conserve ici ta logique existante (chargement d’index FAISS, init de clients,
    # vérifications de fichiers, warmup du modèle, etc.). Exemple :
    #
    # self._ensure_index_dir()
    # self._load_or_build_index()
    # self._init_clients()
    # if self.debug:
    #     logger.debug("FastRAGEmbedder initialisé: dir=%s, method=%s, model=%s",
    #                  self.index_dir, self.method_override, self.model_name)
    #
    # (Laisse ce bloc tel qu’il est dans ton code si tu en as déjà un.)
