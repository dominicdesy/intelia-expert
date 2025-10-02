#!/usr/bin/env python3
"""
Gestionnaire de base de données PostgreSQL
"""

import json
import logging
from typing import Dict, Any, List
from datetime import datetime

import asyncpg

from models import TaxonomyInfo, MetricData

logger = logging.getLogger(__name__)


class PostgreSQLManager:
    """Gestionnaire PostgreSQL avec support intents.json"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.pool = None

    async def initialize(self):
        """Initialise la connexion et crée les tables"""
        logger.info("Connexion à PostgreSQL...")

        try:
            self.pool = await asyncpg.create_pool(
                user=self.config["user"],
                password=self.config["password"],
                host=self.config["host"],
                port=self.config["port"],
                database=self.config["database"],
                ssl=self.config["ssl"],
            )
            logger.info("Connexion PostgreSQL établie")

            await self._create_tables()
            logger.info("Tables créées/vérifiées")

        except Exception as e:
            logger.error(f"Erreur connexion PostgreSQL: {e}")
            raise

    async def _create_tables(self):
        """Crée les tables avec support multi-types de données"""

        create_sql = """
        -- Table des compagnies
        CREATE TABLE IF NOT EXISTS companies (
            id SERIAL PRIMARY KEY,
            company_name VARCHAR(100) NOT NULL UNIQUE,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Table des breeds
        CREATE TABLE IF NOT EXISTS breeds (
            id SERIAL PRIMARY KEY,
            company_id INTEGER REFERENCES companies(id),
            breed_name VARCHAR(100) NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(company_id, breed_name)
        );

        -- Table des strains
        CREATE TABLE IF NOT EXISTS strains (
            id SERIAL PRIMARY KEY,
            breed_id INTEGER REFERENCES breeds(id),
            strain_name VARCHAR(100) NOT NULL,
            species VARCHAR(50) NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(breed_id, strain_name)
        );

        -- Table des documents avec support data_type
        CREATE TABLE IF NOT EXISTS documents (
            id SERIAL PRIMARY KEY,
            filename VARCHAR(255) NOT NULL,
            strain_id INTEGER REFERENCES strains(id),
            housing_system VARCHAR(200),
            feather_color VARCHAR(50),
            sex VARCHAR(10),
            data_type VARCHAR(50),
            file_hash VARCHAR(64) UNIQUE,
            metadata JSONB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(filename, file_hash)
        );

        -- Table des catégories étendues
        CREATE TABLE IF NOT EXISTS data_categories (
            id SERIAL PRIMARY KEY,
            category_name VARCHAR(100) NOT NULL UNIQUE,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Table des métriques
        CREATE TABLE IF NOT EXISTS metrics (
            id SERIAL PRIMARY KEY,
            document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
            category_id INTEGER REFERENCES data_categories(id),
            sheet_name VARCHAR(100) NOT NULL,
            metric_key VARCHAR(200) NOT NULL,
            metric_name VARCHAR(200),
            value_text TEXT,
            value_numeric DECIMAL(15,6),
            unit VARCHAR(50),
            age_min INTEGER,
            age_max INTEGER,
            metadata JSONB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Index pour performance
        CREATE INDEX IF NOT EXISTS idx_metrics_document_sheet ON metrics(document_id, sheet_name);
        CREATE INDEX IF NOT EXISTS idx_metrics_category ON metrics(category_id);
        CREATE INDEX IF NOT EXISTS idx_metrics_age ON metrics(age_min, age_max);
        CREATE INDEX IF NOT EXISTS idx_metrics_key ON metrics(metric_key);
        CREATE INDEX IF NOT EXISTS idx_metrics_name ON metrics(metric_name);
        CREATE INDEX IF NOT EXISTS idx_documents_data_type ON documents(data_type);
        
        -- Index GIN pour recherche dans métadonnées JSONB
        CREATE INDEX IF NOT EXISTS idx_documents_metadata_gin ON documents USING GIN (metadata);
        
        -- Insertion des catégories étendues
        INSERT INTO data_categories (category_name, description) 
        VALUES 
            ('performance', 'Performance and production metrics'),
            ('nutrition', 'Nutritional requirements and feed data'),
            ('pharmaceutical', 'Pharmaceutical and veterinary data'),
            ('carcass', 'Carcass yield and processing data'),
            ('environment', 'Environmental conditions and housing'),
            ('health', 'Health and mortality data'),
            ('economics', 'Economic and cost data'),
            ('other', 'Other miscellaneous data')
        ON CONFLICT (category_name) DO NOTHING;
        """

        async with self.pool.acquire() as conn:
            await conn.execute(create_sql)

    async def insert_document_data(
        self,
        taxonomy: TaxonomyInfo,
        metrics: List[MetricData],
        filename: str,
        file_hash: str,
    ) -> int:
        """Insert un document avec support data_type et logging amélioré"""

        async with self.pool.acquire() as conn:
            async with conn.transaction():

                # Insertion company/breed/strain
                company_id = await conn.fetchval(
                    "INSERT INTO companies (company_name) VALUES ($1) ON CONFLICT (company_name) DO UPDATE SET company_name = EXCLUDED.company_name RETURNING id",
                    taxonomy.company,
                )

                breed_id = await conn.fetchval(
                    "INSERT INTO breeds (company_id, breed_name) VALUES ($1, $2) ON CONFLICT (company_id, breed_name) DO UPDATE SET breed_name = EXCLUDED.breed_name RETURNING id",
                    company_id,
                    taxonomy.breed,
                )

                strain_id = await conn.fetchval(
                    "INSERT INTO strains (breed_id, strain_name, species) VALUES ($1, $2, $3) ON CONFLICT (breed_id, strain_name) DO UPDATE SET species = EXCLUDED.species RETURNING id",
                    breed_id,
                    taxonomy.strain,
                    taxonomy.species,
                )

                # Construire métadonnées complètes
                full_metadata = {
                    "processed_at": datetime.now().isoformat(),
                    "data_type": taxonomy.data_type,
                    "intents_config_version": "v1.2",
                }

                # Ajouter métadonnées de structure si disponibles
                if hasattr(self, "_current_table_metadata"):
                    table_meta = self._current_table_metadata
                    if "descriptive_metadata" in table_meta:
                        full_metadata.update(table_meta["descriptive_metadata"])

                    full_metadata["table_structure"] = {
                        k: v
                        for k, v in table_meta.items()
                        if k not in ["descriptive_metadata"]
                    }

                document_id = await conn.fetchval(
                    """
                    INSERT INTO documents (filename, strain_id, housing_system, feather_color, sex, data_type, file_hash, metadata)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    ON CONFLICT (filename, file_hash) DO UPDATE SET
                        strain_id = EXCLUDED.strain_id,
                        housing_system = EXCLUDED.housing_system,
                        feather_color = EXCLUDED.feather_color,
                        sex = EXCLUDED.sex,
                        data_type = EXCLUDED.data_type,
                        metadata = EXCLUDED.metadata
                    RETURNING id
                """,
                    filename,
                    strain_id,
                    taxonomy.housing_system,
                    taxonomy.feather_color,
                    taxonomy.sex,
                    taxonomy.data_type,
                    file_hash,
                    json.dumps(full_metadata),
                )

                # Insertion métriques
                categories = await conn.fetch(
                    "SELECT id, category_name FROM data_categories"
                )
                category_map = {row["category_name"]: row["id"] for row in categories}

                await conn.execute(
                    "DELETE FROM metrics WHERE document_id = $1", document_id
                )

                metric_records = []
                for metric in metrics:
                    category_id = category_map.get(
                        metric.category, category_map.get("other")
                    )

                    metric_records.append(
                        (
                            document_id,
                            category_id,
                            metric.sheet_name,
                            metric.metric_key,
                            metric.metric_name,
                            metric.value_text,
                            metric.value_numeric,
                            metric.unit,
                            metric.age_min,
                            metric.age_max,
                            json.dumps(metric.metadata) if metric.metadata else None,
                        )
                    )

                if metric_records:
                    await conn.executemany(
                        """
                        INSERT INTO metrics (document_id, category_id, sheet_name, metric_key, metric_name,
                                           value_text, value_numeric, unit, age_min, age_max, metadata)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                    """,
                        metric_records,
                    )

                logger.info("Document inséré avec succès:")
                logger.info(f"  - ID: {document_id}")
                logger.info(f"  - Métriques: {len(metric_records)}")
                logger.info(f"  - Type: {taxonomy.data_type}")
                logger.info(f"  - Lignée: {taxonomy.strain}")

                return document_id

    async def close(self):
        if self.pool:
            await self.pool.close()
