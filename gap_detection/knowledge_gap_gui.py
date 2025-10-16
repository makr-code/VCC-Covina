# -*- coding: utf-8 -*-
"""
Knowledge Gap Management GUI

Tkinter-Frontend zur Sichtung, Bearbeitung und Verwaltung von Knowledge Gaps
im Covina-System. Bietet Tabellenansicht, Filter, Detail- und Editierdialoge,
Statusmanagement und Exportfunktionen.

Autor: Covina Team
Lizenz: AGPL-3.0
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import json
from gap_detection.database import KnowledgeGapDB
from datetime import datetime

class KnowledgeGapGUI(tk.Tk):
    def __init__(self, db_path="./data/knowledge_gaps.db"):
        super().__init__()
        self.title("Covina Knowledge Gap Management")
        self.geometry("1200x700")
        self.db = KnowledgeGapDB(db_path)
        self._setup_ui()
        self._load_gaps_async()

    def _setup_ui(self):
        # Filter Frame
        filter_frame = ttk.Frame(self)
        filter_frame.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(filter_frame, text="Typ:").pack(side=tk.LEFT)
        self.type_var = tk.StringVar()
        type_combo = ttk.Combobox(filter_frame, textvariable=self.type_var, width=15)
        type_combo['values'] = ("", "process", "reference", "compliance")
        type_combo.pack(side=tk.LEFT, padx=5)
        ttk.Label(filter_frame, text="Status:").pack(side=tk.LEFT)
        self.status_var = tk.StringVar()
        status_combo = ttk.Combobox(filter_frame, textvariable=self.status_var, width=15)
        status_combo['values'] = ("", "open", "in_progress", "resolved", "deferred")
        status_combo.pack(side=tk.LEFT, padx=5)
        ttk.Label(filter_frame, text="Suche:").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(filter_frame, textvariable=self.search_var, width=30)
        search_entry.pack(side=tk.LEFT, padx=5)
        ttk.Button(filter_frame, text="Filtern", command=self._load_gaps_async).pack(side=tk.LEFT, padx=5)
        ttk.Button(filter_frame, text="Export", command=self._export_gaps).pack(side=tk.RIGHT, padx=5)

        # Table Frame
        table_frame = ttk.Frame(self)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        columns = ("gap_id", "gap_type", "subtype", "title", "severity_level", "status", "detected_at")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="browse")
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=120 if col!="title" else 350, anchor=tk.W)
        self.tree.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        self.tree.bind("<Double-1>", self._on_gap_double_click)
        # Scrollbar
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Button Frame
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X, padx=10, pady=5)
        ttk.Button(btn_frame, text="Neu", command=self._new_gap_dialog).pack(side=tk.LEFT)
        ttk.Button(btn_frame, text="Bearbeiten", command=self._edit_selected_gap).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Als gelöst markieren", command=self._resolve_selected_gap).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Aktualisieren", command=self._load_gaps_async).pack(side=tk.RIGHT)

    def _load_gaps_async(self):
        threading.Thread(target=self._load_gaps, daemon=True).start()

    def _load_gaps(self):
        filters = {}
        if self.type_var.get():
            filters['gap_type'] = self.type_var.get()
        if self.status_var.get():
            filters['status'] = self.status_var.get()
        if self.search_var.get():
            filters['search'] = self.search_var.get()
        gaps = self.db.get_knowledge_gaps(filters, limit=500)
        self._update_table(gaps)

    def _update_table(self, gaps):
        def update():
            self.tree.delete(*self.tree.get_children())
            for gap in gaps:
                self.tree.insert('', tk.END, values=(
                    gap.get('gap_id'), gap.get('gap_type'), gap.get('subtype'),
                    gap.get('title'), gap.get('severity_level'),
                    gap.get('status'), gap.get('detected_at')
                ))
        self.after(0, update)

    def _on_gap_double_click(self, event):
        item = self.tree.selection()
        if item:
            gap_id = self.tree.item(item[0])['values'][0]
            gap = self._get_gap_by_id(gap_id)
            if gap:
                self._show_gap_detail_dialog(gap)

    def _get_gap_by_id(self, gap_id):
        gaps = self.db.get_knowledge_gaps({'gap_id': gap_id}, limit=1)
        return gaps[0] if gaps else None

    def _show_gap_detail_dialog(self, gap):
        dlg = tk.Toplevel(self)
        dlg.title(f"Gap Details: {gap.get('gap_id')}")
        dlg.geometry("700x500")
        frame = ttk.Frame(dlg)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        row = 0
        for key in ["gap_id", "gap_type", "subtype", "title", "description", "severity_level", "business_impact_score", "status", "detected_at", "updated_at"]:
            ttk.Label(frame, text=key+":", font=("Arial", 10, "bold")).grid(row=row, column=0, sticky=tk.W, pady=2)
            val = gap.get(key, "")
            if isinstance(val, (dict, list)):
                val = json.dumps(val, indent=2, ensure_ascii=False)
            ttk.Label(frame, text=str(val), wraplength=500, justify=tk.LEFT).grid(row=row, column=1, sticky=tk.W, pady=2)
            row += 1
        # Show reference/process data if present
        if gap.get('reference_data'):
            ttk.Label(frame, text="Reference Data:", font=("Arial", 10, "bold")).grid(row=row, column=0, sticky=tk.W, pady=2)
            ttk.Label(frame, text=json.dumps(gap['reference_data'], indent=2, ensure_ascii=False), wraplength=500, justify=tk.LEFT).grid(row=row, column=1, sticky=tk.W, pady=2)
            row += 1
        if gap.get('process_data'):
            ttk.Label(frame, text="Process Data:", font=("Arial", 10, "bold")).grid(row=row, column=0, sticky=tk.W, pady=2)
            ttk.Label(frame, text=json.dumps(gap['process_data'], indent=2, ensure_ascii=False), wraplength=500, justify=tk.LEFT).grid(row=row, column=1, sticky=tk.W, pady=2)
            row += 1
        ttk.Button(frame, text="Bearbeiten", command=lambda: [dlg.destroy(), self._edit_gap_dialog(gap)]).grid(row=row, column=0, pady=10)
        ttk.Button(frame, text="Schließen", command=dlg.destroy).grid(row=row, column=1, pady=10)

    def _edit_selected_gap(self):
        item = self.tree.selection()
        if item:
            gap_id = self.tree.item(item[0])['values'][0]
            gap = self._get_gap_by_id(gap_id)
            if gap:
                self._edit_gap_dialog(gap)

    def _edit_gap_dialog(self, gap):
        dlg = tk.Toplevel(self)
        dlg.title(f"Gap bearbeiten: {gap.get('gap_id')}")
        dlg.geometry("700x600")
        frame = ttk.Frame(dlg)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        entries = {}
        fields = ["title", "description", "severity_level", "business_impact_score", "status", "subtype"]
        for i, field in enumerate(fields):
            ttk.Label(frame, text=field+":").grid(row=i, column=0, sticky=tk.W, pady=2)
            val = gap.get(field, "")
            entry = ttk.Entry(frame, width=60)
            entry.insert(0, str(val))
            entry.grid(row=i, column=1, pady=2)
            entries[field] = entry
        def save():
            for field in fields:
                gap[field] = entries[field].get()
            try:
                self.db.store_knowledge_gap(gap)
                messagebox.showinfo("Erfolg", "Gap gespeichert.")
                dlg.destroy()
                self._load_gaps_async()
            except Exception as e:
                messagebox.showerror("Fehler", f"Speichern fehlgeschlagen: {e}")
        ttk.Button(frame, text="Speichern", command=save).grid(row=len(fields), column=0, pady=10)
        ttk.Button(frame, text="Abbrechen", command=dlg.destroy).grid(row=len(fields), column=1, pady=10)

    def _new_gap_dialog(self):
        dlg = tk.Toplevel(self)
        dlg.title("Neues Knowledge Gap anlegen")
        dlg.geometry("700x500")
        frame = ttk.Frame(dlg)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        entries = {}
        fields = ["gap_id", "gap_type", "subtype", "title", "description", "severity_level", "business_impact_score", "status"]
        for i, field in enumerate(fields):
            ttk.Label(frame, text=field+":").grid(row=i, column=0, sticky=tk.W, pady=2)
            entry = ttk.Entry(frame, width=60)
            entry.grid(row=i, column=1, pady=2)
            entries[field] = entry
        def create():
            gap = {field: entries[field].get() for field in fields}
            gap['detected_at'] = datetime.now().isoformat()
            try:
                self.db.store_knowledge_gap(gap)
                messagebox.showinfo("Erfolg", "Gap angelegt.")
                dlg.destroy()
                self._load_gaps_async()
            except Exception as e:
                messagebox.showerror("Fehler", f"Anlegen fehlgeschlagen: {e}")
        ttk.Button(frame, text="Anlegen", command=create).grid(row=len(fields), column=0, pady=10)
        ttk.Button(frame, text="Abbrechen", command=dlg.destroy).grid(row=len(fields), column=1, pady=10)

    def _resolve_selected_gap(self):
        item = self.tree.selection()
        if item:
            gap_id = self.tree.item(item[0])['values'][0]
            gap = self._get_gap_by_id(gap_id)
            if gap:
                if messagebox.askyesno("Bestätigen", "Gap als gelöst markieren?"):
                    try:
                        self.db.resolve_gap(gap_id, {"resolution_type": "manual", "description": "Manuell gelöst", "resolved_by": "GUI"})
                        messagebox.showinfo("Erfolg", "Gap als gelöst markiert.")
                        self._load_gaps_async()
                    except Exception as e:
                        messagebox.showerror("Fehler", f"Statusänderung fehlgeschlagen: {e}")

    def _export_gaps(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON Files", "*.json")])
        if file_path:
            try:
                self.db.export_gaps(file_path)
                messagebox.showinfo("Erfolg", f"Exportiert nach {file_path}")
            except Exception as e:
                messagebox.showerror("Fehler", f"Export fehlgeschlagen: {e}")

if __name__ == "__main__":
    app = KnowledgeGapGUI()
    app.mainloop()
