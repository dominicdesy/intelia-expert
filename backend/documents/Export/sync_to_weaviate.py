# -*- coding: utf-8 -*-
"""
direct_weaviate_import.py - Import direct vers Weaviate v4 SANS TRONCATURE
Usage: python direct_weaviate_import.py /path/to/documents/
"""

import os
import json
import hashlib
import argparse
import time
import uuid
import traceback
from pathlib import Path
from typing import List, Dict, Set
import weaviate
import weaviate.classes as wvc
from dotenv import load_dotenv

# Charger le fichier .env
print("[DEBUG] Chargement du fichier .env...")
load_dotenv()
print("[DEBUG] Fichier .env chargé")

# Configuration Weaviate Cloud
WEAVIATE_URL = "https://xmlc4jvtu6hfw9zrrmnw.c0.us-east1.gcp.weaviate.cloud"
WEAVIATE_API_KEY = os.getenv("WEAVIATE_API_KEY", "")
print(f"[DEBUG] WEAVIATE_URL: {WEAVIATE_URL}")
print(f"[DEBUG] WEAVIATE_API_KEY présente: {'Oui' if WEAVIATE_API_KEY else 'Non'}")
if WEAVIATE_API_KEY:
    print(f"[DEBUG] WEAVIATE_API_KEY longueur: {len(WEAVIATE_API_KEY)} caractères")

# Nom de la collection dans Weaviate - DOIT CORRESPONDRE À VOTRE APP INTELIA
CLASS_NAME = "InteliaKnowledge"
print(f"[DEBUG] Nom de collection: {CLASS_NAME}")

def connect_to_weaviate():
    """Connexion directe à Weaviate Cloud (v4) avec debug"""
    print("[DEBUG] === DÉBUT CONNEXION WEAVIATE ===")
    try:
        print("[DEBUG] Création des credentials d'authentification...")
        
        # Correction A - Connexion améliorée pour Weaviate Cloud
        if ".weaviate.cloud" in WEAVIATE_URL and WEAVIATE_API_KEY:
            auth_credentials = wvc.init.Auth.api_key(WEAVIATE_API_KEY)
            print("[DEBUG] Credentials créés avec succès")
            
            print(f"[DEBUG] Tentative de connexion à : {WEAVIATE_URL}")
            client = weaviate.connect_to_weaviate_cloud(
                cluster_url=WEAVIATE_URL,
                auth_credentials=auth_credentials
            )
            print("[DEBUG] Objet client créé")
        else:
            # Fallback pour connexion locale
            print("[DEBUG] Configuration pour Weaviate local")
            client = weaviate.connect_to_local()
        
        print("[DEBUG] Test de disponibilité du cluster...")
        if client.is_ready():
            print("[DEBUG] Cluster Weaviate prêt")
            print("[DEBUG] Test de connexion avec une requête basique...")
            
            # Test basique pour confirmer la connexion
            try:
                collections = client.collections.list_all()
                collection_names = []
                for c in collections:
                    if hasattr(c, 'name'):
                        collection_names.append(c.name)
                    else:
                        collection_names.append(str(c))
                print(f"[DEBUG] Collections disponibles: {collection_names}")
            except Exception as list_error:
                print(f"[DEBUG] Erreur liste collections (non critique): {list_error}")
                print("[DEBUG] Connexion semble fonctionnelle malgré l'erreur de liste")
            
            print("✅ Connexion Weaviate réussie")
            return client
        else:
            print("[DEBUG] Cluster Weaviate non prêt")
            print("❌ Weaviate non prêt")
            return None
            
    except Exception as e:
        print(f"[DEBUG] Exception lors de la connexion: {type(e).__name__}")
        print(f"[DEBUG] Message d'erreur: {str(e)}")
        print(f"[DEBUG] Traceback complet:")
        traceback.print_exc()
        print(f"❌ Erreur connexion Weaviate: {e}")
        return None

