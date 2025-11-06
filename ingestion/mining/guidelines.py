from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import re

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    yaml = None  # type: ignore


@dataclass
class RuleEvidence:
    rule_id: str
    weight: float
    details: Dict[str, Any]


class RuleEngine:
    """
    YAML-gesteuerte Heuristiken und Mappings für Prozess-Inferenz.

    YAML Schema (Beispiel):
    ---
    version: 1
    normalize:
      authority:
        - pattern: "(?i)Landkreis ([A-Za-z-]+)"
          replace: "LK {1}"
      aktenzeichen:
        - pattern: "([A-Z]{2,3})-([0-9]{3,6})/([0-9]{2,4})"
          group_map:
            series: 1
            number: 2
            year: 3
    signals:
      date_from_title:
        pattern: "(20[0-9]{2}-[01][0-9]-[0-3][0-9])"
    inference:
      steps:
        - id: intake
          if:
            any:
              - authority_matches: "^LK "
              - aktenzeichen.series_in: [AZ, V]
          weight: 0.6
        - id: review
          if:
            after_days: 7
          weight: 0.3
      transitions:
        - from: intake
          to: review
          if:
            min_days_between: 3
          weight: 0.4
    """

    def __init__(self, yaml_text: Optional[str] = None, yaml_path: Optional[str] = None):
        self.config: Dict[str, Any] = {}
        if yaml_text:
            self._load_yaml_text(yaml_text)
        elif yaml_path:
            self._load_yaml_file(yaml_path)

    def _load_yaml_text(self, text: str) -> None:
        if yaml is None:
            raise RuntimeError("PyYAML nicht installiert")
        self.config = yaml.safe_load(text) or {}

    def _load_yaml_file(self, path: str) -> None:
        if yaml is None:
            raise RuntimeError("PyYAML nicht installiert")
        with open(path, encoding="utf-8") as f:
            self.config = yaml.safe_load(f) or {}

    # --- Normalization helpers ---

    def normalize_authority(self, name: Optional[str]) -> Optional[str]:
        if not name:
            return None
        rules = (self.config.get("normalize", {}).get("authority") or [])
        for r in rules:
            pat = re.compile(r.get("pattern", ""))
            m = pat.search(name)
            if m:
                repl = r.get("replace")
                if repl:
                    return pat.sub(repl, name)
        return name.strip()

    def normalize_aktenzeichen(self, text: Optional[str]) -> Dict[str, Any]:
        result: Dict[str, Any] = {"raw": text or None}
        if not text:
            return result
        rules = (self.config.get("normalize", {}).get("aktenzeichen") or [])
        for r in rules:
            pat = re.compile(r.get("pattern", ""))
            m = pat.search(text)
            if m:
                group_map = r.get("group_map", {})
                for k, idx in group_map.items():
                    try:
                        result[k] = m.group(int(idx))
                    except Exception:
                        pass
                break
        return result

    # --- Inference rules ---

    def infer_steps(self, signals: Dict[str, Any]) -> List[RuleEvidence]:
        evidences: List[RuleEvidence] = []
        for step in (self.config.get("inference", {}).get("steps") or []):
            step_id = step.get("id")
            cond = step.get("if", {})
            if self._match_condition(cond, signals):
                evidences.append(RuleEvidence(step_id, float(step.get("weight", 0.1)), {"condition": cond}))
        return evidences

    def infer_transitions(self, signals: Dict[str, Any]) -> List[RuleEvidence]:
        evidences: List[RuleEvidence] = []
        for tr in (self.config.get("inference", {}).get("transitions") or []):
            tr_id = f"{tr.get('from')}->{tr.get('to')}"
            cond = tr.get("if", {})
            if self._match_condition(cond, signals):
                evidences.append(RuleEvidence(tr_id, float(tr.get("weight", 0.1)), {"condition": cond}))
        return evidences

    # --- Condition evaluation (minimal, extend as needed) ---

    def _match_condition(self, cond: Dict[str, Any], signals: Dict[str, Any]) -> bool:
        if not cond:
            return True
        if "any" in cond:
            return any(self._check_atom(atom, signals) for atom in cond["any"])
        if "all" in cond:
            return all(self._check_atom(atom, signals) for atom in cond["all"])
        return self._check_atom(cond, signals)

    def _check_atom(self, atom: Dict[str, Any], signals: Dict[str, Any]) -> bool:
        # authority_matches
        if "authority_matches" in atom:
            p = re.compile(atom["authority_matches"])
            return bool(p.search((signals.get("authority_norm") or "")))
        # aktenzeichen.series_in
        if "aktenzeichen.series_in" in atom:
            options = set(atom["aktenzeichen.series_in"])  # type: ignore
            series = ((signals.get("aktenzeichen") or {}).get("series"))
            return series in options
        # after_days / min_days_between – placeholder (needs date diffs in signals)
        if "after_days" in atom or "min_days_between" in atom:
            # For MVP we accept presence of date signal
            return bool(signals.get("date_iso"))
        return False
