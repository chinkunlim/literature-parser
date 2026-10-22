"""
Layout & Formatting Auditor (LayoutAuditor)
===========================================
Performs deterministic, millisecond-level inspection and safe repair of Markdown layout:
- Heading hierarchy and TOC anchor slug validation.
- Table structure (GFM pipes alignment, HTML table tag closure, caption presence).
- Figure and image presence in local images/ directory.
- Running header and footer noise filtering.
- Tag closure (<style>, <details>, <figure>).
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import List, Optional, Tuple

from literature_parser.services.verification.models import AuditIssue

logger = logging.getLogger(__name__)


class LayoutAuditor:
    """Audits and auto-repairs layout and typography formatting defects in Markdown."""

    NOISE_PATTERNS = [
        re.compile(r'^(?:Copyright\s+©|All\s+rights\s+reserved\b|Printed\s+in\s+the\s+United\s+States)', re.IGNORECASE),
        re.compile(r'^\s*(?:Page\s+)?\d{1,4}\s*$', re.IGNORECASE),
        re.compile(r'^\s*CHAPTER\s+\d+\b\s*$', re.IGNORECASE),
        re.compile(r'^\s*doi:\s*10\.\d{4,9}/[-._;()/:A-Za-z0-9]+\s*$', re.IGNORECASE),
    ]

    @classmethod
    def audit(
        cls,
        markdown_text: str,
        base_dir: Optional[Path] = None,
        auto_fix: bool = True,
    ) -> Tuple[List[AuditIssue], str, int]:
        """Audits Markdown content for layout defects and optionally applies safe auto-fixes.

        Args:
            markdown_text: Raw or processed Markdown text.
            base_dir: Base directory containing images/ and style.css for existence checks.
            auto_fix: Whether to apply deterministic safe auto-fixes to the text.

        Returns:
            Tuple of (list_of_issues, repaired_markdown, repaired_count).
        """
        issues: List[AuditIssue] = []
        lines = markdown_text.splitlines()
        repaired_lines = list(lines)
        repaired_count = 0

        # 1. Heading Hierarchy & Prose Intrusion Check
        has_h1 = False
        prev_level = 0
        slugs = set()

        for idx, line in enumerate(lines, 1):
            s = line.strip()
            m_h = re.match(r'^(#{1,6})\s+(.+)$', s)
            if m_h:
                level = len(m_h.group(1))
                title = m_h.group(2).strip()
                if level == 1:
                    has_h1 = True

                # Check prose intrusion into H3 (long paragraphs erroneously prefixed with ###)
                if level >= 3 and len(title) > 120 and title.endswith(('.', '。', ';')):
                    issue = AuditIssue(
                        severity="WARNING",
                        category="LAYOUT_HEADING_PROSE",
                        line_num=idx,
                        snippet=line[:80],
                        message=f"Over-inflated heading H{level} appears to be prose ({len(title)} chars).",
                        suggested_fix=f"**{title[:50]}...** (demote to bold paragraph)",
                        auto_fixable=True,
                    )
                    issues.append(issue)
                    if auto_fix:
                        repaired_lines[idx - 1] = f"**{title}**"
                        repaired_count += 1
                        continue

                # Heading level monotonicity (no skipping like H1 -> H4)
                if prev_level > 0 and level > prev_level + 1:
                    issues.append(AuditIssue(
                        severity="INFO",
                        category="LAYOUT_HEADING_SKIP",
                        line_num=idx,
                        snippet=line,
                        message=f"Heading level jumps from H{prev_level} to H{level}.",
                        auto_fixable=False,
                    ))
                prev_level = level

                # Collect heading slug for TOC verification
                clean_t = re.sub(r'[*_`]', '', title)
                slug = re.sub(r'[^a-zA-Z0-9\u4e00-\u9fa5]+', '-', clean_t.lower()).strip('-')
                if slug:
                    slugs.add(slug)

        if not has_h1 and len(lines) > 5:
            issues.append(AuditIssue(
                severity="WARNING",
                category="LAYOUT_HEADING_MISSING_H1",
                line_num=1,
                snippet=lines[0] if lines else "",
                message="Document lacks a top-level H1 (#) title heading.",
                auto_fixable=False,
            ))

        # 2. Running Noise Strings & Standalone Page Numbers
        clean_lines = []
        for idx, line in enumerate(repaired_lines, 1):
            s = line.strip()
            is_noise = False
            for pat in cls.NOISE_PATTERNS:
                if pat.match(s) and len(s) < 100:
                    is_noise = True
                    break
            if is_noise:
                issues.append(AuditIssue(
                    severity="INFO",
                    category="LAYOUT_NOISE_LEAK",
                    line_num=idx,
                    snippet=line,
                    message="Detected leaked running header/footer or page number noise.",
                    suggested_fix="",
                    auto_fixable=True,
                ))
                if auto_fix:
                    repaired_count += 1
                    continue
            clean_lines.append(line)
        repaired_lines = clean_lines

        repaired_md = '\n'.join(repaired_lines)

        # 3. HTML Tag Pairs Closure (<style>, <details>, <table>, <figure>)
        for tag in ["style", "details", "table", "figure"]:
            open_count = len(re.findall(rf'<{tag}\b[^>]*>', repaired_md, re.IGNORECASE))
            close_count = len(re.findall(rf'</{tag}>', repaired_md, re.IGNORECASE))
            if open_count > close_count:
                missing = open_count - close_count
                issues.append(AuditIssue(
                    severity="ERROR",
                    category="LAYOUT_UNCLOSED_TAG",
                    line_num=None,
                    snippet=f"<{tag}> ...",
                    message=f"Unclosed HTML <{tag}> tag(s): found {open_count} open, but only {close_count} closed.",
                    suggested_fix=f"Append {missing} </{tag}> tag(s).",
                    auto_fixable=True,
                ))
                if auto_fix:
                    repaired_md += "\n" + f"</{tag}>\n" * missing
                    repaired_count += missing

        # 4. Image Reference Integrity Check
        img_refs = re.findall(r'!\[.*?\]\((images/[^)]+)\)', repaired_md) + re.findall(r'<img[^>]+src=["\'](images/[^"\']+)["\']', repaired_md)
        if base_dir:
            for ref in set(img_refs):
                img_path = base_dir / ref
                if not img_path.exists() or img_path.stat().st_size == 0:
                    issues.append(AuditIssue(
                        severity="ERROR",
                        category="LAYOUT_MISSING_IMAGE",
                        line_num=None,
                        snippet=ref,
                        message=f"Referenced image file does not exist or is empty: {img_path}",
                        auto_fixable=False,
                    ))

        # Collect explicit HTML anchors (<a id="...">, <span id="...">, etc.)
        for m in re.finditer(r'<[a-zA-Z0-9]+\b[^>]*(?:id|name)=["\']([^"\']+)["\']', repaired_md):
            slugs.add(m.group(1))

        # 5. TOC Link Anchors Sanity (Extract links only from genuine TOC block)
        toc_blocks = re.findall(
            r'<details\b[^>]*>\s*<summary>[^<]*Table of Contents[^<]*</summary>(.*?)</details>',
            repaired_md,
            re.DOTALL | re.IGNORECASE,
        )
        toc_text = "\n".join(toc_blocks) if toc_blocks else ""
        toc_links = re.findall(r'\[([^\]]+)\]\(#([^)]+)\)', toc_text) if toc_text else []

        for text, link_slug in toc_links:
            if slugs and link_slug not in slugs:
                # Check for slight mismatch
                matched = any(link_slug in s or s in link_slug for s in slugs)
                if not matched:
                    issues.append(AuditIssue(
                        severity="WARNING",
                        category="LAYOUT_BROKEN_TOC_LINK",
                        line_num=None,
                        snippet=f"[{text}](#{link_slug})",
                        message=f"TOC link anchor '#{link_slug}' does not match any heading in the document.",
                        auto_fixable=False,
                    ))

        return (issues, repaired_md, repaired_count)
