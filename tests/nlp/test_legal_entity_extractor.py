from __future__ import annotations

from ingestion.nlp.legal_entity_extractor import LegalEntityExtractor


def extract_kinds(text: str):
    ext = LegalEntityExtractor()
    return [e.kind for e in ext.extract(text)]


def test_ecli_simple():
    text = "Entscheidung (ECLI:DE:BVerwG:2013:140513U9C2.12.0) ist maßgeblich."
    ext = LegalEntityExtractor()
    ents = ext.extract(text)
    assert any(e.kind == "ecli" and e.value.startswith("ECLI:DE:") for e in ents)


def test_aktenzeichen_variants():
    text = "Az. 4 K 123/20; ferner Az.: VG 4 K 321/19."
    ext = LegalEntityExtractor()
    ents = [e for e in ext.extract(text) if e.kind == "aktenzeichen"]
    values = [e.value for e in ents]
    assert "4 K 123/20" in values
    assert "VG 4 K 321/19" in values


def test_norm_single_with_abs_satz():
    text = "Maßgeblich ist § 4 Abs. 2 Satz 1 BauGB."
    ext = LegalEntityExtractor()
    ents = [e for e in ext.extract(text) if e.kind == "norm"]
    assert any("§ 4 Abs. 2 Satz 1 BauGB" == e.value for e in ents)


def test_norm_multi_paragraphs():
    text = "Siehe §§ 3, 4, 5 BauGB und § 1 BauNVO."
    ext = LegalEntityExtractor()
    ents = [e for e in ext.extract(text) if e.kind == "norm"]
    vals = [e.value for e in ents]
    assert "§ 3 BauGB" in vals and "§ 4 BauGB" in vals and "§ 5 BauGB" in vals
    assert any(v.startswith("§ 1 BauNVO") for v in vals)


def test_norm_article():
    text = "Grundrechte aus Art. 14 GG sind zu beachten."
    ext = LegalEntityExtractor()
    ents = [e for e in ext.extract(text) if e.kind == "norm"]
    assert any(e.value == "Art. 14 GG" for e in ents)


def test_dates_iso_german_text():
    text = "Bescheid vom 2024-03-12 und 12. März 2024 sowie 01.04.2023."
    ext = LegalEntityExtractor()
    ents = [e for e in ext.extract(text) if e.kind == "date"]
    vals = [e.value for e in ents]
    assert "2024-03-12" in vals
    assert "2024-03-12" in vals  # 12. März 2024 → 2024-03-12
    assert "2023-04-01" in vals


def test_mixed_all():
    text = (
        "Az.: 2 B 45/22; ECLI:DE:BVerwG:2013:140513U9C2.12.0; "
        "maßgeblich nach §§ 3, 4 BauGB, § 31 BauGB, Art. 14 GG; "
        "Bescheid vom 15.08.2021."
    )
    ext = LegalEntityExtractor()
    ents = ext.extract(text)
    kinds = [e.kind for e in ents]
    assert set(["aktenzeichen", "ecli", "norm", "date"]).issubset(set(kinds))


def test_aktenzeichen_trailing_punct_trim():
    text = "Az. 9 C 12/23, weitere Angaben folgen."
    ext = LegalEntityExtractor()
    ents = [e for e in ext.extract(text) if e.kind == "aktenzeichen"]
    assert any(e.value == "9 C 12/23" for e in ents)


def test_norm_with_nr():
    text = "§ 5 Abs. 1 Nr. 2 BImSchG ist einschlägig."
    ext = LegalEntityExtractor()
    ents = [e for e in ext.extract(text) if e.kind == "norm"]
    assert any(e.value == "§ 5 Abs. 1 Nr. 2 BImSchG" for e in ents)


def test_date_german_dotted():
    text = "Termin ist am 7.9.2025 festgesetzt."
    ext = LegalEntityExtractor()
    ents = [e for e in ext.extract(text) if e.kind == "date"]
    assert any(e.value == "2025-09-07" for e in ents)


def test_ordering_by_span():
    text = "ECLI:DE:X:2020:U.V; Az. 1 A 2/20; § 4 BauGB; 01.01.2020"
    ext = LegalEntityExtractor()
    ents = ext.extract(text)
    # ensure spans are sorted ascending
    spans = [e.span[0] for e in ents]
    assert spans == sorted(spans)
