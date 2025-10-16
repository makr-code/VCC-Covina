#!/usr/bin/env python3
"""
Enhanced Covina Frontend GUI
===========================

Erweiterte Benutzeroberfläche für Covina Document Processing mit:
- Intelligente Verzeichnisvorschau für große Dateimengen
- Mehrfache gleichzeitige Ingestion-Prozesse
- Resource-Sharing und Batch-Verarbeitung
- Erweiterte Job-Verwaltung mit Prioritäten
- Real-time Resource-Monitoring

Autor: Covina System
Datum: Oktober 2025
"""

import os
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import requests
import json
import time
import webbrowser
from datetime import datetime, timedelta
from pathlib import Path
import uuid
from typing import Dict, List, Optional, Any
import queue
import psutil
import mimetypes
import concurrent.futures
from collections import defaultdict, deque

# Import new architecture components
from covina_architecture import (
    EventBus, 
    TaskExecutor, 
    CovinaBackendService,
    EventType,
    Event
)

# Upload Progress Overlay Window
class UploadProgressOverlay:
    """Overlay-Fenster für Upload-Fortschritt mit Fortschrittsbalken"""
    
    def __init__(self, parent_root):
        self.parent = parent_root
        self.window = None
        self.progress_vars = {}
        self.status_labels = {}
        self.overall_progress = None
        self.overall_label = None
        self.cancel_button = None
        self.details_text = None
        self.is_cancelled = False
        
    def show(self, title: str = "Datei-Upload", total_files: int = 0):
        """Zeigt das Progress-Overlay"""
        if self.window:
            self.window.destroy()
            
        # Overlay-Fenster erstellen
        self.window = tk.Toplevel(self.parent)
        self.window.title(title)
        self.window.geometry("600x400")
        self.window.resizable(False, False)
        
        # Fenster zentrieren
        self.window.transient(self.parent)
        self.window.grab_set()
        
        # Zentrale Position berechnen
        self.parent.update_idletasks()
        parent_x = self.parent.winfo_x()
        parent_y = self.parent.winfo_y()
        parent_width = self.parent.winfo_width()
        parent_height = self.parent.winfo_height()
        
        x = parent_x + (parent_width // 2) - 300
        y = parent_y + (parent_height // 2) - 200
        self.window.geometry(f"600x400+{x}+{y}")
        
        # Hauptframe
        main_frame = ttk.Frame(self.window, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Titel
        title_label = ttk.Label(
            main_frame, 
            text=title, 
            font=('Arial', 14, 'bold')
        )
        title_label.pack(pady=(0, 20))
        
        # Gesamt-Fortschritt
        overall_frame = ttk.LabelFrame(main_frame, text="Gesamt-Fortschritt", padding="10")
        overall_frame.pack(fill=tk.X, pady=(0, 15))
        
        self.overall_label = ttk.Label(
            overall_frame, 
            text=f"0 von {total_files} Dateien verarbeitet"
        )
        self.overall_label.pack(pady=(0, 5))
        
        self.overall_progress = ttk.Progressbar(
            overall_frame,
            mode='determinate',
            length=550
        )
        self.overall_progress.pack(fill=tk.X, pady=(0, 5))
        
        # Status-Label für aktuelle Aktion
        self.current_action_label = ttk.Label(
            overall_frame,
            text="Bereite Upload vor...",
            font=('Arial', 9, 'italic')
        )
        self.current_action_label.pack()
        
        # Details-Bereich (scrollbar)
        details_frame = ttk.LabelFrame(main_frame, text="Upload-Details", padding="10")
        details_frame.pack(fill=tk.BOTH, expand=True, pady=(15, 0))
        
        self.details_text = scrolledtext.ScrolledText(
            details_frame,
            height=8,
            wrap=tk.WORD,
            font=('Consolas', 9),
            state='disabled'
        )
        self.details_text.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Button-Frame
        button_frame = ttk.Frame(details_frame)
        button_frame.pack(fill=tk.X)
        
        # Cancel Button
        self.cancel_button = ttk.Button(
            button_frame,
            text="❌ Abbrechen",
            command=self._cancel_upload
        )
        self.cancel_button.pack(side=tk.LEFT)
        
        # Close Button (initially disabled)
        self.close_button = ttk.Button(
            button_frame,
            text="✅ Schließen",
            command=self._close_window,
            state="disabled"
        )
        self.close_button.pack(side=tk.RIGHT)
        
        # Fenster-Events
        self.window.protocol("WM_DELETE_WINDOW", self._on_window_close)
        
        # Progress zurücksetzen
        self.is_cancelled = False
        self.overall_progress['maximum'] = total_files
        self.overall_progress['value'] = 0
        
        self._log_detail("Upload-Session gestartet", "INFO")
        
    def update_overall_progress(self, current: int, total: int, status: str = ""):
        """Aktualisiert den Gesamt-Fortschritt"""
        if not self.window:
            return
            
        try:
            self.overall_progress['value'] = current
            self.overall_progress['maximum'] = total
            
            percentage = (current / total * 100) if total > 0 else 0
            self.overall_label.config(text=f"{current} von {total} Dateien verarbeitet ({percentage:.1f}%)")
            
            if status:
                self.current_action_label.config(text=status)
                
            # Wenn fertig, Buttons aktivieren/deaktivieren
            if current >= total:
                self.cancel_button.config(state="disabled")
                self.close_button.config(state="normal")
                self.current_action_label.config(text="✅ Upload abgeschlossen!")
                
            self.window.update_idletasks()
        except Exception as e:
            print(f"Error updating progress: {e}")
    
    def update_file_progress(self, filename: str, progress: float, status: str = ""):
        """Aktualisiert Fortschritt für einzelne Datei"""
        if not self.window:
            return
            
        try:
            status_text = f"📄 {filename}: {progress:.1f}%"
            if status:
                status_text += f" - {status}"
                
            self._log_detail(status_text, "PROGRESS")
        except Exception as e:
            print(f"Error updating file progress: {e}")
    
    def _log_detail(self, message: str, level: str = "INFO"):
        """Fügt Detail-Log hinzu"""
        if not self.window or not self.details_text:
            return
            
        try:
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            # Level-spezifische Formatierung
            if level == "INFO":
                prefix = "ℹ️ "
            elif level == "SUCCESS":
                prefix = "✅ "
            elif level == "ERROR":
                prefix = "❌ "
            elif level == "WARNING":
                prefix = "⚠️ "
            elif level == "PROGRESS":
                prefix = "🔄 "
            else:
                prefix = "• "
            
            log_entry = f"[{timestamp}] {prefix}{message}\n"
            
            self.details_text.config(state='normal')
            self.details_text.insert(tk.END, log_entry)
            self.details_text.see(tk.END)
            self.details_text.config(state='disabled')
            
            self.window.update_idletasks()
        except Exception as e:
            print(f"Error logging detail: {e}")
    
    def log_success(self, message: str):
        """Loggt Erfolgsmeldung"""
        self._log_detail(message, "SUCCESS")
    
    def log_error(self, message: str):
        """Loggt Fehlermeldung"""
        self._log_detail(message, "ERROR")
    
    def log_warning(self, message: str):
        """Loggt Warnung"""
        self._log_detail(message, "WARNING")
    
    def log_info(self, message: str):
        """Loggt Information"""
        self._log_detail(message, "INFO")
    
    def _cancel_upload(self):
        """Upload abbrechen"""
        self.is_cancelled = True
        self.cancel_button.config(state="disabled")
        self.current_action_label.config(text="❌ Upload wird abgebrochen...")
        self._log_detail("Upload-Abbruch angefordert", "WARNING")
    
    def _close_window(self):
        """Fenster schließen"""
        if self.window:
            self.window.destroy()
            self.window = None
    
    def _on_window_close(self):
        """Wird aufgerufen, wenn Fenster geschlossen wird"""
        if not self.is_cancelled and self.cancel_button and self.cancel_button.cget('state') != 'disabled':
            # Noch aktiver Upload - Bestätigung anfordern
            if messagebox.askyesno(
                "Upload abbrechen?", 
                "Der Upload läuft noch. Wirklich abbrechen?",
                parent=self.window
            ):
                self._cancel_upload()
                self._close_window()
        else:
            self._close_window()
    
    def hide(self):
        """Versteckt das Overlay"""
        if self.window:
            self.window.withdraw()
    
    def is_visible(self) -> bool:
        """Prüft ob Overlay sichtbar ist"""
        return self.window is not None and self.window.winfo_exists()

# Covina Enhanced API Client
class CovinaAPIClient:
    """Enhanced Client für Covina Backend API mit Resource Management"""
    
    def __init__(self, base_url: str = "http://127.0.0.1:45678"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.timeout = 30
        
        # Connection pool configuration for concurrent requests
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=10,
            pool_maxsize=20,
            max_retries=3
        )
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)
    
    def health_check(self) -> Dict:
        """Backend Health Check"""
        try:
            response = self.session.get(f"{self.base_url}/health")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise Exception(f"Backend nicht erreichbar: {e}")
    
    def upload_files_batch(self, file_paths: List[str], batch_size: int = 10, curated_info: Dict = None) -> List[Dict]:
        """
        Upload files in batches with support for curated files
        
        WICHTIG: Archive (.zip, .tar, etc.) werden als GANZES übertragen!
        Das Backend entpackt diese selbst UND speichert das Original-Archiv in CouchDB.
        """
        results = []
        
        # Separiere Archive von normalen Dokumenten
        archive_extensions = {'.zip', '.tar', '.tar.gz', '.tgz', '.rar', '.7z', '.gz', '.bz2', '.xz'}
        archives = []
        documents = []
        
        for file_path in file_paths:
            file_ext = Path(file_path).suffix.lower()
            # Prüfe auch auf .tar in Dateinamen (für .tar.gz, .tar.bz2, etc.)
            if file_ext in archive_extensions or '.tar' in Path(file_path).name.lower():
                archives.append(file_path)
            else:
                documents.append(file_path)
        
        # Upload Archive einzeln (jedes Archiv als separate Datei)
        for archive_path in archives:
            try:
                with open(archive_path, 'rb') as f:
                    files = [('files', (Path(archive_path).name, f, 'application/octet-stream'))]
                    
                    # Archive-Flag setzen (Backend erkennt auch an Extension)
                    data = {'is_archive': 'true'}
                    if curated_info:
                        data['curated_info'] = json.dumps(curated_info)
                    
                    response = self.session.post(
                        f"{self.base_url}/upload/files",
                        files=files,
                        data=data
                    )
                    response.raise_for_status()
                    results.append(response.json())
                    
            except Exception as e:
                logger.error(f"❌ Fehler beim Upload von Archiv {Path(archive_path).name}: {e}")
                results.append({
                    "error": str(e),
                    "file": Path(archive_path).name,
                    "status": "failed"
                })
        
        # Upload normale Dokumente in Batches
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]
            files = []
            
            try:
                for file_path in batch:
                    files.append(('files', (Path(file_path).name, open(file_path, 'rb'), 'application/octet-stream')))
                
                # Add curated metadata if available
                data = {}
                if curated_info:
                    data['curated_info'] = json.dumps(curated_info)
                
                response = self.session.post(
                    f"{self.base_url}/upload/files", 
                    files=files, 
                    data=data
                )
                response.raise_for_status()
                results.append(response.json())
                
            finally:
                # Close files
                for _, file_tuple in files:
                    if hasattr(file_tuple[1], 'close'):
                        file_tuple[1].close()
        
        return results
    
    def upload_curated_files(self, curated_pairs: List[Dict], batch_size: int = 5) -> List[Dict]:
        """Upload curated file pairs (content + metadata) with high priority"""
        results = []
        
        for i in range(0, len(curated_pairs), batch_size):
            batch = curated_pairs[i:i + batch_size]
            files = []
            curated_metadata = {}
            
            try:
                for pair in batch:
                    content_path = pair['content_file']
                    metadata_path = pair['metadata_file']
                    
                    # Upload content file
                    files.append(('files', (
                        Path(content_path).name, 
                        open(content_path, 'rb'), 
                        'application/octet-stream'
                    )))
                    
                    # Load and include metadata
                    try:
                        with open(metadata_path, 'r', encoding='utf-8') as f:
                            metadata = json.load(f)
                        curated_metadata[Path(content_path).name] = metadata
                    except Exception as e:
                        print(f"Warning: Could not load metadata for {content_path}: {e}")
                
                # Prepare curated upload data
                data = {
                    'curated_upload': 'true',
                    'priority': '9',  # High priority for curated content
                    'curated_metadata': json.dumps(curated_metadata)
                }
                
                response = self.session.post(
                    f"{self.base_url}/upload/curated",  # Special endpoint for curated files
                    files=files,
                    data=data
                )
                
                # Fallback to regular upload if curated endpoint not available
                if response.status_code == 404:
                    response = self.session.post(
                        f"{self.base_url}/upload/files",
                        files=files,
                        data=data
                    )
                
                response.raise_for_status()
                results.append(response.json())
                
            except Exception as e:
                # Close files on error
                for _, file_tuple in files:
                    if hasattr(file_tuple[1], 'close'):
                        file_tuple[1].close()
                raise e
            finally:
                # Close files
                for _, file_tuple in files:
                    if hasattr(file_tuple[1], 'close'):
                        file_tuple[1].close()
        
        return results
    
    def upload_directory_chunked(self, directory_path: str, chunk_size: int = 50, 
                                 progress_callback=None) -> Dict:
        """Upload directory in chunks with progress tracking"""
        try:
            if progress_callback:
                progress_callback("Starte Verzeichnis-Upload...", 0)
            
            print(f"[DEBUG] Sende Directory Upload: {directory_path}, chunk_size: {chunk_size}")
            
            response = self.session.post(
                f"{self.base_url}/upload/directory",
                data={
                    "directory_path": directory_path,
                    "chunk_size": chunk_size
                },
                headers={'Content-Type': 'application/x-www-form-urlencoded'}
            )
            
            if progress_callback:
                progress_callback("Upload-Request gesendet", 50)
                
            response.raise_for_status()
            result = response.json()
            
            if progress_callback:
                progress_callback("Upload erfolgreich initiiert", 100)
                
            return result
            
        except Exception as e:
            print(f"[DEBUG] Upload-Fehler Details: {e}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_detail = e.response.text
                    print(f"[DEBUG] Server Response: {error_detail}")
                except:
                    print("[DEBUG] Konnte Server Response nicht lesen")
            if progress_callback:
                progress_callback(f"Upload-Fehler: {str(e)}", -1)
            raise
    
    def get_job_status(self, job_id: str) -> Dict:
        """Hole Job-Status"""
        response = self.session.get(f"{self.base_url}/jobs/{job_id}/status")
        response.raise_for_status()
        return response.json()
    
    def get_job_metrics(self, job_id: str) -> Dict:
        """Hole Job-Metriken"""
        response = self.session.get(f"{self.base_url}/jobs/{job_id}/metrics")
        response.raise_for_status()
        return response.json()
    
    def list_jobs(self, limit: int = 100) -> List[Dict]:
        """Liste alle Jobs"""
        response = self.session.get(f"{self.base_url}/jobs", params={"limit": limit})
        response.raise_for_status()
        return response.json()
    
    def cancel_job(self, job_id: str) -> Dict:
        """Storniere Job"""
        response = self.session.delete(f"{self.base_url}/jobs/{job_id}")
        response.raise_for_status()
        return response.json()
    
    def pause_job(self, job_id: str) -> Dict:
        """Pausiere Job (if supported by backend)"""
        response = self.session.post(f"{self.base_url}/jobs/{job_id}/pause")
        response.raise_for_status()
        return response.json()
    
    def resume_job(self, job_id: str) -> Dict:
        """Setze Job fort (if supported by backend)"""
        response = self.session.post(f"{self.base_url}/jobs/{job_id}/resume")
        response.raise_for_status()
        return response.json()

# Directory Analysis Utility
class DirectoryAnalyzer:
    """Analysiert Verzeichnisse für bessere Batch-Planung mit Unterstützung für kuratierte Dateien"""
    
    # Synchronisiert mit Backend supported_extensions (backend.py Zeile 4368-4383)
    SUPPORTED_EXTENSIONS = {
        # Dokumente
        '.pdf', '.doc', '.docx', '.odt', '.rtf',
        # Text
        '.txt', '.md', '.markdown', '.rst',
        # Strukturiert
        '.json', '.xml', '.yaml', '.yml', '.toml',
        # Tabellen
        '.csv', '.tsv', '.xlsx', '.xls', '.ods',
        # Web
        '.html', '.htm', '.xhtml',
        # Archive
        '.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz',
        '.tar.gz', '.tgz', '.tar.bz2', '.tbz2', '.tar.xz', '.txz'
    }
    
    @staticmethod
    def analyze_directory(directory_path: str) -> Dict[str, Any]:
        """Analysiert Verzeichnis und gibt Statistiken zurück"""
        path = Path(directory_path)
        
        if not path.exists() or not path.is_dir():
            return {"error": "Verzeichnis existiert nicht"}
        
        analysis = {
            "total_files": 0,
            "supported_files": 0,
            "curated_files": 0,
            "curated_pairs": [],
            "orphaned_metadata": [],
            "total_size": 0,
            "supported_size": 0,
            "curated_size": 0,
            "file_types": defaultdict(int),
            "size_by_type": defaultdict(int),
            "large_files": [],  # Files > 10MB
            "subdirectories": 0,
            "estimated_processing_time": 0,
            "recommended_batches": 1,
            "curation_impact_score": 0
        }
        
        try:
            # First pass: collect all files and identify metadata files
            all_files = list(path.rglob("*"))
            metadata_files = {}
            content_files = []
            
            for file_path in all_files:
                if file_path.is_file():
                    if file_path.name.endswith('_metadata.json'):
                        # Extract base name for pairing
                        base_name = file_path.name[:-14]  # Remove '_metadata.json'
                        metadata_files[base_name] = file_path
                    else:
                        content_files.append(file_path)
                elif file_path.is_dir() and file_path != path:
                    analysis["subdirectories"] += 1
            
            # Second pass: analyze content files and check for curation
            for file_path in content_files:
                analysis["total_files"] += 1
                file_size = file_path.stat().st_size
                analysis["total_size"] += file_size
                
                ext = file_path.suffix.lower()
                analysis["file_types"][ext] += 1
                analysis["size_by_type"][ext] += file_size
                
                if ext in DirectoryAnalyzer.SUPPORTED_EXTENSIONS:
                    analysis["supported_files"] += 1
                    analysis["supported_size"] += file_size
                    
                    # Check if this file has accompanying metadata (curated)
                    base_name = file_path.stem
                    is_curated = base_name in metadata_files
                    
                    if is_curated:
                        analysis["curated_files"] += 1
                        analysis["curated_size"] += file_size
                        
                        # Validate and parse metadata
                        metadata_info = DirectoryAnalyzer._analyze_metadata_file(metadata_files[base_name])
                        
                        analysis["curated_pairs"].append({
                            "content_file": str(file_path.relative_to(path)),
                            "metadata_file": str(metadata_files[base_name].relative_to(path)),
                            "size": file_size,
                            "metadata_valid": metadata_info["valid"],
                            "metadata_quality": metadata_info["quality_score"],
                            "rag_impact": metadata_info["rag_impact"],
                            "curator_info": metadata_info.get("curator", "Unknown")
                        })
                    
                    # Track large files (>10MB)
                    if file_size > 10 * 1024 * 1024:
                        analysis["large_files"].append({
                            "path": str(file_path.relative_to(path)),
                            "size": file_size,
                            "curated": is_curated
                        })
            
            # Check for orphaned metadata files
            for base_name, metadata_path in metadata_files.items():
                # Look for corresponding content file
                found_match = False
                for ext in DirectoryAnalyzer.SUPPORTED_EXTENSIONS:
                    potential_content = path / f"{base_name}{ext}"
                    if potential_content.exists():
                        found_match = True
                        break
                
                if not found_match:
                    analysis["orphaned_metadata"].append(str(metadata_path.relative_to(path)))
            
            # Estimate processing time with curation bonus
            base_time = analysis["supported_size"] // (1024 * 1024)  # 1s per MB
            curated_bonus = analysis["curated_files"] * 2  # Extra time for metadata processing
            analysis["estimated_processing_time"] = base_time + curated_bonus
            
            # Calculate recommended batch size (smaller for curated content)
            if analysis["supported_files"] > 100:
                batch_reduction = min(0.3, analysis["curated_files"] / analysis["supported_files"])
                base_batches = analysis["supported_files"] // 50
                analysis["recommended_batches"] = max(1, int(base_batches * (1 - batch_reduction)))
            
            # Calculate curation impact score
            if analysis["supported_files"] > 0:
                curation_ratio = analysis["curated_files"] / analysis["supported_files"]
                quality_avg = sum(pair["metadata_quality"] for pair in analysis["curated_pairs"]) / max(1, len(analysis["curated_pairs"]))
                analysis["curation_impact_score"] = int(curation_ratio * quality_avg * 100)
            
        except PermissionError:
            analysis["error"] = "Zugriff verweigert"
        except Exception as e:
            analysis["error"] = f"Fehler bei Analyse: {e}"
        
        return analysis
    
    @staticmethod
    def _analyze_metadata_file(metadata_path: Path) -> Dict[str, Any]:
        """Analysiert eine Metadaten-JSON-Datei"""
        result = {
            "valid": False,
            "quality_score": 0,
            "rag_impact": "unknown",
            "error": None
        }
        
        try:
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            # Validate required fields for RAG enhancement
            required_fields = ['title', 'description', 'keywords', 'curator']
            quality_indicators = ['summary', 'key_concepts', 'related_topics', 'importance_level', 'content_type', 'target_audience']
            
            # Check required fields
            has_required = all(field in metadata and metadata[field] for field in required_fields)
            
            if has_required:
                result["valid"] = True
                result["curator"] = metadata.get("curator", "Unknown")
                
                # Calculate quality score (0-100)
                score = 40  # Base score for valid metadata
                
                # Bonus points for quality indicators
                for indicator in quality_indicators:
                    if indicator in metadata and metadata[indicator]:
                        score += 10
                
                # Bonus for rich keyword sets
                keywords = metadata.get("keywords", [])
                if isinstance(keywords, list) and len(keywords) >= 5:
                    score += 10
                elif isinstance(keywords, str) and len(keywords.split(',')) >= 5:
                    score += 10
                
                # Bonus for detailed descriptions
                description = metadata.get("description", "")
                if len(description) > 200:
                    score += 10
                
                result["quality_score"] = min(100, score)
                
                # Determine RAG impact based on metadata richness
                if score >= 80:
                    result["rag_impact"] = "high"
                elif score >= 60:
                    result["rag_impact"] = "medium"
                else:
                    result["rag_impact"] = "low"
                
                # Extract additional useful info
                result["importance_level"] = metadata.get("importance_level", "normal")
                result["content_type"] = metadata.get("content_type", "document")
                result["keywords_count"] = len(keywords) if isinstance(keywords, list) else len(str(keywords).split(','))
                
            else:
                result["error"] = f"Missing required fields: {[f for f in required_fields if f not in metadata or not metadata[f]]}"
                
        except json.JSONDecodeError as e:
            result["error"] = f"Invalid JSON: {e}"
        except Exception as e:
            result["error"] = f"Error reading metadata: {e}"
        
        return result

# Resource Monitor
class ResourceMonitor:
    """System-Resource Monitoring für optimale Performance"""
    
    def __init__(self):
        self.cpu_history = deque(maxlen=60)  # 1 minute history
        self.memory_history = deque(maxlen=60)
        self.disk_history = deque(maxlen=60)
        self._monitoring = False
        self._monitor_thread = None
    
    def start_monitoring(self):
        """Startet Resource Monitoring"""
        if not self._monitoring:
            self._monitoring = True
            self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self._monitor_thread.start()
    
    def stop_monitoring(self):
        """Stoppt Resource Monitoring"""
        self._monitoring = False
    
    def _monitor_loop(self):
        """Monitoring Loop"""
        while self._monitoring:
            try:
                # CPU Usage
                cpu_percent = psutil.cpu_percent(interval=1)
                self.cpu_history.append(cpu_percent)
                
                # Memory Usage
                memory = psutil.virtual_memory()
                self.memory_history.append(memory.percent)
                
                # Disk I/O
                disk_io = psutil.disk_io_counters()
                if disk_io:
                    # Simple metric: read+write bytes per second
                    disk_activity = (disk_io.read_bytes + disk_io.write_bytes) / (1024 * 1024)  # MB
                    self.disk_history.append(min(100, disk_activity))  # Cap at 100 for display
                
            except Exception:
                pass
            
            time.sleep(1)
    
    def get_current_stats(self) -> Dict[str, Any]:
        """Aktuelle Resource-Statistiken"""
        return {
            "cpu_percent": self.cpu_history[-1] if self.cpu_history else 0,
            "memory_percent": self.memory_history[-1] if self.memory_history else 0,
            "disk_activity": self.disk_history[-1] if self.disk_history else 0,
            "cpu_avg": sum(self.cpu_history) / len(self.cpu_history) if self.cpu_history else 0,
            "memory_avg": sum(self.memory_history) / len(self.memory_history) if self.memory_history else 0,
            "recommended_workers": self._calculate_optimal_workers()
        }
    
    def _calculate_optimal_workers(self) -> int:
        """Berechnet optimale Anzahl paralleler Workers"""
        cpu_cores = psutil.cpu_count()
        current_cpu = self.cpu_history[-1] if self.cpu_history else 0
        current_memory = self.memory_history[-1] if self.memory_history else 0
        
        # Conservative approach
        if current_cpu > 80 or current_memory > 85:
            return max(1, cpu_cores // 4)
        elif current_cpu > 60 or current_memory > 70:
            return max(2, cpu_cores // 2)
        else:
            return min(cpu_cores, 8)  # Cap at 8 workers max

# Job Queue Manager
class JobQueueManager:
    """Verwaltet mehrere gleichzeitige Jobs mit Resource-Sharing"""
    
    def __init__(self, max_concurrent_jobs: int = 3):
        self.max_concurrent_jobs = max_concurrent_jobs
        self.active_jobs = {}
        self.job_queue = queue.Queue()
        self.completed_jobs = {}
        self.resource_monitor = ResourceMonitor()
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_concurrent_jobs)
        self._running = True
        
        self.resource_monitor.start_monitoring()
    
    def add_job(self, job_config: Dict[str, Any]) -> str:
        """Fügt neuen Job zur Warteschlange hinzu"""
        job_id = str(uuid.uuid4())
        job_config['job_id'] = job_id
        job_config['created_at'] = datetime.now()
        job_config['status'] = 'queued'
        job_config['priority'] = job_config.get('priority', 5)  # Default priority 5 (1-10)
        
        self.job_queue.put(job_config)
        return job_id
    
    def process_queue(self):
        """Verarbeitet Job-Warteschlange"""
        while self._running:
            try:
                # Check if we can start new jobs
                if len(self.active_jobs) < self.max_concurrent_jobs and not self.job_queue.empty():
                    job_config = self.job_queue.get_nowait()
                    
                    # Start job in executor
                    future = self._executor.submit(self._process_job, job_config)
                    self.active_jobs[job_config['job_id']] = {
                        'config': job_config,
                        'future': future,
                        'started_at': datetime.now()
                    }
                
                # Clean up completed jobs
                completed_job_ids = []
                for job_id, job_info in self.active_jobs.items():
                    if job_info['future'].done():
                        self.completed_jobs[job_id] = job_info
                        completed_job_ids.append(job_id)
                
                for job_id in completed_job_ids:
                    del self.active_jobs[job_id]
                
            except queue.Empty:
                pass
            except Exception as e:
                print(f"Error in job queue processing: {e}")
            
            time.sleep(0.5)
    
    def _process_job(self, job_config: Dict[str, Any]):
        """Verarbeitet einzelnen Job"""
        # This would integrate with the actual Covina API
        # For now, simulate processing
        job_id = job_config['job_id']
        
        try:
            job_config['status'] = 'processing'
            
            # Simulate work based on job type
            if job_config['type'] == 'directory':
                # Directory processing simulation
                time.sleep(job_config.get('estimated_time', 5))
            elif job_config['type'] == 'files':
                # File processing simulation  
                time.sleep(len(job_config.get('files', [])) * 0.5)
            
            job_config['status'] = 'completed'
            job_config['completed_at'] = datetime.now()
            
        except Exception as e:
            job_config['status'] = 'failed'
            job_config['error'] = str(e)
    
    def get_queue_status(self) -> Dict[str, Any]:
        """Status der Job-Warteschlange"""
        return {
            "active_jobs": len(self.active_jobs),
            "queued_jobs": self.job_queue.qsize(),
            "completed_jobs": len(self.completed_jobs),
            "max_concurrent": self.max_concurrent_jobs,
            "resource_stats": self.resource_monitor.get_current_stats()
        }
    
    def shutdown(self):
        """Shutdown Job Queue Manager"""
        self._running = False
        self.resource_monitor.stop_monitoring()
        self._executor.shutdown(wait=True)

# Enhanced Covina GUI
class EnhancedCovinaGUI:
    """Enhanced Hauptklasse für Covina GUI mit verbessertem Resource Management"""
    
    def __init__(self):
        self.root = tk.Tk()
        
        # Initialize new architecture components
        self.event_bus = EventBus()
        self.task_executor = TaskExecutor(max_workers=4)
        self.backend_service = CovinaBackendService(
            base_url="http://127.0.0.1:45678",  # Main Backend (Queries, DSGVO)
            ingestion_base_url="http://127.0.0.1:45679",  # ✅ NEW: Ingestion Backend (Upload)
            event_bus=self.event_bus,
            task_executor=self.task_executor,
            enable_websocket=False  # WebSocket deaktiviert - Backend hat keinen /ws/jobs Endpoint
        )
        
        # Legacy components (kept for gradual migration)
        self.api_client = CovinaAPIClient()  # Still used by some methods
        self.current_jobs = {}
        self.auto_refresh = True
        self.backend_online = False
        self._backend_offline_logged = False
        self._backend_reconnected = False
        
        # Progress Overlay
        self.progress_overlay = None
        
        # Register event handlers
        self._register_event_handlers()
        
        # Start backend service (health check loop + periodic job refresh)
        self.backend_service.start()
        
        # ✅ Directory Analysis Spinner State
        self._analysis_spinner_active = False
        self._analysis_spinner_chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        self._analysis_spinner_index = 0
        
        self.setup_gui()
        self.setup_styles()
        
        # Legacy backend check (will be replaced by backend_service health events)
        self.check_backend_connection()
    
    def _register_event_handlers(self):
        """Registriert Event-Handler für EventBus"""
        # Backend connection events
        self.event_bus.subscribe(EventType.BACKEND_CONNECTED, self._on_backend_connected)
        self.event_bus.subscribe(EventType.BACKEND_DISCONNECTED, self._on_backend_disconnected)
        self.event_bus.subscribe(EventType.BACKEND_ERROR, self._on_backend_error)
        
        # Job events
        self.event_bus.subscribe(EventType.JOB_CREATED, self._on_job_created)
        self.event_bus.subscribe(EventType.JOB_STATUS_CHANGED, self._on_job_status_changed)
        self.event_bus.subscribe(EventType.JOB_PROGRESS_UPDATE, self._on_job_progress_update)
        self.event_bus.subscribe(EventType.JOB_COMPLETED, self._on_job_completed)
        self.event_bus.subscribe(EventType.JOB_FAILED, self._on_job_failed)
        
        # Upload events
        self.event_bus.subscribe(EventType.UPLOAD_STARTED, self._on_upload_started)
        self.event_bus.subscribe(EventType.UPLOAD_PROGRESS, self._on_upload_progress)
        self.event_bus.subscribe(EventType.UPLOAD_FILE_COMPLETE, self._on_upload_file_complete)
        self.event_bus.subscribe(EventType.UPLOAD_BATCH_COMPLETE, self._on_upload_batch_complete)
        self.event_bus.subscribe(EventType.UPLOAD_FINISHED, self._on_upload_finished)
        self.event_bus.subscribe(EventType.UPLOAD_ERROR, self._on_upload_error)
        
        # Directory analysis events
        self.event_bus.subscribe(EventType.DIRECTORY_ANALYSIS_STARTED, self._on_directory_analysis_started)
        self.event_bus.subscribe(EventType.DIRECTORY_ANALYSIS_COMPLETE, self._on_directory_analysis_complete)
        self.event_bus.subscribe(EventType.DIRECTORY_ANALYSIS_ERROR, self._on_directory_analysis_error)
    
    # Event Handler Methods (to be called in main thread via self.after)
    def _on_backend_connected(self, event: Event):
        """Handler für Backend-Verbindung"""
        def update_ui():
            self.backend_online = True
            if not self._backend_reconnected:
                self._backend_reconnected = True
                print(f"✅ Backend verbunden: {event.data.get('url', 'unknown')}")
            self._update_status("✅ Backend verbunden", "success")
        
        self.root.after(0, update_ui)
    
    def _on_backend_disconnected(self, event: Event):
        """Handler für Backend-Trennung"""
        def update_ui():
            self.backend_online = False
            if not self._backend_offline_logged:
                self._backend_offline_logged = True
                print(f"❌ Backend getrennt: {event.data.get('error', 'unknown')}")
            self._update_status("❌ Backend nicht erreichbar", "error")
        
        self.root.after(0, update_ui)
    
    def _on_backend_error(self, event: Event):
        """Handler für Backend-Fehler"""
        def update_ui():
            error_msg = event.data.get('error', 'Unbekannter Fehler')
            print(f"⚠️ Backend-Fehler: {error_msg}")
            self._update_status(f"⚠️ Backend-Fehler: {error_msg}", "error")
        
        self.root.after(0, update_ui)
    
    def _on_job_created(self, event: Event):
        """Handler für Job-Erstellung"""
        def update_ui():
            job = event.data.get('job', {})
            job_id = job.get('job_id', 'unknown')
            print(f"🆕 Job erstellt: {job_id[:16]}...")
            # Jobs werden automatisch via list_jobs() aktualisiert
        
        self.root.after(0, update_ui)
    
    def _on_job_status_changed(self, event: Event):
        """Handler für Job-Status-Änderung (nur bei echten Änderungen)"""
        def update_ui():
            jobs = event.data.get('jobs', [])
            
            # Smart Polling: Ignoriere leere Listen (keine Änderungen)
            if not jobs:
                return
            
            self._update_jobs_treeview(jobs)
        
        self.root.after(0, update_ui)
    
    def _on_job_progress_update(self, event: Event):
        """Handler für Job-Fortschritt"""
        def update_ui():
            job_id = event.data.get('job_id', '')
            progress = event.data.get('progress', 0)
            # Update job in treeview (simplified - full implementation needed)
            print(f"🔄 Job {job_id[:16]}... Fortschritt: {progress}%")
        
        self.root.after(0, update_ui)
    
    def _on_job_completed(self, event: Event):
        """Handler für Job-Abschluss"""
        def update_ui():
            job_id = event.data.get('job_id', '')
            print(f"✅ Job abgeschlossen: {job_id[:16]}...")
            self._update_status(f"✅ Job {job_id[:16]}... abgeschlossen", "success")
            # Trigger job list refresh
            self.backend_service.list_jobs(limit=100)
        
        self.root.after(0, update_ui)
    
    def _on_job_failed(self, event: Event):
        """Handler für Job-Fehler"""
        def update_ui():
            job_id = event.data.get('job_id', '')
            error = event.data.get('error', 'Unbekannter Fehler')
            print(f"❌ Job fehlgeschlagen: {job_id[:16]}... - {error}")
            self._update_status(f"❌ Job {job_id[:16]}... fehlgeschlagen", "error")
        
        self.root.after(0, update_ui)
    
    def _on_upload_started(self, event: Event):
        """Handler für Upload-Start"""
        def update_ui():
            # Support both file_count and total_files keys
            file_count = event.data.get('file_count', event.data.get('total_files', 0))
            directory = event.data.get('directory', '')
            
            if directory:
                # Directory upload
                print(f"📤 Verzeichnis-Upload gestartet: {directory}")
                if self.progress_overlay and not self.progress_overlay.is_visible():
                    # Progress overlay might already be shown from analysis
                    self.progress_overlay.show(f"Verzeichnis-Upload", file_count if file_count > 0 else 100)
            else:
                # File upload
                print(f"📤 Upload gestartet: {file_count} Dateien")
                if self.progress_overlay:
                    self.progress_overlay.show(f"Datei-Upload ({file_count} Dateien)", file_count)
        
        self.root.after(0, update_ui)
    
    def _on_upload_progress(self, event: Event):
        """Handler für Upload-Fortschritt"""
        def update_ui():
            current = event.data.get('current', 0)
            total = event.data.get('total', 0)
            filename = event.data.get('filename', '')
            
            if self.progress_overlay:
                self.progress_overlay.update_overall_progress(current, total, f"Upload: {filename}")
        
        self.root.after(0, update_ui)
    
    def _on_upload_file_complete(self, event: Event):
        """Handler für Datei-Upload-Abschluss"""
        def update_ui():
            filename = event.data.get('filename', '')
            if self.progress_overlay:
                self.progress_overlay.log_success(f"✅ {filename} hochgeladen")
        
        self.root.after(0, update_ui)
    
    def _on_upload_batch_complete(self, event: Event):
        """Handler für Batch-Abschluss"""
        def update_ui():
            batch_num = event.data.get('batch', 0)
            if self.progress_overlay:
                self.progress_overlay.log_info(f"📦 Batch {batch_num} abgeschlossen")
        
        self.root.after(0, update_ui)
    
    def _on_upload_finished(self, event: Event):
        """Handler für Upload-Abschluss"""
        def update_ui():
            total_files = event.data.get('total_files', 0)
            print(f"✅ Upload abgeschlossen: {total_files} Dateien")
            
            if self.progress_overlay:
                self.progress_overlay.update_overall_progress(total_files, total_files, "✅ Upload abgeschlossen!")
                self.progress_overlay.log_success(f"✅ Alle {total_files} Dateien erfolgreich hochgeladen")
            
            self._update_status(f"✅ {total_files} Dateien hochgeladen", "success")
            
            # Trigger job list refresh
            self.backend_service.list_jobs(limit=100)
        
        self.root.after(0, update_ui)
    
    def _on_upload_error(self, event: Event):
        """Handler für Upload-Fehler"""
        def update_ui():
            error = event.data.get('error', 'Unbekannter Fehler')
            filename = event.data.get('filename', '')
            
            print(f"❌ Upload-Fehler: {filename} - {error}")
            
            if self.progress_overlay:
                self.progress_overlay.log_error(f"❌ {filename}: {error}")
            
            self._update_status(f"❌ Upload-Fehler: {error}", "error")
        
        self.root.after(0, update_ui)
    
    def _on_directory_analysis_started(self, event: Event):
        """Handler für Verzeichnis-Analyse-Start"""
        def update_ui():
            directory = event.data.get('path', event.data.get('directory', ''))
            dir_name = Path(directory).name if directory else "Verzeichnis"
            print(f"🔍 Analysiere Verzeichnis: {directory}")
            self._update_status(f"🔍 Analysiere {dir_name}... (kann bei großen Verzeichnissen einige Sekunden dauern)", "info")
            
            # ✅ Start animated spinner for visual feedback
            self._start_analysis_spinner()
        
        self.root.after(0, update_ui)
    
    def _on_directory_analysis_complete(self, event: Event):
        """Handler für Verzeichnis-Analyse-Abschluss"""
        def update_ui():
            # ✅ Stop animated spinner
            self._stop_analysis_spinner()
            
            analysis = event.data.get('analysis', {})
            supported_files = analysis.get('supported_files', 0)
            curated_files = analysis.get('curated_files', 0)
            
            print(f"✅ Analyse abgeschlossen: {supported_files} unterstützte Dateien ({curated_files} kuratiert)")
            
            # Update preview text
            self._display_directory_analysis(analysis)
            
            self._update_status(f"✅ Analyse: {supported_files} Dateien gefunden", "success")
            
            # Check if upload should be triggered (set by upload_directory_enhanced())
            if hasattr(self, '_pending_directory_upload') and self._pending_directory_upload:
                upload_config = self._pending_directory_upload
                self._pending_directory_upload = None  # Clear flag
                
                # Ask user to confirm upload
                directory_name = Path(upload_config['directory']).name
                confirm_message = f"""📁 VERZEICHNIS-UPLOAD STARTEN

Verzeichnis: {directory_name}
Unterstützte Dateien: {supported_files}
Kuratierte Dateien: {curated_files}
Chunk-Größe: {upload_config['chunk_size']}

Möchten Sie den Upload jetzt starten?"""
                
                if messagebox.askyesno("Upload bestätigen", confirm_message):
                    # Initialize progress overlay
                    self.progress_overlay = UploadProgressOverlay(self.root)
                    self.progress_overlay.show(
                        title=f"📂 Verzeichnis-Upload: {directory_name}",
                        total_files=supported_files
                    )
                    
                    # Trigger async upload
                    self.backend_service.upload_directory(
                        directory_path=upload_config['directory'],
                        chunk_size=upload_config['chunk_size']
                    )
                    
                    self.log_message(f"Upload gestartet: {directory_name} ({supported_files} Dateien)", "INFO")
                else:
                    self.log_message("Upload abgebrochen", "INFO")
        
        self.root.after(0, update_ui)
    
    def _on_directory_analysis_error(self, event: Event):
        """Handler für Verzeichnis-Analyse-Fehler"""
        def update_ui():
            # ✅ Stop animated spinner
            self._stop_analysis_spinner()
            
            error = event.data.get('error', 'Unbekannter Fehler')
            print(f"❌ Analyse-Fehler: {error}")
            self._update_status(f"❌ Analyse-Fehler: {error}", "error")
        
        self.root.after(0, update_ui)

    
    def setup_gui(self):
        """Enhanced GUI Setup mit verbesserter Navigation"""
        self.root.title("🏛️ Covina - Enhanced Document Processing System")
        self.root.geometry("1400x900")
        self.root.minsize(1200, 700)
        
        # Header mit Covina Branding
        header_frame = ttk.Frame(self.root, padding="10")
        header_frame.pack(fill=tk.X)
        
        # Left side: Title
        title_container = ttk.Frame(header_frame)
        title_container.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        title_label = ttk.Label(
            title_container,
            text="🏛️ Covina Document Processing",
            font=("Arial", 16, "bold")
        )
        title_label.pack(anchor=tk.W)
        
        # Covina Branding (rechtsbündig) - ohne Rahmen, große Schrift
        covina_btn = tk.Label(
            header_frame,
            text="COVINA",
            font=('Segoe UI', 16, 'bold'),
            foreground='#0066CC',
            cursor='hand2',
            padx=10,
            pady=5
        )
        covina_btn.pack(side=tk.RIGHT, padx=(5, 0))
        covina_btn.bind('<Button-1>', lambda e: self._show_about_covina())
        
        # Hover-Effekt für Covina Button
        def on_enter_covina(e):
            covina_btn.config(foreground='#004499')
        def on_leave_covina(e):
            covina_btn.config(foreground='#0066CC')
        
        covina_btn.bind('<Enter>', on_enter_covina)
        covina_btn.bind('<Leave>', on_leave_covina)
        
        # Create main notebook for organized tabs
        self.notebook = ttk.Notebook(self.root, padding="5")
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Upload Tab
        self.upload_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.upload_frame, text="📁 Upload & Processing")
        self.setup_upload_tab()
        
        # Job Management Tab
        self.jobs_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.jobs_frame, text="📊 Job Management")
        self.setup_jobs_tab()
        
        # Resource Monitor Tab
        self.resources_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.resources_frame, text="💻 Resources")
        self.setup_resources_tab()
        
        # Settings Tab
        self.settings_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.settings_frame, text="⚙️ Settings")
        self.setup_settings_tab()
        
        # Status Bar
        self.setup_status_bar()
    
    def setup_styles(self):
        """Enhanced TTK Styles"""
        style = ttk.Style()
        
        # Status Styles
        style.configure("Success.TLabel", foreground="green", font=('Arial', 9, 'bold'))
        style.configure("Error.TLabel", foreground="red", font=('Arial', 9, 'bold'))
        style.configure("Warning.TLabel", foreground="orange", font=('Arial', 9, 'bold'))
        style.configure("Info.TLabel", foreground="blue", font=('Arial', 9))
        
        # Button Styles
        style.configure("Upload.TButton", font=('Arial', 10, 'bold'))
        style.configure("Action.TButton", font=('Arial', 9, 'bold'))
        
        # Progress Styles
        style.configure("Success.Horizontal.TProgressbar", troughcolor="lightgray", background="green")
        style.configure("Warning.Horizontal.TProgressbar", troughcolor="lightgray", background="orange")
        style.configure("Error.Horizontal.TProgressbar", troughcolor="lightgray", background="red")
    
    def setup_upload_tab(self):
        """Enhanced Upload Tab mit Directory Preview"""
        main_frame = ttk.Frame(self.upload_frame, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Left panel - Upload controls
        upload_panel = ttk.LabelFrame(main_frame, text="📁 Upload Controls", padding="10")
        upload_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        # Files section
        files_section = ttk.LabelFrame(upload_panel, text="Einzelne Dateien", padding="10")
        files_section.pack(fill=tk.X, pady=(0, 10))
        
        self.selected_files_var = tk.StringVar(value="Keine Dateien ausgewählt")
        files_label = ttk.Label(files_section, textvariable=self.selected_files_var, foreground="gray")
        files_label.pack(anchor=tk.W, pady=(0, 5))
        
        files_buttons = ttk.Frame(files_section)
        files_buttons.pack(fill=tk.X)
        
        ttk.Button(
            files_buttons,
            text="📁 Dateien auswählen",
            command=self.select_files,
            style="Upload.TButton"
        ).pack(side=tk.LEFT)
        
        ttk.Button(
            files_buttons,
            text="🚀 Upload",
            command=self.upload_files_enhanced,
            style="Upload.TButton"
        ).pack(side=tk.LEFT, padx=(10, 0))
        
        # Directory section with preview
        dir_section = ttk.LabelFrame(upload_panel, text="Verzeichnis mit Vorschau", padding="10")
        dir_section.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        
        # Directory selection
        dir_select_frame = ttk.Frame(dir_section)
        dir_select_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.selected_dir_var = tk.StringVar(value="Kein Verzeichnis ausgewählt")
        dir_label = ttk.Label(dir_select_frame, textvariable=self.selected_dir_var, foreground="gray")
        dir_label.pack(anchor=tk.W, pady=(0, 5))
        
        dir_buttons = ttk.Frame(dir_select_frame)
        dir_buttons.pack(fill=tk.X)
        
        ttk.Button(
            dir_buttons,
            text="📂 Verzeichnis auswählen",
            command=self.select_directory_enhanced
        ).pack(side=tk.LEFT)
        
        ttk.Button(
            dir_buttons,
            text="🔍 Vorschau",
            command=self.preview_directory,
            state="disabled"
        ).pack(side=tk.LEFT, padx=(10, 0))
        
        self.preview_button = dir_buttons.winfo_children()[-1]  # Store reference
        
        # Directory preview area
        preview_frame = ttk.LabelFrame(dir_section, text="Verzeichnis-Analyse", padding="5")
        preview_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        
        self.preview_text = scrolledtext.ScrolledText(
            preview_frame,
            height=8,
            wrap=tk.WORD,
            font=('Consolas', 9),
            state='disabled'
        )
        self.preview_text.pack(fill=tk.BOTH, expand=True)
        
        # Upload options
        options_frame = ttk.LabelFrame(upload_panel, text="Upload-Optionen", padding="10")
        options_frame.pack(fill=tk.X, pady=(10, 0))
        
        # Batch size
        batch_frame = ttk.Frame(options_frame)
        batch_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(batch_frame, text="Batch-Größe:").pack(side=tk.LEFT)
        self.batch_size_var = tk.StringVar(value="50")
        batch_spinbox = ttk.Spinbox(
            batch_frame,
            from_=10,
            to=200,
            textvariable=self.batch_size_var,
            width=10
        )
        batch_spinbox.pack(side=tk.LEFT, padx=(10, 0))
        
        # Priority
        priority_frame = ttk.Frame(options_frame)
        priority_frame.pack(fill=tk.X, pady=(5, 0))
        
        ttk.Label(priority_frame, text="Priorität:").pack(side=tk.LEFT)
        self.priority_var = tk.StringVar(value="5")
        priority_scale = ttk.Scale(
            priority_frame,
            from_=1,
            to=10,
            orient=tk.HORIZONTAL,
            variable=self.priority_var
        )
        priority_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(10, 0))
        
        priority_label = ttk.Label(priority_frame, textvariable=self.priority_var)
        priority_label.pack(side=tk.LEFT, padx=(10, 0))
        
        # Upload buttons for directory
        upload_buttons_frame = ttk.Frame(options_frame)
        upload_buttons_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(
            upload_buttons_frame,
            text="🚀 Verzeichnis verarbeiten",
            command=self.upload_directory_enhanced,
            style="Upload.TButton",
            state="disabled"
        ).pack(side=tk.LEFT)
        
        self.upload_dir_button = upload_buttons_frame.winfo_children()[-1]
        
        # Curated files only button
        ttk.Button(
            upload_buttons_frame,
            text="🎯 Nur kuratierte Dateien",
            command=self.upload_curated_only,
            style="Upload.TButton",
            state="disabled"
        ).pack(side=tk.LEFT, padx=(10, 0))
        
        self.curated_only_button = upload_buttons_frame.winfo_children()[-1]
        
        # Curated files status
        self.curated_status_var = tk.StringVar(value="")
        curated_status_label = ttk.Label(options_frame, textvariable=self.curated_status_var, font=('Arial', 9))
        curated_status_label.pack(pady=(5, 0))
        
        # Right panel - Queue status
        self.setup_queue_status_panel(main_frame)
    
    def setup_queue_status_panel(self, parent):
        """Queue Status Panel"""
        queue_panel = ttk.LabelFrame(parent, text="📋 Job-Warteschlange", padding="10")
        queue_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=False, padx=(10, 0))
        queue_panel.configure(width=300)
        
        # Current queue stats
        stats_frame = ttk.Frame(queue_panel)
        stats_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.queue_stats_var = tk.StringVar(value="Lade Status...")
        stats_label = ttk.Label(stats_frame, textvariable=self.queue_stats_var, font=('Arial', 9))
        stats_label.pack()
        
        # Active jobs list
        active_frame = ttk.LabelFrame(queue_panel, text="Aktive Jobs", padding="5")
        active_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        self.active_jobs_listbox = tk.Listbox(active_frame, height=6, font=('Consolas', 8))
        self.active_jobs_listbox.pack(fill=tk.BOTH, expand=True)
        
        # Resource usage
        resource_frame = ttk.LabelFrame(queue_panel, text="System-Auslastung", padding="5")
        resource_frame.pack(fill=tk.X)
        
        # CPU Progress Bar
        ttk.Label(resource_frame, text="CPU:").grid(row=0, column=0, sticky=tk.W)
        self.cpu_progress = ttk.Progressbar(resource_frame, length=150, mode='determinate')
        self.cpu_progress.grid(row=0, column=1, padx=(5, 0), pady=2)
        self.cpu_label = ttk.Label(resource_frame, text="0%", width=6)
        self.cpu_label.grid(row=0, column=2, padx=(5, 0))
        
        # Memory Progress Bar  
        ttk.Label(resource_frame, text="RAM:").grid(row=1, column=0, sticky=tk.W)
        self.memory_progress = ttk.Progressbar(resource_frame, length=150, mode='determinate')
        self.memory_progress.grid(row=1, column=1, padx=(5, 0), pady=2)
        self.memory_label = ttk.Label(resource_frame, text="0%", width=6)
        self.memory_label.grid(row=1, column=2, padx=(5, 0))
        
        # Workers info
        self.workers_label = ttk.Label(resource_frame, text="Empf. Workers: -", font=('Arial', 8))
        self.workers_label.grid(row=2, column=0, columnspan=3, pady=(5, 0))
    
    def setup_jobs_tab(self):
        """Enhanced Jobs Management Tab"""
        main_frame = ttk.Frame(self.jobs_frame, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Control Panel
        control_panel = ttk.Frame(main_frame)
        control_panel.pack(fill=tk.X, pady=(0, 10))
        
        # Refresh and control buttons
        ttk.Button(
            control_panel,
            text="🔄 Aktualisieren",
            command=self.refresh_jobs_manual,
            style="Action.TButton"
        ).pack(side=tk.LEFT)
        
        ttk.Button(
            control_panel,
            text="⏸️ Alle pausieren",
            command=self.pause_all_jobs,
            style="Action.TButton"
        ).pack(side=tk.LEFT, padx=(10, 0))
        
        ttk.Button(
            control_panel,
            text="▶️ Alle fortsetzen",
            command=self.resume_all_jobs,
            style="Action.TButton"
        ).pack(side=tk.LEFT, padx=(10, 0))
        
        ttk.Button(
            control_panel,
            text="🗑️ Abgeschlossene löschen",
            command=self.cleanup_completed_jobs,
            style="Action.TButton"
        ).pack(side=tk.LEFT, padx=(10, 0))
        
        # Auto-refresh control
        self.auto_refresh_var = tk.BooleanVar(value=True)
        auto_refresh_cb = ttk.Checkbutton(
            control_panel,
            text="Auto-Refresh",
            variable=self.auto_refresh_var,
            command=self.toggle_auto_refresh
        )
        auto_refresh_cb.pack(side=tk.RIGHT)
        
        # Jobs Treeview with enhanced columns
        tree_frame = ttk.Frame(main_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)
        
        # Treeview
        columns = ("status", "type", "files", "progress", "priority", "created", "eta")
        self.jobs_tree = ttk.Treeview(
            tree_frame,
            columns=columns,
            show="tree headings",
            height=15
        )
        
        # Column configuration
        self.jobs_tree.heading("#0", text="Job ID")
        self.jobs_tree.heading("status", text="Status")
        self.jobs_tree.heading("type", text="Typ")
        self.jobs_tree.heading("files", text="Dateien")
        self.jobs_tree.heading("progress", text="Fortschritt")
        self.jobs_tree.heading("priority", text="Priorität")
        self.jobs_tree.heading("created", text="Erstellt")
        self.jobs_tree.heading("eta", text="ETA")
        
        self.jobs_tree.column("#0", width=120)
        self.jobs_tree.column("status", width=100)
        self.jobs_tree.column("type", width=80)
        self.jobs_tree.column("files", width=80)
        self.jobs_tree.column("progress", width=120)
        self.jobs_tree.column("priority", width=70)
        self.jobs_tree.column("created", width=120)
        self.jobs_tree.column("eta", width=100)
        
        # Scrollbars
        v_scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.jobs_tree.yview)
        h_scrollbar = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL, command=self.jobs_tree.xview)
        self.jobs_tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        self.jobs_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        v_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        h_scrollbar.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        # Bind events
        self.jobs_tree.bind("<<TreeviewSelect>>", self.on_job_select)
        self.jobs_tree.bind("<Double-1>", self.show_job_details)
        self.jobs_tree.bind("<Button-3>", self.show_job_context_menu)  # Right-click
        
        # Job Details Panel
        details_panel = ttk.LabelFrame(main_frame, text="📋 Job Details & Actions", padding="10")
        details_panel.pack(fill=tk.X, pady=(10, 0))
        
        # Job info display
        info_frame = ttk.Frame(details_panel)
        info_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.selected_job_info = tk.StringVar(value="Kein Job ausgewählt")
        ttk.Label(info_frame, textvariable=self.selected_job_info, font=('Arial', 10)).pack(anchor=tk.W)
        
        # Action buttons
        action_frame = ttk.Frame(details_panel)
        action_frame.pack(fill=tk.X)
        
        self.pause_button = ttk.Button(
            action_frame,
            text="⏸️ Pausieren",
            command=self.pause_selected_job,
            state="disabled"
        )
        self.pause_button.pack(side=tk.LEFT)
        
        self.resume_button = ttk.Button(
            action_frame,
            text="▶️ Fortsetzen",
            command=self.resume_selected_job,
            state="disabled"
        )
        self.resume_button.pack(side=tk.LEFT, padx=(10, 0))
        
        self.cancel_button = ttk.Button(
            action_frame,
            text="❌ Stornieren",
            command=self.cancel_selected_job,
            state="disabled"
        )
        self.cancel_button.pack(side=tk.LEFT, padx=(10, 0))
        
        self.details_button = ttk.Button(
            action_frame,
            text="📊 Details",
            command=self.show_detailed_metrics,
            state="disabled"
        )
        self.details_button.pack(side=tk.LEFT, padx=(10, 0))
        
        # Priority adjustment
        priority_frame = ttk.Frame(action_frame)
        priority_frame.pack(side=tk.RIGHT)
        
        ttk.Label(priority_frame, text="Priorität:").pack(side=tk.LEFT)
        
        self.job_priority_var = tk.StringVar(value="5")
        self.priority_spinbox = ttk.Spinbox(
            priority_frame,
            from_=1,
            to=10,
            textvariable=self.job_priority_var,
            width=5,
            command=self.update_job_priority,
            state="disabled"
        )
        self.priority_spinbox.pack(side=tk.LEFT, padx=(5, 0))
    
    # Job management methods
    def refresh_jobs_manual(self):
        """Manual job refresh using CovinaBackendService"""
        # Trigger async job list retrieval via Service
        # Result will be delivered via EventBus (JOB_STATUS_CHANGED)
        self.backend_service.list_jobs(limit=200)
        self.log_message("Job-Refresh angefordert", "INFO")
    
    def _update_jobs_treeview(self, jobs):
        """Update jobs treeview with enhanced information"""
        # Clear existing items
        for item in self.jobs_tree.get_children():
            self.jobs_tree.delete(item)
        
        # Sort jobs by creation time (newest first)
        jobs_sorted = sorted(jobs, key=lambda x: x.get('created_at', ''), reverse=True)
        
        # Add jobs to treeview
        for job in jobs_sorted:
            job_id_short = job['job_id'][:12] + "..."
            status = job['status']
            
            # Determine job type with curated indicators
            description = job.get('description', '').lower()
            if "kuratierte dateien" in description or "curated_only" in job.get('type', ''):
                job_type = "🎯 Kuratiert"
            elif "kuratiert" in description:
                job_type = "📁+ Kuratiert"
            elif "directory" in description:
                job_type = "📁 Dir"
            else:
                job_type = "📄 Files"
            
            file_count = job.get('file_count', 0)
            processed = job.get('processed_files', 0)
            
            # Progress calculation
            if file_count > 0:
                progress_pct = (processed / file_count) * 100
                progress_text = f"{processed}/{file_count} ({progress_pct:.0f}%)"
            else:
                progress_text = "Wartend..."
            
            # Priority with curated boost indicator
            base_priority = job.get('priority', 5)
            curated_count = job.get('curated_files', 0)
            
            if curated_count > 0:
                priority_display = f"{base_priority}⭐"  # Star for curated content
            else:
                priority_display = str(base_priority)
            
            # Time formatting
            try:
                created_dt = datetime.fromisoformat(job['created_at'].replace('Z', '+00:00'))
                created_str = created_dt.strftime("%H:%M:%S")
            except:
                created_str = "Unbekannt"
            
            # ETA calculation (rough estimate)
            eta = "Unbekannt"
            if status == "processing" and file_count > 0 and processed > 0:
                files_remaining = file_count - processed
                avg_time_per_file = 2  # seconds (rough estimate)
                eta_seconds = files_remaining * avg_time_per_file
                if eta_seconds < 3600:
                    eta = f"{eta_seconds//60}m {eta_seconds%60}s"
                else:
                    eta = f"{eta_seconds//3600}h {(eta_seconds%3600)//60}m"
            
            # Status icons
            status_icons = {
                "pending": "⏳",
                "processing": "🔄",
                "completed": "✅",
                "failed": "❌",
                "cancelled": "🚫",
                "paused": "⏸️"
            }
            
            status_display = f"{status_icons.get(status, '❓')} {status.title()}"
            
            # Insert item with appropriate tags
            tags = [status]
            if curated_count > 0:
                tags.append("curated")
            
            item_id = self.jobs_tree.insert(
                "",
                "end",
                text=job_id_short,
                values=(status_display, job_type, file_count, progress_text, priority_display, created_str, eta),
                tags=tuple(tags)
            )
            
            # Store full job data
            self.current_jobs[item_id] = job
        
        # Configure status-based colors
        self.jobs_tree.tag_configure("completed", foreground="green")
        self.jobs_tree.tag_configure("failed", foreground="red")
        self.jobs_tree.tag_configure("processing", foreground="blue")
        self.jobs_tree.tag_configure("cancelled", foreground="gray")
        self.jobs_tree.tag_configure("paused", foreground="orange")
        
        # Configure curated content highlighting
        self.jobs_tree.tag_configure("curated", background="#fff8dc", foreground="#b8860b")  # Light golden background
    
    def on_job_select(self, event):
        """Handle job selection in treeview"""
        selection = self.jobs_tree.selection()
        if selection:
            item = selection[0]
            job = self.current_jobs.get(item)
            
            if job:
                # Update job info display
                job_info = f"Job: {job['job_id'][:16]}... | Status: {job['status']} | Dateien: {job.get('file_count', 0)}"
                self.selected_job_info.set(job_info)
                
                # Update priority display
                self.job_priority_var.set(str(job.get('priority', 5)))
                
                # Enable/disable buttons based on job status
                status = job['status']
                
                if status in ['pending', 'processing']:
                    self.pause_button.configure(state="normal")
                    self.cancel_button.configure(state="normal")
                else:
                    self.pause_button.configure(state="disabled")
                    self.cancel_button.configure(state="disabled")
                
                if status == 'paused':
                    self.resume_button.configure(state="normal")
                else:
                    self.resume_button.configure(state="disabled")
                
                self.details_button.configure(state="normal")
                self.priority_spinbox.configure(state="normal")
                
                self.selected_job = job
            else:
                self._clear_job_selection()
        else:
            self._clear_job_selection()
    
    def _clear_job_selection(self):
        """Clear job selection"""
        self.selected_job_info.set("Kein Job ausgewählt")
        self.pause_button.configure(state="disabled")
        self.resume_button.configure(state="disabled")
        self.cancel_button.configure(state="disabled")
        self.details_button.configure(state="disabled")
        self.priority_spinbox.configure(state="disabled")
        self.selected_job = None
    
    def pause_selected_job(self):
        """Pause selected job"""
        if hasattr(self, 'selected_job') and self.selected_job:
            job_id = self.selected_job['job_id']
            self._pause_job(job_id)
    
    def resume_selected_job(self):
        """Resume selected job"""
        if hasattr(self, 'selected_job') and self.selected_job:
            job_id = self.selected_job['job_id']
            self._resume_job(job_id)
    
    def cancel_selected_job(self):
        """Cancel selected job with confirmation"""
        if not hasattr(self, 'selected_job') or not self.selected_job:
            return
        
        job_id = self.selected_job['job_id']
        
        if messagebox.askyesno(
            "Job stornieren",
            f"Job {job_id[:16]}... wirklich stornieren?"
        ):
            self._cancel_job(job_id)
    
    def _pause_job(self, job_id):
        """Pause job using CovinaBackendService"""
        # Trigger async pause via Service
        # Result will be delivered via EventBus
        self.backend_service.pause_job(job_id)
        self.log_message(f"Job-Pause angefordert: {job_id[:8]}...", "INFO")
    
    def _resume_job(self, job_id):
        """Resume job using CovinaBackendService"""
        # Trigger async resume via Service
        # Result will be delivered via EventBus
        self.backend_service.resume_job(job_id)
        self.log_message(f"Job-Resume angefordert: {job_id[:8]}...", "INFO")
    
    def _cancel_job(self, job_id):
        """Cancel job using CovinaBackendService"""
        # Trigger async cancel via Service
        # Result will be delivered via EventBus
        self.backend_service.cancel_job(job_id)
        self.log_message(f"Job-Cancel angefordert: {job_id[:8]}...", "INFO")
    
    def pause_all_jobs(self):
        """Pause all active jobs"""
        active_jobs = [job for job in self.current_jobs.values() 
                      if job['status'] in ['pending', 'processing']]
        
        if not active_jobs:
            messagebox.showinfo("Info", "Keine aktiven Jobs zum Pausieren gefunden.")
            return
        
        if messagebox.askyesno(
            "Alle Jobs pausieren",
            f"{len(active_jobs)} aktive Jobs pausieren?"
        ):
            for job in active_jobs:
                self._pause_job(job['job_id'])
    
    def resume_all_jobs(self):
        """Resume all paused jobs"""
        paused_jobs = [job for job in self.current_jobs.values() 
                      if job['status'] == 'paused']
        
        if not paused_jobs:
            messagebox.showinfo("Info", "Keine pausierten Jobs zum Fortsetzen gefunden.")
            return
        
        if messagebox.askyesno(
            "Alle Jobs fortsetzen",
            f"{len(paused_jobs)} pausierte Jobs fortsetzen?"
        ):
            for job in paused_jobs:
                self._resume_job(job['job_id'])
    
    def cleanup_completed_jobs(self):
        """Remove completed/failed jobs from display"""
        completed_jobs = [job for job in self.current_jobs.values() 
                         if job['status'] in ['completed', 'failed', 'cancelled']]
        
        if not completed_jobs:
            messagebox.showinfo("Info", "Keine abgeschlossenen Jobs zum Löschen gefunden.")
            return
        
        if messagebox.askyesno(
            "Abgeschlossene Jobs löschen",
            f"{len(completed_jobs)} abgeschlossene Jobs aus der Anzeige entfernen?"
        ):
            # This would typically call backend to delete job records
            # For now, just refresh to update display
            self.refresh_jobs_manual()
            self.log_message(f"{len(completed_jobs)} abgeschlossene Jobs bereinigt", "INFO")
    
    def update_job_priority(self):
        """Update priority for selected job"""
        if hasattr(self, 'selected_job') and self.selected_job:
            new_priority = int(self.job_priority_var.get())
            job_id = self.selected_job['job_id']
            
            # This would typically call backend API to update priority
            self.log_message(f"Job-Priorität geändert: {job_id[:8]}... -> Priorität {new_priority}", "INFO")
    
    def show_job_context_menu(self, event):
        """Show context menu for job operations"""
        # Select item under cursor
        item = self.jobs_tree.identify_row(event.y)
        if item:
            self.jobs_tree.selection_set(item)
            
            # Create context menu
            context_menu = tk.Menu(self.root, tearoff=0)
            context_menu.add_command(label="📊 Details anzeigen", command=self.show_detailed_metrics)
            context_menu.add_separator()
            context_menu.add_command(label="⏸️ Pausieren", command=self.pause_selected_job)
            context_menu.add_command(label="▶️ Fortsetzen", command=self.resume_selected_job)
            context_menu.add_command(label="❌ Stornieren", command=self.cancel_selected_job)
            
            context_menu.tk_popup(event.x_root, event.y_root)
    
    def toggle_auto_refresh(self):
        """Toggle auto-refresh functionality"""
        self.auto_refresh = self.auto_refresh_var.get()
        status = "aktiviert" if self.auto_refresh else "deaktiviert"
        self.log_message(f"Auto-Refresh {status}", "INFO")
    
    def show_detailed_metrics(self):
        """Show detailed job metrics (placeholder)"""
        if hasattr(self, 'selected_job') and self.selected_job:
            job_id = self.selected_job['job_id']
            self.log_message(f"Zeige Details für Job: {job_id[:8]}...", "INFO")
            # Implementation would show detailed metrics window
        else:
            messagebox.showwarning("Warnung", "Bitte wählen Sie zuerst einen Job aus.")
    
    def show_job_details(self, event):
        """Handle double-click to show job details"""
        self.show_detailed_metrics()
    
    def setup_resources_tab(self):
        """Advanced Resources Monitoring Tab"""
        main_frame = ttk.Frame(self.resources_frame, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # System Overview Panel
        overview_panel = ttk.LabelFrame(main_frame, text="🖥️ System-Übersicht", padding="10")
        overview_panel.pack(fill=tk.X, pady=(0, 10))
        
        # Resource gauges
        gauges_frame = ttk.Frame(overview_panel)
        gauges_frame.pack(fill=tk.X)
        
        # CPU Gauge
        cpu_frame = ttk.Frame(gauges_frame)
        cpu_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        ttk.Label(cpu_frame, text="💻 CPU-Auslastung", font=('Arial', 10, 'bold')).pack()
        self.cpu_gauge = ttk.Progressbar(
            cpu_frame, 
            length=200, 
            mode='determinate',
            style="Success.Horizontal.TProgressbar"
        )
        self.cpu_gauge.pack(pady=5)
        self.cpu_detail_var = tk.StringVar(value="CPU: 0% (0 Kerne)")
        ttk.Label(cpu_frame, textvariable=self.cpu_detail_var, font=('Arial', 9)).pack()
        
        # Memory Gauge
        memory_frame = ttk.Frame(gauges_frame)
        memory_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        ttk.Label(memory_frame, text="🧠 Arbeitsspeicher", font=('Arial', 10, 'bold')).pack()
        self.memory_gauge = ttk.Progressbar(
            memory_frame, 
            length=200, 
            mode='determinate',
            style="Success.Horizontal.TProgressbar"
        )
        self.memory_gauge.pack(pady=5)
        self.memory_detail_var = tk.StringVar(value="RAM: 0% (0/0 GB)")
        ttk.Label(memory_frame, textvariable=self.memory_detail_var, font=('Arial', 9)).pack()
        
        # Disk Gauge
        disk_frame = ttk.Frame(gauges_frame)
        disk_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        ttk.Label(disk_frame, text="💾 Festplatte I/O", font=('Arial', 10, 'bold')).pack()
        self.disk_gauge = ttk.Progressbar(
            disk_frame, 
            length=200, 
            mode='determinate',
            style="Success.Horizontal.TProgressbar"
        )
        self.disk_gauge.pack(pady=5)
        self.disk_detail_var = tk.StringVar(value="I/O: 0 MB/s")
        ttk.Label(disk_frame, textvariable=self.disk_detail_var, font=('Arial', 9)).pack()
        
        # Performance Metrics Panel
        metrics_panel = ttk.LabelFrame(main_frame, text="📊 Performance-Metriken", padding="10")
        metrics_panel.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Metrics notebook
        metrics_notebook = ttk.Notebook(metrics_panel)
        metrics_notebook.pack(fill=tk.BOTH, expand=True)
        
        # Real-time metrics tab
        realtime_frame = ttk.Frame(metrics_notebook)
        metrics_notebook.add(realtime_frame, text="📈 Echtzeit")
        
        # Historical metrics tab
        history_frame = ttk.Frame(metrics_notebook)
        metrics_notebook.add(history_frame, text="📅 Verlauf")
        
        # Recommendations tab
        recommendations_frame = ttk.Frame(metrics_notebook)
        metrics_notebook.add(recommendations_frame, text="💡 Empfehlungen")
        
        # Real-time metrics content
        realtime_text = scrolledtext.ScrolledText(
            realtime_frame, 
            height=10, 
            wrap=tk.WORD, 
            font=('Consolas', 9)
        )
        realtime_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.realtime_metrics_text = realtime_text
        
        # Historical metrics content
        history_text = scrolledtext.ScrolledText(
            history_frame, 
            height=10, 
            wrap=tk.WORD, 
            font=('Consolas', 9)
        )
        history_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.history_metrics_text = history_text
        
        # Recommendations content
        recommendations_text = scrolledtext.ScrolledText(
            recommendations_frame, 
            height=10, 
            wrap=tk.WORD, 
            font=('Arial', 10)
        )
        recommendations_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.recommendations_text = recommendations_text
        
        # Control Panel
        control_panel = ttk.LabelFrame(main_frame, text="⚙️ Steuerung", padding="10")
        control_panel.pack(fill=tk.X)
        
        # Worker configuration
        worker_frame = ttk.Frame(control_panel)
        worker_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(worker_frame, text="Maximale Worker:").pack(side=tk.LEFT)
        self.max_workers_var = tk.StringVar(value="3")
        worker_spinbox = ttk.Spinbox(
            worker_frame,
            from_=1,
            to=16,
            textvariable=self.max_workers_var,
            width=5,
            command=self.update_max_workers
        )
        worker_spinbox.pack(side=tk.LEFT, padx=(10, 0))
        
        # Auto-scaling toggle
        self.auto_scaling_var = tk.BooleanVar(value=True)
        auto_scaling_cb = ttk.Checkbutton(
            worker_frame,
            text="Auto-Skalierung",
            variable=self.auto_scaling_var,
            command=self.toggle_auto_scaling
        )
        auto_scaling_cb.pack(side=tk.LEFT, padx=(20, 0))
        
        # Resource limits
        limits_frame = ttk.Frame(control_panel)
        limits_frame.pack(fill=tk.X, pady=(5, 0))
        
        ttk.Label(limits_frame, text="CPU-Limit:").pack(side=tk.LEFT)
        self.cpu_limit_var = tk.StringVar(value="80")
        cpu_limit_spinbox = ttk.Spinbox(
            limits_frame,
            from_=50,
            to=100,
            textvariable=self.cpu_limit_var,
            width=5
        )
        cpu_limit_spinbox.pack(side=tk.LEFT, padx=(10, 0))
        ttk.Label(limits_frame, text="%").pack(side=tk.LEFT)
        
        ttk.Label(limits_frame, text="RAM-Limit:").pack(side=tk.LEFT, padx=(20, 0))
        self.memory_limit_var = tk.StringVar(value="85")
        memory_limit_spinbox = ttk.Spinbox(
            limits_frame,
            from_=60,
            to=95,
            textvariable=self.memory_limit_var,
            width=5
        )
        memory_limit_spinbox.pack(side=tk.LEFT, padx=(10, 0))
        ttk.Label(limits_frame, text="%").pack(side=tk.LEFT)
        
        # Start resource monitoring updates
        self.update_resource_displays()
    
    def update_resource_displays(self):
        """Update resource monitoring displays"""
        try:
            # Get current system stats
            cpu_percent = psutil.cpu_percent(interval=None)
            memory = psutil.virtual_memory()
            disk_io = psutil.disk_io_counters()
            
            # Update gauges
            self.cpu_gauge['value'] = cpu_percent
            if cpu_percent > 80:
                self.cpu_gauge.configure(style="Error.Horizontal.TProgressbar")
            elif cpu_percent > 60:
                self.cpu_gauge.configure(style="Warning.Horizontal.TProgressbar")
            else:
                self.cpu_gauge.configure(style="Success.Horizontal.TProgressbar")
            
            self.memory_gauge['value'] = memory.percent
            if memory.percent > 85:
                self.memory_gauge.configure(style="Error.Horizontal.TProgressbar")
            elif memory.percent > 70:
                self.memory_gauge.configure(style="Warning.Horizontal.TProgressbar")
            else:
                self.memory_gauge.configure(style="Success.Horizontal.TProgressbar")
            
            # Calculate disk I/O rate (simplified)
            disk_activity = 0
            if disk_io and hasattr(self, '_last_disk_io'):
                time_diff = 1.0  # Assuming 1 second intervals
                bytes_diff = (disk_io.read_bytes + disk_io.write_bytes) - self._last_disk_io
                disk_activity = min(100, (bytes_diff / (1024 * 1024)) / time_diff)  # MB/s, capped at 100 for display
            
            if disk_io:
                self._last_disk_io = disk_io.read_bytes + disk_io.write_bytes
            
            self.disk_gauge['value'] = disk_activity
            
            # Update detail labels
            cpu_cores = psutil.cpu_count()
            self.cpu_detail_var.set(f"CPU: {cpu_percent:.1f}% ({cpu_cores} Kerne)")
            
            memory_total_gb = memory.total / (1024**3)
            memory_used_gb = memory.used / (1024**3)
            self.memory_detail_var.set(f"RAM: {memory.percent:.1f}% ({memory_used_gb:.1f}/{memory_total_gb:.1f} GB)")
            
            self.disk_detail_var.set(f"I/O: {disk_activity:.1f} MB/s")
            
            # Update real-time metrics text
            current_time = datetime.now().strftime("%H:%M:%S")
            
            # Get job count from current_jobs (legacy job tracking)
            active_jobs_count = len([j for j in self.current_jobs.values() if j.get('status') in ['pending', 'processing']])
            completed_jobs_count = len([j for j in self.current_jobs.values() if j.get('status') == 'completed'])
            
            metrics_content = f"""⏰ {current_time} - SYSTEM-METRIKEN
{'='*50}

🖥️  CPU-Auslastung: {cpu_percent:.1f}%
    - Kerne verfügbar: {cpu_cores}
    - Durchschnitt (1min): {cpu_percent:.1f}%
    
🧠 Arbeitsspeicher: {memory.percent:.1f}%
    - Verwendet: {memory_used_gb:.2f} GB
    - Verfügbar: {memory.available / (1024**3):.2f} GB
    - Gesamt: {memory_total_gb:.2f} GB
    
💾 Festplatte:
    - I/O-Rate: {disk_activity:.1f} MB/s
    - Lesen: {disk_io.read_count if disk_io else 0:,} Operationen
    - Schreiben: {disk_io.write_count if disk_io else 0:,} Operationen
    
📊 JOB STATUS:
    - Aktive Jobs: {active_jobs_count}
    - Abgeschlossen: {completed_jobs_count}
    - Task Executor: {self.task_executor.max_workers} Workers

📈 EMPFEHLUNGEN:
"""
            
            # Add recommendations based on current metrics
            recommendations = []
            
            if cpu_percent > 85:
                recommendations.append("⚠️ Hohe CPU-Auslastung - Reduziere gleichzeitige Jobs")
            elif cpu_percent < 30 and active_jobs_count > 0:
                recommendations.append("✅ CPU unterausgelastet - Mehr Jobs können parallel verarbeitet werden")
            
            if memory.percent > 90:
                recommendations.append("⚠️ Kritischer Speichermangel - Pausiere nicht-essentielle Jobs")
            elif memory.percent > 80:
                recommendations.append("⚠️ Hohe Speicherauslastung - Überwache Speicherverbrauch")
            
            if disk_activity > 80:
                recommendations.append("⚠️ Hohe Festplatten-Aktivität - I/O-intensive Jobs staffeln")
            
            if not recommendations:
                recommendations.append("✅ Alle Ressourcen im optimalen Bereich")
            
            metrics_content += "\n".join(f"    {rec}" for rec in recommendations)
            
            # Update metrics display
            self.realtime_metrics_text.configure(state='normal')
            self.realtime_metrics_text.delete('1.0', tk.END)
            self.realtime_metrics_text.insert('1.0', metrics_content)
            self.realtime_metrics_text.configure(state='disabled')
            
            # Update recommendations tab
            self.recommendations_text.configure(state='normal')
            self.recommendations_text.delete('1.0', tk.END)
            
            recommendations_content = f"""💡 PERFORMANCE-EMPFEHLUNGEN
{'='*40}

Basierend auf aktuellen Systemmetriken:

"""
            
            # Detailed recommendations
            if cpu_percent > 80:
                recommendations_content += """🔴 HOHE CPU-AUSLASTUNG
• Reduziere die Anzahl gleichzeitiger Jobs
• Prüfe auf CPU-intensive Prozesse
• Erwäge kleinere Batch-Größen
• Nutze Pausenfunktion bei kritischen Lasten

"""
            
            if memory.percent > 85:
                recommendations_content += """🟡 HOHE SPEICHERAUSLASTUNG  
• Überwache große Dateien in der Verarbeitung
• Reduziere Batch-Größen für speicherintensive Operationen
• Schließe nicht benötigte Anwendungen
• Erwäge Speicher-Upgrade bei dauerhaft hoher Auslastung

"""
            
            if active_jobs_count > 5:
                recommendations_content += """📋 VIELE AKTIVE JOBS
• Prüfe Job-Prioritäten und passe sie an
• Erwäge Batch-Verarbeitung für ähnliche Jobs
• Überwache Verarbeitungszeiten pro Job
• Nutze Pause-Funktion für nicht-kritische Jobs

"""
            
            if cpu_percent < 50 and memory.percent < 70:
                recommendations_content += """✅ OPTIMALE LEISTUNG
• System läuft im optimalen Bereich
• Kapazität für zusätzliche Jobs verfügbar
• Erwäge höhere Parallelisierung
• Nutze Auto-Skalierung für dynamische Anpassung

"""
            
            # Calculate recommended workers based on current metrics
            cpu_cores = psutil.cpu_count()
            if cpu_percent > 80 or memory.percent > 85:
                recommended_workers = max(1, cpu_cores // 4)
            elif cpu_percent > 60 or memory.percent > 70:
                recommended_workers = max(2, cpu_cores // 2)
            else:
                recommended_workers = min(cpu_cores, 8)
            
            recommendations_content += f"""

⚙️ AKTUELLE EINSTELLUNGEN:
• Max. Worker: {self.max_workers_var.get()}
• CPU-Limit: {self.cpu_limit_var.get()}%
• RAM-Limit: {self.memory_limit_var.get()}%
• Auto-Skalierung: {'Aktiviert' if self.auto_scaling_var.get() else 'Deaktiviert'}

🎯 OPTIMIERUNGSVORSCHLÄGE:
• Batch-Größe: {max(10, min(100, int(50 * (1 - cpu_percent/100))))} (empfohlen)
• Worker-Anzahl: {recommended_workers} (empfohlen basierend auf CPU: {cpu_cores} Kerne)
• Verarbeitungsmodus: {'Konservativ' if cpu_percent > 70 else 'Aggressiv'} (aktuell optimal)
"""
            
            self.recommendations_text.insert('1.0', recommendations_content)
            self.recommendations_text.configure(state='disabled')
            
        except Exception as e:
            print(f"Resource monitoring error: {e}")
        
        # Schedule next update
        self.root.after(2000, self.update_resource_displays)  # Update every 2 seconds
    
    def update_max_workers(self):
        """Update maximum worker count"""
        try:
            new_max = int(self.max_workers_var.get())
            # Update TaskExecutor max workers (if possible - currently not supported)
            # For now, just log the change
            self.log_message(f"Max. Worker auf {new_max} gesetzt (benötigt TaskExecutor-Neustart)", "INFO")
        except ValueError:
            pass
    
    def toggle_auto_scaling(self):
        """Toggle auto-scaling functionality"""
        enabled = self.auto_scaling_var.get()
        status = "aktiviert" if enabled else "deaktiviert"
        self.log_message(f"Auto-Skalierung {status}", "INFO")
    
    def setup_settings_tab(self):
        """Settings Configuration Tab"""
        main_frame = ttk.Frame(self.settings_frame, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Backend Configuration
        backend_frame = ttk.LabelFrame(main_frame, text="🌐 Backend-Konfiguration", padding="10")
        backend_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(backend_frame, text="Backend URL:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.backend_url_var = tk.StringVar(value="http://127.0.0.1:45678")
        backend_entry = ttk.Entry(backend_frame, textvariable=self.backend_url_var, width=40)
        backend_entry.grid(row=0, column=1, padx=(10, 0), pady=5, sticky=tk.W)
        
        ttk.Button(
            backend_frame,
            text="🔗 Verbinden",
            command=self.reconnect_backend
        ).grid(row=0, column=2, padx=(10, 0), pady=5)
        
        # Processing Settings  
        processing_frame = ttk.LabelFrame(main_frame, text="⚙️ Verarbeitungseinstellungen", padding="10")
        processing_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Default batch size
        ttk.Label(processing_frame, text="Standard Batch-Größe:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.default_batch_var = tk.StringVar(value="50")
        batch_spinbox = ttk.Spinbox(
            processing_frame,
            from_=10,
            to=500,
            textvariable=self.default_batch_var,
            width=10
        )
        batch_spinbox.grid(row=0, column=1, padx=(10, 0), pady=5, sticky=tk.W)
        
        # Auto-retry settings
        ttk.Label(processing_frame, text="Wiederholungsversuche:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.retry_count_var = tk.StringVar(value="3")
        retry_spinbox = ttk.Spinbox(
            processing_frame,
            from_=0,
            to=10,
            textvariable=self.retry_count_var,
            width=10
        )
        retry_spinbox.grid(row=1, column=1, padx=(10, 0), pady=5, sticky=tk.W)
        
        # Timeout settings
        ttk.Label(processing_frame, text="Request Timeout (s):").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.timeout_var = tk.StringVar(value="30")
        timeout_spinbox = ttk.Spinbox(
            processing_frame,
            from_=10,
            to=300,
            textvariable=self.timeout_var,
            width=10
        )
        timeout_spinbox.grid(row=2, column=1, padx=(10, 0), pady=5, sticky=tk.W)
        
        # UI Settings
        ui_frame = ttk.LabelFrame(main_frame, text="🎨 Benutzeroberfläche", padding="10")
        ui_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Theme selection (placeholder)
        ttk.Label(ui_frame, text="Design:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.theme_var = tk.StringVar(value="Standard")
        theme_combo = ttk.Combobox(
            ui_frame,
            textvariable=self.theme_var,
            values=["Standard", "Dunkel", "Hell"],
            state="readonly",
            width=15
        )
        theme_combo.grid(row=0, column=1, padx=(10, 0), pady=5, sticky=tk.W)
        
        # Auto-refresh interval
        ttk.Label(ui_frame, text="Auto-Refresh (s):").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.refresh_interval_var = tk.StringVar(value="5")
        refresh_spinbox = ttk.Spinbox(
            ui_frame,
            from_=1,
            to=60,
            textvariable=self.refresh_interval_var,
            width=10
        )
        refresh_spinbox.grid(row=1, column=1, padx=(10, 0), pady=5, sticky=tk.W)
        
        # Log level
        ttk.Label(ui_frame, text="Log-Level:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.log_level_var = tk.StringVar(value="INFO")
        log_combo = ttk.Combobox(
            ui_frame,
            textvariable=self.log_level_var,
            values=["DEBUG", "INFO", "WARNING", "ERROR"],
            state="readonly",
            width=15
        )
        log_combo.grid(row=2, column=1, padx=(10, 0), pady=5, sticky=tk.W)
        
        # Action Buttons
        action_frame = ttk.Frame(main_frame)
        action_frame.pack(fill=tk.X, pady=(20, 0))
        
        ttk.Button(
            action_frame,
            text="💾 Einstellungen speichern",
            command=self.save_settings,
            style="Action.TButton"
        ).pack(side=tk.LEFT)
        
        ttk.Button(
            action_frame,
            text="🔄 Zurücksetzen",
            command=self.reset_settings,
            style="Action.TButton"
        ).pack(side=tk.LEFT, padx=(10, 0))
        
        ttk.Button(
            action_frame,
            text="📊 System-Info",
            command=self.show_system_info,
            style="Action.TButton"
        ).pack(side=tk.RIGHT)
    
    def reconnect_backend(self):
        """Reconnect to backend with new URL"""
        new_url = self.backend_url_var.get()
        self.api_client.base_url = new_url
        self.log_message(f"Backend URL geändert: {new_url}", "INFO")
        self.check_backend_connection()
    
    def save_settings(self):
        """Save current settings to file"""
        settings = {
            'backend_url': self.backend_url_var.get(),
            'default_batch_size': int(self.default_batch_var.get()),
            'retry_count': int(self.retry_count_var.get()),
            'timeout': int(self.timeout_var.get()),
            'theme': self.theme_var.get(),
            'refresh_interval': int(self.refresh_interval_var.get()),
            'log_level': self.log_level_var.get(),
            'max_workers': int(self.max_workers_var.get()),
            'auto_scaling': self.auto_scaling_var.get(),
            'cpu_limit': int(self.cpu_limit_var.get()),
            'memory_limit': int(self.memory_limit_var.get())
        }
        
        try:
            import json
            with open('covina_gui_settings.json', 'w') as f:
                json.dump(settings, f, indent=2)
            self.log_message("Einstellungen gespeichert", "SUCCESS")
            messagebox.showinfo("Erfolg", "Einstellungen wurden gespeichert.")
        except Exception as e:
            self.log_message(f"Fehler beim Speichern: {e}", "ERROR")
            messagebox.showerror("Fehler", f"Fehler beim Speichern: {e}")
    
    def reset_settings(self):
        """Reset settings to defaults"""
        if messagebox.askyesno("Zurücksetzen", "Alle Einstellungen auf Standard zurücksetzen?"):
            self.backend_url_var.set("http://127.0.0.1:45678")
            self.default_batch_var.set("50")
            self.retry_count_var.set("3")
            self.timeout_var.set("30")
            self.theme_var.set("Standard")
            self.refresh_interval_var.set("5")
            self.log_level_var.set("INFO")
            self.max_workers_var.set("3")
            self.auto_scaling_var.set(True)
            self.cpu_limit_var.set("80")
            self.memory_limit_var.set("85")
            
            self.log_message("Einstellungen zurückgesetzt", "INFO")
    
    def show_system_info(self):
        """Show detailed system information"""
        try:
            import platform
            
            # Collect system info
            system_info = f"""🖥️ SYSTEM-INFORMATION
{'='*50}

Betriebssystem: {platform.system()} {platform.release()}
Prozessor: {platform.processor() or 'Unbekannt'}
Architektur: {platform.architecture()[0]}
Hostname: {platform.node()}
Python-Version: {platform.python_version()}

💻 HARDWARE:
CPU-Kerne: {psutil.cpu_count()} ({psutil.cpu_count(logical=False)} physisch)
RAM gesamt: {psutil.virtual_memory().total / (1024**3):.2f} GB
Festplatten: {len(psutil.disk_partitions())} Partitionen

📊 AKTUELLE AUSLASTUNG:
CPU: {psutil.cpu_percent()}%
RAM: {psutil.virtual_memory().percent}%
"""
            
            # Show in new window
            info_window = tk.Toplevel(self.root)
            info_window.title("🖥️ System-Information")
            info_window.geometry("600x400")
            info_window.transient(self.root)
            
            text_widget = scrolledtext.ScrolledText(
                info_window,
                wrap=tk.WORD,
                font=('Consolas', 10),
                state='normal'
            )
            text_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            text_widget.insert('1.0', system_info)
            text_widget.configure(state='disabled')
            
        except Exception as e:
            messagebox.showerror("Fehler", f"Fehler beim Abrufen der System-Info: {e}")
    
    def setup_status_bar(self):
        """Enhanced Status Bar"""
        self.status_bar = ttk.Frame(self.root)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=2)
        
        self.status_var = tk.StringVar(value="Bereit")
        status_label = ttk.Label(self.status_bar, textvariable=self.status_var)
        status_label.pack(side=tk.LEFT)
        
        # Backend connection indicator
        self.backend_status_var = tk.StringVar(value="🔍 Backend prüfen...")
        backend_label = ttk.Label(self.status_bar, textvariable=self.backend_status_var)
        backend_label.pack(side=tk.RIGHT, padx=(0, 10))
        
        # Time display
        self.time_var = tk.StringVar()
        time_label = ttk.Label(self.status_bar, textvariable=self.time_var, font=('Arial', 9))
        time_label.pack(side=tk.RIGHT)
        
        self.update_time()
    
    def select_directory_enhanced(self):
        """Enhanced Directory Selection mit Analyse"""
        directory = filedialog.askdirectory(title="Verzeichnis auswählen")
        
        if directory:
            self.selected_directory = directory
            self.selected_dir_var.set(Path(directory).name)
            
            # Enable preview button
            self.preview_button.configure(state="normal")
            
            self.log_message(f"Verzeichnis ausgewählt: {directory}", "INFO")
        else:
            self.selected_directory = None
            self.selected_dir_var.set("Kein Verzeichnis ausgewählt")
            self.preview_button.configure(state="disabled")
    
    def preview_directory(self):
        """Verzeichnis-Vorschau und Analyse"""
        if not hasattr(self, 'selected_directory') or not self.selected_directory:
            return
        
        def analyze():
            try:
                self.preview_text.configure(state='normal')
                self.preview_text.delete('1.0', tk.END)
                self.preview_text.insert(tk.END, "🔍 Analysiere Verzeichnis...\n")
                self.preview_text.configure(state='disabled')
                
                analysis = DirectoryAnalyzer.analyze_directory(self.selected_directory)
                
                if "error" in analysis:
                    result_text = f"❌ Fehler: {analysis['error']}\n"
                else:
                    # Format analysis results
                    result_text = f"""📊 VERZEICHNIS-ANALYSE
{'='*40}

📁 Dateien gesamt: {analysis['total_files']:,}
✅ Unterstützte Dateien: {analysis['supported_files']:,}
📏 Gesamtgröße: {analysis['total_size'] / (1024*1024):.1f} MB
📏 Unterstützte Dateien: {analysis['supported_size'] / (1024*1024):.1f} MB

⏱️  Geschätzte Verarbeitungszeit: {analysis['estimated_processing_time']:,} Sekunden
🔄 Empfohlene Batches: {analysis['recommended_batches']}

📋 DATEITYPEN:
{'-'*20}
"""
                    
                    for ext, count in sorted(analysis['file_types'].items(), key=lambda x: x[1], reverse=True)[:10]:
                        size_mb = analysis['size_by_type'][ext] / (1024*1024)
                        supported = "✅" if ext in DirectoryAnalyzer.SUPPORTED_EXTENSIONS else "❌"
                        result_text += f"{supported} {ext:<8} {count:>6} Dateien ({size_mb:>7.1f} MB)\n"
                    
                    # Show curation information
                    if analysis.get('curated_files', 0) > 0:
                        result_text += f"\n🎯 KURATIERTE DATEIEN:\n{'-'*25}\n"
                        result_text += f"✨ Kuratierte Dateien: {analysis['curated_files']} von {analysis['supported_files']}\n"
                        result_text += f"📊 Kuration-Impact-Score: {analysis['curation_impact_score']}/100\n"
                        result_text += f"💎 Kuratierte Größe: {analysis['curated_size'] / (1024*1024):.1f} MB\n\n"
                        
                        result_text += f"📋 KURATIERTE DATEIEN-PAARE:\n{'-'*35}\n"
                        for pair in analysis['curated_pairs'][:5]:
                            quality_icon = "🟢" if pair['metadata_quality'] >= 80 else "🟡" if pair['metadata_quality'] >= 60 else "🔴"
                            impact_icon = {"high": "🚀", "medium": "⚡", "low": "📄"}.get(pair['rag_impact'], "❓")
                            result_text += f"{quality_icon}{impact_icon} {Path(pair['content_file']).name:<30} (Q:{pair['metadata_quality']}, {pair['curator_info']})\n"
                        
                        if len(analysis['curated_pairs']) > 5:
                            result_text += f"... und {len(analysis['curated_pairs'])-5} weitere kuratierte Dateien\n"
                    
                    if len(analysis.get('orphaned_metadata', [])) > 0:
                        result_text += f"\n⚠️  VERWAISTE METADATEN:\n{'-'*28}\n"
                        for orphaned in analysis['orphaned_metadata'][:3]:
                            result_text += f"❓ {orphaned}\n"
                        if len(analysis['orphaned_metadata']) > 3:
                            result_text += f"... und {len(analysis['orphaned_metadata'])-3} weitere\n"
                    
                    if len(analysis['large_files']) > 0:
                        result_text += f"\n⚠️  GROSSE DATEIEN (>10MB):\n{'-'*30}\n"
                        for large_file in analysis['large_files'][:5]:
                            size_mb = large_file['size'] / (1024*1024)
                            curated_icon = "🎯" if large_file.get('curated', False) else "📄"
                            result_text += f"{curated_icon} {large_file['path']:<35} ({size_mb:.1f} MB)\n"
                        
                        if len(analysis['large_files']) > 5:
                            result_text += f"... und {len(analysis['large_files'])-5} weitere große Dateien\n"
                
                # Update UI in main thread
                self.root.after(0, self._update_preview_text, result_text)
                
                # Enable upload buttons if files found
                if analysis.get('supported_files', 0) > 0:
                    self.root.after(0, lambda: self.upload_dir_button.configure(state="normal"))
                
                # Enable curated-only button if curated files found
                curated_count = analysis.get('curated_files', 0)
                if curated_count > 0:
                    self.root.after(0, lambda: self.curated_only_button.configure(state="normal"))
                    status_text = f"🎯 {curated_count} kuratierte Dateien erkannt (Score: {analysis.get('curation_impact_score', 0)})"
                    self.root.after(0, lambda: self.curated_status_var.set(status_text))
                else:
                    self.root.after(0, lambda: self.curated_only_button.configure(state="disabled"))
                    self.root.after(0, lambda: self.curated_status_var.set(""))
                
            except Exception as e:
                error_text = f"❌ Fehler bei Analyse: {e}\n"
                self.root.after(0, self._update_preview_text, error_text)
        
        # Run analysis in background thread
        threading.Thread(target=analyze, daemon=True).start()
    
    def _display_directory_analysis(self, analysis: Dict[str, Any]):
        """Displays directory analysis results in preview text (main thread only)"""
        if "error" in analysis:
            result_text = f"❌ Fehler: {analysis['error']}\n"
        else:
            # Format analysis results
            result_text = f"""📊 VERZEICHNIS-ANALYSE
{'='*40}

📁 Dateien gesamt: {analysis['total_files']:,}
✅ Unterstützte Dateien: {analysis['supported_files']:,}
📏 Gesamtgröße: {analysis['total_size'] / (1024*1024):.1f} MB
📏 Unterstützte Dateien: {analysis['supported_size'] / (1024*1024):.1f} MB

⏱️  Geschätzte Verarbeitungszeit: {analysis['estimated_processing_time']:,} Sekunden
🔄 Empfohlene Batches: {analysis['recommended_batches']}

📋 DATEITYPEN:
{'-'*20}
"""
            
            for ext, count in sorted(analysis['file_types'].items(), key=lambda x: x[1], reverse=True)[:10]:
                size_mb = analysis['size_by_type'][ext] / (1024*1024)
                supported = "✅" if ext in DirectoryAnalyzer.SUPPORTED_EXTENSIONS else "❌"
                result_text += f"{supported} {ext:<8} {count:>6} Dateien ({size_mb:>7.1f} MB)\n"
            
            # Show curation information
            if analysis.get('curated_files', 0) > 0:
                result_text += f"\n🎯 KURATIERTE DATEIEN:\n{'-'*25}\n"
                result_text += f"✨ Kuratierte Dateien: {analysis['curated_files']} von {analysis['supported_files']}\n"
                result_text += f"📊 Kuration-Impact-Score: {analysis['curation_impact_score']}/100\n"
                result_text += f"💎 Kuratierte Größe: {analysis['curated_size'] / (1024*1024):.1f} MB\n\n"
                
                result_text += f"📋 KURATIERTE DATEIEN-PAARE:\n{'-'*35}\n"
                for pair in analysis['curated_pairs'][:5]:
                    quality_icon = "🟢" if pair['metadata_quality'] >= 80 else "🟡" if pair['metadata_quality'] >= 60 else "🔴"
                    impact_icon = {"high": "🚀", "medium": "⚡", "low": "📄"}.get(pair['rag_impact'], "❓")
                    result_text += f"{quality_icon}{impact_icon} {Path(pair['content_file']).name:<30} (Q:{pair['metadata_quality']}, {pair['curator_info']})\n"
                
                if len(analysis['curated_pairs']) > 5:
                    result_text += f"... und {len(analysis['curated_pairs'])-5} weitere kuratierte Dateien\n"
            
            if len(analysis.get('orphaned_metadata', [])) > 0:
                result_text += f"\n⚠️  VERWAISTE METADATEN:\n{'-'*28}\n"
                for orphaned in analysis['orphaned_metadata'][:3]:
                    result_text += f"❓ {orphaned}\n"
                if len(analysis['orphaned_metadata']) > 3:
                    result_text += f"... und {len(analysis['orphaned_metadata'])-3} weitere\n"
            
            if len(analysis['large_files']) > 0:
                result_text += f"\n⚠️  GROSSE DATEIEN (>10MB):\n{'-'*30}\n"
                for large_file in analysis['large_files'][:5]:
                    size_mb = large_file['size'] / (1024*1024)
                    curated_icon = "🎯" if large_file.get('curated', False) else "📄"
                    result_text += f"{curated_icon} {large_file['path']:<35} ({size_mb:.1f} MB)\n"
                
                if len(analysis['large_files']) > 5:
                    result_text += f"... und {len(analysis['large_files'])-5} weitere große Dateien\n"
        
        # Update preview text
        self._update_preview_text(result_text)
        
        # Enable upload buttons if files found
        if analysis.get('supported_files', 0) > 0:
            self.upload_dir_button.configure(state="normal")
        
        # Enable curated-only button if curated files found
        curated_count = analysis.get('curated_files', 0)
        if curated_count > 0:
            self.curated_only_button.configure(state="normal")
            status_text = f"🎯 {curated_count} kuratierte Dateien erkannt (Score: {analysis.get('curation_impact_score', 0)})"
            self.curated_status_var.set(status_text)
        else:
            self.curated_only_button.configure(state="disabled")
            self.curated_status_var.set("")
    
    def _update_preview_text(self, text):
        """Updates preview text (main thread only)"""
        self.preview_text.configure(state='normal')
        self.preview_text.delete('1.0', tk.END)
        self.preview_text.insert('1.0', text)
        self.preview_text.configure(state='disabled')
    
    def select_files(self):
        """Enhanced file selection with size preview inkl. Archive"""
        files = filedialog.askopenfilenames(
            title="Dokumente auswählen",
            filetypes=[
                ("PDF files", "*.pdf"),
                ("Word documents", "*.docx *.doc"),
                ("Text files", "*.txt *.rtf"),
                ("Markdown files", "*.md *.markdown"),
                ("OpenDocument", "*.odt"),
                ("Archive files", "*.zip *.tar *.tar.gz *.tgz *.rar *.7z"),
                ("All supported", "*.pdf *.docx *.doc *.txt *.rtf *.odt *.md *.markdown *.zip *.tar *.gz"),
                ("All files", "*.*")
            ]
        )
        
        if files:
            self.selected_files = list(files)
            
            # Separate archives and documents
            archive_extensions = {'.zip', '.tar', '.tar.gz', '.tgz', '.rar', '.7z', '.gz'}
            archives = [f for f in self.selected_files if any(f.lower().endswith(ext) for ext in archive_extensions)]
            documents = [f for f in self.selected_files if f not in archives]
            
            total_size = sum(Path(f).stat().st_size for f in files if Path(f).exists())
            
            size_mb = total_size / (1024 * 1024)
            status_text = f"{len(files)} Dateien ({size_mb:.1f} MB)"
            if archives:
                status_text += f" - 📦 {len(archives)} Archiv(e)"
            
            self.selected_files_var.set(status_text)
            
            # Show file details in log
            file_details = []
            for file_path in files[:5]:  # Show first 5
                if Path(file_path).exists():
                    size = Path(file_path).stat().st_size / (1024 * 1024)
                    icon = "📦" if any(file_path.lower().endswith(ext) for ext in archive_extensions) else "📄"
                    file_details.append(f"{icon} {Path(file_path).name} ({size:.1f}MB)")
            
            if len(files) > 5:
                file_details.append(f"... und {len(files) - 5} weitere")
            
            details_msg = f"Dateien ausgewählt: {'; '.join(file_details)}"
            if archives:
                details_msg += f"\n📦 {len(archives)} Archive werden automatisch extrahiert"
            
            self.log_message(details_msg, "INFO")
        else:
            self.selected_files = []
            self.selected_files_var.set("Keine Dateien ausgewählt")
    
    def upload_files_enhanced(self):
        """Enhanced file upload using CovinaBackendService"""
        if not hasattr(self, 'selected_files') or not self.selected_files:
            messagebox.showwarning("Warnung", "Bitte wählen Sie zuerst Dateien aus.")
            return
        
        batch_size = int(self.batch_size_var.get())
        total_files = len(self.selected_files)
        
        # Initialize progress overlay
        self.progress_overlay = UploadProgressOverlay(self.root)
        self.progress_overlay.show(
            title=f"📄 Datei-Upload: {total_files} Dateien",
            total_files=total_files
        )
        
        # Trigger async upload via Service
        # Progress will be delivered via EventBus (UPLOAD_* events)
        self.backend_service.upload_files(
            file_paths=self.selected_files,
            batch_size=batch_size
        )
        
        self.log_message(f"Upload gestartet: {total_files} Dateien (Batch-Größe: {batch_size})", "INFO")
        
        # Reset selection
        self.selected_files = []
        self.selected_files_var.set("Keine Dateien ausgewählt")
    
    def upload_directory_enhanced(self):
        """Enhanced directory upload using CovinaBackendService"""
        if not hasattr(self, 'selected_directory') or not self.selected_directory:
            messagebox.showwarning("Warnung", "Bitte wählen Sie zuerst ein Verzeichnis aus.")
            return
        
        batch_size = int(self.batch_size_var.get())
        
        # Set flag to trigger upload after analysis
        self._pending_directory_upload = {
            'directory': self.selected_directory,
            'chunk_size': batch_size
        }
        
        # Trigger async directory analysis via Service
        # Analysis result will be delivered via DIRECTORY_ANALYSIS_COMPLETE event
        # Upload will be triggered automatically in _on_directory_analysis_complete()
        self.backend_service.analyze_directory(self.selected_directory)
        
        self.log_message(f"Verzeichnis-Analyse gestartet: {Path(self.selected_directory).name}", "INFO")
    
    def upload_curated_only(self):
        """Upload only curated files from the selected directory"""
        if not hasattr(self, 'selected_directory') or not self.selected_directory:
            messagebox.showwarning("Warnung", "Bitte wählen Sie zuerst ein Verzeichnis aus.")
            return
        
        # Analyze directory for curated files
        analysis = DirectoryAnalyzer.analyze_directory(self.selected_directory)
        
        if "error" in analysis:
            messagebox.showerror("Fehler", f"Verzeichnis-Analyse fehlgeschlagen: {analysis['error']}")
            return
        
        curated_count = analysis.get('curated_files', 0)
        if curated_count == 0:
            messagebox.showinfo("Info", "Keine kuratierten Dateien im ausgewählten Verzeichnis gefunden.")
            return
        
        # Confirm curated-only upload
        impact_score = analysis.get('curation_impact_score', 0)
        orphaned = len(analysis.get('orphaned_metadata', []))
        
        confirm_message = f"""🎯 NUR KURATIERTE DATEIEN VERARBEITEN

Gefundene kuratierte Dateien: {curated_count}
Kuration-Impact-Score: {impact_score}/100
Verwaiste Metadaten: {orphaned}

Dies wird nur die Dateien mit begleitenden *_metadata.json verarbeiten.
Alle anderen Dateien werden ignoriert.

Fortfahren?"""
        
        if not messagebox.askyesno("Nur kuratierte Dateien", confirm_message):
            return
        
        # Get current settings with high priority for curated content
        batch_size = max(3, int(self.batch_size_var.get()) // 2)  # Smaller batches for quality
        priority = 9  # Always high priority for curated content
        
        # Create specialized job configuration
        job_config = {
            'type': 'curated_only',
            'directory': self.selected_directory,
            'batch_size': batch_size,
            'priority': priority,
            'estimated_time': curated_count * 3,  # More time per curated file
            'file_count': curated_count,
            'total_size': analysis.get('curated_size', 0),
            'curated_files': curated_count,
            'curation_impact': impact_score,
            'curated_pairs': analysis.get('curated_pairs', []),
            'description': f"🎯 Kuratierte Dateien: {Path(self.selected_directory).name} ({curated_count} Dateien, Score: {impact_score})"
        }
        
        # LEGACY: Job Queue Manager wurde durch CovinaBackendService ersetzt
        # TODO: Implementiere upload_curated_files() in CovinaBackendService
        self.log_message(f"🎯 Kuratierter Upload vorbereitet: {curated_count} Dateien (Legacy-Funktion)", "WARNING")
        
        self.log_message(f"🎯 Kuratierter Job in Warteschlange: {job_id[:8]}... ({curated_count} Dateien)", "INFO")
        
        # Capture directory path for background thread before reset
        selected_directory_path_curated = self.selected_directory
        
        # Reset selection
        self.selected_directory = None
        self.selected_dir_var.set("Kein Verzeichnis ausgewählt")
        self.preview_button.configure(state="disabled")
        self.upload_dir_button.configure(state="disabled")
        self.curated_only_button.configure(state="disabled")
        self.curated_status_var.set("")
        
        # Clear preview
        self._update_preview_text("Kuratierte Dateien wurden zur Hochprioritäts-Verarbeitung übermittelt.")
        
        # Process curated upload in background
        def process_curated_upload():
            try:
                # Prepare curated pairs for upload
                curated_pairs_full = []
                base_path = Path(selected_directory_path_curated)
                
                for pair in analysis['curated_pairs']:
                    curated_pairs_full.append({
                        'content_file': str(base_path / pair['content_file']),
                        'metadata_file': str(base_path / pair['metadata_file']),
                        'quality': pair['metadata_quality'],
                        'rag_impact': pair['rag_impact'],
                        'curator': pair['curator_info']
                    })
                
                # Upload curated files with maximum priority
                results = self.api_client.upload_curated_files(curated_pairs_full, batch_size=batch_size)
                
                total_uploaded = 0
                for result in results:
                    backend_job_id = result.get('job_id')
                    file_count = result.get('file_count', 0)
                    total_uploaded += file_count
                    self.log_message(f"🎯 Kuratierter Batch erfolgreich: {backend_job_id} ({file_count} Dateien)", "SUCCESS")
                
                self.log_message(f"✨ {total_uploaded} kuratierte Dateien mit maximaler RAG-Priorität übertragen", "SUCCESS")
                self.log_message(f"📊 Durchschnittliche Metadaten-Qualität: {sum(p['quality'] for p in curated_pairs_full) / len(curated_pairs_full):.1f}/100", "INFO")
                
            except Exception as e:
                self.log_message(f"🎯 Kuratierter Upload fehlgeschlagen: {e}", "ERROR")
        
        threading.Thread(target=process_curated_upload, daemon=True).start()
    
    def check_backend_connection(self):
        """Enhanced backend connection check with intelligent retry and offline mode"""
        def check():
            try:
                health = self.api_client.health_check()
                status = health.get("status", "unknown")
                active_jobs = health.get("active_jobs", 0)
                
                if status == "healthy":
                    status_text = f"✅ Backend Online ({active_jobs} aktive Jobs)"
                    self.root.after(0, lambda: self.backend_status_var.set(status_text))
                    
                    # Enable backend-dependent features
                    self.root.after(0, self._enable_backend_features)
                    
                    if not hasattr(self, '_backend_reconnected') or not self._backend_reconnected:
                        self.log_message("Backend-Verbindung wiederhergestellt", "SUCCESS")
                        self._backend_reconnected = True
                    return True
                else:
                    raise Exception(f"Backend Status: {status}")
                    
            except Exception as e:
                self.root.after(0, lambda: self.backend_status_var.set("❌ Backend Offline"))
                
                # Disable backend-dependent features
                self.root.after(0, self._disable_backend_features)
                
                if not hasattr(self, '_backend_offline_logged') or not self._backend_offline_logged:
                    self.log_message("Backend nicht erreichbar - Offline-Modus aktiv", "WARNING")
                    self._backend_offline_logged = True
                    self._backend_reconnected = False
                
                return False
        
        return threading.Thread(target=check, daemon=True).start()
    
    def _enable_backend_features(self):
        """Enable features that require backend connection"""
        # Enable upload buttons if conditions are met
        if hasattr(self, 'selected_files') and self.selected_files:
            # File upload button logic would go here
            pass
        
        if hasattr(self, 'selected_directory') and self.selected_directory:
            # Directory upload button logic would go here
            pass
        
        # Reset offline status
        self._backend_offline_logged = False
    
    def _disable_backend_features(self):
        """Disable features that require backend connection"""
        # This would disable upload buttons and other backend-dependent features
        # For now, we'll just ensure the UI shows offline status
        pass
    
    # LEGACY METHOD - Replaced by CovinaBackendService health check loop
    # def start_refresh_thread(self):
    #     """Enhanced refresh thread with adaptive intervals and error throttling"""
    #     # This is now handled by backend_service.start() which runs periodic health checks
    #     # and emits BACKEND_CONNECTED/DISCONNECTED events
    #     pass
    
    def _update_jobs_display(self, jobs):
        """Update jobs display in UI"""
        # Update active jobs listbox
        self.active_jobs_listbox.delete(0, tk.END)
        
        active_jobs = [job for job in jobs if job['status'] in ['pending', 'processing']]
        
        for job in active_jobs[:10]:  # Show up to 10 active jobs
            status_icon = {"pending": "⏳", "processing": "🔄"}.get(job['status'], "❓")
            job_text = f"{status_icon} {job['job_id'][:8]}... ({job['file_count']} files)"
            self.active_jobs_listbox.insert(tk.END, job_text)
    
    # LEGACY METHOD - Replaced by CovinaBackendService task executor
    # def start_queue_processor(self):
    #     """Start job queue processor"""
    #     # This is now handled by TaskExecutor within CovinaBackendService
    #     # Queue management is done via EventBus events
    #     pass
    
    # LEGACY METHOD - Replaced by event-driven resource updates
    # def _update_queue_status(self, status):
    #     """Update queue status UI elements"""
    #     # Resource monitoring now happens via backend_service events
    #     # UI updates triggered by event handlers
    #     pass
    
    def log_message(self, message: str, level: str = "INFO"):
        """Enhanced log message with timestamp and color coding"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Color coding based on level
        color_map = {
            "SUCCESS": "\033[92m",  # Green
            "INFO": "\033[94m",     # Blue  
            "WARNING": "\033[93m",  # Yellow
            "ERROR": "\033[91m",    # Red
            "RESET": "\033[0m"      # Reset
        }
        
        color = color_map.get(level, color_map["INFO"])
        reset = color_map["RESET"]
        
        # Print to console with colors
        print(f"{color}[{timestamp}] {level}: {message}{reset}")
        
        # Store in memory for GUI log display if needed
        if not hasattr(self, '_log_messages'):
            self._log_messages = deque(maxlen=1000)  # Keep last 1000 messages
        
        self._log_messages.append({
            'timestamp': timestamp,
            'level': level,
            'message': message
        })
    
    def _update_status(self, message: str, status_type: str = "info"):
        """Updates status bar with message (main thread only)"""
        icon_map = {
            "success": "✅",
            "error": "❌",
            "warning": "⚠️",
            "info": "ℹ️"
        }
        
        icon = icon_map.get(status_type, "ℹ️")
        self.status_var.set(f"{icon} {message}")
    
    def update_time(self):
        """Update time display"""
        current_time = datetime.now().strftime("%H:%M:%S")
        self.time_var.set(current_time)
        self.root.after(1000, self.update_time)
    
    def _show_about_covina(self):
        """Zeigt Covina About-Dialog"""
        about_window = tk.Toplevel(self.root)
        about_window.title("Über Covina")
        about_window.geometry("600x400")
        about_window.resizable(False, False)
        
        # Header
        header_frame = tk.Frame(about_window, bg='#0066CC', height=80)
        header_frame.pack(fill=tk.X)
        header_frame.pack_propagate(False)
        
        covina_title = tk.Label(
            header_frame,
            text="COVINA",
            font=('Segoe UI', 28, 'bold'),
            foreground='white',
            bg='#0066CC'
        )
        covina_title.pack(expand=True)
        
        # Content
        content_frame = tk.Frame(about_window, bg='white', padx=30, pady=20)
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Info Text
        info_text = """
Covina Development Framework
Contextual Vertex Intelligence & Navigation Architecture

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Enhanced Document Processing System
Version 3.0 (2025-10-08)

Intelligente Dokumentenverarbeitung mit multi-modaler
Analyse, Graph-basierter Wissensrepräsentation und
Vector-Store-Integration.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Features:
• Multi-Backend-Support (PostgreSQL, Neo4j, ChromaDB)
• Asynchrone Job-Verarbeitung
• Resource Management & Monitoring
• SAGA-Pattern für Transaktionen

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

© 2025 Covina Development Team
Alle Rechte vorbehalten.
        """
        
        info_label = tk.Label(
            content_frame,
            text=info_text,
            font=('Courier New', 9),
            justify=tk.LEFT,
            bg='white',
            foreground='#333333'
        )
        info_label.pack(fill=tk.BOTH, expand=True)
        
        # Footer Button
        close_btn = tk.Button(
            about_window,
            text="Schließen",
            command=about_window.destroy,
            font=('Segoe UI', 10),
            bg='#0066CC',
            fg='white',
            activebackground='#004499',
            activeforeground='white',
            relief=tk.FLAT,
            padx=20,
            pady=8,
            cursor='hand2'
        )
        close_btn.pack(pady=(0, 20))
        
        # Center window
        about_window.transient(self.root)
        about_window.grab_set()
        about_window.update_idletasks()
        x = (about_window.winfo_screenwidth() // 2) - (600 // 2)
        y = (about_window.winfo_screenheight() // 2) - (400 // 2)
        about_window.geometry(f"600x400+{x}+{y}")
    
    # ========================================================================
    # DIRECTORY ANALYSIS SPINNER (Visual Feedback for Long Operations)
    # ========================================================================
    
    def _start_analysis_spinner(self):
        """Start animated spinner for directory analysis"""
        if self._analysis_spinner_active:
            return  # Already running
        
        self._analysis_spinner_active = True
        self._analysis_spinner_index = 0
        self._update_analysis_spinner()
    
    def _stop_analysis_spinner(self):
        """Stop animated spinner"""
        self._analysis_spinner_active = False
    
    def _update_analysis_spinner(self):
        """Update spinner animation (called recursively)"""
        if not self._analysis_spinner_active:
            return
        
        # Get current spinner character
        spinner_char = self._analysis_spinner_chars[self._analysis_spinner_index]
        self._analysis_spinner_index = (self._analysis_spinner_index + 1) % len(self._analysis_spinner_chars)
        
        # Update status with spinner
        if hasattr(self, 'status_label'):
            current_text = self.status_var.get()
            if "Analysiere" in current_text:
                # Replace old spinner with new one
                base_text = current_text.split("🔍")[1].strip() if "🔍" in current_text else "Analysiere..."
                base_text = base_text.split(self._analysis_spinner_chars[0])[0].strip()
                for char in self._analysis_spinner_chars:
                    base_text = base_text.replace(char, "").strip()
                
                new_text = f"{spinner_char} {base_text}"
                self.status_var.set(new_text)
        
        # Schedule next update (100ms = 10 FPS)
        if self._analysis_spinner_active:
            self.root.after(100, self._update_analysis_spinner)
    
    # ========================================================================
    # MAIN EVENT LOOP
    # ========================================================================
    
    def run(self):
        """Start the Enhanced GUI"""
        self.log_message("🏛️ Enhanced Covina GUI gestartet", "SUCCESS")
        
        try:
            self.root.mainloop()
        finally:
            # Cleanup - shutdown backend service and task executor
            try:
                self.backend_service.stop()
                self.task_executor.stop()
                self.event_bus.stop()
            except Exception as e:
                print(f"Cleanup error: {e}")

# Main Entry Point
if __name__ == "__main__":
    app = EnhancedCovinaGUI()
    app.run()