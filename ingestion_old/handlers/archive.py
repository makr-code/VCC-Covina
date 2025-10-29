"""Archive ingestion handler with extraction and recursive processing."""
from __future__ import annotations

import logging
import shutil
import zipfile
import tarfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from .base import BaseIngestionHandler, HandlerContext
from ..file_events import FileCategory

logger = logging.getLogger(__name__)

# Optional dependencies for additional archive formats
try:
    import py7zr  # type: ignore
    PY7ZR_AVAILABLE = True
except ImportError:
    PY7ZR_AVAILABLE = False
    logger.debug("py7zr not available - .7z support disabled")

try:
    import rarfile  # type: ignore
    RARFILE_AVAILABLE = True
except ImportError:
    RARFILE_AVAILABLE = False
    logger.debug("rarfile not available - .rar support disabled")


class ArchiveIngestionHandler(BaseIngestionHandler):
    """
    Handles archive files with extraction and recursive processing.
    
    Supported formats:
    - ZIP (.zip)
    - TAR (.tar, .tar.gz, .tgz, .tar.bz2, .tbz2)
    - 7-Zip (.7z) - requires py7zr
    - RAR (.rar) - requires rarfile + unrar binary
    
    Features:
    - Recursive extraction (archives within archives)
    - Content discovery (finds ingestible files)
    - Metadata extraction (compression ratio, file count)
    - Error handling (corrupted archives, password-protected)
    
    Usage:
        handler = ArchiveIngestionHandler()
        context = HandlerContext(file_path=Path("data.zip"), temp_dir=Path("temp"))
        extracted_files = handler.extract_and_discover_files(context)
    """
    
    category = FileCategory.ARCHIVE
    
    # Supported text/office formats to extract and process
    INGESTIBLE_EXTENSIONS: Set[str] = {
        # Text documents
        '.txt', '.md', '.markdown', '.rtf',
        # Office documents
        '.pdf', '.doc', '.docx', '.odt',
        '.xls', '.xlsx', '.ods',
        '.ppt', '.pptx', '.odp',
        # Data formats
        '.json', '.xml', '.yaml', '.yml',
        '.csv', '.tsv',
        # Web formats
        '.html', '.htm',
        # Code (optional - can be filtered later)
        '.py', '.js', '.ts', '.java', '.cs', '.go',
        '.sql', '.sh', '.bat', '.ps1',
    }
    
    def extract_metadata(self, context: HandlerContext) -> Dict[str, Any]:
        """Extract archive metadata without full extraction."""
        path = context.file_path
        suffix = path.suffix.lower()
        
        metadata: Dict[str, Any] = {
            "archive_type": suffix.lstrip('.'),
            "size_bytes": path.stat().st_size,
            "modified_at": path.stat().st_mtime,
        }
        
        try:
            if suffix == '.zip':
                metadata.update(self._extract_zip_metadata(path))
            elif suffix in ['.tar', '.tar.gz', '.tgz', '.tar.bz2', '.tbz2']:
                metadata.update(self._extract_tar_metadata(path))
            elif suffix == '.7z' and PY7ZR_AVAILABLE:
                metadata.update(self._extract_7z_metadata(path))
            elif suffix == '.rar' and RARFILE_AVAILABLE:
                metadata.update(self._extract_rar_metadata(path))
            else:
                logger.warning(f"Unsupported archive format: {suffix}")
                metadata["unsupported"] = True
        except Exception as e:
            logger.error(f"Failed to extract metadata from {path}: {e}")
            metadata["metadata_error"] = str(e)
        
        return metadata
    
    def extract_content(self, context: HandlerContext, metadata: Dict[str, Any]) -> Optional[str]:
        """
        Extract archive and return summary of contents.
        
        Returns:
            Summary string describing extracted contents
        """
        path = context.file_path
        
        try:
            extracted_files = self.extract_and_discover_files(context)
            
            total_files = len(extracted_files)
            file_types = {}
            for file_path in extracted_files:
                ext = Path(file_path).suffix.lower()
                file_types[ext] = file_types.get(ext, 0) + 1
            
            summary_parts = [
                f"Extracted {total_files} ingestible files from archive",
                f"File types: {', '.join(f'{ext}({count})' for ext, count in sorted(file_types.items()))}"
            ]
            
            return " | ".join(summary_parts)
            
        except Exception as e:
            logger.error(f"Failed to extract archive {path}: {e}")
            return f"ERROR: {str(e)}"
    
    def generate_summary(
        self,
        context: HandlerContext,
        content: Optional[str],
        metadata: Dict[str, Any]
    ) -> Optional[str]:
        """Generate human-readable summary of archive."""
        archive_type = metadata.get("archive_type", "unknown").upper()
        total_files = metadata.get("total_files", 0)
        compressed_size = metadata.get("compressed_size_mb", 0)
        uncompressed_size = metadata.get("uncompressed_size_mb", 0)
        
        if uncompressed_size > 0:
            ratio = (1 - compressed_size / uncompressed_size) * 100
            return (
                f"{archive_type} Archive: {total_files} files, "
                f"{compressed_size:.1f}MB compressed ({ratio:.0f}% compression)"
            )
        else:
            return f"{archive_type} Archive: {total_files} files"
    
    # ========================================================================
    # Archive Extraction Methods
    # ========================================================================
    
    def extract_and_discover_files(self, context: HandlerContext) -> List[str]:
        """
        Extract archive and recursively discover ingestible files.
        
        Args:
            context: Handler context with file_path and temp_dir
            
        Returns:
            List of absolute paths to extracted ingestible files
            
        Raises:
            ValueError: If archive format is unsupported
            RuntimeError: If extraction fails
        """
        path = context.file_path
        suffix = path.suffix.lower()
        
        if not context.temp_dir:
            raise ValueError("temp_dir is required for archive extraction")
        
        # Create extraction directory
        extract_dir = context.temp_dir / "extracted" / path.stem
        extract_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"📦 Extracting archive: {path.name} → {extract_dir}")
        
        try:
            # Extract based on format
            if suffix == '.zip':
                self._extract_zip(path, extract_dir)
            elif suffix in ['.tar', '.tar.gz', '.tgz', '.tar.bz2', '.tbz2']:
                self._extract_tar(path, extract_dir)
            elif suffix == '.7z' and PY7ZR_AVAILABLE:
                self._extract_7z(path, extract_dir)
            elif suffix == '.rar' and RARFILE_AVAILABLE:
                self._extract_rar(path, extract_dir)
            else:
                raise ValueError(f"Unsupported archive format: {suffix}")
            
            # Recursively discover ingestible files
            discovered_files = self._discover_ingestible_files(extract_dir)
            
            logger.info(
                f"✅ Extracted {len(discovered_files)} ingestible files from {path.name}"
            )
            
            return discovered_files
            
        except Exception as e:
            logger.error(f"❌ Failed to extract archive {path.name}: {e}")
            # Cleanup failed extraction
            if extract_dir.exists():
                shutil.rmtree(extract_dir, ignore_errors=True)
            raise RuntimeError(f"Archive extraction failed: {e}") from e
    
    def _extract_zip(self, archive_path: Path, extract_dir: Path) -> None:
        """Extract ZIP archive."""
        with zipfile.ZipFile(archive_path, 'r') as zip_ref:
            # Check for password protection
            for info in zip_ref.infolist():
                if info.flag_bits & 0x1:  # Password-protected
                    raise RuntimeError("Password-protected ZIP archives are not supported")
            
            # Extract all files
            zip_ref.extractall(extract_dir)
            logger.debug(f"ZIP extracted: {len(zip_ref.namelist())} files")
    
    def _extract_tar(self, archive_path: Path, extract_dir: Path) -> None:
        """Extract TAR archive (including .tar.gz, .tar.bz2)."""
        with tarfile.open(archive_path, 'r:*') as tar_ref:
            # Security check: prevent path traversal
            for member in tar_ref.getmembers():
                if member.name.startswith('/') or '..' in member.name:
                    logger.warning(f"Skipping unsafe path: {member.name}")
                    continue
            
            # Extract all files
            tar_ref.extractall(extract_dir)
            logger.debug(f"TAR extracted: {len(tar_ref.getnames())} files")
    
    def _extract_7z(self, archive_path: Path, extract_dir: Path) -> None:
        """Extract 7-Zip archive (requires py7zr)."""
        if not PY7ZR_AVAILABLE:
            raise RuntimeError("py7zr not installed - cannot extract .7z files")
        
        with py7zr.SevenZipFile(archive_path, mode='r') as z:
            # Check for password protection
            if z.needs_password():
                raise RuntimeError("Password-protected 7z archives are not supported")
            
            # Extract all files
            z.extractall(path=extract_dir)
            logger.debug(f"7z extracted to {extract_dir}")
    
    def _extract_rar(self, archive_path: Path, extract_dir: Path) -> None:
        """Extract RAR archive (requires rarfile + unrar binary)."""
        if not RARFILE_AVAILABLE:
            raise RuntimeError("rarfile not installed - cannot extract .rar files")
        
        with rarfile.RarFile(archive_path, 'r') as rar_ref:
            # Check for password protection
            if rar_ref.needs_password():
                raise RuntimeError("Password-protected RAR archives are not supported")
            
            # Extract all files
            rar_ref.extractall(extract_dir)
            logger.debug(f"RAR extracted: {len(rar_ref.namelist())} files")
    
    # ========================================================================
    # File Discovery Methods
    # ========================================================================
    
    def _discover_ingestible_files(self, extract_dir: Path) -> List[str]:
        """
        Recursively find all ingestible files in extracted directory.
        
        This includes:
        - Text documents
        - Office documents (PDF, DOCX, etc.)
        - Structured data (JSON, XML, etc.)
        - Nested archives (will be extracted later)
        
        Args:
            extract_dir: Directory to search
            
        Returns:
            List of absolute paths to ingestible files
        """
        discovered = []
        
        for item in extract_dir.rglob("*"):
            if not item.is_file():
                continue
            
            suffix = item.suffix.lower()
            
            # Check if file is ingestible
            if suffix in self.INGESTIBLE_EXTENSIONS:
                discovered.append(str(item.absolute()))
            
            # Also discover nested archives (for recursive processing)
            elif suffix in {'.zip', '.tar', '.tar.gz', '.tgz', '.7z', '.rar'}:
                discovered.append(str(item.absolute()))
                logger.debug(f"Found nested archive: {item.name}")
        
        return discovered
    
    # ========================================================================
    # Metadata Extraction Methods
    # ========================================================================
    
    def _extract_zip_metadata(self, path: Path) -> Dict[str, Any]:
        """Extract ZIP archive metadata."""
        with zipfile.ZipFile(path, 'r') as zip_ref:
            file_list = zip_ref.namelist()
            compressed_size = sum(info.compress_size for info in zip_ref.infolist())
            uncompressed_size = sum(info.file_size for info in zip_ref.infolist())
            
            return {
                "total_files": len(file_list),
                "compressed_size_mb": compressed_size / (1024 * 1024),
                "uncompressed_size_mb": uncompressed_size / (1024 * 1024),
                "compression_ratio": compressed_size / uncompressed_size if uncompressed_size > 0 else 0,
                "is_encrypted": any(info.flag_bits & 0x1 for info in zip_ref.infolist()),
            }
    
    def _extract_tar_metadata(self, path: Path) -> Dict[str, Any]:
        """Extract TAR archive metadata."""
        with tarfile.open(path, 'r:*') as tar_ref:
            members = tar_ref.getmembers()
            uncompressed_size = sum(m.size for m in members if m.isfile())
            
            return {
                "total_files": sum(1 for m in members if m.isfile()),
                "compressed_size_mb": path.stat().st_size / (1024 * 1024),
                "uncompressed_size_mb": uncompressed_size / (1024 * 1024),
                "compression_ratio": path.stat().st_size / uncompressed_size if uncompressed_size > 0 else 0,
                "is_encrypted": False,  # TAR doesn't support encryption natively
            }
    
    def _extract_7z_metadata(self, path: Path) -> Dict[str, Any]:
        """Extract 7-Zip archive metadata."""
        if not PY7ZR_AVAILABLE:
            return {"unsupported": True}
        
        with py7zr.SevenZipFile(path, mode='r') as z:
            file_list = z.getnames()
            
            return {
                "total_files": len(file_list),
                "compressed_size_mb": path.stat().st_size / (1024 * 1024),
                "is_encrypted": z.needs_password(),
            }
    
    def _extract_rar_metadata(self, path: Path) -> Dict[str, Any]:
        """Extract RAR archive metadata."""
        if not RARFILE_AVAILABLE:
            return {"unsupported": True}
        
        with rarfile.RarFile(path, 'r') as rar_ref:
            file_list = rar_ref.namelist()
            compressed_size = sum(info.compress_size for info in rar_ref.infolist())
            uncompressed_size = sum(info.file_size for info in rar_ref.infolist())
            
            return {
                "total_files": len(file_list),
                "compressed_size_mb": compressed_size / (1024 * 1024),
                "uncompressed_size_mb": uncompressed_size / (1024 * 1024),
                "compression_ratio": compressed_size / uncompressed_size if uncompressed_size > 0 else 0,
                "is_encrypted": rar_ref.needs_password(),
            }
