"""
Document & Literature Profile Domain Schema
===========================================
Defines the canonical, strongly-typed DocumentProfile data structures
for unified profile.json files across textbooks and academic literature:
- ProfileMetadata: Document archetype, title, publisher, and scan mode
- ProfileGeometry: Page dimensions, margins, gutter splits, and cutoffs
- ProfileTypography: Heading font scales, body sizes, and glyph mappings
- ProfileSemantics: Citation style (APA/IEEE/Chicago), LO and EOC patterns
- ProfileSpecialBlocks: Flags for concept maps, margin glossaries, callouts
- DocumentProfile: Root aggregation container supporting validation,
  serialization, deep merging, and closed-loop feedback adjustments.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ProfileMetadata:
    """Document metadata and pipeline execution flags.

    Attributes:
        doc_type: Archetype classification ('book' or 'literature').
        mode: Processing mode ('digital' or 'scanned').
        title: Document or book title string.
        publisher: Identified publisher identifier or None.
        version: Profile schema version string.
        front_matter_sections: List of detected Front Matter sections and page ranges.
    """

    doc_type: str = "book"
    mode: str = "digital"
    title: str = "untitled"
    publisher: Optional[str] = None
    version: str = "2.0"
    front_matter_sections: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Converts metadata to dictionary representation.

        Returns:
            Dictionary with metadata attributes.
        """
        res: Dict[str, Any] = {
            "doc_type": self.doc_type,
            "mode": self.mode,
            "title": self.title,
            "publisher": self.publisher,
            "version": self.version,
        }
        if self.front_matter_sections:
            res["front_matter_sections"] = list(self.front_matter_sections)
        return res

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ProfileMetadata:
        """Constructs ProfileMetadata from dictionary data.

        Args:
            data: Raw dictionary containing metadata fields.

        Returns:
            Validated ProfileMetadata instance.
        """
        fm_secs = data.get("front_matter_sections", [])
        return cls(
            doc_type=data.get("doc_type") or ("literature" if data.get("is_journal") else "book"),
            mode="scanned" if data.get("is_scanned") else data.get("mode", "digital"),
            title=data.get("title") or data.get("book_name", "untitled"),
            publisher=data.get("publisher"),
            version=data.get("version", "2.0"),
            front_matter_sections=list(fm_secs),
        )


