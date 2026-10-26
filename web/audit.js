/**
 * @file Audit Inspector and Defect Locator for Literature Studio Web Application.
 * Renders quality inspection status badges, defect lists, and handles smooth scrolling/highlighting
 * to problematic lines in the live preview or editor.
 */

/**
 * Renders the top audit inspector bar and defect list drawer for the active chapter.
 * @param {object|null} audit - Audit report data from API.
 * @returns {void}
 */
function renderAuditInspector(audit) {
  const bar = document.getElementById("audit-inspector-bar");
  const badge = document.getElementById("audit-score-badge");
  const text = document.getElementById("audit-summary-text");
  const btnToggle = document.getElementById("btn-toggle-defects");
  const drawer = document.getElementById("audit-defect-drawer");
  const list = document.getElementById("audit-defect-list");
  if (!bar || !badge || !text) return;

  if (!audit) {
    bar.style.display = "none";
    if (drawer) drawer.style.display = "none";
    return;
  }

  bar.style.display = "flex";
  const score = audit.score != null ? audit.score : 100;
  badge.textContent = `${score}%`;
  badge.className = "badge-score";

  if (score >= 95) {
    badge.classList.add("badge-score-success");
  } else if (score >= 80) {
    badge.classList.add("badge-score-warning");
  } else {
    badge.classList.add("badge-score-danger");
  }

  const issues = audit.issues || [];
  if (issues.length === 0 && score === 100) {
    text.textContent = "✅ 質量檢驗通過 (出版級 100% 無瑕疵)";
    if (btnToggle) btnToggle.style.display = "none";
    if (drawer) drawer.style.display = "none";
  } else {
    text.textContent = `⚠️ 檢出 ${issues.length} 處待審查排版/格式問題`;
    if (btnToggle) {
      btnToggle.style.display = "inline-block";
      btnToggle.textContent = `🚨 展開待審查問題 (${issues.length})`;
    }

    if (list) {
      list.innerHTML = "";
      issues.forEach((iss) => {
        const card = document.createElement("div");
        card.className = "audit-defect-card";
        const lineStr = iss.line_num != null ? `第 ${iss.line_num} 行` : "全域";
        const sevClass = `severity-${iss.severity || 'WARNING'}`;
        card.innerHTML = `
          <div class="audit-defect-meta">
            <span class="audit-severity-tag ${sevClass}">${iss.severity || 'WARN'}</span>
            <span style="color:var(--text-secondary);">${lineStr}:</span>
            <strong style="color:var(--text-bright);">${iss.category || 'DEFECT'}</strong>
            <span style="color:var(--text-primary); margin-left:4px;">${iss.message}</span>
          </div>
          <button class="btn" style="padding:1px 6px; font-size:0.7rem;">定位 ➔</button>
        `;

        card.addEventListener("click", () => {
          jumpToDefect(iss.line_num, iss.snippet || iss.message);
        });
        list.appendChild(card);
      });
    }

    // Auto expand drawer when defects exist
    if (drawer) drawer.style.display = "block";
  }
}

/**
 * Smoothly scrolls to a defect location and flashes a golden highlighting halo.
 * @param {number|null} lineNum - 1-based line number in source Markdown.
 * @param {string} snippet - Text snippet or keyword to locate in preview.
 * @returns {void}
 */
function jumpToDefect(lineNum, snippet) {
  const isRawTab = document.getElementById("tab-editor-raw")?.classList.contains("active");
  const textarea = document.getElementById("markdown-textarea");

  if (isRawTab && textarea && lineNum != null) {
    const lines = textarea.value.split("\n");
    let charPos = 0;
    for (let i = 0; i < Math.min(lineNum - 1, lines.length); i++) {
      charPos += lines[i].length + 1;
    }
    textarea.focus();
    textarea.setSelectionRange(charPos, charPos + (lines[lineNum - 1]?.length || 0));
    textarea.scrollTop = Math.max(0, (lineNum - 5) * 18);
    showToast(`已跳轉至 Markdown 編輯器第 ${lineNum} 行`, "info");
    return;
  }

  const preview = document.getElementById("preview-viewport");
  if (!preview) return;

  const cleanSnippet = (snippet || "").replace(/[*_#`]/g, "").trim().slice(0, 30);
  const elements = preview.querySelectorAll("p, h1, h2, h3, h4, table, div");
  let targetEl = null;

  if (cleanSnippet && cleanSnippet.length > 3) {
    for (const el of elements) {
      if (el.textContent && el.textContent.includes(cleanSnippet)) {
        targetEl = el;
        break;
      }
    }
  }

  if (!targetEl && lineNum != null) {
    const approxIdx = Math.min(Math.floor(lineNum / 4), elements.length - 1);
    if (approxIdx >= 0 && approxIdx < elements.length) {
      targetEl = elements[approxIdx];
    }
  }

  if (targetEl) {
    targetEl.scrollIntoView({ behavior: "smooth", block: "center" });
    targetEl.classList.remove("audit-highlight-flash");
    void targetEl.offsetWidth;
    targetEl.classList.add("audit-highlight-flash");
    setTimeout(() => {
      targetEl.classList.remove("audit-highlight-flash");
    }, 2800);
    showToast(`已鎖定問題段落: ${cleanSnippet || `第 ${lineNum} 行`}`, "info");
  } else {
    showToast(`已標示問題: ${cleanSnippet || '全域問題'}`, "info");
  }
}
