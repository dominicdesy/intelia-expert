#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pipeline complet Vectorize Iris - Version tout-en-un
1. Débloque les PDFs protégés
2. Upload vers Vectorize Iris
3. Télécharge les JSON/TXT résultats

Usage:
    python iris_complete_pipeline.py
"""

import os
import sys
import time
import json
import urllib3
import vectorize_client as v
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime
import tempfile

# Force UTF-8 encoding for Windows console
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Charger .env
load_dotenv()

# Configuration par défaut
DEFAULT_INPUT_DIR = r"C:\intelia_gpt\intelia-expert\rag\documents\Sources"
DEFAULT_OUTPUT_DIR = r"C:\intelia_gpt\intelia-expert\rag\documents\Knowledge"

# Limites et exclusions
MAX_FILE_SIZE_MB = 50  # Limite Vectorize Iris
EXCLUDED_FILES = [
    "Manual_of_poultry_diseases_en.pdf"  # Trop gros pour Iris
]


class PDFUnlocker:
    """Débloqueur de PDFs protégés"""

    @staticmethod
    def is_protected(pdf_path: Path) -> bool:
        """Vérifie si le PDF est protégé"""
        try:
            import fitz
            doc = fitz.open(str(pdf_path))
            is_encrypted = doc.is_encrypted
            needs_pass = doc.needs_pass
            doc.close()
            return is_encrypted or needs_pass
        except:
            return False

    @staticmethod
    def unlock_with_pikepdf(input_path: Path, output_path: Path) -> bool:
        """Débloquer avec pikepdf"""
        try:
            import pikepdf
            pdf = pikepdf.open(input_path)
            pdf.save(output_path)
            pdf.close()
            return True
        except ImportError:
            return False
        except Exception as e:
            print(f"      pikepdf error: {e}")
            return False

    @staticmethod
    def unlock_with_pymupdf(input_path: Path, output_path: Path) -> bool:
        """Débloquer avec PyMuPDF"""
        try:
            import fitz
            doc = fitz.open(str(input_path))

            # Essayer mots de passe communs si nécessaire
            if doc.needs_pass:
                common_passwords = ["", "password", "123456"]
                for pwd in common_passwords:
                    if doc.authenticate(pwd):
                        break
                else:
                    doc.close()
                    return False

            doc.save(str(output_path), encryption=fitz.PDF_ENCRYPT_NONE)
            doc.close()
            return True
        except ImportError:
            return False
        except Exception as e:
            print(f"      pymupdf error: {e}")
            return False

    @classmethod
    def unlock(cls, pdf_path: Path) -> Path:
        """
        Débloque un PDF protégé et retourne le chemin du fichier débloqué
        Retourne le fichier original si pas de protection
        """
        if not cls.is_protected(pdf_path):
            print(f"   🔓 PDF déjà débloqué")
            return pdf_path

        print(f"   🔒 PDF protégé - déblocage en cours...")

        # Créer fichier temporaire pour la version débloquée
        temp_dir = Path(tempfile.gettempdir())
        unlocked_path = temp_dir / f"unlocked_{pdf_path.name}"

        # Essayer pikepdf d'abord (plus puissant)
        if cls.unlock_with_pikepdf(pdf_path, unlocked_path):
            print(f"   ✅ Débloqué avec pikepdf")
            return unlocked_path

        # Sinon PyMuPDF
        if cls.unlock_with_pymupdf(pdf_path, unlocked_path):
            print(f"   ✅ Débloqué avec pymupdf")
            return unlocked_path

        # Échec
        print(f"   ⚠️  Impossible de débloquer - tentative avec fichier original")
        return pdf_path


class IrisExtractor:
    """Extracteur Vectorize Iris"""

    def __init__(self, api_key: str, organization_id: str, output_dir: Path):
        self.organization_id = organization_id
        self.output_dir = output_dir
        self.output_dir.mkdir(exist_ok=True, parents=True)

        # Créer client API
        cfg = v.Configuration(host="https://api.vectorize.io")
        if hasattr(cfg, "access_token"):
            cfg.access_token = api_key
        else:
            cfg.api_key = {"ApiKeyAuth": api_key}

        self.api_client = v.ApiClient(cfg)
        self.files_api = v.FilesApi(self.api_client)
        self.extraction_api = v.ExtractionApi(self.api_client)

    def upload_pdf(self, pdf_path: Path) -> str:
        """Upload PDF vers Iris"""
        print(f"   📤 Upload vers Iris...")

        upload_request = v.StartFileUploadRequest(
            content_type="application/pdf",
            name=pdf_path.name
        )

        upload_response = self.files_api.start_file_upload(
            self.organization_id,
            start_file_upload_request=upload_request
        )

        # Upload avec retries
        http = urllib3.PoolManager(
            retries=urllib3.util.retry.Retry(
                total=5, backoff_factor=0.5,
                status_forcelist=[429, 500, 502, 503, 504],
                allowed_methods=frozenset({"PUT"}),
                raise_on_status=False,
            ),
            timeout=60.0,
        )

        file_size = pdf_path.stat().st_size

        with open(pdf_path, "rb") as file:
            response = http.request(
                "PUT",
                upload_response.upload_url,
                body=file,
                headers={
                    "Content-Type": "application/pdf",
                    "Content-Length": str(file_size),
                },
            )

        if response.status not in (200, 201, 204):
            raise Exception(f"Upload échoué: {response.status}")

        print(f"      ✅ Upload réussi ({file_size / 1024:.1f} KB)")
        return upload_response.file_id

    def extract(self, file_id: str) -> str:
        """Démarre extraction"""
        print(f"   🔄 Extraction démarrée...")

        extraction_request = v.StartExtractionRequest(file_id=file_id)

        response = self.extraction_api.start_extraction(
            self.organization_id,
            start_extraction_request=extraction_request
        )

        return response.extraction_id

    def wait_for_result(self, extraction_id: str, timeout=600) -> dict:
        """Attend le résultat (max 10 min)"""
        print(f"   ⏳ Attente du résultat...", end="", flush=True)
        start_time = time.time()

        dots = 0
        while time.time() - start_time < timeout:
            response = self.extraction_api.get_extraction_result(
                self.organization_id,
                extraction_id
            )

            if response.ready:
                elapsed = time.time() - start_time
                if response.data.success:
                    print(f"\r   ✅ Terminé ({elapsed:.1f}s)      ")
                    return response.data
                else:
                    error = getattr(response.data, 'error', 'Erreur inconnue')
                    raise Exception(f"Extraction échouée: {error}")

            # Animation points
            dots = (dots + 1) % 4
            print(f"\r   ⏳ Attente du résultat{'.' * dots}   ", end="", flush=True)
            time.sleep(2)

        raise Exception(f"Timeout après {timeout}s")

    def save_results(self, extraction_data, original_pdf_name: str) -> tuple:
        """Sauvegarde JSON et TXT"""
        base_name = Path(original_pdf_name).stem

        # JSON
        json_path = self.output_dir / f"{base_name}_extracted.json"
        json_data = {
            "source_file": original_pdf_name,
            "extraction_date": datetime.now().isoformat(),
            "text": extraction_data.text,
            "metadata": getattr(extraction_data, "metadata", {}),
            "chunks": getattr(extraction_data, "chunks", [])
        }

        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False, default=str)

        # TXT
        txt_path = self.output_dir / f"{base_name}_extracted.txt"
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(extraction_data.text)

        print(f"   💾 Résultats sauvegardés:")
        print(f"      📄 JSON: {json_path.name}")
        print(f"      📄 TXT: {txt_path.name}")

        return json_path, txt_path


class CompletePipeline:
    """Pipeline complet: déblocage + extraction + sauvegarde"""

    def __init__(self, api_key: str, organization_id: str, output_dir: Path):
        self.unlocker = PDFUnlocker()
        self.extractor = IrisExtractor(api_key, organization_id, output_dir)

    def process_pdf(self, pdf_path: Path) -> dict:
        """Traite un PDF complet"""
        result = {
            "success": False,
            "pdf": pdf_path.name,
            "error": None,
            "json_path": None,
            "txt_path": None
        }

        try:
            print(f"\n{'='*70}")
            print(f"📄 {pdf_path.name}")
            print(f"{'='*70}")

            # Étape 1: Déblocage
            unlocked_pdf = self.unlocker.unlock(pdf_path)

            # Étape 2: Upload
            file_id = self.extractor.upload_pdf(unlocked_pdf)

            # Étape 3: Extraction
            extraction_id = self.extractor.extract(file_id)

            # Étape 4: Attente résultat
            extraction_data = self.extractor.wait_for_result(extraction_id)

            # Étape 5: Sauvegarde
            json_path, txt_path = self.extractor.save_results(
                extraction_data,
                pdf_path.name
            )

            # Statistiques
            text_length = len(extraction_data.text)
            chunks_count = len(getattr(extraction_data, 'chunks', []))

            print(f"\n   📊 Statistiques:")
            print(f"      Texte: {text_length:,} caractères")
            print(f"      Chunks: {chunks_count}")
            print(f"\n   ✅ SUCCÈS")

            result["success"] = True
            result["json_path"] = str(json_path)
            result["txt_path"] = str(txt_path)
            result["text_length"] = text_length
            result["chunks_count"] = chunks_count

            # Nettoyer fichier temporaire débloqué si différent de l'original
            if unlocked_pdf != pdf_path and unlocked_pdf.exists():
                try:
                    unlocked_pdf.unlink()
                except:
                    pass

        except Exception as e:
            print(f"\n   ❌ ÉCHEC: {e}")
            result["error"] = str(e)

        return result

    def is_already_extracted(self, pdf_path: Path) -> bool:
        """Vérifie si le PDF a déjà été extrait"""
        base_name = pdf_path.stem
        json_output = self.extractor.output_dir / f"{base_name}_extracted.json"
        return json_output.exists()

    def should_exclude_file(self, pdf_path: Path) -> tuple[bool, str]:
        """Vérifie si le fichier doit être exclu (nom ou taille)"""
        # Vérifier exclusions par nom
        if pdf_path.name in EXCLUDED_FILES:
            return True, "Fichier exclu (trop gros pour Iris)"

        # Vérifier taille
        file_size_mb = pdf_path.stat().st_size / (1024 * 1024)
        if file_size_mb > MAX_FILE_SIZE_MB:
            return True, f"Fichier trop gros ({file_size_mb:.1f} MB > {MAX_FILE_SIZE_MB} MB)"

        return False, ""

    def process_directory(self, input_dir: Path, skip_existing: bool = True) -> dict:
        """Traite tous les PDFs d'un répertoire"""
        print(f"\n🔍 Recherche de PDFs dans: {input_dir}")

        # Trouver PDFs récursivement
        all_pdf_files = list(input_dir.rglob("*.pdf"))

        if not all_pdf_files:
            print(f"❌ Aucun PDF trouvé")
            return {"total": 0, "success": 0, "failed": 0, "skipped": 0, "excluded": 0, "results": []}

        print(f"📚 {len(all_pdf_files)} PDF(s) trouvé(s)")

        # Filtrer les fichiers
        new_files = []
        already_extracted = []
        excluded_files = []

        for pdf_file in all_pdf_files:
            # Vérifier exclusions
            should_exclude, exclude_reason = self.should_exclude_file(pdf_file)
            if should_exclude:
                excluded_files.append((pdf_file, exclude_reason))
                continue

            # Vérifier si déjà extrait
            if skip_existing and self.is_already_extracted(pdf_file):
                already_extracted.append(pdf_file)
            else:
                new_files.append(pdf_file)

        # Afficher le statut
        print(f"\n📊 Statut:")
        print(f"   ✅ Déjà extraits: {len(already_extracted)}")
        print(f"   🚫 Exclus: {len(excluded_files)}")
        print(f"   🆕 Nouveaux: {len(new_files)}")

        if excluded_files:
            print(f"\n🚫 Fichiers exclus:")
            for pdf, reason in excluded_files:
                print(f"   • {pdf.name} - {reason}")

        if already_extracted:
            print(f"\n⏭️  Fichiers déjà extraits (ignorés):")
            for pdf in already_extracted[:5]:
                print(f"   • {pdf.name}")
            if len(already_extracted) > 5:
                print(f"   ... et {len(already_extracted) - 5} autres")

        if not new_files:
            print(f"\n✅ Aucun nouveau fichier à traiter!")
            return {
                "total": len(all_pdf_files),
                "success": 0,
                "failed": 0,
                "skipped": len(already_extracted),
                "excluded": len(excluded_files),
                "results": []
            }

        # Afficher les fichiers à traiter
        print(f"\n📋 Nouveaux fichiers à traiter:")
        for i, pdf in enumerate(new_files, 1):
            print(f"   {i}. {pdf.name}")

        print(f"\n🚀 Démarrage de l'extraction de {len(new_files)} fichier(s)...")

        # Traitement
        stats = {
            "total": len(all_pdf_files),
            "success": 0,
            "failed": 0,
            "skipped": len(already_extracted),
            "excluded": len(excluded_files),
            "results": []
        }
        start_time = time.time()

        for i, pdf_file in enumerate(new_files, 1):
            print(f"\n[{i}/{len(new_files)}]", end=" ")

            result = self.process_pdf(pdf_file)
            stats["results"].append(result)

            if result["success"]:
                stats["success"] += 1
            else:
                stats["failed"] += 1

            # Pause entre fichiers
            if i < len(new_files):
                time.sleep(1)

        # Rapport final
        elapsed = time.time() - start_time
        stats["elapsed_minutes"] = elapsed / 60

        print(f"\n{'='*70}")
        print(f"📊 RAPPORT FINAL")
        print(f"{'='*70}")
        print(f"Total PDFs trouvés: {stats['total']}")
        print(f"🚫 Exclus (trop gros): {stats['excluded']}")
        print(f"⏭️  Déjà extraits: {stats['skipped']}")
        print(f"🆕 Nouveaux traités: {stats['success'] + stats['failed']}")
        print(f"   ✅ Succès: {stats['success']}")
        print(f"   ❌ Échecs: {stats['failed']}")
        print(f"⏱️  Temps: {elapsed / 60:.1f} minutes")

        if stats['failed'] > 0:
            print(f"\n❌ Fichiers en échec:")
            for r in stats['results']:
                if not r['success']:
                    print(f"   • {r['pdf']}: {r['error']}")

        print(f"{'='*70}")

        return stats


