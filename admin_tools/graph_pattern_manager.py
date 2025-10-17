"""
Graph Pattern Manager - Admin Tool
===================================

Tkinter GUI für CRUD Operations auf Graph Golden Datasets (Neo4j Patterns)

Features:
- List/Search Graph Patterns
- Create New Patterns
- Update Existing Patterns
- Delete Patterns
- Visualize Pattern Structure
- Export to JSON

Author: Covina Backend Team
Date: 17. Oktober 2025
Version: 1.0.0
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import requests
from datetime import datetime
from typing import Optional, List, Dict
import json


class GraphPatternManager:
    """Admin GUI für Graph Pattern Management"""
    
    def __init__(self, root: tk.Tk, backend_url: str = "http://127.0.0.1:45678"):
        self.root = root
        self.backend_url = backend_url
        self.current_pattern: Optional[Dict] = None
        
        # Window Configuration
        self.root.title("Graph Pattern Manager - Covina Admin")
        self.root.geometry("1600x900")
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
        file_menu.add_command(label="Exportieren (JSON)", command=self.export_to_json)
        file_menu.add_separator()
        file_menu.add_command(label="Beenden", command=self.root.quit)
        
        # Edit Menu
        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Bearbeiten", menu=edit_menu)
        edit_menu.add_command(label="Neues Pattern", command=self.show_create_dialog)
        edit_menu.add_command(label="Pattern bearbeiten", command=self.show_edit_dialog)
        edit_menu.add_command(label="Pattern löschen", command=self.delete_pattern)
        
        # View Menu
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Ansicht", menu=view_menu)
        view_menu.add_command(label="Aktualisieren", command=self.refresh_list)
        view_menu.add_command(label="Details anzeigen", command=self.show_pattern_details)
    
    def _create_toolbar(self):
        """Create toolbar with quick actions"""
        toolbar = tk.Frame(self.root, bg="#3c3f41", height=50)
        toolbar.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        
        # Buttons
        btn_style = {"bg": "#4a90e2", "fg": "white", "padx": 15, "pady": 5}
        
        tk.Button(toolbar, text="➕ Neues Pattern", command=self.show_create_dialog, **btn_style).pack(side=tk.LEFT, padx=5)
        tk.Button(toolbar, text="✏️ Bearbeiten", command=self.show_edit_dialog, **btn_style).pack(side=tk.LEFT, padx=5)
        tk.Button(toolbar, text="🗑️ Löschen", command=self.delete_pattern, bg="#e74c3c", fg="white", padx=15, pady=5).pack(side=tk.LEFT, padx=5)
        tk.Button(toolbar, text="📋 Details", command=self.show_pattern_details, **btn_style).pack(side=tk.LEFT, padx=5)
        tk.Button(toolbar, text="🔄 Aktualisieren", command=self.refresh_list, **btn_style).pack(side=tk.LEFT, padx=5)
        tk.Button(toolbar, text="📊 Exportieren", command=self.export_to_json, **btn_style).pack(side=tk.LEFT, padx=5)
        
        # Connection Status
        self.status_label = tk.Label(toolbar, text="◉ Verbindung wird geprüft...", bg="#3c3f41", fg="yellow")
        self.status_label.pack(side=tk.RIGHT, padx=10)
        
        self._check_backend_connection()
    
    def _create_main_layout(self):
        """Create main layout with pattern list and details"""
        main_frame = tk.Frame(self.root, bg="#2b2b2b")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Left Panel - Pattern List
        list_frame = tk.LabelFrame(main_frame, text="Graph Patterns", bg="#3c3f41", fg="white", padx=10, pady=10)
        list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        # Treeview
        columns = ("ID", "Name", "Kategorie", "Nodes", "Relations", "Verwendungen", "Erstellt")
        self.tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=25)
        
        # Column Configuration
        self.tree.heading("ID", text="ID")
        self.tree.heading("Name", text="Pattern Name")
        self.tree.heading("Kategorie", text="Kategorie")
        self.tree.heading("Nodes", text="Nodes")
        self.tree.heading("Relations", text="Relationen")
        self.tree.heading("Verwendungen", text="Verwendungen")
        self.tree.heading("Erstellt", text="Erstellt am")
        
        self.tree.column("ID", width=50, anchor=tk.CENTER)
        self.tree.column("Name", width=250)
        self.tree.column("Kategorie", width=150)
        self.tree.column("Nodes", width=70, anchor=tk.CENTER)
        self.tree.column("Relations", width=80, anchor=tk.CENTER)
        self.tree.column("Verwendungen", width=100, anchor=tk.CENTER)
        self.tree.column("Erstellt", width=150)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Bind events
        self.tree.bind('<Double-1>', lambda e: self.show_pattern_details())
        self.tree.bind('<<TreeviewSelect>>', self.on_pattern_select)
        
        # Right Panel - Pattern Details
        details_frame = tk.LabelFrame(main_frame, text="Pattern Details", bg="#3c3f41", fg="white", padx=10, pady=10)
        details_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.details_text = scrolledtext.ScrolledText(details_frame, width=60, height=40, 
                                                      bg="#3c3f41", fg="white", wrap=tk.WORD)
        self.details_text.pack(fill=tk.BOTH, expand=True)
    
    def _create_status_bar(self):
        """Create status bar"""
        status_bar = tk.Frame(self.root, bg="#3c3f41", height=30)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.record_count_label = tk.Label(status_bar, text="Patterns: 0", bg="#3c3f41", fg="white")
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
    
    def refresh_list(self):
        """Refresh pattern list from backend"""
        try:
            response = requests.get(f"{self.backend_url}/graph-golden-dataset", timeout=5)
            response.raise_for_status()
            
            data = response.json()
            patterns = data.get('patterns', [])
            
            # Clear existing items
            for item in self.tree.get_children():
                self.tree.delete(item)
            
            # Insert new items
            for pattern in patterns:
                nodes_def = pattern.get('nodes_definition', {})
                rels_def = pattern.get('relationships_definition', {})
                
                self.tree.insert('', tk.END, values=(
                    pattern.get('id', ''),
                    pattern.get('pattern_name', ''),
                    pattern.get('category', ''),
                    len(nodes_def.get('node_types', [])) if isinstance(nodes_def, dict) else 0,
                    len(rels_def.get('relationship_types', [])) if isinstance(rels_def, dict) else 0,
                    pattern.get('usage_count', 0),
                    pattern.get('created_at', '')[:19] if pattern.get('created_at') else ''
                ))
            
            # Update status
            self.record_count_label.config(text=f"Patterns: {len(patterns)}")
            self.info_label.config(text=f"Aktualisiert: {datetime.now().strftime('%H:%M:%S')}")
            
        except requests.exceptions.RequestException as e:
            messagebox.showerror("Verbindungsfehler", f"Backend nicht erreichbar:\n{str(e)}")
    
    def on_pattern_select(self, event):
        """Handle pattern selection"""
        selection = self.tree.selection()
        if not selection:
            return
        
        item = self.tree.item(selection[0])
        pattern_id = item['values'][0]
        
        # Fetch pattern details
        try:
            response = requests.get(f"{self.backend_url}/graph-golden-dataset/{pattern_id}", timeout=5)
            response.raise_for_status()
            
            self.current_pattern = response.json()
            self.display_pattern_details(self.current_pattern)
            
        except requests.exceptions.RequestException as e:
            self.details_text.delete(1.0, tk.END)
            self.details_text.insert(tk.END, f"Fehler beim Laden der Details:\n{str(e)}")
    
    def display_pattern_details(self, pattern: Dict):
        """Display pattern details in text widget"""
        self.details_text.delete(1.0, tk.END)
        
        # Header
        self.details_text.insert(tk.END, f"{'='*60}\n", "header")
        self.details_text.insert(tk.END, f"Pattern: {pattern.get('pattern_name', 'N/A')}\n", "header")
        self.details_text.insert(tk.END, f"{'='*60}\n\n", "header")
        
        # Basic Info
        self.details_text.insert(tk.END, "📋 Grundinformationen:\n", "section")
        self.details_text.insert(tk.END, f"  ID: {pattern.get('pattern_id', 'N/A')}\n")
        self.details_text.insert(tk.END, f"  Kategorie: {pattern.get('category', 'N/A')}\n")
        self.details_text.insert(tk.END, f"  Beschreibung: {pattern.get('description', 'N/A')}\n")
        self.details_text.insert(tk.END, f"  Verwendungen: {pattern.get('usage_count', 0)}\n\n")
        
        # Nodes
        self.details_text.insert(tk.END, "🔵 Node-Definitionen:\n", "section")
        nodes_def = pattern.get('nodes_definition', {})
        if isinstance(nodes_def, dict):
            node_types = nodes_def.get('node_types', [])
            for node_type in node_types:
                self.details_text.insert(tk.END, f"  • {node_type.get('type', 'N/A')}")
                if node_type.get('properties'):
                    self.details_text.insert(tk.END, f" (Properties: {', '.join(node_type['properties'])})")
                self.details_text.insert(tk.END, "\n")
        self.details_text.insert(tk.END, "\n")
        
        # Relationships
        self.details_text.insert(tk.END, "🔗 Relationen-Definitionen:\n", "section")
        rels_def = pattern.get('relationships_definition', {})
        if isinstance(rels_def, dict):
            rel_types = rels_def.get('relationship_types', [])
            for rel in rel_types:
                self.details_text.insert(tk.END, f"  • {rel.get('type', 'N/A')}")
                if rel.get('from_node') and rel.get('to_node'):
                    self.details_text.insert(tk.END, f" ({rel['from_node']} → {rel['to_node']})")
                self.details_text.insert(tk.END, "\n")
        self.details_text.insert(tk.END, "\n")
        
        # Validation Rules
        self.details_text.insert(tk.END, "✅ Validierungsregeln:\n", "section")
        validation = pattern.get('validation_rules', {})
        if isinstance(validation, dict):
            self.details_text.insert(tk.END, f"  Erforderliche Nodes: {validation.get('required_nodes', [])}\n")
            self.details_text.insert(tk.END, f"  Erforderliche Relationen: {validation.get('required_relationships', [])}\n")
        self.details_text.insert(tk.END, "\n")
        
        # Metadata
        self.details_text.insert(tk.END, "📊 Metadaten:\n", "section")
        self.details_text.insert(tk.END, f"  Erstellt von: {pattern.get('created_by', 'N/A')}\n")
        self.details_text.insert(tk.END, f"  Erstellt am: {pattern.get('created_at', 'N/A')[:19]}\n")
        self.details_text.insert(tk.END, f"  Geändert am: {pattern.get('updated_at', 'N/A')[:19]}\n")
        
        # JSON Preview
        self.details_text.insert(tk.END, "\n" + "="*60 + "\n")
        self.details_text.insert(tk.END, "📄 JSON Vorschau:\n", "section")
        self.details_text.insert(tk.END, json.dumps(pattern, indent=2, ensure_ascii=False))
    
    def show_pattern_details(self):
        """Show detailed pattern view in popup"""
        if not self.current_pattern:
            messagebox.showwarning("Keine Auswahl", "Bitte wählen Sie ein Pattern aus.")
            return
        
        # Create popup window
        detail_window = tk.Toplevel(self.root)
        detail_window.title(f"Pattern Details - {self.current_pattern.get('pattern_name', 'N/A')}")
        detail_window.geometry("800x600")
        detail_window.configure(bg="#2b2b2b")
        
        # JSON Display
        text_widget = scrolledtext.ScrolledText(detail_window, bg="#3c3f41", fg="white", wrap=tk.WORD)
        text_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        text_widget.insert(tk.END, json.dumps(self.current_pattern, indent=2, ensure_ascii=False))
        text_widget.config(state=tk.DISABLED)
    
    def show_create_dialog(self):
        """Show dialog to create new pattern"""
        dialog = GraphPatternDialog(self.root, self.backend_url, mode="create")
        self.root.wait_window(dialog.dialog)
        if dialog.result:
            self.refresh_list()
    
    def show_edit_dialog(self):
        """Show dialog to edit selected pattern"""
        if not self.current_pattern:
            messagebox.showwarning("Keine Auswahl", "Bitte wählen Sie ein Pattern aus.")
            return
        
        dialog = GraphPatternDialog(self.root, self.backend_url, mode="edit", data=self.current_pattern)
        self.root.wait_window(dialog.dialog)
        if dialog.result:
            self.refresh_list()
    
    def delete_pattern(self):
        """Delete selected pattern"""
        if not self.current_pattern:
            messagebox.showwarning("Keine Auswahl", "Bitte wählen Sie ein Pattern aus.")
            return
        
        pattern_id = self.current_pattern.get('pattern_id')
        pattern_name = self.current_pattern.get('pattern_name')
        
        if messagebox.askyesno("Löschen bestätigen", 
                              f"Pattern '{pattern_name}' (ID: {pattern_id}) wirklich löschen?\n\n"
                              f"HINWEIS: DELETE Endpoint noch nicht implementiert."):
            messagebox.showinfo("Info", "DELETE Endpoint muss noch im Backend implementiert werden.")
    
    def export_to_json(self):
        """Export all patterns to JSON"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON Dateien", "*.json"), ("Alle Dateien", "*.*")],
            initialfile=f"graph_patterns_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        
        if not filename:
            return
        
        try:
            response = requests.get(f"{self.backend_url}/graph-golden-dataset", timeout=5)
            response.raise_for_status()
            data = response.json()
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            messagebox.showinfo("Export erfolgreich", f"Daten exportiert nach:\n{filename}")
        except Exception as e:
            messagebox.showerror("Export Fehler", f"Fehler beim Exportieren:\n{str(e)}")


