"""Domain models for user corrections, error classification, and regression tracking.

Encapsulates human-in-the-loop edits performed in the web UI or via MCP tools,
linking the original and modified texts with taxonomy classification and user notes.
"""

from __future__ import annotations

import datetime
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any, Dict


@dataclass(frozen=True)
class CorrectionRecord:
    """Immutable record of a user correction on a chapter or document.

    Attributes:
        id: Unique identifier for the correction record.
        book_id: Directory name of the parent book/literature.
        chapter_id: Name of the chapter folder (e.g. `Ch01-Introduction-to-Scientific-Research`).
        created_at: ISO 8601 formatted timestamp when the record was created.
        issue_type: Taxonomy tag (e.g. `ocr_typo`, `heading_level`, `table_layout`, `missing_image`).
        original_text: Snippet of original text before modification.
        corrected_text: Snippet of modified text after correction.
        diff_snippet: Unified diff summarizing the modifications.
        user_notes: Optional remarks or root cause explanation from the user.
        applied: Whether the correction has been saved to the chapter markdown.
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    book_id: str = ""
    chapter_id: str = ""
    created_at: str = field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())
    issue_type: str = "general_edit"
    original_text: str = ""
    corrected_text: str = ""
    diff_snippet: str = ""
    user_notes: str = ""
    applied: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Converts the record into a serializable dictionary.

        Returns:
            Dictionary containing all fields.
        """
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> CorrectionRecord:
        """Constructs a CorrectionRecord from a dictionary.

        Args:
            data: Raw dictionary loaded from JSON or API payload.

        Returns:
            Instantiated CorrectionRecord.
        """
        return cls(
            id=str(data.get("id", str(uuid.uuid4()))),
            book_id=str(data.get("book_id", "")),
            chapter_id=str(data.get("chapter_id", "")),
            created_at=str(data.get("created_at", datetime.datetime.now(datetime.timezone.utc).isoformat())),
            issue_type=str(data.get("issue_type", "general_edit")),
            original_text=str(data.get("original_text", "")),
            corrected_text=str(data.get("corrected_text", "")),
            diff_snippet=str(data.get("diff_snippet", "")),
            user_notes=str(data.get("user_notes", "")),
            applied=bool(data.get("applied", True)),
        )
