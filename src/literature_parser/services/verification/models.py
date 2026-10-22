"""
Data Models and Quality Report Contracts
========================================
Defines strongly-typed data structures for the three-tier Markdown verification system:
- AuditIssue: Individual issue found during inspection (severity, category, line, fix).
- QualityScore: Weighted scores for layout, lexical, and semantic dimensions.
- AuditReport: Aggregated audit report carrying issues, scores, fixes, and dispositions.
- VerificationConfig: Tunable configuration controlling thresholds and execution.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class AuditIssue:
    """Represents a specific defect or anomaly detected during inspection.

    Attributes:
        severity: Severity level ('ERROR', 'WARNING', 'INFO').
        category: Verification dimension or category (e.g. 'LAYOUT_HEADING', 'LEXICAL_SPELLING', 'SEMANTIC_CONTINUITY').
        line_num: 1-indexed line number in the Markdown file, or None if global.
        snippet: Offending text snippet or context line.
        message: Descriptive explanation of the issue.
        suggested_fix: Proposed replacement or remediation instruction.
        auto_fixable: Whether this issue can be safely and automatically remediated.
        confidence: Confidence score of the detection or suggested fix (0.0 to 1.0).
    """

    severity: str
    category: str
    line_num: Optional[int]
    snippet: str
    message: str
    suggested_fix: Optional[str] = None
    auto_fixable: bool = False
    confidence: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        """Converts issue to dictionary representation.

        Returns:
            Dictionary containing issue attributes.
        """
        return asdict(self)


@dataclass
class QualityScore:
    """Weighted scores across the three verification dimensions.

    Attributes:
        layout_score: Layout and formatting score (0.0 to 100.0).
        lexical_score: Lexical spelling and LaTeX formula score (0.0 to 100.0).
        semantic_score: Semantic reading flow and continuity score (0.0 to 100.0).
        overall_score: Weighted composite score (0.0 to 100.0).
        passed: Whether overall score meets or exceeds the required passing threshold.
    """

    layout_score: float = 100.0
    lexical_score: float = 100.0
    semantic_score: float = 100.0
    overall_score: float = 100.0
    passed: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Converts score metrics to dictionary representation.

        Returns:
            Dictionary with breakdown of scores.
        """
        return asdict(self)


@dataclass
class VerificationConfig:
    """Configuration options controlling verification behavior and thresholds.

    Attributes:
        pass_threshold: Minimum overall score percentage to pass verification.
        enable_safe_autofix: Whether to automatically apply safe deterministic fixes.
        enable_ollama_deep_dive: Whether to trigger local Ollama semantic deep-dive when score < threshold.
        dictionary_path: Optional custom path to dictionary wordlist.
        min_dictionary_coverage: Expected minimum dictionary word coverage ratio.
        max_heading_chars_for_h3: Max character length before ### is flagged as prose intrusion.
    """

    pass_threshold: float = 85.0
    enable_safe_autofix: bool = True
    enable_ollama_deep_dive: bool = True
    dictionary_path: Optional[str] = None
    min_dictionary_coverage: float = 0.90
    max_heading_chars_for_h3: int = 120


@dataclass
class AuditReport:
    """Comprehensive inspection report consolidating findings across all tiers.

    Attributes:
        doc_name: Name or title of the audited document.
        file_path: Source Markdown file path on disk.
        scores: QualityScore breakdown.
        issues: List of all AuditIssue instances detected.
        repaired_count: Total number of automatically repaired issues.
        repaired_markdown: Full Markdown text after applying safe auto-fixes.
        ollama_review: Optional feedback string returned by local Ollama AI.
        stats: Dictionary carrying execution stats (word count, lines, elapsed time).
    """

    doc_name: str
    file_path: str
    scores: QualityScore = field(default_factory=QualityScore)
    issues: List[AuditIssue] = field(default_factory=list)
    repaired_count: int = 0
    repaired_markdown: Optional[str] = None
    ollama_review: Optional[str] = None
    stats: Dict[str, Any] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        """Indicates whether the document passed verification."""
        return self.scores.passed

    @property
    def error_count(self) -> int:
        """Counts issues with ERROR severity."""
        return sum(1 for i in self.issues if i.severity == "ERROR")

    @property
    def warning_count(self) -> int:
        """Counts issues with WARNING severity."""
        return sum(1 for i in self.issues if i.severity == "WARNING")

    @property
    def info_count(self) -> int:
        """Counts issues with INFO severity."""
        return sum(1 for i in self.issues if i.severity == "INFO")

    def to_dict(self) -> Dict[str, Any]:
        """Converts report to serializable dictionary.

        Returns:
            Dictionary containing full report contents.
        """
        return {
            "doc_name": self.doc_name,
            "file_path": self.file_path,
            "passed": self.passed,
            "scores": self.scores.to_dict(),
            "summary": {
                "total_issues": len(self.issues),
                "error_count": self.error_count,
                "warning_count": self.warning_count,
                "info_count": self.info_count,
                "repaired_count": self.repaired_count,
            },
            "stats": self.stats,
            "ollama_review": self.ollama_review,
            "issues": [i.to_dict() for i in self.issues],
        }
