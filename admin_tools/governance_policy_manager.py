"""
Governance Policy Manager - Admin Tool
======================================

Tkinter GUI für CRUD Operations auf Governance Policies

Features:
- List/Search Governance Policies
- Create New Policies
- Update Existing Policies
- Delete Policies (soft delete)
- Filter by Type, Scope, Status
- Approval Workflow
- Export to JSON

Author: Covina Backend Team
Date: 17. Oktober 2025
Version: 1.0.0
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import requests
from datetime import datetime, timedelta
from typing import Optional, List, Dict
import json


class GovernancePolicyManager:
    """Admin GUI für Governance Policy Management"""
    
    def __init__(self, root: tk.Tk, backend_url: str = "http://127.0.0.1:45678"):
        self.root = root
        self.backend_url = backend_url
        self.current_policy: Optional[Dict] = None
        
        # Window Configuration
        self.root.title("Governance Policy Manager - Covina Admin")
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
        edit_menu.add_command(label="Neue Policy", command=self.show_create_dialog)
        edit_menu.add_command(label="Policy bearbeiten", command=self.show_edit_dialog)
        edit_menu.add_command(label="Policy löschen", command=self.delete_policy)
        edit_menu.add_separator()
        edit_menu.add_command(label="Policy genehmigen", command=self.approve_policy)
        
        # View Menu
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Ansicht", menu=view_menu)
        view_menu.add_command(label="Aktualisieren", command=self.refresh_list)
        view_menu.add_command(label="Nur aktive Policies", command=self.show_active_only)
        view_menu.add_command(label="Filter zurücksetzen", command=self.reset_filters)
    
    def _create_toolbar(self):
        """Create toolbar with quick actions"""
        toolbar = tk.Frame(self.root, bg="#3c3f41", height=50)
        toolbar.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        
        # Buttons
        btn_style = {"bg": "#4a90e2", "fg": "white", "padx": 15, "pady": 5}
        
        tk.Button(toolbar, text="➕ Neue Policy", command=self.show_create_dialog, **btn_style).pack(side=tk.LEFT, padx=5)
        tk.Button(toolbar, text="✏️ Bearbeiten", command=self.show_edit_dialog, **btn_style).pack(side=tk.LEFT, padx=5)
        tk.Button(toolbar, text="🗑️ Löschen", command=self.delete_policy, bg="#e74c3c", fg="white", padx=15, pady=5).pack(side=tk.LEFT, padx=5)
        tk.Button(toolbar, text="✅ Genehmigen", command=self.approve_policy, bg="#27ae60", fg="white", padx=15, pady=5).pack(side=tk.LEFT, padx=5)
        tk.Button(toolbar, text="🔄 Aktualisieren", command=self.refresh_list, **btn_style).pack(side=tk.LEFT, padx=5)
        tk.Button(toolbar, text="📊 Exportieren", command=self.export_to_json, **btn_style).pack(side=tk.LEFT, padx=5)
        
        # Connection Status
        self.status_label = tk.Label(toolbar, text="◉ Verbindung wird geprüft...", bg="#3c3f41", fg="yellow")
        self.status_label.pack(side=tk.RIGHT, padx=10)
        
        self._check_backend_connection()
    
    def _create_main_layout(self):
        """Create main layout with filters, table and details"""
        main_frame = tk.Frame(self.root, bg="#2b2b2b")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Left Panel - Filters
        filter_frame = tk.LabelFrame(main_frame, text="Filter", bg="#3c3f41", fg="white", padx=10, pady=10)
        filter_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 5))
        
        # Policy Type Filter
        tk.Label(filter_frame, text="Policy Type:", bg="#3c3f41", fg="white").pack(anchor=tk.W, pady=(5, 0))
        self.policy_type_var = tk.StringVar()
        self.policy_type_combo = ttk.Combobox(filter_frame, textvariable=self.policy_type_var, width=20)
        self.policy_type_combo['values'] = ['Alle', 'retention', 'access_control', 'classification', 
                                             'quality', 'audit', 'compliance', 'custom']
        self.policy_type_combo.current(0)
        self.policy_type_combo.pack(pady=5)
        
        # Scope Filter
        tk.Label(filter_frame, text="Scope:", bg="#3c3f41", fg="white").pack(anchor=tk.W, pady=(10, 0))
        self.scope_var = tk.StringVar()
        self.scope_combo = ttk.Combobox(filter_frame, textvariable=self.scope_var, width=20)
        self.scope_combo['values'] = ['Alle', 'global', 'department', 'project', 'document_type', 'custom']
        self.scope_combo.current(0)
        self.scope_combo.pack(pady=5)
        
        # Status Filter
        tk.Label(filter_frame, text="Status:", bg="#3c3f41", fg="white").pack(anchor=tk.W, pady=(10, 0))
        self.status_var = tk.StringVar()
        self.status_combo = ttk.Combobox(filter_frame, textvariable=self.status_var, width=20)
        self.status_combo['values'] = ['Alle', 'draft', 'pending', 'active', 'inactive', 'deprecated']
        self.status_combo.current(0)
        self.status_combo.pack(pady=5)
        
        # Active Only Checkbox
        self.active_only_var = tk.BooleanVar(value=False)
        tk.Checkbutton(filter_frame, text="Nur aktive Policies", variable=self.active_only_var,
                      bg="#3c3f41", fg="white", selectcolor="#2b2b2b").pack(anchor=tk.W, pady=(10, 0))
        
        # Filter Buttons
        tk.Button(filter_frame, text="Filter anwenden", command=self.apply_filters, 
                 bg="#4a90e2", fg="white", padx=10, pady=5).pack(pady=(20, 5), fill=tk.X)
        tk.Button(filter_frame, text="Zurücksetzen", command=self.reset_filters, 
                 bg="#95a5a6", fg="white", padx=10, pady=5).pack(pady=5, fill=tk.X)
        
        # Middle Panel - Table
        table_frame = tk.Frame(main_frame, bg="#2b2b2b")
        table_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        # Treeview
        columns = ("ID", "Name", "Type", "Scope", "Status", "Priorität", "Gültig von", "Genehmigt")
        self.tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=25)
        
        # Column Configuration
        self.tree.heading("ID", text="ID")
        self.tree.heading("Name", text="Policy Name")
        self.tree.heading("Type", text="Type")
        self.tree.heading("Scope", text="Scope")
        self.tree.heading("Status", text="Status")
        self.tree.heading("Priorität", text="Priorität")
        self.tree.heading("Gültig von", text="Gültig von")
        self.tree.heading("Genehmigt", text="Genehmigt")
        
        self.tree.column("ID", width=50, anchor=tk.CENTER)
        self.tree.column("Name", width=250)
        self.tree.column("Type", width=120)
        self.tree.column("Scope", width=100)
        self.tree.column("Status", width=90)
        self.tree.column("Priorität", width=70, anchor=tk.CENTER)
        self.tree.column("Gültig von", width=100)
        self.tree.column("Genehmigt", width=80, anchor=tk.CENTER)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Bind events
        self.tree.bind('<Double-1>', lambda e: self.show_edit_dialog())
        self.tree.bind('<<TreeviewSelect>>', self.on_policy_select)
        
        # Right Panel - Policy Details
        details_frame = tk.LabelFrame(main_frame, text="Policy Details", bg="#3c3f41", fg="white", padx=10, pady=10)
        details_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.details_text = scrolledtext.ScrolledText(details_frame, width=50, height=40, 
                                                      bg="#3c3f41", fg="white", wrap=tk.WORD)
        self.details_text.pack(fill=tk.BOTH, expand=True)
    
    def _create_status_bar(self):
        """Create status bar"""
        status_bar = tk.Frame(self.root, bg="#3c3f41", height=30)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.record_count_label = tk.Label(status_bar, text="Policies: 0", bg="#3c3f41", fg="white")
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
        """Refresh policy list from backend"""
        try:
            # Build query parameters
            params = {}
            if filters:
                if filters.get('policy_type') and filters['policy_type'] != 'Alle':
                    params['policy_type'] = filters['policy_type']
                if filters.get('scope') and filters['scope'] != 'Alle':
                    params['scope'] = filters['scope']
                if filters.get('status') and filters['status'] != 'Alle':
                    params['status'] = filters['status']
                if filters.get('active_only'):
                    params['active_only'] = 'true'
            
            response = requests.get(f"{self.backend_url}/governance/policies", params=params, timeout=5)
            response.raise_for_status()
            
            data = response.json()
            policies = data.get('policies', [])
            
            # Clear existing items
            for item in self.tree.get_children():
                self.tree.delete(item)
            
            # Insert new items
            for policy in policies:
                approved = "✅" if policy.get('approved_at') else "⏳"
                
                self.tree.insert('', tk.END, values=(
                    policy.get('id', ''),
                    policy.get('name', ''),
                    policy.get('policy_type', ''),
                    policy.get('scope', ''),
                    policy.get('status', ''),
                    policy.get('priority', ''),
                    policy.get('effective_from', '')[:10] if policy.get('effective_from') else '',
                    approved
                ))
            
            # Update status
            self.record_count_label.config(text=f"Policies: {len(policies)}")
            self.info_label.config(text=f"Aktualisiert: {datetime.now().strftime('%H:%M:%S')}")
            
        except requests.exceptions.RequestException as e:
            messagebox.showerror("Verbindungsfehler", f"Backend nicht erreichbar:\n{str(e)}")
    
    def on_policy_select(self, event):
        """Handle policy selection"""
        selection = self.tree.selection()
        if not selection:
            return
        
        item = self.tree.item(selection[0])
        policy_id = item['values'][0]
        
        # Fetch policy from list
        try:
            response = requests.get(f"{self.backend_url}/governance/policies", timeout=5)
            response.raise_for_status()
            
            policies = response.json().get('policies', [])
            self.current_policy = next((p for p in policies if p['id'] == policy_id), None)
            
            if self.current_policy:
                self.display_policy_details(self.current_policy)
            
        except requests.exceptions.RequestException as e:
            self.details_text.delete(1.0, tk.END)
            self.details_text.insert(tk.END, f"Fehler beim Laden der Details:\n{str(e)}")
    
    def display_policy_details(self, policy: Dict):
        """Display policy details in text widget"""
        self.details_text.delete(1.0, tk.END)
        
        # Header
        self.details_text.insert(tk.END, f"{'='*50}\n", "header")
        self.details_text.insert(tk.END, f"Policy: {policy.get('name', 'N/A')}\n", "header")
        self.details_text.insert(tk.END, f"{'='*50}\n\n", "header")
        
        # Basic Info
        self.details_text.insert(tk.END, "📋 Grundinformationen:\n", "section")
        self.details_text.insert(tk.END, f"  ID: {policy.get('policy_id', 'N/A')}\n")
        self.details_text.insert(tk.END, f"  Type: {policy.get('policy_type', 'N/A')}\n")
        self.details_text.insert(tk.END, f"  Scope: {policy.get('scope', 'N/A')}\n")
        self.details_text.insert(tk.END, f"  Status: {policy.get('status', 'N/A')}\n")
        self.details_text.insert(tk.END, f"  Priorität: {policy.get('priority', 'N/A')}\n\n")
        
        # Description
        self.details_text.insert(tk.END, "📝 Beschreibung:\n", "section")
        self.details_text.insert(tk.END, f"  {policy.get('description', 'N/A')}\n\n")
        
        # Rules
        self.details_text.insert(tk.END, "⚙️ Regeln:\n", "section")
        rules = policy.get('rules', {})
        if isinstance(rules, dict):
            self.details_text.insert(tk.END, json.dumps(rules, indent=2, ensure_ascii=False) + "\n\n")
        else:
            self.details_text.insert(tk.END, f"  {rules}\n\n")
        
        # Validity Period
        self.details_text.insert(tk.END, "📅 Gültigkeitszeitraum:\n", "section")
        effective_from = policy.get('effective_from', 'N/A')
        effective_until = policy.get('effective_until', 'unbegrenzt')
        self.details_text.insert(tk.END, f"  Von: {effective_from[:19] if effective_from != 'N/A' else 'N/A'}\n")
        self.details_text.insert(tk.END, f"  Bis: {effective_until[:19] if effective_until != 'unbegrenzt' else 'unbegrenzt'}\n\n")
        
        # Approval Info
        self.details_text.insert(tk.END, "✅ Genehmigung:\n", "section")
        approved_by = policy.get('approved_by', 'Nicht genehmigt')
        approved_at = policy.get('approved_at')
        self.details_text.insert(tk.END, f"  Genehmigt von: {approved_by}\n")
        if approved_at:
            self.details_text.insert(tk.END, f"  Genehmigt am: {approved_at[:19]}\n\n")
        else:
            self.details_text.insert(tk.END, "  Status: ⏳ Ausstehend\n\n")
        
        # Metadata
        self.details_text.insert(tk.END, "📊 Metadaten:\n", "section")
        self.details_text.insert(tk.END, f"  Erstellt von: {policy.get('created_by', 'N/A')}\n")
        self.details_text.insert(tk.END, f"  Erstellt am: {policy.get('created_at', 'N/A')[:19]}\n")
        self.details_text.insert(tk.END, f"  Geändert am: {policy.get('updated_at', 'N/A')[:19]}\n")
        
        metadata = policy.get('metadata', {})
        if isinstance(metadata, dict) and metadata:
            self.details_text.insert(tk.END, f"\n  Zusätzliche Metadaten:\n")
            self.details_text.insert(tk.END, json.dumps(metadata, indent=4, ensure_ascii=False) + "\n")
    
    def apply_filters(self):
        """Apply current filters"""
        filters = {
            'policy_type': self.policy_type_var.get(),
            'scope': self.scope_var.get(),
            'status': self.status_var.get(),
            'active_only': self.active_only_var.get()
        }
        self.refresh_list(filters)
    
    def reset_filters(self):
        """Reset all filters"""
        self.policy_type_combo.current(0)
        self.scope_combo.current(0)
        self.status_combo.current(0)
        self.active_only_var.set(False)
        self.refresh_list()
    
    def show_active_only(self):
        """Show only active policies"""
        self.active_only_var.set(True)
        self.apply_filters()
    
    def show_create_dialog(self):
        """Show dialog to create new policy"""
        dialog = GovernancePolicyDialog(self.root, self.backend_url, mode="create")
        self.root.wait_window(dialog.dialog)
        if dialog.result:
            self.refresh_list()
    
    def show_edit_dialog(self):
        """Show dialog to edit selected policy"""
        if not self.current_policy:
            messagebox.showwarning("Keine Auswahl", "Bitte wählen Sie eine Policy aus.")
            return
        
        dialog = GovernancePolicyDialog(self.root, self.backend_url, mode="edit", data=self.current_policy)
        self.root.wait_window(dialog.dialog)
        if dialog.result:
            self.refresh_list()
    
    def approve_policy(self):
        """Approve selected policy"""
        if not self.current_policy:
            messagebox.showwarning("Keine Auswahl", "Bitte wählen Sie eine Policy aus.")
            return
        
        if self.current_policy.get('approved_at'):
            messagebox.showinfo("Bereits genehmigt", 
                              f"Diese Policy wurde bereits genehmigt von: {self.current_policy.get('approved_by')}")
            return
        
        # Approval dialog
        approver = tk.simpledialog.askstring("Genehmigung", "Ihr Name:")
        if not approver:
            return
        
        # Update policy with approval
        self.current_policy['approved_by'] = approver
        self.current_policy['approved_at'] = datetime.now().isoformat()
        self.current_policy['status'] = 'active'
        
        try:
            response = requests.post(f"{self.backend_url}/governance/policies", 
                                   json=self.current_policy, timeout=5)
            response.raise_for_status()
            
            messagebox.showinfo("Erfolg", f"Policy genehmigt von: {approver}")
            self.refresh_list()
            
        except requests.exceptions.RequestException as e:
            messagebox.showerror("Fehler", f"Fehler bei der Genehmigung:\n{str(e)}")
    
    def delete_policy(self):
        """Delete selected policy (soft delete - mark as inactive)"""
        if not self.current_policy:
            messagebox.showwarning("Keine Auswahl", "Bitte wählen Sie eine Policy aus.")
            return
        
        policy_name = self.current_policy.get('name')
        
        if messagebox.askyesno("Löschen bestätigen", 
                              f"Policy '{policy_name}' wirklich löschen?\n\n"
                              f"Die Policy wird als 'inactive' markiert (Soft Delete)."):
            # Soft delete: set status to inactive
            self.current_policy['status'] = 'inactive'
            
            try:
                response = requests.post(f"{self.backend_url}/governance/policies", 
                                       json=self.current_policy, timeout=5)
                response.raise_for_status()
                
                messagebox.showinfo("Erfolg", "Policy als inaktiv markiert.")
                self.refresh_list()
                
            except requests.exceptions.RequestException as e:
                messagebox.showerror("Fehler", f"Fehler beim Löschen:\n{str(e)}")
    
    def export_to_json(self):
        """Export all policies to JSON"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON Dateien", "*.json"), ("Alle Dateien", "*.*")],
            initialfile=f"governance_policies_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        
        if not filename:
            return
        
        try:
            response = requests.get(f"{self.backend_url}/governance/policies", timeout=5)
            response.raise_for_status()
            data = response.json()
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            messagebox.showinfo("Export erfolgreich", f"Daten exportiert nach:\n{filename}")
        except Exception as e:
            messagebox.showerror("Export Fehler", f"Fehler beim Exportieren:\n{str(e)}")


