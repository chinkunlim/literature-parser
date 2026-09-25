"""
Fix Playbook Knowledge Base & Recipe Execution Engine
=====================================================
Stores learned, specialized document repair recipes that are too specific or domain-dependent
to bake directly into the generic pipeline core.

Provides:
- Recipe registration and cataloging with symptoms, descriptions, and handlers
- On-demand recipe execution: `python run.py fix apply <recipe_id> <target_file>`
- Symptom detection & auto-recommendation in `FormatAuditor`
- Safe dry-run and atomic file modification
"""

import json
import logging
import re
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Callable

logger = logging.getLogger(__name__)


@dataclass
class FixRecipe:
    recipe_id: str                      # Unique identifier, e.g. "cup_narrow_sidebar_stitch"
    name: str                           # Human-readable title
    description: str                    # Detailed explanation of what issue it solves
    symptoms: List[str]                 # Regex patterns or string keywords that trigger this recipe
    archetype: str = "literature"       # "literature", "book", or "all"
    category: str = "format"            # "format", "latex", "references", "structure", "noise"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class FixPlaybook:
    """Registry and execution engine for specialized document repair recipes."""

    _recipes: Dict[str, Tuple[FixRecipe, Callable[[str], Tuple[str, int]]]] = {}

    @classmethod
    def register(cls, recipe: FixRecipe, handler: Callable[[str], Tuple[str, int]]) -> None:
        """Registers a new repair recipe and its transformation handler."""
        cls._recipes[recipe.recipe_id] = (recipe, handler)

    @classmethod
    def list_recipes(cls, archetype: Optional[str] = None) -> List[FixRecipe]:
        """Returns all registered recipes, optionally filtered by archetype."""
        recipes = []
        for r, _ in cls._recipes.values():
            if archetype is None or r.archetype in (archetype, "all"):
                recipes.append(r)
        return sorted(recipes, key=lambda x: x.recipe_id)

    @classmethod
    def get_recipe(cls, recipe_id: str) -> Optional[FixRecipe]:
        """Gets a recipe definition by ID."""
        if recipe_id in cls._recipes:
            return cls._recipes[recipe_id][0]
        return None

    @classmethod
    def match_symptoms(cls, text: str, archetype: str = "literature") -> List[Tuple[FixRecipe, List[str]]]:
        """
        Scans text for known symptom patterns and returns matched recipes with matched evidence.
        """
        matches = []
        for recipe, _ in cls._recipes.values():
            if archetype != "all" and recipe.archetype not in (archetype, "all"):
                continue
            matched_evidence = []
            for symptom_pat in recipe.symptoms:
                if re.search(symptom_pat, text, re.I):
                    matched_evidence.append(symptom_pat)
            if matched_evidence:
                matches.append((recipe, matched_evidence))
        return matches

    @classmethod
    def apply_recipe(cls, recipe_id: str, text: str) -> Tuple[str, int, bool]:
        """
        Executes a specific recipe on the given text.
        Returns: (repaired_text, fix_count, success)
        """
        if recipe_id not in cls._recipes:
            raise KeyError(f"Fix recipe '{recipe_id}' is not registered in the playbook.")

        recipe, handler = cls._recipes[recipe_id]
        try:
            repaired_text, count = handler(text)
            return repaired_text, count, True
        except Exception as e:
            logger.error("FixPlaybook: Error applying recipe '%s': %s", recipe_id, e)
            return text, 0, False

    @classmethod
    def apply_recipe_to_file(cls, recipe_id: str, file_path: Path, backup: bool = False) -> Tuple[int, bool, str]:
        """
        Applies a recipe directly to a file on disk.
        Returns: (fix_count, success, message)
        """
        path = Path(file_path)
        if not path.exists():
            return 0, False, f"File not found: {path}"

        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            repaired_text, count, success = cls.apply_recipe(recipe_id, content)
            if not success:
                return 0, False, f"Recipe '{recipe_id}' execution failed."

            if count > 0:
                if backup:
                    bak_path = path.with_suffix(path.suffix + ".bak")
                    bak_path.write_text(content, encoding="utf-8")
                path.write_text(repaired_text, encoding="utf-8")
                return count, True, f"Successfully applied '{recipe_id}' ({count} changes applied)."
            else:
                return 0, True, f"Recipe '{recipe_id}' executed cleanly, but no symptoms were present."
        except Exception as e:
            return 0, False, f"I/O Error: {e}"


# =============================================================================
# Built-in Specialised Repair Handlers
# =============================================================================

def _handle_clean_orphan_page_numbers(text: str) -> Tuple[str, int]:
    """Strips solitary lines that contain only 1-4 digit page numbers."""
    lines = text.splitlines()
    clean_lines = []
    count = 0
    for line in lines:
        s = line.strip()
        if re.match(r'^\d{1,4}$', s) and not s.startswith("0"):
            count += 1
            continue
        clean_lines.append(line)
    return "\n".join(clean_lines), count


