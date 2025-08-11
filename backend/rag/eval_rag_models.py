# -*- coding: utf-8 -*-
"""
A/B test d'embeddings pour RAG

But:
- Comparer plusieurs sentence-transformers (ou APIs compatibles) sur votre corpus existant
- Mesures: Recall@k, MRR@k, latences (embed corpus, embed requêtes), taille mémoire
- Input corpus: le fichier pickle `rag_index/<species>/index.pkl` (items[{text, metadata}])
- Qrels: CSV avec colonnes: query, positive_file (optionnel), positive_text (optionnel)
    * positive_file: chemin (ou sous-chaîne du chemin) attendu dans metadata.source_file / source
    * positive_text: sous-chaîne de texte attendue dans au moins un chunk pertinent

Exemples d'usage (PowerShell):

python .\eval_rag_models.py ^
  --corpus "C:\\intelia_gpt\\intelia-expert\\backend\\rag_index\\broiler\\index.pkl" ^
  --models "sentence-transformers/all-MiniLM-L6-v2,BAAI/bge-large-en-v1.5,BAAI/bge-m3" ^
  --qrels .\qa\eval_broiler.csv ^
  --k 5 --normalize --batch-size 128

(Optionnel) avec reranker cross-encoder pour reranker les Top-50:

python .\eval_rag_models.py ^
  --corpus "...index.pkl" ^
  --models "BAAI/bge-large-en-v1.5,Alibaba-NLP/gte-large-en-v1.5" ^
  --qrels .\qa\eval_broiler.csv ^
  --k 5 --reranker "BAAI/bge-reranker-large" --rerank-topn 50

Sorties:
- Tableau récapitulatif par modèle
- Fichier CSV détaillé dans .\qa\eval_results_<timestamp>.csv

Notes:
- On utilise la normalisation L2 + produit scalaire (cosine) si --normalize
- Pas besoin de FAISS pour l'évaluation; tout se fait en numpy.
"""

from __future__ import annotations
import argparse, csv, os, sys, time, pickle, math, json
from pathlib import Path
from typing import List, Dict, Any, Tuple
import numpy as np

try:
    from sentence_transformers import SentenceTransformer, CrossEncoder
except Exception as e:
    print("❌ sentence-transformers manquant: pip install sentence-transformers", flush=True)
    raise

# --------------------------- Utils ------------------------------------- #

def log(msg: str):
    print(msg, flush=True)

def load_corpus(pkl_path: str) -> Tuple[List[str], List[Dict[str, Any]]]:
    with open(pkl_path, 'rb') as f:
        items = pickle.load(f)
    texts = []
    norm_keys = ("source_file", "source", "file", "path")
    # nettoyage minimal
    for it in items:
        txt = it.get("text", "") if isinstance(it, dict) else getattr(it, "text", "")
        meta = it.get("metadata", {}) if isinstance(it, dict) else getattr(it, "metadata", {}) or {}
        if not isinstance(meta, dict):
            meta = {}
        # harmoniser une clé de chemin si possible
        src = None
        for k in norm_keys:
            if k in meta and meta[k]:
                src = meta[k]
                break
        if src is None:
            # parfois dans nested
            for k in meta.keys():
                if isinstance(meta.get(k), str) and ("\\" in meta[k] or "/" in meta[k]):
                    src = meta[k]; break
        meta.setdefault("source_file", src or "")
        texts.append(str(txt))
        it["metadata"] = meta
    return texts, items

def read_qrels(csv_path: str) -> List[Dict[str, str]]:
    rows = []
    with open(csv_path, newline='', encoding='utf-8') as f:
        r = csv.DictReader(f)
        for row in r:
            if not row.get('query'): continue
            rows.append({
                'query': row['query'].strip(),
                'positive_file': (row.get('positive_file') or '').strip(),
                'positive_text': (row.get('positive_text') or '').strip(),
            })
    return rows

# matching flexible sur file path

def path_match(meta: Dict[str, Any], needle: str) -> bool:
    if not needle: return False
    cand = (meta.get('source_file') or meta.get('source') or '')
    if not cand: return False
    # match insensible à la casse et aux séparateurs
    n = os.path.normcase(needle)
    c = os.path.normcase(cand)
    return n in c

# matching sur sous-chaîne de texte

def text_match(text: str, needle: str) -> bool:
    if not needle: return False
    return needle.lower() in (text or '').lower()

# métriques

def recall_at_k(ranks: List[int], k: int) -> float:
    hits = sum(1 for r in ranks if (r is not None and r <= k))
    return hits / max(len(ranks), 1)

def mrr_at_k(ranks: List[int], k: int) -> float:
    acc = 0.0
    for r in ranks:
        if r is not None and r <= k:
            acc += 1.0 / r
    return acc / max(len(ranks), 1)

# --------------------------- Core eval --------------------------------- #

def embed_texts(model_name: str, texts: List[str], batch_size: int, normalize: bool) -> Tuple[np.ndarray, float]:
    t0 = time.time()
    model = SentenceTransformer(model_name, device='cpu')
    embs = model.encode(texts, batch_size=batch_size, show_progress_bar=True,
                        convert_to_numpy=True, normalize_embeddings=normalize)
    dt = time.time() - t0
    return embs.astype('float32', copy=False), dt


