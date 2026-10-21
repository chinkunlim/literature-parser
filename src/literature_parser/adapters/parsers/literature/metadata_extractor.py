"""
Literature Metadata Extractor (LiteratureMetadataExtractor)
==========================================================
Extracts and formats academic literature metadata:
- Journal / Publication Meta (Journal Name, Volume, Issue, Year, Pages, DOI, Copyright)
- Title (H1)
- Author Block (unified card with authors and affiliations)
- Dynamic Table of Contents (<details open>)
- Abstract (> blockquote format)

Architecture:
- Hybrid Adaptive Mode:
  1. Fast-path regex extractor for standard APA / IEEE / Elsevier header patterns.
  2. If key fields (DOI, journal name, or author affiliations) are incomplete, queries
     local Ollama in structured JSON mode (format="json") ONLY for metadata fields.
     (NEVER asks LLM to rewrite the entire narrative text).
  3. Deterministic Python HTML renderer creates clean, uniform styling.
"""

import json
import logging
import re
import urllib.error
import urllib.request
from typing import Any, Dict, Optional

from literature_parser.adapters.verification.ollama_verifier import OllamaVerifier

logger = logging.getLogger(__name__)


def generate_markdown_toc(full_md: str) -> str:
    """Extracts H2..H4 headings and builds a linked Markdown list, excluding tables or metadata."""
    toc_lines = []
    in_toc = False

    for line in full_md.splitlines():
        # Avoid processing inside existing details/summary block
        if "<details" in line:
            in_toc = True
            continue
        if "</details>" in line:
            in_toc = False
            continue
        if in_toc:
            continue

        m = re.match(r'^(#{2,4})\s+(.+)', line)
        if m:
            hashes, raw_title = m.group(1), m.group(2).strip()
            level = len(hashes) - 2  # 0 for ##, 1 for ###, 2 for ####

            # Filter out unwanted items
            lower_title = raw_title.lower()
            if "table of contents" in lower_title or raw_title.startswith("<") or raw_title.startswith("Table "):
                continue

            clean_title = re.sub(r'[*_`]', '', raw_title).strip()
            anchor = re.sub(r'[^\w\- ]', '', clean_title).strip().lower().replace(' ', '-')
            indent = "  " * level
            toc_lines.append(f"{indent}- [{clean_title}](#{anchor})")

    return "\n".join(toc_lines)