def _handle_escape_currency_katex(text: str) -> Tuple[str, int]:
    """Escapes $ currency signs (e.g. $25 -> \\$25) to prevent KaTeX math delimiter collision."""
    new_text, count = re.subn(r'(?<!\\)\$(?=(\d+(?:,\d{3})*(?:\.\d+)?\b))', r'\\$', text)
    return new_text, count


def _handle_elsevier_glued_references(text: str) -> Tuple[str, int]:
    """Splits inline **References** glued to the end of acknowledgment or disclosure sentences."""
    def _repl(m):
        return f"{m.group(1)}\n\n## References\n\n{m.group(2)}"
    new_text, count = re.subn(r'([\.?!]\s+)\*\*References\*\*\s+([A-Z])', _repl, text)
    return new_text, count


def _handle_normalize_corrupted_stats(text: str) -> Tuple[str, int]:
    """Repairs Elsevier OCR corrupted statistical formulas like t ð 24 Þ -> $t(24)$."""
    count = 0
    new_text = text

    # 1. t ð 24 Þ = 2: 06 -> $t(24) = 2.06$
    def _r1(m):
        nonlocal count
        count += 1
        t_var = m.group(1).replace("*", "").strip()
        df = m.group(2).strip()
        val = m.group(3).replace(" ", "").replace(":", ".")
        return f"${t_var}({df}) = {val}$"
    new_text = re.sub(r'(\*?[tTF]\*?)\s*ð\s*(\d+)\s*Þ\s*=\s*(\d+[:\.]\s*\d+)', _r1, new_text)

    # 2. p o 0: 01 -> $p < 0.01$
    def _r2(m):
        nonlocal count
        count += 1
        raw_val = m.group(1).replace(" ", "")
        val = f"0.{raw_val}" if not raw_val.startswith("0.") else raw_val
        return f"$p < {val}$"
    new_text = re.sub(r'\*?[pP]\*?\s*o\s*0?[:\.]\s*(\d+)', _r2, new_text)

    # 3. M = 4: 46 -> $M = 4.46$
    def _r3(m):
        nonlocal count
        count += 1
        m_var = m.group(1).replace("*", "").strip()
        val = m.group(2).replace(" ", "").replace(":", ".")
        return f"${m_var} = {val}$"
    new_text = re.sub(r'(\*?[mM]\*?)\s*=\s*(\d+[:\.]\s*\d+)', _r3, new_text)

    # 4. s. d. =2.02 -> $SD = 2.02$
    def _r4(m):
        nonlocal count
        count += 1
        val = m.group(1).strip()
        return f"$SD = {val}$"
    new_text = re.sub(r'(?:\*?s\.\s*d\.\*?)\s*=\s*(\d+(?:\.\d+)?)', _r4, new_text)

    return new_text, count


def _handle_strip_nih_watermarks(text: str) -> Tuple[str, int]:
    """Strips NIH Public Access / Author Manuscript / Article In Press watermarks masquerading as headings."""
    pattern = r'(?m)^#+\s*(?:NIH\s+Public\s+Access|Author\s+Manuscript|HHS\s+Public\s+Access|ARTICLE\s+IN\s+PRESS|RESEARCH\s+ARTICLE)\s*\n+'
    new_text, count = re.subn(pattern, '', text, flags=re.I)
    return new_text, count


def _handle_unparenthesized_ref_years(text: str) -> Tuple[str, int]:
    """Formats references with unparenthesized author years ending in semicolons (e.g. Author N. 2012;)."""
    # Normalize 'Author A. 2018; Title...' into '- Author A. (2018). Title...'
    count = 0
    lines = text.splitlines()
    new_lines = []
    in_refs = False

    for line in lines:
        if re.match(r'^##\s+(?:References|Literature Cited|Bibliography)', line, re.I):
            in_refs = True
            new_lines.append(line)
            continue
        elif in_refs and line.startswith("## "):
            in_refs = False

        if in_refs:
            # Check for un-bulleted unparenthesized citation
            m = re.match(r'^([A-Z][a-zA-Z\s\.,\-]+?)\s+(\d{4});\s+(.*)', line)
            if m:
                count += 1
                authors, year, rest = m.groups()
                new_lines.append(f"- {authors.strip()} ({year}). {rest.strip()}")
                continue
        new_lines.append(line)

    return "\n".join(new_lines), count


def _handle_demote_recommendation_headings(text: str) -> Tuple[str, int]:
    """Demotes numbered clinical guideline sentences mistakenly formatted as ## headings to ordered list items."""
    count = 0
    def _repl(m):
        nonlocal count
        count += 1
        num = m.group(1)
        body = m.group(2)
        return f"{num}. {body}"

    # Match ## 1. Clinicians are encouraged to... (length >= 45)
    pattern = r'(?m)^##\s+(\d+)\.\s+([A-Z][^\n]{40,})'
    new_text = re.sub(pattern, _repl, text)
    return new_text, count


