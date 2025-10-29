from ingestionV2.core.provenance import deterministic_chunk_id


def test_deterministic_chunk_id_is_stable():
    a = deterministic_chunk_id("file.txt", 0)
    b = deterministic_chunk_id("file.txt", 0)
    assert a == b
    assert len(a) == 64


def test_deterministic_chunk_id_changes_with_index():
    a = deterministic_chunk_id("file.txt", 0)
    b = deterministic_chunk_id("file.txt", 1)
    assert a != b


def test_deterministic_chunk_id_changes_with_source():
    a = deterministic_chunk_id("fileA.txt", 0)
    b = deterministic_chunk_id("fileB.txt", 0)
    assert a != b