def main():
    """Point d'entrée principal"""
    print("=" * 70)
    print("🚀 PIPELINE COMPLET VECTORIZE IRIS")
    print("=" * 70)
    print("1. Débloque les PDFs protégés")
    print("2. Upload vers Vectorize Iris")
    print("3. Télécharge JSON + TXT")
    print("4. Skip les fichiers déjà extraits")
    print("=" * 70)

    # Vérifier .env
    api_key = os.getenv("VECTORIZE_API_KEY", "").strip()
    organization_id = os.getenv("VECTORIZE_ORGANIZATION_ID", "").strip()

    if not api_key or not organization_id:
        print("\n❌ Variables d'environnement manquantes")
        print("\nCréez un fichier .env avec:")
        print("VECTORIZE_API_KEY=votre_clé")
        print("VECTORIZE_ORGANIZATION_ID=votre_org_id")
        return

    # Configuration avec chemins par défaut
    input_path = Path(DEFAULT_INPUT_DIR)
    output_path = Path(DEFAULT_OUTPUT_DIR)

    print(f"\n📋 Configuration:")
    print(f"   Input: {input_path}")
    print(f"   Output: {output_path}")
    print(f"   Organisation: {organization_id}")

    # Vérifier que les répertoires existent
    if not input_path.exists():
        print(f"\n❌ Répertoire source non trouvé: {input_path}")
        return

    # Créer le répertoire de sortie s'il n'existe pas
    output_path.mkdir(parents=True, exist_ok=True)

    # Lancer le pipeline
    pipeline = CompletePipeline(api_key, organization_id, output_path)
    stats = pipeline.process_directory(input_path, skip_existing=True)

    # Message final
    if stats["success"] > 0:
        print(f"\n🎉 Extraction terminée!")
        print(f"📁 Résultats dans: {output_path}")
        print(f"\n💡 Prochaine étape:")
        print(f"   cd ../knowledge_extractor")
        print(f"   python knowledge_extractor.py --force")
    elif stats["skipped"] > 0 and stats["success"] == 0 and stats["failed"] == 0:
        print(f"\n✅ Tous les fichiers sont déjà extraits!")
        print(f"📁 Résultats existants dans: {output_path}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n⚠️  Interrompu par l'utilisateur")
    except Exception as e:
        print(f"\n❌ Erreur fatale: {e}")
        import traceback
        traceback.print_exc()
