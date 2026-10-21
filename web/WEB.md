# Web 前端

純 HTML + CSS + JavaScript，不需要建置工具。檔案開頭都要有用途說明註解（`agentctl check` 會檢查）。

本機預覽（只綁 `127.0.0.1`，區網看不到；不需要安裝任何東西）：

```bash
uv run python -m http.server 8000 --bind 127.0.0.1 -d web
```

然後打開 http://127.0.0.1:8000 （不要用 localhost）。
