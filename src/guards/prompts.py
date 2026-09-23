"""
Deterministic Prompts for Local Ollama AI Tasks
================================================
Centralized repository of hardened, pre-defined system prompts and templates.
Runtime execution is 100% autonomous — Antigravity / AI Agent cannot intervene
once the Python pipeline is launched.
"""

# ==============================================================================
# 1. LaTeX Math Formula Self-Healing Prompt
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

# ==============================================================================
# 2. Input Manifest Schema Diagnostic Prompt
# ==============================================================================
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

# ==============================================================================
# 3. Academic Chapter Semantic & Continuity Auditor Prompt
# ==============================================================================
SYSTEM_SEMANTIC_AUDITOR = (
    "You are an expert academic editor and publication auditor. "
    "You evaluate extracted textbook and journal content with zero tolerance for OCR glitches or AI hallucinations."
)

PROMPT_SEMANTIC_AUDITOR_TEMPLATE = (
    "Review the following extracted publication section titled '{chapter_title}'.\n"
    "Audit these 4 critical dimensions:\n"
    "1. Heading Authenticity: Are all headings genuine author section titles (NO AI-hallucinated summary subheadings)?\n"
    "2. LaTeX & Symbols: Are all LaTeX formulas ($...$ or $$...$$) syntactically valid with NO unescaped currency ($3) or broken delimiters?\n"
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

# ==============================================================================
# 4. Structured OCR Proofreading & Error Proposal Prompt
# ==============================================================================
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

# ==============================================================================
# 5. Two-Column Academic Paper Reading Order Reconstructor
# ==============================================================================
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

# ==============================================================================
# 6. Structured Citation & Reference Parser
# ==============================================================================
SYSTEM_REFERENCE_PARSER = (
    "You are a bibliographic citation specialist. Convert raw reference strings into clean, structured BibTeX entries."
)

PROMPT_REFERENCE_PARSER_TEMPLATE = (
    "Raw References Section:\n```text\n{raw_references}\n```\n\n"
    "Task: Parse each citation into a standard BibTeX entry (@article, @book, @inproceedings). "
    "Include fields: author, title, journal/booktitle, year, volume, pages, doi (if present)."
)
