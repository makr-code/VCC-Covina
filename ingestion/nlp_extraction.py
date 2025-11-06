"""
Phase L6A: NLP-Extraktion & Semantische Analyse
Modul für Named Entity Recognition, Domain Classification und Relation Extraction aus Markdown-Inhalten.

Environment Variablen:
- SPACY_MODEL           (default: de_core_news_md)
- SPACY_MAX_LENGTH      (default: 1000000)
- SPACY_CHUNK_SIZE      (default: min(100000, SPACY_MAX_LENGTH-1))
- NLP_ENABLE_ZERO_SHOT  (default: false)
- NLP_INPUT_DIR         (default: data/uploads)
- NLP_WRITE_JSONL       (default: false)
- NLP_OUTPUT_JSONL      (default: data/nlp/entities.jsonl)
"""

import json
import os
from typing import List, Dict, Any, Iterable, Tuple

# spaCy und Transformers werden dynamisch importiert, falls installiert
try:
    import spacy
except ImportError:
    spacy = None

try:
    from transformers import pipeline
except ImportError:
    pipeline = None


def _get_env_bool(name: str, default: bool = False) -> bool:
    val = os.environ.get(name)
    if val is None:
        return default
    return str(val).strip().lower() in {"1", "true", "yes", "y", "on"}


class NLPExtractor:
    def __init__(self, spacy_model: str | None = None):
        model_name = spacy_model or os.environ.get("SPACY_MODEL", "de_core_news_md")
        self.spacy_model = model_name
        self.nlp = None
        self.zero_shot_enabled = _get_env_bool("NLP_ENABLE_ZERO_SHOT", False)
        if spacy:
            try:
                self.nlp = spacy.load(model_name)
                # Max length über ENV konfigurierbar
                max_len_env = os.environ.get("SPACY_MAX_LENGTH")
                if max_len_env:
                    try:
                        self.nlp.max_length = int(max_len_env)
                    except ValueError:
                        pass
            except Exception:
                self.nlp = None

        # Zero-shot Classifier lazy initialisieren
        self._zs_classifier = None

    def _iter_text_chunks(self, text: str) -> Iterable[Tuple[int, str]]:
        """Erzeugt Text-Chunks unterhalb spaCy max_length. Versucht weiche Trennungen (\n\n).
        Liefert (offset, chunk_text).
        """
        if not text:
            return
        max_len = getattr(self.nlp, "max_length", 1_000_000) if self.nlp else 1_000_000
        default_chunk = min(100_000, max_len - 1)
        chunk_size = int(os.environ.get("SPACY_CHUNK_SIZE", default_chunk))
        i = 0
        n = len(text)
        while i < n:
            end = min(i + chunk_size, n)
            # weiche Grenze suchen
            soft = text.rfind("\n\n", i + max(0, end - i - 1000), end)
            if soft != -1 and soft > i:
                end = soft
            chunk = text[i:end]
            yield i, chunk
            i = end

    def extract_entities(self, text: str) -> List[Dict[str, Any]]:
        """Extrahiert Named Entities aus Text mittels spaCy. Chunked bei langen Texten."""
        if not self.nlp:
            return []

        results: List[Dict[str, Any]] = []
        for offset, chunk in self._iter_text_chunks(text):
            if not chunk:
                continue
            doc = self.nlp(chunk)
            for ent in doc.ents:
                results.append(
                    {
                        "text": ent.text,
                        "label": ent.label_,
                        "start": ent.start_char + offset,
                        "end": ent.end_char + offset,
                    }
                )
        return results

    def _get_zero_shot_classifier(self):
        if not self.zero_shot_enabled or not pipeline:
            return None
        if self._zs_classifier is None:
            self._zs_classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")
        return self._zs_classifier

    def classify_domain(self, text: str) -> str:
        """Klassifiziert den Text in eine Rechtsdomäne (optional: Transformers)."""
        classifier = self._get_zero_shot_classifier()
        if classifier is None:
            return "Unbekannt"
        try:
            candidate_labels = [
                "Baurecht",
                "Immissionsschutz",
                "Wasserrecht",
                "Bildungsrecht",
                "Verwaltungsrecht",
            ]
            # Nur einen kleinen Ausschnitt klassifizieren, um Kosten zu begrenzen
            sample_text = text[:2000]
            result = classifier(sample_text, candidate_labels)
            return result["labels"][0]
        except Exception:
            return "Unbekannt"

    def extract_relations(self, text: str) -> List[Dict[str, Any]]:
        """Regelbasierte Relation Extraction mit spaCy Matcher für Legal-Patterns."""
        if not self.nlp:
            return []
        
        results: List[Dict[str, Any]] = []
        
        # Einfache Patterns für häufige Legal-Relationen
        # Pattern 1: "§ X [Gesetz]" → CITES_NORM
        # Pattern 2: "[Behörde] ist zuständig für [Bereich]" → HAS_JURISDICTION
        
        for offset, chunk in self._iter_text_chunks(text):
            if not chunk:
                continue
            doc = self.nlp(chunk)
            
            # Pattern: "§ <NUM> <PROPN>" (z.B. "§ 5 BImSchG")
            for i, token in enumerate(doc):
                if token.text == "§" and i + 2 < len(doc):
                    next_tok = doc[i + 1]
                    law_tok = doc[i + 2]
                    if next_tok.pos_ in {"NUM", "X"} and law_tok.pos_ == "PROPN":
                        results.append({
                            "type": "CITES_NORM",
                            "subject": None,
                            "predicate": "cites",
                            "object": f"§ {next_tok.text} {law_tok.text}",
                            "start": token.idx + offset,
                            "end": law_tok.idx + len(law_tok.text) + offset,
                        })
            
            # Pattern: "[ORG] ist zuständig für [X]" → HAS_JURISDICTION
            for sent in doc.sents:
                if "zuständig" in sent.text.lower():
                    org_ents = [e for e in sent.ents if e.label_ == "ORG"]
                    if org_ents:
                        results.append({
                            "type": "HAS_JURISDICTION",
                            "subject": org_ents[0].text,
                            "predicate": "zuständig für",
                            "object": sent.text,
                            "start": sent.start_char + offset,
                            "end": sent.end_char + offset,
                        })
        
        return results


