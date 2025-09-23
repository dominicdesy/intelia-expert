"""
Segmenteur de contenu intelligent pour créer des chunks sémantiques
Version corrigée - Résout la perte massive de contenu
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
    """Segmenteur corrigé - Préserve les chunks volumineux et divise intelligemment"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

        # CORRECTION CIBLÉE: Limites ajustées mais fonctions conservées
        self.min_chunk_words = 20  # Réduit de 50 à 20
        self.max_chunk_words = 3000  # Augmenté de 500 à 3000 (au lieu de 2000)
        self.overlap_words = 50  # Augmenté pour meilleur contexte

        # Options pour préservation des chunks existants
        self.preserve_large_chunks = True  # Préserver chunks > 3000 mots
        self.smart_splitting = True  # Division intelligente si nécessaire

    def create_semantic_segments(
        self,
        json_file: str,
        txt_file: str = None,
        document_context: DocumentContext = None,
    ) -> List[Dict[str, Any]]:
        """Crée des segments en préservant ALL chunks pré-extraits"""
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                json_data = json.load(f)

            # PRIORITÉ 1: Préserver les chunks pré-extraits
            existing_chunks = json_data.get("chunks", [])
            if existing_chunks and len(existing_chunks) > 0:
                self.logger.info(
                    f"📦 Traitement {len(existing_chunks)} chunks pré-extraits"
                )

                segments = []
                chunks_accepted = 0
                chunks_split = 0
                chunks_rejected = 0

                for i, chunk_content in enumerate(existing_chunks):
                    if (
                        not isinstance(chunk_content, str)
                        or len(chunk_content.strip()) < 20
                    ):
                        chunks_rejected += 1
                        continue

                    # Nettoyage du contenu
                    cleaned_content = self._clean_content(chunk_content)
                    word_count = len(cleaned_content.split())

                    # CORRECTION CRITIQUE: Accepter tous les chunks valides
                    if word_count >= self.min_chunk_words:

                        if word_count <= self.max_chunk_words:
                            # Chunk dans les limites - accepté directement
                            segment = {
                                "content": cleaned_content,
                                "word_count": word_count,
                                "chunk_index": i,
                                "source": "pre_extracted",
                                "segment_type": "pre_extracted_preserved",
                            }
                            segments.append(segment)
                            chunks_accepted += 1
                            self.logger.debug(
                                f"✅ Chunk {i}: {word_count} mots - ACCEPTÉ"
                            )

                        elif self.preserve_large_chunks:
                            # Chunk volumineux - préservé tel quel
                            segment = {
                                "content": cleaned_content,
                                "word_count": word_count,
                                "chunk_index": i,
                                "source": "pre_extracted_large",
                                "segment_type": "large_chunk_preserved",
                            }
                            segments.append(segment)
                            chunks_accepted += 1
                            self.logger.info(
                                f"📄 Chunk {i}: {word_count} mots - PRÉSERVÉ (volumineux)"
                            )

                        elif self.smart_splitting:
                            # Division intelligente du chunk volumineux
                            split_segments = self._smart_split_large_chunk(
                                cleaned_content, i, source="pre_extracted_split"
                            )
                            segments.extend(split_segments)
                            chunks_split += 1
                            self.logger.info(
                                f"✂️ Chunk {i}: {word_count} mots - DIVISÉ en {len(split_segments)} parties"
                            )

                        else:
                            chunks_rejected += 1
                            self.logger.warning(
                                f"❌ Chunk {i}: {word_count} mots - REJETÉ (trop volumineux)"
                            )
                    else:
                        chunks_rejected += 1
                        self.logger.debug(
                            f"❌ Chunk {i}: {word_count} mots - REJETÉ (trop petit)"
                        )

                # Rapport de traitement
                self.logger.info(
                    f"📊 Résultats: {chunks_accepted} acceptés, {chunks_split} divisés, "
                    f"{chunks_rejected} rejetés → {len(segments)} segments finaux"
                )

                if segments:
                    return segments
                else:
                    self.logger.warning(
                        "Aucun segment valide depuis chunks pré-extraits"
                    )

            # Fallback: segmentation normale si pas de chunks pré-extraits
            self.logger.info("📄 Passage à la segmentation normale")
            return self._perform_normal_segmentation(json_file, txt_file)

        except Exception as e:
            self.logger.error(f"Erreur segmentation: {e}")
            return []

    def _smart_split_large_chunk(
        self, content: str, original_index: int, source: str = "split"
    ) -> List[Dict[str, Any]]:
        """Division intelligente d'un chunk volumineux"""
        segments = []

        # Tentative de division par sections markdown
        if self._has_markdown_structure(content):
            segments = self._split_by_markdown_sections(content, original_index, source)
        else:
            # Division par paragraphes avec chevauchement
            segments = self._split_by_paragraphs_with_overlap(
                content, original_index, source
            )

        # Si échec, division brutale en respectant les phrases
        if not segments:
            segments = self._split_by_sentences(content, original_index, source)

        return segments

    def _split_by_markdown_sections(
        self, content: str, original_index: int, source: str
    ) -> List[Dict[str, Any]]:
        """Divise par sections markdown"""
        segments = []
        sections = re.split(r"\n(?=#+\s)", content)

        current_segment = ""
        section_count = 0

        for section in sections:
            section = section.strip()
            if not section:
                continue

            section_words = len(section.split())
            current_words = len(current_segment.split())

            if current_words + section_words <= self.max_chunk_words:
                current_segment += "\n\n" + section if current_segment else section
            else:
                # Sauvegarde segment actuel
                if current_segment:
                    segments.append(
                        {
                            "content": current_segment.strip(),
                            "word_count": len(current_segment.split()),
                            "chunk_index": f"{original_index}_{section_count}",
                            "source": source,
                            "segment_type": "markdown_section_split",
                        }
                    )
                    section_count += 1

                # Nouveau segment
                current_segment = section

        # Segment final
        if current_segment:
            segments.append(
                {
                    "content": current_segment.strip(),
                    "word_count": len(current_segment.split()),
                    "chunk_index": f"{original_index}_{section_count}",
                    "source": source,
                    "segment_type": "markdown_section_split",
                }
            )

        return segments

    def _split_by_paragraphs_with_overlap(
        self, content: str, original_index: int, source: str
    ) -> List[Dict[str, Any]]:
        """Divise par paragraphes avec chevauchement intelligent"""
        segments = []
        paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]

        if not paragraphs:
            return segments

        current_chunk = ""
        current_words = 0
        segment_count = 0

        for i, paragraph in enumerate(paragraphs):
            para_words = len(paragraph.split())

            if current_words + para_words <= self.max_chunk_words:
                current_chunk += "\n\n" + paragraph if current_chunk else paragraph
                current_words += para_words
            else:
                # Sauvegarde chunk actuel
                if current_chunk:
                    segments.append(
                        {
                            "content": current_chunk.strip(),
                            "word_count": current_words,
                            "chunk_index": f"{original_index}_{segment_count}",
                            "source": source,
                            "segment_type": "paragraph_split",
                        }
                    )
                    segment_count += 1

                # Chevauchement: garde les derniers paragraphes
                overlap_paras = self._get_overlap_paragraphs(paragraphs, i)
                current_chunk = (
                    overlap_paras + "\n\n" + paragraph if overlap_paras else paragraph
                )
                current_words = len(current_chunk.split())

        # Segment final
        if current_chunk:
            segments.append(
                {
                    "content": current_chunk.strip(),
                    "word_count": current_words,
                    "chunk_index": f"{original_index}_{segment_count}",
                    "source": source,
                    "segment_type": "paragraph_split",
                }
            )

        return segments

    def _get_overlap_paragraphs(self, paragraphs: List[str], current_index: int) -> str:
        """Récupère les paragraphes de chevauchement"""
        if current_index == 0:
            return ""

        overlap_words = 0
        overlap_paras = []

        # Remonte dans les paragraphes pour créer le chevauchement
        for j in range(current_index - 1, -1, -1):
            para_words = len(paragraphs[j].split())
            if overlap_words + para_words <= self.overlap_words:
                overlap_paras.insert(0, paragraphs[j])
                overlap_words += para_words
            else:
                break

        return "\n\n".join(overlap_paras)

    def _split_by_sentences(
        self, content: str, original_index: int, source: str
    ) -> List[Dict[str, Any]]:
        """Division par phrases en dernier recours"""
        segments = []
        sentences = re.split(r"(?<=[.!?])\s+", content)

        current_segment = ""
        current_words = 0
        segment_count = 0

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            sentence_words = len(sentence.split())

            if current_words + sentence_words <= self.max_chunk_words:
                current_segment += " " + sentence if current_segment else sentence
                current_words += sentence_words
            else:
                # Sauvegarde segment actuel
                if current_segment:
                    segments.append(
                        {
                            "content": current_segment.strip(),
                            "word_count": current_words,
                            "chunk_index": f"{original_index}_{segment_count}",
                            "source": source,
                            "segment_type": "sentence_split",
                        }
                    )
                    segment_count += 1

                # Nouveau segment
                current_segment = sentence
                current_words = sentence_words

        # Segment final
        if current_segment and current_words >= self.min_chunk_words:
            segments.append(
                {
                    "content": current_segment.strip(),
                    "word_count": current_words,
                    "chunk_index": f"{original_index}_{segment_count}",
                    "source": source,
                    "segment_type": "sentence_split",
                }
            )

        return segments

    def _perform_normal_segmentation(
        self, json_file: str, txt_file: str = None
    ) -> List[Dict[str, Any]]:
        """Segmentation normale pour fichiers sans chunks pré-extraits"""
        content_parts = self._extract_content_from_files(json_file, txt_file)
        segments = []

        for part_name, content in content_parts.items():
            if not content or len(content.strip()) < self.min_chunk_words * 3:
                continue

            part_segments = self._segment_content_intelligently(content, part_name)
            segments.extend(part_segments)

        validated_segments = self._validate_and_filter_segments(segments)

        self.logger.info(
            f"Segmentation normale: {len(validated_segments)} segments créés"
        )
        return validated_segments

    def _extract_content_from_files(
        self, json_file: str, txt_file: str = None
    ) -> Dict[str, str]:
        """Extrait le contenu depuis les fichiers JSON et TXT"""
        content_parts = {}

        # Extraction JSON avec gestion d'encodage robuste
        try:
            with open(json_file, "r", encoding="utf-8", errors="strict") as f:
                json_data = json.load(f)
        except UnicodeDecodeError as e:
            self.logger.warning(f"Erreur encodage UTF-8 pour {json_file}: {e}")

            # Auto-détection d'encodage
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

            # Fallback sur chunks (ne devrait pas arriver si appelé correctement)
            elif "chunks" in json_data and isinstance(json_data["chunks"], list):
                for i, chunk in enumerate(json_data["chunks"]):
                    if isinstance(chunk, str) and chunk.strip():
                        content_parts[f"chunk_{i}"] = self._normalize_unicode_content(
                            chunk
                        )

        except Exception as e:
            self.logger.error(f"Erreur traitement contenu JSON {json_file}: {e}")

        # Extraction TXT (prioritaire si disponible)
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
            except Exception as e:
                self.logger.error(f"Erreur lecture TXT {txt_file}: {e}")

        return content_parts

    def _normalize_unicode_content(self, content: str) -> str:
        """Normalise le contenu Unicode"""
        if not content:
            return content

        try:
            # Normalisation NFD puis NFC pour gérer les accents composés
            normalized = unicodedata.normalize("NFD", content)
            normalized = unicodedata.normalize("NFC", normalized)

            # Suppression des caractères de contrôle problématiques
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
        content = self._clean_content(content)

        if self._has_markdown_structure(content):
            return self._segment_by_markdown_sections(content, source_name)
        else:
            return self._segment_by_paragraphs(content, source_name)

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

            if paragraph_words > self.max_chunk_words:
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

                # Nouveau chunk avec chevauchement
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
        """Valide et filtre les segments selon les critères de qualité ASSOUPLIS"""
        validated = []

        for segment in segments:
            word_count = segment.get("word_count", 0)
            content = segment.get("content", "")

            # CORRECTION: Critères assouplis pour préserver le contenu
            if word_count < self.min_chunk_words:
                continue

            # Filtre contenu vide seulement
            if not content or len(content.strip()) < 10:
                continue

            # Filtre qualité très permissif
            if not self._is_acceptable_content(content):
                continue

            validated.append(segment)

        return validated

    def _is_acceptable_content(self, content: str) -> bool:
        """Critères de qualité très assouplis pour préserver le contenu"""
        # Contenu trop court
        if len(content) < 10:
            return False

        # Contenu majoritairement constitué de caractères spéciaux (très permissif)
        special_chars_ratio = len(re.findall(r"[^a-zA-Z0-9\s]", content)) / len(content)
        if special_chars_ratio > 0.8:  # Très permissif
            return False

        # Contenu répétitif extrême seulement
        words = content.split()
        if len(words) > 100:  # Seulement pour contenus très longs
            unique_words = set(words)
            if len(unique_words) / len(words) < 0.05:  # Extrêmement répétitif
                return False

        return True
