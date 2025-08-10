# -*- coding: utf-8 -*-
"""
Builds three separate indices: broiler, layer, global.
Scans folders under RAG_INDEX_ROOT and writes meta.json manifests.
Plug this with your actual embedding/index writer.
"""
import os, time, json

INDEX_ROOT = os.environ.get("RAG_INDEX_ROOT", "public")
SPECIES_DIRS = ["broiler","layer","global"]

def _scan_count_docs(path: str):
    cnt = 0
    for root, dirs, files in os.walk(path):
        for f in files:
            if f.lower().endswith((".pdf", ".md", ".txt", ".html")):
                cnt += 1
    return cnt

def main():
    os.makedirs(INDEX_ROOT, exist_ok=True)
    for name in SPECIES_DIRS:
        p = os.path.join(INDEX_ROOT, name)
        os.makedirs(p, exist_ok=True)
        meta = {"index_name": name, "updated_at": int(time.time()), "doc_count": _scan_count_docs(p), "table_chunks_count": None}
        with open(os.path.join(p, "meta.json"), "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
    print("Indexes initialized. Plug embedding/build logic.")

if __name__ == "__main__":
    main()