def reset_collection(client):
    """Supprime et recrée la collection avec le bon schéma"""
    print("[DEBUG] === RESET COLLECTION ===")
    try:
        if client.collections.exists(CLASS_NAME):
            print(f"[DEBUG] Suppression de la collection {CLASS_NAME}...")
            client.collections.delete(CLASS_NAME)
            print(f"✅ Collection {CLASS_NAME} supprimée")
        else:
            print(f"[DEBUG] Collection {CLASS_NAME} n'existe pas, rien à supprimer")
        return True
    except Exception as e:
        print(f"[DEBUG] Exception lors du reset: {type(e).__name__}: {e}")
        print(f"❌ Erreur suppression: {e}")
        return False

def ensure_schema_exists(client):
    """Crée le schéma Weaviate si nécessaire (v4) avec debug"""
    print("[DEBUG] === VÉRIFICATION/CRÉATION SCHÉMA ===")
    try:
        print(f"[DEBUG] Vérification existence collection '{CLASS_NAME}'...")
        collection_exists = client.collections.exists(CLASS_NAME)
        print(f"[DEBUG] Collection existe: {collection_exists}")
        
        if not collection_exists:
            print("[DEBUG] Création de la collection...")
            print("[DEBUG] Définition des propriétés...")
            
            properties = [
                wvc.config.Property(name="content", data_type=wvc.config.DataType.TEXT),
                wvc.config.Property(name="title", data_type=wvc.config.DataType.TEXT),
                wvc.config.Property(name="category", data_type=wvc.config.DataType.TEXT),
                wvc.config.Property(name="source", data_type=wvc.config.DataType.TEXT),
                wvc.config.Property(name="language", data_type=wvc.config.DataType.TEXT),
                wvc.config.Property(name="geneticLine", data_type=wvc.config.DataType.TEXT),
                wvc.config.Property(name="species", data_type=wvc.config.DataType.TEXT),
                wvc.config.Property(name="originalFile", data_type=wvc.config.DataType.TEXT),
                wvc.config.Property(name="fileHash", data_type=wvc.config.DataType.TEXT),
                wvc.config.Property(name="syncTimestamp", data_type=wvc.config.DataType.NUMBER),
                wvc.config.Property(name="chunkIndex", data_type=wvc.config.DataType.NUMBER),
                wvc.config.Property(name="totalChunks", data_type=wvc.config.DataType.NUMBER),
                wvc.config.Property(name="isComplete", data_type=wvc.config.DataType.BOOLEAN)
            ]
            print(f"[DEBUG] {len(properties)} propriétés définies")
            
            # CORRECTION 2 : Activer la vectorisation OpenAI
            print("[DEBUG] Configuration vectorisation OpenAI...")
            client.collections.create(
                name=CLASS_NAME,
                description="Documents de connaissance Intelia Expert avec chunking",
                properties=properties,
                vectorizer_config=wvc.config.Configure.Vectorizer.text2vec_openai(
                    model="text-embedding-3-small"
                )
            )
            print(f"[DEBUG] Collection créée avec succès avec vectorisation OpenAI")
            print(f"✅ Collection {CLASS_NAME} créée")
        else:
            print(f"[DEBUG] Collection déjà existante")
            print(f"✅ Collection {CLASS_NAME} existe déjà")
            
    except Exception as e:
        print(f"[DEBUG] Exception lors création schéma: {type(e).__name__}")
        print(f"[DEBUG] Message d'erreur: {str(e)}")
        traceback.print_exc()
        print(f"❌ Erreur création schéma: {e}")
        return False
    return True

