# -*- coding: utf-8 -*-
"""
Configuration for data ingestion pipeline
Version: 1.4.1
Last modified: 2025-10-26
"""
"""
Configuration for data ingestion pipeline
"""

from typing import Dict, List
from dataclasses import dataclass
import os


@dataclass
class FetcherConfig:
    """Configuration for a data source fetcher"""
    name: str
    enabled: bool
    rate_limit: int  # requests per second
    max_results_per_topic: int
    timeout: int  # seconds
    retry_attempts: int
    api_key: str = None


@dataclass
class ProcessorConfig:
    """Configuration for data processors"""
    min_content_length: int = 200  # Minimum abstract length
    min_citations: int = 0  # Minimum citations (0 = no filter)
    min_year: int = 2015  # Only papers from this year onwards
    languages: List[str] = None  # Accepted languages

    def __post_init__(self):
        if self.languages is None:
            self.languages = ["en", "fr", "es"]


@dataclass
class WeaviateConfig:
    """Configuration for Weaviate loader"""
    url: str
    api_key: str = None
    class_name: str = "Document"
    batch_size: int = 100
    timeout: int = 30


class IngestionConfig:
    """Main configuration for ingestion pipeline"""

    # Data source configurations
    SEMANTIC_SCHOLAR = FetcherConfig(
        name="semantic_scholar",
        enabled=True,
        rate_limit=10,  # 10 requests/sec (conservative)
        max_results_per_topic=500,
        timeout=30,
        retry_attempts=3
    )

    PUBMED = FetcherConfig(
        name="pubmed",
        enabled=True,
        rate_limit=3,  # 3 req/sec without API key, 10 with key
        max_results_per_topic=300,
        timeout=30,
        retry_attempts=3,
        api_key=os.getenv("PUBMED_API_KEY")  # Optional but recommended
    )

    EUROPE_PMC = FetcherConfig(
        name="europe_pmc",
        enabled=True,
        rate_limit=5,
        max_results_per_topic=300,
        timeout=30,
        retry_attempts=3
    )

    FAO = FetcherConfig(
        name="fao",
        enabled=True,
        rate_limit=1,  # Conservative for scraping
        max_results_per_topic=50,
        timeout=60,
        retry_attempts=5
    )

    # Processing configuration
    PROCESSOR = ProcessorConfig(
        min_content_length=200,
        min_citations=5,  # At least 5 citations for quality
        min_year=2015,
        languages=["en", "fr", "es"]
    )

    # Weaviate configuration
    WEAVIATE = WeaviateConfig(
        url=os.getenv("WEAVIATE_URL", "http://localhost:8080"),
        api_key=os.getenv("WEAVIATE_API_KEY"),
        class_name="Document",
        batch_size=100,
        timeout=30
    )

    # Topics to collect
    TOPICS = [
        # Nutrition
        "broiler nutrition",
        "layer nutrition",
        "poultry feed formulation",
        "amino acids requirements poultry",
        "energy requirements broiler",
        "vitamin requirements poultry",
        "mineral requirements poultry",
        "feed additives poultry",

        # Health & Diseases
        "Newcastle disease",
        "infectious bronchitis",
        "Gumboro disease",
        "coccidiosis poultry",
        "Marek's disease",
        "avian influenza",
        "necrotic enteritis",
        "colibacillosis poultry",
        "mycotoxins poultry",

        # Management
        "broiler management",
        "layer management",
        "poultry biosecurity",
        "heat stress poultry",
        "ventilation poultry house",
        "lighting program broiler",
        "water quality poultry",
        "litter management poultry",

        # Performance
        "feed conversion ratio",
        "broiler growth performance",
        "egg production optimization",
        "uniformity flock management",
        "mortality reduction poultry",

        # Genetics
        "Ross 308 performance",
        "Cobb 500 management",
        "broiler breeding programs",
        "egg production genetics",

        # Welfare & Environment
        "animal welfare poultry",
        "environmental impact poultry",
        "carbon footprint poultry production",
        "ammonia emissions poultry",

        # Economics
        "poultry production economics",
        "feed cost optimization",
        "profitability broiler production"
    ]

    # Storage paths
    CACHE_DIR = "data_ingestion/cache"
    LOGS_DIR = "data_ingestion/logs"
    PROGRESS_FILE = "data_ingestion/progress.json"

    # Quality thresholds
    DEDUPLICATION_SIMILARITY_THRESHOLD = 0.85  # 85% similarity = duplicate


# Singleton instance
config = IngestionConfig()
