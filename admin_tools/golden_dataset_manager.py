"""
Golden Dataset Manager - Admin Tool
====================================

Tkinter GUI für CRUD Operations auf Golden Datasets (Relational)

Features:
- List/Search Golden Datasets
- Create New Entries
- Update Existing Entries
- Delete Entries
- Filter by Classification, Quality Score
- Export to CSV

Author: Covina Backend Team
Date: 17. Oktober 2025
Version: 1.0.0
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import requests
from datetime import datetime
from typing import Optional, List, Dict
import json
import csv


class GoldenDatasetManager:
    """Admin GUI für Golden Dataset Management"""
    
    def __init__(self, root: tk.Tk, backend_url: str = "http://127.0.0.1:45678"):
        self.root = root
        self.backend_url = backend_url
        self.current_selection: Optional[Dict] = None
        
        # Window Configuration
        self.root.title("Golden Dataset Manager - Covina Admin")
        self.root.geometry("1400x800")
        self.root.configure(bg="#2b2b2b")
        
        # Initialize UI
        self._create_menu()
        self._create_toolbar()
        self._create_main_layout()
        self._create_status_bar()
        
        # Load initial data
        self.refresh_list()
    
    def _create_menu(self):
        """Create menu bar"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File Menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Datei", menu=file_menu)
        file_menu.add_command(label="Exportieren (CSV)", command=self.export_to_csv)
        file_menu.add_separator()
        file_menu.add_command(label="Beenden", command=self.root.quit)
        
        # Edit Menu
        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Bearbeiten", menu=edit_menu)
        edit_menu.add_command(label="Neu", command=self.show_create_dialog)
        edit_menu.add_command(label="Bearbeiten", command=self.show_edit_dialog)
        edit_menu.add_command(label="Löschen", command=self.delete_entry)
        
        # View Menu
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Ansicht", menu=view_menu)
        view_menu.add_command(label="Aktualisieren", command=self.refresh_list)
        view_menu.add_command(label="Filter zurücksetzen", command=self.reset_filters)
    
    def _create_toolbar(self):
        """Create toolbar with quick actions"""
        toolbar = tk.Frame(self.root, bg="#3c3f41", height=50)
        toolbar.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        
        # Buttons
        btn_style = {"bg": "#4a90e2", "fg": "white", "padx": 15, "pady": 5}
        
        tk.Button(toolbar, text="➕ Neu", command=self.show_create_dialog, **btn_style).pack(side=tk.LEFT, padx=5)
        tk.Button(toolbar, text="✏️ Bearbeiten", command=self.show_edit_dialog, **btn_style).pack(side=tk.LEFT, padx=5)
        tk.Button(toolbar, text="🗑️ Löschen", command=self.delete_entry, bg="#e74c3c", fg="white", padx=15, pady=5).pack(side=tk.LEFT, padx=5)
        tk.Button(toolbar, text="🔄 Aktualisieren", command=self.refresh_list, **btn_style).pack(side=tk.LEFT, padx=5)
        tk.Button(toolbar, text="📊 Exportieren", command=self.export_to_csv, **btn_style).pack(side=tk.LEFT, padx=5)
        
        # Connection Status
        self.status_label = tk.Label(toolbar, text="◉ Verbindung wird geprüft...", bg="#3c3f41", fg="yellow")
        self.status_label.pack(side=tk.RIGHT, padx=10)
        
        self._check_backend_connection()
    
    def _create_main_layout(self):
        """Create main layout with filters and table"""
        main_frame = tk.Frame(self.root, bg="#2b2b2b")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Left Panel - Filters
        filter_frame = tk.LabelFrame(main_frame, text="Filter", bg="#3c3f41", fg="white", padx=10, pady=10)
        filter_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 5))
        
        # Classification Filter
        tk.Label(filter_frame, text="Klassifikation:", bg="#3c3f41", fg="white").pack(anchor=tk.W, pady=(5, 0))
        self.classification_var = tk.StringVar()
        self.classification_combo = ttk.Combobox(filter_frame, textvariable=self.classification_var, width=20)
        self.classification_combo['values'] = ['Alle', 'Rechnung', 'Vertrag', 'Brief', 'E-Mail', 'Bestellung', 'Lieferschein']
        self.classification_combo.current(0)
        self.classification_combo.pack(pady=5)
        
        # Quality Score Filter
        tk.Label(filter_frame, text="Min. Qualität:", bg="#3c3f41", fg="white").pack(anchor=tk.W, pady=(10, 0))
        self.quality_var = tk.DoubleVar(value=0.0)
        quality_scale = tk.Scale(filter_frame, from_=0.0, to=1.0, resolution=0.1, 
                                orient=tk.HORIZONTAL, variable=self.quality_var, bg="#3c3f41", fg="white")
        quality_scale.pack(pady=5, fill=tk.X)
        
        # Reviewed By Filter
        tk.Label(filter_frame, text="Geprüft von:", bg="#3c3f41", fg="white").pack(anchor=tk.W, pady=(10, 0))
        self.reviewer_var = tk.StringVar()
        self.reviewer_entry = tk.Entry(filter_frame, textvariable=self.reviewer_var, width=22)
        self.reviewer_entry.pack(pady=5)
        
        # Filter Buttons
        tk.Button(filter_frame, text="Filter anwenden", command=self.apply_filters, 
                 bg="#4a90e2", fg="white", padx=10, pady=5).pack(pady=(20, 5), fill=tk.X)
        tk.Button(filter_frame, text="Zurücksetzen", command=self.reset_filters, 
                 bg="#95a5a6", fg="white", padx=10, pady=5).pack(pady=5, fill=tk.X)
        
        # Right Panel - Table
        table_frame = tk.Frame(main_frame, bg="#2b2b2b")
        table_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Treeview
        columns = ("ID", "Dokument ID", "Klassifikation", "Qualität", "Geprüft von", "Erstellt am")
        self.tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=25)
        
        # Column Configuration
        self.tree.heading("ID", text="ID")
        self.tree.heading("Dokument ID", text="Dokument ID")
        self.tree.heading("Klassifikation", text="Klassifikation")
        self.tree.heading("Qualität", text="Qualität")
        self.tree.heading("Geprüft von", text="Geprüft von")
        self.tree.heading("Erstellt am", text="Erstellt am")
        
        self.tree.column("ID", width=50, anchor=tk.CENTER)
        self.tree.column("Dokument ID", width=200)
        self.tree.column("Klassifikation", width=150)
        self.tree.column("Qualität", width=100, anchor=tk.CENTER)
        self.tree.column("Geprüft von", width=150)
        self.tree.column("Erstellt am", width=180)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Bind events
        self.tree.bind('<Double-1>', lambda e: self.show_edit_dialog())
    
    def _create_status_bar(self):
        """Create status bar"""
        status_bar = tk.Frame(self.root, bg="#3c3f41", height=30)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.record_count_label = tk.Label(status_bar, text="Einträge: 0", bg="#3c3f41", fg="white")
        self.record_count_label.pack(side=tk.LEFT, padx=10)
        
        self.info_label = tk.Label(status_bar, text="Bereit", bg="#3c3f41", fg="white")
        self.info_label.pack(side=tk.RIGHT, padx=10)
    
    def _check_backend_connection(self):
        """Check backend connection status"""
        try:
            response = requests.get(f"{self.backend_url}/health", timeout=2)
            if response.status_code == 200:
                self.status_label.config(text="◉ Verbunden", fg="green")
            else:
                self.status_label.config(text="◉ Backend Fehler", fg="red")
        except requests.exceptions.RequestException:
            self.status_label.config(text="◉ Nicht verbunden", fg="red")
    
    def refresh_list(self, filters: Optional[Dict] = None):
        """Refresh dataset list from backend"""
        try:
            # Build query parameters
            params = {}
            if filters:
                if filters.get('classification') and filters['classification'] != 'Alle':
                    params['classification'] = filters['classification']
                if filters.get('min_quality'):
                    params['min_quality_score'] = filters['min_quality']
                if filters.get('reviewed_by'):
                    params['reviewed_by'] = filters['reviewed_by']
            
            response = requests.get(f"{self.backend_url}/golden-dataset", params=params, timeout=5)
            response.raise_for_status()
            
            data = response.json()
            datasets = data.get('datasets', [])
            
            # Clear existing items
            for item in self.tree.get_children():
                self.tree.delete(item)
            
            # Insert new items
            for ds in datasets:
                self.tree.insert('', tk.END, values=(
                    ds.get('id', ''),
                    ds.get('document_id', ''),
                    ds.get('classification', ''),
                    f"{ds.get('quality_score', 0.0):.2f}",
                    ds.get('reviewed_by', ''),
                    ds.get('created_at', '')[:19] if ds.get('created_at') else ''
                ))
            
            # Update status
            self.record_count_label.config(text=f"Einträge: {len(datasets)}")
            self.info_label.config(text=f"Aktualisiert: {datetime.now().strftime('%H:%M:%S')}")
            
        except requests.exceptions.RequestException as e:
            messagebox.showerror("Verbindungsfehler", f"Backend nicht erreichbar:\n{str(e)}")
    
    def apply_filters(self):
        """Apply current filters"""
        filters = {
            'classification': self.classification_var.get(),
            'min_quality': self.quality_var.get(),
            'reviewed_by': self.reviewer_var.get().strip()
        }
        self.refresh_list(filters)
    
    def reset_filters(self):
        """Reset all filters"""
        self.classification_combo.current(0)
        self.quality_var.set(0.0)
        self.reviewer_var.set("")
        self.refresh_list()
    
    def show_create_dialog(self):
        """Show dialog to create new entry"""
        dialog = GoldenDatasetDialog(self.root, self.backend_url, mode="create")
        self.root.wait_window(dialog.dialog)
        if dialog.result:
            self.refresh_list()
    
    def show_edit_dialog(self):
        """Show dialog to edit selected entry"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Keine Auswahl", "Bitte wählen Sie einen Eintrag aus.")
            return
        
        # Get entry ID
        item = self.tree.item(selection[0])
        entry_id = item['values'][0]
        
        # Fetch full entry data
        try:
            response = requests.get(f"{self.backend_url}/golden-dataset", timeout=5)
            response.raise_for_status()
            datasets = response.json().get('datasets', [])
            entry_data = next((ds for ds in datasets if ds['id'] == entry_id), None)
            
            if entry_data:
                dialog = GoldenDatasetDialog(self.root, self.backend_url, mode="edit", data=entry_data)
                self.root.wait_window(dialog.dialog)
                if dialog.result:
                    self.refresh_list()
        except requests.exceptions.RequestException as e:
            messagebox.showerror("Fehler", f"Eintrag konnte nicht geladen werden:\n{str(e)}")
    
    def delete_entry(self):
        """Delete selected entry (not implemented in backend, show warning)"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Keine Auswahl", "Bitte wählen Sie einen Eintrag aus.")
            return
        
        item = self.tree.item(selection[0])
        entry_id = item['values'][0]
        
        if messagebox.askyesno("Löschen bestätigen", 
                              f"Eintrag #{entry_id} wirklich löschen?\n\nHINWEIS: DELETE Endpoint noch nicht implementiert."):
            messagebox.showinfo("Info", "DELETE Endpoint muss noch im Backend implementiert werden.")
    
    def export_to_csv(self):
        """Export current view to CSV"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV Dateien", "*.csv"), ("Alle Dateien", "*.*")],
            initialfile=f"golden_dataset_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )
        
        if not filename:
            return
        
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                
                # Write header
                writer.writerow(["ID", "Dokument ID", "Klassifikation", "Qualität", "Geprüft von", "Erstellt am"])
                
                # Write data
                for item in self.tree.get_children():
                    values = self.tree.item(item)['values']
                    writer.writerow(values)
            
            messagebox.showinfo("Export erfolgreich", f"Daten exportiert nach:\n{filename}")
        except Exception as e:
            messagebox.showerror("Export Fehler", f"Fehler beim Exportieren:\n{str(e)}")


class GoldenDatasetDialog:
    """Dialog for creating/editing golden dataset entries"""
    
    def __init__(self, parent, backend_url: str, mode: str = "create", data: Optional[Dict] = None):
        self.backend_url = backend_url
        self.mode = mode
        self.result = False
        
        # Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(f"Golden Dataset - {'Neu' if mode == 'create' else 'Bearbeiten'}")
        self.dialog.geometry("600x500")
        self.dialog.configure(bg="#2b2b2b")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Form fields
        form_frame = tk.Frame(self.dialog, bg="#2b2b2b", padx=20, pady=20)
        form_frame.pack(fill=tk.BOTH, expand=True)
        
        # Document ID
        tk.Label(form_frame, text="Dokument ID:", bg="#2b2b2b", fg="white").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.doc_id_var = tk.StringVar(value=data.get('document_id', '') if data else '')
        tk.Entry(form_frame, textvariable=self.doc_id_var, width=40).grid(row=0, column=1, pady=5, sticky=tk.EW)
        
        # Classification
        tk.Label(form_frame, text="Klassifikation:", bg="#2b2b2b", fg="white").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.classification_var = tk.StringVar(value=data.get('classification', '') if data else '')
        classification_combo = ttk.Combobox(form_frame, textvariable=self.classification_var, width=38)
        classification_combo['values'] = ['Rechnung', 'Vertrag', 'Brief', 'E-Mail', 'Bestellung', 'Lieferschein', 'Andere']
        classification_combo.grid(row=1, column=1, pady=5, sticky=tk.EW)
        
        # Quality Score
        tk.Label(form_frame, text="Qualitätsscore:", bg="#2b2b2b", fg="white").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.quality_var = tk.DoubleVar(value=data.get('quality_score', 0.95) if data else 0.95)
        quality_frame = tk.Frame(form_frame, bg="#2b2b2b")
        quality_frame.grid(row=2, column=1, pady=5, sticky=tk.EW)
        tk.Scale(quality_frame, from_=0.0, to=1.0, resolution=0.01, orient=tk.HORIZONTAL, 
                variable=self.quality_var, bg="#2b2b2b", fg="white").pack(fill=tk.X)
        
        # Reviewed By
        tk.Label(form_frame, text="Geprüft von:", bg="#2b2b2b", fg="white").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.reviewer_var = tk.StringVar(value=data.get('reviewed_by', '') if data else '')
        tk.Entry(form_frame, textvariable=self.reviewer_var, width=40).grid(row=3, column=1, pady=5, sticky=tk.EW)
        
        # Review Date
        tk.Label(form_frame, text="Prüfdatum:", bg="#2b2b2b", fg="white").grid(row=4, column=0, sticky=tk.W, pady=5)
        self.review_date_var = tk.StringVar(value=data.get('review_date', datetime.now().strftime('%Y-%m-%d')) if data else datetime.now().strftime('%Y-%m-%d'))
        tk.Entry(form_frame, textvariable=self.review_date_var, width=40).grid(row=4, column=1, pady=5, sticky=tk.EW)
        
        # Notes
        tk.Label(form_frame, text="Notizen:", bg="#2b2b2b", fg="white").grid(row=5, column=0, sticky=tk.NW, pady=5)
        self.notes_text = tk.Text(form_frame, width=40, height=6, bg="#3c3f41", fg="white")
        self.notes_text.grid(row=5, column=1, pady=5, sticky=tk.EW)
        if data and data.get('notes'):
            self.notes_text.insert(1.0, data['notes'])
        
        # Buttons
        button_frame = tk.Frame(self.dialog, bg="#2b2b2b", pady=10)
        button_frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        tk.Button(button_frame, text="Speichern", command=self.save, bg="#4a90e2", fg="white", padx=20, pady=5).pack(side=tk.RIGHT, padx=10)
        tk.Button(button_frame, text="Abbrechen", command=self.dialog.destroy, bg="#95a5a6", fg="white", padx=20, pady=5).pack(side=tk.RIGHT)
        
        form_frame.columnconfigure(1, weight=1)
    
    def save(self):
        """Save entry to backend"""
        # Validate
        if not self.doc_id_var.get().strip():
            messagebox.showerror("Validierung", "Dokument ID ist erforderlich.")
            return
        if not self.classification_var.get().strip():
            messagebox.showerror("Validierung", "Klassifikation ist erforderlich.")
            return
        
        # Prepare data
        data = {
            "document_id": self.doc_id_var.get().strip(),
            "classification": self.classification_var.get().strip(),
            "quality_score": self.quality_var.get(),
            "reviewed_by": self.reviewer_var.get().strip(),
            "review_date": self.review_date_var.get().strip(),
            "notes": self.notes_text.get(1.0, tk.END).strip()
        }
        
        try:
            response = requests.post(f"{self.backend_url}/golden-dataset", json=data, timeout=5)
            response.raise_for_status()
            
            self.result = True
            messagebox.showinfo("Erfolg", f"Eintrag erfolgreich {'erstellt' if self.mode == 'create' else 'aktualisiert'}!")
            self.dialog.destroy()
            
        except requests.exceptions.RequestException as e:
            messagebox.showerror("Fehler", f"Fehler beim Speichern:\n{str(e)}")


def main():
    """Main entry point"""
    root = tk.Tk()
    app = GoldenDatasetManager(root)
    root.mainloop()


if __name__ == "__main__":
    main()
