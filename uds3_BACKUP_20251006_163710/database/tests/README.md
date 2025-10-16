Test-Hinweis für `tests/test_import_guard.py`
=============================================

Wozu dient der Import-Guard?
-----------------------------
In einigen Windows- oder eingeschränkten Python-Umgebungen fehlt die Socket-Konstante
`socket.EAI_ADDRFAMILY`. Manche optionale Treiber (z. B. `neo4j`) erwarten diese Konstante
bei Import und werfen beim Laden eine Ausnahme. Das würde Tests beim Import der Adapter
sofort abbrechen.

Der Test-Import-Guard (`tests/test_import_guard.py`) setzt in Testumgebungen diese Konstante
vorsichtig, damit die Adapter importiert werden können und alternative Fallbacks (z. B. HTTP)
getestet werden können.

Wichtig:
- Dieser Monkeypatch ist ausschließlich für Tests gedacht. Bitte nicht in Produktionscode verwenden.
- Wenn du eine saubere Umgebung hast, entferne die Zeile aus `tests/test_all_configured_backends.py`,
  die das Guard-Modul importiert.

Deaktivieren / alternative Vorgehensweise
----------------------------------------
Wenn du den Guard nicht verwenden möchtest, kannst du die folgende Zeile am Anfang von
`tests/test_all_configured_backends.py` entfernen oder auskommentieren:

```python
try:
    import tests.test_import_guard as _import_guard
    _ = _import_guard.patched
except Exception:
    pass
```

Alternativ empfiehlt es sich, ein virtuelles Environment (`venv`) mit einer offiziellen CPython-Installation
zu verwenden, die die entsprechenden Socket-Konstanten bereitstellt.
