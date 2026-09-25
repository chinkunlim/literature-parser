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
from typing import Any, Dict, List, Optional, Tuple, Callable

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

    STAGED_DIR: Path = Path(__file__).resolve().parent / "staged"
    PROMOTED_DIR: Path = Path(__file__).resolve().parent / "promoted"

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

    @classmethod
    def list_staged_recipes(cls) -> List[Dict[str, Any]]:
        """Returns all currently staged recipes waiting for review."""
        staged_dir = cls.STAGED_DIR
        if not staged_dir.exists():
            return []
        results = []
        for json_file in sorted(staged_dir.glob("*.json")):
            try:
                data = json.loads(json_file.read_text(encoding="utf-8"))
                py_file = staged_dir / f"{data['recipe_id']}.py"
                data["has_py"] = py_file.exists()
                results.append(data)
            except Exception as e:
                logger.warning("Error reading staged metadata %s: %s", json_file, e)
        return results

    @classmethod
    def get_staged_recipe_code(cls, recipe_id: str) -> Optional[str]:
        """Reads the source code of a staged recipe."""
        staged_dir = cls.STAGED_DIR
        py_file = staged_dir / f"{recipe_id}.py"
        if py_file.exists():
            return py_file.read_text(encoding="utf-8")
        return None

    @classmethod
    def test_staged_recipe(cls, recipe_id: str) -> Dict[str, Any]:
        """Runs the self-contained test cases of a staged recipe."""
        code = cls.get_staged_recipe_code(recipe_id)
        if not code:
            return {"success": False, "error": f"Staged recipe '{recipe_id}' not found."}
        from doc_processor.fixes.synthesizer import OllamaRecipeSynthesizer
        synth = OllamaRecipeSynthesizer()
        passed, info = synth._execute_sandbox_tests(code)
        return {"success": passed, "details": info}

    @classmethod
    def promote_staged_recipe(cls, recipe_id: str) -> Tuple[bool, str]:
        """
        Promotes a staged recipe into the official promoted/ directory and registers it.
        """
        staged_dir = cls.STAGED_DIR
        promoted_dir = cls.PROMOTED_DIR
        promoted_dir.mkdir(parents=True, exist_ok=True)

        py_file = staged_dir / f"{recipe_id}.py"
        json_file = staged_dir / f"{recipe_id}.json"

        if not py_file.exists():
            return False, f"Staged recipe script '{recipe_id}.py' not found."

        # Verify test cases pass before promoting
        test_res = cls.test_staged_recipe(recipe_id)
        if not test_res["success"]:
            err_detail = test_res.get("details", {}).get("error", "Unknown test failure")
            return False, f"Cannot promote recipe '{recipe_id}': sandbox tests failed ({err_detail})."

        target_py = promoted_dir / f"{recipe_id}.py"
        target_json = promoted_dir / f"{recipe_id}.json"

        target_py.write_text(py_file.read_text(encoding="utf-8"), encoding="utf-8")
        if json_file.exists():
            data = json.loads(json_file.read_text(encoding="utf-8"))
            data["status"] = "promoted"
            target_json.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
            json_file.unlink()
        py_file.unlink()

        # Register immediately into playbook
        cls._load_and_register_module(target_py)
        return True, f"Successfully promoted '{recipe_id}' to active playbook."

    @classmethod
    def reject_staged_recipe(cls, recipe_id: str) -> Tuple[bool, str]:
        """Rejects and deletes a staged recipe."""
        staged_dir = cls.STAGED_DIR
        py_file = staged_dir / f"{recipe_id}.py"
        json_file = staged_dir / f"{recipe_id}.json"

        deleted = False
        if py_file.exists():
            py_file.unlink()
            deleted = True
        if json_file.exists():
            json_file.unlink()
            deleted = True

        if deleted:
            return True, f"Rejected and removed staged recipe '{recipe_id}'."
        return False, f"Staged recipe '{recipe_id}' not found."

    @classmethod
    def _load_and_register_module(cls, py_path: Path) -> bool:
        """Dynamically loads a promoted recipe module and registers it into FixPlaybook."""
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location(py_path.stem, str(py_path))
            if not spec or not spec.loader:
                return False
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)

            meta = getattr(mod, "RECIPE_METADATA", None)
            repair_fn = getattr(mod, "repair", None)

            if isinstance(meta, dict) and callable(repair_fn):
                recipe = FixRecipe(
                    recipe_id=meta.get("recipe_id", py_path.stem),
                    name=meta.get("name", py_path.stem),
                    description=meta.get("description", ""),
                    symptoms=meta.get("symptoms", []),
                    archetype=meta.get("archetype", "literature"),
                    category=meta.get("category", "format"),
                )
                cls.register(recipe, repair_fn)
                return True
        except Exception as e:
            logger.error("Failed to load promoted recipe '%s': %s", py_path.name, e)
        return False

    @classmethod
    def load_all_promoted_recipes(cls) -> int:
        """Loads and registers all approved recipes from promoted/ directory."""
        promoted_dir = Path(__file__).resolve().parent / "promoted"
        if not promoted_dir.exists():
            return 0
        count = 0
        for py_file in promoted_dir.glob("*.py"):
            if py_file.name.startswith("__"):
                continue
            if cls._load_and_register_module(py_file):
                count += 1
        return count


from doc_processor.utils.shared_text import (
    clean_orphan_page_numbers_text,
    escape_currency_katex_text,
    separate_glued_references_text,
    normalize_corrupted_stats_text,
    strip_manuscript_watermarks_text,
    normalize_unparenthesized_ref_years_text,
)

# =============================================================================
# Built-in Specialised Repair Handlers
# =============================================================================

def _handle_clean_orphan_page_numbers(text: str) -> Tuple[str, int]:
    return clean_orphan_page_numbers_text(text)


def _handle_escape_currency_katex(text: str) -> Tuple[str, int]:
    return escape_currency_katex_text(text)


def _handle_elsevier_glued_references(text: str) -> Tuple[str, int]:
    return separate_glued_references_text(text)


def _handle_normalize_corrupted_stats(text: str) -> Tuple[str, int]:
    return normalize_corrupted_stats_text(text)


def _handle_strip_nih_watermarks(text: str) -> Tuple[str, int]:
    return strip_manuscript_watermarks_text(text)


def _handle_unparenthesized_ref_years(text: str) -> Tuple[str, int]:
    return normalize_unparenthesized_ref_years_text(text)



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

# Automatically register any user-promoted custom recipes
FixPlaybook.load_all_promoted_recipes()
