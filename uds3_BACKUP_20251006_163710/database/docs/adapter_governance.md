# `adapter_governance.py`

Kurzbeschreibung
-----------------
Implementiert Governance- und Policy-Prüfungen, die vor Backend-Operationen
ausgeführt werden. Erlaubt feingranulare Kontrolle (Allow/Deny), Reporting und
Fehlerauslösung mittels `AdapterGovernanceError`.

Analyse
-------
Das Modul bietet zentrale Kontrollmechanismen, die insbesondere in Saga-
Workflows genutzt werden, um sichere Ausführungen zu erzwingen. Die
Implementierung ist bewusst schlank gehalten: Policies werden üblicherweise als
Konfig-Dictionary geladen und auf Operationen angewendet.

Haupt-APIs / Funktionen
-----------------------
- `AdapterGovernance(policies: dict, strict: bool = True)`
  - Konstruktor: nimmt Policies entgegen, `strict` steuert Verhalten bei
    fehlender Regeldefinition.
- `ensure_operation_allowed(backend_key, operation)`
  - Hebt `AdapterGovernanceError` falls Aktion verboten ist.
- `enforce_payload_policy(backend_key, operation, payload)`
  - Validiert Payload anhand definierter Regeln (z. B. Feld-Whitelist,
    Size-Limits) und wirft ggf. `AdapterGovernanceError`.

Testabdeckung
-------------
- Covered indirectly by Saga-Tests, die Governance-Blockierungen simulieren.
- Empfehlung: Ein dedizierter Unit-Test für edge-cases (missing rules, strict vs lenient) wäre nützlich.

Roadmap / Empfehlungen
---------------------
- Policy-Sprache vereinheitlichen (z. B. JSON Schema oder Rego/OPA) für
  bessere Validierungs-Basis.
- Monitoring-Hooks: expose metrics (blocked_count, last_block_reason).
- Caching von Policy-Resolutions für häufige Operationen.

Beispiel
-------
```python
from database.adapter_governance import AdapterGovernance, AdapterGovernanceError
policies = {'relational': {'insert': {'allow': True}, 'delete': {'allow': False}}}
ag = AdapterGovernance(policies)
try:
    ag.ensure_operation_allowed('relational', 'delete')
except AdapterGovernanceError as exc:
    print('Operation blocked:', exc)
```