"""
Quality Inspection Engine (QualityInspectionEngine)
===================================================
Coordinates three-tier inspection (Layout, Lexical, Semantic), calculates
multidimensional quality scores, applies safe auto-fixes, and generates
standardized audit reports (AUDIT.md and audit_report.json).
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, Optional

from literature_parser.services.verification.layout_auditor import LayoutAuditor
from literature_parser.services.verification.lexical_auditor import LexicalAuditor
from literature_parser.services.verification.models import (
    AuditIssue,
    AuditReport,
    QualityScore,
    VerificationConfig,
)
from literature_parser.services.verification.semantic_auditor import SemanticAuditor

logger = logging.getLogger(__name__)


class QualityInspectionEngine:
    """Unified engine executing three-tier Markdown quality verification."""

    def __init__(self, config: Optional[VerificationConfig] = None):
        """Initializes QualityInspectionEngine with configuration.

        Args:
            config: Optional VerificationConfig controlling thresholds and checks.
        """
        self.config = config or VerificationConfig()
        self.lexical_auditor = LexicalAuditor(dict_path=self.config.dictionary_path)

    def inspect(
        self,
        markdown_text: str,
        doc_name: str = "document",
        file_path: Optional[str | Path] = None,
        base_dir: Optional[Path] = None,
    ) -> AuditReport:
        """Runs the three-tier inspection on Markdown text.

        Args:
            markdown_text: Markdown text to inspect.
            doc_name: Human-readable name or title of the document.
            file_path: Optional file path string of the source Markdown file.
            base_dir: Optional directory containing images/ and style.css.

        Returns:
            Consolidated AuditReport with scores, issues, and auto-fixes.
        """
        start_time = time.time()
        all_issues: list[AuditIssue] = []
        total_repaired = 0
        current_md = markdown_text

        # ── Tier 1: Layout & Formatting Audit ─────────────────────────────────
        layout_issues, current_md, layout_repairs = LayoutAuditor.audit(
            markdown_text=current_md,
            base_dir=base_dir,
            auto_fix=self.config.enable_safe_autofix,
        )
        all_issues.extend(layout_issues)
        total_repaired += layout_repairs

        # Deduct layout points: ERROR = 15, WARNING = 5, INFO = 1
        layout_deductions = sum(
            15 if i.severity == "ERROR" else (5 if i.severity == "WARNING" else 1)
            for i in layout_issues
        )
        layout_score = max(0.0, round(100.0 - layout_deductions, 2))

        # ── Tier 2: Lexical & Formula Audit ───────────────────────────────────
        lex_issues, current_md, lex_repairs, coverage = self.lexical_auditor.audit(
            markdown_text=current_md,
            auto_fix=self.config.enable_safe_autofix,
        )
        all_issues.extend(lex_issues)
        total_repaired += lex_repairs

        # Deduct lexical points: LaTeX ERROR = 20, WARNING = 5, plus coverage penalty
        coverage_penalty = max(0.0, (1.0 - coverage) * 100.0)
        lex_deductions = sum(
            20 if i.severity == "ERROR" else (5 if i.severity == "WARNING" else 1)
            for i in lex_issues
        ) + coverage_penalty
        lexical_score = max(0.0, round(100.0 - lex_deductions, 2))

        # ── Tier 3: Semantic & Reading Flow Audit ─────────────────────────────
        sem_issues, current_md, sem_repairs = SemanticAuditor.audit(
            markdown_text=current_md,
            auto_fix=self.config.enable_safe_autofix,
        )
        all_issues.extend(sem_issues)
        total_repaired += sem_repairs

        sem_deductions = sum(
            15 if i.severity == "ERROR" else (5 if i.severity == "WARNING" else 1)
            for i in sem_issues
        )
        semantic_score = max(0.0, round(100.0 - sem_deductions, 2))

        # ── Composite Overall Score (35% Layout, 35% Lexical, 30% Semantic) ───
        overall = round(layout_score * 0.35 + lexical_score * 0.35 + semantic_score * 0.30, 2)
        passed = bool(overall >= self.config.pass_threshold)

        scores = QualityScore(
            layout_score=layout_score,
            lexical_score=lexical_score,
            semantic_score=semantic_score,
            overall_score=overall,
            passed=passed,
        )

        elapsed = round(time.time() - start_time, 3)
        stats = {
            "elapsed_sec": elapsed,
            "word_count": len(current_md.split()),
            "line_count": len(current_md.splitlines()),
            "dictionary_coverage": f"{coverage:.1%}",
        }

        return AuditReport(
            doc_name=doc_name,
            file_path=str(file_path or ""),
            scores=scores,
            issues=all_issues,
            repaired_count=total_repaired,
            repaired_markdown=current_md,
            stats=stats,
        )

    @classmethod
    def export_report_files(cls, report: AuditReport, target_dir: Path) -> Tuple[Path, Path]:
        """Saves AUDIT.md and audit_report.json into the target directory.

        Args:
            report: The AuditReport instance to export.
            target_dir: Directory where the report files will be written.

        Returns:
            Tuple of (audit_md_path, audit_json_path).
        """
        target_dir.mkdir(parents=True, exist_ok=True)
        json_path = target_dir / "audit_report.json"
        md_path = target_dir / "AUDIT.md"

        # Write JSON Report
        json_path.write_text(json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

        # Format Markdown Report
        status_badge = "✅ PASS" if report.passed else "❌ NEEDS REVIEW"
        md_lines = [
            f"# Quality Inspection Report: {report.doc_name}",
            "",
            f"> Status: **{status_badge}** | Overall Quality Score: **{report.scores.overall_score}%**",
            "",
            "## 📊 Score Breakdown",
            "",
            f"- **Layout & Formatting (35%)**: {report.scores.layout_score}%",
            f"- **Lexical & Formulas (35%)**: {report.scores.lexical_score}%",
            f"- **Semantic Reading Flow (30%)**: {report.scores.semantic_score}%",
            "",
            "## 🔍 Findings & Issues Summary",
            "",
            f"- Total Issues Detected: **{len(report.issues)}**",
            f"- Errors: **{report.error_count}** | Warnings: **{report.warning_count}** | Info: **{report.info_count}**",
            f"- Safe Auto-Repairs Applied: **{report.repaired_count}**",
            "",
        ]

        if report.issues:
            md_lines.append("### Detailed Issue List")
            md_lines.append("")
            md_lines.append("| Severity | Dimension | Line | Message | Auto-Fixed |")
            md_lines.append("|---|---|---|---|---|")
            for issue in report.issues:
                line_str = str(issue.line_num) if issue.line_num is not None else "-"
                fixed_str = "✓" if issue.auto_fixable else "-"
                clean_msg = issue.message.replace("|", "/")
                md_lines.append(f"| {issue.severity} | `{issue.category}` | {line_str} | {clean_msg} | {fixed_str} |")
            md_lines.append("")

        if report.stats:
            md_lines.append("## 📈 Document Statistics")
            md_lines.append("")
            for k, v in report.stats.items():
                md_lines.append(f"- **{k}**: {v}")
            md_lines.append("")

        md_path.write_text("\n".join(md_lines), encoding="utf-8")
        return (md_path, json_path)
