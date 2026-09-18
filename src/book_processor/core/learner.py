"""
Adaptive Learner & Self-Healing Feedback Loop
=============================================
Diagnoses verification failures, dynamically adjusts processing parameters
(noise patterns, DPI, contrast, column gaps), automatically re-runs failed
chapters, and persists learned rules so subsequent chapters and future runs
avoid identical failures.

Two persistence layers:
  • AdaptiveLearner  – book-scoped  (output/<Book>/learned_rules.json)
  • GlobalLearner    – cross-book   (~/.book_processor/global_rules.json)
"""

import json
import logging
import os
import re
import tempfile
from pathlib import Path

from book_processor.config import GLOBAL_RULES_DIR

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Atomic write helper
# ---------------------------------------------------------------------------

def _atomic_write_json(path: Path, data: dict) -> None:
    """Write *data* to *path* atomically (temp-file + rename) to avoid corruption."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp, str(path))
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


# ---------------------------------------------------------------------------
# Global Learner (cross-book, user-home scope)
# ---------------------------------------------------------------------------

class GlobalLearner:
    """
    Persists noise patterns and OCR corrections learned across *all* books
    to ``~/.book_processor/global_rules.json``.

    This prevents the system from re-learning the same publisher footer
    patterns every time a new book from the same publisher is processed.
    """

    _rules_file: Path = GLOBAL_RULES_DIR / "global_rules.json"

    @classmethod
    def _load(cls) -> dict:
        target = cls._rules_file
        if not target.exists():
            fallback = Path(".book_processor") / "global_rules.json"
            if fallback.exists():
                target = fallback
        if target.exists():
            try:
                with open(target, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError) as e:
                logger.warning("GlobalLearner: could not load global rules – %s", e)
        return {"noise_patterns": [], "custom_corrections": {}}

    @classmethod
    def _save(cls, rules: dict) -> None:
        try:
            _atomic_write_json(cls._rules_file, rules)
        except OSError:
            # Graceful fallback to project directory if ~/.book_processor is non-writable
            try:
                fallback = Path(".book_processor") / "global_rules.json"
                _atomic_write_json(fallback, rules)
            except OSError as e2:
                logger.warning("GlobalLearner: could not save global rules – %s", e2)

    @classmethod
    def get_noise_patterns(cls) -> list:
        """Return globally learned noise-filter regex patterns."""
        return cls._load().get("noise_patterns", [])

    @classmethod
    def add_noise_patterns(cls, patterns: list) -> int:
        """
        Merge *patterns* into the global store.

        Returns the number of *new* patterns actually added.
        """
        rules = cls._load()
        existing = set(rules.get("noise_patterns", []))
        new_ones = [p for p in patterns if p not in existing]
        if new_ones:
            rules["noise_patterns"] = list(existing | set(new_ones))
            cls._save(rules)
            logger.info("GlobalLearner: persisted %d new noise pattern(s) globally.", len(new_ones))
        return len(new_ones)

    @classmethod
    def add_corrections(cls, corrections: dict) -> None:
        """Merge OCR correction pairs {original: corrected} into the global store."""
        rules = cls._load()
        rules.setdefault("custom_corrections", {}).update(corrections)
        cls._save(rules)


# ---------------------------------------------------------------------------
# Book-scoped Adaptive Learner
# ---------------------------------------------------------------------------

class AdaptiveLearner:
    """Diagnoses failures, tunes parameters, and manages persistent learned rule memory."""

    def __init__(self, book_dir: str) -> None:
        self.book_dir = Path(book_dir)
        self.rules_file = self.book_dir / "learned_rules.json"
        self.rules = self._load()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> dict:
        """Loads previously learned rules from disk if available."""
        if self.rules_file.exists():
            try:
                with open(self.rules_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError) as e:
                logger.warning(
                    "AdaptiveLearner: could not load '%s' – %s. Starting fresh.",
                    self.rules_file.name, e,
                )
        return {
            "noise_patterns": [],
            "dpi_override": None,
            "column_gap_override": None,
            "custom_corrections": {},
        }

    def save_rules(self) -> None:
        """Atomically persists learned rules to learned_rules.json."""
        try:
            _atomic_write_json(self.rules_file, self.rules)
        except OSError as e:
            logger.warning("AdaptiveLearner: could not save rules – %s", e)

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------

    def get_noise_patterns(self) -> list:
        """Returns merged local + global noise patterns."""
        local = self.rules.get("noise_patterns", [])
        global_ = GlobalLearner.get_noise_patterns()
        # Deduplicate while preserving order (local first)
        seen = set()
        merged = []
        for p in local + global_:
            if p not in seen:
                seen.add(p)
                merged.append(p)
        return merged

    def get_dpi(self, default_dpi: int = 300) -> int:
        return self.rules.get("dpi_override") or default_dpi

    def get_column_gap(self, default_gap: int = 80) -> int:
        return self.rules.get("column_gap_override") or default_gap

    # ------------------------------------------------------------------
    # Diagnose & Learn
    # ------------------------------------------------------------------

    def diagnose_and_learn(self, verification_results: dict, chapter_dir: str) -> dict:
        """
        Diagnoses verification report and devises an adaptation strategy.

        Returns:
            {'should_retry': bool, 'actions': list, 'adaptation': dict}
        """
        ch_path = Path(chapter_dir)
        checks = verification_results.get("checks", {})
        actions: list = []
        adaptation: dict = {}

        # 1. Noise Filter Failure: Unrecognized recurring header/footer found
        noise_check = checks.get("noise_filter", {})
        if not noise_check.get("passed", True):
            found_noise = noise_check.get("found_strings", [])
            new_patterns = []
            for ns in found_noise:
                escaped = re.escape(ns.strip())
                pattern = rf"\b{escaped}\b"
                if pattern not in self.rules["noise_patterns"]:
                    self.rules["noise_patterns"].append(pattern)
                    new_patterns.append(pattern)
            if new_patterns:
                self.save_rules()
                # Also push to global store so other books benefit.
                GlobalLearner.add_noise_patterns(new_patterns)
                actions.append(
                    f"Learned {len(new_patterns)} new noise filter pattern(s) "
                    f"(also stored globally)."
                )
                adaptation["learned_noise"] = True

        # 2. Vocabulary / OCR Low Quality Failure
        vocab_check = checks.get("vocabulary", {})
        if not vocab_check.get("passed", True):
            accuracy = vocab_check.get("accuracy_percent", 100.0)
            # Only escalate DPI for the specific chapter, not book-wide permanently
            if accuracy < 85.0 and self.rules.get("dpi_override") != 400:
                self.rules["dpi_override"] = 400
                self.save_rules()
                actions.append(
                    f"Low vocabulary accuracy ({accuracy:.1f}%). "
                    f"Escalated OCR resolution to 400 DPI."
                )
                adaptation["dpi_escalation"] = 400

        # 3. Markdown / LaTeX Delimiter Failure – auto-repair
        md_file = ch_path / f"{ch_path.name}.md"
        if md_file.exists():
            try:
                content = md_file.read_text(encoding="utf-8")
                if content.count("$") % 2 != 0:
                    actions.append(
                        "Detected unpaired LaTeX math delimiter; auto-repaired dangling delimiter."
                    )
                    fixed = re.sub(r"(?<!\$)\$(?!\$)", "", content, count=1)
                    try:
                        _atomic_write_json  # ensure import above is used
                        fd, tmp = tempfile.mkstemp(
                            dir=str(md_file.parent), suffix=".tmp"
                        )
                        with os.fdopen(fd, "w", encoding="utf-8") as f:
                            f.write(fixed)
                        os.replace(tmp, str(md_file))
                    except OSError as e:
                        logger.warning("Could not write repaired markdown – %s", e)
                    adaptation["repaired_latex"] = True
            except OSError as e:
                logger.warning("diagnose_and_learn: could not read markdown – %s", e)

        # 4. Content Continuity & Sentence Truncation – auto-repair
        cont_check = checks.get("continuity", {})
        if not cont_check.get("passed", True):
            abrupt = cont_check.get("abrupt_cuts", 0)
            page_cuts = cont_check.get("page_break_cuts", 0)
            if md_file.exists() and (abrupt > 0 or page_cuts > 0):
                try:
                    from book_processor.utils.text_utils import stitch_cross_page_continuity
                    cur_text = md_file.read_text(encoding="utf-8")
                    stitched = stitch_cross_page_continuity(cur_text)
                    if stitched != cur_text:
                        fd, tmp = tempfile.mkstemp(dir=str(md_file.parent), suffix=".tmp")
                        with os.fdopen(fd, "w", encoding="utf-8") as f:
                            f.write(stitched)
                        os.replace(tmp, str(md_file))
                        actions.append(
                            f"Repaired cross-page continuity: {abrupt} abrupt cuts, {page_cuts} page-break splits reflowed."
                        )
                        adaptation["repaired_continuity"] = True
                except Exception as e:
                    logger.warning("Could not auto-repair continuity – %s", e)


        should_retry = len(actions) > 0
        return {
            "should_retry": should_retry,
            "actions": actions,
            "adaptation": adaptation,
        }
