"""
Client LLM simplifié avec chargement automatique des clés
"""

import os
import json
import logging


class LLMClient:
    """Client LLM unifié avec support multi-provider"""

    def __init__(self, provider="openai", api_key=None, model="gpt-4"):
        self.provider = provider.lower()
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
            from pathlib import Path

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
        """Complète un prompt avec le LLM"""
        if self.provider == "mock":
            return self._mock_response(prompt)

        elif self.provider == "openai":
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=0.1,
            )
            return response.choices[0].message.content

        elif self.provider == "anthropic":
            response = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=0.1,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text

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
