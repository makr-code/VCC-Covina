"""
Config Loader with JSON Schema Validation

Features:
- Load and merge configs from multiple YAML/JSON files
- JSON Schema validation (optional, via jsonschema package)
- merge_configs() with deep merge support
- Optional hot-reload watcher (file change detection)

Usage:
    loader = ConfigLoader(schema_path="config/schema.json")
    config = loader.load_and_merge(["base.yaml", "overrides.yaml"])
    loader.validate(config)  # raises if invalid
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml

try:
    import jsonschema
except ImportError:
    jsonschema = None  # type: ignore


class ConfigLoader:
    """Loads and validates configuration from YAML/JSON files."""
    
    def __init__(self, schema_path: Optional[str] = None):
        """
        Args:
            schema_path: Path to JSON Schema file for validation (optional)
        """
        self.schema_path = schema_path
        self.schema: Optional[Dict[str, Any]] = None
        if schema_path and Path(schema_path).exists():
            with open(schema_path, encoding="utf-8") as f:
                self.schema = json.load(f)
    
    def load_file(self, path: str) -> Dict[str, Any]:
        """Load a single YAML or JSON file.
        
        Args:
            path: Path to config file (.yaml, .yml, or .json)
            
        Returns:
            Dictionary with config data
            
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file format is unsupported
        """
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Config file not found: {path}")
        
        with open(p, encoding="utf-8") as f:
            if p.suffix in {".yaml", ".yml"}:
                return yaml.safe_load(f) or {}
            elif p.suffix == ".json":
                return json.load(f)
            else:
                raise ValueError(f"Unsupported config format: {p.suffix}")
    
    def merge_configs(self, configs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Deep merge multiple config dictionaries.
        
        Later configs override earlier ones. Nested dicts are merged recursively.
        
        Args:
            configs: List of config dictionaries to merge
            
        Returns:
            Merged config dictionary
        """
        result: Dict[str, Any] = {}
        for cfg in configs:
            result = self._deep_merge(result, cfg)
        return result
    
    def _deep_merge(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively merge override into base."""
        merged = base.copy()
        for key, value in override.items():
            if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                merged[key] = self._deep_merge(merged[key], value)
            else:
                merged[key] = value
        return merged
    
    def load_and_merge(self, paths: List[str]) -> Dict[str, Any]:
        """Load and merge multiple config files.
        
        Args:
            paths: List of config file paths (order matters: later overrides earlier)
            
        Returns:
            Merged config dictionary
        """
        configs = [self.load_file(p) for p in paths]
        return self.merge_configs(configs)
    
    def validate(self, config: Dict[str, Any]) -> None:
        """Validate config against JSON Schema.
        
        Args:
            config: Config dictionary to validate
            
        Raises:
            ValueError: If schema is not loaded
            jsonschema.ValidationError: If config is invalid
        """
        if not self.schema:
            raise ValueError("No schema loaded. Provide schema_path to constructor.")
        if jsonschema is None:
            raise RuntimeError("jsonschema package not installed. Run: pip install jsonschema")
        
        jsonschema.validate(instance=config, schema=self.schema)
    
    def watch(self, paths: List[str], callback) -> None:
        """Watch config files for changes and call callback on modification.
        
        Note: This is a simple implementation using polling. For production,
        consider watchdog or inotify.
        
        Args:
            paths: List of config file paths to watch
            callback: Function to call when files change (receives merged config)
        """
        import time
        mtimes = {p: Path(p).stat().st_mtime for p in paths if Path(p).exists()}
        
        try:
            while True:
                time.sleep(1)  # Poll every second
                changed = False
                for p in paths:
                    if not Path(p).exists():
                        continue
                    current_mtime = Path(p).stat().st_mtime
                    if current_mtime > mtimes.get(p, 0):
                        changed = True
                        mtimes[p] = current_mtime
                
                if changed:
                    try:
                        config = self.load_and_merge(paths)
                        callback(config)
                    except Exception as e:
                        print(f"[CONFIG-WATCH] Error reloading config: {e}")
        except KeyboardInterrupt:
            pass