def eval_model(model_name: str, corpus_texts: List[str], items: List[Dict[str, Any]],
               qrels: List[Dict[str, str]], k: int, batch_size: int,
               normalize: bool, reranker_name: str | None, rerank_topn: int) -> Dict[str, Any]:
    # 1) embeddings corpus
    corpus_embs, dt_corpus = embed_texts(model_name, corpus_texts, batch_size, normalize)

    # 2) embeddings requêtes
    queries = [row['query'] for row in qrels]
    q_embs, dt_queries = embed_texts(model_name, queries, max(8, batch_size//2), normalize)

    # 3) recherche brute (produit scalaire si normalisé → cosine)
    # scores = Q x D^T
    scores = np.matmul(q_embs.astype('float32'), corpus_embs.T)

    # 4) topK init
    topn = max(k, rerank_topn)
    idx_top = np.argpartition(-scores, kth=min(topn-1, scores.shape[1]-1), axis=1)[:, :topn]

    # tri local pour chaque requête
    sorted_idx = np.take_along_axis(idx_top, np.argsort(-np.take_along_axis(scores, idx_top, axis=1), axis=1), axis=1)

    # 5) reranking optionnel (cross-encoder)
    if reranker_name:
        log(f"   · Reranking top-{rerank_topn} avec {reranker_name}")
        ce = CrossEncoder(reranker_name, max_length=512, device='cpu')
        reranked = []
        for qi, row in enumerate(qrels):
            cand_ids = sorted_idx[qi, :rerank_topn].tolist()
            pairs = [(row['query'], corpus_texts[j]) for j in cand_ids]
            ce_scores = ce.predict(pairs)
            order = np.argsort(-np.array(ce_scores))
            reranked.append([cand_ids[o] for o in order])
        sorted_idx = np.array(reranked, dtype=object)

    # 6) évalue ranks
    ranks: List[int | None] = []
    details = []
    for qi, row in enumerate(qrels):
        pos_file = row.get('positive_file', '')
        pos_text = row.get('positive_text', '')
        found_rank = None
        for rank, cid in enumerate(sorted_idx[qi][:k], start=1):
            it = items[int(cid)]
            if pos_file and path_match(it.get('metadata', {}), pos_file):
                found_rank = rank; break
            if pos_text and text_match(it.get('text', ''), pos_text):
                found_rank = rank; break
        ranks.append(found_rank)
        details.append({
            'query': row['query'],
            'hit_rank': found_rank if found_rank is not None else 0,
            'top_hit_file': items[int(sorted_idx[qi][0])]['metadata'].get('source_file', ''),
        })

    R = recall_at_k(ranks, k)
    M = mrr_at_k(ranks, k)

    return {
        'model': model_name,
        'k': k,
        'recall@k': R,
        'mrr@k': M,
        'embed_time_corpus_s': round(dt_corpus, 2),
        'embed_time_queries_s': round(dt_queries, 2),
        'num_chunks': len(corpus_texts),
        'num_queries': len(qrels),
        'normalize': normalize,
        'details': details,
    }

# --------------------------- CLI --------------------------------------- #

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--corpus', required=True, help='Chemin vers rag_index/<species>/index.pkl')
    ap.add_argument('--qrels', required=True, help='CSV avec colonnes: query,positive_file,positive_text')
    ap.add_argument('--models', required=True, help='Liste de modèles séparés par des virgules')
    ap.add_argument('--k', type=int, default=5)
    ap.add_argument('--batch-size', type=int, default=64)
    ap.add_argument('--normalize', action='store_true')
    ap.add_argument('--reranker', default=None)
    ap.add_argument('--rerank-topn', type=int, default=50)
    ap.add_argument('--out', default='qa')
    args = ap.parse_args()

    corpus_path = Path(args.corpus)
    qrels_path = Path(args.qrels)
    out_dir = Path(args.out); out_dir.mkdir(parents=True, exist_ok=True)

    if not corpus_path.exists():
        log(f"❌ Corpus non trouvé: {corpus_path}"); sys.exit(2)
    if not qrels_path.exists():
        log(f"❌ Qrels non trouvé: {qrels_path}"); sys.exit(2)

    log(f"📦 Chargement corpus: {corpus_path}")
    texts, items = load_corpus(str(corpus_path))
    log(f"   • chunks: {len(texts)}")

    log(f"📝 Chargement qrels: {qrels_path}")
    qrels = read_qrels(str(qrels_path))
    log(f"   • queries: {len(qrels)}")

    models = [m.strip() for m in args.models.split(',') if m.strip()]
    results = []

    for m in models:
        log(f"\n🔬 Test modèle: {m}")
        res = eval_model(m, texts, items, qrels, args.k, args.batch_size, args.normalize, args.reranker, args.rerank_topn)
        results.append(res)
        log(json.dumps({k: v for k, v in res.items() if k != 'details'}, ensure_ascii=False, indent=2))

    # export CSV résultats détaillés
    ts = time.strftime('%Y%m%d_%H%M%S')
    out_csv = out_dir / f"eval_results_{ts}.csv"
    with open(out_csv, 'w', newline='', encoding='utf-8') as f:
        cols = ['model','query','hit_rank','top_hit_file']
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for res in results:
            for d in res['details']:
                w.writerow({'model': res['model'], **d})
    log(f"\n✅ Écrit: {out_csv}")

    # tableau récapitulatif
    print("\n=== Résumé ===")
    header = ["model","recall@k","mrr@k","num_queries","num_chunks","embed_time_corpus_s","embed_time_queries_s"]
    print("\t".join(header))
    for r in results:
        print("\t".join([
            r['model'], f"{r['recall@k']:.3f}", f"{r['mrr@k']:.3f}",
            str(r['num_queries']), str(r['num_chunks']),
            str(r['embed_time_corpus_s']), str(r['embed_time_queries_s'])
        ]))

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("Interrompu.")
