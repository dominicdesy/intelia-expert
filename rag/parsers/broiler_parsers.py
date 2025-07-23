"""
Broiler Specialized Parser Plugins - Fixed Excel Handling
Clean code compliant version with proper error handling
"""

import pandas as pd
import numpy as np
import re
from typing import List, Optional, Dict, Any
import logging
from pathlib import Path

from .parser_base import BaseParser, ParserCapability, Document

logger = logging.getLogger(__name__)


class BroilerPerformanceParser(BaseParser):
    """
    Universal parser for broiler performance standard files.
    Handles Excel files containing weekly performance data with automatic
    breed detection and optimal chunking strategy.
    """
    
    # Supported breed patterns for automatic detection
    SUPPORTED_BREEDS = {
        'ross_308': ['ross 308', 'ross308', 'ross-308'],
        'ross_708': ['ross 708', 'ross708', 'ross-708'],
        'cobb_500': ['cobb 500', 'cobb500', 'cobb-500'],
        'cobb_700': ['cobb 700', 'cobb700', 'cobb-700'],
        'aviagen_plus': ['aviagen plus', 'aviagen+', 'aviagen-plus'],
        'hubbard_flex': ['hubbard flex', 'hubbard-flex'],
        'generic_broiler': ['broiler', 'chicken', 'poultry']
    }
    
    # Universal column mapping with breed-specific variants
    COLUMN_MAPPINGS = {
        'universal': {
            'Day': 'age',
            'Age': 'age',
            'Days': 'age',
            'Body weight': 'weight',
            'Live weight': 'weight',
            'Weight': 'weight',
            'Daily gain': 'daily_gain',
            'Daily weight gain': 'daily_gain',
            'Weight gain': 'daily_gain',
            'FCR': 'fcr',
            'Feed conversion': 'fcr',
            'Feed efficiency': 'fcr',
            'Daily feed intake': 'daily_intake',
            'Feed intake': 'daily_intake',
            'Feed consumption': 'daily_intake'
        }
    }
    
    @property
    def capability(self) -> ParserCapability:
        return ParserCapability(
            name="BroilerPerformanceParser",
            supported_extensions=['.xlsx', '.xls'],
            breed_types=['Ross 308', 'Cobb 500', 'Aviagen Plus', 'Hubbard Flex', 'Generic Broiler'],
            data_types=['performance_standards', 'growth_targets', 'breed_standards'],
            quality_score='optimal',
            description='Universal broiler performance parser with automatic breed detection',
            priority=90
        )
    
    def can_parse(self, file_path: str, content_sample: Optional[str] = None) -> float:
        """Evaluate capability to parse broiler performance files."""
        score = 0.0
        file_name = file_path.lower()
        file_ext = file_path.lower().split('.')[-1]
        
        # File extension check
        if file_ext in ['xlsx', 'xls']:
            score += 0.3
        
        # Filename pattern matching
        performance_indicators = ['performance', 'growth', 'weight', 'fcr', 'gain']
        breed_indicators = ['ross', 'cobb', 'aviagen', 'hubbard', 'broiler']
        
        for indicator in performance_indicators:
            if indicator in file_name:
                score += 0.2
                break
        
        for indicator in breed_indicators:
            if indicator in file_name:
                score += 0.3
                break
        
        return min(score, 1.0)
    
    def parse(self, file_path: str) -> List[Document]:
        """Parse broiler performance Excel file."""
        try:
            # Read Excel file with all sheets
            logger.info(f"Reading Excel file: {file_path}")
            excel_data = pd.read_excel(file_path, sheet_name=None, header=None)
            
            documents = []
            
            for sheet_name, df in excel_data.items():
                logger.info(f"Processing broiler performance sheet: {sheet_name}")
                
                try:
                    # Extract performance data from sheet
                    performance_data = self._extract_performance_data(df, sheet_name, file_path)
                    
                    if performance_data:
                        # Create document from performance data
                        doc = Document(
                            page_content=performance_data['content'],
                            metadata=self.create_base_metadata(file_path, {
                                'sheet_name': sheet_name,
                                'breed': performance_data.get('breed', 'Unknown'),
                                'data_type': 'performance_data',
                                'extraction_method': 'broiler_performance_parser',
                                'performance_metrics': performance_data.get('metrics', [])
                            })
                        )
                        documents.append(doc)
                
                except Exception as e:
                    logger.error(f"Error extracting performance structure: {e}")
                    # Try simple extraction as fallback
                    try:
                        simple_content = self._simple_excel_extraction(df, sheet_name)
                        if simple_content:
                            doc = Document(
                                page_content=simple_content,
                                metadata=self.create_base_metadata(file_path, {
                                    'sheet_name': sheet_name,
                                    'data_type': 'excel_data',
                                    'extraction_method': 'simple_excel_parser'
                                })
                            )
                            documents.append(doc)
                    except Exception as fallback_error:
                        logger.warning(f"Fallback extraction also failed for sheet {sheet_name}: {fallback_error}")
                        continue
            
            logger.info(f"Created {len(documents)} chunks from broiler performance file")
            return documents
            
        except Exception as e:
            logger.error(f"Error parsing broiler performance file {file_path}: {e}")
            return []
    
    def _extract_performance_data(self, df: pd.DataFrame, sheet_name: str, file_path: str) -> Optional[Dict[str, Any]]:
        """Extract structured performance data from DataFrame."""
        try:
            # Convert DataFrame to string representation for analysis
            df_str = df.to_string(na_rep='', index=False, header=False)
            
            # Check if DataFrame has meaningful data
            if df.empty or df.shape[0] < 2:
                return None
            
            # Detect breed from sheet name or file path
            breed = self._detect_breed(sheet_name + " " + str(file_path))
            
            # Look for numeric data patterns
            numeric_columns = []
            for col in df.columns:
                try:
                    numeric_count = pd.to_numeric(df[col], errors='coerce').notna().sum()
                    if numeric_count > 0:
                        numeric_columns.append(col)
                except:
                    pass
            
            # Extract performance metrics
            metrics = []
            performance_keywords = ['weight', 'gain', 'fcr', 'feed', 'mortality', 'age', 'day']
            
            for keyword in performance_keywords:
                if keyword in df_str.lower():
                    metrics.append(keyword)
            
            # Create structured content
            content_parts = [
                f"Broiler Performance Data - {sheet_name}",
                f"Breed: {breed}",
                f"Data dimensions: {df.shape[0]} rows × {df.shape[1]} columns"
            ]
            
            if metrics:
                content_parts.append(f"Performance metrics detected: {', '.join(metrics)}")
            
            # Add sample data if available
            if not df.empty:
                content_parts.append("\nData sample:")
                # Get first few rows as text
                sample_data = df.head(5).to_string(na_rep='', index=False)
                content_parts.append(sample_data)
            
            return {
                'content': '\n'.join(content_parts),
                'breed': breed,
                'metrics': metrics,
                'sheet_name': sheet_name
            }
            
        except Exception as e:
            logger.error(f"Error in performance data extraction: {e}")
            return None
    
    def _simple_excel_extraction(self, df: pd.DataFrame, sheet_name: str) -> Optional[str]:
        """Simple fallback extraction for Excel data."""
        try:
            if df.empty:
                return None
            
            # Convert to string representation
            content_parts = [
                f"Excel Data - {sheet_name}",
                f"Dimensions: {df.shape[0]} rows × {df.shape[1]} columns",
                "",
                "Data content:"
            ]
            
            # Add data as string
            df_str = df.to_string(na_rep='', index=False, header=True, max_rows=20)
            content_parts.append(df_str)
            
            if df.shape[0] > 20:
                content_parts.append(f"... and {df.shape[0] - 20} more rows")
            
            return '\n'.join(content_parts)
            
        except Exception as e:
            logger.warning(f"Simple extraction failed: {e}")
            return None
    
    def _detect_breed(self, text: str) -> str:
        """Detect broiler breed from text."""
        text_lower = text.lower()
        
        for breed_key, patterns in self.SUPPORTED_BREEDS.items():
            for pattern in patterns:
                if pattern in text_lower:
                    return breed_key.replace('_', ' ').title()
        
        return "Generic Broiler"


