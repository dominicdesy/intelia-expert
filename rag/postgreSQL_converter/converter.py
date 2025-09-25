#!/usr/bin/env python3
"""
Convertisseur Excel Universel vers PostgreSQL - Données Avicoles
Traite automatiquement tous formats: Hyline, Cobb, Ross, etc.
Architecture intelligente avec détection automatique des formats
"""

import asyncio
import asyncpg
import logging
import sys
import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass
import hashlib

try:
    import openpyxl
    from openpyxl import load_workbook
except ImportError:
    print("ERREUR: openpyxl requis. Installez avec: pip install openpyxl")
    sys.exit(1)

# Configuration logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Chargement variables d'environnement depuis la racine du projet
try:
    from dotenv import load_dotenv
    
    # Chemins spécifiques pour votre structure de projet
    project_root = Path(__file__).parent.parent  # Remonte vers la racine
    env_paths = [
        project_root / '.env',                    # Racine du projet ✅
        Path(__file__).parent / '.env',           # postgreSQL_converter/
        Path.cwd() / '.env',                      # Répertoire courant
    ]
    
    env_loaded = False
    for env_path in env_paths:
        if env_path.exists():
            load_dotenv(env_path)
            logger.info(f"✅ Variables d'environnement chargées depuis: {env_path}")
            env_loaded = True
            break
    
    if not env_loaded:
        logger.warning("⚠️ Aucun fichier .env trouvé, utilisation variables système")
        logger.info(f"Chemins vérifiés: {[str(p) for p in env_paths]}")
        
except ImportError:
    logger.warning("python-dotenv non installé, utilisation variables système")

import os

# Configuration Digital Ocean PostgreSQL depuis variables d'environnement
DATABASE_CONFIG = {
    'user': os.getenv('DB_USER', 'doadmin'),
    'password': os.getenv('DB_PASSWORD'),
    'host': os.getenv('DB_HOST'),
    'port': int(os.getenv('DB_PORT', 25060)),
    'database': os.getenv('DB_NAME', 'defaultdb'),
    'ssl': os.getenv('DB_SSL', 'require')
}

# Validation des variables requises
required_vars = ['DB_PASSWORD', 'DB_HOST']
missing_vars = [var for var in required_vars if not os.getenv(var)]
if missing_vars:
    logger.error(f"❌ Variables d'environnement manquantes: {missing_vars}")
    print("Créez un fichier .env ou définissez les variables système")
    sys.exit(1)

@dataclass
class TaxonomyInfo:
    """Information taxonomique extraite du fichier"""
    company: str
    breed: str
    strain: str
    species: str  # layer/broiler
    housing_system: Optional[str] = None
    feather_color: Optional[str] = None
    sex: Optional[str] = None

@dataclass
class MetricData:
    """Données de métrique extraites"""
    sheet_name: str
    category: str
    metric_key: str
    metric_name: str
    value_text: Optional[str] = None
    value_numeric: Optional[float] = None
    unit: Optional[str] = None
    age_min: Optional[int] = None
    age_max: Optional[int] = None
    metadata: Optional[Dict] = None

