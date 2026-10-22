"""
SpecialBlockScanner — Accumulated Per-Book Layout Feature Learner
=================================================================
Scans the first few chapters of a new book to auto-discover and
accumulate book-specific special block patterns:

  • Callout / sidebar keywords  (e.g. "Research in Action", "Focus Box")
  • Learning Objective numbering format  (1.1 / LO 1 / Objective 1 / etc.)
  • End-of-Chapter section headings
  • Column role classification  (which column is body vs margin glossary)
  • Whether the book has concept maps / margin glossaries

Results are merged into `book_profile.json` under `discovered_blocks` and
`column_roles` so that subsequent runs load them instantly without
re-scanning.

Usage:
    from literature_parser.services.profiler.special_block_scanner import SpecialBlockScanner
    scanner = SpecialBlockScanner(book_dir=Path("./data/output/books/MyBook"))
    scanner.scan_and_update(chapter_pdfs=[Path("chapters/Ch01/Ch01.pdf"), ...])
"""

import json
import logging
import re
import subprocess
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Known special block keyword families (seed list, auto-extended per book)
# ---------------------------------------------------------------------------
_CALLOUT_SEED_PATTERNS = [
    # Research-methods style
    r"^Research (?:in Action|Spotlight|Focus|Corner)",
    r"^Focus (?:Box|Case|Study)",
    r"^Case (?:Study|Example|Analysis)\b",
    r"^Clinical (?:Focus|Note|Case)\b",
    r"^In (?:Practice|Focus|Depth)\b",
    r"^(?:Key|Important) (?:Concept|Point|Term|Idea)\b",
    r"^Study (?:Tip|Note|Hint)\b",
    r"^Highlight\b",
    r"^(?:Did You Know|Fun Fact|Trivia)\b",
    # Science/medical textbooks
    r"^(?:Warning|Caution|Danger|Note)\b",
    r"^(?:Application|Extension|Worked Example)\b",
    r"^(?:Checkpoint|Review Question)\b",
]

# Known LO numbering formats
_LO_FORMAT_PATTERNS = [
    (r"^\d+\.\d+$",               "digit_dot_digit",   r"^\d+\.\d+"),
    (r"^LO\s*\d+$",               "LO_space_digit",    r"^LO\s*\d+"),
    (r"^Objective\s+\d+$",        "Objective_digit",   r"^Objective\s+\d+"),
    (r"^Chapter Objective\s+\d+$","Chapter_Objective",  r"^Chapter Objective\s+\d+"),
    (r"^Learning Outcome\s+\d+$", "Learning_Outcome",   r"^Learning Outcome\s+\d+"),
]

# Common EOC section headings (insensitive)
_EOC_HEADING_SEEDS = [
    "Summary", "Key Terms and Concepts", "Key Terms", "Review Questions",
    "Discussion Questions", "Practice Test", "Practice Problems",
    "Challenge Exercises", "Critical Thinking", "Related Internet Sites",
    "Web Resources", "Further Reading", "References", "Bibliography",
    "Exercises", "Problems", "Applications",
]


