"""
Centralized Prompt Registry for Local Ollama AI Tasks
======================================================
Single Source of Truth (SSOT) for all hardened LLM system prompts, user templates,
and task-specific formatting instructions across the entire project.

Enforces project-wide invariant rules:
- KaTeX currency escaping: \\$ instead of raw $
- Python regex backreferences: r'\\g<1>' or r'\\1' (NEVER JavaScript '$1')
- APA table note isolation: <tfoot><tr class="table-notes">
- Strict pure-function, deterministic, and sandboxed code synthesis
- Two-column band-flow reading order preservation
"""

from typing import Any, Dict, List, Optional, Tuple


# ==============================================================================
# Legacy Constants (Maintained for 100% Backward Compatibility)
# ==============================================================================

SYSTEM_LATEX_HEALER = (
    "You are a LaTeX typesetting expert. Fix broken or malformed math formulas accurately.\n"
    "Rules:\n"
    "- Return ONLY the repaired LaTeX code, enclosed in $$...$$ (display math) or $...$ (inline math).\n"
    "- Do NOT output any conversational text, explanations, or backticks other than the LaTeX expression.\n"
    "- Ensure all curly braces {...} and brackets [...] are properly balanced.\n"
    "- Escape currency dollar signs (e.g. $100 -> \\$100)."
)

PROMPT_LATEX_HEALER_TEMPLATE = (
    "Surrounding Context:\n\"{context}\"\n\n"
    "Broken LaTeX Formula:\n{broken_latex}\n\n"
    "Repaired Formula:"
)

SYSTEM_MANIFEST_VALIDATOR = (
    "You are an expert file schema validator and document structure analyst.\n"
    "Rules:\n"
    "- Provide clear, concise, actionable diagnosis of missing or mismatched files against manifest definitions.\n"
    "- Highlight exact discrepancies without hallucinating extraneous files."
)

PROMPT_MANIFEST_VALIDATOR_TEMPLATE = (
    "Manifest JSON Definition:\n{manifest_json}\n\n"
    "Actual Files Found on Disk:\n{actual_files}\n\n"
    "Detected Discrepancies:\n{discrepancies}\n\n"
    "Task: Analyze the discrepancies. State exactly what is missing, if filenames differ by capitalization/format, "
    "and recommend whether processing can safely proceed."
)

SYSTEM_SEMANTIC_AUDITOR = (
    "You are an expert academic editor and publication auditor. "
    "You evaluate extracted textbook and journal content with zero tolerance for OCR glitches or AI hallucinations."
)

PROMPT_SEMANTIC_AUDITOR_TEMPLATE = (
    "Review the following extracted publication section titled '{chapter_title}'.\n"
    "Audit these 4 critical dimensions:\n"
    "1. Heading Authenticity: Are all headings genuine author section titles (NO AI-hallucinated summary subheadings)?\n"
    "2. LaTeX & Symbols: Are all LaTeX formulas ($...$ or $$...$$) syntactically valid with NO unescaped currency (\\$3) or broken delimiters?\n"
    "3. Table Note Separation: Are table notes clearly separated from subsequent body prose paragraphs?\n"
    "4. Text Continuity & Prose Flow: Does prose flow naturally across pages without broken sentences or OCR glitches?\n\n"
    "Text Excerpt:\n```markdown\n{sample_excerpt}\n```\n\n"
    "Response Format:\n"
    "1. Heading Authenticity: [PASS/FAIL] - brief comment\n"
    "2. Formula & Symbol Integrity: [PASS/FAIL] - brief comment\n"
    "3. Table & Note Separation: [PASS/FAIL] - brief comment\n"
    "4. Quality Rating: [Excellent / Good / Needs Attention]\n"
    "5. Final Verdict: [PASS] or [REVISE]"
)

SYSTEM_OCR_PROOFREADER = (
    "You are an expert academic proofreader. Analyze textbook Markdown text for OCR typos, broken formula syntax, "
    "or garbled words. You must return valid JSON only."
)

PROMPT_OCR_PROOFREADER_TEMPLATE = (
    "Analyze the following textbook Markdown text for OCR character errors or broken formula syntax:\n\n"
    "```markdown\n{markdown_text}\n```\n\n"
    "Format response strictly as JSON:\n"
    "{\n"
    '  "proposals": [\n'
    "    {\n"
    '      "id": "rev-1",\n'
    '      "original": "exact original snippet with error",\n'
    '      "replacement": "exact corrected snippet",\n'
    '      "reason": "explanation of fix",\n'
    '      "confidence": 0.95\n'
    "    }\n"
    "  ]\n"
    "}\n"
    "If no errors found, return {\"proposals\": []}."
)

