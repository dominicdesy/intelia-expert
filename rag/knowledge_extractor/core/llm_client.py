"""
Client LLM simplifié avec chargement automatique des clés
VERSION CORRIGÉE: Retry automatique + Validation JSON renforcée
"""

import os
import json
import logging
import time
from typing import Dict, Any
from pathlib import Path


class LLMClient:
    """Client LLM unifié avec support multi-provider et retry automatique"""

    def __init__(self, provider="openai", api_key=None, model="gpt-4", max_retries=3):
        self.provider = provider.lower()
        self.max_retries = max_retries
        self.logger = logging.getLogger(__name__)

        # Chargement automatique de la clé API depuis .env parent
        if api_key is None:
            self._load_env_file()
            if self.provider == "openai":
                api_key = os.getenv("OPENAI_API_KEY")
            elif self.provider == "anthropic":
                api_key = os.getenv("ANTHROPIC_API_KEY")

        self.api_key = api_key
        self.model = model
        self._setup_client()

    def _load_env_file(self):
        """Charge le fichier .env depuis le répertoire parent"""
        try:
            from dotenv import load_dotenv

            # Chemins possibles pour le .env (du plus probable au moins probable)
            env_paths = [
                Path(__file__).parent.parent.parent
                / ".env",  # rag/.env (répertoire parent)
                Path(__file__).parent.parent / ".env",  # knowledge_extractor/.env
                Path.cwd() / ".env",  # répertoire courant
                Path.cwd().parent / ".env",  # parent du répertoire courant
            ]

            for env_path in env_paths:
                if env_path.exists():
                    load_dotenv(env_path)
                    self.logger.info(
                        f"Variables d'environnement chargées depuis: {env_path}"
                    )
                    return

            self.logger.warning(
                "Fichier .env non trouvé dans les emplacements attendus"
            )

        except ImportError:
            self.logger.warning(
                "python-dotenv non installé - variables d'environnement système utilisées"
            )

    def _setup_client(self):
        """Configure le client selon le provider"""
        if self.provider == "openai":
            if not self.api_key:
                raise ValueError("Clé OPENAI_API_KEY manquante")
            try:
                import openai

                self.client = openai.OpenAI(api_key=self.api_key)
                self.logger.info(f"Client OpenAI configuré: {self.model}")
            except ImportError:
                raise ImportError("pip install openai requis")

        elif self.provider == "anthropic":
            if not self.api_key:
                raise ValueError("Clé ANTHROPIC_API_KEY manquante")
            try:
                import anthropic

                self.client = anthropic.Anthropic(api_key=self.api_key)
                self.logger.info(f"Client Anthropic configuré: {self.model}")
            except ImportError:
                raise ImportError("pip install anthropic requis")

        elif self.provider == "mock":
            self.client = None
            self.logger.info("Mode MOCK activé")
        else:
            raise ValueError(f"Provider non supporté: {self.provider}")

    @classmethod
    def create_auto(cls, provider="openai", model="gpt-4"):
        """Factory method avec chargement automatique"""
        return cls(provider=provider, model=model)

    def complete(self, prompt: str, max_tokens: int = 1000) -> str:
        """Complète un prompt avec le LLM - AVEC RETRY AUTOMATIQUE"""

        for attempt in range(self.max_retries):
            try:
                if self.provider == "mock":
                    return self._mock_response(prompt)

                elif self.provider == "openai":
                    return self._complete_openai_with_retry(prompt, max_tokens, attempt)

                elif self.provider == "anthropic":
                    return self._complete_anthropic_with_retry(
                        prompt, max_tokens, attempt
                    )

            except Exception as e:
                self.logger.warning(
                    f"Tentative {attempt + 1}/{self.max_retries} échouée: {e}"
                )

                if attempt == self.max_retries - 1:
                    # Dernière tentative échouée - retour en mode dégradé
                    self.logger.error(
                        f"Toutes les tentatives échouées. Erreur finale: {e}"
                    )
                    return self._fallback_response(prompt)

                # Attente exponentielle entre les tentatives
                wait_time = (2**attempt) + 1
                self.logger.info(f"Attente {wait_time}s avant nouvelle tentative...")
                time.sleep(wait_time)

        return self._fallback_response(prompt)

    def _complete_openai_with_retry(
        self, prompt: str, max_tokens: int, attempt: int
    ) -> str:
        """Complétion OpenAI avec validation de réponse renforcée"""

        try:
            # Ajustement des paramètres selon l'attempt
            adjusted_temperature = (
                0.1 if attempt == 0 else 0.05
            )  # Plus conservateur après échec
            adjusted_max_tokens = (
                max_tokens if attempt == 0 else min(max_tokens + 200, 1500)
            )

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=adjusted_max_tokens,
                temperature=adjusted_temperature,
                timeout=30 + (attempt * 10),  # Timeout progressif
            )

            # Validation de la réponse
            if not response or not response.choices:
                raise ValueError("Réponse OpenAI vide ou malformée")

            content = response.choices[0].message.content
            if not content or content.strip() == "":
                raise ValueError("Contenu de réponse vide")

            # Validation JSON si le prompt suggère une réponse JSON
            if self._expects_json_response(prompt):
                validated_content = self._validate_and_fix_json(content, attempt)
                return validated_content

            return content.strip()

        except Exception as e:
            self.logger.error(f"Erreur OpenAI (tentative {attempt + 1}): {e}")
            raise

    def _complete_anthropic_with_retry(
        self, prompt: str, max_tokens: int, attempt: int
    ) -> str:
        """Complétion Anthropic avec validation de réponse renforcée"""

        try:
            adjusted_temperature = 0.1 if attempt == 0 else 0.05
            adjusted_max_tokens = (
                max_tokens if attempt == 0 else min(max_tokens + 200, 1500)
            )

            response = self.client.messages.create(
                model=self.model,
                max_tokens=adjusted_max_tokens,
                temperature=adjusted_temperature,
                messages=[{"role": "user", "content": prompt}],
            )

            if not response or not response.content:
                raise ValueError("Réponse Anthropic vide ou malformée")

            content = response.content[0].text
            if not content or content.strip() == "":
                raise ValueError("Contenu de réponse vide")

            # Validation JSON si nécessaire
            if self._expects_json_response(prompt):
                validated_content = self._validate_and_fix_json(content, attempt)
                return validated_content

            return content.strip()

        except Exception as e:
            self.logger.error(f"Erreur Anthropic (tentative {attempt + 1}): {e}")
            raise

    def _expects_json_response(self, prompt: str) -> bool:
        """Détermine si le prompt attend une réponse JSON"""
        json_indicators = [
            "return json",
            "respond with json",
            "format json",
            "analyze this document",
            "analyze this chunk",
            "return a json object",
            "json format",
            "as json",
        ]
        return any(indicator in prompt.lower() for indicator in json_indicators)

    def _validate_and_fix_json(self, content: str, attempt: int) -> str:
        """SOLUTION 2: Validation et correction du JSON"""

        # Nettoyage préliminaire du contenu
        content = content.strip()

        # Si complètement vide, lever une erreur pour retry
        if not content:
            raise ValueError("Contenu JSON vide - retry nécessaire")

        # Tentative de parsing direct
        try:
            json.loads(content)  # Validation JSON sans assignment
            self.logger.debug(f"JSON valide détecté (tentative {attempt + 1})")
            return content
        except json.JSONDecodeError as e:
            self.logger.warning(f"JSON invalide détecté: {e}")

        # Tentatives de réparation du JSON
        fixed_content = self._attempt_json_repair(content)

        try:
            json.loads(fixed_content)
            self.logger.info(f"JSON réparé avec succès (tentative {attempt + 1})")
            return fixed_content
        except json.JSONDecodeError:
            self.logger.error(
                f"Impossible de réparer le JSON (tentative {attempt + 1})"
            )

            # Sur la dernière tentative, retourner un JSON par défaut
            if attempt >= self.max_retries - 1:
                self.logger.warning("Retour JSON par défaut")
                return self._default_json_response()

            # Sinon, lever erreur pour retry
            raise ValueError("JSON non réparable - retry nécessaire")

    def _attempt_json_repair(self, content: str) -> str:
        """Tentatives de réparation automatique du JSON"""

        # 1. Suppression des caractères de contrôle et espaces problématiques
        content = content.replace("\r", "").replace("\n", " ")
        content = "".join(
            char for char in content if ord(char) >= 32 or char in "\t\n\r"
        )

        # 2. Extraction du JSON si dans un bloc de code
        if "```json" in content:
            try:
                start = content.find("```json") + 7
                end = content.find("```", start)
                if end > start:
                    content = content[start:end].strip()
            except (ValueError, IndexError):
                pass

        # 3. Recherche du premier { et dernier }
        try:
            first_brace = content.find("{")
            last_brace = content.rfind("}")
            if first_brace >= 0 and last_brace > first_brace:
                content = content[first_brace : last_brace + 1]
        except (ValueError, IndexError):
            pass

        # 4. Nettoyages courants
        repairs = [
            ('"', '"'),  # Guillemets courbes
            ('"', '"'),  # Guillemets courbes
            ("'", '"'),  # Guillemets simples -> doubles
            ("True", "true"),  # Booléens Python -> JSON
            ("False", "false"),
            ("None", "null"),
        ]

        for old, new in repairs:
            content = content.replace(old, new)

        return content.strip()

    def _default_json_response(self) -> str:
        """JSON par défaut en cas d'échec total"""
        return json.dumps(
            {
                "genetic_line": "unknown",
                "document_type": "general",
                "confidence_score": 0.0,
                "error": "parsing_failed",
                "fallback": True,
            }
        )

    def _fallback_response(self, prompt: str) -> str:
        """Réponse de fallback en cas d'échec total"""
        self.logger.warning("Activation du mode fallback")

        if self._expects_json_response(prompt):
            return self._default_json_response()

        return "Réponse non disponible - service temporairement indisponible"

    def _mock_response(self, prompt: str) -> str:
        """Réponses mock pour tests"""
        if "analyze this document" in prompt.lower():
            return json.dumps(
                {
                    "genetic_line": "Ross 308",
                    "document_type": "health_management",
                    "species": "broilers",
                    "measurement_units": "metric",
                    "target_audience": "veterinarians",
                    "table_types_expected": ["prevention_guidelines"],
                    "confidence_score": 0.9,
                }
            )
        elif "analyze this chunk" in prompt.lower():
            return json.dumps(
                {
                    "intent_category": "environment_setting",
                    "content_type": "prevention_guidelines",
                    "technical_level": "intermediate",
                    "age_applicability": ["0-42_days"],
                    "applicable_metrics": ["ambient_temp_target"],
                    "actionable_recommendations": ["maintain_consistent_temperature"],
                    "followup_themes": ["ventilation_strategy"],
                    "detected_phase": "all",
                    "detected_bird_type": "broiler",
                    "detected_site_type": "broiler_farm",
                    "confidence_score": 0.85,
                    "reasoning": "Content describes environmental management",
                }
            )
        return "{}"

    def validate_file_content(self, file_path: str) -> Dict[str, Any]:
        """SOLUTION 2: Validation du contenu du fichier ascites_extracted.json"""

        try:
            if not Path(file_path).exists():
                return {
                    "valid": False,
                    "error": "File not found",
                    "file_path": file_path,
                }

            # Lecture et validation du JSON
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            if not content.strip():
                return {"valid": False, "error": "Empty file", "file_path": file_path}

            # Tentative de parsing JSON
            try:
                data = json.loads(content)
                return {
                    "valid": True,
                    "chunks_count": len(data.get("chunks", [])),
                    "has_title": bool(data.get("title")),
                    "file_size": len(content),
                    "file_path": file_path,
                }
            except json.JSONDecodeError as e:
                return {
                    "valid": False,
                    "error": f"Invalid JSON: {e}",
                    "content_preview": content[:200],
                    "file_path": file_path,
                }

        except Exception as e:
            return {
                "valid": False,
                "error": f"File access error: {e}",
                "file_path": file_path,
            }