def get_existing_hashes(client) -> Set[str]:
    """Récupère les hashes des documents déjà présents (v4) avec debug"""
    print("[DEBUG] === RÉCUPÉRATION HASHES EXISTANTS ===")
    try:
        print(f"[DEBUG] Récupération collection '{CLASS_NAME}'...")
        collection = client.collections.get(CLASS_NAME)
        print("[DEBUG] Collection récupérée")
        
        print("[DEBUG] Exécution requête pour obtenir les hashes...")
        response = collection.query.fetch_objects(
            limit=10000,
            return_properties=["fileHash"]
        )
        print(f"[DEBUG] Requête exécutée, {len(response.objects)} objets retournés")
        
        hashes = set()
        for obj in response.objects:
            file_hash = obj.properties.get('fileHash', '')
            if file_hash:
                hashes.add(file_hash)
                print(f"[DEBUG] Hash trouvé: {file_hash[:16]}...")
        
        print(f"[DEBUG] Total hashes récupérés: {len(hashes)}")
        return hashes
        
    except Exception as e:
        print(f"[DEBUG] Exception lors récupération hashes: {type(e).__name__}")
        print(f"[DEBUG] Message d'erreur: {str(e)}")
        traceback.print_exc()
        print(f"❌ Erreur récupération hashes: {e}")
        return set()

def get_file_hash(file_path: str) -> str:
    """Génère un hash unique pour un fichier avec debug"""
    print(f"[DEBUG] Calcul hash pour: {os.path.basename(file_path)}")
    try:
        with open(file_path, 'rb') as f:
            content = f.read()
            file_hash = hashlib.md5(content).hexdigest()
            print(f"[DEBUG] Hash calculé: {file_hash}")
            print(f"[DEBUG] Taille fichier: {len(content)} bytes")
            return file_hash
    except Exception as e:
        print(f"[DEBUG] Erreur calcul hash: {e}")
        raise

def split_text_into_chunks(text: str, max_chars: int = 7000, overlap: int = 500) -> List[str]:
    """Découpe le texte en chunks avec chevauchement pour préserver le contexte"""
    print(f"[DEBUG] Découpage texte de {len(text)} caractères en chunks de {max_chars} chars")
    
    if len(text) <= max_chars:
        print("[DEBUG] Texte assez court, pas de découpage nécessaire")
        return [text]
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + max_chars
        
        # Si ce n'est pas le dernier chunk, essayer de couper à une phrase complète
        if end < len(text):
            # Chercher le dernier point, point d'exclamation ou point d'interrogation
            last_sentence_end = max(
                text.rfind('.', start, end),
                text.rfind('!', start, end),
                text.rfind('?', start, end),
                text.rfind('\n\n', start, end)  # Ou paragraphe
            )
            
            # Si on trouve une fin de phrase, couper là 
            if last_sentence_end > start + max_chars // 2:  # Au moins à mi-chemin
                end = last_sentence_end + 1
            # Sinon, chercher un espace pour éviter de couper un mot
            else:
                last_space = text.rfind(' ', start, end)
                if last_space > start:
                    end = last_space
        
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
            print(f"[DEBUG] Chunk {len(chunks)}: {len(chunk)} caractères")
        
        # Calculer le prochain démarrage avec chevauchement
        start = end - overlap if end < len(text) else len(text)
        
        # Éviter les boucles infinies
        if start >= end:
            break
    
    print(f"[DEBUG] Découpage terminé: {len(chunks)} chunks créés")
    return chunks

