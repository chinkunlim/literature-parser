# Web 前端與視覺化看板

純 HTML + CSS + JavaScript，不需要外部建置工具。檔案開頭都要有用途說明註解（`agentctl check` 會檢查）。

## 1. 視覺化儀表板 (Dashboard)
系統提供現代暗色系轉換進度儀表板，支援以 CLI 一鍵生成並瀏覽：
```bash
uv run literature-parser dashboard
```
將自動彙整 `DATA_DIR/state/global_status.json` 並調用預設瀏覽器檢視。

## 2. 本機靜態伺服器預覽
（只綁 `127.0.0.1`，區網看不到；不需要安裝任何額外套件）：

```bash
uv run python -m http.server 8000 --bind 127.0.0.1 -d web
```

瀏覽器開啟：`http://127.0.0.1:8000/dashboard.html` 或 `http://127.0.0.1:8000/`（嚴禁使用 localhost）。
