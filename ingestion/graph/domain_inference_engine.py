"""
Dynamic Domain Inference Engine
================================

Self-learning, YAML-based domain inference system that:
1. Loads rules from config/domain_inference_rules.yaml
2. Learns new patterns during ingestion
3. Auto-updates rules file with learned patterns
4. Tracks statistics and confidence scores

Usage:
    from ingestion.graph.domain_inference_engine import DomainInferenceEngine
    
    engine = DomainInferenceEngine()
    domain, confidence = engine.infer(file_path="vg_hamburg_case.md", classification="RECHTSPRECHUNG")
    
    # Learn from successful classification
    engine.learn_pattern(file_path="vg_hamburg_case.md", domain="verwaltungsrecht", confidence=0.95)
    
    # Save learned patterns
    engine.save_rules()
"""

import logging
import re
import yaml
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class DomainInferenceEngine:
    """
    Dynamic, self-learning domain inference engine.
    """
    
    def __init__(self, rules_file: str = "config/domain_inference_rules.yaml"):
        """
        Initialize engine with YAML rules file.
        
        Args:
            rules_file: Path to YAML rules configuration
        """
        self.rules_file = Path(rules_file)
        self.rules = self._load_rules()
        
        # In-memory learning buffers
        self.learned_patterns = defaultdict(list)  # domain → [(pattern, count, confidence)]
        self.inference_stats = {
            "total": 0,
            "success": 0,
            "failed": 0,
            "by_domain": defaultdict(int)
        }
        
        logger.info(f"[INIT] Domain Inference Engine loaded from {rules_file}")
        logger.info(f"[INIT] Loaded {len(self.rules['keyword_mappings'])} keyword rules")
        logger.info(f"[INIT] Loaded {len(self.rules['court_mappings'])} court rules")
        logger.info(f"[INIT] Auto-learning: {'ENABLED' if self.rules['auto_learning']['enabled'] else 'DISABLED'}")
    
    def _load_rules(self) -> Dict:
        """Load rules from YAML file."""
        if not self.rules_file.exists():
            logger.warning(f"[WARNING] Rules file not found: {self.rules_file}")
            logger.warning(f"[WARNING] Creating default rules file")
            self._create_default_rules()
        
        with open(self.rules_file, "r", encoding="utf-8") as f:
            rules = yaml.safe_load(f)
        
        return rules
    
    def _create_default_rules(self):
        """Create default rules file if missing."""
        # This would contain the full YAML template
        # For now, raise error if file missing
        raise FileNotFoundError(
            f"Rules file not found: {self.rules_file}. "
            f"Please create config/domain_inference_rules.yaml"
        )
    
    def infer(
        self,
        file_path: str,
        classification: Optional[str] = None,
        legal_terms_count: int = 0,
        content: Optional[str] = None
    ) -> Tuple[Optional[str], float]:
        """
        Infer legal domain from document metadata.
        
        Args:
            file_path: Document file path
            classification: Document classification (RECHTSPRECHUNG, VERTRAG, etc.)
            legal_terms_count: Number of legal terms found
            content: Optional full document text (for statutory refs)
        
        Returns:
            (domain_id, confidence) or (None, 0.0) if no match
        """
        self.inference_stats["total"] += 1
        
        # Try inference strategies in order of confidence
        strategies = [
            ("court", self._infer_from_court),
            ("keyword", self._infer_from_keywords),
            ("statutory", self._infer_from_statutory_refs),
        ]
        
        best_match = None
        best_confidence = 0.0
        
        for strategy_name, strategy_func in strategies:
            domain, confidence = strategy_func(file_path, classification, legal_terms_count, content)
            
            if domain and confidence > best_confidence:
                best_match = domain
                best_confidence = confidence
                logger.debug(f"[INFER] Strategy '{strategy_name}' → {domain} ({confidence:.2f})")
        
        # Apply confidence boosters
        if best_match:
            best_confidence = self._apply_boosters(best_confidence, legal_terms_count)
            self.inference_stats["success"] += 1
            self.inference_stats["by_domain"][best_match] += 1
        else:
            self.inference_stats["failed"] += 1
        
        return best_match, best_confidence
    
    def _infer_from_keywords(
        self,
        file_path: str,
        classification: Optional[str],
        legal_terms_count: int,
        content: Optional[str]
    ) -> Tuple[Optional[str], float]:
        """Infer from keyword mappings."""
        if not file_path:
            return None, 0.0
        
        normalized = file_path.lower()
        
        for mapping in self.rules["keyword_mappings"]:
            for keyword in mapping["keywords"]:
                if keyword.lower() in normalized:
                    return mapping["domain"], mapping["confidence"]
        
        return None, 0.0
    
    def _infer_from_court(
        self,
        file_path: str,
        classification: Optional[str],
        legal_terms_count: int,
        content: Optional[str]
    ) -> Tuple[Optional[str], float]:
        """Infer from court name patterns."""
        if not file_path:
            return None, 0.0
        
        normalized = file_path.lower()
        
        for mapping in self.rules["court_mappings"]:
            for pattern in mapping["patterns"]:
                if pattern.lower() in normalized:
                    logger.debug(f"[COURT] Matched '{pattern}' → {mapping['domain']}")
                    return mapping["domain"], mapping["confidence"]
        
        return None, 0.0
    
    def _infer_from_statutory_refs(
        self,
        file_path: str,
        classification: Optional[str],
        legal_terms_count: int,
        content: Optional[str]
    ) -> Tuple[Optional[str], float]:
        """Infer from statutory references (BGB, StGB, etc.)."""
        if not content:
            return None, 0.0
        
        content_lower = content.lower()
        
        for ref in self.rules["statutory_refs"]:
            for pattern in ref["patterns"]:
                if pattern.lower() in content_lower:
                    return ref["domain"], ref["confidence"]
        
        return None, 0.0
    
    def _apply_boosters(self, base_confidence: float, legal_terms_count: int) -> float:
        """Apply confidence boosters based on metadata quality."""
        confidence = base_confidence
        
        for booster in self.rules["confidence_rules"]["boosters"]:
            condition = booster["condition"]
            
            # Evaluate condition (simplified - could use eval() or AST)
            if "legal_terms_count > 50" in condition and legal_terms_count > 50:
                confidence = min(confidence + booster["boost"], booster["max_confidence"])
            elif "legal_terms_count > 100" in condition and legal_terms_count > 100:
                confidence = min(confidence + booster["boost"], booster["max_confidence"])
        
        return confidence
    
    def learn_pattern(
        self,
        file_path: str,
        domain: str,
        confidence: float,
        source: str = "auto"
    ):
        """
        Learn a new pattern from successful inference.
        
        Args:
            file_path: Document file path that matched
            domain: Inferred domain
            confidence: Confidence score
            source: "auto" (learned) or "manual" (user correction)
        """
        if not self.rules["auto_learning"]["enabled"]:
            return
        
        # Check quality thresholds
        min_conf = self.rules["auto_learning"]["quality_thresholds"]["min_confidence_to_learn"]
        if confidence < min_conf:
            return
        
        # Extract pattern from file path
        pattern = self._extract_pattern(file_path)
        if not pattern:
            return
        
        # Add to learning buffer
        self.learned_patterns[domain].append({
            "pattern": pattern,
            "confidence": confidence,
            "source": source,
            "learned_at": datetime.now().isoformat()
        })
        
        logger.debug(f"[LEARN] Pattern '{pattern}' → {domain} ({confidence:.2f})")
    
    def _extract_pattern(self, file_path: str) -> Optional[str]:
        """
        Extract meaningful pattern from file path.
        
        Examples:
            "VG Hamburg_case.md" → "vg hamburg"
            "arbeitsgericht_berlin.md" → "arbeitsgericht"
        """
        if not file_path:
            return None
        
        # Remove ignored patterns
        ignored = self.rules["auto_learning"]["pattern_extraction"]["ignore_patterns"]
        for ignore in ignored:
            file_path = file_path.replace(ignore, "")
        
        # Extract meaningful tokens
        tokens = re.findall(r'\b\w+\b', file_path.lower())
        
        # Filter by length
        min_len = self.rules["auto_learning"]["pattern_extraction"]["min_pattern_length"]
        max_len = self.rules["auto_learning"]["pattern_extraction"]["max_pattern_length"]
        
        valid_tokens = [t for t in tokens if min_len <= len(t) <= max_len]
        
        if not valid_tokens:
            return None
        
        # Return most significant token (longest, or court name if present)
        court_keywords = ["gericht", "court", "vg", "ag", "lg", "olg"]
        for token in valid_tokens:
            if any(ck in token for ck in court_keywords):
                return token
        
        # Return longest token
        return max(valid_tokens, key=len) if valid_tokens else None
    
    def save_rules(self, backup: bool = True):
        """
        Save learned patterns to YAML rules file.
        
        Args:
            backup: Create backup before saving
        """
        if not self.rules["auto_learning"]["auto_save"]["enabled"]:
            logger.info("[SAVE] Auto-save disabled, skipping")
            return
        
        # Create backup
        if backup and self.rules["auto_learning"]["auto_save"]["backup_on_save"]:
            backup_file = self.rules_file.with_suffix(f".{datetime.now().strftime('%Y%m%d_%H%M%S')}.yaml.bak")
            import shutil
            shutil.copy(self.rules_file, backup_file)
            logger.info(f"[BACKUP] Rules backed up to {backup_file}")
        
        # Promote learned patterns to rules
        min_occurrences = self.rules["auto_learning"]["learn_from_success"]["min_occurrences"]
        
        for domain, patterns in self.learned_patterns.items():
            # Count pattern occurrences
            pattern_counts = Counter(p["pattern"] for p in patterns)
            
            for pattern, count in pattern_counts.items():
                if count >= min_occurrences:
                    # Check if pattern already exists
                    exists = any(
                        pattern in mapping["keywords"]
                        for mapping in self.rules["keyword_mappings"]
                        if mapping["domain"] == domain
                    )
                    
                    if not exists:
                        # Add as new keyword mapping
                        self.rules["keyword_mappings"].append({
                            "keywords": [pattern],
                            "domain": domain,
                            "confidence": 0.8,  # Default for learned patterns
                            "tier": 3,
                            "source": "auto_learned"
                        })
                        logger.info(f"[PROMOTE] Learned pattern '{pattern}' -> {domain} (count: {count})")
        
        # Update metadata
        self.rules["metadata"]["last_updated"] = datetime.now().isoformat()
        self.rules["metadata"]["total_mappings"] = len(self.rules["keyword_mappings"])
        self.rules["metadata"]["auto_learned_mappings"] = len([
            m for m in self.rules["keyword_mappings"] if m.get("source") == "auto_learned"
        ])
        
        # Update learning stats
        self.rules["learning_stats"]["total_inferences"] = self.inference_stats["total"]
        self.rules["learning_stats"]["successful_inferences"] = self.inference_stats["success"]
        self.rules["learning_stats"]["failed_inferences"] = self.inference_stats["failed"]
        self.rules["learning_stats"]["last_learning_run"] = datetime.now().isoformat()
        
        # Save to file
        with open(self.rules_file, "w", encoding="utf-8") as f:
            yaml.dump(self.rules, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
        
        logger.info(f"[SAVE] Rules saved to {self.rules_file}")
        logger.info(f"[SAVE] Total mappings: {self.rules['metadata']['total_mappings']}")
        logger.info(f"[SAVE] Auto-learned: {self.rules['metadata']['auto_learned_mappings']}")
    
    def get_stats(self) -> Dict:
        """Get inference statistics."""
        return {
            **self.inference_stats,
            "learned_patterns_count": sum(len(p) for p in self.learned_patterns.values()),
            "learning_buffer": {
                domain: len(patterns)
                for domain, patterns in self.learned_patterns.items()
            }
        }


# ============================================================================
# CLI for testing
# ============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Domain Inference Engine - Test CLI")
    parser.add_argument("--file-path", required=True, help="File path to test")
    parser.add_argument("--classification", help="Document classification")
    parser.add_argument("--legal-terms", type=int, default=0, help="Legal terms count")
    parser.add_argument("--stats", action="store_true", help="Show statistics")
    
    args = parser.parse_args()
    
    engine = DomainInferenceEngine()
    
    if args.stats:
        print(yaml.dump(engine.get_stats(), default_flow_style=False))
    else:
        domain, confidence = engine.infer(
            file_path=args.file_path,
            classification=args.classification,
            legal_terms_count=args.legal_terms
        )
        
        print(f"File Path: {args.file_path}")
        print(f"Domain:    {domain or 'UNKNOWN'}")
        print(f"Confidence: {confidence:.2f}")