def _handle_cup_sidebar_cleaning(text: str) -> Tuple[str, int]:
    """Strips Cambridge University Press running header / rail artifacts (cambridge.org/bil)."""
    count = 0
    lines = text.splitlines()
    clean_lines = []
    for line in lines:
        s = line.strip()
        if s.startswith("cambridge.org/bil") or s.startswith("https://doi.org/10.1017"):
            count += 1
            continue
        clean_lines.append(line)
    return "\n".join(clean_lines), count


# =============================================================================
# Register Built-in Recipes into FixPlaybook
# =============================================================================

FixPlaybook.register(
    FixRecipe(
        recipe_id="clean_orphan_page_numbers",
        name="孤立頁碼數字清理",
        description="清除正文行間殘留的孤立純數字頁碼行（例如單獨成行之 '75' 或 '4'），避免破壞段落閱讀流。",
        symptoms=[r'(?m)^\d{1,4}$'],
        archetype="all",
        category="noise",
    ),
    _handle_clean_orphan_page_numbers
)

FixPlaybook.register(
    FixRecipe(
        recipe_id="escape_currency_katex",
        name="KaTeX 貨幣符號轉義",
        description="將金額數字前的貨幣符號（如 $25、$300）轉義為 \\$ 或 &#36;，防止 KaTeX 公式渲染引擎崩潰。",
        symptoms=[r'(?<!\\)\$(?:\d+(?:,\d{3})*(?:\.\d+)?)\b'],
        archetype="all",
        category="latex",
    ),
    _handle_escape_currency_katex
)

FixPlaybook.register(
    FixRecipe(
        recipe_id="elsevier_glued_references",
        name="致謝句末粘連參考文獻拆分",
        description="將粘連在致謝或基金資助句末之 '**References**' 獨立拆分為標準 Markdown 二級章節標題。",
        symptoms=[r'[\.?!]\s+\*\*References\*\*\s+[A-Z]'],
        archetype="literature",
        category="references",
    ),
    _handle_elsevier_glued_references
)

FixPlaybook.register(
    FixRecipe(
        recipe_id="normalize_corrupted_stats",
        name="Elsevier OCR 破損統計公式修復",
        description="修復 PDF OCR 過程中括號被損毀之統計公式（如 't ð 24 Þ' 轉為 '$t(24)$'、'p o 0: 01' 轉為 '$p < 0.01$'）。",
        symptoms=[
            r'(?:\*?[tTF]\*?)\s*ð\s*\d+\s*Þ',
            r'(?:\*?[pP]\*?)\s*o\s*0?[:\.]\s*\d+',
            r'(?:\*?[mM]\*?)\s*=\s*\d+[:\.]\s*\d+',
            r'(?:\*?s\.\s*d\.\*?)\s*=\s*\d+',
        ],
        archetype="literature",
        category="latex",
    ),
    _handle_normalize_corrupted_stats
)

FixPlaybook.register(
    FixRecipe(
        recipe_id="strip_nih_watermarks",
        name="NIH/HHS 作者手稿浮水印過濾",
        description="過濾 'NIH Public Access'、'Author Manuscript' 等文章類別與手稿浮水印標題行，保護真實論文標題。",
        symptoms=[r'(?m)^#+\s*(?:NIH\s+Public\s+Access|Author\s+Manuscript|ARTICLE\s+IN\s+PRESS)\b'],
        archetype="literature",
        category="structure",
    ),
    _handle_strip_nih_watermarks
)

FixPlaybook.register(
    FixRecipe(
        recipe_id="unparenthesized_ref_years",
        name="無括號年份與分號結尾參考文獻正規化",
        description="將 Annual Reviews 等期刊之無括號年份引用條目（如 'Author N. 2012; Title'）重構為標準 Markdown 清單。",
        symptoms=[r'(?m)^[A-Z][a-zA-Z\s\.,\-]+?\s+\d{4};\s+'],
        archetype="literature",
        category="references",
    ),
    _handle_unparenthesized_ref_years
)

FixPlaybook.register(
    FixRecipe(
        recipe_id="demote_recommendation_headings",
        name="指引長句建議條目降級為有序清單",
        description="將臨床實務指引中以 '1. Clinicians are encouraged...' 等長句建議誤升之二級標題降級為正常清單，防止目錄膨脹。",
        symptoms=[r'(?m)^##\s+\d+\.\s+[A-Z][^\n]{40,}'],
        archetype="literature",
        category="structure",
    ),
    _handle_demote_recommendation_headings
)

FixPlaybook.register(
    FixRecipe(
        recipe_id="cup_sidebar_cleaning",
        name="劍橋大學出版社 (CUP) 側欄與頁眉網址清理",
        description="過濾殘留於正文行間之劍橋期刊網址 ('cambridge.org/bil') 與首頁側欄 DOI 孤兒行。",
        symptoms=[r'(?m)^(?:cambridge\.org/bil|https://doi\.org/10\.1017)'],
        archetype="literature",
        category="noise",
    ),
    _handle_cup_sidebar_cleaning
)