def _iter_markdown_files(directory: str) -> Iterable[str]:
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".md"):
                yield os.path.join(root, file)


def batch_extract(directory: str) -> List[Dict[str, Any]]:
    """Batch-Extraktion über alle Markdown-Dateien im Verzeichnis.
    Optionaler JSONL-Writer via ENV NLP_WRITE_JSONL=true.
    """
    extractor = NLPExtractor()
    results: List[Dict[str, Any]] = []

    write_jsonl = _get_env_bool("NLP_WRITE_JSONL", False)
    out_path = os.environ.get("NLP_OUTPUT_JSONL", os.path.join("data", "nlp", "entities.jsonl"))
    jsonl_fh = None
    if write_jsonl:
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        jsonl_fh = open(out_path, "w", encoding="utf-8")

    count = 0
    # Optional limiter to keep smoke-runs fast
    max_files_env = os.environ.get("NLP_MAX_FILES")
    try:
        max_files = int(max_files_env) if max_files_env else None
    except ValueError:
        max_files = None
    errors = 0
    try:
        for path in _iter_markdown_files(directory):
            try:
                with open(path, encoding="utf-8") as f:
                    text = f.read()
                entities = extractor.extract_entities(text)
                domain = extractor.classify_domain(text)
                relations = extractor.extract_relations(text)
                record = {
                    "path": path,
                    "entities": entities,
                    "domain": domain,
                    "relations": relations,
                }
                if jsonl_fh:
                    jsonl_fh.write(json.dumps(record, ensure_ascii=False) + "\n")
                    jsonl_fh.flush()  # Flush nach jeder Zeile für Crash-Recovery
                else:
                    results.append(record)
                count += 1
                if count % 100 == 0:
                    print(f"[NLP] Processed: {count} files (errors: {errors})")
                # Respect limiter
                if max_files and count >= max_files:
                    print(f"[NLP] Limit reached via NLP_MAX_FILES={max_files}; stopping early.")
                    break
            except Exception as e:
                errors += 1
                # Fehler pro Datei isolieren
                err_rec = {"path": path, "error": str(e)}
                if jsonl_fh:
                    jsonl_fh.write(json.dumps(err_rec, ensure_ascii=False) + "\n")
                    jsonl_fh.flush()
                else:
                    results.append(err_rec)
    finally:
        if jsonl_fh:
            jsonl_fh.close()
        print(f"[NLP] Completed: {count} files (errors: {errors})")

    return results


if __name__ == "__main__":
    base_dir = os.environ.get("NLP_INPUT_DIR", os.path.join("data", "uploads"))
    print(f"[NLP] Starting batch extraction on: {base_dir}")
    res = batch_extract(base_dir)
    if res is not None:
        print(f"[NLP] Completed. Records: {len(res)} (use NLP_WRITE_JSONL=true for streaming output)")
