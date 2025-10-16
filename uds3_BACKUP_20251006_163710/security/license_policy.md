# UDS3 License & Protection Keys Policy

Datum: 2025-10-01

Zweck
-----
Dieses Dokument beschreibt das verpflichtende Vorgehen bei Dateien, die eingebettete Lizenz- oder Schutzmarker (z. B. `module_licence_key`, `module_file_key`, `VERITAS PROTECTION KEYS`) enthalten. Ziel ist, Änderungen rechtssicher, nachvollziehbar und auditierbar zu gestalten.

Geltungsbereich
---------------
Gilt für alle Entwickler und Repositories, die mit dem UDS3-Code arbeiten. Betroffene Dateien sind im `security/key_inventory.md` aufgelistet.

Grundsatz
---------
- Niemals Schlüssel oder Lizenzdaten im Klartext in VCS ändern oder entfernen ohne formelle Genehmigung.
- Keine Geheimnisse in Repo ablegen. Schutz- bzw. Lizenz-Marker dürfen zwar in Dateien stehen (siehe Inventory), Schlüsselwerte jedoch nicht in Commits geändert werden.

Verfahren für Änderungen an geschützten Dateien
------------------------------------------------
1. Ticket anlegen
   - Erstelle ein Issue mit dem Template "License change request" (siehe `.github/ISSUE_TEMPLATE/license-change-request.md`).
   - Füge die Liste betroffener Dateien hinzu und beschreibe den Änderungsbedarf.

2. Review & Legal Approval
   - Das Issue muss von einem Tech-Lead und von der Rechts-/Lizenzabteilung genehmigt werden.
   - Bei Bedarf muss eine Non-Disclosure/License-Agreement-Prüfung erfolgen.

3. Secure Implementation
   - Nach Genehmigung wird die Änderung so vorgenommen, dass keine Klartext-Schlüssel in Code verbleiben. Mögliche Patterns:
     - Schlüssel aus Konfiguration/Environment laden (z. B. `os.environ["VERITAS_KEY"]`)
     - Nutzung eines Secret Stores (HashiCorp Vault, Azure KeyVault, AWS Secrets Manager)
     - Referenz auf interne Lizenz-Management-API

4. Audit Trail
   - In jedem Commit/PR muss die genehmigende Person/Referenz (Issue-Number, Approval-Email) dokumentiert werden.
   - Security/key_inventory.md muss nach Änderungen aktualisiert werden.

Checkliste für License‑Change PRs
---------------------------------
- [ ] Issue existiert und ist verlinkt
- [ ] Written approval von Rechts/Licensing vorhanden (attach proof)
- [ ] Änderungen entfernen keine unerwünschten Binary/Secret‑Artefakte
- [ ] Unit-Tests und CI laufen grün
- [ ] Security inventory aktualisiert

Kontakt & Escalation
---------------------
- Erstkontakt: Projekt‑Techlead (in repo README / team docs)
- Legal/Licensing: licensing@veritas.example (oder interner Kontakt im Unternehmen)

Anmerkung
---------
Dieses Policy‑Dokument ist minimal und dient als Arbeitsgrundlage. Es ersetzt nicht die offizielle rechtliche Freigabe durch die Lizenzhalter.