class GraphPatternDialog:
    """Dialog for creating/editing graph patterns"""
    
    def __init__(self, parent, backend_url: str, mode: str = "create", data: Optional[Dict] = None):
        self.backend_url = backend_url
        self.mode = mode
        self.result = False
        
        # Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(f"Graph Pattern - {'Neu' if mode == 'create' else 'Bearbeiten'}")
        self.dialog.geometry("900x700")
        self.dialog.configure(bg="#2b2b2b")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Create notebook for tabs
        notebook = ttk.Notebook(self.dialog)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Tab 1: Basic Info
        basic_tab = tk.Frame(notebook, bg="#2b2b2b")
        notebook.add(basic_tab, text="Grundinformationen")
        self._create_basic_tab(basic_tab, data)
        
        # Tab 2: Nodes
        nodes_tab = tk.Frame(notebook, bg="#2b2b2b")
        notebook.add(nodes_tab, text="Nodes")
        self._create_nodes_tab(nodes_tab, data)
        
        # Tab 3: Relationships
        rels_tab = tk.Frame(notebook, bg="#2b2b2b")
        notebook.add(rels_tab, text="Relationen")
        self._create_relationships_tab(rels_tab, data)
        
        # Tab 4: Validation
        val_tab = tk.Frame(notebook, bg="#2b2b2b")
        notebook.add(val_tab, text="Validierung")
        self._create_validation_tab(val_tab, data)
        
        # Buttons
        button_frame = tk.Frame(self.dialog, bg="#2b2b2b", pady=10)
        button_frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        tk.Button(button_frame, text="Speichern", command=self.save, 
                 bg="#4a90e2", fg="white", padx=20, pady=5).pack(side=tk.RIGHT, padx=10)
        tk.Button(button_frame, text="Abbrechen", command=self.dialog.destroy, 
                 bg="#95a5a6", fg="white", padx=20, pady=5).pack(side=tk.RIGHT)
    
    def _create_basic_tab(self, parent, data):
        """Create basic info tab"""
        frame = tk.Frame(parent, bg="#2b2b2b", padx=20, pady=20)
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Pattern ID
        tk.Label(frame, text="Pattern ID:", bg="#2b2b2b", fg="white").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.pattern_id_var = tk.StringVar(value=data.get('pattern_id', '') if data else '')
        tk.Entry(frame, textvariable=self.pattern_id_var, width=40).grid(row=0, column=1, pady=5, sticky=tk.EW)
        
        # Pattern Name
        tk.Label(frame, text="Pattern Name:", bg="#2b2b2b", fg="white").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.pattern_name_var = tk.StringVar(value=data.get('pattern_name', '') if data else '')
        tk.Entry(frame, textvariable=self.pattern_name_var, width=40).grid(row=1, column=1, pady=5, sticky=tk.EW)
        
        # Category
        tk.Label(frame, text="Kategorie:", bg="#2b2b2b", fg="white").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.category_var = tk.StringVar(value=data.get('category', '') if data else '')
        category_combo = ttk.Combobox(frame, textvariable=self.category_var, width=38)
        category_combo['values'] = ['workflow', 'compliance', 'organization', 'process', 'data_flow', 'custom']
        category_combo.grid(row=2, column=1, pady=5, sticky=tk.EW)
        
        # Description
        tk.Label(frame, text="Beschreibung:", bg="#2b2b2b", fg="white").grid(row=3, column=0, sticky=tk.NW, pady=5)
        self.description_text = tk.Text(frame, width=40, height=5, bg="#3c3f41", fg="white")
        self.description_text.grid(row=3, column=1, pady=5, sticky=tk.EW)
        if data and data.get('description'):
            self.description_text.insert(1.0, data['description'])
        
        # Created By
        tk.Label(frame, text="Erstellt von:", bg="#2b2b2b", fg="white").grid(row=4, column=0, sticky=tk.W, pady=5)
        self.created_by_var = tk.StringVar(value=data.get('created_by', '') if data else '')
        tk.Entry(frame, textvariable=self.created_by_var, width=40).grid(row=4, column=1, pady=5, sticky=tk.EW)
        
        frame.columnconfigure(1, weight=1)
    
    def _create_nodes_tab(self, parent, data):
        """Create nodes definition tab"""
        frame = tk.Frame(parent, bg="#2b2b2b", padx=20, pady=20)
        frame.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(frame, text="Node-Definitionen (JSON):", bg="#2b2b2b", fg="white").pack(anchor=tk.W, pady=(0, 5))
        
        self.nodes_text = scrolledtext.ScrolledText(frame, bg="#3c3f41", fg="white", wrap=tk.WORD, height=25)
        self.nodes_text.pack(fill=tk.BOTH, expand=True)
        
        # Load existing data or template
        if data and data.get('nodes_definition'):
            self.nodes_text.insert(1.0, json.dumps(data['nodes_definition'], indent=2, ensure_ascii=False))
        else:
            template = {
                "node_types": [
                    {
                        "type": "Document",
                        "properties": ["document_id", "title", "date"],
                        "required": True
                    }
                ]
            }
            self.nodes_text.insert(1.0, json.dumps(template, indent=2, ensure_ascii=False))
    
    def _create_relationships_tab(self, parent, data):
        """Create relationships definition tab"""
        frame = tk.Frame(parent, bg="#2b2b2b", padx=20, pady=20)
        frame.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(frame, text="Relationen-Definitionen (JSON):", bg="#2b2b2b", fg="white").pack(anchor=tk.W, pady=(0, 5))
        
        self.relationships_text = scrolledtext.ScrolledText(frame, bg="#3c3f41", fg="white", wrap=tk.WORD, height=25)
        self.relationships_text.pack(fill=tk.BOTH, expand=True)
        
        # Load existing data or template
        if data and data.get('relationships_definition'):
            self.relationships_text.insert(1.0, json.dumps(data['relationships_definition'], indent=2, ensure_ascii=False))
        else:
            template = {
                "relationship_types": [
                    {
                        "type": "RELATED_TO",
                        "from_node": "Document",
                        "to_node": "Document",
                        "properties": ["relation_type"],
                        "required": False
                    }
                ]
            }
            self.relationships_text.insert(1.0, json.dumps(template, indent=2, ensure_ascii=False))
    
    def _create_validation_tab(self, parent, data):
        """Create validation rules tab"""
        frame = tk.Frame(parent, bg="#2b2b2b", padx=20, pady=20)
        frame.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(frame, text="Validierungsregeln (JSON):", bg="#2b2b2b", fg="white").pack(anchor=tk.W, pady=(0, 5))
        
        self.validation_text = scrolledtext.ScrolledText(frame, bg="#3c3f41", fg="white", wrap=tk.WORD, height=25)
        self.validation_text.pack(fill=tk.BOTH, expand=True)
        
        # Load existing data or template
        if data and data.get('validation_rules'):
            self.validation_text.insert(1.0, json.dumps(data['validation_rules'], indent=2, ensure_ascii=False))
        else:
            template = {
                "required_nodes": ["Document"],
                "required_relationships": [],
                "min_nodes": 1,
                "max_nodes": 100
            }
            self.validation_text.insert(1.0, json.dumps(template, indent=2, ensure_ascii=False))
    
    def save(self):
        """Save pattern to backend"""
        # Validate basic fields
        if not self.pattern_id_var.get().strip():
            messagebox.showerror("Validierung", "Pattern ID ist erforderlich.")
            return
        if not self.pattern_name_var.get().strip():
            messagebox.showerror("Validierung", "Pattern Name ist erforderlich.")
            return
        
        # Parse JSON fields
        try:
            nodes_def = json.loads(self.nodes_text.get(1.0, tk.END))
            rels_def = json.loads(self.relationships_text.get(1.0, tk.END))
            validation = json.loads(self.validation_text.get(1.0, tk.END))
        except json.JSONDecodeError as e:
            messagebox.showerror("JSON Fehler", f"Ungültiges JSON Format:\n{str(e)}")
            return
        
        # Prepare data
        data = {
            "pattern_id": self.pattern_id_var.get().strip(),
            "pattern_name": self.pattern_name_var.get().strip(),
            "category": self.category_var.get().strip(),
            "description": self.description_text.get(1.0, tk.END).strip(),
            "nodes_definition": nodes_def,
            "relationships_definition": rels_def,
            "validation_rules": validation,
            "created_by": self.created_by_var.get().strip()
        }
        
        try:
            response = requests.post(f"{self.backend_url}/graph-golden-dataset", json=data, timeout=5)
            response.raise_for_status()
            
            self.result = True
            messagebox.showinfo("Erfolg", f"Pattern erfolgreich {'erstellt' if self.mode == 'create' else 'aktualisiert'}!")
            self.dialog.destroy()
            
        except requests.exceptions.RequestException as e:
            messagebox.showerror("Fehler", f"Fehler beim Speichern:\n{str(e)}")


def main():
    """Main entry point"""
    root = tk.Tk()
    app = GraphPatternManager(root)
    root.mainloop()


if __name__ == "__main__":
    main()