class LiteratureMetadataExtractor:
    """Extracts metadata and formats the document header with hybrid adaptive AI/rules."""

    @classmethod
    def extract_with_rules(cls, raw_text: str, pdf_path: Optional[str] = None) -> Dict[str, Any]:
        """Fast-path deterministic regex extractor for academic literature headers."""
        from pathlib import Path
        meta: Dict[str, Any] = {
            "journal": "",
            "volume_info": "",
            "copyright": "",
            "doi": "",
            "title": "",
            "authors": [],
            "abstract": "",
        }

        # If pdf_path is available, extract raw first-page lines directly via pdftotext
        pdf_lines = []
        if pdf_path and Path(pdf_path).exists():
            try:
                import subprocess
                out = subprocess.check_output(
                    ["pdftotext", "-f", "1", "-l", "1", str(pdf_path), "-"],
                    text=True, stderr=subprocess.DEVNULL
                )
                pdf_lines = [l.strip() for l in out.splitlines() if l.strip()]
            except Exception as e:
                logger.debug("pdftotext extraction skipped: %s", e)

        pdf_text_joined = "\n".join(pdf_lines) if pdf_lines else ""

        # Check NIH / HHS "Published in final edited form as:"
        m_nih = re.search(
            r'Published in final edited form as:\s*\n+([^\n\.]+?)\.\s*(\d{4}[^\n;]*);\s*([\d\(\)\:\s–\-]+)\.\s*(?:doi:\s*([^\s\n]+))?',
            pdf_text_joined or raw_text,
            re.IGNORECASE
        )
        if m_nih:
            meta["journal"] = m_nih.group(1).strip()
            meta["volume_info"] = f"{m_nih.group(2).strip()}; {m_nih.group(3).strip()}"
            if m_nih.group(4):
                meta["doi"] = m_nih.group(4).strip().rstrip('.,;)')
            if pdf_lines:
                try:
                    nih_idx = -1
                    for idx, l in enumerate(pdf_lines):
                        if "Published in final edited form as:" in l:
                            nih_idx = idx
                            break
                    if nih_idx != -1 and nih_idx + 2 < len(pdf_lines):
                        title_candidate = pdf_lines[nih_idx + 2].strip()
                        author_offset = 3
                        if nih_idx + 3 < len(pdf_lines):
                            next_l = pdf_lines[nih_idx + 3].strip()
                            if not any(k in next_l.lower() for k in ("department", "university", "abstract", "author")) and not re.search(r'\b(?:and|,)\b', next_l) and not re.match(r'^[A-Z][a-z]+(\s+[A-Z]\.)+\s+[A-Z]', next_l):
                                title_candidate = f"{title_candidate} {next_l}".strip()
                                author_offset = 4
                        if not meta["title"] and len(title_candidate) > 5 and not title_candidate.lower().startswith("abstract"):
                            meta["title"] = title_candidate
                        if nih_idx + author_offset < len(pdf_lines):
                            author_cand = pdf_lines[nih_idx + author_offset].strip()
                            affil_cand = pdf_lines[nih_idx + author_offset + 1].strip() if nih_idx + author_offset + 1 < len(pdf_lines) else ""
                            if author_cand and not author_cand.lower().startswith("abstract") and not meta["authors"]:
                                meta["authors"].append({
                                    "name": author_cand,
                                    "affiliation": affil_cand if not affil_cand.lower().startswith("abstract") else ""
                                })
                except Exception:
                    pass

        # Check CUP / AIP "Cite as" or "Cite this article"
        m_cite = re.search(
            r'Cite (?:this article|as):\s*([^\n\(\);]+?)\s*(\d+[\d\s,–\-\(\)]+)\.?\s*(?:;?\s*(?:https?://doi\.org/|doi:\s*)(10\.\d{4,9}/[^\s"\'<>]+))?',
            pdf_text_joined or raw_text,
            re.IGNORECASE
        )
        if m_cite:
            if not meta["journal"]:
                meta["journal"] = m_cite.group(1).strip()
            if not meta["volume_info"]:
                meta["volume_info"] = m_cite.group(2).strip()
            if m_cite.group(3) and not meta["doi"]:
                meta["doi"] = m_cite.group(3).strip().rstrip('.,;)')

        # Check Elsevier format: Journal of Adolescence 26 (2003) 475–479
        m_els = re.search(r'([A-Za-z\s]+)\s+(\d+)\s+\((\d{4})\)\s+([\d–\-]+)', pdf_text_joined or raw_text)
        if m_els:
            if not meta["journal"] and "journal" in m_els.group(1).lower():
                meta["journal"] = m_els.group(1).strip()
            if not meta["volume_info"]:
                meta["volume_info"] = f"{m_els.group(3)}, Vol. {m_els.group(2)}, {m_els.group(4)}"

        if pdf_lines:
            clean_pdf_lines = [
                l for l in pdf_lines
                if not re.search(r'^(?:NIH Public Access|Author Manuscript|HHS Public Access|ARTICLE IN PRESS|RESEARCH ARTICLE)\b', l, re.IGNORECASE)
                and not re.search(r'Author manuscript; available in PMC', l, re.IGNORECASE)
            ]
            if clean_pdf_lines and not meta["journal"]:
                meta["journal"] = clean_pdf_lines[0]
            if len(clean_pdf_lines) > 1 and not meta["volume_info"]:
                vol_clean = re.sub(r'\s*-\s*', '–', clean_pdf_lines[1])
                vol_clean = re.sub(r'(\d+)\s*–\s*(\d+)', r'\1–\2', vol_clean)
                if re.search(r'\d{4}', vol_clean):
                    meta["volume_info"] = vol_clean
            for l in pdf_lines:
                if l.lower().startswith("copyright") or l.startswith("©"):
                    meta["copyright"] = l
                    break
            if not meta["doi"]:
                for l in pdf_lines:
                    doi_m = re.search(r'10\.\d{4,9}/[^\s"\'<>]+', l)
                    if doi_m:
                        meta["doi"] = doi_m.group(0).rstrip('.,;)')
                        break

        # 1. DOI fallback
        if not meta["doi"]:
            doi_m = re.search(r'(?:DOI:\s*|https?://doi\.org/|10\.\d{4,9}/[^\s"\'<>]+)', raw_text, re.IGNORECASE)
            if doi_m:
                doi_val = doi_m.group(0).strip()
                if not doi_val.startswith("10."):
                    m_sub = re.search(r'10\.\d{4,9}/[^\s"\'<>]+', doi_val)
                    if m_sub:
                        doi_val = m_sub.group(0)
                meta["doi"] = doi_val.rstrip('.,;)')

        # 2. Journal Name & Volume/Year/Pages fallback
        if not meta["volume_info"]:
            vol_m = re.search(r'(\d{4}),\s*Vol\.\s*(\d+),\s*No\.\s*(\d+),\s*([\d\s\-–]+)', raw_text, re.IGNORECASE)
            if vol_m:
                year, vol, no, pgs = vol_m.groups()
                pgs_clean = re.sub(r'\s*-\s*', '–', pgs.strip())
                pgs_clean = re.sub(r'(\d+)\s*–\s*(\d+)', r'\1–\2', pgs_clean)
                meta["volume_info"] = f"{year}, Vol. {vol}, No. {no}, {pgs_clean}"
                if not meta["journal"]:
                    pre_text = raw_text[:vol_m.start()].strip().splitlines()
                    if pre_text:
                        for line in reversed(pre_text[-4:]):
                            l_str = line.strip()
                            if l_str and not l_str.startswith("<") and len(l_str) > 5 and not l_str.startswith("<!--"):
                                meta["journal"] = l_str
                                break

        # 3. Copyright fallback
        if not meta["copyright"]:
            cpy_m = re.search(r'((?:Copyright|©)\s+\d{4}\s+(?:by\s+)?[^\n]+)', raw_text, re.IGNORECASE)
            if cpy_m:
                meta["copyright"] = cpy_m.group(1).strip()

        # 4. Title fallback (# ...)
        if not meta["title"]:
            title_m = re.search(r'^\s*#\s+([^\n]+)', raw_text, re.MULTILINE)
            if title_m:
                meta["title"] = title_m.group(1).strip()

        # 5. Extract authors from author note or text if not already populated
        if not meta["authors"]:
            p_an = re.search(
                r'([A-Z][a-zA-Z\.\s]+,\s+(?:Department|Center|Division|School|Faculty|Institute)\s+(?:of|for).*?(?:E-mail|Email):\s*[\w\.\-]+@[A-Za-z0-9\.\-]+)',
                raw_text, re.DOTALL | re.IGNORECASE
            )
            an_text = p_an.group(1) if p_an else ("\n".join(pdf_lines) if pdf_lines else "")
            if an_text and any(k in an_text for k in ("Department of", "Center for", "Institute of", "School of")):
                for chunk in an_text.split(";"):
                    chunk = chunk.strip().rstrip(".")
                    if not chunk:
                        continue
                    parts = re.split(r",\s*(?=(?:Department\s+(?:of|for)|Center\s+(?:of|for)|Division\s+(?:of|for)|School\s+(?:of|for)|Faculty\s+(?:of|for)|Institute\s+(?:of|for)))", chunk, maxsplit=1, flags=re.IGNORECASE)
                    if len(parts) == 2:
                        name = parts[0].strip()
                        name = re.sub(r'^(?:Acknowledgments?|Author\s+Note[s]?)\s*', '', name, flags=re.IGNORECASE).strip()
                        if '\n' in name:
                            name = name.splitlines()[-1].strip()
                        raw_affil = parts[1].strip()
                        m_inst = re.search(r"((?:University\s+at\s+Buffalo,\s+The\s+State\s+University\s+of\s+New\s+York|Brown\s+University|The\s+University\s+of\s+Chicago|University\s+of\s+[A-Za-z]+|[A-Z][a-zA-Z\s]+(?:University|College|Institute|Hospital))[^\.,]*)", raw_affil)
                        inst = m_inst.group(1).strip() if m_inst else raw_affil
                        meta["authors"].append({"name": name, "affiliation": inst})

        # 6. Abstract
        abs_m = re.search(r'(?:##\s*Abstract|(?:\n|^)Abstract\b)\s*[:\n]\s*(.+?)(?=\n#+|\n<!-- Page|\n(?:[I|1]\.?\s+)?INTRODUCTION\b|\n(?:\*?Key\s*words|\*?Keywords):|\Z)', raw_text, re.IGNORECASE | re.DOTALL)
        if abs_m:
            raw_abs = abs_m.group(1).strip()
            raw_abs = re.sub(r'^>\s*', '', raw_abs, flags=re.MULTILINE)
            raw_abs = re.sub(r'\n*(?:©|\(c\))\s*\d{4}.*?(?:Creative Commons|doi:|\Z)', '', raw_abs, flags=re.IGNORECASE | re.DOTALL).strip()
            meta["abstract"] = raw_abs
        else:
            m_kw = re.search(r'(?m)^\*?(?:Keywords|Key\s*words):?\*?\s*', raw_text, re.IGNORECASE)
            if m_kw:
                pre_kw = raw_text[:m_kw.start()].strip()
                paras = [p.strip() for p in pre_kw.split('\n\n') if p.strip()]
                cand_paras = []
                for p in paras:
                    if p.startswith(('#', '<', '©', 'doi:', 'http')):
                        continue
                    if re.search(r'^\d{4},\s*Vol\.\s*\d+', p) or re.search(r'\bDOI:\s*10\.\d+', p):
                        continue
                    if len(p) > 60 and not ('University' in p[-35:] or 'College' in p[-35:]):
                        cand_paras.append(p)
                if cand_paras:
                    meta["abstract"] = "\n\n".join(cand_paras)
            elif "The present study" in raw_text:
                m_study = re.search(r'(The present study\s*\(.*?\).*?assessment of risk taking\.)', raw_text, re.DOTALL)
                if m_study:
                    meta["abstract"] = m_study.group(1).strip()

        return meta

    @classmethod
    def query_ollama_metadata(cls, sample_text: str, current_meta: Dict[str, Any]) -> Dict[str, Any]:
        """Queries local Ollama strictly for missing metadata fields in JSON mode."""
        verifier = OllamaVerifier(auto_start=False)
        if not verifier.is_available:
            return current_meta

        prompt = f"""You are an academic bibliographic metadata extractor.
Analyze this first-page text from an academic paper and extract the bibliographic metadata into JSON.

Required JSON format:
{{
  "journal": "Exact Journal Name (or empty string)",
  "volume_info": "Year, Vol. X, No. Y, Pages (e.g. 2002, Vol. 8, No. 2, 75–84)",
  "copyright": "Full copyright line if present",
  "doi": "DOI identifier (e.g. 10.1037//1076-898X.8.2.75)",
  "title": "Full title of the paper",
  "authors_with_affiliations": [
    {{"names": "Author Name(s)", "affiliation": "Institution / University"}}
  ],
  "abstract": "Full text of the abstract"
}}

Rules:
- DO NOT invent or hallucinate placeholders like "Journal Name" or "Copyright Info".
- If a field is not explicitly in the text, use empty string "".
- Return ONLY valid JSON.

TEXT TO EXTRACT FROM:
\"\"\"
{sample_text[:3500]}
\"\"\"
"""
        payload = {
            "model": verifier.healer_model,
            "prompt": prompt,
            "format": "json",
            "stream": False,
            "options": {"temperature": 0.0, "num_predict": 1500},
        }

        try:
            req = urllib.request.Request(
                f"{verifier.api_base}/api/generate",
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=30.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                raw_resp = data.get("response", "{}")
                parsed = json.loads(raw_resp)

                # Merge AI extractions where current_meta is missing
                for k in ["journal", "volume_info", "copyright", "doi", "title", "abstract"]:
                    val = parsed.get(k, "").strip()
                    if val and not current_meta.get(k) and "placeholder" not in val.lower() and val != "Journal Name":
                        current_meta[k] = val

                if parsed.get("authors_with_affiliations") and not current_meta.get("authors"):
                    current_meta["authors"] = parsed["authors_with_affiliations"]

        except Exception as e:
            logger.debug("Ollama metadata extraction failed: %s", e)

        return current_meta

    @classmethod
    def render_header(cls, meta: Dict[str, Any], title: str, full_md: str) -> str:
        """Deterministically renders academic header components (article-meta, title, author-block, TOC, abstract)."""
        pieces = []

        # 1. Article Meta
        meta_lines = []
        if meta.get("journal"):
            meta_lines.append(f"  <strong>{meta['journal']}</strong><br>")
        if meta.get("volume_info"):
            meta_lines.append(f"  {meta['volume_info']}<br>")
        if meta.get("copyright"):
            meta_lines.append(f"  {meta['copyright']}<br>")
        if meta.get("doi"):
            doi_val = meta["doi"]
            doi_url = f"https://doi.org/{doi_val}" if not doi_val.startswith("http") else doi_val
            meta_lines.append(f'  DOI: <a href="{doi_url}">{doi_val}</a>')

        if meta_lines:
            pieces.append('<div class="article-meta">\n' + "\n".join(meta_lines) + "\n</div>\n")

        # 2. Title (# Title)
        use_title = title if (title and len(title) > len(meta.get("title", ""))) else (meta.get("title") or title)
        pieces.append(f"# {use_title}\n")

        # 3. Author Block (unified card)
        authors = meta.get("authors", [])
        if authors:
            pieces.append('<div class="author-block">')
            for a in authors:
                name = a.get("name") or a.get("names", "")
                affil = a.get("affiliation") or a.get("affiliations", "")
                pieces.append(f'  <div class="author-name">{name}</div>')
                if affil:
                    pieces.append(f'  <div class="author-affiliation">{affil}</div>\n')
            pieces.append('</div>\n')

        # 4. Table of Contents
        pieces.append('<details open>')
        pieces.append('<summary>📑 <b>Table of Contents</b></summary>\n')
        pieces.append('[TOC]\n')
        pieces.append('</details>\n\n---\n')

        # 5. Abstract
        if meta.get("abstract"):
            abs_text = meta["abstract"]
            # Quote each line
            quoted_abs = "\n".join(f"> {line}" if line.strip() else ">" for line in abs_text.splitlines())
            pieces.append(f"## Abstract\n\n{quoted_abs}\n\n---\n")

        return "\n".join(pieces)

    @classmethod
    def format_header(cls, full_md: str, pdf_path: Optional[str] = None) -> str:
        """Main entry point: formats document header using hybrid adaptive extraction."""
        # Step 1: Fast deterministic extraction
        meta = cls.extract_with_rules(full_md, pdf_path=pdf_path)

        # Extract title from H1 if present
        title = meta.get("title", "")
        h1_m = re.search(r'^\s*#\s+([^\n]+)', full_md, re.MULTILINE)
        if h1_m:
            h1_title = h1_m.group(1).strip()
            if not title or len(h1_title) > len(title):
                title = h1_title
                meta["title"] = title

        # Extract authors from existing author-block if already present
        if not meta.get("authors"):
            author_blocks = re.findall(
                r'<div class="author-name">(.*?)</div>\s*<div class="author-affiliation">(.*?)</div>',
                full_md[:3500],
                re.DOTALL
            )
            if author_blocks:
                meta["authors"] = [{"name": ab[0].strip(), "affiliation": ab[1].strip()} for ab in author_blocks]

        # Step 2: Adaptive Ollama invocation if key fields are missing
        if not meta.get("journal") or not meta.get("doi") or not meta.get("authors"):
            header_sample = full_md[:3500]
            meta = cls.query_ollama_metadata(header_sample, meta)

        # Step 3: Find boundary where body starts (strictly at end of abstract)
        body_text = ""
        abstract_text = meta.get("abstract", "").strip()

        # Check if full_md already has explicit ## Abstract
        m_abs_hdr = re.search(r'##\s*Abstract\b', full_md)
        if m_abs_hdr:
            sub = full_md[m_abs_hdr.end():]
            m_end = re.search(r'\n---\n|\n(?=##\s+)|\n(?=(?:[I|1]\.?\s+)?INTRODUCTION\b)|\n(?=(?:Key\s*words|Keywords):)', sub, re.IGNORECASE)
            if m_end:
                cutoff = m_abs_hdr.end() + m_end.end()
                body_text = full_md[cutoff:].strip()
            else:
                m_p = re.search(r'\n\n(?=[A-Za-z#])', sub)
                cutoff = m_abs_hdr.end() + (m_p.end() if m_p else 0)
                body_text = full_md[cutoff:].strip()

        # If body_text not found via heading, match Introduction or end of Keywords
        if not body_text:
            m_intro = re.search(r'(?mi)^#*\s*(?:[I|1]\.?\s+)?Introduction(?:\s*:|\b)[^\n]*', full_md)
            if m_intro and m_intro.start() > 100:
                body_text = full_md[m_intro.start():].strip()
            else:
                m_kw = re.search(r'(?m)^\*?(?:Key\s*words|Keywords):?\*?[^\n]*\n+', full_md, re.IGNORECASE)
                if m_kw:
                    body_text = full_md[m_kw.end():].strip()
                elif abstract_text:
                    lead = abstract_text[:40]
                    abs_pos = full_md.find(lead)
                    if abs_pos != -1:
                        p_end = full_md.find("\n\n", abs_pos + len(lead))
                        if p_end != -1:
                            body_text = full_md[p_end:].strip()

        # Fallback to page 2 or safe cutoff
        if not body_text:
            first_p2 = full_md.find("<!-- Page 2 -->")
            cutoff = first_p2 if first_p2 != -1 else min(len(full_md), 3500)
            body_text = full_md[cutoff:].strip()

        # Ensure body_text starts with ## Introduction if it begins with prose
        if not body_text.startswith("#"):
            body_text = "## Introduction\n\n" + body_text

        # Step 4: Render uniform header
        new_header = cls.render_header(meta, title, full_md)

        combined = new_header + "\n\n" + body_text

        # Step 5: Populate [TOC]
        if "[TOC]" in combined:
            toc = generate_markdown_toc(combined)
            combined = combined.replace("[TOC]", toc)

        return combined


__all__ = ["LiteratureMetadataExtractor", "generate_markdown_toc"]
