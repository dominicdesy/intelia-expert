"""
Segmenteur de contenu intelligent pour créer des chunks sémantiques
Version corrigée - Gestion des chunks pré-extraits
"""

import re
import json
import logging
import unicodedata
from pathlib import Path
from typing import List, Dict, Any
from core.models import DocumentContext

# Gestion robuste des encodages
try:
    import chardet

    CHARDET_AVAILABLE = True
except ImportError:
    CHARDET_AVAILABLE = False


class ContentSegmenter:
    """Segmenteur de contenu sémantique avec gestion Unicode robuste et chunks pré-extraits"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.min_chunk_words = 50
        self.max_chunk_words = 500
        self.overlap_words = 25

    def create_semantic_segments(
        self,
        json_file: str,
        txt_file: str = None,
        document_context: DocumentContext = None,
    ) -> List[Dict[str, Any]]:
        """Crée des segments sémantiques depuis les fichiers JSON/TXT"""
        try:
            # CORRECTION: Vérifier d'abord s'il y a des chunks pré-extraits
            with open(json_file, "r", encoding="utf-8") as f:
                json_data = json.load(f)

            # Utiliser les chunks pré-extraits s'ils existent et sont valides
            existing_chunks = json_data.get("chunks", [])
            if existing_chunks and len(existing_chunks) > 0:
                self.logger.info(
                    f"Utilisation de {len(existing_chunks)} chunks pré-extraits"
                )

                segments = []
                for i, chunk_content in enumerate(existing_chunks):
                    if (
                        isinstance(chunk_content, str)
                        and len(chunk_content.strip()) > 50
                    ):
                        # Nettoyage du contenu du chunk
                        cleaned_content = self._clean_content(chunk_content)
                        word_count = len(cleaned_content.split())

                        # Vérification des critères de qualité
                        if (
                            self.min_chunk_words <= word_count <= self.max_chunk_words
                            and not self._is_low_quality_content(cleaned_content)
                        ):

                            segment = {
                                "content": cleaned_content,
                                "word_count": word_count,
                                "chunk_index": i,
                                "source": "pre_extracted",
                                "segment_type": "pre_extracted_chunk",
                            }
                            segments.append(segment)
                            self.logger.debug(f"Chunk {i} accepté: {word_count} mots")
                        else:
                            self.logger.debug(
                                f"Chunk {i} rejeté: {word_count} mots, critères non respectés"
                            )

                if segments:
                    self.logger.info(
                        f"Segmentation terminée: {len(segments)} segments depuis chunks pré-extraits"
                    )
                    return segments
                else:
                    self.logger.warning(
                        "Aucun chunk pré-extrait valide, passage à la segmentation normale"
                    )

            # Si pas de chunks pré-extraits ou tous invalides, segmentation normale
            return self._perform_normal_segmentation(json_file, txt_file)

        except Exception as e:
            self.logger.error(f"Erreur segmentation: {e}")
            return []

    def _perform_normal_segmentation(
        self, json_file: str, txt_file: str = None
    ) -> List[Dict[str, Any]]:
        """Effectue la segmentation normale quand il n'y a pas de chunks pré-extraits"""
        # Extraction du contenu depuis JSON et TXT
        content_parts = self._extract_content_from_files(json_file, txt_file)

        # Segmentation sémantique
        segments = []

        for part_name, content in content_parts.items():
            if not content or len(content.strip()) < self.min_chunk_words * 5:
                continue

            part_segments = self._segment_content_intelligently(content, part_name)
            segments.extend(part_segments)

        # Post-traitement et validation
        validated_segments = self._validate_and_filter_segments(segments)

        self.logger.info(
            f"Segmentation terminée: {len(validated_segments)} segments créés"
        )
        return validated_segments

    def _extract_content_from_files(
        self, json_file: str, txt_file: str = None
    ) -> Dict[str, str]:
        """Extrait le contenu depuis les fichiers JSON et TXT avec gestion robuste des encodages"""
        content_parts = {}

        # Extraction depuis JSON avec gestion d'encodage robuste
        try:
            with open(json_file, "r", encoding="utf-8", errors="strict") as f:
                json_data = json.load(f)
        except UnicodeDecodeError as e:
            self.logger.warning(f"Erreur encodage UTF-8 pour {json_file}: {e}")

            # Tentative de détection automatique d'encodage
            if CHARDET_AVAILABLE:
                with open(json_file, "rb") as f:
                    raw_data = f.read()
                    detected = chardet.detect(raw_data)
                    encoding = (
                        detected["encoding"]
                        if detected["confidence"] > 0.8
                        else "utf-8"
                    )
                    self.logger.info(
                        f"Encodage détecté: {encoding} (confiance: {detected['confidence']:.2f})"
                    )
            else:
                encoding = "latin-1"

            try:
                with open(json_file, "r", encoding=encoding, errors="replace") as f:
                    json_data = json.load(f)
                self.logger.info(f"Fichier {json_file} lu avec encodage {encoding}")
            except Exception as e:
                self.logger.error(f"Échec lecture {json_file} avec {encoding}: {e}")
                return content_parts

        try:
            # Priorité au texte principal
            if "text" in json_data and json_data["text"]:
                content_parts["main_text"] = self._normalize_unicode_content(
                    json_data["text"]
                )

            # Utilisation des chunks comme fallback (déjà géré plus haut)
            elif "chunks" in json_data and isinstance(json_data["chunks"], list):
                for i, chunk in enumerate(json_data["chunks"]):
                    if isinstance(chunk, str) and chunk.strip():
                        content_parts[f"chunk_{i}"] = self._normalize_unicode_content(
                            chunk
                        )

        except Exception as e:
            self.logger.error(f"Erreur traitement contenu JSON {json_file}: {e}")

        # Extraction depuis TXT (prioritaire si disponible)
        if txt_file and Path(txt_file).exists():
            try:
                with open(txt_file, "r", encoding="utf-8", errors="strict") as f:
                    txt_content = f.read()
                    if txt_content and len(txt_content.strip()) > 100:
                        content_parts["txt_content"] = self._normalize_unicode_content(
                            txt_content
                        )
                        self.logger.info(
                            f"Contenu TXT lu: {len(txt_content)} caractères"
                        )

            except UnicodeDecodeError as e:
                self.logger.warning(f"Erreur encodage UTF-8 pour {txt_file}: {e}")

                # Auto-détection pour TXT
                if CHARDET_AVAILABLE:
                    with open(txt_file, "rb") as f:
                        raw_data = f.read()
                        detected = chardet.detect(raw_data)
                        encoding = (
                            detected["encoding"]
                            if detected["confidence"] > 0.8
                            else "latin-1"
                        )
                else:
                    encoding = "latin-1"

                try:
                    with open(txt_file, "r", encoding=encoding, errors="replace") as f:
                        txt_content = f.read()
                        if txt_content and len(txt_content.strip()) > 100:
                            content_parts["txt_content"] = (
                                self._normalize_unicode_content(txt_content)
                            )
                            self.logger.info(f"Fichier TXT lu avec encodage {encoding}")
                except Exception as e:
                    self.logger.error(f"Échec lecture TXT {txt_file}: {e}")

        return content_parts

    def _normalize_unicode_content(self, content: str) -> str:
        """Normalise le contenu Unicode pour éviter les problèmes d'accents"""
        if not content:
            return content

        try:
            # Normalisation NFD puis NFC pour gérer les accents composés
            normalized = unicodedata.normalize("NFD", content)
            normalized = unicodedata.normalize("NFC", normalized)

            # Suppression des caractères de contrôle problématiques (sauf \n, \t, \r)
            cleaned = "".join(
                char
                for char in normalized
                if not unicodedata.category(char).startswith("C") or char in "\n\t\r"
            )

            return cleaned

        except Exception as e:
            self.logger.warning(f"Erreur normalisation Unicode: {e}")
            return content

    def _segment_content_intelligently(
        self, content: str, source_name: str
    ) -> List[Dict[str, Any]]:
        """Segmente le contenu de manière intelligente"""
        segments = []

        # Nettoyage du contenu
        content = self._clean_content(content)

        # Segmentation par structure markdown/sections
        if self._has_markdown_structure(content):
            segments = self._segment_by_markdown_sections(content, source_name)
        else:
            # Segmentation par paragraphes intelligente
            segments = self._segment_by_paragraphs(content, source_name)

        return segments

    def _clean_content(self, content: str) -> str:
        """Nettoie le contenu en gardant la structure"""
        # Supprime les références d'images markdown
        content = re.sub(r"!\[Image description\]\([^)]*\)", "", content)

        # Normalise les espaces
        content = re.sub(r"\n\s*\n\s*\n", "\n\n", content)
        content = re.sub(r"[ \t]+", " ", content)

        return content.strip()

    def _has_markdown_structure(self, content: str) -> bool:
        """Vérifie si le contenu a une structure markdown"""
        markdown_indicators = [
            r"^#+\s",  # Headers
            r"^\s*[-*]\s",  # Listes
            r"^\s*\d+\.\s",  # Listes numérotées
            r"\*\*.*\*\*",  # Gras
        ]

        for pattern in markdown_indicators:
            if re.search(pattern, content, re.MULTILINE):
                return True
        return False

    def _segment_by_markdown_sections(
        self, content: str, source_name: str
    ) -> List[Dict[str, Any]]:
        """Segmente par sections markdown"""
        segments = []
        current_segment = ""
        current_header = ""

        lines = content.split("\n")

        for line in lines:
            # Détection des headers
            header_match = re.match(r"^(#+)\s+(.+)$", line.strip())

            if header_match:
                # Sauvegarde du segment précédent
                if (
                    current_segment
                    and len(current_segment.split()) >= self.min_chunk_words
                ):
                    segments.append(
                        {
                            "content": current_segment.strip(),
                            "section_header": current_header,
                            "source": source_name,
                            "word_count": len(current_segment.split()),
                            "segment_type": "markdown_section",
                        }
                    )

                # Début nouveau segment
                current_header = header_match.group(2).strip()
                current_segment = line + "\n"

            else:
                current_segment += line + "\n"

                # Vérification taille max
                if len(current_segment.split()) > self.max_chunk_words:
                    segments.append(
                        {
                            "content": current_segment.strip(),
                            "section_header": current_header,
                            "source": source_name,
                            "word_count": len(current_segment.split()),
                            "segment_type": "markdown_section",
                        }
                    )
                    current_segment = ""

        # Segment final
        if current_segment and len(current_segment.split()) >= self.min_chunk_words:
            segments.append(
                {
                    "content": current_segment.strip(),
                    "section_header": current_header,
                    "source": source_name,
                    "word_count": len(current_segment.split()),
                    "segment_type": "markdown_section",
                }
            )

        return segments

    def _segment_by_paragraphs(
        self, content: str, source_name: str
    ) -> List[Dict[str, Any]]:
        """Segmente par paragraphes avec chevauchement"""
        segments = []
        paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]

        current_chunk = ""
        current_words = 0

        for paragraph in paragraphs:
            paragraph_words = len(paragraph.split())

            # Si le paragraphe seul dépasse la limite
            if paragraph_words > self.max_chunk_words:
                # Sauvegarde du chunk actuel s'il existe
                if current_chunk:
                    segments.append(
                        {
                            "content": current_chunk.strip(),
                            "source": source_name,
                            "word_count": current_words,
                            "segment_type": "paragraph_group",
                        }
                    )
                    current_chunk = ""
                    current_words = 0

                # Divise le long paragraphe
                long_segments = self._split_long_paragraph(paragraph, source_name)
                segments.extend(long_segments)

            elif current_words + paragraph_words > self.max_chunk_words:
                # Sauvegarde du chunk actuel
                if current_chunk:
                    segments.append(
                        {
                            "content": current_chunk.strip(),
                            "source": source_name,
                            "word_count": current_words,
                            "segment_type": "paragraph_group",
                        }
                    )

                # Début nouveau chunk avec chevauchement
                current_chunk = paragraph + "\n\n"
                current_words = paragraph_words

            else:
                # Ajout au chunk actuel
                current_chunk += paragraph + "\n\n"
                current_words += paragraph_words

        # Chunk final
        if current_chunk and current_words >= self.min_chunk_words:
            segments.append(
                {
                    "content": current_chunk.strip(),
                    "source": source_name,
                    "word_count": current_words,
                    "segment_type": "paragraph_group",
                }
            )

        return segments

    def _split_long_paragraph(
        self, paragraph: str, source_name: str
    ) -> List[Dict[str, Any]]:
        """Divise un long paragraphe en segments plus petits"""
        segments = []
        sentences = re.split(r"(?<=[.!?])\s+", paragraph)

        current_segment = ""
        current_words = 0

        for sentence in sentences:
            sentence_words = len(sentence.split())

            if current_words + sentence_words > self.max_chunk_words:
                if current_segment:
                    segments.append(
                        {
                            "content": current_segment.strip(),
                            "source": source_name,
                            "word_count": current_words,
                            "segment_type": "sentence_group",
                        }
                    )

                current_segment = sentence + " "
                current_words = sentence_words
            else:
                current_segment += sentence + " "
                current_words += sentence_words

        if current_segment and current_words >= self.min_chunk_words:
            segments.append(
                {
                    "content": current_segment.strip(),
                    "source": source_name,
                    "word_count": current_words,
                    "segment_type": "sentence_group",
                }
            )

        return segments

    def _validate_and_filter_segments(
        self, segments: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Valide et filtre les segments selon les critères de qualité"""
        validated = []

        for segment in segments:
            # Filtres de qualité
            word_count = segment.get("word_count", 0)
            content = segment.get("content", "")

            # Filtre taille
            if word_count < self.min_chunk_words or word_count > self.max_chunk_words:
                continue

            # Filtre contenu vide ou répétitif
            if not content or len(set(content.split())) < 10:
                continue

            # Filtre contenu trop technique (tables HTML, etc.)
            if self._is_low_quality_content(content):
                continue

            validated.append(segment)

        return validated

    def _is_low_quality_content(self, content: str) -> bool:
        """Vérifie si le contenu est de faible qualité"""
        # Contenu principalement constitué de caractères spéciaux
        special_chars_ratio = len(re.findall(r"[^a-zA-Z0-9\s]", content)) / len(content)
        if special_chars_ratio > 0.3:
            return True

        # Contenu répétitif
        words = content.split()
        unique_words = set(words)
        if len(words) > 20 and len(unique_words) / len(words) < 0.3:
            return True

        return False
