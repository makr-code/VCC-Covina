import pytest
import json
import tempfile
from pathlib import Path
from ingestion.config.config_loader import ConfigLoader


def test_load_yaml_file(tmp_path):
    config_file = tmp_path / "test.yaml"
    config_file.write_text("key: value\nnested:\n  item: 123")
    
    loader = ConfigLoader()
    config = loader.load_file(str(config_file))
    
    assert config["key"] == "value"
    assert config["nested"]["item"] == 123


def test_load_json_file(tmp_path):
    config_file = tmp_path / "test.json"
    config_file.write_text('{"key": "value", "number": 42}')
    
    loader = ConfigLoader()
    config = loader.load_file(str(config_file))
    
    assert config["key"] == "value"
    assert config["number"] == 42


def test_merge_configs_simple():
    loader = ConfigLoader()
    base = {"a": 1, "b": 2}
    override = {"b": 3, "c": 4}
    
    merged = loader.merge_configs([base, override])
    
    assert merged == {"a": 1, "b": 3, "c": 4}


def test_merge_configs_nested():
    loader = ConfigLoader()
    base = {"db": {"host": "localhost", "port": 5432}}
    override = {"db": {"port": 3000}}
    
    merged = loader.merge_configs([base, override])
    
    assert merged["db"]["host"] == "localhost"
    assert merged["db"]["port"] == 3000


def test_load_and_merge(tmp_path):
    base_file = tmp_path / "base.yaml"
    base_file.write_text("a: 1\nb: 2")
    
    override_file = tmp_path / "override.yaml"
    override_file.write_text("b: 3\nc: 4")
    
    loader = ConfigLoader()
    config = loader.load_and_merge([str(base_file), str(override_file)])
    
    assert config == {"a": 1, "b": 3, "c": 4}


def test_validate_with_schema(tmp_path):
    schema_file = tmp_path / "schema.json"
    schema_file.write_text(json.dumps({
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "age": {"type": "integer"}
        },
        "required": ["name"]
    }))
    
    loader = ConfigLoader(schema_path=str(schema_file))
    
    # Valid config
    loader.validate({"name": "Test", "age": 30})
    
    # Invalid config (missing required field)
    with pytest.raises(Exception):  # jsonschema.ValidationError
        loader.validate({"age": 30})


def test_file_not_found():
    loader = ConfigLoader()
    with pytest.raises(FileNotFoundError):
        loader.load_file("nonexistent.yaml")
