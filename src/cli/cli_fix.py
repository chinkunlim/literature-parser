"""
CLI Fix Playbook & Recipe Management
====================================
Provides command-line interface for the Fix Playbook:
- List all available repair recipes
- Apply a recipe to a specific file
- Inspect recipe details
- Review staged AI-synthesized recipes
- Sandboxed test runs for staged recipes
- Promote staged recipe to official playbook
- Reject and remove staged recipe
- Synthesize new Python repair recipes using Ollama
"""

import sys
from pathlib import Path

from src.utils.logger import get_diagnostic_logger

logger = get_diagnostic_logger("CommandCenter")


def cmd_fix(args):
    """
    Fix Playbook Command Center.
    Enables viewing and executing specialized document repair recipes.
    """
    from doc_processor.fixes.playbook import FixPlaybook
    from doc_processor.verification.format_auditor import FormatAuditor

    action = getattr(args, "fix_action", None) or "list"

    if action == "list":
        recipes = FixPlaybook.list_recipes()
        print("\n" + "=" * 70)
        print("📖 [FIX PLAYBOOK] 專屬修復手冊配方庫清單")
        print("=" * 70)
        print(f"{'配方 ID (recipe_id)':34s} {'類別':10s} {'配方名稱'}")
        print("-" * 70)
        for r in recipes:
            print(f"{r.recipe_id:34s} {r.category:10s} {r.name}")
            print(f"  ↳ 說明: {r.description}")
            print(f"  ↳ 症狀: {', '.join(r.symptoms[:2])}")
        print("=" * 70)
        print("💡 執行指令範例: uv run python run.py fix apply <recipe_id> <target_file>\n")
        return

    elif action == "apply":
        recipe_id = getattr(args, "recipe_id", None)
        target = Path(args.target) if getattr(args, "target", None) else None
        if not recipe_id or not target:
            print("🛑 錯誤：請提供配方 ID 與目標檔案路徑。")
            print("  範例: uv run python run.py fix apply clean_orphan_page_numbers data/output/literature/paper/paper.md")
            sys.exit(1)

        print(f"\n🔧 [FIX PLAYBOOK] 正在執行配方 '{recipe_id}' ➔ 目標: {target.name}...")
        recipe = FixPlaybook.get_recipe(recipe_id)
        if not recipe:
            print(f"🛑 錯誤：找不到配方 '{recipe_id}'。請執行 'python run.py fix list' 查看可用配方。")
            sys.exit(1)

        count, success, msg = FixPlaybook.apply_recipe_to_file(recipe_id, target, backup=True)
        if success:
            print(f"✅ {msg}")
            # Re-audit
            auditor = FormatAuditor(is_literature=True)
            report = auditor.audit_file(target)
            status_badge = "✅ [PASS]" if report.passed else "🛑 [FAILED]"
            print(f"📊 修復後最新品質得分: {report.score_percent:.1f}% ({status_badge}) | 錯誤: {report.error_count}, 警告: {report.warning_count}\n")
        else:
            print(f"🛑 修復失敗: {msg}\n")
            sys.exit(1)

    elif action == "info":
        recipe_id = getattr(args, "recipe_id", None)
        recipe = FixPlaybook.get_recipe(recipe_id)
        if not recipe:
            print(f"🛑 錯誤：找不到配方 '{recipe_id}'。")
            sys.exit(1)
        print("\n" + "=" * 65)
        print(f"📖 配方詳情: {recipe.name} ({recipe.recipe_id})")
        print("=" * 65)
        print(f"• 類別 (Category)   : {recipe.category}")
        print(f"• 領域 (Archetype)  : {recipe.archetype}")
        print(f"• 功能說明          : {recipe.description}")
        print(f"• 觸發症狀正則      : {', '.join(recipe.symptoms)}")
        print(f"• 執行指令範例      : uv run python run.py fix apply {recipe.recipe_id} <target_file>")
        print("=" * 65 + "\n")

    elif action == "review":
        staged = FixPlaybook.list_staged_recipes()
        print("\n" + "=" * 70)
        print("🧪 [FIX PLAYBOOK - STAGED] 待審核 AI 自動生成修復配方")
        print("=" * 70)
        if not staged:
            print("目前沒有任何待審核的修復配方（暫存區為空）。")
            print("若要由 Ollama 自動生成新配方，請執行: uv run python run.py fix synthesize <file> '<issue>'")
        else:
            print(f"{'配方 ID (recipe_id)':34s} {'生成時間':20s} {'配方名稱'}")
            print("-" * 70)
            for item in staged:
                meta = item.get("metadata", {})
                r_id = item.get("recipe_id", "unknown")
                created = item.get("created_at", "")
                name = meta.get("name", r_id)
                print(f"{r_id:34s} {created:20s} {name}")
                print(f"  ↳ 描述: {meta.get('description', '')}")
                print(f"  ↳ 症狀: {', '.join(meta.get('symptoms', [])[:2])}")
                print(f"  ↳ 單元測試通過數: {meta.get('test_cases_run', 0)} 例")
            print("-" * 70)
            print("💡 審核工作流指令:")
            print("  • 測試試跑: uv run python run.py fix test <recipe_id>")
            print("  • 批准整合: uv run python run.py fix promote <recipe_id>")
            print("  • 駁回刪除: uv run python run.py fix reject <recipe_id>")
        print("=" * 70 + "\n")

    elif action == "test":
        recipe_id = getattr(args, "recipe_id", None)
        if not recipe_id:
            print("🛑 錯誤：請提供待審核配方 ID。")
            sys.exit(1)
        print(f"\n🧪 [FIX PLAYBOOK] 正在沙盒中測試待審核配方 '{recipe_id}'...")
        res = FixPlaybook.test_staged_recipe(recipe_id)
        if res["success"]:
            details = res.get("details", {})
            print(f"✅ 沙盒測試通過！共執行 {details.get('test_cases_run', 0)} 個測試案例。")
            for c in details.get("cases", []):
                print(f"  • Case #{c['case']}: 套用 {c['fixes']} 處修復 (耗時 {c['elapsed_ms']} ms)")
            print(f"\n💡 若確認無誤，可執行: uv run python run.py fix promote {recipe_id}\n")
        else:
            print(f"🛑 測試失敗: {res.get('error') or res.get('details', {}).get('error')}\n")
            sys.exit(1)

    elif action == "promote":
        recipe_id = getattr(args, "recipe_id", None)
        if not recipe_id:
            print("🛑 錯誤：請提供待審核配方 ID。")
            sys.exit(1)
        print(f"\n🚀 [FIX PLAYBOOK] 正在批准並升級配方 '{recipe_id}' 至正式手冊...")
        ok, msg = FixPlaybook.promote_staged_recipe(recipe_id)
        if ok:
            print(f"✅ {msg}")
            print(f"🎉 配方已正式加入全域修復庫，可直接使用: uv run python run.py fix apply {recipe_id} <target_file>\n")
        else:
            print(f"🛑 升級失敗: {msg}\n")
            sys.exit(1)

    elif action == "reject":
        recipe_id = getattr(args, "recipe_id", None)
        if not recipe_id:
            print("🛑 錯誤：請提供待審核配方 ID。")
            sys.exit(1)
        print(f"\n🗑️ [FIX PLAYBOOK] 正在駁回並刪除暫存配方 '{recipe_id}'...")
        ok, msg = FixPlaybook.reject_staged_recipe(recipe_id)
        if ok:
            print(f"✅ {msg}\n")
        else:
            print(f"🛑 刪除失敗: {msg}\n")
            sys.exit(1)

    elif action == "synthesize":
        from doc_processor.fixes.synthesizer import OllamaRecipeSynthesizer
        target = Path(args.target) if getattr(args, "target", None) else None
        issue = getattr(args, "issue", "")
        id_hint = getattr(args, "id_hint", None)

        if not target or not target.exists():
            print(f"🛑 錯誤：找不到指定之目標檔案 '{target}'。")
            sys.exit(1)
        if not issue:
            print("🛑 錯誤：請提供欲解決之問題描述。")
            sys.exit(1)

        print("\n🤖 [OLLAMA SYNTHESIZER] 正在分析文檔瑕疵並由 Ollama 自動撰寫修復程式...")
        print(f"  • 目標檔案: {target.name}")
        print(f"  • 問題描述: {issue}")

        excerpt = target.read_text(encoding="utf-8", errors="ignore")[:2500]
        synth = OllamaRecipeSynthesizer()
        res = synth.synthesize_recipe(
            problem_description=issue,
            sample_excerpt=excerpt,
            recipe_id_hint=id_hint,
        )

        if res.success:
            print("\n🎉 [修復程式生成成功！]")
            print(f"  • 配方 ID  : {res.recipe_id}")
            print(f"  • 配方名稱: {res.recipe_name}")
            print(f"  • 暫存檔案: {res.file_path}")
            print(f"  • 沙盒測試: {res.test_results.get('test_cases_run', 0)} 例 100% 通過")
            print(f"  • 調用模型: {res.model_used}")
            print("\n💡 下一步工作流:")
            print("  1. 檢視暫存清單: uv run python run.py fix review")
            print(f"  2. 試跑測試用例: uv run python run.py fix test {res.recipe_id}")
            print(f"  3. 批准升級正式: uv run python run.py fix promote {res.recipe_id}")
            print(f"  4. 駁回並刪除  : uv run python run.py fix reject {res.recipe_id}\n")
        else:
            print(f"\n🛑 [生成失敗]: {res.error}")
            if res.code:
                print(f"產生的代碼片段:\n```python\n{res.code[:500]}\n```")
            sys.exit(1)
