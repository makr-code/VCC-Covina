#!/usr/bin/env python3
"""
Covina Frontend GUI
==================

Benutzerfreundliche Tkinter-Anwendung für Covina Document Processing:
- Datei/Verzeichnis Upload
- Job-Status Monitoring
- Metriken-Anzeige
- Real-time Updates
- Export-Funktionen

Autor: Covina System
Datum: Oktober 2025
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import tkinter.font as tkFont
import requests
import json
import threading
import time
from datetime import datetime
from pathlib import Path
import webbrowser
from typing import Dict, List, Optional, Any
import os
import tempfile
import shutil

# Covina API Client
class CovinaAPIClient:
    """Client für Covina Backend API"""
    
    def __init__(self, base_url: str = "http://127.0.0.1:45678"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.timeout = 30
    
    def health_check(self) -> Dict:
        """Backend Health Check"""
        try:
            response = self.session.get(f"{self.base_url}/health")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise Exception(f"Backend nicht erreichbar: {e}")
    
    def upload_files(self, file_paths: List[str]) -> Dict:
        """Upload mehrerer Dateien"""
        files = []
        try:
            for file_path in file_paths:
                files.append(('files', (Path(file_path).name, open(file_path, 'rb'), 'application/octet-stream')))
            
            response = self.session.post(f"{self.base_url}/upload/files", files=files)
            response.raise_for_status()
            return response.json()
            
        finally:
            # Dateien schließen
            for _, file_tuple in files:
                if hasattr(file_tuple[1], 'close'):
                    file_tuple[1].close()
    
    def upload_directory(self, directory_path: str) -> Dict:
        """Upload ganzes Verzeichnis"""
        response = self.session.post(
            f"{self.base_url}/upload/directory",
            params={"directory_path": directory_path}
        )
        response.raise_for_status()
        return response.json()
    
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
    
    def list_jobs(self, limit: int = 50) -> List[Dict]:
        """Liste alle Jobs"""
        response = self.session.get(f"{self.base_url}/jobs", params={"limit": limit})
        response.raise_for_status()
        return response.json()
    
    def cancel_job(self, job_id: str) -> Dict:
        """Storniere Job"""
        response = self.session.delete(f"{self.base_url}/jobs/{job_id}")
        response.raise_for_status()
        return response.json()

# Hauptanwendung
class CovinaGUI:
    """Hauptklasse für Covina GUI"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.api_client = CovinaAPIClient()
        self.current_jobs = {}
        self.auto_refresh = True
        
        self.setup_gui()
        self.setup_styles()
        self.check_backend_connection()
        self.start_refresh_thread()
    
    def setup_gui(self):
        """GUI Setup"""
        self.root.title("🏛️ Covina - Deutsche Rechtsdokument Verarbeitung")
        self.root.geometry("1200x800")
        self.root.minsize(1000, 600)
        
        # Icon (falls vorhanden)
        try:
            self.root.iconbitmap("covina_icon.ico")
        except:
            pass
        
        # Main Frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=034,11464,11561,11657,11774,11896,12001,12106,12209,12351,12501,12608,12717,12792,12896,12998,13109,13203,13294,13399,13479,13564,13665,13771,13864,13965,14052,14160,14259,14362,14486,14566,14669,14763"
                    }
                },
                {
                    "source": "C:\\Users\\mkrueger\\.gradle\\caches\\8.13\\transforms\\55eaf6392191e12577859473ecbcdf98\\transformed\\appcompat-1.7.1\\res\\values-or\\values-or.xml",
                    "from": {
                        "startLines": "2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29",
                        "startColumns": "4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4",
                        "startOffsets": "105,216,326,433,519,623,743,822,903,994,1087,1188,1283,1383,1476,1571,1667,1758,1848,1937,2047,2151,2257,2368,2470,2588,2751,2857",
                        "endColumns": "110,109,106,85,103,119,78,80,90,92,100,94,99,92,94,95,90,89,88,109,103,105,110,101,117,162,105,89",
                        "endOffsets": "211,321,428,514,618,738,817,898,989,1082,1183,1278,1378,1471,1566,1662,1753,1843,1932,2042,2146,2252,2363,2465,2583,2746,2852,2942"
                    },
                    "to": {
                        "startLines": "6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,213",
                        "startColumns": "4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4",
                        "startOffsets": "322,433,543,650,736,840,960,1039,1120,1211,1304,1405,1500,1600,1693,1788,1884,1975,2065,2154,2264,2368,2474,2585,2687,2805,2968,20500",
                        "endColumns": "110,109,106,85,103,119,78,80,90,92,100,94,99,92,94,95,90,89,88,109,103,105,110,101,117,162,105,89",
                        "endOffsets": "428,538,645,731,835,955,1034,1115,1206,1299,1400,1495,1595,1688,1783,1879,1970,2060,2149,2259,2363,2469,2580,2682,2800,2963,3069,20585"
                    }
                },
                {
                    "source": "C:\\Users\\mkrueger\\.gradle\\caches\\8.13\\transforms\\fb7e4845b5a12436e262cf00ce348bc2\\transformed\\material-1.13.0\\res\\values-or\\values-or.xml",
                    "from": {
                        "startLines": "2,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58,59,60,61,62,63,64,65,66,67,68,69,70,71,72,73,74,75,76,77,78,79,80,81,82,83,84,85",
                        "startColumns": "4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4",
                        "startOffsets": "100,272,354,432,509,593,687,792,871,931,996,1085,1150,1209,1286,1372,1436,1500,1563,1636,1700,1764,1832,1888,1942,2054,2112,2174,2228,2300,2422,2509,2585,2677,2759,2845,2985,3062,3143,3270,3361,3438,3492,3543,3609,3679,3756,3827,3902,3973,4050,4119,4188,4295,4386,4458,4547,4636,4710,4782,4868,4918,4997,5063,5143,5227,5289,5353,5416,5485,5585,5673,5765,5850,5941,6029,6087,6142,6226,6307,6382",
                        "endLines": "5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58,59,60,61,62,63,64,65,66,67,68,69,70,71,72,73,74,75,76,77,78,79,80,81,82,83,84,85",
                        "endColumns": "12,81,77,76,83,93,104,78,59,64,88,64,58,76,85,63,63,62,72,63,63,67,55,53,111,57,61,53,71,121,86,75,91,81,85,139,76,80,126,90,76,53,50,65,69,76,70,74,70,76,68,68,106,90,71,88,88,73,71,85,49,78,65,79,83,61,63,62,68,99,87,91,84,90,87,57,54,83,80,74,74",
                        "endOffsets": "267,349,427,504,588,682,787,866,926,991,1080,1145,1204,1281,1367,1431,1495,1558,1631,1695,1759,1827,1883,1937,2049,2107,2169,2223,2295,2417,2504,2580,2672,2754,2840,2980,3057,3138,3265,3356,3433,3487,3538,3604,3674,3751,3822,3897,3968,4045,4114,4183,4290,4381,4453,4542,4631,4705,4777,4863,4913,4992,5058,5138,5222,5284,5348,5411,5480,5580,5668,5760,5845,5936,6024,6082,6137,6221,6302,6377,6452"
                    },
                    "to": {
                        "startLines": "2,34,35,36,37,45,46,47,72,73,75,79,82,83,141,142,143,144,145,146,147,148,149,150,151,152,153,154,155,156,157,158,159,160,161,162,163,164,165,166,167,168,169,170,171,172,173,174,175,176,177,178,179,180,181,182,183,184,185,186,187,188,189,190,191,192,193,194,195,196,197,198,199,200,201,202,203,209,214,215,217",
                        "startColumns": "4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4",
                        "startOffsets": "150,3147,3229,3307,3384,4203,4297,4402,7297,7357,7511,8030,8270,8329,14768,14854,14918,14982,15045,15118,15182,15246,15314,15370,15424,15536,15594,15656,15710,15782,15904,15991,16067,16159,16241,16327,16467,16544,16625,16752,16843,16920,16974,17025,17091,17161,17238,17309,17384,17455,17532,17601,17670,17777,17868,17940,18029,18118,18192,18264,18350,18400,18479,18545,18625,18709,18771,18835,18898,18967,19067,19155,19247,19332,19423,19511,19569,20117,20590,20671,20816",
                        "endLines": "5,34,35,36,37,45,46,47,72,73,75,79,82,83,141,142,143,144,145,146,147,148,149,150,151,152,153,154,155,156,157,158,159,160,161,162,163,164,165,166,167,168,169,170,171,172,173,174,175,176,177,178,179,180,181,182,183,184,185,186,187,188,189,190,191,192,193,194,195,196,197,198,199,200,201,202,203,209,214,215,217",
                        "endColumns": "12,81,77,76,83,93,104,78,59,64,88,64,58,76,85,63,63,62,72,63,63,67,55,53,111,57,61,53,71,121,86,75,91,81,85,139,76,80,126,90,76,53,50,65,69,76,70,74,70,76,68,68,106,90,71,88,88,73,71,85,49,78,65,79,83,61,63,62,68,99,87,91,84,90,87,57,54,83,80,74,74",
                        "endOffsets": "317,3224,3302,3379,3463,4292,4397,4476,7352,7417,7595,8090,8324,8401,14849,14913,14977,15040,15113,15177,15241,15309,15365,15419,15531,15589,15651,15705,15777,15899,15986,16062,16154,16236,16322,16462,16539,16620,16747,16838,16915,16969,17020,17086,17156,17233,17304,17379,17450,17527,17596,17665,17772,17863,17935,18024,18113,18187,18259,18345,18395,18474,18540,18620,18704,18766,18830,18893,18962,19062,19150,19242,19327,19418,19506,19564,19619,20196,20666,20741,20886"
                    }
                },
                {
                    "source": "C:\\Users\\mkrueger\\.gradle\\caches\\8.13\\transforms\\5f5c549d3a61eb0368ed1f84a4c13113\\transformed\\play-services-base-18.5.0\\res\\values-or\\values.xml",
                    "from": {
                        "startLines": "4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20",
                        "startColumns": "0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0",
                        "startOffsets": "193,300,457,585,698,849,980,1090,1196,1359,1468,1625,1754,1900,2053,2114,2182",
                        "endColumns": "106,156,127,112,150,130,109,105,162,108,156,128,145,152,60,67,82",
                        "endOffsets": "299,456,584,697,848,979,1089,1195,1358,1467,1624,1753,1899,2052,2113,2181,2264"
                    },
                    "to": {
                        "startLines": "50,51,52,53,54,55,56,57,59,60,61,62,63,64,65,66,67",
                        "startColumns": "4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4",
                        "startOffsets": "4665,4776,4937,5069,5186,5341,5476,5590,5840,6007,6120,6281,6414,6564,6721,6786,6858",
                        "endColumns": "110,160,131,116,154,134,113,109,166,112,160,132,149,156,64,71,86",
                        "endOffsets": "4771,4932,5064,5181,5336,5471,5585,5695,6002,6115,6276,6409,6559,6716,6781,6853,6940"
                    }
                },
                {
                    "source": "C:\\Users\\mkrueger\\.gradle\\caches\\8.13\\transforms\\fbec8997159b718443be441e57ff2ef4\\transformed\\ui-release\\res\\values-or\\values-or.xml",
                    "from": {
                        "startLines": "3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21",
                        "startColumns": "4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4",
                        "startOffsets": "179,276,363,455,555,641,718,816,904,991,1069,1151,1221,1305,1380,1457,1533,1616,1683",
                        "endColumns": "96,86,91,99,85,76,97,87,86,77,81,69,83,74,76,75,82,66,118",
                        "endOffsets": "271,358,450,550,636,713,811,899,986,1064,1146,1216,1300,1375,1452,1528,1611,1678,1797"
                    },
                    "to": {
                        "startLines": "48,49,69,70,71,80,81,206,207,211,212,216,218,219,220,221,224,225,226",
                        "startColumns": "4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4",
                        "startOffsets": "4481,4578,7019,7111,7211,8095,8172,19862,19950,20340,20418,20746,20891,20975,21050,21127,21473,21556,21623",
                        "endColumns": "96,86,91,99,85,76,97,87,86,77,81,69,83,74,76,75,82,66,118",
                        "endOffsets": "4573,4660,7106,7206,7292,8167,8265,19945,20032,20413,20495,20811,20970,21045,21122,21198,21551,21618,21737"
                    }
                }
            ]
        }
    ]
}                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            "INFO")
                
                response = self.api_client.upload_files(self.selected_files)
                
                job_id = response['job_id']
                message = response['message']
                
                self.log_message(f"Upload erfolgreich - Job ID: {job_id}", "SUCCESS")
                self.log_message(f"Geschätzte Verarbeitungszeit: {response['estimated_processing_time']}", "INFO")
                
                self.status_var.set("Upload abgeschlossen")
                
                # Reset selection
                self.selected_files = []
                self.selected_files_var.set("Keine Dateien ausgewählt")
                self.files_label.configure(foreground="gray")
                
                # Refresh jobs
                self.refresh_jobs()
                
            except Exception as e:
                self.log_message(f"Upload fehlgeschlagen: {e}", "ERROR")
                self.status_var.set("Upload fehlgeschlagen")
                messagebox.showerror("Fehler", f"Upload fehlgeschlagen:\n{e}")
        
        # Run in thread
        threading.Thread(target=upload, daemon=True).start()
    
    def upload_directory(self):
        """Upload selected directory"""
        if not hasattr(self, 'selected_directory') or not self.selected_directory:
            messagebox.showwarning("Warnung", "Bitte wählen Sie zuerst ein Verzeichnis aus.")
            return
        
        def upload():
            try:
                self.status_var.set("Verzeichnis-Upload läuft...")
                self.log_message(f"Starte Verzeichnis-Upload: {self.selected_directory}", "INFO")
                
                response = self.api_client.upload_directory(self.selected_directory)
                
                job_id = response['job_id']
                file_count = response['file_count']
                
                self.log_message(f"Verzeichnis-Upload erfolgreich - Job ID: {job_id}", "SUCCESS")
                self.log_message(f"{file_count} Dateien gefunden", "INFO")
                
                self.status_var.set("Verzeichnis-Upload abgeschlossen")
                
                # Reset selection
                self.selected_directory = None
                self.selected_dir_var.set("Kein Verzeichnis ausgewählt")
                self.dir_label.configure(foreground="gray")
                
                # Refresh jobs
                self.refresh_jobs()
                
            except Exception as e:
                self.log_message(f"Verzeichnis-Upload fehlgeschlagen: {e}", "ERROR")
                self.status_var.set("Verzeichnis-Upload fehlgeschlagen")
                messagebox.showerror("Fehler", f"Verzeichnis-Upload fehlgeschlagen:\n{e}")
        
        # Run in thread
        threading.Thread(target=upload, daemon=True).start()
    
    def refresh_jobs(self):
        """Refresh jobs list"""
        def refresh():
            try:
                jobs = self.api_client.list_jobs()
                
                # Update treeview in main thread
                self.root.after(0, self._update_jobs_treeview, jobs)
                
            except Exception as e:
                self.root.after(0, self.log_message, f"Fehler beim Laden der Jobs: {e}", "ERROR")
        
        threading.Thread(target=refresh, daemon=True).start()
    
    def _update_jobs_treeview(self, jobs: List[Dict]):
        """Update jobs treeview (main thread)"""
        # Clear existing items
        for item in self.jobs_tree.get_children():
            self.jobs_tree.delete(item)
        
        # Add new items
        for job in jobs:
            job_id = job['job_id'][:8] + "..."  # Shorten for display
            status = job['status']
            file_count = job['file_count']
            processed = job['processed_files']
            created_at = job['created_at']
            
            # Progress calculation
            if file_count > 0:
                progress = f"{processed}/{file_count}"
            else:
                progress = "0/0"
            
            # Status icon
            status_icons = {
                "pending": "⏳",
                "processing": "🔄",
                "completed": "✅",
                "failed": "❌",
                "cancelled": "🚫"
            }
            
            status_display = f"{status_icons.get(status, '❓')} {status}"
            
            # Time formatting
            try:
                time_str = datetime.fromisoformat(created_at.replace('Z', '+00:00')).strftime("%H:%M:%S")
            except:
                time_str = "Unknown"
            
            item_id = self.jobs_tree.insert(
                "",
                "end",
                text=job_id,
                values=(status_display, file_count, progress, time_str),
                tags=(status,)
            )
            
            # Store full job data
            self.current_jobs[item_id] = job
        
        # Configure tags for colors
        self.jobs_tree.tag_configure("completed", foreground="green")
        self.jobs_tree.tag_configure("failed", foreground="red")
        self.jobs_tree.tag_configure("processing", foreground="blue")
        self.jobs_tree.tag_configure("cancelled", foreground="gray")
    
    def on_job_select(self, event):
        """Handle job selection"""
        selection = self.jobs_tree.selection()
        if selection:
            item = selection[0]
            job = self.current_jobs.get(item)
            
            if job:
                job_id = job['job_id']
                status = job['status']
                
                self.selected_job_var.set(f"Job: {job_id[:16]}... | Status: {status}")
                
                # Enable/disable buttons
                if status in ["completed"]:
                    self.details_button.configure(state="normal")
                    self.cancel_button.configure(state="disabled")
                elif status in ["pending", "processing"]:
                    self.details_button.configure(state="disabled")
                    self.cancel_button.configure(state="normal")
                else:
                    self.details_button.configure(state="disabled")
                    self.cancel_button.configure(state="disabled")
        else:
            self.selected_job_var.set("Kein Job ausgewählt")
            self.details_button.configure(state="disabled")
            self.cancel_button.configure(state="disabled")
    
    def show_job_details(self, event):
        """Show detailed job information"""
        self.show_detailed_metrics()
    
    def show_detailed_metrics(self):
        """Show detailed metrics for selected job"""
        selection = self.jobs_tree.selection()
        if not selection:
            return
        
        item = selection[0]
        job = self.current_jobs.get(item)
        if not job:
            return
        
        job_id = job['job_id']
        
        def get_metrics():
            try:
                metrics = self.api_client.get_job_metrics(job_id)
                self.root.after(0, self._show_metrics_window, job_id, metrics)
            except Exception as e:
                self.root.after(0, self.log_message, f"Fehler beim Laden der Metriken: {e}", "ERROR")
        
        threading.Thread(target=get_metrics, daemon=True).start()
    
    def _show_metrics_window(self, job_id: str, metrics: Dict):
        """Show metrics in new window"""
        metrics_window = tk.Toplevel(self.root)
        metrics_window.title(f"📊 Detaillierte Metriken - {job_id[:16]}...")
        metrics_window.geometry("800x600")
        metrics_window.transient(self.root)
        
        # Create notebook for different metric categories
        notebook = ttk.Notebook(metrics_window, padding="10")
        notebook.pack(fill=tk.BOTH, expand=True)
        
        # Overview Tab
        overview_frame = ttk.Frame(notebook)
        notebook.add(overview_frame, text="📋 Übersicht")
        
        overview_text = scrolledtext.ScrolledText(overview_frame, wrap=tk.WORD, font=('Consolas', 10))
        overview_text.pack(fill=tk.BOTH, expand=True, padding=5)
        
        overview_content = f"""
📊 JOB METRIKEN ÜBERSICHT
=========================

Job ID: {job_id}
Gesamte Dateien: {metrics.get('total_files', 0)}
Erfolgreich: {metrics.get('successful_files', 0)}
Fehlgeschlagen: {metrics.get('failed_files', 0)}
Durchschnittliche Verarbeitungszeit: {metrics.get('processing_time_avg', 0):.3f}s

🏛️ DOKUMENTKLASSIFIKATION
=========================
"""
        
        classification_stats = metrics.get('classification_stats', {})
        for doc_type, count in classification_stats.items():
            overview_content += f"{doc_type}: {count} Dokumente\n"
        
        overview_content += f"""

📄 CONTENT-EXTRAKTION
=====================
Zeichen extrahiert: {metrics.get('content_extraction', {}).get('content_extracted_chars', 0):,}
Erfolgreiche Extraktionen: {metrics.get('content_extraction', {}).get('successful_extractions', 0)}

🧠 KI-VERARBEITUNG
==================
Entitäten gefunden: {metrics.get('ai_processing', {}).get('entities_found', 0)}
PII-Elemente: {metrics.get('ai_processing', {}).get('pii_found', 0)}

🔍 METADATA-EXTRAKTION
======================
Durchschnittliche Vollständigkeit: {metrics.get('metadata_extraction', {}).get('avg_completeness', 0):.1f}%
"""
        
        overview_text.insert("1.0", overview_content)
        overview_text.configure(state="disabled")
        
        # Backend Metrics Tab
        backend_frame = ttk.Frame(notebook)
        notebook.add(backend_frame, text="💾 Backend")
        
        backend_text = scrolledtext.ScrolledText(backend_frame, wrap=tk.WORD, font=('Consolas', 10))
        backend_text.pack(fill=tk.BOTH, expand=True, padding=5)
        
        backend_content = "💾 BACKEND-SCHREIBVORGÄNGE\n=========================\n\n"
        
        backend_metrics = metrics.get('backend_metrics', {})
        for backend_name, backend_data in backend_metrics.items():
            backend_content += f"🔧 {backend_name.upper().replace('_', ' ')}\n"
            backend_content += "-" * 30 + "\n"
            
            if isinstance(backend_data, dict):
                for key, value in backend_data.items():
                    backend_content += f"{key.replace('_', ' ').title()}: {value:,}\n"
            else:
                backend_content += f"Wert: {backend_data}\n"
            
            backend_content += "\n"
        
        backend_text.insert("1.0", backend_content)
        backend_text.configure(state="disabled")
        
        # Raw JSON Tab
        json_frame = ttk.Frame(notebook)
        notebook.add(json_frame, text="🔧 Raw JSON")
        
        json_text = scrolledtext.ScrolledText(json_frame, wrap=tk.WORD, font=('Consolas', 9))
        json_text.pack(fill=tk.BOTH, expand=True, padding=5)
        
        json_content = json.dumps(metrics, indent=2, ensure_ascii=False)
        json_text.insert("1.0", json_content)
        json_text.configure(state="disabled")
        
        # Export button
        export_frame = ttk.Frame(metrics_window)
        export_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(
            export_frame,
            text="💾 Metriken exportieren",
            command=lambda: self.export_metrics(job_id, metrics)
        ).pack(side=tk.LEFT)
        
        ttk.Button(
            export_frame,
            text="❌ Schließen",
            command=metrics_window.destroy
        ).pack(side=tk.RIGHT)
    
    def export_metrics(self, job_id: str, metrics: Dict):
        """Export metrics to file"""
        try:
            file_path = filedialog.asksaveasfilename(
                defaultextension=".json",
                filetypes=[("JSON files", "*.json"), ("Text files", "*.txt"), ("All files", "*.*")],
                title="Metriken exportieren",
                initialname=f"covina_metrics_{job_id[:8]}.json"
            )
            
            if file_path:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(metrics, f, indent=2, ensure_ascii=False)
                
                self.log_message(f"Metriken exportiert: {file_path}", "SUCCESS")
                
        except Exception as e:
            self.log_message(f"Fehler beim Export: {e}", "ERROR")
    
    def cancel_selected_job(self):
        """Cancel selected job"""
        selection = self.jobs_tree.selection()
        if not selection:
            return
        
        item = selection[0]
        job = self.current_jobs.get(item)
        if not job:
            return
        
        job_id = job['job_id']
        
        # Confirmation dialog
        if not messagebox.askyesno(
            "Job stornieren",
            f"Möchten Sie den Job {job_id[:16]}... wirklich stornieren?"
        ):
            return
        
        def cancel():
            try:
                response = self.api_client.cancel_job(job_id)
                self.root.after(0, self.log_message, f"Job storniert: {job_id}", "WARNING")
                self.root.after(0, self.refresh_jobs)
            except Exception as e:
                self.root.after(0, self.log_message, f"Fehler beim Stornieren: {e}", "ERROR")
        
        threading.Thread(target=cancel, daemon=True).start()
    
    def toggle_auto_refresh(self):
        """Toggle auto refresh"""
        self.auto_refresh = self.auto_refresh_var.get()
        
        if self.auto_refresh:
            self.log_message("Auto-Refresh aktiviert", "INFO")
        else:
            self.log_message("Auto-Refresh deaktiviert", "INFO")
    
    def start_refresh_thread(self):
        """Start auto refresh thread"""
        def refresh_loop():
            while True:
                time.sleep(5)  # 5 second interval
                if self.auto_refresh:
                    try:
                        jobs = self.api_client.list_jobs()
                        self.root.after(0, self._update_jobs_treeview, jobs)
                    except:
                        pass  # Ignore errors in background refresh
        
        refresh_thread = threading.Thread(target=refresh_loop, daemon=True)
        refresh_thread.start()
    
    def open_api_docs(self):
        """Open API documentation in browser"""
        try:
            webbrowser.open("http://127.0.0.1:8000/docs")
            self.log_message("API-Dokumentation geöffnet", "INFO")
        except Exception as e:
            self.log_message(f"Fehler beim Öffnen der API-Docs: {e}", "ERROR")
    
    def run(self):
        """Start the GUI"""
        self.log_message("🏛️ Covina GUI gestartet", "SUCCESS")
        self.log_message("Bereit für Dokumentenverarbeitung", "INFO")
        
        # Initial jobs refresh
        self.refresh_jobs()
        
        self.root.mainloop()

# Main Entry Point
if __name__ == "__main__":
    app = CovinaGUI()
    app.run()