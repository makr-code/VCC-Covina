"""
Refactored DirectoryScanJob with Modular Architecture
This file contains the new implementation to replace the old one.
Lines 245-587 in ingestion_backend.py
"""

class DirectoryScanJob:
    """
    Modular directory scan job using ingestion.handlers architecture.
    
    Workflow:
    1. Scan directory recursively (DirectoryScanner)
    2. Copy files to temp directory (data/uploads/scan_{id}/)
    3. Extract archives (ArchiveIngestionHandler)
    4. Discover all ingestible files (including extracted)
    5. Create smart chunks
    6. Submit jobs to ThreadPool
    
    Features:
    - Modular handler system
    - Archive extraction (ZIP, RAR, 7z, TAR)
    - Timeout protection (network drives)
    - Smart chunking (size-aware)
    - Real-time WebSocket updates
    """
    
    def __init__(
        self,
        scan_job_id: str,
        directory_path: str,
        handler_factory: Optional[HandlerFactory] = None,
        chunk_size: int = 50
    ):
        self.scan_job_id = scan_job_id
        self.directory_path = Path(directory_path)
        self.handler_factory = handler_factory or HANDLER_FACTORY
        self.chunk_size = chunk_size
        
        # Create temp directory for file processing
        self.temp_dir = Path("data/uploads") / f"scan_{scan_job_id}"
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Scanner configuration
        self.scanner = DirectoryScanner(
            root=self.directory_path,
            classifier=FileClassifier(),
            compute_hashes=False  # Skip hashing for performance
        )
        
        # Status tracking
        self.status = "scanning"
        self.files_found = 0
        self.files_extracted = 0  # NEW: Track extracted files
        self.upload_jobs_created = []
        self.error_message = None
        self.start_time = datetime.now()
    
    async def scan_and_create_jobs(self):
        """Main workflow: scan → copy → extract → chunk → submit"""
        try:
            logger.info(f"🎯 [SCAN {self.scan_job_id}] Starting modular scan: {self.directory_path}")
            
            # Phase 1: Directory Scan
            file_events = await self._scan_directory()
            self.files_found = len(file_events)
            logger.info(f"📂 [SCAN {self.scan_job_id}] Found {self.files_found} files")
            
            if not file_events:
                self.status = "completed"
                self.error_message = "No supported files found"
                await self._broadcast_status()
                return
            
            # Phase 2: Copy Files & Extract Archives
            self.status = "extracting"
            await self._broadcast_status()
            
            all_files = await self._copy_and_extract_files(file_events)
            logger.info(
                f"✅ [SCAN {self.scan_job_id}] "
                f"{len(all_files)} files ready (extracted: {self.files_extracted})"
            )
            
            # Phase 3: Create Jobs
            self.status = "creating_jobs"
            await self._broadcast_status()
            
            await self._create_and_submit_jobs(all_files)
            
            # Phase 4: Complete
            self.status = "completed"
            elapsed = (datetime.now() - self.start_time).total_seconds()
            logger.info(
                f"🎉 [SCAN {self.scan_job_id}] Completed: "
                f"{self.files_found} original + {self.files_extracted} extracted = "
                f"{len(all_files)} total files in {elapsed:.1f}s"
            )
            await self._broadcast_status()
            
        except Exception as e:
            logger.error(f"❌ [SCAN {self.scan_job_id}] Error: {e}", exc_info=True)
            self.status = "error"
            self.error_message = str(e)
            await self._broadcast_status()
    
    async def _scan_directory(self) -> List:
        """Scan directory using DirectoryScanner with timeout protection."""
        logger.info(f"🔍 [SCAN {self.scan_job_id}] Scanning: {self.directory_path}")
        
        def scan_sync():
            """Sync wrapper for DirectoryScanner"""
            return self.scanner.scan_once()
        
        # Execute with timeout (network drive protection)
        loop = asyncio.get_running_loop()
        timeout_seconds = 300  # 5 minutes
        
        try:
            events = await asyncio.wait_for(
                loop.run_in_executor(None, scan_sync),
                timeout=timeout_seconds
            )
            logger.info(f"✅ [SCAN {self.scan_job_id}] Scan complete: {len(events)} events")
            return events
        except asyncio.TimeoutError:
            raise TimeoutError(
                f"Directory scan timeout after {timeout_seconds}s "
                f"(network drive issue: {self.directory_path})"
            )
    
    async def _copy_and_extract_files(self, file_events: List) -> List[str]:
        """
        Copy files to temp directory and extract archives.
        
        Returns:
            List of absolute paths to all processable files (including extracted)
        """
        all_files = []
        
        for event in file_events:
            snapshot = event.snapshot
            
            # Skip deleted files
            if event.type == FileEventType.DELETED:
                continue
            
            # Copy file to temp directory
            dest_path = self.temp_dir / snapshot.path.name
            try:
                shutil.copy2(snapshot.path, dest_path)
                logger.debug(f"📋 Copied: {snapshot.path.name} → {dest_path}")
            except Exception as e:
                logger.error(f"Failed to copy {snapshot.path}: {e}")
                continue
            
            # Handle based on category
            category = snapshot.category
            
            if category == FileCategory.ARCHIVE:
                # Extract archive using ArchiveIngestionHandler
                extracted = await self._extract_archive(dest_path)
                all_files.extend(extracted)
                self.files_extracted += len(extracted)
                logger.info(
                    f"📦 [SCAN {self.scan_job_id}] Extracted {len(extracted)} files "
                    f"from {snapshot.path.name}"
                )
            else:
                # Regular file - add directly
                all_files.append(str(dest_path))
        
        return all_files
    
    async def _extract_archive(self, archive_path: Path) -> List[str]:
        """Extract archive using ArchiveIngestionHandler."""
        try:
            # Get handler for archives
            handler = self.handler_factory.create(FileCategory.ARCHIVE)
            
            # Create handler context
            context = HandlerContext(
                file_path=archive_path,
                temp_dir=self.temp_dir
            )
            
            # Execute extraction in thread pool (I/O bound)
            loop = asyncio.get_running_loop()
            extracted_files = await loop.run_in_executor(
                None,
                handler.extract_and_discover_files,
                context
            )
            
            logger.info(f"✅ Extracted {len(extracted_files)} files from {archive_path.name}")
            return extracted_files
            
        except Exception as e:
            logger.error(f"❌ Failed to extract {archive_path.name}: {e}")
            return []  # Return empty list on error (don't fail entire scan)
    
    async def _create_and_submit_jobs(self, file_paths: List[str]):
        """Create smart chunks and submit to ThreadPool."""
        from ingestion_backend import get_job_manager, io_executor, process_documents_batch
        
        jm = get_job_manager()
        
        # Smart chunking (size-aware)
        file_chunks = self._create_smart_chunks(file_paths)
        
        logger.info(
            f"📦 [SCAN {self.scan_job_id}] Created {len(file_chunks)} chunks "
            f"from {len(file_paths)} files"
        )
        
        # Submit each chunk
        for chunk_idx, chunk in enumerate(file_chunks):
            # Create job with temp_directory tracking
            upload_job_id = jm.create_job(
                len(chunk),
                temp_directory=str(self.temp_dir),  # ✅ IMPORTANT!
                scan_job_id=self.scan_job_id
            )
            self.upload_jobs_created.append(upload_job_id)
            
            # Submit to ThreadPool
            def process_chunk_sync(job_id, file_paths_chunk, chunk_idx, temp_dir):
                """Sync wrapper for background processing"""
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    logger.info(f"🚀 [THREAD {chunk_idx}] Processing {len(file_paths_chunk)} files")
                    loop.run_until_complete(
                        process_documents_batch(job_id, file_paths_chunk, temp_dir)
                    )
                    logger.info(f"✅ [THREAD {chunk_idx}] Completed")
                except Exception as e:
                    logger.error(f"❌ [THREAD {chunk_idx}] Error: {e}", exc_info=True)
                finally:
                    loop.close()
            
            io_executor.submit(
                process_chunk_sync,
                upload_job_id,
                chunk,
                chunk_idx,
                Path(self.temp_dir)
            )
            
            logger.info(
                f"📦 [SCAN {self.scan_job_id}] Job {chunk_idx+1}/{len(file_chunks)}: "
                f"{upload_job_id} ({len(chunk)} files)"
            )
    
    def _create_smart_chunks(self, file_paths: List[str]) -> List[List[str]]:
        """Create size-aware chunks respecting limits."""
        chunks = []
        current_chunk = []
        current_size = 0
        
        for file_path in file_paths:
            try:
                file_size = os.path.getsize(file_path)
                
                # Check if new chunk needed
                if (len(current_chunk) >= MAX_CHUNK_SIZE_FILES or
                    current_size + file_size > MAX_CHUNK_SIZE_MB * 1024 * 1024):
                    if current_chunk:
                        chunks.append(current_chunk)
                    current_chunk = []
                    current_size = 0
                
                current_chunk.append(file_path)
                current_size += file_size
                
            except OSError:
                # Skip files we can't access
                continue
        
        # Add final chunk
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks
    
    async def _broadcast_status(self):
        """Broadcast scan status via WebSocket"""
        try:
            elapsed = (datetime.now() - self.start_time).total_seconds()
            
            await ws_manager.broadcast_job_update({
                "type": "directory_scan_update",
                "scan_job_id": self.scan_job_id,
                "status": self.status,
                "files_found": self.files_found,
                "files_extracted": self.files_extracted,
                "upload_jobs_created": len(self.upload_jobs_created),
                "upload_job_ids": self.upload_jobs_created,
                "error": self.error_message,
                "elapsed_time": elapsed
            })
        except Exception as e:
            logger.debug(f"Status broadcast failed: {e}")
