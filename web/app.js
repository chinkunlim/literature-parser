/**
 * @file Front-end logic: renders the four standard UI states (loading, empty, error, data).
 */

const container = document.getElementById("app");

/**
 * Render one UI state into the #app section.
 * @param {"loading"|"empty"|"error"|"data"} state State to show.
 * @param {{items?: string[]}} [payload={}] Data for the "data" state.
 * @returns {void}
 */
function render(state, payload = {}) {
  if (!container) return;
  const views = {
    loading: '<p class="muted">載入中…</p>',
    empty: '<p class="muted">目前沒有資料。</p>',
    error: '<p role="alert">載入失敗，請重試。</p>',
    data: `<ul>${(payload.items || []).map((item) => `<li>${item}</li>`).join("")}</ul>`,
  };
  container.innerHTML = views[state] || views.empty;
}

/**
 * Load data and render it (replace the sample data with a fetch() call to your API).
 * @returns {Promise<void>}
 */
async function load() {
  render("loading");
  try {
    const items = ["範例資料 A", "範例資料 B"];
    render(items.length ? "data" : "empty", { items });
  } catch (error) {
    console.error(error);
    render("error");
  }
}

document.getElementById("refresh")?.addEventListener("click", load);
load();
