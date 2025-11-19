"""
Table Extraction Module

Extracts tables from PDFs and office documents using multiple methods:
- camelot-py for PDF tables (high quality)
- tabula-py as fallback
- pdfplumber as additional fallback
- python-docx for DOCX tables

Integrates with existing worker pool architecture.
"""
import logging
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict
import json

logger = logging.getLogger(__name__)


@dataclass
class ExtractedTable:
    """Container for extracted table data"""
    table_index: int
    page_number: Optional[int]
    rows: int
    columns: int
    data: List[List[str]]  # 2D array of cell values
    headers: Optional[List[str]]
    confidence: float  # 0.0-1.0
    extraction_method: str
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return asdict(self)
    
    def to_csv(self) -> str:
        """Convert table to CSV format"""
        lines = []
        
        # Add headers if present
        if self.headers:
            lines.append(','.join(f'"{h}"' for h in self.headers))
        
        # Add data rows
        for row in self.data:
            lines.append(','.join(f'"{cell}"' for cell in row))
        
        return '\n'.join(lines)
    
    def to_json(self) -> str:
        """Convert table to JSON format"""
        table_dict = {
            'headers': self.headers,
            'data': self.data,
            'metadata': {
                'rows': self.rows,
                'columns': self.columns,
                'page': self.page_number,
                'confidence': self.confidence
            }
        }
        return json.dumps(table_dict, ensure_ascii=False, indent=2)