class BroilerTemperatureParser(BaseParser):
    """
    Universal parser for broiler temperature management files.
    Handles Excel files with temperature-humidity matrices for all broiler breeds.
    """
    
    @property
    def capability(self) -> ParserCapability:
        return ParserCapability(
            name="BroilerTemperatureParser",
            supported_extensions=['.xlsx', '.xls'],
            breed_types=['Ross 308', 'Cobb 500', 'Aviagen Plus', 'Hubbard Flex', 'Generic Broiler'],
            data_types=['temperature_guidelines', 'environmental_control', 'climate_management'],
            quality_score='optimal',
            description='Universal broiler temperature parser with breed-specific optimization',
            priority=85
        )
    
    def can_parse(self, file_path: str, content_sample: Optional[str] = None) -> float:
        """Evaluate capability to parse broiler temperature files."""
        score = 0.0
        file_name = file_path.lower()
        file_ext = file_path.lower().split('.')[-1]
        
        # File extension check
        if file_ext in ['xlsx', 'xls']:
            score += 0.3
        
        # Temperature-specific indicators
        temp_indicators = ['temperature', 'temp', 'climate', 'environment', 'heating', 'cooling']
        breed_indicators = ['ross', 'cobb', 'aviagen', 'hubbard', 'broiler']
        
        for indicator in temp_indicators:
            if indicator in file_name:
                score += 0.4
                break
        
        for indicator in breed_indicators:
            if indicator in file_name:
                score += 0.3
                break
        
        return min(score, 1.0)
    
    def parse(self, file_path: str) -> List[Document]:
        """Parse broiler temperature Excel file."""
        try:
            # Read Excel file with all sheets
            logger.info(f"Reading temperature Excel file: {file_path}")
            excel_data = pd.read_excel(file_path, sheet_name=None, header=None)
            
            documents = []
            
            for sheet_name, df in excel_data.items():
                logger.info(f"Processing broiler temperature sheet: {sheet_name}")
                
                try:
                    # Extract temperature data from sheet
                    temp_data = self._extract_temperature_data(df, sheet_name, file_path)
                    
                    if temp_data:
                        # Create document from temperature data
                        doc = Document(
                            page_content=temp_data['content'],
                            metadata=self.create_base_metadata(file_path, {
                                'sheet_name': sheet_name,
                                'breed': temp_data.get('breed', 'Unknown'),
                                'data_type': 'temperature_data',
                                'extraction_method': 'broiler_temperature_parser',
                                'temperature_ranges': temp_data.get('temp_ranges', [])
                            })
                        )
                        documents.append(doc)
                
                except Exception as e:
                    logger.error(f"Error extracting temperature structure: {e}")
                    # Try simple extraction as fallback
                    try:
                        simple_content = self._simple_excel_extraction(df, sheet_name)
                        if simple_content:
                            doc = Document(
                                page_content=simple_content,
                                metadata=self.create_base_metadata(file_path, {
                                    'sheet_name': sheet_name,
                                    'data_type': 'excel_data',
                                    'extraction_method': 'simple_excel_parser'
                                })
                            )
                            documents.append(doc)
                    except Exception as fallback_error:
                        logger.warning(f"Fallback extraction also failed for sheet {sheet_name}: {fallback_error}")
                        continue
            
            logger.info(f"Created {len(documents)} chunks from broiler temperature file")
            return documents
            
        except Exception as e:
            logger.error(f"Error parsing broiler temperature file {file_path}: {e}")
            return []
    
    def _extract_temperature_data(self, df: pd.DataFrame, sheet_name: str, file_path: str) -> Optional[Dict[str, Any]]:
        """Extract structured temperature data from DataFrame."""
        try:
            # Convert DataFrame to string representation for analysis
            df_str = df.to_string(na_rep='', index=False, header=False)
            
            # Check if DataFrame has meaningful data
            if df.empty or df.shape[0] < 2:
                return None
            
            # Detect breed from sheet name or file path
            breed = self._detect_breed(sheet_name + " " + str(file_path))
            
            # Look for temperature-related patterns
            temp_ranges = []
            temp_keywords = ['temperature', 'temp', '°c', 'celsius', 'heating', 'cooling']
            
            for keyword in temp_keywords:
                if keyword in df_str.lower():
                    temp_ranges.append(keyword)
            
            # Create structured content
            content_parts = [
                f"Broiler Temperature Management - {sheet_name}",
                f"Breed: {breed}",
                f"Data dimensions: {df.shape[0]} rows × {df.shape[1]} columns"
            ]
            
            if temp_ranges:
                content_parts.append(f"Temperature indicators detected: {', '.join(temp_ranges)}")
            
            # Add sample data if available
            if not df.empty:
                content_parts.append("\nTemperature data sample:")
                # Get first few rows as text
                sample_data = df.head(5).to_string(na_rep='', index=False)
                content_parts.append(sample_data)
            
            return {
                'content': '\n'.join(content_parts),
                'breed': breed,
                'temp_ranges': temp_ranges,
                'sheet_name': sheet_name
            }
            
        except Exception as e:
            logger.error(f"Error in temperature data extraction: {e}")
            return None
    
    def _simple_excel_extraction(self, df: pd.DataFrame, sheet_name: str) -> Optional[str]:
        """Simple fallback extraction for Excel data."""
        try:
            if df.empty:
                return None
            
            # Convert to string representation
            content_parts = [
                f"Excel Data - {sheet_name}",
                f"Dimensions: {df.shape[0]} rows × {df.shape[1]} columns",
                "",
                "Data content:"
            ]
            
            # Add data as string
            df_str = df.to_string(na_rep='', index=False, header=True, max_rows=20)
            content_parts.append(df_str)
            
            if df.shape[0] > 20:
                content_parts.append(f"... and {df.shape[0] - 20} more rows")
            
            return '\n'.join(content_parts)
            
        except Exception as e:
            logger.warning(f"Simple extraction failed: {e}")
            return None
    
    def _detect_breed(self, text: str) -> str:
        """Detect broiler breed from text."""
        text_lower = text.lower()
        
        breed_patterns = {
            'ross_308': ['ross 308', 'ross308', 'ross-308'],
            'cobb_500': ['cobb 500', 'cobb500', 'cobb-500'],
            'aviagen_plus': ['aviagen plus', 'aviagen+'],
            'hubbard_flex': ['hubbard flex', 'hubbard-flex']
        }
        
        for breed_key, patterns in breed_patterns.items():
            for pattern in patterns:
                if pattern in text_lower:
                    return breed_key.replace('_', ' ').title()
        
        return "Generic Broiler"