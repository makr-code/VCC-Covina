from uds3.uds3_core import UnifiedDatabaseStrategy


def test_generate_and_format_document_id():
    strategy = UnifiedDatabaseStrategy()
    # Use a deterministic preview
    file_path = "C:/tmp/test_document.txt"
    preview = "This is a test preview"
    doc_id = strategy._generate_document_id(file_path, preview)
    assert isinstance(doc_id, str)
    assert doc_id.startswith("doc_")
    # infer uuid from doc id if possible
    inferred = strategy._infer_uuid_from_document_id(doc_id)
    # _infer_uuid_from_document_id will only return a uuid if the hex part is 32 chars; our id is of that form
    assert inferred is not None


def test_format_document_id():
    strategy = UnifiedDatabaseStrategy()
    uuid = "12345678-1234-1234-1234-1234567890ab"
    formatted = strategy._format_document_id(uuid)
    assert formatted.startswith("doc_")
    assert "-" not in formatted