def load_json_document(file_path: str) -> List[Dict]:
    """Charge et convertit un document JSON en chunks avec debug"""
    print(f"[DEBUG] === CHARGEMENT DOCUMENT: {os.path.basename(file_path)} ===")
    try:
        print("[DEBUG] Lecture fichier JSON...")
        with open(file_path, 'r', encoding='utf-8') as f:
            doc = json.load(f)
        print(f"[DEBUG] JSON chargé, clés principales: {list(doc.keys())}")
        
        # Extraction du contenu
        content = ""
        if doc.get('text'):
            content = doc['text'].strip()
            print(f"[DEBUG] Contenu extrait du champ 'text': {len(content)} caractères")
        elif doc.get('chunks') and isinstance(doc['chunks'], list):
            content = '\n\n'.join(chunk for chunk in doc['chunks'] if chunk.strip())
            print(f"[DEBUG] Contenu extrait de {len(doc['chunks'])} chunks: {len(content)} caractères")
        elif doc.get('content'):
            content = doc['content'].strip()
            print(f"[DEBUG] Contenu extrait du champ 'content': {len(content)} caractères")
        else:
            print("[DEBUG] Aucun contenu trouvé dans le document")
        
        # Nettoyage du contenu
        print("[DEBUG] Nettoyage du contenu...")
        content = clean_content(content)
        print(f"[DEBUG] Contenu après nettoyage: {len(content)} caractères")
        
        # Génération du titre
        print("[DEBUG] Génération du titre...")
        title = generate_title(doc, file_path)
        print(f"[DEBUG] Titre généré: '{title}'")
        
        # Métadonnées
        metadata = doc.get('metadata', {})
        print(f"[DEBUG] Métadonnées trouvées: {list(metadata.keys()) if metadata else 'Aucune'}")
        
        # Découpage en chunks
        print("[DEBUG] Découpage en chunks...")
        text_chunks = split_text_into_chunks(content)
        
        # Création des documents chunks
        documents = []
        file_hash = get_file_hash(file_path)
        base_timestamp = time.time()
        
        for i, chunk_content in enumerate(text_chunks):
            chunk_doc = {
                'content': chunk_content,
                'title': f"{title}" + (f" (partie {i+1})" if len(text_chunks) > 1 else ""),
                'category': determine_category(metadata, chunk_content),
                'source': 'direct_import',
                'language': detect_language(chunk_content),
                # Correction B - Normalisation geneticLine
                'geneticLine': metadata.get('genetic_line', 'unknown').lower(),
                'species': metadata.get('species', 'unknown'),
                'originalFile': os.path.basename(file_path),
                'fileHash': file_hash,
                'syncTimestamp': base_timestamp,
                'chunkIndex': i,
                'totalChunks': len(text_chunks),
                'isComplete': (len(text_chunks) == 1)  # True si un seul chunk
            }
            documents.append(chunk_doc)
        
        print(f"[DEBUG] Document converti en {len(documents)} chunks")
        for i, doc in enumerate(documents):
            print(f"[DEBUG] Chunk {i+1}: {len(doc['content'])} chars - {doc['category']} - {doc['language']}")
        
        return documents
        
    except Exception as e:
        print(f"[DEBUG] Exception lors chargement document: {type(e).__name__}")
        print(f"[DEBUG] Message d'erreur: {str(e)}")
        traceback.print_exc()
        raise

def clean_content(content: str) -> str:
    """Nettoie le contenu du document avec debug"""
    if not content:
        print("[DEBUG] Contenu vide, rien à nettoyer")
        return ""
    
    print(f"[DEBUG] Nettoyage contenu de {len(content)} caractères")
    import re
    
    original_length = len(content)
    content = content.replace('![Image description]', '')
    content = content.replace('\\[', '[').replace('\\]', ']')
    content = re.sub(r'\s+', ' ', content)
    content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
    content = content.strip()
    
    print(f"[DEBUG] Nettoyage terminé: {original_length} -> {len(content)} caractères")
    return content

def generate_title(doc: Dict, file_path: str) -> str:
    """Génère un titre pour le document avec debug"""
    print("[DEBUG] Génération titre...")
    
    if doc.get('source_file'):
        filename = os.path.splitext(os.path.basename(doc['source_file']))[0]
        if filename and filename != 'extracted':
            title = filename.replace('_', ' ').replace('-', ' ')
            print(f"[DEBUG] Titre depuis source_file: '{title}'")
            return title
    
    filename = os.path.splitext(os.path.basename(file_path))[0]
    title = filename.replace('_', ' ').replace('-', ' ')
    print(f"[DEBUG] Titre depuis nom fichier: '{title}'")
    return title