@dataclass
class PageAsymmetry:
    """Odd or even page asymmetric boundary definitions.

    Attributes:
        outer_margin_x: Ratio range [min_x, max_x] of page width where outer notes/glossary lie.
        binding_margin_x: Ratio range [min_x, max_x] of page width adjacent to book spine binding.
        header_align: Running header text alignment ('left', 'center', 'right').
        page_number_pos: Location of page number ('bottom_left', 'bottom_right', 'top_left', 'top_right').
    """

    outer_margin_x: List[float] = field(default_factory=lambda: [0.72, 1.0])
    binding_margin_x: List[float] = field(default_factory=lambda: [0.0, 0.28])
    header_align: str = "right"
    page_number_pos: str = "bottom_right"

    def to_dict(self) -> Dict[str, Any]:
        """Converts asymmetric page settings to dictionary representation.

        Returns:
            Dictionary with asymmetric parameters.
        """
        return {
            "outer_margin_x": list(self.outer_margin_x),
            "binding_margin_x": list(self.binding_margin_x),
            "header_align": self.header_align,
            "page_number_pos": self.page_number_pos,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> PageAsymmetry:
        """Constructs PageAsymmetry from dictionary data.

        Args:
            data: Raw dictionary containing asymmetric page fields.

        Returns:
            Validated PageAsymmetry instance.
        """
        return cls(
            outer_margin_x=list(data.get("outer_margin_x", [0.72, 1.0])),
            binding_margin_x=list(data.get("binding_margin_x", [0.0, 0.28])),
            header_align=str(data.get("header_align", "right")),
            page_number_pos=str(data.get("page_number_pos", "bottom_right")),
        )


@dataclass
class ProfileGeometry:
    """Physical page geometry, margins, cutoffs, and column boundaries.

    Attributes:
        page_width: Standard calibrated page width in points.
        page_height: Standard calibrated page height in points.
        header_cutoff_y: Top Y threshold below which running headers are discarded.
        footer_cutoff_y: Bottom Y threshold above which running footers are discarded.
        p1_content_start_y: First page Y threshold below article banners/metadata.
        layout: Column layout ('single_column' or 'two_column').
        gutter_split_x: Central X coordinate separating left and right columns.
        even_margin_bound: Outer margin boundary ratio for even pages (textbooks).
        odd_margin_bound: Outer margin boundary ratio for odd pages (textbooks).
        has_odd_even_asymmetry: Whether textbook uses distinct verso (left) and recto (right) layouts.
        even_page: Verso (left page) layout boundaries.
        odd_page: Recto (right page) layout boundaries.
        has_spanning_boxes: Whether textbook contains full-width boxes that cross both columns.
        uniform_crop_margin_pt: Uniform margin in points added to all four sides when cropping figures and tables.
    """

    page_width: float = 612.0
    page_height: float = 792.0
    header_cutoff_y: float = 45.0
    footer_cutoff_y: float = 740.0
    p1_content_start_y: Optional[float] = None
    layout: str = "single_column"
    gutter_split_x: Optional[float] = None
    even_margin_bound: float = 0.30
    odd_margin_bound: float = 0.70
    has_odd_even_asymmetry: bool = True
    even_page: PageAsymmetry = field(default_factory=lambda: PageAsymmetry(
        outer_margin_x=[0.0, 0.28], binding_margin_x=[0.72, 1.0], header_align="left", page_number_pos="bottom_left"
    ))
    odd_page: PageAsymmetry = field(default_factory=lambda: PageAsymmetry(
        outer_margin_x=[0.72, 1.0], binding_margin_x=[0.0, 0.28], header_align="right", page_number_pos="bottom_right"
    ))
    has_spanning_boxes: bool = True
    uniform_crop_margin_pt: float = 16.0

    def to_dict(self) -> Dict[str, Any]:
        """Converts geometry to dictionary representation.

        Returns:
            Dictionary containing geometry parameters.
        """
        return {
            "page_dimensions": {"width": self.page_width, "height": self.page_height},
            "header_cutoff_y": self.header_cutoff_y,
            "footer_cutoff_y": self.footer_cutoff_y,
            "p1_content_start_y": self.p1_content_start_y,
            "layout": self.layout,
            "gutter_split_x": self.gutter_split_x,
            "even_margin_bound": self.even_margin_bound,
            "odd_margin_bound": self.odd_margin_bound,
            "has_odd_even_asymmetry": self.has_odd_even_asymmetry,
            "even_page": self.even_page.to_dict(),
            "odd_page": self.odd_page.to_dict(),
            "has_spanning_boxes": self.has_spanning_boxes,
            "uniform_crop_margin_pt": self.uniform_crop_margin_pt,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ProfileGeometry:
        """Constructs ProfileGeometry from dictionary data.

        Args:
            data: Raw dictionary containing geometry fields.

        Returns:
            Validated ProfileGeometry instance.
        """
        dims = data.get("page_dimensions", {})
        margins = data.get("margins", {})
        gutters = data.get("gutters", {})

        pw = float(dims.get("width") or data.get("page_width", 612.0))
        ph = float(dims.get("height") or data.get("page_height", 792.0))

        hdr = float(margins.get("header_cutoff_y") or data.get("header_cutoff_y", 45.0))
        ftr = float(margins.get("footer_cutoff_y") or data.get("footer_cutoff_y", ph * 0.93))
        p1_start = margins.get("p1_content_start_y", data.get("p1_content_start_y"))

        split_x = gutters.get("split_x", data.get("gutter_split_x"))
        if split_x is not None:
            split_x = float(split_x)

        even_data = data.get("even_page", {})
        odd_data = data.get("odd_page", {})
        even_page = PageAsymmetry.from_dict(even_data) if even_data else PageAsymmetry(
            outer_margin_x=[0.0, 0.28], binding_margin_x=[0.72, 1.0], header_align="left", page_number_pos="bottom_left"
        )
        odd_page = PageAsymmetry.from_dict(odd_data) if odd_data else PageAsymmetry(
            outer_margin_x=[0.72, 1.0], binding_margin_x=[0.0, 0.28], header_align="right", page_number_pos="bottom_right"
        )

        return cls(
            page_width=pw,
            page_height=ph,
            header_cutoff_y=hdr,
            footer_cutoff_y=ftr,
            p1_content_start_y=float(p1_start) if p1_start is not None else None,
            layout=data.get("layout", "single_column"),
            gutter_split_x=split_x,
            even_margin_bound=float(margins.get("even_page_margin_bound", data.get("even_margin_bound", 0.30))),
            odd_margin_bound=float(margins.get("odd_page_margin_bound", data.get("odd_margin_bound", 0.70))),
            has_odd_even_asymmetry=bool(data.get("has_odd_even_asymmetry", True)),
            even_page=even_page,
            odd_page=odd_page,
            has_spanning_boxes=bool(data.get("has_spanning_boxes", True)),
            uniform_crop_margin_pt=float(data.get("uniform_crop_margin_pt", 16.0)),
        )


@dataclass
class ProfileTypography:
    """Typography scales, heading size thresholds, and font mappings.

    Attributes:
        h1_min_size: Minimum font size in points to promote text to H1 (#).
        h2_min_size: Minimum font size in points to promote text to H2 (##).
        h3_min_size: Minimum font size in points to promote text to H3 (###).
        body_font_size: Standard body text font size in points.
        symbol_mappings: Dictionary of custom Unicode-to-LaTeX mappings.
        has_drop_caps: Whether chapter opening paragraphs use drop caps.
        drop_cap_lines: Height in lines of drop caps.
        caption_patterns: Regex patterns matching figure, table, and box captions.
    """

    h1_min_size: float = 18.0
    h2_min_size: float = 14.0
    h3_min_size: float = 12.0
    body_font_size: float = 10.0
    symbol_mappings: Dict[str, str] = field(default_factory=dict)
    has_drop_caps: bool = False
    drop_cap_lines: int = 2
    caption_patterns: List[str] = field(default_factory=lambda: [
        r"^Figure\s+\d+[\.\-]\d+",
        r"^Table\s+\d+[\.\-]\d+",
        r"^Box\s+\d+[\.\-]\d+",
        r"^Exhibit\s+\d+[\.\-]\d+",
    ])

    def to_dict(self) -> Dict[str, Any]:
        """Converts typography settings to dictionary representation.

        Returns:
            Dictionary with typography parameters.
        """
        return {
            "h1_min_size": self.h1_min_size,
            "h2_min_size": self.h2_min_size,
            "h3_min_size": self.h3_min_size,
            "body_font_size": self.body_font_size,
            "symbol_mappings": dict(self.symbol_mappings),
            "has_drop_caps": self.has_drop_caps,
            "drop_cap_lines": self.drop_cap_lines,
            "caption_patterns": list(self.caption_patterns),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ProfileTypography:
        """Constructs ProfileTypography from dictionary data.

        Args:
            data: Raw dictionary containing typography fields.

        Returns:
            Validated ProfileTypography instance.
        """
        caps = data.get("caption_patterns")
        return cls(
            h1_min_size=float(data.get("h1_min_size", 18.0)),
            h2_min_size=float(data.get("h2_min_size", 14.0)),
            h3_min_size=float(data.get("h3_min_size", 12.0)),
            body_font_size=float(data.get("body_font_size", 10.0)),
            symbol_mappings=dict(data.get("symbol_mappings", {})),
            has_drop_caps=bool(data.get("has_drop_caps", False)),
            drop_cap_lines=int(data.get("drop_cap_lines", 2)),
            caption_patterns=list(caps) if caps is not None else [
                r"^Figure\s+\d+[\.\-]\d+",
                r"^Table\s+\d+[\.\-]\d+",
                r"^Box\s+\d+[\.\-]\d+",
                r"^Exhibit\s+\d+[\.\-]\d+",
            ],
        )


@dataclass
class ProfileSpecialBlocks:
    """Indicators and patterns for domain-specific pedagogical and research blocks.

    Attributes:
        has_concept_map: Whether textbook contains 2D concept/mind maps.
        has_margin_glossary: Whether textbook has key terms in margins.
        lo_pattern: Regex pattern identifying Learning Objectives.
        eoc_heading_patterns: Regex patterns identifying End-of-Chapter sections.
        active_blocks: List of active pedagogical block keys identified in this book.
        block_rules: Detailed rules and styles for each active block.
    """

    has_concept_map: bool = False
    has_margin_glossary: bool = False
    lo_pattern: Optional[str] = None
    eoc_heading_patterns: List[str] = field(default_factory=lambda: [
        r"^Key Terms and Concepts\b",
        r"^Related Internet Sites\b",
        r"^Practice Test\b",
        r"^Challenge Exercises\b",
        r"^Summary\b",
        r"^Review Questions\b",
        r"^Discussion Questions\b",
        r"^Critical Thinking\b",
        r"^Further Reading\b",
        r"^Questions for Thought and Discussion\b",
        r"^Exercises\b",
        r"^References\b",
        r"^Author Note\b",
    ])
    active_blocks: List[str] = field(default_factory=list)
    block_rules: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Converts special blocks settings to dictionary representation.

        Returns:
            Dictionary with special blocks parameters.
        """
        return {
            "has_concept_map": self.has_concept_map,
            "has_margin_glossary": self.has_margin_glossary,
            "lo_pattern": self.lo_pattern,
            "eoc_heading_patterns": list(self.eoc_heading_patterns),
            "active_blocks": list(self.active_blocks),
            "block_rules": {k: dict(v) for k, v in self.block_rules.items()},
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ProfileSpecialBlocks:
        """Constructs ProfileSpecialBlocks from dictionary data.

        Args:
            data: Raw dictionary containing special blocks fields.

        Returns:
            Validated ProfileSpecialBlocks instance.
        """
        default_patterns = [
            r"^Key Terms and Concepts\b",
            r"^Related Internet Sites\b",
            r"^Practice Test\b",
            r"^Challenge Exercises\b",
            r"^Summary\b",
            r"^Review Questions\b",
            r"^Discussion Questions\b",
            r"^Critical Thinking\b",
            r"^Further Reading\b",
            r"^Questions for Thought and Discussion\b",
            r"^Exercises\b",
            r"^References\b",
            r"^Author Note\b",
        ]
        patterns = data.get("eoc_heading_patterns")
        if patterns is not None:
            merged_patterns = list(patterns)
            for dp in default_patterns:
                if dp not in merged_patterns:
                    merged_patterns.append(dp)
        else:
            merged_patterns = default_patterns
        active = data.get("active_blocks", [])
        rules = data.get("block_rules", {})
        return cls(
            has_concept_map=bool(data.get("has_concept_map", False)),
            has_margin_glossary=bool(data.get("has_margin_glossary", False)),
            lo_pattern=data.get("lo_pattern"),
            eoc_heading_patterns=merged_patterns,
            active_blocks=list(active),
            block_rules={k: dict(v) for k, v in rules.items()} if isinstance(rules, dict) else {},
        )


@dataclass
class DocumentProfile:
    """Canonical root profile aggregating metadata, geometry, typography, and blocks.

    Attributes:
        meta: Metadata parameters.
        geometry: Page geometry and layout boundaries.
        typography: Heading scales and font thresholds.
        special_blocks: Special pedagogical and research block detection flags.
        publisher_rules: Publisher-specific regex patterns and cleanups.
    """

    meta: ProfileMetadata = field(default_factory=ProfileMetadata)
    geometry: ProfileGeometry = field(default_factory=ProfileGeometry)
    typography: ProfileTypography = field(default_factory=ProfileTypography)
    special_blocks: ProfileSpecialBlocks = field(default_factory=ProfileSpecialBlocks)
    publisher_rules: Dict[str, Any] = field(default_factory=dict)
    anomalies: List[Dict[str, Any]] = field(default_factory=list)
    learned_fixes: Dict[str, Any] = field(default_factory=dict)
    chapter_history: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serializes the complete profile to a nested dictionary for JSON export.

        Returns:
            Full dictionary structure conforming to canonical profile.json schema.
        """
        res: Dict[str, Any] = {
            "meta": self.meta.to_dict(),
            "geometry": self.geometry.to_dict(),
            "typography": self.typography.to_dict(),
            "special_blocks": self.special_blocks.to_dict(),
        }
        if self.publisher_rules:
            res["publisher_rules"] = dict(self.publisher_rules)
        if self.anomalies:
            res["anomalies"] = list(self.anomalies)
        if self.learned_fixes:
            res["learned_fixes"] = dict(self.learned_fixes)
        if self.chapter_history:
            res["chapter_history"] = dict(self.chapter_history)

        # Flat top-level convenience aliases for backward compatibility
        res["publisher"] = self.meta.publisher
        res["is_journal"] = (self.meta.doc_type == "literature")
        res["book_name"] = self.meta.title
        return res

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> DocumentProfile:
        """Parses and normalizes a dictionary into a validated DocumentProfile.

        Args:
            data: Raw dictionary loaded from profile.json, book_profile.json, etc.

        Returns:
            Validated DocumentProfile instance with normalized subcomponents.
        """
        if not data:
            return cls()

        meta_data = data.get("meta", data)
        geom_data = data.get("geometry", data)
        typo_data = data.get("typography", data)
        blocks_data = data.get("special_blocks", data)
        pub_rules = data.get("publisher_rules", data.get("publisher_config", {}))

        return cls(
            meta=ProfileMetadata.from_dict(meta_data),
            geometry=ProfileGeometry.from_dict(geom_data),
            typography=ProfileTypography.from_dict(typo_data),
            special_blocks=ProfileSpecialBlocks.from_dict(blocks_data),
            publisher_rules=dict(pub_rules),
            anomalies=list(data.get("anomalies", [])),
            learned_fixes=dict(data.get("learned_fixes", {})),
            chapter_history=dict(data.get("chapter_history", {})),
        )

    def record_chapter_audit(
        self,
        chapter_name: str,
        audit_data: Dict[str, Any],
        visual_data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Records chapter verification results, visual scores, and discovered layout anomalies.

        Args:
            chapter_name: Name or slug of the processed chapter.
            audit_data: Result dictionary from AccuracyVerifier.
            visual_data: Optional visual audit result from VisualAuditor / MiniCPM-V.

        Returns:
            None.
        """
        import time

        checks = audit_data.get("checks", {})
        passed = audit_data.get("passed", True)
        accuracy = audit_data.get("accuracy_percent", 0.0)

        history_entry: Dict[str, Any] = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%SZ", time.gmtime()),
            "passed": passed,
            "accuracy_percent": accuracy,
            "checks_summary": {k: (v.get("passed") if isinstance(v, dict) else v) for k, v in checks.items()},
        }

        if visual_data:
            history_entry["visual_audit"] = {
                "status": visual_data.get("status"),
                "quality_score": visual_data.get("quality_score"),
                "vision_model": visual_data.get("vision_model"),
                "audited_pages_count": len(visual_data.get("audited_pages", [])),
            }

            # Extract any visual defects as book anomalies
            for ap in visual_data.get("audited_pages", []):
                if not ap.get("verified", True) and ap.get("vision_defect"):
                    anomaly = {
                        "chapter": chapter_name,
                        "page": ap.get("page"),
                        "feature": ap.get("feature"),
                        "defect": ap.get("vision_defect"),
                        "confidence": ap.get("confidence"),
                    }
                    if anomaly not in self.anomalies:
                        self.anomalies.append(anomaly)

        self.chapter_history[chapter_name] = history_entry

    def validate(self) -> List[str]:
        """Validates internal consistency and boundary ranges of profile parameters.

        Returns:
            List of warning or error strings (empty if valid).
        """
        warnings = []
        if self.geometry.page_width <= 0 or self.geometry.page_height <= 0:
            warnings.append("Invalid page dimensions: width and height must be positive.")
        if self.geometry.header_cutoff_y >= self.geometry.footer_cutoff_y:
            warnings.append("Header cutoff must be strictly less than footer cutoff.")
        if self.geometry.layout == "two_column" and self.geometry.gutter_split_x is None:
            warnings.append("Two-column layout specified without gutter_split_x coordinate.")
        return warnings

    def apply_feedback(self, anomaly_type: str, details: Optional[Dict[str, Any]] = None) -> bool:
        """Applies closed-loop healing feedback to adjust boundaries when auditor detects drift.

        Args:
            anomaly_type: Type of layout anomaly ('LEAKED_HEADER', 'LEAKED_FOOTER', 'GUTTER_OVERFLOW').
            details: Optional dictionary containing specific coordinates or delta hints.

        Returns:
            True if geometry parameters were adjusted, False otherwise.
        """
        details = details or {}
        delta = details.get("delta", 5.0)

        if anomaly_type == "LEAKED_HEADER":
            # Running header leaked into body text -> push cutoff downwards
            old_cutoff = self.geometry.header_cutoff_y
            self.geometry.header_cutoff_y = round(old_cutoff + delta, 2)
            return True

        elif anomaly_type == "LEAKED_FOOTER":
            # Running footer or page number leaked -> pull footer cutoff upwards
            old_cutoff = self.geometry.footer_cutoff_y
            self.geometry.footer_cutoff_y = round(old_cutoff - delta, 2)
            return True

        elif anomaly_type == "GUTTER_OVERFLOW":
            # Words crossing column boundary -> widen column gap if split_x is defined
            if self.geometry.gutter_split_x is not None:
                split_override = details.get("split_x")
                if split_override:
                    self.geometry.gutter_split_x = round(float(split_override), 2)
                    return True
        return False
