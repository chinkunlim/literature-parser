/**
 * @file Client-side controller for Literature Parser Web Studio.
 * Handles view routing, book and chapter navigation, live editing, and test generation.
 */

// Application State
const state = {
  currentView: "dashboard",
  books: [],
  selectedBookId: "",
  chapters: [],
  selectedChapterId: "",
  currentPdfPage: 1,
  totalPdfPages: 1,
  originalMarkdown: "",
  currentMarkdown: "",
};

/**
 * Shows temporary toast notification.
 * @param {string} msg - Message text.
 * @param {"info"|"success"|"error"} [type="info"] - Notification style.
 * @returns {void}
 */
function showToast(msg, type = "info") {
  const container = document.getElementById("toast-container");
  if (!container) return;
  const t = document.createElement("div");
  t.className = `toast toast-${type}`;
  t.textContent = msg;
  container.appendChild(t);
  setTimeout(() => {
    t.style.opacity = "0";
    setTimeout(() => t.remove(), 250);
  }, 3000);
}

/**
 * Switches the active main viewport view.
 * @param {string} view - View identifier.
 * @returns {void}
 */
function switchView(view) {
  state.currentView = view;
  document.querySelectorAll(".nav-item").forEach((el) => {
    el.classList.toggle("active", el.dataset.view === view);
  });
  document.querySelectorAll(".view-panel").forEach((el) => {
    el.classList.toggle("active", el.id === `view-${view}`);
  });
  const switcher = document.getElementById("layout-switcher");
  if (switcher) switcher.style.display = (view === "compare") ? "inline-flex" : "none";

  const titleMap = {
    dashboard: "📊 處理進度儀表板",
    compare: "🔍 PDF vs EPUB 雙欄對比與編輯",
    diffs: "🖼️ 頁對頁視覺圖像對照",
    corrections: "🛠️ 人工修正與反饋資料庫",
  };
  const titleEl = document.getElementById("current-view-title");
  if (titleEl) titleEl.textContent = titleMap[view] || "Literature Studio";

  if (view === "dashboard") loadDashboard();
  if (view === "diffs" && state.selectedBookId) loadVisualDiffs();
  if (view === "corrections") loadCorrections();
}

/**
 * Fetches and renders dashboard metrics and book progress cards.
 * @returns {Promise<void>}
 */
async function loadDashboard() {
  try {
    const res = await fetch("/api/dashboard");
    const data = await res.json();
    document.getElementById("stat-total-docs").textContent = data.total_docs || "0";
    document.getElementById("stat-completed-docs").textContent = data.completed_docs || "0";
    document.getElementById("stat-overall-pct").textContent = `${data.overall_pct || 0}%`;
    document.getElementById("stat-total-corrections").textContent = data.total_corrections || "0";

    const grid = document.getElementById("books-grid");
    if (!grid) return;
    if (!data.books?.length) {
      grid.innerHTML = '<p style="color:var(--text-secondary);text-align:center;padding:2rem;">尚無轉檔紀錄。</p>';
      return;
    }
    grid.innerHTML = data.books.map((b) => `
      <div class="book-card">
        <div class="book-card-header">
          <div>
            <div class="book-card-title">${b.title}</div>
            <div style="font-size:0.75rem;color:var(--text-secondary);margin-top:0.2rem;">
              類型: ${b.doc_type.toUpperCase()} | 更新: ${b.last_updated || "N/A"}
            </div>
          </div>
          <span class="badge-score">${b.status === "COMPLETE" ? "✅ 已全數完工" : "🔄 進行中"}</span>
        </div>
        <div class="progress-track">
          <div class="progress-bar ${b.status === "COMPLETE" ? "complete" : ""}" style="width: ${b.progress_pct || 0}%;"></div>
        </div>
        <div style="display:flex;justify-content:space-between;align-items:center;font-size:0.8rem;margin-top:0.6rem;">
          <span>章節進度: <strong>${b.verified || 0} / ${b.total_chapters || 0}</strong> (${b.progress_pct || 0}%)</span>
          <div style="display:flex;gap:0.4rem;">
            <button class="btn" onclick="quickJumpToBook('${b.id}')">🔍 開啟雙欄對照</button>
            ${b.has_epub ? `<a class="btn" href="/api/books/${b.id}/epub/file" target="_blank">⬇️ 下載 EPUB</a>` : ""}
          </div>
        </div>
      </div>
    `).join("");
    document.getElementById("api-status-text").textContent = "正常運作";
  } catch (err) {
    document.getElementById("api-status-text").textContent = "連線失敗";
  }
}

/**
 * Loads books to populate selector.
 * @returns {Promise<void>}
 */
