"""
Human-in-the-Loop AI Review & Diff Manager
==========================================
Manages interactive inspection, approval, or rejection of AI-proposed corrections
while guaranteeing zero destructive overwrite without user consent.

High-confidence proposals (>= AUTO_ACCEPT_CONFIDENCE_THRESHOLD) are
automatically applied without requiring human review.
"""

import json
import logging
import os
import re
import tempfile
from pathlib import Path

from literature_parser.config.processor_config import AUTO_ACCEPT_CONFIDENCE_THRESHOLD
from literature_parser.services.core.learner import GlobalLearner

logger = logging.getLogger(__name__)


def _detect_archetype_from_dir(path: Path) -> str:
    """
    Walks *path* and its parents looking for ``book_profile.json`` to determine
    whether the document is a 'journal' article or a 'textbook'.
    Falls back to 'textbook' if no profile is found.
    """
    for candidate in [path, *path.parents]:
        profile = candidate / "book_profile.json"
        if profile.exists():
            try:
                with open(profile, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                if (
                    data.get("archetype") == "journal"
                    or data.get("is_journal", False)
                    or data.get("features", {}).get("is_journal_article", False)
                ):
                    return "journal"
            except Exception:
                pass
        if candidate == candidate.parent:
            break
    return "textbook"


def _atomic_write_json(path: Path, data: dict) -> None:
    """Write *data* to *path* atomically (temp-file + rename)."""
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


def _atomic_write_text(path: Path, text: str) -> None:
    """Write *text* to *path* atomically (temp-file + rename)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp, str(path))
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


class ReviewManager:
    """Manages chapter-level AI review manifests and interactive CLI approvals."""

    @staticmethod
    def get_review_json_path(chapter_dir: str) -> Path:
        ch_path = Path(chapter_dir)
        return ch_path / f"{ch_path.name}.review.json"

    @staticmethod
    def get_markdown_path(chapter_dir: str) -> Path:
        ch_path = Path(chapter_dir)
        return ch_path / f"{ch_path.name}.md"

    @classmethod
    def save_review_manifest(cls, chapter_dir: str, proposals: list) -> dict:
        """
        Saves proposed corrections to <Chapter>.review.json.

        Proposals with confidence >= AUTO_ACCEPT_CONFIDENCE_THRESHOLD are
        automatically accepted and marked as AUTO_ACCEPTED; the rest are PENDING.

        Returns:
            {'auto_accepted': int, 'pending': int}
        """
        if not proposals:
            return {"auto_accepted": 0, "pending": 0}

        auto_accepted = []
        pending = []
        for idx, p in enumerate(proposals, 1):
            confidence = float(p.get("confidence", 0.5))
            entry = {
                "id": p.get("id", f"rev-{idx}"),
                "original": p.get("original", ""),
                "proposed": p.get("proposed", ""),
                "reason": p.get("reason", ""),
                "category": p.get("category", "ocr_typo"),
                "confidence": confidence,
                "status": "PENDING",
            }
            if confidence >= AUTO_ACCEPT_CONFIDENCE_THRESHOLD:
                entry["status"] = "AUTO_ACCEPTED"
                auto_accepted.append(entry)
            else:
                pending.append(entry)

        manifest_path = cls.get_review_json_path(chapter_dir)
        data = {
            "chapter": Path(chapter_dir).name,
            "total_proposals": len(proposals),
            "auto_accepted_count": len(auto_accepted),
            "pending_count": len(pending),
            "proposals": auto_accepted + pending,
        }
        try:
            _atomic_write_json(manifest_path, data)
        except OSError as e:
            logger.error("ReviewManager: could not save review manifest – %s", e)

        # Immediately apply auto-accepted proposals directly (no annotation markers needed)
        if auto_accepted:
            md_path = cls.get_markdown_path(chapter_dir)
            if md_path.exists():
                try:
                    md_text = md_path.read_text(encoding="utf-8")
                    changed = False
                    for entry in auto_accepted:
                        orig = entry.get("original", "")
                        proposed = entry.get("proposed", "")
                        if orig and orig in md_text and orig != proposed:
                            md_text = md_text.replace(orig, proposed, 1)
                            changed = True
                    if changed:
                        _atomic_write_text(md_path, md_text)
                except OSError as e:
                    logger.error("ReviewManager: could not apply auto-accept – %s", e)
            logger.info(
                "ReviewManager: auto-accepted %d high-confidence proposal(s) for '%s'.",
                len(auto_accepted),
                Path(chapter_dir).name,
            )

            # ──────────────────────────────────────────────────────────────
            # Cross-document learning: propagate high-confidence repairs to
            # GlobalLearner so every future document of the same archetype
            # benefits immediately without Ollama re-discovering the same fix.
            # ──────────────────────────────────────────────────────────────
            try:
                archetype = _detect_archetype_from_dir(Path(chapter_dir))
                pushed = GlobalLearner.add_fix_rules(auto_accepted, archetype=archetype)
                if pushed > 0:
                    logger.info(
                        "ReviewManager: propagated %d new fix rule(s) to global memory (archetype: %s).",
                        pushed, archetype,
                    )
            except Exception as _gl_err:
                logger.debug("ReviewManager: GlobalLearner propagation skipped – %s", _gl_err)

        return {"auto_accepted": len(auto_accepted), "pending": len(pending)}


    @classmethod
    def load_review_manifest(cls, chapter_dir: str) -> dict:
        manifest_path = cls.get_review_json_path(chapter_dir)
        if not manifest_path.exists():
            return {"proposals": []}
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("ReviewManager: could not load review manifest – %s", e)
            return {"proposals": []}

    @classmethod
    def apply_review_decisions(
        cls,
        chapter_dir: str,
        accept_all: bool = False,
        decisions: dict = None,
    ) -> dict:
        """
        Programmatically applies review decisions (accept or reject) to the
        chapter Markdown and updates the review manifest.

        Args:
            decisions: Optional dict mapping rev_id -> 'y' (accept) or 'n' (reject).
        """
        manifest = cls.load_review_manifest(chapter_dir)
        proposals = manifest.get("proposals", [])
        md_path = cls.get_markdown_path(chapter_dir)
        if not md_path.exists():
            return {"success": False, "error": f"Markdown file not found: {md_path}"}

        try:
            md_text = md_path.read_text(encoding="utf-8")
        except OSError as e:
            return {"success": False, "error": str(e)}

        applied_count = 0
        decisions = decisions or {}

        for prop in proposals:
            if prop.get("status") not in ("PENDING", "AUTO_ACCEPTED"):
                continue
            # Re-check: don't re-apply already accepted
            if prop.get("status") == "AUTO_ACCEPTED" and decisions.get(prop.get("id")) != "y":
                continue

            rev_id = prop.get("id")
            orig = prop.get("original", "")
            prop_text = prop.get("proposed", "")

            if accept_all or decisions.get(rev_id) in ("y", "accept", True):
                action = "y"
            elif decisions.get(rev_id) in ("n", "reject", False):
                action = "n"
            else:
                continue  # leave pending

            pattern = (
                rf'<!-- AI-REVIEW-START id="{re.escape(rev_id)}"[^>]*-->\s*'
                rf"<!-- ORIGINAL:\s*(.*?)\s*-->\s*"
                rf"(?:<!-- REASON:[^>]*-->\s*)?"
                rf"(.*?)\s*"
                rf"<!-- AI-REVIEW-END -->"
            )

            if action == "y":
                md_text = re.sub(pattern, prop_text, md_text, flags=re.DOTALL)
                prop["status"] = "ACCEPTED"
                applied_count += 1
            else:
                md_text = re.sub(pattern, orig, md_text, flags=re.DOTALL)
                prop["status"] = "REJECTED"
                applied_count += 1

        try:
            _atomic_write_text(md_path, md_text)
            _atomic_write_json(cls.get_review_json_path(chapter_dir), manifest)
        except OSError as e:
            return {"success": False, "error": str(e)}

        return {"success": True, "applied_count": applied_count}

    @classmethod
    def interactive_review(cls, chapter_dir: str) -> None:
        """
        Interactive terminal CLI tool to accept or reject AI corrections.
        Shows colored diff and updates Markdown upon user decision.
        """
        manifest = cls.load_review_manifest(chapter_dir)
        proposals = manifest.get("proposals", [])
        pending = [p for p in proposals if p.get("status") == "PENDING"]

        if not pending:
            print(f"\n[✓] No pending AI reviews for chapter: {Path(chapter_dir).name}")
            auto = sum(1 for p in proposals if p.get("status") in ("AUTO_ACCEPTED", "ACCEPTED"))
            if auto:
                print(f"    ({auto} proposal(s) were auto-accepted based on confidence threshold.)")
            return

        md_path = cls.get_markdown_path(chapter_dir)
        if not md_path.exists():
            print(f"[!] Markdown file not found: {md_path}")
            return

        print(f"\n{'='*70}")
        print(f"[AI REVIEW DESK] Chapter: {Path(chapter_dir).name}")
        print(f"Total proposals to review: {len(pending)}")
        print(f"{'='*70}\n")

        decisions = {}
        accept_all = False

        for idx, prop in enumerate(pending, 1):
            rev_id = prop.get("id")
            orig = prop.get("original", "")
            prop_text = prop.get("proposed", "")
            reason = prop.get("reason", "")
            cat = prop.get("category", "general")
            conf = prop.get("confidence", 0.5)

            print(f"[{idx}/{len(pending)}] Review Item #{rev_id} [Category: {cat}] [Confidence: {conf:.0%}]")
            print(f"  Reason: {reason}")
            print(f"  \033[31m- Original: {orig}\033[0m")
            print(f"  \033[32m+ Proposed: {prop_text}\033[0m")

            if accept_all:
                decisions[rev_id] = "y"
                print("  -> \033[32mACCEPTED\033[0m\n")
            else:
                prompt = "  Action: [y] Accept  [n] Reject  [a] Accept All  [q] Quit: "
                try:
                    choice = input(prompt).strip().lower()
                except (EOFError, KeyboardInterrupt):
                    print("\n[!] Review session paused.")
                    break

                if choice == "a":
                    accept_all = True
                    decisions[rev_id] = "y"
                    print("  -> \033[32mACCEPTED\033[0m\n")
                elif choice == "q":
                    print("[!] Exiting review session.")
                    break
                elif choice in ("y", "yes"):
                    decisions[rev_id] = "y"
                    print("  -> \033[32mACCEPTED\033[0m\n")
                else:
                    decisions[rev_id] = "n"
                    print("  -> \033[33mREJECTED (Original preserved)\033[0m\n")

        cls.apply_review_decisions(chapter_dir, accept_all=accept_all, decisions=decisions)
        print(f"[✓] Review decisions saved to: {md_path.name}\n")

    @classmethod
    def interactive_review_book(cls, book_dir: str) -> None:
        """
        Aggregates and reviews pending AI proposals across all chapters in a book.
        Allows human reviewers to process all book issues from a single centralized console.
        """
        b_path = Path(book_dir)
        ch_root = b_path / "chapters" if (b_path / "chapters").exists() else b_path
        chapter_dirs = sorted([d for d in ch_root.iterdir() if d.is_dir() and (d / "review_manifest.json").exists()])

        if not chapter_dirs:
            print(f"\n[✓] No pending AI reviews found in book: {b_path.name}")
            return

        total_pending = 0
        chapters_with_pending = []
        for ch in chapter_dirs:
            manifest = cls.load_review_manifest(str(ch))
            pending = [p for p in manifest.get("proposals", []) if p.get("status") == "PENDING"]
            if pending:
                total_pending += len(pending)
                chapters_with_pending.append((ch, len(pending)))

        if not chapters_with_pending:
            print(f"\n[✓] All AI proposals in book '{b_path.name}' have been resolved (100% PASS / reviewed).")
            return

        print(f"\n{'='*75}")
        print(f"[CENTRALIZED REVIEW CONSOLE] Book: {b_path.name}")
        print(f"Total pending proposals: {total_pending} across {len(chapters_with_pending)} chapter(s)")
        print(f"{'='*75}\n")

        for ch, count in chapters_with_pending:
            print(f"--- Reviewing Chapter: {ch.name} ({count} pending) ---")
            cls.interactive_review(str(ch))
