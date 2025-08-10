# rag/build_rag.py
import os
from pathlib import Path
from typing import List
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from rag.parser_router import route_and_parse

BASE_DIR = Path(__file__).resolve().parent.parent
DOCS_DIR = BASE_DIR / "documents"
INDEX_DIR = BASE_DIR / "public"

EMBED_MODEL = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"

def build_index_for_species(species: str, files: List[str]):
    print(f"🔹 Building index for {species} with {len(files)} files")
    embeddings = HuggingFaceEmbeddings(model_name=EMBED_MODEL)
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    all_docs = []

    for f in files:
        for chunk in route_and_parse(f):
            splits = text_splitter.split_text(chunk["text"])
            for s in splits:
                meta = chunk["metadata"]
                all_docs.append({"page_content": s, "metadata": meta})

    if not all_docs:
        print(f"⚠️ No documents found for {species}")
        return

    faiss_index = FAISS.from_documents(all_docs, embeddings)
    species_dir = INDEX_DIR / species
    species_dir.mkdir(parents=True, exist_ok=True)
    faiss_index.save_local(str(species_dir))
    print(f"✅ Index saved for {species} → {species_dir}")

def build_all():
    files_by_species = {"global": [], "broiler": [], "layer": []}

    for root, _, files in os.walk(DOCS_DIR):
        for f in files:
            fp = os.path.join(root, f)
            low = fp.lower()
            if "broiler" in low or "ross" in low or "cobb" in low:
                files_by_species["broiler"].append(fp)
            elif "layer" in low or "lohmann" in low or "hy-line" in low:
                files_by_species["layer"].append(fp)
            else:
                files_by_species["global"].append(fp)

    for sp, files in files_by_species.items():
        build_index_for_species(sp, files)

if __name__ == "__main__":
    build_all()