async function loadBooks() {
  try {
    const res = await fetch("/api/books");
    const data = await res.json();
    state.books = data.books || [];
    const select = document.getElementById("book-select");
    if (!select) return;
    select.innerHTML = state.books.map((b) => `<option value="${b.id}">${b.title}</option>`).join("");
    if (state.books.length > 0 && !state.selectedBookId) selectBook(state.books[0].id);
  } catch (err) {
    console.error("loadBooks error:", err);
  }
}

/**
 * Selects active book and fetches chapter items.
 * @param {string} bookId - Identifier of the book directory.
 * @returns {Promise<void>}
 */
async function selectBook(bookId) {
  state.selectedBookId = bookId;
  const select = document.getElementById("book-select");
  if (select) select.value = bookId;

  const dl = document.getElementById("btn-download-epub");
  const rb = document.getElementById("btn-rebuild-epub-top");
  if (dl) { dl.href = `/api/books/${bookId}/epub/file`; dl.style.display = "inline-flex"; }
  if (rb) rb.style.display = "inline-flex";

  try {
    const res = await fetch(`/api/books/${bookId}/chapters`);
    const data = await res.json();
    state.chapters = data.chapters || [];
    const listEl = document.getElementById("chapter-list");
    if (!listEl) return;
    listEl.innerHTML = state.chapters.map((ch) => `
      <li class="chapter-item ${ch.id === state.selectedChapterId ? "active" : ""}" data-id="${ch.id}">
        <span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:180px;">${ch.title}</span>
        <span class="badge-score">${ch.audit_score || 100}分</span>
      </li>
    `).join("");
    document.querySelectorAll(".chapter-item").forEach((el) => {
      el.addEventListener("click", () => selectChapter(el.dataset.id));
    });
    if (state.chapters.length > 0 && !state.selectedChapterId) selectChapter(state.chapters[0].id);
  } catch (err) {
    console.error("selectBook error:", err);
  }
}

/**
 * Jumps to a specific book from dashboard card.
 * @param {string} id - Book ID.
 * @returns {void}
 */
window.quickJumpToBook = function(id) {
  selectBook(id).then(() => switchView("compare"));
};

/**
 * Selects chapter, loads Markdown, and initializes PDF viewer.
 * @param {string} chId - Chapter folder ID.
 * @returns {Promise<void>}
 */
async function selectChapter(chId) {
  state.selectedChapterId = chId;
  document.querySelectorAll(".chapter-item").forEach((el) => {
    el.classList.toggle("active", el.dataset.id === chId);
  });
  const bc = document.getElementById("active-breadcrumb");
  if (bc) bc.textContent = `▸ ${state.selectedBookId} ▸ ${chId}`;

  try {
    const res = await fetch(`/api/books/${state.selectedBookId}/chapters/${chId}/markdown`);
    const data = await res.json();
    state.originalMarkdown = data.markdown || "";
    state.currentMarkdown = state.originalMarkdown;
    const txt = document.getElementById("markdown-textarea");
    if (txt) txt.value = state.currentMarkdown;
    renderPreview(state.currentMarkdown);
    renderAuditInspector(data.audit_report);
  } catch (err) {
    renderPreview("# 載入失敗\n無法讀取此章節 Markdown。");
    renderAuditInspector(null);
  }

  try {
    const res = await fetch(`/api/books/${state.selectedBookId}/chapters/${chId}/pdf/meta`);
    const meta = await res.json();
    state.totalPdfPages = meta.total_pages || 1;
    if (meta.has_pdf && state.totalPdfPages > 0) {
      buildPdfScrollFeed(state.selectedBookId, chId, state.totalPdfPages);
    }
  } catch (err) {
    console.error("PDF meta error:", err);
  }
}

/**
 * Renders Markdown into EPUB-like HTML preview with page anchors.
 * @param {string} md - Markdown source.
 * @returns {void}
 */