class TableExtractor:
    """
    Extract tables from documents using multiple extraction methods.
    
    Supports:
    - PDF tables (camelot, tabula, pdfplumber)
    - DOCX tables (python-docx)
    
    Graceful fallback when libraries unavailable.
    """
    
    def __init__(self):
        self.available_methods = self._check_available_methods()
        logger.info(f"Table extraction methods available: {self.available_methods}")
    
    def _check_available_methods(self) -> Dict[str, bool]:
        """Check which extraction libraries are available"""
        methods = {
            'camelot': False,
            'tabula': False,
            'pdfplumber': False,
            'docx': False
        }
        
        # Check camelot
        try:
            import camelot
            methods['camelot'] = True
        except ImportError:
            pass
        
        # Check tabula
        try:
            import tabula
            methods['tabula'] = True
        except ImportError:
            pass
        
        # Check pdfplumber
        try:
            import pdfplumber
            methods['pdfplumber'] = True
        except ImportError:
            pass
        
        # Check python-docx
        try:
            import docx
            methods['docx'] = True
        except ImportError:
            pass
        
        return methods
    
    def is_available(self) -> bool:
        """Check if at least one extraction method is available"""
        return any(self.available_methods.values())
    
    def extract_tables(self, file_path: str) -> List[ExtractedTable]:
        """
        Extract all tables from a document.
        
        Args:
            file_path: Path to document file
            
        Returns:
            List of ExtractedTable objects
        """
        if not self.is_available():
            logger.warning("No table extraction libraries available - install camelot-py, tabula-py, or pdfplumber")
            return []
        
        file_path_obj = Path(file_path)
        extension = file_path_obj.suffix.lower()
        
        try:
            if extension == '.pdf':
                return self._extract_from_pdf(file_path)
            elif extension in ['.docx', '.doc']:
                return self._extract_from_docx(file_path)
            else:
                logger.debug(f"Table extraction not supported for {extension}")
                return []
        
        except Exception as e:
            logger.error(f"Table extraction failed for {file_path}: {e}")
            return []
    
    def _extract_from_pdf(self, file_path: str) -> List[ExtractedTable]:
        """Extract tables from PDF using best available method"""
        
        # Try camelot first (highest quality)
        if self.available_methods['camelot']:
            tables = self._extract_with_camelot(file_path)
            if tables:
                return tables
        
        # Try tabula as fallback
        if self.available_methods['tabula']:
            tables = self._extract_with_tabula(file_path)
            if tables:
                return tables
        
        # Try pdfplumber as last resort
        if self.available_methods['pdfplumber']:
            tables = self._extract_with_pdfplumber(file_path)
            if tables:
                return tables
        
        logger.warning(f"No tables found in PDF: {file_path}")
        return []
    
    def _extract_with_camelot(self, file_path: str) -> List[ExtractedTable]:
        """Extract tables using camelot-py (highest quality)"""
        try:
            import camelot
            
            # Extract tables with lattice method (structured tables)
            tables_lattice = camelot.read_pdf(file_path, flavor='lattice', pages='all')
            
            # Extract tables with stream method (borderless tables)
            tables_stream = camelot.read_pdf(file_path, flavor='stream', pages='all')
            
            # Combine results
            all_tables = list(tables_lattice) + list(tables_stream)
            
            extracted = []
            for idx, table in enumerate(all_tables):
                # Convert to our format
                df = table.df
                data = df.values.tolist()
                headers = df.columns.tolist() if not df.columns.equals(range(len(df.columns))) else None
                
                extracted_table = ExtractedTable(
                    table_index=idx,
                    page_number=table.page,
                    rows=len(data),
                    columns=len(data[0]) if data else 0,
                    data=[[str(cell) for cell in row] for row in data],
                    headers=[str(h) for h in headers] if headers else None,
                    confidence=table.accuracy / 100.0,  # camelot returns 0-100
                    extraction_method='camelot',
                    metadata={
                        'flavor': table.flavor,
                        'order': table.order,
                        'whitespace': table.whitespace
                    }
                )
                extracted.append(extracted_table)
            
            logger.info(f"✓ Camelot extracted {len(extracted)} tables from {file_path}")
            return extracted
        
        except Exception as e:
            logger.warning(f"Camelot extraction failed: {e}")
            return []
    
    def _extract_with_tabula(self, file_path: str) -> List[ExtractedTable]:
        """Extract tables using tabula-py"""
        try:
            import tabula
            
            # Extract all tables
            tables = tabula.read_pdf(file_path, pages='all', multiple_tables=True)
            
            extracted = []
            for idx, df in enumerate(tables):
                if df.empty:
                    continue
                
                data = df.values.tolist()
                headers = df.columns.tolist()
                
                extracted_table = ExtractedTable(
                    table_index=idx,
                    page_number=None,  # tabula doesn't provide page info easily
                    rows=len(data),
                    columns=len(data[0]) if data else 0,
                    data=[[str(cell) for cell in row] for row in data],
                    headers=[str(h) for h in headers],
                    confidence=0.8,  # tabula doesn't provide confidence
                    extraction_method='tabula',
                    metadata={}
                )
                extracted.append(extracted_table)
            
            logger.info(f"✓ Tabula extracted {len(extracted)} tables from {file_path}")
            return extracted
        
        except Exception as e:
            logger.warning(f"Tabula extraction failed: {e}")
            return []
    
    def _extract_with_pdfplumber(self, file_path: str) -> List[ExtractedTable]:
        """Extract tables using pdfplumber"""
        try:
            import pdfplumber
            
            extracted = []
            table_idx = 0
            
            with pdfplumber.open(file_path) as pdf:
                for page_num, page in enumerate(pdf.pages, start=1):
                    tables = page.extract_tables()
                    
                    for table in tables:
                        if not table:
                            continue
                        
                        # First row might be headers
                        headers = None
                        data = table
                        
                        if len(table) > 1:
                            # Check if first row looks like headers (all strings, no numbers)
                            first_row = table[0]
                            if first_row and all(isinstance(cell, str) for cell in first_row):
                                headers = [str(cell) for cell in first_row]
                                data = table[1:]
                        
                        extracted_table = ExtractedTable(
                            table_index=table_idx,
                            page_number=page_num,
                            rows=len(data),
                            columns=len(data[0]) if data else 0,
                            data=[[str(cell) if cell else '' for cell in row] for row in data],
                            headers=headers,
                            confidence=0.7,  # pdfplumber doesn't provide confidence
                            extraction_method='pdfplumber',
                            metadata={'page': page_num}
                        )
                        extracted.append(extracted_table)
                        table_idx += 1
            
            logger.info(f"✓ PDFPlumber extracted {len(extracted)} tables from {file_path}")
            return extracted
        
        except Exception as e:
            logger.warning(f"PDFPlumber extraction failed: {e}")
            return []
    
    def _extract_from_docx(self, file_path: str) -> List[ExtractedTable]:
        """Extract tables from DOCX using python-docx"""
        if not self.available_methods['docx']:
            logger.warning("python-docx not available for DOCX table extraction")
            return []
        
        try:
            import docx
            
            doc = docx.Document(file_path)
            extracted = []
            
            for idx, table in enumerate(doc.tables):
                # Extract table data
                data = []
                for row in table.rows:
                    row_data = [cell.text.strip() for cell in row.cells]
                    data.append(row_data)
                
                if not data:
                    continue
                
                # First row as headers
                headers = data[0] if data else None
                table_data = data[1:] if len(data) > 1 else data
                
                extracted_table = ExtractedTable(
                    table_index=idx,
                    page_number=None,  # DOCX doesn't have page numbers
                    rows=len(table_data),
                    columns=len(table_data[0]) if table_data else 0,
                    data=table_data,
                    headers=headers,
                    confidence=1.0,  # DOCX extraction is deterministic
                    extraction_method='python-docx',
                    metadata={}
                )
                extracted.append(extracted_table)
            
            logger.info(f"✓ python-docx extracted {len(extracted)} tables from {file_path}")
            return extracted
        
        except Exception as e:
            logger.error(f"DOCX table extraction failed: {e}")
            return []
    
    def get_table_statistics(self, tables: List[ExtractedTable]) -> Dict[str, Any]:
        """Generate statistics about extracted tables"""
        if not tables:
            return {
                'total_tables': 0,
                'total_cells': 0,
                'avg_rows': 0,
                'avg_columns': 0,
                'avg_confidence': 0.0,
                'methods_used': []
            }
        
        total_cells = sum(t.rows * t.columns for t in tables)
        avg_rows = sum(t.rows for t in tables) / len(tables)
        avg_columns = sum(t.columns for t in tables) / len(tables)
        avg_confidence = sum(t.confidence for t in tables) / len(tables)
        methods_used = list(set(t.extraction_method for t in tables))
        
        return {
            'total_tables': len(tables),
            'total_cells': total_cells,
            'avg_rows': round(avg_rows, 1),
            'avg_columns': round(avg_columns, 1),
            'avg_confidence': round(avg_confidence, 2),
            'methods_used': methods_used,
            'tables': [
                {
                    'index': t.table_index,
                    'page': t.page_number,
                    'size': f"{t.rows}x{t.columns}",
                    'method': t.extraction_method,
                    'confidence': t.confidence
                }
                for t in tables
            ]
        }
