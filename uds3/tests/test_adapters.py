import pytest

from uds3.uds3_adapters import InMemorySagaCrud


def test_inmemory_create_read_update_delete():
    store = InMemorySagaCrud()
    c = "documents"

    # create
    doc = store.create(c, {"title": "hello"})
    assert "id" in doc
    doc_id = doc["id"]

    # read
    read = store.read(c, doc_id)
    assert read is not None
    assert read["title"] == "hello"

    # update
    updated = store.update(c, doc_id, {"title": "changed", "count": 1})
    assert updated["title"] == "changed"
    assert updated["count"] == 1

    # delete
    ok = store.delete(c, doc_id)
    assert ok is True
    assert store.read(c, doc_id) is None


def test_update_nonexistent_raises():
    store = InMemorySagaCrud()
    with pytest.raises(KeyError):
        store.update("x", "nope", {"a": 1})
