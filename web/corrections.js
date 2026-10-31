/**
 * @file Human Corrections Feedback Library & Visual Diff Samples for Literature Studio.
 * Handles issue modal recording, unified diff calculations, feedback history table,
 * deletion, and triggering automated regression test generation.
 */

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
 * @param {string} id - Record UUID.
 * @returns {Promise<void>}
 */
async function deleteCorrection(id) {
  if (!confirm("確定要刪除這筆修正記錄？")) return;
  try {
    const res = await fetch(`/api/corrections/${id}`, { method: "DELETE" });
    if (res.ok) {
      showToast("已刪除記錄", "info");
      loadCorrections();
      loadDashboard();
    }
  } catch (err) {
    showToast(`刪除失敗: ${err.message}`, "error");
  }
}

/**
 * Triggers automated regression test generator from corrections.
 * @returns {Promise<void>}
 */
async function generateRegressionTests() {
  try {
    showToast("正在分析修正並生成測試...", "info");
    const res = await fetch("/api/corrections/generate-tests", { method: "POST" });
    const data = await res.json();
    showToast(`成功產生 ${data.tests_generated} 個回歸測試案例！`, "success");
  } catch (err) {
    showToast(`生成失敗: ${err.message}`, "error");
  }
}