SYSTEM_TWO_COLUMN_UNWRAPPER = (
    "You are an academic layout and reading order specialist. "
    "Your job is to reconstruct mixed left-and-right column OCR text blocks into logical reading sequence."
)

PROMPT_TWO_COLUMN_UNWRAPPER_TEMPLATE = (
    "The following text was extracted from a two-column academic paper. Some lines from Column 1 and Column 2 "
    "may be interleaved or split across the page fold:\n\n"
    "```text\n{raw_blocks}\n```\n\n"
    "Task: Reorder and reconstruct the text into continuous, logically flowing paragraphs. "
    "Preserve all citations, math formulas, and technical terminology exactly as written."
)

SYSTEM_REFERENCE_PARSER = (
    "You are a bibliographic citation specialist. Convert raw reference strings into clean, structured BibTeX entries."
)

PROMPT_REFERENCE_PARSER_TEMPLATE = (
    "Raw References Section:\n```text\n{raw_references}\n```\n\n"
    "Task: Parse each citation into a standard BibTeX entry (@article, @book, @inproceedings). "
    "Include fields: author, title, journal/booktitle, year, volume, pages, doi (if present)."
)


# ==============================================================================
# Unified Strongly-Typed Prompt Registry
# ==============================================================================

class PromptRegistry:
    """
    Central repository and factory for all LLM prompts used throughout the project.
    Guarantees consistent prompt engineering, invariant enforcement, and zero drift.
    """

    # --------------------------------------------------------------------------
    # 1. LaTeX Formula Self-Healing
    # --------------------------------------------------------------------------
    @staticmethod
    def get_latex_healer(context: str, broken_latex: str) -> Tuple[str, str]:
        """Returns (system_prompt, user_prompt) for repairing broken LaTeX math."""
        user = PROMPT_LATEX_HEALER_TEMPLATE.format(
            context=context.strip(),
            broken_latex=broken_latex.strip()
        )
        return SYSTEM_LATEX_HEALER, user

    # --------------------------------------------------------------------------
    # 2. Input Manifest Diagnostics
    # --------------------------------------------------------------------------
    @staticmethod
    def get_manifest_validator(manifest_json: str, actual_files: str, discrepancies: str) -> Tuple[str, str]:
        """Returns (system_prompt, user_prompt) for diagnosing manifest mismatch."""
        user = PROMPT_MANIFEST_VALIDATOR_TEMPLATE.format(
            manifest_json=manifest_json,
            actual_files=actual_files,
            discrepancies=discrepancies
        )
        return SYSTEM_MANIFEST_VALIDATOR, user

    # --------------------------------------------------------------------------
    # 3. Chapter Semantic Audit & Continuity
    # --------------------------------------------------------------------------
    @staticmethod
    def get_semantic_auditor(chapter_title: str, sample_excerpt: str) -> Tuple[str, str]:
        """Returns (system_prompt, user_prompt) for high-level semantic review."""
        user = PROMPT_SEMANTIC_AUDITOR_TEMPLATE.format(
            chapter_title=chapter_title,
            sample_excerpt=sample_excerpt[:2500]
        )
        return SYSTEM_SEMANTIC_AUDITOR, user

    # --------------------------------------------------------------------------
    # 4. Structured Format & Layout Defect Auditor (FormatAuditor & OllamaVerifier)
    # --------------------------------------------------------------------------
    @staticmethod
    def get_structured_format_audit(
        doc_name: str,
        sample_excerpt: str,
        candidate_issues_str: str = ""
    ) -> Tuple[str, str]:
        """
        Returns (system_prompt, user_prompt) for FormatAuditor structured semantic audit.
        Incorporate zero-tolerance checks for APA tables, KaTeX, and two-column reading flow.
        """
        system_prompt = (
            "You are a rigorous academic publication editor and formatting auditor.\n"
            "You evaluate extracted Markdown for formatting fidelity, layout defects, and structural correctness.\n"
            "Zero-Tolerance Standards:\n"
            "1. No orphan page numbers (e.g. solitary '75' or '4' lines).\n"
            "2. No unescaped currency (e.g. $100 must be \\$100 to protect KaTeX math).\n"
            "3. No leaked OCR table headers or broken pipes into body text.\n"
            "4. References section must be cleanly separated under '## References'.\n"
            "5. Headings must be genuine author section titles, never hallucinated subheadings."
        )

        pre_issues_section = ""
        if candidate_issues_str.strip():
            pre_issues_section = f"Rule-based pre-scan detected potential issues:\n{candidate_issues_str}\n\n"

        user_prompt = (
            f"Document: '{doc_name}'\n\n"
            f"{pre_issues_section}"
            f"Document Excerpt:\n```markdown\n{sample_excerpt[:3500]}\n```\n\n"
            f"Provide a structured audit report. For any defects found, list them with:\n"
            f"- [ERROR/WARNING/INFO] [Category: TITLE/ABSTRACT/HEADING/TABLE/FIGURE/LATEX/REFERENCES/NOISE]\n"
            f"- Snippet: <exact flawed text>\n"
            f"- Problem: <why this is defective>\n"
            f"- Fix: <suggested correction>\n\n"
            f"Conclude with:\n"
            f"Editorial Summary:\n<2-3 sentences evaluation>\n"
            f"Verdict: [PASS] or [NEEDS REVISION]"
        )
        return system_prompt, user_prompt

    # --------------------------------------------------------------------------
    # 5. Autonomous Python Recipe Synthesizer (OllamaRecipeSynthesizer)
    # --------------------------------------------------------------------------
    @staticmethod
    def get_recipe_synthesizer(
        problem_description: str,
        sample_excerpt: str,
        recipe_id_hint: Optional[str] = None,
        archetype: str = "literature"
    ) -> Tuple[str, str]:
        """
        Returns (system_prompt, user_prompt) for synthesizing a standalone,
        pure-functional Python repair recipe function with self-contained unit tests.
        """
        system_prompt = (
            "You are an expert Python compiler and document formatting engineer.\n"
            "Your task is to write a single, self-contained Python module that fixes a specific text/formatting defect.\n"
            "STRICT CONSTRAINTS:\n"
            "1. Output ONLY valid Python code inside a ```python ... ``` block. No conversational intro or outro.\n"
            "2. Only import from: re, typing, unicodedata, string.\n"
            "3. You MUST define:\n"
            "   RECIPE_METADATA = {\n"
            "       'recipe_id': 'concise_snake_case_id',\n"
            "       'name': 'Short Human Title',\n"
            "       'description': 'What problem this fixes',\n"
            "       'symptoms': ['regex_pattern_1', 'regex_pattern_2'],\n"
            "       'category': 'format' # or 'references', 'latex', 'noise', 'tables'\n"
            "   }\n"
            "4. You MUST define:\n"
            "   def repair(text: str) -> Tuple[str, int]:\n"
            "       # returns (repaired_text, number_of_fixes_applied)\n"
            "5. You MUST define:\n"
            "   TEST_CASES = [\n"
            "       ('input_text_with_bug', 'expected_fixed_output'),\n"
            "   ]\n"
            "6. In Python re.sub(), ALWAYS use r'\\g<1>' or r'\\1' for capture group backreferences, NEVER '$1'.\n"
            "7. The code must be pure functional, deterministic, and safe (no os, sys, subprocess, eval, or file I/O).\n"
        )

        id_instruction = f"Preferred recipe_id: '{recipe_id_hint}'\n" if recipe_id_hint else ""
        user_prompt = (
            f"Archetype: {archetype}\n"
            f"{id_instruction}"
            f"Problem Description:\n{problem_description}\n\n"
            f"Defective Text Excerpt:\n```\n{sample_excerpt[:1500]}\n```\n\n"
            f"Generate the complete Python recipe module adhering strictly to all system constraints."
        )
        return system_prompt, user_prompt

    # --------------------------------------------------------------------------
    # 6. Recipe Refinement / Self-Healing Retry
    # --------------------------------------------------------------------------
    @staticmethod
    def get_recipe_refinement_prompt(
        error_detail: str,
        is_ast_error: bool = False
    ) -> str:
        """Constructs an iterative retry prompt feeding back execution/AST errors to Ollama."""
        if is_ast_error:
            return (
                f"Your previously generated Python code violated AST constraints:\n{error_detail}\n\n"
                f"Please fix the code strictly adhering to all constraints and re-generate inside ```python ... ```."
            )
        return (
            f"Your previously generated Python code failed its self-contained unit tests:\n{error_detail}\n\n"
            f"Remember:\n"
            f"- In Python re.sub(), use r'\\g<1>' or r'\\1' for group substitution, NEVER '$1'.\n"
            f"- Make sure `repair` actually transforms the defective input string to the exact expected output.\n"
            f"Please fix the implementation of `repair` or `TEST_CASES` and return the complete corrected module inside ```python ... ```."
        )

    # --------------------------------------------------------------------------
    # 7. Two-Column Academic Paper Reading Order
    # --------------------------------------------------------------------------
    @staticmethod
    def get_two_column_unwrapper(raw_blocks: str) -> Tuple[str, str]:
        """Returns (system_prompt, user_prompt) for reconstructing two-column reading flow."""
        user = PROMPT_TWO_COLUMN_UNWRAPPER_TEMPLATE.format(raw_blocks=raw_blocks[:3000])
        return SYSTEM_TWO_COLUMN_UNWRAPPER, user

    # --------------------------------------------------------------------------
    # 8. Bibliographic Citation Parser
    # --------------------------------------------------------------------------
    @staticmethod
    def get_reference_parser(raw_references: str) -> Tuple[str, str]:
        """Returns (system_prompt, user_prompt) for converting reference strings to BibTeX."""
        user = PROMPT_REFERENCE_PARSER_TEMPLATE.format(raw_references=raw_references[:3000])
        return SYSTEM_REFERENCE_PARSER, user

    # --------------------------------------------------------------------------
    # 9. OCR Character Proofreading
    # --------------------------------------------------------------------------
    @staticmethod
    def get_ocr_proofreading(markdown_text: str, max_chars: int = 4000) -> Tuple[str, str]:
        """Returns (system_prompt, user_prompt) for detecting clear OCR typographical defects."""
        system_prompt = (
            "You are an expert academic proofreader. Analyze the following textbook Markdown text.\n"
            "If you detect clear OCR character errors (e.g., '2s1' -> '281', 'tezt' -> 'text'), "
            "broken formula syntax, or garbled words, return your proposed corrections in valid JSON format.\n"
            "Format:\n"
            "{\n"
            '  "proposals": [\n'
            '    {\n'
            '      "id": "rev-1",\n'
            '      "original": "exact flawed string from text",\n'
            '      "proposed": "corrected clean string",\n'
            '      "reason": "brief reason for fix",\n'
            '      "category": "ocr_typo",\n'
            '      "confidence": 0.97\n'
            "    }\n"
            "  ]\n"
            "}\n"
            "Rules:\n"
            "- Set confidence = 1.0 only for unambiguous character substitutions (e.g. 0->O, l->1).\n"
            "- Set confidence >= 0.95 for clear OCR errors with no plausible alternative meaning.\n"
            "- Set confidence < 0.90 for ambiguous or context-dependent corrections.\n"
            "- If KaTeX currency symbols are unescaped (e.g. $25), propose escaping to \\$25.\n"
            "If no issues exist, return: {\"proposals\": []}\n"
            "Respond ONLY with the JSON object."
        )
        user_prompt = f"Markdown text to analyze:\n```markdown\n{markdown_text[:max_chars]}\n```"
        return system_prompt, user_prompt

    # --------------------------------------------------------------------------
    # 10. Multi-Modal Vision Layout Audit
    # --------------------------------------------------------------------------
    @staticmethod
    def get_multimodal_layout_audit(element_type: str, markdown_snippet: str) -> str:
        """Returns user prompt for visual comparison between crop image and extracted Markdown."""
        return (
            f"You are an expert textbook layout auditor. Compare the attached original textbook {element_type} image "
            f"with the following extracted Markdown representation:\n\n"
            f"```markdown\n{markdown_snippet[:1500]}\n```\n\n"
            f"Audit criteria:\n"
            f"1. Are all key headers/nodes present without omissions?\n"
            f"2. Is the structure faithful to the original image?\n"
            f"Respond ONLY in valid JSON format:\n"
            f'{{"passed": true, "defect": null, "confidence": 0.95}}\n'
            f'If flawed, return:\n'
            f'{{"passed": false, "defect": "brief description of defect", "confidence": 0.95}}'
        )

    # --------------------------------------------------------------------------
    # 11. Complex Academic Table Reconstruction
    # --------------------------------------------------------------------------
    @staticmethod
    def get_table_reconstruction(table_text: str, caption: str = "") -> str:
        """Returns prompt for reconstructing complex unbordered tabular text into Markdown table."""
        return (
            "You are an expert data formatting AI. The following raw text represents a complex academic table.\n"
            f"Table Title: {caption}\n\n"
            "Raw Table Content:\n"
            f"```\n{table_text[:3000]}\n```\n\n"
            "Instructions:\n"
            "1. Output ONLY a clean, valid Markdown table with proper header row and alignment delimiters (| :--- | :---: |).\n"
            "2. Preserve all numbers, decimal places, minus signs, and statistical symbols (e.g., *, **, p, M, SD, F).\n"
            "3. If table footnotes or notes are present at the bottom, format them inside <tfoot><tr class=\"table-notes\"><td colspan=\"N\">...</td></tr></tfoot>.\n"
            "4. Do NOT include conversational preamble, explanations, or enclosing markdown tags. Output ONLY the table."
        )

    # --------------------------------------------------------------------------
    # 12. Book Special Block Profiling
    # --------------------------------------------------------------------------
    @staticmethod
    def get_profile_special_blocks(sample_text: str) -> str:
        """Returns prompt for determining concept maps, margin glossaries, and learning objectives."""
        return (
            "Analyze this sample textbook excerpt and return a JSON object with: "
            "has_concept_map (boolean), has_margin_glossary (boolean), lo_pattern (regex string).\n"
            f"Text:\n{sample_text[:2000]}"
        )
