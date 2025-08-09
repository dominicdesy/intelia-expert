"""
Table Parser Plugins - Advanced Data Extraction
Specialized parsers for extracting and structuring tabular data from documents
"""

import pandas as pd
import re
from typing import List, Optional, Dict, Any
import logging

from .parser_base import BaseParser, ParserCapability, Document

logger = logging.getLogger(__name__)


class PerformanceTableParser(BaseParser):
    """
    Advanced parser for poultry performance tables
    
    Extracts structured performance data from tables containing:
    - Weekly performance metrics (age, weight, feed intake, mortality)
    - Production data (egg production, feed conversion, etc.)
    - Nutritional specifications
    """
    
    # Performance table indicators
    PERFORMANCE_INDICATORS = {
        'weekly_performance': [
            'age', 'weeks', 'body weight', 'feed intake', 'mortality',
            'water intake', 'cumulative', 'uniformity'
        ],
        'production_data': [
            'hen-day', 'egg production', '%', 'feed conversion',
            'egg weight', 'hen-housed', 'livability'
        ],
        'nutritional_specs': [
            'protein', 'energy', 'lysine', 'methionine', 'calcium',
            'phosphorus', 'metabolizable energy', 'amino acids'
        ]
    }
    
    @property
    def capability(self) -> ParserCapability:
        return ParserCapability(
            name="PerformanceTableParser",
            supported_extensions=['.pdf', '.xlsx', '.xls'],
            breed_types=['Hy-Line Brown', 'Ross 308', 'Cobb 500', 'Generic'],
            data_types=['performance_tables', 'production_data', 'nutritional_specs'],
            quality_score='optimal',
            description='Advanced parser for poultry performance tables with structured extraction',
            priority=95
        )
    
    def can_parse(self, file_path: str, content_sample: Optional[str] = None) -> float:
        """Evaluate capability to parse performance tables"""
        score = 0.0
        
        # File type check
        file_ext = file_path.lower().split('.')[-1]
        if file_ext in ['pdf', 'xlsx', 'xls']:
            score += 0.3
        
        if content_sample:
            content_lower = content_sample.lower()
            
            # Check for performance table indicators
            table_score = 0
            for category, indicators in self.PERFORMANCE_INDICATORS.items():
                found_indicators = sum(1 for indicator in indicators 
                                     if indicator in content_lower)
                if found_indicators >= 3:  # At least 3 indicators per category
                    table_score += 0.25
            
            score += min(table_score, 0.6)
            
            # Check for breed indicators
            breed_indicators = ['hy-line', 'hyline', 'ross', 'cobb', 'broiler', 'layer']
            if any(breed in content_lower for breed in breed_indicators):
                score += 0.1
        
        return min(score, 1.0)
    
    def parse(self, file_path: str) -> List[Document]:
        """Parse performance tables with structured extraction"""
        try:
            # Detect file type and use appropriate extraction method
            file_ext = file_path.lower().split('.')[-1]
            
            if file_ext == 'pdf':
                return self._parse_pdf_tables(file_path)
            elif file_ext in ['xlsx', 'xls']:
                return self._parse_excel_tables(file_path)
            else:
                logger.warning(f"Unsupported file type for table parsing: {file_ext}")
                return []
                
        except Exception as e:
            logger.error(f"Error parsing performance tables from {file_path}: {e}")
            return []
    
    def _parse_pdf_tables(self, file_path: str) -> List[Document]:
        """Extract tables from PDF using text analysis"""
        try:
            # Use PDF loader to get content
            from langchain_community.document_loaders import PyPDFLoader
            loader = PyPDFLoader(file_path)
            pdf_documents = loader.load()
            
            documents = []
            for page_num, doc in enumerate(pdf_documents):
                content = doc.page_content
                
                # Extract tables from text content
                table_sections = self._extract_table_sections(content)
                
                for i, table_section in enumerate(table_sections):
                    # Create structured document from table
                    structured_doc = self._create_structured_document(
                        table_section, file_path, page_num, i
                    )
                    if structured_doc:
                        documents.append(structured_doc)
            
            logger.info(f"Extracted {len(documents)} table sections from PDF")
            return documents
            
        except Exception as e:
            logger.error(f"Error parsing PDF tables: {e}")
            return []
    
    def _parse_excel_tables(self, file_path: str) -> List[Document]:
        """Extract structured data from Excel files"""
        try:
            documents = []
            excel_file = pd.ExcelFile(file_path)
            
            for sheet_name in excel_file.sheet_names:
                logger.info(f"Processing Excel sheet: {sheet_name}")
                
                try:
                    df = pd.read_excel(file_path, sheet_name=sheet_name)
                    
                    # Analyze and structure the data
                    structured_content = self._analyze_excel_structure(df, sheet_name)
                    
                    if structured_content:
                        doc = Document(
                            page_content=structured_content['content'],
                            metadata=self.create_base_metadata(file_path, {
                                'sheet_name': sheet_name,
                                'table_type': structured_content['table_type'],
                                'data_structure': structured_content['structure'],
                                'metrics_detected': structured_content['metrics'],
                                'breed_detected': structured_content.get('breed', 'Unknown')
                            })
                        )
                        documents.append(doc)
                        
                except Exception as e:
                    logger.warning(f"Error processing sheet {sheet_name}: {e}")
                    continue
            
            return documents
            
        except Exception as e:
            logger.error(f"Error parsing Excel tables: {e}")
            return []
    
    def _extract_table_sections(self, content: str) -> List[Dict[str, Any]]:
        """Extract table sections from text content"""
        table_sections = []
        
        # Split content into logical sections
        sections = self._split_content_by_headers(content)
        
        for section in sections:
            # Analyze if section contains tabular data
            if self._is_table_section(section['content']):
                table_data = self._parse_text_table(section['content'])
                if table_data:
                    table_sections.append({
                        'title': section['title'],
                        'content': section['content'],
                        'parsed_data': table_data,
                        'table_type': self._classify_table_type(section['content'])
                    })
        
        return table_sections
    
    def _split_content_by_headers(self, content: str) -> List[Dict[str, str]]:
        """Split content by headers and titles"""
        sections = []
        lines = content.split('\n')
        current_section = {'title': 'Introduction', 'content': ''}
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check if line is a header (all caps, or title case with few words)
            if (line.isupper() and len(line.split()) <= 8) or self._is_header_line(line):
                # Save current section if it has content
                if current_section['content'].strip():
                    sections.append(current_section)
                
                # Start new section
                current_section = {'title': line, 'content': ''}
            else:
                current_section['content'] += line + '\n'
        
        # Add last section
        if current_section['content'].strip():
            sections.append(current_section)
        
        return sections
    
    def _is_header_line(self, line: str) -> bool:
        """Determine if a line is likely a header"""
        # Check for common header patterns
        header_patterns = [
            r'^[A-Z][a-z\s]+Table$',
            r'^[A-Z][a-z\s]+Period$',
            r'^[A-Z][a-z\s]+Performance$',
            r'^[A-Z][a-z\s]+Recommendations$'
        ]
        
        return any(re.match(pattern, line) for pattern in header_patterns)
    
    def _is_table_section(self, content: str) -> bool:
        """Determine if content section contains tabular data"""
        lines = content.split('\n')
        
        # Count lines that look like table rows (numbers, consistent spacing)
        table_like_lines = 0
        for line in lines:
            if self._is_table_row(line):
                table_like_lines += 1
        
        # If more than 30% of lines look like table rows, consider it a table
        return table_like_lines > len(lines) * 0.3
    
    def _is_table_row(self, line: str) -> bool:
        """Check if a line appears to be a table row"""
        line = line.strip()
        if not line:
            return False
        
        # Look for numeric data with consistent spacing
        numeric_pattern = r'\d+\.?\d*'
        numbers = re.findall(numeric_pattern, line)
        
        # Table rows typically have multiple numbers
        return len(numbers) >= 2 and len(line.split()) >= 3
    
    def _parse_text_table(self, content: str) -> Optional[Dict[str, Any]]:
        """Parse table structure from text content"""
        lines = [line.strip() for line in content.split('\n') if line.strip()]
        
        if len(lines) < 2:
            return None
        
        # Try to identify headers and data rows
        header_line = None
        data_rows = []
        
        for i, line in enumerate(lines):
            if self._is_table_row(line):
                if header_line is None and i > 0:
                    # Previous line might be header
                    header_line = lines[i-1]
                data_rows.append(line)
        
        if not data_rows:
            return None
        
        return {
            'header': header_line,
            'rows': data_rows,
            'row_count': len(data_rows)
        }
    
    def _classify_table_type(self, content: str) -> str:
        """Classify the type of table based on content"""
        content_lower = content.lower()
        
        # Check for different table types
        if any(indicator in content_lower for indicator in self.PERFORMANCE_INDICATORS['weekly_performance']):
            return 'weekly_performance'
        elif any(indicator in content_lower for indicator in self.PERFORMANCE_INDICATORS['production_data']):
            return 'production_data'
        elif any(indicator in content_lower for indicator in self.PERFORMANCE_INDICATORS['nutritional_specs']):
            return 'nutritional_specs'
        else:
            return 'general_table'
    
    def _analyze_excel_structure(self, df: pd.DataFrame, sheet_name: str) -> Optional[Dict[str, Any]]:
        """Analyze Excel sheet structure and extract meaningful content"""
        if df.empty:
            return None
        
        # Detect table type
        table_type = self._classify_excel_table(df, sheet_name)
        
        # Extract structured content
        content_parts = [
            f"Performance Data Table - {sheet_name}",
            f"Table Type: {table_type}",
            f"Data Dimensions: {df.shape[0]} rows × {df.shape[1]} columns",
            ""
        ]
        
        # Detect breed information
        breed = self._detect_breed_from_excel(df, sheet_name)
        
        # Extract key metrics
        metrics = self._extract_excel_metrics(df)
        
        # Create readable summary
        if table_type == 'weekly_performance':
            content_parts.extend(self._format_weekly_performance(df))
        elif table_type == 'production_data':
            content_parts.extend(self._format_production_data(df))
        elif table_type == 'nutritional_specs':
            content_parts.extend(self._format_nutritional_data(df))
        else:
            # Generic table formatting
            content_parts.extend(self._format_generic_table(df))
        
        return {
            'content': '\n'.join(content_parts),
            'table_type': table_type,
            'structure': f"{df.shape[0]}x{df.shape[1]}",
            'metrics': metrics,
            'breed': breed
        }
    
    def _classify_excel_table(self, df: pd.DataFrame, sheet_name: str) -> str:
        """Classify Excel table type"""
        # Convert all text to lowercase for analysis
        text_content = f"{sheet_name} {str(df.columns.tolist())} {str(df.head().values.tolist())}"
        text_lower = text_content.lower()
        
        # Score each table type
        scores = {}
        for table_type, indicators in self.PERFORMANCE_INDICATORS.items():
            score = sum(1 for indicator in indicators if indicator in text_lower)
            scores[table_type] = score
        
        # Return type with highest score
        return max(scores, key=scores.get) if max(scores.values()) > 0 else 'general_table'
    
    def _detect_breed_from_excel(self, df: pd.DataFrame, sheet_name: str) -> str:
        """Detect breed from Excel content"""
        text_content = f"{sheet_name} {str(df.values)}"
        text_lower = text_content.lower()
        
        breed_patterns = {
            'hy_line_brown': ['hy-line brown', 'hyline brown', 'hy line brown'],
            'ross_308': ['ross 308', 'ross308'],
            'cobb_500': ['cobb 500', 'cobb500'],
            'generic_layer': ['layer', 'laying hen'],
            'generic_broiler': ['broiler', 'meat bird']
        }
        
        for breed_key, patterns in breed_patterns.items():
            if any(pattern in text_lower for pattern in patterns):
                return breed_key.replace('_', ' ').title()
        
        return "Unknown"
    
    def _extract_excel_metrics(self, df: pd.DataFrame) -> List[str]:
        """Extract key metrics from Excel data"""
        metrics = []
        
        # Look for common metrics in column names
        columns_lower = [str(col).lower() for col in df.columns]
        
        metric_keywords = [
            'weight', 'feed', 'production', 'mortality', 'age',
            'protein', 'energy', 'calcium', 'phosphorus'
        ]
        
        for keyword in metric_keywords:
            if any(keyword in col for col in columns_lower):
                metrics.append(keyword)
        
        return metrics
    
    def _format_weekly_performance(self, df: pd.DataFrame) -> List[str]:
        """Format weekly performance data"""
        content = ["Weekly Performance Summary:"]
        
        # Try to identify key columns
        age_col = self._find_column(df, ['age', 'week', 'days'])
        weight_col = self._find_column(df, ['weight', 'body weight', 'bw'])
        feed_col = self._find_column(df, ['feed', 'intake', 'consumption'])
        
        # Create summary rows
        if age_col is not None and not df[age_col].isna().all():
            age_range = df[age_col].dropna()
            if not age_range.empty:
                content.append(f"Age range: Week {age_range.min()} to Week {age_range.max()}")
        
        if weight_col is not None and not df[weight_col].isna().all():
            weight_range = df[weight_col].dropna()
            if not weight_range.empty:
                content.append(f"Weight range: {weight_range.min()}g to {weight_range.max()}g")
        
        return content
    
    def _format_production_data(self, df: pd.DataFrame) -> List[str]:
        """Format production data"""
        content = ["Production Performance Summary:"]
        
        # Look for production metrics
        production_col = self._find_column(df, ['production', 'hen-day', 'henday'])
        egg_weight_col = self._find_column(df, ['egg weight', 'egg wt'])
        
        if production_col is not None:
            prod_data = df[production_col].dropna()
            if not prod_data.empty:
                content.append(f"Production range: {prod_data.min():.1f}% to {prod_data.max():.1f}%")
        
        return content
    
    def _format_nutritional_data(self, df: pd.DataFrame) -> List[str]:
        """Format nutritional specification data"""
        content = ["Nutritional Specifications Summary:"]
        
        # Look for nutritional components
        nutrients = ['protein', 'energy', 'lysine', 'methionine', 'calcium']
        found_nutrients = []
        
        for nutrient in nutrients:
            col = self._find_column(df, [nutrient])
            if col is not None:
                found_nutrients.append(nutrient)
        
        if found_nutrients:
            content.append(f"Nutrients specified: {', '.join(found_nutrients)}")
        
        return content
    
    def _format_generic_table(self, df: pd.DataFrame) -> List[str]:
        """Format generic table data"""
        content = ["Table Data Summary:"]
        
        # Show column names
        content.append(f"Columns: {', '.join(str(col) for col in df.columns[:5])}")
        if len(df.columns) > 5:
            content.append(f"... and {len(df.columns) - 5} more columns")
        
        # Show sample data
        if not df.empty:
            content.append("\nSample data:")
            sample_data = df.head(3).to_string(index=False, max_cols=5)
            content.append(sample_data)
        
        return content
    
    def _find_column(self, df: pd.DataFrame, keywords: List[str]) -> Optional[str]:
        """Find column containing any of the keywords"""
        columns_lower = {str(col).lower(): col for col in df.columns}
        
        for keyword in keywords:
            for col_lower, col_original in columns_lower.items():
                if keyword in col_lower:
                    return col_original
        
        return None
    
    def _create_structured_document(self, table_section: Dict[str, Any], 
                                  file_path: str, page_num: int, section_num: int) -> Optional[Document]:
        """Create structured document from table section"""
        if not table_section.get('parsed_data'):
            return None
        
        # Build structured content
        content_parts = [
            f"Performance Table - {table_section['title']}",
            f"Table Type: {table_section['table_type']}",
            ""
        ]
        
        # Add parsed table data
        if table_section['parsed_data']['header']:
            content_parts.append(f"Headers: {table_section['parsed_data']['header']}")
        
        content_parts.append(f"Data rows: {table_section['parsed_data']['row_count']}")
        content_parts.append("")
        
        # Add sample of actual data
        content_parts.append("Sample data:")
        for i, row in enumerate(table_section['parsed_data']['rows'][:3]):
            content_parts.append(f"Row {i+1}: {row}")
        
        return Document(
            page_content='\n'.join(content_parts),
            metadata=self.create_base_metadata(file_path, {
                'page_number': page_num,
                'section_number': section_num,
                'table_type': table_section['table_type'],
                'table_title': table_section['title'],
                'data_rows': table_section['parsed_data']['row_count'],
                'extraction_method': 'performance_table_parser'
            })
        )
