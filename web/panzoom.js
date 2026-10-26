/**
 * @file Continuous PDF Vertical Scroll Feed, Bidirectional EPUB Synchronized Scrolling, and Layout.
 * Supports lazy-loaded PDF page feed, Page N anchor matching, sync lock toggle, and resizable panes.
 */

// Global Sync & Scroll State
const syncState = {
  enabled: true,
  isProgrammatic: false,
  timer: null,
  zoomScale: 1.0,
};

/**
 * Builds continuous vertical scroll feed for all chapter PDF pages.
 * @param {string} bookId - Book folder name.
 * @param {string} chapterId - Chapter folder name.
 * @param {number} totalPages - Total page count in chapter PDF.
 * @returns {void}
 */
function buildPdfScrollFeed(bookId, chapterId, totalPages) {
  const feed = document.getElementById("pdf-scroll-feed");
  if (!feed) return;
  feed.innerHTML = "";

  if (totalPages <= 0) {
    feed.innerHTML = '<div style="color:var(--text-secondary);text-align:center;padding:2rem;">此章節無 PDF 檔案。</div>';
    return;
  }

  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        const img = entry.target.querySelector("img");
        if (img && img.dataset.src && !img.src) {
          img.src = img.dataset.src;
        }
      }
    });
  }, { root: feed, rootMargin: "350px 0px" });

  for (let i = 1; i <= totalPages; i++) {
    const card = document.createElement("div");
    card.id = `pdf-page-${i}`;
    card.className = "pdf-page-card";
    card.dataset.page = String(i);

    const pill = document.createElement("span");
    pill.className = "pdf-page-num-pill";
    pill.textContent = `Page ${i}`;

    const img = document.createElement("img");
    img.className = "pdf-scroll-img";
    img.alt = `Page ${i}`;
    img.dataset.src = `/api/books/${bookId}/chapters/${chapterId}/pdf/page/${i}`;

    card.appendChild(pill);
    card.appendChild(img);
    feed.appendChild(card);
    observer.observe(card);
  }

  // Preload first page immediately
  const firstImg = feed.querySelector("img");
  if (firstImg && firstImg.dataset.src) {
    firstImg.src = firstImg.dataset.src;
  }

  const indicator = document.getElementById("pdf-scroll-indicator");
  if (indicator) indicator.textContent = `第 1 / ${totalPages} 頁`;
}

/**
 * Adjusts page width zoom in continuous scroll feed.
 * @param {number} delta - Zoom multiplier step.
 * @returns {void}
 */
function zoomPdfFeed(delta) {
  syncState.zoomScale = Math.max(0.5, Math.min(2.5, syncState.zoomScale * delta));
  const feed = document.getElementById("pdf-scroll-feed");
  if (feed) {
    feed.style.setProperty("--pdf-page-width", `${Math.round(92 * syncState.zoomScale)}%`);
  }
}

/**
 * Resets PDF feed zoom to fit container width.
 * @returns {void}
 */
function resetPdfFeedZoom() {
  syncState.zoomScale = 1.0;
  const feed = document.getElementById("pdf-scroll-feed");
  if (feed) {
    feed.style.setProperty("--pdf-page-width", "92%");
  }
}

/**
 * Initializes bidirectional synchronized scrolling between PDF feed and EPUB preview.
 * @returns {void}
 */