class GovernancePolicyDialog:
    """Dialog for creating/editing governance policies"""
    
    def __init__(self, parent, backend_url: str, mode: str = "create", data: Optional[Dict] = None):
        self.backend_url = backend_url
        self.mode = mode
        self.result = False
        
        # Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(f"Governance Policy - {'Neu' if mode == 'create' else 'Bearbeiten'}")
        self.dialog.geometry("800x700")
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
        
        # Tab 2: Rules
        rules_tab = tk.Frame(notebook, bg="#2b2b2b")
        notebook.add(rules_tab, text="Regeln")
        self._create_rules_tab(rules_tab, data)
        
        # Tab 3: Validity
        validity_tab = tk.Frame(notebook, bg="#2b2b2b")
        notebook.add(validity_tab, text="Gültigkeit")
        self._create_validity_tab(validity_tab, data)
        
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
        
        # Policy ID
        tk.Label(frame, text="Policy ID:", bg="#2b2b2b", fg="white").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.policy_id_var = tk.StringVar(value=data.get('policy_id', '') if data else '')
        tk.Entry(frame, textvariable=self.policy_id_var, width=40).grid(row=0, column=1, pady=5, sticky=tk.EW)
        
        # Name
        tk.Label(frame, text="Name:", bg="#2b2b2b", fg="white").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.name_var = tk.StringVar(value=data.get('name', '') if data else '')
        tk.Entry(frame, textvariable=self.name_var, width=40).grid(row=1, column=1, pady=5, sticky=tk.EW)
        
        # Policy Type
        tk.Label(frame, text="Type:", bg="#2b2b2b", fg="white").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.policy_type_var = tk.StringVar(value=data.get('policy_type', '') if data else '')
        type_combo = ttk.Combobox(frame, textvariable=self.policy_type_var, width=38)
        type_combo['values'] = ['retention', 'access_control', 'classification', 'quality', 'audit', 'compliance', 'custom']
        type_combo.grid(row=2, column=1, pady=5, sticky=tk.EW)
        
        # Scope
        tk.Label(frame, text="Scope:", bg="#2b2b2b", fg="white").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.scope_var = tk.StringVar(value=data.get('scope', '') if data else '')
        scope_combo = ttk.Combobox(frame, textvariable=self.scope_var, width=38)
        scope_combo['values'] = ['global', 'department', 'project', 'document_type', 'custom']
        scope_combo.grid(row=3, column=1, pady=5, sticky=tk.EW)
        
        # Status
        tk.Label(frame, text="Status:", bg="#2b2b2b", fg="white").grid(row=4, column=0, sticky=tk.W, pady=5)
        self.status_var = tk.StringVar(value=data.get('status', 'draft') if data else 'draft')
        status_combo = ttk.Combobox(frame, textvariable=self.status_var, width=38)
        status_combo['values'] = ['draft', 'pending', 'active', 'inactive', 'deprecated']
        status_combo.grid(row=4, column=1, pady=5, sticky=tk.EW)
        
        # Priority
        tk.Label(frame, text="Priorität:", bg="#2b2b2b", fg="white").grid(row=5, column=0, sticky=tk.W, pady=5)
        self.priority_var = tk.IntVar(value=data.get('priority', 100) if data else 100)
        tk.Spinbox(frame, from_=1, to=1000, textvariable=self.priority_var, width=38).grid(row=5, column=1, pady=5, sticky=tk.EW)
        
        # Description
        tk.Label(frame, text="Beschreibung:", bg="#2b2b2b", fg="white").grid(row=6, column=0, sticky=tk.NW, pady=5)
        self.description_text = tk.Text(frame, width=40, height=6, bg="#3c3f41", fg="white")
        self.description_text.grid(row=6, column=1, pady=5, sticky=tk.EW)
        if data and data.get('description'):
            self.description_text.insert(1.0, data['description'])
        
        # Created By
        tk.Label(frame, text="Erstellt von:", bg="#2b2b2b", fg="white").grid(row=7, column=0, sticky=tk.W, pady=5)
        self.created_by_var = tk.StringVar(value=data.get('created_by', '') if data else '')
        tk.Entry(frame, textvariable=self.created_by_var, width=40).grid(row=7, column=1, pady=5, sticky=tk.EW)
        
        frame.columnconfigure(1, weight=1)
    
    def _create_rules_tab(self, parent, data):
        """Create rules tab"""
        frame = tk.Frame(parent, bg="#2b2b2b", padx=20, pady=20)
        frame.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(frame, text="Regeln (JSON):", bg="#2b2b2b", fg="white").pack(anchor=tk.W, pady=(0, 5))
        
        self.rules_text = scrolledtext.ScrolledText(frame, bg="#3c3f41", fg="white", wrap=tk.WORD, height=25)
        self.rules_text.pack(fill=tk.BOTH, expand=True)
        
        # Load existing data or template
        if data and data.get('rules'):
            self.rules_text.insert(1.0, json.dumps(data['rules'], indent=2, ensure_ascii=False))
        else:
            template = {
                "retention_days": 3650,
                "action": "archive",
                "applies_to": ["Rechnung", "Vertrag"]
            }
            self.rules_text.insert(1.0, json.dumps(template, indent=2, ensure_ascii=False))
    
    def _create_validity_tab(self, parent, data):
        """Create validity period tab"""
        frame = tk.Frame(parent, bg="#2b2b2b", padx=20, pady=20)
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Effective From
        tk.Label(frame, text="Gültig ab:", bg="#2b2b2b", fg="white").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.effective_from_var = tk.StringVar(
            value=data.get('effective_from', datetime.now().strftime('%Y-%m-%d')) if data 
            else datetime.now().strftime('%Y-%m-%d')
        )
        tk.Entry(frame, textvariable=self.effective_from_var, width=30).grid(row=0, column=1, pady=5, sticky=tk.W)
        tk.Label(frame, text="(YYYY-MM-DD)", bg="#2b2b2b", fg="gray").grid(row=0, column=2, sticky=tk.W, padx=5)
        
        # Effective Until
        tk.Label(frame, text="Gültig bis:", bg="#2b2b2b", fg="white").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.effective_until_var = tk.StringVar(value=data.get('effective_until', '') if data else '')
        tk.Entry(frame, textvariable=self.effective_until_var, width=30).grid(row=1, column=1, pady=5, sticky=tk.W)
        tk.Label(frame, text="(leer = unbegrenzt)", bg="#2b2b2b", fg="gray").grid(row=1, column=2, sticky=tk.W, padx=5)
        
        # Metadata
        tk.Label(frame, text="Metadaten (JSON):", bg="#2b2b2b", fg="white").grid(row=2, column=0, sticky=tk.NW, pady=(20, 5))
        
        self.metadata_text = scrolledtext.ScrolledText(frame, bg="#3c3f41", fg="white", wrap=tk.WORD, height=15)
        self.metadata_text.grid(row=3, column=0, columnspan=3, pady=5, sticky=tk.EW)
        
        if data and data.get('metadata'):
            self.metadata_text.insert(1.0, json.dumps(data['metadata'], indent=2, ensure_ascii=False))
        else:
            self.metadata_text.insert(1.0, json.dumps({}, indent=2, ensure_ascii=False))
        
        frame.columnconfigure(1, weight=1)
    
    def save(self):
        """Save policy to backend"""
        # Validate basic fields
        if not self.policy_id_var.get().strip():
            messagebox.showerror("Validierung", "Policy ID ist erforderlich.")
            return
        if not self.name_var.get().strip():
            messagebox.showerror("Validierung", "Name ist erforderlich.")
            return
        
        # Parse JSON fields
        try:
            rules = json.loads(self.rules_text.get(1.0, tk.END))
            metadata = json.loads(self.metadata_text.get(1.0, tk.END))
        except json.JSONDecodeError as e:
            messagebox.showerror("JSON Fehler", f"Ungültiges JSON Format:\n{str(e)}")
            return
        
        # Prepare data
        data = {
            "policy_id": self.policy_id_var.get().strip(),
            "name": self.name_var.get().strip(),
            "description": self.description_text.get(1.0, tk.END).strip(),
            "policy_type": self.policy_type_var.get().strip(),
            "scope": self.scope_var.get().strip(),
            "rules": rules,
            "status": self.status_var.get().strip(),
            "priority": self.priority_var.get(),
            "effective_from": self.effective_from_var.get().strip(),
            "effective_until": self.effective_until_var.get().strip() or None,
            "created_by": self.created_by_var.get().strip(),
            "metadata": metadata
        }
        
        try:
            response = requests.post(f"{self.backend_url}/governance/policies", json=data, timeout=5)
            response.raise_for_status()
            
            self.result = True
            messagebox.showinfo("Erfolg", f"Policy erfolgreich {'erstellt' if self.mode == 'create' else 'aktualisiert'}!")
            self.dialog.destroy()
            
        except requests.exceptions.RequestException as e:
            messagebox.showerror("Fehler", f"Fehler beim Speichern:\n{str(e)}")


def main():
    """Main entry point"""
    root = tk.Tk()
    app = GovernancePolicyManager(root)
    root.mainloop()


if __name__ == "__main__":
    main()