def determine_category(metadata: Dict, content: str) -> str:
    """Détermine la catégorie du document avec debug"""
    species = metadata.get('species', '').lower()
    content_lower = content.lower()
    
    if species == 'layers' or 'pondeuse' in content_lower:
        category = 'pondeuses'
    elif species == 'broilers' or 'poulet de chair' in content_lower:
        category = 'poulets_chair'
    elif 'nutrition' in content_lower:
        category = 'nutrition'
    elif 'management' in content_lower:
        category = 'management'
    else:
        category = 'general'
    
    return category

def detect_language(content: str) -> str:
    """Détection basique de la langue avec debug"""
    if not content:
        return 'fr'
    
    content_lower = content.lower()
    english_indicators = ['the', 'and', 'of', 'to', 'in', 'management', 'performance']
    french_indicators = ['le', 'de', 'et', 'à', 'un', 'gestion', 'performance']
    
    english_count = sum(1 for word in english_indicators if word in content_lower)
    french_count = sum(1 for word in french_indicators if word in content_lower)
    
    language = 'en' if english_count > french_count else 'fr'
    return language

def upload_documents_to_weaviate(client, documents: List[Dict]) -> int:
    """Upload les documents vers Weaviate par lots (v4) avec debug"""
    print("[DEBUG] === DÉBUT UPLOAD DOCUMENTS ===")
    uploaded_count = 0
    total_docs = len(documents)
    
    try:
        print(f"[DEBUG] Upload de {total_docs} documents...")
        print(f"[DEBUG] Récupération collection '{CLASS_NAME}'...")
        collection = client.collections.get(CLASS_NAME)
        print("[DEBUG] Collection récupérée")
        
        # Upload par lots
        batch_size = 1  # Un seul document à la fois pour connexion stable
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = len(documents)
            
            print(f"[DEBUG] === DOCUMENT {batch_num}/{total_batches} ===")
            print(f"[DEBUG] Traitement document unique...")
            
            objects_to_insert = []
            
            for j, doc in enumerate(batch):
                doc_index = i + j + 1
                print(f"[DEBUG] [{doc_index}/{total_docs}] Document: {doc['title'][:50]}...")
                print(f"[DEBUG] Contenu: {len(doc['content'])} caractères (chunk {doc['chunkIndex']+1}/{doc['totalChunks']})")
                
                # Préparer l'objet pour Weaviate (avec vectorisation automatique)
                print(f"[DEBUG] Préparation objet Weaviate...")
                
                # Propriétés séparées du vecteur pour Weaviate v4
                properties = {
                    "content": doc['content'],
                    "title": doc['title'],
                    "category": doc['category'],
                    "source": doc['source'],
                    "language": doc['language'],
                    "geneticLine": doc['geneticLine'],
                    "species": doc['species'],
                    "originalFile": doc['originalFile'],
                    "fileHash": doc['fileHash'],
                    "syncTimestamp": doc['syncTimestamp'],
                    "chunkIndex": doc['chunkIndex'],
                    "totalChunks": doc['totalChunks'],
                    "isComplete": doc['isComplete']
                }
                
                # Créer l'objet DataObject pour Weaviate v4 (sans embedding manuel)
                from weaviate.classes.data import DataObject
                data_obj = DataObject(
                    properties=properties
                    # Pas de vector car Weaviate va automatiquement vectoriser avec OpenAI
                )
                
                objects_to_insert.append(data_obj)
                print(f"[DEBUG] Objet préparé pour {doc['title']}")
            
            # Insert du document unique
            print(f"[DEBUG] Upload document vers Weaviate...")
            try:
                result = collection.data.insert_many(objects_to_insert)
                print(f"[DEBUG] Insert terminé")
                
                # Vérification des résultats avec la nouvelle structure v4
                if hasattr(result, 'failed_objects') and result.failed_objects:
                    print(f"[DEBUG] Échec:")
                    for idx, failed in enumerate(result.failed_objects):
                        print(f"[DEBUG]   Erreur: {failed.message}")
                    print(f"❌ Document {batch_num}: Échec - {doc['title']}")
                elif hasattr(result, 'errors') and result.errors:
                    print(f"[DEBUG] Erreur dans result.errors:")
                    for error in result.errors:
                        print(f"[DEBUG]   Erreur: {error}")
                    print(f"❌ Document {batch_num}: Échec - {doc['title']}")
                else:
                    print(f"[DEBUG] Succès! (result type: {type(result)})")
                    uploaded_count += 1
                    chunk_info = f"(chunk {doc['chunkIndex']+1}/{doc['totalChunks']})" if doc['totalChunks'] > 1 else ""
                    print(f"✅ Document {batch_num}/{total_batches}: {doc['title']} {chunk_info}")
                
            except Exception as batch_error:
                print(f"[DEBUG] Exception upload: {type(batch_error).__name__}: {batch_error}")
                print(f"❌ Erreur upload document {batch_num}: {batch_error}")
            
            # Pause entre chaque document pour connexion stable
            if i + batch_size < len(documents):
                print("[DEBUG] Pause 1 seconde...")
                time.sleep(1)
                
    except Exception as e:
        print(f"[DEBUG] Exception générale upload: {type(e).__name__}: {e}")
        traceback.print_exc()
        print(f"❌ Erreur upload batch: {e}")
    
    print(f"[DEBUG] Upload terminé - Total uploadé: {uploaded_count}")
    return uploaded_count

