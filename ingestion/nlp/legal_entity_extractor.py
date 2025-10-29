from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional


@dataclass
class ExtractedEntity:
    kind: str            # "ecli" | "aktenzeichen" | "norm" | "date"
    value: str           # Normalisierte Darstellung
    span: Tuple[int, int]  # (start, end)
    meta: Dict[str, str]


class LegalEntityExtractor:
    """Tier-1 Regex-Extraktor für juristische Entitäten.

    Unterstützt:
      - Aktenzeichen (Az.)
      - ECLI
      - Rechtsnormen ("§", "§§", "Art.") inkl. Gesetzesabkürzung
      - Datumsangaben (mehrere Formate)
    """

    # ECLI: ECLI:DE:BVerwG:2013:140513U9C2.12.0
    _re_ecli = re.compile(r"\bECLI:[A-Z]{2}:[A-Za-z0-9.:-]+", re.UNICODE)

    # Aktenzeichen: "Az. 4 K 123/20" | "Az.: VG 4 K 123/20"
    _re_az = re.compile(
        r"\bAz\.?\s*:?\s*([A-Za-zÄÖÜäöüß0-9\s./-]{2,40})",
        re.UNICODE
    )

    # Normen:
    #  - § 4 Abs. 2 Satz 1 BauGB
    #  - §§ 3, 4, 5 BauGB  → einzelne Paragraphen expandieren
    #  - Art. 14 GG
    _re_norm_single = re.compile(
        r"(§|Art\.)\s*([\d]+[a-zA-Z]?)"
        r"(?:\s*Abs\.\s*([\d]+[a-zA-Z]?))?"
        r"(?:\s*Satz\s*([\d]+))?"
        r"(?:\s*Nr\.\s*([\d]+))?"
        r"\s*([A-ZÄÖÜ][A-Za-zÄÖÜäöüß0-9]{1,15})\b",
        re.UNICODE
    )
    _re_norm_multi = re.compile(
        r"§§\s*([\d ,]+)\s*([A-ZÄÖÜ][A-Za-zÄÖÜäöüß0-9]{1,15})\b",
        re.UNICODE
    )

    # Dates:
    _re_date_iso = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
    _re_date_de = re.compile(r"\b(\d{1,2})\.(\d{1,2})\.(\d{4})\b")
    _re_date_text = re.compile(
        r"\b(\d{1,2})\.(?:\s*)(Januar|Februar|März|April|Mai|Juni|Juli|August|September|Oktober|November|Dezember)\s+(\d{4})\b",
        re.UNICODE
    )

    _months = {
        "Januar": "01", "Februar": "02", "März": "03", "April": "04", "Mai": "05", "Juni": "06",
        "Juli": "07", "August": "08", "September": "09", "Oktober": "10", "November": "11", "Dezember": "12",
    }

    def extract(self, text: str) -> List[ExtractedEntity]:
        entities: List[ExtractedEntity] = []

        entities.extend(self._extract_ecli(text))
        entities.extend(self._extract_aktenzeichen(text))
        entities.extend(self._extract_normen(text))
        entities.extend(self._extract_dates(text))

        # Sort by position
        entities.sort(key=lambda e: e.span[0])
        return entities

    def _extract_ecli(self, text: str) -> List[ExtractedEntity]:
        out: List[ExtractedEntity] = []
        for m in self._re_ecli.finditer(text):
            out.append(ExtractedEntity(
                kind="ecli",
                value=m.group(0),
                span=(m.start(), m.end()),
                meta={}
            ))
        return out

    def _extract_aktenzeichen(self, text: str) -> List[ExtractedEntity]:
        out: List[ExtractedEntity] = []
        for m in self._re_az.finditer(text):
            raw = m.group(1).strip()
            # trim trailing punctuation
            raw = raw.rstrip(".;, ")
            out.append(ExtractedEntity(
                kind="aktenzeichen",
                value=raw,
                span=(m.start(1), m.end(1)),
                meta={}
            ))
        return out

    def _extract_normen(self, text: str) -> List[ExtractedEntity]:
        out: List[ExtractedEntity] = []

        # Multi-Paragraph pattern first: §§ 3, 4, 5 BauGB
        for m in self._re_norm_multi.finditer(text):
            paras = [p.strip() for p in m.group(1).split(',') if p.strip()]
            law = m.group(2)
            for p in paras:
                val = f"§ {p} {law}"
                out.append(ExtractedEntity(
                    kind="norm",
                    value=val,
                    span=(m.start(), m.end()),
                    meta={"law": law, "paragraph": p}
                ))

        # Single paragraph, possibly with Abs./Satz/Nr.
        for m in self._re_norm_single.finditer(text):
            prefix = m.group(1)
            para = m.group(2)
            abschnitt = m.group(3)
            satz = m.group(4)
            nr = m.group(5)
            law = m.group(6)

            parts = [f"{prefix} {para}"]
            if abschnitt:
                parts.append(f"Abs. {abschnitt}")
            if satz:
                parts.append(f"Satz {satz}")
            if nr:
                parts.append(f"Nr. {nr}")
            parts.append(law)
            val = " ".join(parts)

            out.append(ExtractedEntity(
                kind="norm",
                value=val,
                span=(m.start(), m.end()),
                meta={
                    "law": law,
                    "paragraph": para,
                    **({"abs": abschnitt} if abschnitt else {}),
                    **({"satz": satz} if satz else {}),
                    **({"nr": nr} if nr else {}),
                }
            ))

        return out

    def _extract_dates(self, text: str) -> List[ExtractedEntity]:
        out: List[ExtractedEntity] = []

        for m in self._re_date_iso.finditer(text):
            y, mo, d = m.group(1), m.group(2), m.group(3)
            out.append(ExtractedEntity(
                kind="date",
                value=f"{y}-{mo}-{d}",
                span=(m.start(), m.end()),
                meta={"format": "iso"}
            ))

        for m in self._re_date_de.finditer(text):
            d, mo, y = int(m.group(1)), int(m.group(2)), m.group(3)
            out.append(ExtractedEntity(
                kind="date",
                value=f"{y}-{mo:02d}-{d:02d}",
                span=(m.start(), m.end()),
                meta={"format": "de"}
            ))

        for m in self._re_date_text.finditer(text):
            d, mon, y = int(m.group(1)), m.group(2), m.group(3)
            mo = self._months.get(mon, "01")
            out.append(ExtractedEntity(
                kind="date",
                value=f"{y}-{mo}-{d:02d}",
                span=(m.start(), m.end()),
                meta={"format": "de_text"}
            ))

        return out