function renderPreview(md) {
  const c = document.getElementById("preview-viewport");
  if (!c) return;
  const html = md
    .replace(/^### (.*$)/gim, '<h3 style="font-size:1.15rem;margin:1.2rem 0 0.5rem;color:#111;">$1</h3>')
    .replace(/^## (.*$)/gim, '<h2 style="font-size:1.35rem;margin:1.4rem 0 0.6rem;color:#111;border-bottom:1px solid #eee;">$1</h2>')
    .replace(/^# (.*$)/gim, '<h1 style="font-size:1.6rem;margin:1.6rem 0 0.8rem;color:#000;">$1</h1>')
    .replace(/\*\*(.*?)\*\*/gim, "<strong>$1</strong>")
    .replace(/\*(.*?)\*/gim, "<em>$1</em>")
    .replace(/!\[(.*?)\]\((.*?)\)/gim, '<div style="text-align:center;margin:1.2rem 0;"><img src="$2" alt="$1" style="max-width:90%;"><p style="font-size:0.8rem;color:#666;">$1</p></div>')
    .replace(/<!--\s*page\s*0*(\d+)\s*-->/gim, '<div id="epub-page-$1" class="epub-page-divider" data-page="$1"><span class="epub-page-pill">Page $1</span></div>')
    .replace(/\n\n/gim, "</p><p style=\"margin-bottom:1rem;text-indent:1.5rem;\">");
  c.innerHTML = `<div style="max-width:760px;margin:0 auto;"><p style="margin-bottom:1rem;text-indent:1.5rem;">${html}</p></div>`;
}

/**
 * Opens correction modal with calculated diff snippet.
 * @returns {void}
 */
function openCorrectionModal() {
  const txt = document.getElementById("markdown-textarea");
  if (txt) state.currentMarkdown = txt.value;
  const diffEl = document.getElementById("modal-diff-preview");
  if (state.originalMarkdown === state.currentMarkdown) {
    diffEl.textContent = "內容未變動（直接記錄備註或建立標籤）。";
  } else {
    diffEl.textContent = `原長度: ${state.originalMarkdown.length} 字 ➔ 新長度: ${state.currentMarkdown.length} 字\n章節: ${state.selectedChapterId}`;
  }
  document.getElementById("correction-modal")?.classList.add("active");
}

/**
 * Submits chapter changes and records feedback to API.
 * @returns {Promise<void>}
 */
async function submitCorrection() {
  const issue = document.getElementById("modal-issue-type").value;
  const notes = document.getElementById("modal-user-notes").value;
  const rebuild = document.getElementById("modal-rebuild-epub").checked;
  try {
    showToast("儲存中並觸發 EPUB 重建...", "info");
    const res = await fetch(`/api/books/${state.selectedBookId}/chapters/${state.selectedChapterId}/markdown`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ markdown: state.currentMarkdown, issue_type: issue, user_notes: notes, rebuild_epub: rebuild }),
    });
    const data = await res.json();
    document.getElementById("correction-modal")?.classList.remove("active");
    state.originalMarkdown = state.currentMarkdown;
    renderPreview(state.currentMarkdown);
    showToast(`儲存成功！(ID: ${data.correction_id.slice(0, 8)})`, "success");
    loadDashboard();
  } catch (err) {
    showToast(`儲存失敗: ${err.message}`, "error");
  }
}

/**
 * Fetches and displays visual diff sample gallery.
 * @returns {Promise<void>}
 */
async function loadVisualDiffs() {
  const g = document.getElementById("diff-gallery");
  if (!g) return;
  try {
    const res = await fetch(`/api/books/${state.selectedBookId}/visual-diffs`);
    const data = await res.json();
    if (!data.samples?.length) {
      g.innerHTML = '<p style="color:var(--text-secondary);padding:2rem;">此書籍尚無視覺比對樣本。</p>';
      return;
    }
    g.innerHTML = data.samples.map((s) => `
      <div class="diff-card">
        <div class="diff-card-header">${s.title}</div>
        <div class="diff-image-wrapper"><img src="${s.url}" alt="${s.title}" loading="lazy"></div>
      </div>
    `).join("");
  } catch (err) {
    console.error("loadVisualDiffs error:", err);
  }
}

/**
 * Fetches and renders correction feedback history.
 * @returns {Promise<void>}
 */
async function loadCorrections() {
  const tbody = document.getElementById("corrections-tbody");
  if (!tbody) return;
  try {
    const res = await fetch("/api/corrections");
    const data = await res.json();
    if (!data.corrections?.length) {
      tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:var(--text-secondary);padding:2rem;">尚無修正記錄。</td></tr>';
      return;
    }
    tbody.innerHTML = data.corrections.map((r) => `
      <tr>
        <td style="white-space:nowrap;font-size:0.75rem;">${r.created_at.split("T")[0]}</td>
        <td><strong>${r.book_id}</strong><br><span style="font-size:0.75rem;color:var(--text-secondary);">${r.chapter_id}</span></td>
        <td><span class="diff-badge diff-badge-${r.issue_type}">${r.issue_type}</span></td>
        <td><pre style="max-height:80px;overflow-y:auto;font-size:0.75rem;color:#58a6ff;">${r.diff_snippet || "置換"}</pre></td>
        <td style="font-size:0.8rem;">${r.user_notes || "-"}</td>
        <td><button class="btn btn-danger" style="padding:0.2rem 0.5rem;font-size:0.72rem;" onclick="deleteCorrection('${r.id}')">刪除</button></td>
      </tr>
    `).join("");
  } catch (err) {
    console.error("loadCorrections error:", err);
  }
}

/**
 * Deletes a correction record by identifier.
 * @param {string} id - Record identifier.
 * @returns {Promise<void>}
 */
