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
    const badge = document.getElementById("chapter-count-badge");
    if (badge) badge.textContent = `${state.chapters.length} 章`;
    listEl.innerHTML = state.chapters.map((ch) => `
      <li class="chapter-item ${ch.id === state.selectedChapterId ? "active" : ""}" data-id="${ch.id}">
        <span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:180px;">${ch.title}</span>
        <span class="badge-score">${ch.audit_score || 100}分</span>
      </li>
    `).join("");
    document.querySelectorAll(".chapter-item").forEach((el) => {
      el.addEventListener("click", () => selectChapter(el.dataset.id));
    });
    const filterInput = document.getElementById("chapter-filter-input");
    if (filterInput && filterInput.value) filterChapters(filterInput.value);
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
    if (txt) {
      txt.value = state.currentMarkdown;
      updateEditorStats();
    }
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
 * Updates character count in editor toolbar.
 * @returns {void}
 */
function updateEditorStats() {
  const txt = document.getElementById("markdown-textarea");
  const el = document.getElementById("editor-char-count");
  if (txt && el) el.textContent = `${(txt.value || "").length.toLocaleString()} 字`;
}

/**
 * Filters the chapter navigation list in real-time.
 * @param {string} q - Keyword search query.
 * @returns {void}
 */
function filterChapters(q) {
  const kw = (q || "").toLowerCase().trim();
  let count = 0;
  document.querySelectorAll(".chapter-item").forEach((el) => {
    const match = !kw || el.textContent.toLowerCase().includes(kw);
    el.style.display = match ? "flex" : "none";
    if (match) count++;
  });
  const b = document.getElementById("chapter-count-badge");
  if (b) b.textContent = `${count} 章`;
}

/**
 * Toggles the keyboard shortcuts guide dialog.
 * @param {boolean} [force] - Optional explicit state.
 * @returns {void}
 */
function toggleShortcutsModal(force) {
  const m = document.getElementById("shortcuts-modal");
  if (m) m.classList.toggle("active", typeof force === "boolean" ? force : !m.classList.contains("active"));
}

/**
 * Navigates to adjacent chapter in current book.
 * @param {number} delta - Chapter offset (-1 or 1).
 * @returns {void}
 */
function navigateChapter(delta) {
  const idx = state.chapters.findIndex((c) => c.id === state.selectedChapterId);
  if (idx !== -1 && state.chapters[idx + delta]) selectChapter(state.chapters[idx + delta].id);
}

/**
 * Renders Markdown into EPUB-like HTML preview with page anchors and tables.
 * @param {string} md - Markdown source.
 * @returns {void}
 */
function renderPreview(md) {
  const c = document.getElementById("preview-viewport");
  if (!c) return;
  c.innerHTML = typeof parseMarkdownToHtml === "function" ? parseMarkdownToHtml(md) : md;
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

  document.getElementById("chapter-filter-input")?.addEventListener("input", (e) => filterChapters(e.target.value));
  document.getElementById("btn-copy-markdown")?.addEventListener("click", () => {
    const txt = document.getElementById("markdown-textarea");
    const val = txt ? txt.value : state.currentMarkdown;
    if (!val) { showToast("無內容可複製", "info"); return; }
    navigator.clipboard.writeText(val).then(() => showToast("📋 已複製 Markdown 到剪貼簿！", "success"));
  });
  document.getElementById("btn-shortcuts-help")?.addEventListener("click", () => toggleShortcutsModal(true));
  document.getElementById("btn-shortcuts-close")?.addEventListener("click", () => toggleShortcutsModal(false));
  document.getElementById("btn-shortcuts-ok")?.addEventListener("click", () => toggleShortcutsModal(false));

  const mdTextarea = document.getElementById("markdown-textarea");
  mdTextarea?.addEventListener("input", () => {
    state.currentMarkdown = mdTextarea.value;
    updateEditorStats();
  });
  mdTextarea?.addEventListener("keydown", (e) => {
    if (e.key === "Tab") {
      e.preventDefault();
      const s = mdTextarea.selectionStart;
      const end = mdTextarea.selectionEnd;
      mdTextarea.value = mdTextarea.value.substring(0, s) + "  " + mdTextarea.value.substring(end);
      mdTextarea.selectionStart = mdTextarea.selectionEnd = s + 2;
      updateEditorStats();
    }
  });

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
    if (e.key === "Escape") {
      document.getElementById("correction-modal")?.classList.remove("active");
      document.getElementById("shortcuts-modal")?.classList.remove("active");
      return;
    }
    if (!isEditing) {
      if (e.key === "?") toggleShortcutsModal();
      else if (e.key === "[") navigateChapter(-1);
      else if (e.key === "]") navigateChapter(1);
      else if (e.key === "1") setLayoutMode("pdf-only");
      else if (e.key === "2") setLayoutMode("split");
      else if (e.key === "3") setLayoutMode("editor-only");
    }
  });

  if (window.innerWidth < 960) document.getElementById("sidebar")?.classList.add("collapsed");
  loadDashboard();
  loadBooks();
}

window.addEventListener("DOMContentLoaded", init);
