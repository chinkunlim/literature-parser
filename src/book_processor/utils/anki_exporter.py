"""
Flashcard Anki Export Utility
=============================
Exports chapter key terms & flashcards into standard Anki tab-delimited text
format or generates an Anki deck import file (.txt) suitable for direct import
into Anki or spaced-repetition mobile apps.
"""

import re
from pathlib import Path
from typing import List, Dict, Any


class AnkiExporter:
    """Exports structured Flashcard decks to Anki-compatible TSV format."""

    @staticmethod
    def export_chapter_flashcards_to_tsv(terms: List[Dict[str, Any]], output_tsv_path: Path, chapter_name: str = "") -> int:
        """
        Exports terms to TSV format:
        Front (Term + Chapter tag) \t Back (Definition + Active Recall prompt) \t Tags
        """
        if not terms:
            return 0

        output_tsv_path = Path(output_tsv_path)
        output_tsv_path.parent.mkdir(parents=True, exist_ok=True)

        tag = re.sub(r'[^a-zA-Z0-9_]+', '_', chapter_name).strip('_') if chapter_name else "Textbook_Key_Terms"

        lines = ["#separator:tab", "#html:true", f"#tags column:3"]
        count = 0
        for t in terms:
            term_name = t.get('term', '').strip()
            if not term_name:
                continue
            definition = t.get('definition') or ''
            page = t.get('page')
            page_info = f"<br><small><i>(Page {page})</i></small>" if page else ""

            front = f"<b>{term_name}</b>{page_info}"
            if definition:
                back = f"{definition}<br><br><i>Ask yourself: How does this connect to other chapter concepts?</i>"
            else:
                loc = f"Page {page}" if page else "this chapter"
                back = f"<i>Key term mentioned on {loc}. Recall its context and definition.</i>"

            lines.append(f"{front}\t{back}\t{tag}")
            count += 1

        with open(output_tsv_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines) + '\n')

        return count
