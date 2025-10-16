from uds3.uds3_security import create_security_manager, SecurityLevel


def test_security_manager_generate_id():
    mgr = create_security_manager(SecurityLevel.INTERNAL)
    info = mgr.generate_secure_document_id("hello world", "file.txt")
    assert isinstance(info, dict)
    assert "document_id" in info
    assert "document_uuid" in info
    assert "content_hash" in info