class UniversalFormatDetector:
    """Détecteur intelligent de formats de fichiers avicoles"""
    
    def __init__(self):
        self.format_patterns = {
            'hyline': {
                'company_patterns': ['hy-line', 'hyline', 'ew group'],
                'breed_patterns': ['hy-line'],
                'format_indicators': ['metadata', 'value'],
                'species_indicators': {'layer': ['layer', 'laying', 'hen'], 'broiler': ['broiler', 'meat']}
            },
            'cobb': {
                'company_patterns': ['cobb', 'cobb-vantress'],
                'breed_patterns': ['cobb'],
                'format_indicators': ['week', 'age', 'performance'],
                'species_indicators': {'broiler': ['broiler', 'meat'], 'layer': ['layer']}
            },
            'ross': {
                'company_patterns': ['ross', 'aviagen'],
                'breed_patterns': ['ross'],
                'format_indicators': ['day', 'week', 'target'],
                'species_indicators': {'broiler': ['broiler', 'meat', 'ross'], 'layer': ['layer']}
            },
            'generic': {
                'company_patterns': [],
                'breed_patterns': [],
                'format_indicators': ['age', 'week', 'performance', 'data'],
                'species_indicators': {'layer': ['layer', 'egg'], 'broiler': ['broiler', 'meat']}
            }
        }
    
    def detect_format(self, workbook: openpyxl.Workbook, filename: str) -> Tuple[str, TaxonomyInfo]:
        """Détecte le format et extrait la taxonomie"""
        logger.info(f"Détection du format pour: {filename}")
        
        # Analyse du nom de fichier
        filename_lower = filename.lower()
        detected_format = 'generic'
        
        # Détection par nom de fichier
        for format_name, patterns in self.format_patterns.items():
            if format_name == 'generic':
                continue
            for pattern in patterns['company_patterns']:
                if pattern in filename_lower:
                    detected_format = format_name
                    break
        
        # Analyse des feuilles pour confirmation et extraction taxonomique
        taxonomy = self._extract_taxonomy(workbook, detected_format, filename)
        
        logger.info(f"Format détecté: {detected_format}")
        logger.info(f"Taxonomie: {taxonomy.company} - {taxonomy.breed} - {taxonomy.strain}")
        
        return detected_format, taxonomy
    
    def _extract_taxonomy(self, workbook: openpyxl.Workbook, format_type: str, filename: str) -> TaxonomyInfo:
        """Extrait la taxonomie selon le format détecté"""
        
        # Stratégies d'extraction par format
        if format_type == 'hyline':
            return self._extract_hyline_taxonomy(workbook, filename)
        elif format_type == 'cobb':
            return self._extract_cobb_taxonomy(workbook, filename)
        elif format_type == 'ross':
            return self._extract_ross_taxonomy(workbook, filename)
        else:
            return self._extract_generic_taxonomy(workbook, filename)
    
    def _extract_hyline_taxonomy(self, workbook: openpyxl.Workbook, filename: str) -> TaxonomyInfo:
        """Extraction spécifique Hyline (format metadata/value)"""
        
        # Chercher dans les premières feuilles
        for sheet_name in workbook.sheetnames[:3]:
            sheet = workbook[sheet_name]
            
            # Format Hyline: metadata/value
            if sheet['A1'].value == 'metadata' and sheet['B1'].value == 'value':
                taxonomy_data = {}
                
                for row in sheet.iter_rows(min_row=2, max_row=20):
                    if row[0].value and row[1].value:
                        key = str(row[0].value).lower().strip()
                        value = str(row[1].value).strip()
                        taxonomy_data[key] = value
                
                return TaxonomyInfo(
                    company=taxonomy_data.get('brand', 'EW Group'),
                    breed=taxonomy_data.get('breed', 'Hy-Line'),
                    strain=taxonomy_data.get('strain', self._extract_strain_from_filename(filename)),
                    species='layer' if 'layer' in taxonomy_data.get('bird_type', '') else 'broiler',
                    housing_system=taxonomy_data.get('housing_system'),
                    feather_color=taxonomy_data.get('feather_color'),
                    sex=taxonomy_data.get('sex')
                )
        
        # Fallback depuis filename
        return self._extract_generic_taxonomy(workbook, filename)
    
    def _extract_cobb_taxonomy(self, workbook: openpyxl.Workbook, filename: str) -> TaxonomyInfo:
        """Extraction spécifique Cobb"""
        
        # Logique spécifique Cobb (à adapter selon format réel)
        strain = self._extract_strain_from_filename(filename)
        
        return TaxonomyInfo(
            company='Cobb-Vantress',
            breed='Cobb',
            strain=strain,
            species='broiler',  # Cobb = principalement broilers
            housing_system=None,
            feather_color=None,
            sex=None
        )
    
    def _extract_ross_taxonomy(self, workbook: openpyxl.Workbook, filename: str) -> TaxonomyInfo:
        """Extraction spécifique Ross"""
        
        strain = self._extract_strain_from_filename(filename)
        
        return TaxonomyInfo(
            company='Aviagen',
            breed='Ross',
            strain=strain,
            species='broiler',  # Ross = principalement broilers
            housing_system=None,
            feather_color=None,
            sex=None
        )
    
    def _extract_generic_taxonomy(self, workbook: openpyxl.Workbook, filename: str) -> TaxonomyInfo:
        """Extraction générique pour formats inconnus"""
        
        # Analyse basique du filename
        strain = self._extract_strain_from_filename(filename)
        
        # Détection company/breed depuis filename
        filename_lower = filename.lower()
        company = 'Unknown'
        breed = 'Unknown'
        species = 'layer'  # default
        
        if 'hyline' in filename_lower or 'hy-line' in filename_lower:
            company, breed = 'EW Group', 'Hy-Line'
            species = 'layer'
        elif 'cobb' in filename_lower:
            company, breed = 'Cobb-Vantress', 'Cobb'
            species = 'broiler'
        elif 'ross' in filename_lower:
            company, breed = 'Aviagen', 'Ross'
            species = 'broiler'
        
        return TaxonomyInfo(
            company=company,
            breed=breed,
            strain=strain,
            species=species
        )
    
    def _extract_strain_from_filename(self, filename: str) -> str:
        """Extrait la strain du nom de fichier"""
        
        # Patterns courants
        patterns = [
            r'(brown\s+alternative?)',
            r'(white\s+alternative?)',
            r'(ross\s+\d+)',
            r'(cobb\s+\d+)',
            r'(\d+\s+fast)',
            r'(ap\s*\d+)',
        ]
        
        filename_lower = filename.lower()
        
        for pattern in patterns:
            match = re.search(pattern, filename_lower)
            if match:
                return match.group(1).title()
        
        # Fallback: utiliser le nom de fichier nettoyé
        base_name = Path(filename).stem
        return re.sub(r'[^\w\s]', ' ', base_name).title()