class SpecialBlockScanner:
    """
    Scans a book's chapter PDFs and accumulates special-block metadata
    into book_profile.json.
    """

    def __init__(self, book_dir: Path):
        self.book_dir = Path(book_dir)
        cand_canon = self.book_dir / "profile.json"
        cand_legacy = self.book_dir / "book_profile.json"
        self.profile_path = cand_canon if cand_canon.exists() or not cand_legacy.exists() else cand_legacy

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def scan_and_update(
        self,
        chapter_pdfs: List[Path],
        max_pages_per_chapter: int = 6,
        force_rescan: bool = False,
    ) -> Dict[str, Any]:
        """
        Scans `chapter_pdfs` (at most `max_pages_per_chapter` pages each)
        and merges findings into book_profile.json.
        Returns the updated profile dict.
        """
        profile = self._load_profile()

        # Skip if already scanned (unless forced)
        if not force_rescan and profile.get("scan_complete"):
            logger.info("SpecialBlockScanner: profile already complete, skipping scan.")
            return profile

        # For academic journals: bypass concept maps, LOs, and margin glossaries
        if profile.get("is_journal"):
            profile.setdefault("special_blocks", {})
            profile["special_blocks"]["has_concept_map"] = False
            profile["special_blocks"]["has_margin_glossary"] = False
            profile["special_blocks"]["lo_pattern"] = None
            profile["special_blocks"]["eoc_heading_patterns"] = [r"^References\b", r"^Author Note\b"]
            profile["column_roles"] = {
                "even_left": "body",
                "even_right": "body",
                "odd_left": "body",
                "odd_right": "body",
            }
            profile["scan_complete"] = True
            self._save_profile(profile)
            logger.info("SpecialBlockScanner: journal profile initialized with clean academic defaults.")
            return profile

        discovered_blocks: List[Dict] = list(profile.get("discovered_blocks", []))
        existing_keywords = {b["keyword"] for b in discovered_blocks if b.get("keyword")}
        existing_types    = {b["type"] for b in discovered_blocks}

        callout_counter: Counter = Counter()
        lo_formats:      Counter = Counter()
        eoc_headings:    Counter = Counter()
        has_concept_map   = profile.get("special_blocks", {}).get("has_concept_map", False)
        has_margin_glossary = profile.get("special_blocks", {}).get("has_margin_glossary", False)
        column_role_votes: List[Dict] = []

        for pdf_path in chapter_pdfs[:5]:          # limit to first 5 chapters
            pdf_str = str(pdf_path)
            try:
                total_pages = self._get_page_count(pdf_str)
            except Exception:
                total_pages = max_pages_per_chapter

            scan_pages = min(max_pages_per_chapter, total_pages)
            for pg in range(1, scan_pages + 1):
                xml = self._extract_page_xml(pdf_str, pg)
                if not xml or "<page" not in xml:
                    continue
                try:
                    root = self._parse_page_xml(xml)
                except Exception:
                    continue

                pw = float(root.attrib.get("width", 800))
                ph = float(root.attrib.get("height", 1100))

                texts = self._collect_texts(root, ph)

                # Detect callouts
                for t_top, t_left, t_w, t_size, t_txt in texts:
                    for pat in _CALLOUT_SEED_PATTERNS:
                        if re.match(pat, t_txt, re.IGNORECASE):
                            kw = re.split(r"\s{2,}|\t", t_txt)[0].strip()
                            callout_counter[kw] += 1

                # Detect LO format
                lo_hits = self._detect_lo_format(texts)
                for fmt in lo_hits:
                    lo_formats[fmt] += 1

                # Detect EOC headings
                eoc_hits = self._detect_eoc_headings(texts)
                for h in eoc_hits:
                    eoc_headings[h] += 1

                # Detect concept map & margin glossary
                if not has_concept_map and self._has_concept_map(texts, pw, ph):
                    has_concept_map = True
                if not has_margin_glossary and self._has_margin_glossary(texts, pw, ph, pg):
                    has_margin_glossary = True

                # Column role detection
                role_dict = self._classify_column_roles(texts, pw, ph, pg)
                if role_dict:
                    column_role_votes.append(role_dict)

        # Merge callout discoveries
        for kw, count in callout_counter.items():
            if count >= 1 and kw not in existing_keywords:
                discovered_blocks.append({
                    "type": "callout",
                    "keyword": kw,
                    "style": "box",
                    "count": count,
                })
                existing_keywords.add(kw)

        # Merge LO format
        if lo_formats and "lo_format" not in existing_types:
            best_fmt, _ = lo_formats.most_common(1)[0]
            # Map format name → regex
            lo_regex = next((r for _, n, r in _LO_FORMAT_PATTERNS if n == best_fmt), r"^\d+\.\d+")
            discovered_blocks.append({
                "type": "lo_format",
                "format_name": best_fmt,
                "pattern": lo_regex,
            })

        # Merge EOC headings
        existing_eoc = {b["heading"] for b in discovered_blocks if b.get("type") == "eoc_section"}
        for heading, count in eoc_headings.items():
            if count >= 1 and heading not in existing_eoc:
                discovered_blocks.append({
                    "type": "eoc_section",
                    "heading": heading,
                    "count": count,
                })
                existing_eoc.add(heading)

        # Finalise column roles (majority vote)
        column_roles = self._finalise_column_roles(column_role_votes)

        # Write back to profile
        profile.setdefault("special_blocks", {})
        profile["special_blocks"]["has_concept_map"]    = has_concept_map
        profile["special_blocks"]["has_margin_glossary"] = has_margin_glossary
        if lo_formats:
            best_fmt, _ = lo_formats.most_common(1)[0]
            lo_regex = next((r for _, n, r in _LO_FORMAT_PATTERNS if n == best_fmt), r"^\d+\.\d+")
            profile["special_blocks"]["lo_pattern"] = lo_regex

        if eoc_headings:
            profile["special_blocks"]["eoc_heading_patterns"] = [
                rf"^{re.escape(h)}\b" for h in eoc_headings
            ]

        profile["discovered_blocks"] = discovered_blocks
        profile["column_roles"]      = column_roles
        profile["scan_complete"]     = True

        self._save_profile(profile)
        logger.info(
            "SpecialBlockScanner: saved %d discovered blocks to %s",
            len(discovered_blocks),
            self.profile_path,
        )
        return profile

    # ------------------------------------------------------------------
    # Detection helpers
    # ------------------------------------------------------------------

    def _detect_lo_format(self, texts: List[Tuple]) -> List[str]:
        """Checks text lines against known LO numbering patterns."""
        found = []
        for _, _, _, size, txt in texts:
            for full_pat, fmt_name, _ in _LO_FORMAT_PATTERNS:
                if re.match(full_pat, txt.strip()):
                    found.append(fmt_name)
        return found

    def _detect_eoc_headings(self, texts: List[Tuple]) -> List[str]:
        """Checks text lines against known EOC heading seeds."""
        found = []
        for _, _, w, size, txt in texts:
            clean = txt.strip()
            for seed in _EOC_HEADING_SEEDS:
                if re.match(rf"^{re.escape(seed)}$", clean, re.IGNORECASE):
                    found.append(seed)
        return found

    def _has_concept_map(self, texts: List[Tuple], pw: float, ph: float) -> bool:
        """Heuristic: many short texts widely spread across top-right area → concept map."""
        short_scatter = [
            (l, t) for t, l, w, s, txt in texts
            if len(txt.split()) <= 4 and l > pw * 0.45 and t < ph * 0.55
        ]
        return len(short_scatter) >= 8

    def _has_margin_glossary(
        self, texts: List[Tuple], pw: float, ph: float, page_num: int
    ) -> bool:
        """Heuristic: narrow text band on outer margin of page."""
        is_even = page_num % 2 == 0
        margin_texts = []
        for t_top, t_left, t_w, t_size, t_txt in texts:
            rel_left  = t_left / pw
            rel_width = t_w / pw
            if is_even and rel_left < 0.30 and rel_width < 0.28 and len(t_txt) > 3 or (not is_even) and rel_left > 0.68 and rel_width < 0.28 and len(t_txt) > 3:
                margin_texts.append(t_txt)
        return len(margin_texts) >= 3

    def _classify_column_roles(
        self, texts: List[Tuple], pw: float, ph: float, page_num: int
    ) -> Dict[str, str]:
        """
        Classifies the left/right column role for a page as 'body' or
        'margin_glossary'.  Returns a partial dict for this page.
        """
        is_even = page_num % 2 == 0
        left_col_texts  = [t for _, l, w, s, t in texts if (l / pw) < 0.35]
        right_col_texts = [t for _, l, w, s, t in texts if (l / pw) > 0.65]

        def avg_len(lst):
            return sum(len(x) for x in lst) / max(len(lst), 1)

        # Short words on the outer margin → glossary; long prose → body
        roles: Dict[str, str] = {}
        if is_even:
            roles["even_left"]  = "margin_glossary" if avg_len(left_col_texts)  < 30 else "body"
            roles["even_right"] = "body"
        else:
            roles["odd_left"]   = "body"
            roles["odd_right"]  = "margin_glossary" if avg_len(right_col_texts) < 30 else "body"
        return roles

    def _finalise_column_roles(self, votes: List[Dict]) -> Dict[str, str]:
        """Majority-vote across all page samples to get consensus column roles."""
        if not votes:
            return {
                "even_left":  "margin_glossary",
                "even_right": "body",
                "odd_left":   "body",
                "odd_right":  "margin_glossary",
            }
        result = {}
        keys = ["even_left", "even_right", "odd_left", "odd_right"]
        for k in keys:
            vals = [v[k] for v in votes if k in v]
            if vals:
                result[k] = Counter(vals).most_common(1)[0][0]
        return result

    # ------------------------------------------------------------------
    # Low-level XML helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _get_page_count(pdf_path: str) -> int:
        try:
            out = subprocess.check_output(
                ["pdfinfo", pdf_path],
                stderr=subprocess.DEVNULL, timeout=10,
            ).decode("utf-8", errors="ignore")
            for line in out.splitlines():
                if line.startswith("Pages:"):
                    return int(line.split(":")[1].strip())
        except Exception:
            pass
        return 10

    @staticmethod
    def _extract_page_xml(pdf_path: str, page_num: int) -> str:
        try:
            res = subprocess.run(
                ["pdftohtml", "-xml", "-nodrm", "-i", "-stdout",
                 "-f", str(page_num), "-l", str(page_num), pdf_path],
                capture_output=True, timeout=20,
            )
            return res.stdout.decode("utf-8", errors="ignore")
        except Exception as e:
            logger.debug("XML extraction failed for page %d: %s", page_num, e)
            return ""

    @staticmethod
    def _parse_page_xml(xml: str) -> ET.Element:
        start = xml.find("<page")
        end   = xml.rfind("</page>") + len("</page>")
        return ET.fromstring(xml[start:end])

    @staticmethod
    def _collect_texts(root: ET.Element, ph: float) -> List[Tuple]:
        """Returns list of (top, left, width, size, text) for non-header/footer text."""
        result = []
        for t in root.findall("text"):
            top  = float(t.attrib.get("top",    0))
            left = float(t.attrib.get("left",   0))
            w    = float(t.attrib.get("width",  0))
            size = float(t.attrib.get("height", 12))
            if top < ph * 0.04 or top > ph * 0.96:
                continue
            txt = "".join(t.itertext()).strip()
            if txt:
                result.append((top, left, w, size, txt))
        return result

    # ------------------------------------------------------------------
    # Profile I/O
    # ------------------------------------------------------------------

    def _load_profile(self) -> Dict[str, Any]:
        paths = [
            self.profile_path,
            self.book_dir / ("book_profile.json" if self.profile_path.name == "profile.json" else "profile.json"),
        ]
        for p in paths:
            if p.exists():
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        return json.load(f)
                except Exception as e:
                    logger.warning("Failed to read %s: %s", p, e)
        return {}

    def _save_profile(self, profile: Dict[str, Any]) -> None:
        self.profile_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(self.profile_path, "w", encoding="utf-8") as f:
                json.dump(profile, f, indent=2, ensure_ascii=False)
            mirror = self.book_dir / ("book_profile.json" if self.profile_path.name == "profile.json" else "profile.json")
            with open(mirror, "w", encoding="utf-8") as f:
                json.dump(profile, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error("Failed to write %s: %s", self.profile_path, e)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    if len(sys.argv) < 2:
        print("Usage: python3 special_block_scanner.py <book_output_dir> [chapter_pdf ...]")
        sys.exit(1)

    book_dir = Path(sys.argv[1])
    pdf_args = [Path(p) for p in sys.argv[2:]] if len(sys.argv) > 2 else []

    # Auto-discover chapter PDFs if none supplied
    if not pdf_args:
        pdf_args = sorted(book_dir.rglob("*.pdf"))[:5]

    scanner = SpecialBlockScanner(book_dir)
    result  = scanner.scan_and_update(pdf_args, force_rescan=True)
    print("\n=== Discovered Blocks ===")
    print(json.dumps(result.get("discovered_blocks", []), indent=2, ensure_ascii=False))
    print("\n=== Column Roles ===")
    print(json.dumps(result.get("column_roles", {}), indent=2))
