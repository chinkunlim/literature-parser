# 大模型提示詞集中規範 (docs/PROMPT_TEMPLATES.md)

## 1. 架構中樞理念 (Architecture Philosophy)

本專案全面落實 **PromptRegistry 單一真理來源 (Single Source of Truth, SSOT)** 原則：
- **嚴禁硬編碼提示詞**：所有模組嚴禁在業務程式碼（如 parser、verifier、pipeline）中以行內拼接字串方式呼叫大模型。
- **強型別集中管理**：所有與本地 Ollama 互動之 Prompt 必須統一定義於 `src/literature_parser/services/guards/prompts.py` 中的 `PromptRegistry` 類別，具備靜態型別標註與入參約束。
- **排版不變量保護**：所有 Prompt 模板皆嚴格嵌入防重構與排版規範（KaTeX 貨幣符號 `\$` 轉義、Python 正則反向引用 `\g<1>`、APA 表格附註結構隔離 `<tfoot>`、雙欄帶狀流動不變量）。

---

## 2. PromptRegistry 核心提示詞矩陣 (Prompt Catalog)

| 提示詞方法名 | 呼叫時機 / 模組 | 任務目標與約束 |
| :--- | :--- | :--- |
| `get_latex_healer()` | `LaTeXHealer`, `FormulaParser` | 修復損毀或括號不平衡之數學公式，嚴格隔離非數學文本與轉義貨幣符號 |
| `get_manifest_validator()` | `InputGuard`, `Doctor` | 比對輸入檔案與 manifest.json，精準診斷缺失或命名歧異 |
| `get_semantic_auditor()` | `FormatAuditor` | 4 維度審計：標題真實性、LaTeX 完整性、表格附註隔離、跨頁散文流動性 |
| `get_ocr_proofreader()` | `ScannedPDFParser` | 檢查掃描版 OCR 錯字、破損字符，強制要求返回嚴格 JSON 格式建議清單 |
| `get_two_column_unwrapper()` | `TwoColumnFlowUnwrapper` | 解決左右雙欄文字交錯與穿插問題，依閱讀流重構成連續語意段落 |
| `get_reference_parser()` | `ReferenceParser` | 將非結構化論文參考文獻文字段落解析為標準 BibTeX 條目 |
| `get_semantic_header_formatter()` | `SemanticHeaderFormatter` | 期刊論文首頁元數據解析：主標題、副標題、作者群、研究機構、DOI 與摘要 |
| `get_table_healer()` | `TableSemanticHealer` | 複雜跨頁表格、合併儲存格與多層表頭之 HTML/Markdown 結構重建 |
| `get_code_synthesis_prompt()` | `OllamaRecipeSynthesizer` | 生成針對特定排版瑕疵的 Python 純函數修復腳本（AST 沙盒審查專用） |

---

## 3. 核心提示詞範例展示 (Exemplary Templates)

### 3.1 LaTeX 數學公式自我修復 (`get_latex_healer`)
```text
[SYSTEM]
You are a LaTeX typesetting expert. Fix broken or malformed math formulas accurately.
Rules:
- Return ONLY the repaired LaTeX code, enclosed in $$...$$ (display math) or $...$ (inline math).
- Do NOT output any conversational text, explanations, or backticks other than the LaTeX expression.
- Ensure all curly braces {...} and brackets [...] are properly balanced.
- Escape currency dollar signs (e.g. $100 -> \$100).

[USER TEMPLATE]
Surrounding Context:
"{context}"

Broken LaTeX Formula:
{broken_latex}

Repaired Formula:
```

### 3.2 雙欄學術閱讀流還原 (`get_two_column_unwrapper`)
```text
[SYSTEM]
You are an academic layout and reading order specialist.
Your job is to reconstruct mixed left-and-right column OCR text blocks into logical reading sequence.

[USER TEMPLATE]
The following text was extracted from a two-column academic paper. Some lines from Column 1 and Column 2 may be interleaved or split across the page fold:

```text
{raw_blocks}
```

Task: Reorder and reconstruct the text into continuous, logically flowing paragraphs.
Preserve all citations, math formulas, and technical terminology exactly as written.
```

### 3.3 學術期刊標題與元數據提取 (`get_semantic_header_formatter`)
```text
[SYSTEM]
You are an academic metadata extraction specialist. Extract title, authors, affiliations, 
journal metadata, and abstract from the first page of an academic journal article.
Format the output strictly as valid Markdown with structured YAML frontmatter or standard headers.
```