class UniversalDataExtractor:
    """Extracteur universel de données selon le format détecté"""
    
    def __init__(self, format_type: str):
        self.format_type = format_type
        self.category_mapping = {
            'performance': ['performance', 'prod', 'rear', 'basic'],
            'nutrition': ['nutr', 'feed', 'vitamin', 'mineral', 'protein', 'amino'],
            'environment': ['temp', 'light', 'space', 'housing'],
            'quality': ['qual', 'egg', 'water'],
            'health': ['health', 'mortality', 'disease'],
            'other': []
        }
    
    def extract_metrics(self, workbook: openpyxl.Workbook) -> List[MetricData]:
        """Extrait toutes les métriques selon le format"""
        
        all_metrics = []
        
        for sheet_name in workbook.sheetnames:
            sheet = workbook[sheet_name]
            
            # Détection du format de feuille
            if self._is_hyline_format(sheet):
                metrics = self._extract_hyline_sheet(sheet, sheet_name)
            elif self._is_tabular_format(sheet):
                metrics = self._extract_tabular_sheet(sheet, sheet_name)
            else:
                metrics = self._extract_generic_sheet(sheet, sheet_name)
            
            all_metrics.extend(metrics)
        
        logger.info(f"Total métriques extraites: {len(all_metrics)}")
        return all_metrics
    
    def _is_hyline_format(self, sheet) -> bool:
        """Détecte format Hyline metadata/value"""
        return (sheet['A1'].value == 'metadata' and 
                sheet['B1'].value == 'value')
    
    def _is_tabular_format(self, sheet) -> bool:
        """Détecte format tabulaire standard"""
        first_row = [cell.value for cell in sheet[1] if cell.value]
        return len(first_row) > 2 and any(
            keyword in str(first_row[0]).lower() 
            for keyword in ['age', 'week', 'day', 'phase']
        )
    
    def _extract_hyline_sheet(self, sheet, sheet_name: str) -> List[MetricData]:
        """Extraction format Hyline metadata/value"""
        metrics = []
        category = self._categorize_sheet(sheet_name)
        
        for row in sheet.iter_rows(min_row=2):
            if not row[0].value:
                break
                
            metric_key = str(row[0].value).strip()
            value_raw = row[1].value if row[1].value else ""
            
            # Skip métadonnées de base (déjà dans taxonomy)
            if metric_key.lower() in ['brand', 'breed', 'strain', 'type', 'bird_type', 
                                     'housing_system', 'feather_color', 'sex']:
                continue
            
            # Extraction valeur numérique si possible
            value_numeric, unit = self._parse_numeric_value(str(value_raw))
            
            # Extraction âge si présent
            age_min, age_max = self._parse_age_range(metric_key, str(value_raw))
            
            metric = MetricData(
                sheet_name=sheet_name,
                category=category,
                metric_key=metric_key,
                metric_name=self._clean_metric_name(metric_key),
                value_text=str(value_raw) if value_raw else None,
                value_numeric=value_numeric,
                unit=unit,
                age_min=age_min,
                age_max=age_max,
                metadata={'format': 'hyline_metadata_value'}
            )
            
            metrics.append(metric)
        
        return metrics
    
    def _extract_tabular_sheet(self, sheet, sheet_name: str) -> List[MetricData]:
        """Extraction format tabulaire (Cobb/Ross style)"""
        metrics = []
        category = self._categorize_sheet(sheet_name)
        
        # Récupération des en-têtes
        headers = []
        for cell in sheet[1]:
            if cell.value:
                headers.append(str(cell.value).strip())
            else:
                break
        
        # Traitement des données
        for row_idx, row in enumerate(sheet.iter_rows(min_row=2), 2):
            if not row[0].value:
                break
            
            # Première colonne = âge/période généralement
            age_value = str(row[0].value).strip()
            age_min, age_max = self._parse_age_range(age_value, age_value)
            
            # Autres colonnes = métriques
            for col_idx, cell in enumerate(row[1:], 1):
                if col_idx >= len(headers) or not cell.value:
                    continue
                
                metric_key = f"{age_value}_{headers[col_idx]}"
                value_raw = cell.value
                value_numeric, unit = self._parse_numeric_value(str(value_raw))
                
                metric = MetricData(
                    sheet_name=sheet_name,
                    category=category,
                    metric_key=metric_key,
                    metric_name=f"{headers[col_idx]} at {age_value}",
                    value_text=str(value_raw),
                    value_numeric=value_numeric,
                    unit=unit,
                    age_min=age_min,
                    age_max=age_max,
                    metadata={'format': 'tabular', 'row': row_idx, 'col': col_idx}
                )
                
                metrics.append(metric)
        
        return metrics
    
    def _extract_generic_sheet(self, sheet, sheet_name: str) -> List[MetricData]:
        """Extraction générique pour formats non reconnus"""
        metrics = []
        category = self._categorize_sheet(sheet_name)
        
        # Tentative d'extraction basique
        for row_idx, row in enumerate(sheet.iter_rows(max_row=50), 1):
            for col_idx, cell in enumerate(row):
                if cell.value and isinstance(cell.value, (int, float)):
                    
                    metric = MetricData(
                        sheet_name=sheet_name,
                        category=category,
                        metric_key=f"cell_{row_idx}_{col_idx}",
                        metric_name=f"Value at R{row_idx}C{col_idx}",
                        value_numeric=float(cell.value),
                        metadata={'format': 'generic', 'row': row_idx, 'col': col_idx}
                    )
                    
                    metrics.append(metric)
        
        return metrics
    
    def _categorize_sheet(self, sheet_name: str) -> str:
        """Catégorise une feuille selon son nom"""
        sheet_lower = sheet_name.lower()
        
        for category, keywords in self.category_mapping.items():
            if any(keyword in sheet_lower for keyword in keywords):
                return category
        
        return 'other'
    
    def _parse_numeric_value(self, value_str: str) -> Tuple[Optional[float], Optional[str]]:
        """Extrait valeur numérique et unité d'une chaîne"""
        if not value_str:
            return None, None
        
        # Regex pour nombre + unité optionnelle
        patterns = [
            r'(\d+\.?\d*)\s*(%|kg|g|cm|mm|°C|°F|hrs?|days?|weeks?|months?)',
            r'(\d+\.?\d*)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, str(value_str))
            if match:
                try:
                    value = float(match.group(1))
                    unit = match.group(2) if len(match.groups()) > 1 else None
                    return value, unit
                except ValueError:
                    continue
        
        return None, None
    
    def _parse_age_range(self, key: str, value: str) -> Tuple[Optional[int], Optional[int]]:
        """Extrait plage d'âge d'une clé ou valeur"""
        text = f"{key} {value}".lower()
        
        # Patterns pour âges
        patterns = [
            r'(\d+)-(\d+)\s*weeks?',
            r'week\s*(\d+)',
            r'(\d+)\s*weeks?',
            r'day\s*(\d+)',
            r'(\d+)-(\d+)\s*days?',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                if len(match.groups()) == 2:
                    return int(match.group(1)), int(match.group(2))
                else:
                    age = int(match.group(1))
                    return age, age
        
        return None, None
    
    def _clean_metric_name(self, metric_key: str) -> str:
        """Nettoie le nom de métrique pour affichage"""
        cleaned = re.sub(r'[_-]+', ' ', metric_key)
        cleaned = re.sub(r'\s+', ' ', cleaned)
        return cleaned.title().strip()

class PostgreSQLManager:
    """Gestionnaire de base de données PostgreSQL"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.pool = None
    
    async def initialize(self):
        """Initialise la connexion et crée les tables"""
        logger.info("Connexion à PostgreSQL...")
        
        try:
            self.pool = await asyncpg.create_pool(
                user=self.config['user'],
                password=self.config['password'],
                host=self.config['host'],
                port=self.config['port'],
                database=self.config['database'],
                ssl=self.config['ssl']
            )
            logger.info("✅ Connexion PostgreSQL établie")
            
            # Création des tables
            await self._create_tables()
            logger.info("✅ Tables créées/vérifiées")
            
        except Exception as e:
            logger.error(f"❌ Erreur connexion PostgreSQL: {e}")
            raise
    
    async def _create_tables(self):
        """Crée les tables nécessaires"""
        
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

        -- Table des documents
        CREATE TABLE IF NOT EXISTS documents (
            id SERIAL PRIMARY KEY,
            filename VARCHAR(255) NOT NULL,
            strain_id INTEGER REFERENCES strains(id),
            housing_system VARCHAR(200),
            feather_color VARCHAR(50),
            sex VARCHAR(10),
            file_hash VARCHAR(64) UNIQUE,
            metadata JSONB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(filename, file_hash)
        );

        -- Table des catégories
        CREATE TABLE IF NOT EXISTS data_categories (
            id SERIAL PRIMARY KEY,
            category_name VARCHAR(100) NOT NULL UNIQUE,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Table des métriques (cœur du système)
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
        
        -- Insertion des catégories de base
        INSERT INTO data_categories (category_name, description) 
        VALUES 
            ('performance', 'Performance and production metrics'),
            ('nutrition', 'Nutritional requirements and feed data'),
            ('environment', 'Environmental conditions and housing'),
            ('quality', 'Product quality specifications'),
            ('health', 'Health and mortality data'),
            ('other', 'Other miscellaneous data')
        ON CONFLICT (category_name) DO NOTHING;
        """
        
        async with self.pool.acquire() as conn:
            await conn.execute(create_sql)
    
    async def insert_document_data(self, taxonomy: TaxonomyInfo, metrics: List[MetricData], 
                                 filename: str, file_hash: str) -> int:
        """Insert un document complet avec toutes ses métriques"""
        
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                
                # 1. Insérer/récupérer company
                company_id = await conn.fetchval(
                    "INSERT INTO companies (company_name) VALUES ($1) ON CONFLICT (company_name) DO UPDATE SET company_name = EXCLUDED.company_name RETURNING id",
                    taxonomy.company
                )
                
                # 2. Insérer/récupérer breed
                breed_id = await conn.fetchval(
                    "INSERT INTO breeds (company_id, breed_name) VALUES ($1, $2) ON CONFLICT (company_id, breed_name) DO UPDATE SET breed_name = EXCLUDED.breed_name RETURNING id",
                    company_id, taxonomy.breed
                )
                
                # 3. Insérer/récupérer strain
                strain_id = await conn.fetchval(
                    "INSERT INTO strains (breed_id, strain_name, species) VALUES ($1, $2, $3) ON CONFLICT (breed_id, strain_name) DO UPDATE SET species = EXCLUDED.species RETURNING id",
                    breed_id, taxonomy.strain, taxonomy.species
                )
                
                # 4. Insérer document
                document_id = await conn.fetchval("""
                    INSERT INTO documents (filename, strain_id, housing_system, feather_color, sex, file_hash, metadata)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                    ON CONFLICT (filename, file_hash) DO UPDATE SET
                        strain_id = EXCLUDED.strain_id,
                        housing_system = EXCLUDED.housing_system,
                        feather_color = EXCLUDED.feather_color,
                        sex = EXCLUDED.sex,
                        metadata = EXCLUDED.metadata
                    RETURNING id
                """, filename, strain_id, taxonomy.housing_system, taxonomy.feather_color, 
                taxonomy.sex, file_hash, json.dumps({'processed_at': datetime.now().isoformat()}))
                
                # 5. Récupérer IDs des catégories
                categories = await conn.fetch("SELECT id, category_name FROM data_categories")
                category_map = {row['category_name']: row['id'] for row in categories}
                
                # 6. Supprimer anciennes métriques du document
                await conn.execute("DELETE FROM metrics WHERE document_id = $1", document_id)
                
                # 7. Insérer nouvelles métriques
                metric_records = []
                for metric in metrics:
                    category_id = category_map.get(metric.category, category_map.get('other'))
                    
                    metric_records.append((
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
                        json.dumps(metric.metadata) if metric.metadata else None
                    ))
                
                if metric_records:
                    await conn.executemany("""
                        INSERT INTO metrics (document_id, category_id, sheet_name, metric_key, metric_name,
                                           value_text, value_numeric, unit, age_min, age_max, metadata)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                    """, metric_records)
                
                logger.info(f"✅ Document inséré: {len(metric_records)} métriques")
                return document_id
    
    async def close(self):
        """Ferme la connexion"""
        if self.pool:
            await self.pool.close()

class UniversalExcelConverter:
    """Convertisseur principal universel"""
    
    def __init__(self, db_config: Dict[str, Any]):
        self.format_detector = UniversalFormatDetector()
        self.db_manager = PostgreSQLManager(db_config)
    
    async def initialize(self):
        """Initialise le convertisseur"""
        await self.db_manager.initialize()
    
    async def convert_file(self, file_path: str) -> bool:
        """Convertit un fichier Excel vers PostgreSQL"""
        
        try:
            logger.info(f"🚀 Traitement: {file_path}")
            
            # 1. Chargement du fichier
            workbook = load_workbook(file_path, read_only=True, data_only=True)
            filename = Path(file_path).name
            
            # Calcul hash du fichier
            with open(file_path, 'rb') as f:
                file_hash = hashlib.md5(f.read()).hexdigest()
            
            # 2. Détection format et extraction taxonomie
            format_type, taxonomy = self.format_detector.detect_format(workbook, filename)
            
            # 3. Extraction des données
            extractor = UniversalDataExtractor(format_type)
            metrics = extractor.extract_metrics(workbook)
            
            if not metrics:
                logger.warning("⚠️ Aucune métrique extraite")
                return False
            
            # 4. Insertion en base
            document_id = await self.db_manager.insert_document_data(
                taxonomy, metrics, filename, file_hash
            )
            
            logger.info(f"✅ Conversion réussie - Document ID: {document_id}")
            logger.info(f"📊 Stats: {len(metrics)} métriques, format: {format_type}")
            
            workbook.close()
            return True
            
        except Exception as e:
            logger.error(f"❌ Erreur conversion {file_path}: {e}")
            raise
    
    async def convert_directory(self, directory_path: str) -> int:
        """Convertit tous les fichiers Excel d'un répertoire"""
        
        directory = Path(directory_path)
        excel_files = list(directory.glob("*.xlsx")) + list(directory.glob("*.xls"))
        
        if not excel_files:
            logger.warning(f"Aucun fichier Excel trouvé dans {directory_path}")
            return 0
        
        logger.info(f"📁 {len(excel_files)} fichiers trouvés")
        
        success_count = 0
        for file_path in excel_files:
            try:
                if await self.convert_file(str(file_path)):
                    success_count += 1
            except Exception as e:
                logger.error(f"Échec {file_path}: {e}")
        
        logger.info(f"🏆 Conversion terminée: {success_count}/{len(excel_files)} réussies")
        return success_count
    
    async def close(self):
        """Ferme le convertisseur"""
        await self.db_manager.close()

async def main():
    """Fonction principale"""
    
    # Gestion des arguments
    if len(sys.argv) >= 2 and sys.argv[1] == '--test-connection':
        logger.info("🧪 Test de connexion à la base de données...")
        converter = UniversalExcelConverter(DATABASE_CONFIG)
        try:
            await converter.initialize()
            logger.info("✅ Connexion réussie ! Configuration OK")
            await converter.close()
            return
        except Exception as e:
            logger.error(f"❌ Échec connexion: {e}")
            sys.exit(1)
    
    if len(sys.argv) < 2:
        print("Usage: python converter.py <fichier_excel_ou_dossier>")
        print("Exemples:")
        print("  python converter.py ../documents/PerformanceMetrics\\ \\(XLSX\\)/Hyline\\ Brown\\ ALT\\ STD\\ ENG.xlsx")
        print("  python converter.py ../documents/PerformanceMetrics\\ \\(XLSX\\)/")
        print("  python converter.py --test-connection    # Test la connexion DB")
        print()
        print("Fichiers disponibles dans votre projet:")
        print("  - Hyline Brown ALT STD ENG.xlsx")
        print("  - Futurs fichiers Cobb, Ross, etc.")
        sys.exit(1)
    
    input_path = sys.argv[1]
    
    # Initialisation convertisseur
    converter = UniversalExcelConverter(DATABASE_CONFIG)
    
    try:
        await converter.initialize()
        
        # Conversion selon type d'entrée
        if Path(input_path).is_file():
            await converter.convert_file(input_path)
        elif Path(input_path).is_dir():
            await converter.convert_directory(input_path)
        else:
            logger.error(f"❌ Chemin invalide: {input_path}")
            sys.exit(1)
        
    except Exception as e:
        logger.error(f"❌ Erreur fatale: {e}")
        sys.exit(1)
    finally:
        await converter.close()

if __name__ == "__main__":
    asyncio.run(main())