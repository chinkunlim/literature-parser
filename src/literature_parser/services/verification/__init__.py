"""
Verification Service Package (literature_parser.services.verification)
======================================================================
Comprehensive quality inspection and auditing framework:
- LayoutAuditor: Tier 1 deterministic layout and format auditing.
- LexicalAuditor: Tier 2 dictionary, hyphenation, and LaTeX formula verification.
- SemanticAuditor: Tier 3A reading-flow continuity and citation cross-referencing.
- QualityInspectionEngine: Unified orchestrator computing composite quality scores.
- AuditReport, AuditIssue, QualityScore, VerificationConfig: Core data models.
"""

from literature_parser.services.verification.layout_auditor import LayoutAuditor
from literature_parser.services.verification.lexical_auditor import LexicalAuditor
from literature_parser.services.verification.models import (
    AuditIssue,
    AuditReport,
    QualityScore,
    VerificationConfig,
)
from literature_parser.services.verification.quality_engine import QualityInspectionEngine
from literature_parser.services.verification.semantic_auditor import SemanticAuditor

__all__ = [
    "AuditIssue",
    "AuditReport",
    "QualityScore",
    "VerificationConfig",
    "LayoutAuditor",
    "LexicalAuditor",
    "SemanticAuditor",
    "QualityInspectionEngine",
]
