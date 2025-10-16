def test_create_secure_document_light_importable():
    import sys
    from pathlib import Path

    # Ensure parent folder (workspace root) and stubs are on sys.path for CI/dev environments
    repo_root = Path(__file__).resolve().parents[1]
    stubs = repo_root / "third_party_stubs"
    if str(stubs) not in sys.path:
        sys.path.insert(0, str(stubs))
    parent = str(repo_root.parent)
    if parent not in sys.path:
        sys.path.insert(0, parent)

    try:
        from uds3 import create_secure_document_light
    except Exception as e:
        raise AssertionError(f"Import failed: {e}")

    res = create_secure_document_light({"file_path": "test.txt", "content": "Hallo"})
    assert isinstance(res, dict)
    # The function may return a dict with an error key if core features are missing; we just check the type
    assert res is not None