window.deleteCorrection = async function(id) {
  if (!confirm("確定刪除此記錄？")) return;
  try {
    await fetch(`/api/corrections/${id}`, { method: "DELETE" });
    showToast("已刪除記錄", "info");
    loadCorrections();
  } catch (err) {
    showToast(`刪除失敗: ${err.message}`, "error");
  }
};

/**
 * Triggers automated unit regression test suite generation.
 * @returns {Promise<void>}
 */
async function generateRegressionTests() {
  try {
    showToast("正在分析問題並生成回歸測試...", "info");
    const res = await fetch("/api/corrections/generate-tests", { method: "POST" });
    const data = await res.json();
    showToast(`成功生成 ${data.total_records} 個回歸測試！`, "success");
  } catch (err) {
    showToast(`生成失敗: ${err.message}`, "error");
  }
}

/**
 * Initializes listeners and default views.
 * @returns {void}
 */
function init() {
  initSidebarState();
  document.getElementById("btn-sidebar-toggle")?.addEventListener("click", () => toggleSidebar());
  document.querySelectorAll(".nav-item").forEach((el) => {
    el.addEventListener("click", () => switchView(el.dataset.view));
  });

  // Layout Switcher
  document.getElementById("btn-layout-pdf")?.addEventListener("click", () => setLayoutMode("pdf-only"));
  document.getElementById("btn-layout-split")?.addEventListener("click", () => setLayoutMode("split"));
  document.getElementById("btn-layout-editor")?.addEventListener("click", () => setLayoutMode("editor-only"));

  document.getElementById("btn-pdf-fit-width")?.addEventListener("click", resetPdfFeedZoom);
  document.getElementById("btn-pdf-reset-view")?.addEventListener("click", resetPdfFeedZoom);
  document.getElementById("btn-pdf-zoom-in")?.addEventListener("click", () => zoomPdfFeed(1.15));
  document.getElementById("btn-pdf-zoom-out")?.addEventListener("click", () => zoomPdfFeed(0.85));

  document.getElementById("book-select")?.addEventListener("change", (e) => selectBook(e.target.value));
  document.getElementById("btn-refresh")?.addEventListener("click", () => {
    loadDashboard();
    if (state.selectedBookId) selectBook(state.selectedBookId);
    showToast("已重新整理", "info");
  });

  document.getElementById("tab-editor-preview")?.addEventListener("click", () => {
    document.getElementById("tab-editor-preview").classList.add("active");
    document.getElementById("tab-editor-raw").classList.remove("active");
    document.getElementById("preview-viewport").classList.add("active");
    document.getElementById("markdown-textarea").style.display = "none";
    const txt = document.getElementById("markdown-textarea");
    if (txt) renderPreview(txt.value);
  });
  document.getElementById("tab-editor-raw")?.addEventListener("click", () => {
    document.getElementById("tab-editor-raw").classList.add("active");
    document.getElementById("tab-editor-preview").classList.remove("active");
    document.getElementById("markdown-textarea").style.display = "block";
    document.getElementById("preview-viewport").classList.remove("active");
  });

  document.getElementById("btn-save-correction")?.addEventListener("click", openCorrectionModal);
  document.getElementById("btn-modal-close")?.addEventListener("click", () => document.getElementById("correction-modal")?.classList.remove("active"));
  document.getElementById("btn-modal-cancel")?.addEventListener("click", () => document.getElementById("correction-modal")?.classList.remove("active"));
  document.getElementById("btn-modal-confirm")?.addEventListener("click", submitCorrection);
  document.getElementById("btn-generate-tests")?.addEventListener("click", generateRegressionTests);

  // Defect Drawer Toggle Listeners
  document.getElementById("btn-toggle-defects")?.addEventListener("click", () => {
    const drawer = document.getElementById("audit-defect-drawer");
    if (drawer) {
      drawer.style.display = drawer.style.display === "none" ? "block" : "none";
    }
  });
  document.getElementById("btn-close-defects")?.addEventListener("click", () => {
    const drawer = document.getElementById("audit-defect-drawer");
    if (drawer) drawer.style.display = "none";
  });

  initSyncScrollController();
  initSplitResizer();

  // Keyboard Shortcuts
  window.addEventListener("keydown", (e) => {
    const isEditing = ["TEXTAREA", "INPUT"].includes(document.activeElement?.tagName);
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "s") {
      e.preventDefault();
      openCorrectionModal();
      return;
    }
    if ((e.metaKey || e.ctrlKey) && e.key === "0") {
      e.preventDefault();
      resetPdfFeedZoom();
      return;
    }
  });

  if (window.innerWidth < 960) document.getElementById("sidebar")?.classList.add("collapsed");
  loadDashboard();
  loadBooks();
}

window.addEventListener("DOMContentLoaded", init);