function initSyncScrollController() {
  const pdfFeed = document.getElementById("pdf-scroll-feed");
  const epubPreview = document.getElementById("preview-viewport");
  const toggleBtn = document.getElementById("btn-toggle-sync");
  if (!pdfFeed || !epubPreview) return;

  toggleBtn?.addEventListener("click", () => {
    syncState.enabled = !syncState.enabled;
    toggleBtn.classList.toggle("active", syncState.enabled);
    toggleBtn.textContent = syncState.enabled ? "🔗 同步中" : "🔓 獨立滾動";
  });

  // PDF Feed Scroll ➔ Syncs to EPUB Preview
  pdfFeed.addEventListener("scroll", () => {
    if (!syncState.enabled || syncState.isProgrammatic) return;

    // Detect currently visible page
    const feedRect = pdfFeed.getBoundingClientRect();
    const midY = feedRect.top + feedRect.height / 3;
    const cards = pdfFeed.querySelectorAll(".pdf-page-card");
    let activePage = 1;

    for (const card of cards) {
      const cardRect = card.getBoundingClientRect();
      if (cardRect.top <= midY && cardRect.bottom >= midY) {
        activePage = parseInt(card.dataset.page, 10);
        break;
      }
    }

    const indicator = document.getElementById("pdf-scroll-indicator");
    if (indicator) indicator.textContent = `第 ${activePage} / ${cards.length || 1} 頁`;

    // Locate target anchor in EPUB preview
    const targetAnchor = epubPreview.querySelector(`#epub-page-${activePage}`);
    if (targetAnchor) {
      syncState.isProgrammatic = true;
      const targetTop = targetAnchor.offsetTop - epubPreview.offsetTop - 16;
      epubPreview.scrollTo({ top: Math.max(0, targetTop), behavior: "smooth" });
      clearTimeout(syncState.timer);
      syncState.timer = setTimeout(() => { syncState.isProgrammatic = false; }, 140);
    } else {
      const maxPdf = pdfFeed.scrollHeight - pdfFeed.clientHeight;
      const maxEpub = epubPreview.scrollHeight - epubPreview.clientHeight;
      if (maxPdf > 0 && maxEpub > 0) {
        syncState.isProgrammatic = true;
        const ratio = pdfFeed.scrollTop / maxPdf;
        epubPreview.scrollTo({ top: ratio * maxEpub, behavior: "smooth" });
        clearTimeout(syncState.timer);
        syncState.timer = setTimeout(() => { syncState.isProgrammatic = false; }, 140);
      }
    }
  }, { passive: true });

  // EPUB Preview Scroll ➔ Syncs to PDF Feed
  epubPreview.addEventListener("scroll", () => {
    if (!syncState.enabled || syncState.isProgrammatic) return;

    const dividers = epubPreview.querySelectorAll(".epub-page-divider");
    if (dividers.length === 0) {
      const maxEpub = epubPreview.scrollHeight - epubPreview.clientHeight;
      const maxPdf = pdfFeed.scrollHeight - pdfFeed.clientHeight;
      if (maxEpub > 0 && maxPdf > 0) {
        syncState.isProgrammatic = true;
        const ratio = epubPreview.scrollTop / maxEpub;
        pdfFeed.scrollTo({ top: ratio * maxPdf, behavior: "smooth" });
        clearTimeout(syncState.timer);
        syncState.timer = setTimeout(() => { syncState.isProgrammatic = false; }, 140);
      }
      return;
    }

    let activePage = 1;
    const scrollY = epubPreview.scrollTop + 60;

    for (const div of dividers) {
      if (div.offsetTop <= scrollY) {
        activePage = parseInt(div.dataset.page, 10);
      } else {
        break;
      }
    }

    const targetCard = pdfFeed.querySelector(`#pdf-page-${activePage}`);
    if (targetCard) {
      syncState.isProgrammatic = true;
      const targetTop = targetCard.offsetTop - pdfFeed.offsetTop - 16;
      pdfFeed.scrollTo({ top: Math.max(0, targetTop), behavior: "smooth" });
      const indicator = document.getElementById("pdf-scroll-indicator");
      if (indicator) indicator.textContent = `第 ${activePage} 頁`;
      clearTimeout(syncState.timer);
      syncState.timer = setTimeout(() => { syncState.isProgrammatic = false; }, 140);
    }
  }, { passive: true });
}

/**
 * Initializes draggable divider between split panes.
 * @returns {void}
 */
function initSplitResizer() {
  const resizer = document.getElementById("pane-resizer");
  const panePdf = document.getElementById("pane-pdf");
  const paneEd = document.getElementById("pane-editor");
  const ws = document.getElementById("split-workspace");
  if (!resizer || !panePdf || !paneEd || !ws) return;

  let isResizing = false;

  resizer.addEventListener("mousedown", (e) => {
    isResizing = true;
    resizer.classList.add("resizing");
    document.body.style.cursor = "col-resize";
  });

  window.addEventListener("mousemove", (e) => {
    if (!isResizing) return;
    const rect = ws.getBoundingClientRect();
    const clientX = e.clientX - rect.left;
    const pct = Math.max(20, Math.min(80, (clientX / rect.width) * 100));
    panePdf.style.flex = `0 0 ${pct}%`;
    paneEd.style.flex = `0 0 ${100 - pct}%`;
  });

  window.addEventListener("mouseup", () => {
    if (isResizing) {
      isResizing = false;
      resizer.classList.remove("resizing");
      document.body.style.cursor = "";
    }
  });
}

const SIDEBAR_STORAGE_KEY = "literature_parser_sidebar_collapsed";

/**
 * Toggles sidebar visibility to maximize workspace on smaller screens and persists state.
 * @param {boolean} [forceState] - Optional explicit collapse state to set.
 * @returns {void}
 */
function toggleSidebar(forceState) {
  const sidebar = document.getElementById("sidebar");
  if (!sidebar) return;
  const isCollapsed = typeof forceState === "boolean"
    ? forceState
    : !sidebar.classList.contains("collapsed");
  sidebar.classList.toggle("collapsed", isCollapsed);
  try {
    localStorage.setItem(SIDEBAR_STORAGE_KEY, isCollapsed ? "1" : "0");
  } catch (e) {
    // Ignore localStorage errors
  }
}

/**
 * Initializes sidebar collapse state from localStorage or screen width.
 * Automatically collapses sidebar on initial load if screen width is narrow (< 900px).
 * @returns {void}
 */
function initSidebarState() {
  const sidebar = document.getElementById("sidebar");
  if (!sidebar) return;
  try {
    const saved = localStorage.getItem(SIDEBAR_STORAGE_KEY);
    if (saved !== null) {
      if (saved === "1") sidebar.classList.add("collapsed");
      return;
    }
  } catch (e) {
    // Ignore localStorage errors
  }
  if (window.innerWidth < 900) {
    sidebar.classList.add("collapsed");
  }
}

/**
 * Sets layout mode for the comparison view.
 * @param {"pdf-only"|"split"|"editor-only"} mode - Layout mode name.
 * @returns {void}
 */
function setLayoutMode(mode) {
  const ws = document.getElementById("split-workspace");
  if (ws) ws.dataset.layout = mode;
  document.getElementById("btn-layout-pdf")?.classList.toggle("active", mode === "pdf-only");
  document.getElementById("btn-layout-split")?.classList.toggle("active", mode === "split");
  document.getElementById("btn-layout-editor")?.classList.toggle("active", mode === "editor-only");
}