def find_json_files(directory: str) -> List[str]:
    """Trouve tous les fichiers JSON dans le répertoire avec debug"""
    print(f"[DEBUG] Recherche fichiers JSON dans: {directory}")
    json_files = []
    
    for root, dirs, files in os.walk(directory):
        print(f"[DEBUG] Exploration dossier: {root}")
        json_in_dir = [f for f in files if f.lower().endswith('.json')]
        print(f"[DEBUG] {len(json_in_dir)} fichiers JSON trouvés dans ce dossier")
        
        for file in json_in_dir:
            full_path = os.path.join(root, file)
            json_files.append(full_path)
            print(f"[DEBUG] Ajouté: {file}")
    
    print(f"[DEBUG] Total fichiers JSON: {len(json_files)}")
    return json_files

def main():
    print("[DEBUG] === DÉBUT SCRIPT ===")
    parser = argparse.ArgumentParser(description='Import direct vers Weaviate v4 SANS TRONCATURE')
    parser.add_argument('directory', help='Répertoire contenant les fichiers JSON')
    parser.add_argument('--batch-size', type=int, default=5, help='Taille des lots (défaut: 5)')
    parser.add_argument('--dry-run', action='store_true', help='Simulation sans envoi')
    parser.add_argument('--chunk-size', type=int, default=7000, help='Taille max des chunks (défaut: 7000)')
    parser.add_argument('--reset', action='store_true', help='Supprime et recrée la collection')
    
    args = parser.parse_args()
    print(f"[DEBUG] Arguments: directory={args.directory}, batch_size={args.batch_size}, dry_run={args.dry_run}, chunk_size={args.chunk_size}, reset={args.reset}")
    
    if not os.path.exists(args.directory):
        print(f"[DEBUG] Répertoire inexistant: {args.directory}")
        print(f"❌ Le répertoire {args.directory} n'existe pas")
        return
    
    if not WEAVIATE_API_KEY:
        print("[DEBUG] Clé API Weaviate manquante")
        print("❌ WEAVIATE_API_KEY non définie. Ajoutez-la dans votre fichier .env")
        return
    
    print(f"🔍 Scan du répertoire: {args.directory}")
    json_files = find_json_files(args.directory)
    print(f"🔍 {len(json_files)} fichiers JSON trouvés")
    
    if not json_files:
        print("[DEBUG] Aucun fichier JSON trouvé")
        print("ℹ️ Aucun fichier JSON trouvé")
        return
    
    # Connexion à Weaviate
    print("🔌 Connexion à Weaviate...")
    client = connect_to_weaviate()
    if not client:
        print("[DEBUG] Échec connexion Weaviate")
        return
    
    # Reset de la collection si demandé
    if args.reset:
        print("🗑️ Reset de la collection...")
        if not reset_collection(client):
            print("[DEBUG] Échec reset collection")
            return
    
    # Vérification/création du schéma
    print("🔧 Vérification du schéma...")
    if not ensure_schema_exists(client):
        print("[DEBUG] Échec création/vérification schéma")
        return
    
    # Configuration embeddings OpenAI
    print("🤖 Configuration embeddings OpenAI...")
    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key:
        print("❌ OPENAI_API_KEY non définie. Ajoutez-la dans votre fichier .env")
        return
    print("✅ Embeddings OpenAI configurés")
    
    # Récupération des documents existants
    print("🔍 Vérification des documents existants...")
    existing_hashes = get_existing_hashes(client)
    print(f"📊 {len(existing_hashes)} documents déjà présents")
    
    # Filtrage des nouveaux documents et création des chunks
    print("[DEBUG] === TRAITEMENT ET CHUNKING DES DOCUMENTS ===")
    all_document_chunks = []
    skipped_files = 0
    
    for file_path in json_files:
        try:
            print(f"[DEBUG] Traitement: {os.path.basename(file_path)}")
            file_hash = get_file_hash(file_path)
            
            if file_hash in existing_hashes and not args.reset:
                skipped_files += 1
                print(f"[DEBUG] Document déjà présent (hash match)")
                print(f"⭐ Ignoré (déjà présent): {os.path.basename(file_path)}")
                continue
            
            print(f"[DEBUG] Nouveau document détecté")
            # load_json_document retourne maintenant une liste de chunks
            document_chunks = load_json_document(file_path)
            all_document_chunks.extend(document_chunks)
            
            if len(document_chunks) == 1:
                print(f"📄 Nouveau: {os.path.basename(file_path)} -> {document_chunks[0]['title']}")
            else:
                print(f"📄 Nouveau: {os.path.basename(file_path)} -> {document_chunks[0]['title']} ({len(document_chunks)} chunks)")
            
        except Exception as e:
            print(f"[DEBUG] Exception traitement {file_path}: {type(e).__name__}: {e}")
            traceback.print_exc()
            print(f"❌ Erreur traitement {file_path}: {e}")
    
    print(f"\n📈 Résumé:")
    print(f"   - Fichiers analysés: {len(json_files)}")
    print(f"   - Déjà présents: {skipped_files}")
    print(f"   - Nouveaux fichiers: {len(json_files) - skipped_files}")
    print(f"   - Total chunks à importer: {len(all_document_chunks)}")
    
    if not all_document_chunks:
        print("[DEBUG] Aucun chunk à importer")
        print("✅ Tous les documents sont déjà synchronisés")
        client.close()
        return
    
    if args.dry_run:
        print("[DEBUG] Mode dry-run activé")
        print("🔍 Mode simulation - aucun document envoyé")
        for chunk in all_document_chunks[:10]:  # Afficher 10 premiers chunks
            chunk_info = f" (chunk {chunk['chunkIndex']+1}/{chunk['totalChunks']})" if chunk['totalChunks'] > 1 else ""
            print(f"   - {chunk['title']}{chunk_info} ({chunk['category']}) - {len(chunk['content'])} chars")
        if len(all_document_chunks) > 10:
            print(f"   ... et {len(all_document_chunks) - 10} autres chunks")
        client.close()
        return
    
    # Upload vers Weaviate
    print(f"\n🚀 Upload vers Weaviate...")
    total_uploaded = upload_documents_to_weaviate(client, all_document_chunks)
    
    # Fermer la connexion Weaviate
    print("[DEBUG] Fermeture connexion Weaviate...")
    client.close()
    print("[DEBUG] Connexion fermée")
    
    print(f"\n🎉 Import terminé!")
    print(f"   - Chunks uploadés: {total_uploaded}/{len(all_document_chunks)}")
    print(f"   - Fichiers ignorés: {skipped_files}")
    print("[DEBUG] === FIN SCRIPT ===")

if __name__ == "__main__":
    main()