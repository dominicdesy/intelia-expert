"""
General Data Parser Plugins
High-quality parsers for CSV and Excel files with contextual chunking
"""

import pandas as pd
from typing import List, Optional, Dict, Any
import logging

from .parser_base import BaseParser, ParserCapability, Document

logger = logging.getLogger(__name__)


class GeneralCSVParser(BaseParser):
    """
    General-purpose CSV parser with intelligent contextual chunking
    
    This parser handles CSV files containing poultry production data
    by identifying column types and creating meaningful text chunks
    that preserve data relationships and context.
    """
    
    # Mapping of common poultry data column patterns
    POULTRY_COLUMN_PATTERNS = {
        'age': ['age', 'day', 'days', 'age_days', 'bird_age', 'week'],
        'weight': ['weight', 'body_weight', 'avg_weight', 'weight_kg', 'weight_g', 'bw'],
        'gain': ['gain', 'daily_gain', 'weight_gain', 'adg', 'avg_daily_gain', 'dwg'],
        'temperature': ['temperature', 'temp', 'barn_temp', 'house_temp', 'ambient_temp'],
        'feed_intake': ['feed', 'feed_intake', 'daily_feed', 'consumption', 'intake', 'fi'],
        'water': ['water', 'water_intake', 'water_consumption', 'wi'],
        'mortality': ['mortality', 'death', 'cumulative_mortality', 'daily_mortality', 'mort'],
        'fcr': ['fcr', 'feed_conversion', 'feed_conversion_ratio', 'fc'],
        'humidity': ['humidity', 'rh', 'relative_humidity', 'hum'],
        'date': ['date', 'timestamp', 'time', 'day_date'],
        'flock': ['flock', 'house', 'barn', 'batch', 'lot'],
        'breed': ['breed', 'strain', 'line', 'genetic']
    }
    
    @property
    def capability(self) -> ParserCapability:
        return ParserCapability(
            name="GeneralCSVParser",
            supported_extensions=['.csv'],
            breed_types=['Any'],
            data_types=['performance_data', 'production_records', 'monitoring_data'],
            quality_score='high',
            description='General CSV parser with contextual chunking for poultry production data',
            priority=60
        )
    
    def can_parse(self, file_path: str, content_sample: Optional[str] = None) -> float:
        """Evaluate capability to parse CSV files"""
        file_ext = file_path.lower().split('.')[-1]
        
        if file_ext != 'csv':
            return 0.0
        
        base_score = 0.6  # Base score for any CSV file
        
        # Analyze content for poultry-related data
        if content_sample:
            content_lower = content_sample.lower()
            poultry_keywords = ['weight', 'feed', 'temperature', 'day', 'age', 'fcr', 'gain', 'mortality']
            found_keywords = sum(1 for keyword in poultry_keywords if keyword in content_lower)
            # Boost score based on relevant keywords found
            keyword_score = (found_keywords / len(poultry_keywords)) * 0.4
            base_score += keyword_score
        
        return min(base_score, 1.0)
    
    def parse(self, file_path: str) -> List[Document]:
        """Parse CSV file with intelligent contextual chunking"""
        try:
            # Read CSV with error handling
            df = pd.read_csv(file_path, encoding='utf-8')
            
            # Clean the data
            df = self._clean_csv_data(df)
            
            if df.empty:
                logger.warning(f"CSV file {file_path} is empty or contains no valid data")
                return []
            
            # Identify column types for contextual processing
            column_mapping = self._identify_column_types(df)
            
            # Create contextual chunks
            chunk_texts = self._create_contextual_chunks(df, column_mapping)
            
            # Convert to Document objects
            documents = []
            for i, chunk_text in enumerate(chunk_texts):
                doc = Document(
                    page_content=chunk_text,
                    metadata={
                        **self.create_base_metadata(file_path, {
                            'chunk_id': i,
                            'data_type': 'structured_csv',
                            'total_rows': len(df),
                            'total_columns': len(df.columns),
                            'column_types': ', '.join(set(column_mapping.values())),
                            'rows_in_chunk': self._estimate_rows_in_chunk(df, len(chunk_texts), i)
                        })
                    }
                )
                documents.append(doc)
            
            logger.info(f"✅ Created {len(documents)} contextual chunks from CSV")
            return documents
            
        except Exception as e:
            logger.error(f"Error parsing CSV file {file_path}: {e}")
            return []
    
    def _clean_csv_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and prepare CSV data for processing"""
        # Remove completely empty rows
        df = df.dropna(how='all').reset_index(drop=True)
        
        # Clean column names
        df.columns = [col.strip() for col in df.columns]
        
        # Convert numeric columns where possible
        for col in df.columns:
            if df[col].dtype == 'object':
                # Try to convert to numeric, keeping non-numeric as is
                df[col] = pd.to_numeric(df[col], errors='ignore')
        
        return df
    
    def _identify_column_types(self, df: pd.DataFrame) -> Dict[str, str]:
        """Identify the semantic type of each column based on name patterns"""
        column_mapping = {}
        df_columns_lower = [col.lower().strip() for col in df.columns]
        
        for data_type, possible_names in self.POULTRY_COLUMN_PATTERNS.items():
            for col_idx, col_name in enumerate(df_columns_lower):
                # Check if any pattern matches the column name
                if any(pattern in col_name for pattern in possible_names):
                    original_col_name = df.columns[col_idx]
                    column_mapping[original_col_name] = data_type
                    break
        
        return column_mapping
    
    def _create_contextual_chunks(self, df: pd.DataFrame, column_mapping: Dict[str, str], 
                                 chunk_size: int = 7) -> List[str]:
        """Create contextual chunks that preserve data relationships"""
        chunks = []
        
        # Create header chunk with data overview
        header_chunk = self._create_header_chunk(df, column_mapping)
        chunks.append(header_chunk)
        
        # Create data chunks by grouping rows
        for start_idx in range(0, len(df), chunk_size):
            end_idx = min(start_idx + chunk_size, len(df))
            chunk_df = df.iloc[start_idx:end_idx]
            
            chunk_text = self._format_data_chunk(chunk_df, column_mapping, start_idx)
            if chunk_text.strip():
                chunks.append(chunk_text)
        
        return chunks
    
    def _create_header_chunk(self, df: pd.DataFrame, column_mapping: Dict[str, str]) -> str:
        """Create overview chunk describing the dataset"""
        lines = [
            "Poultry Production Data Overview",
            f"Dataset contains {len(df)} records with {len(df.columns)} data fields",
            ""
        ]
        
        # Describe identified data types
        if column_mapping:
            lines.append("Data Fields Identified:")
            data_types = {}
            for col, data_type in column_mapping.items():
                if data_type not in data_types:
                    data_types[data_type] = []
                data_types[data_type].append(col)
            
            for data_type, columns in data_types.items():
                lines.append(f"• {data_type.replace('_', ' ').title()}: {', '.join(columns)}")
        
        # Add data range information
        if column_mapping:
            lines.append("")
            lines.append("Data Range Summary:")
            
            age_col = self._get_column_by_type(df, column_mapping, 'age')
            if age_col is not None:
                age_range = df[age_col].dropna()
                if not age_range.empty:
                    lines.append(f"• Age range: Day {int(age_range.min())} to Day {int(age_range.max())}")
            
            weight_col = self._get_column_by_type(df, column_mapping, 'weight')
            if weight_col is not None:
                weight_range = df[weight_col].dropna()
                if not weight_range.empty:
                    lines.append(f"• Weight range: {weight_range.min():.1f} to {weight_range.max():.1f}")
        
        return "\n".join(lines)
    
    def _format_data_chunk(self, chunk_df: pd.DataFrame, column_mapping: Dict[str, str], 
                          start_idx: int) -> str:
        """Format data chunk into readable text"""
        if chunk_df.empty:
            return ""
        
        period_start = start_idx + 1
        period_end = start_idx + len(chunk_df)
        
        lines = [f"Production Data Records {period_start} to {period_end}:", ""]
        
        for idx, row in chunk_df.iterrows():
            row_description = self._format_row_description(row, column_mapping)
            if row_description:
                lines.append(row_description)
        
        return "\n".join(lines)
    
    def _format_row_description(self, row: pd.Series, column_mapping: Dict[str, str]) -> str:
        """Format a single row into descriptive text"""
        components = []
        
        # Get key identifying information
        age = self._get_value_by_type(row, column_mapping, 'age')
        flock = self._get_value_by_type(row, column_mapping, 'flock')
        date = self._get_value_by_type(row, column_mapping, 'date')
        
        # Start with identifier
        if age is not None:
            identifier = f"Day {int(age)}"
        elif date is not None:
            identifier = f"Date {date}"
        else:
            identifier = f"Record {row.name + 1}" if hasattr(row, 'name') else "Record"
        
        if flock is not None:
            identifier += f" (Flock {flock})"
        
        components.append(identifier + ":")
        
        # Add performance metrics
        metrics = []
        
        weight = self._get_value_by_type(row, column_mapping, 'weight')
        if weight is not None:
            if weight > 10:  # Assume grams if > 10
                metrics.append(f"weight {weight:.0f}g")
            else:  # Assume kg if <= 10
                metrics.append(f"weight {weight:.2f}kg")
        
        feed = self._get_value_by_type(row, column_mapping, 'feed_intake')
        if feed is not None:
            metrics.append(f"feed intake {feed:.1f}g")
        
        temp = self._get_value_by_type(row, column_mapping, 'temperature')
        if temp is not None:
            metrics.append(f"temperature {temp:.1f}°C")
        
        fcr = self._get_value_by_type(row, column_mapping, 'fcr')
        if fcr is not None:
            metrics.append(f"FCR {fcr:.2f}")
        
        mortality = self._get_value_by_type(row, column_mapping, 'mortality')
        if mortality is not None:
            if mortality < 1:  # Percentage
                metrics.append(f"mortality {mortality:.2%}")
            else:  # Count
                metrics.append(f"mortality {int(mortality)} birds")
        
        if metrics:
            components.append(", ".join(metrics))
        
        return " ".join(components)
    
    def _get_column_by_type(self, df: pd.DataFrame, column_mapping: Dict[str, str], 
                           data_type: str) -> Optional[str]:
        """Get the first column of a specific data type"""
        for col, mapped_type in column_mapping.items():
            if mapped_type == data_type and col in df.columns:
                return col
        return None
    
    def _get_value_by_type(self, row: pd.Series, column_mapping: Dict[str, str], 
                          data_type: str) -> Optional[float]:
        """Get value from row by semantic data type"""
        for col, mapped_type in column_mapping.items():
            if mapped_type == data_type and col in row and pd.notna(row[col]):
                try:
                    return float(row[col])
                except (ValueError, TypeError):
                    # Return string value for non-numeric data
                    return str(row[col])
        return None
    
    def _estimate_rows_in_chunk(self, df: pd.DataFrame, total_chunks: int, chunk_index: int) -> int:
        """Estimate number of rows represented in a specific chunk"""
        if chunk_index == 0:  # Header chunk
            return 0
        
        data_chunks = total_chunks - 1  # Subtract header chunk
        if data_chunks <= 0:
            return 0
        
        rows_per_chunk = len(df) / data_chunks
        return int(rows_per_chunk)


class GeneralExcelParser(BaseParser):
    """
    General-purpose Excel parser with multi-sheet support
    
    Handles Excel files containing structured data with intelligent
    sheet processing and contextual chunking similar to CSV parser.
    """
    
    @property
    def capability(self) -> ParserCapability:
        return ParserCapability(
            name="GeneralExcelParser",
            supported_extensions=['.xlsx', '.xls'],
            breed_types=['Any'],
            data_types=['structured_data', 'tabular_data', 'multi_sheet_data'],
            quality_score='high',
            description='General Excel parser with multi-sheet support and contextual chunking',
            priority=55
        )
    
    def can_parse(self, file_path: str, content_sample: Optional[str] = None) -> float:
        """Evaluate capability to parse Excel files"""
        file_ext = file_path.lower().split('.')[-1]
        
        if file_ext not in ['xlsx', 'xls']:
            return 0.0
        
        # Base score for Excel files
        base_score = 0.5
        
        # Analyze content for structured data indicators
        if content_sample:
            content_lower = content_sample.lower()
            # Look for tabular data indicators
            if any(indicator in content_lower for indicator in ['sheet', 'table', 'data', 'records']):
                base_score += 0.2
        
        return min(base_score, 1.0)
    
    def parse(self, file_path: str) -> List[Document]:
        """Parse Excel file with multi-sheet processing"""
        try:
            documents = []
            excel_file = pd.ExcelFile(file_path)
            
            # Create CSV parser instance for reusing logic
            csv_parser = GeneralCSVParser()
            
            for sheet_name in excel_file.sheet_names:
                logger.info(f"Processing Excel sheet: {sheet_name}")
                
                try:
                    # Read sheet data
                    df = pd.read_excel(file_path, sheet_name=sheet_name)
                    df = csv_parser._clean_csv_data(df)
                    
                    if df.empty:
                        logger.warning(f"Sheet {sheet_name} is empty, skipping")
                        continue
                    
                    # Use CSV parser logic for contextual chunking
                    column_mapping = csv_parser._identify_column_types(df)
                    chunk_texts = csv_parser._create_contextual_chunks(df, column_mapping)
                    
                    # Create documents with sheet-specific metadata
                    for i, chunk_text in enumerate(chunk_texts):
                        doc = Document(
                            page_content=chunk_text,
                            metadata={
                                **self.create_base_metadata(file_path, {
                                    'sheet_name': sheet_name,
                                    'chunk_id': i,
                                    'data_type': 'structured_excel',
                                    'total_rows': len(df),
                                    'total_columns': len(df.columns),
                                    'column_types': ', '.join(set(column_mapping.values())) if column_mapping else 'general',
                                    'sheet_index': list(excel_file.sheet_names).index(sheet_name)
                                })
                            }
                        )
                        documents.append(doc)
                        
                except Exception as e:
                    logger.error(f"Error processing sheet {sheet_name}: {e}")
                    continue
            
            logger.info(f"✅ Created {len(documents)} chunks from {len(excel_file.sheet_names)} Excel sheets")
            return documents
            
        except Exception as e:
            logger.error(f"Error parsing Excel file {file_path}: {e}")
            return []
