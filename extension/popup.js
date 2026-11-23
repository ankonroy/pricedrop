// Pricedrop Tracker — popup logic
// Talks to the FastAPI backend running on localhost:8000

const API = "http://localhost:8000";

const urlEl = document.getElementById("currentUrl");
const trackBtn = document.getElementById("trackBtn");
const statusEl = document.getElementById("status");
const listEl = document.getElementById("list");

let currentUrl = null;


// --- Helpers ---
function showStatus(message, kind = "success") {
  statusEl.textContent = message;
  statusEl.className = kind;
  setTimeout(() => {
    statusEl.className = "";
    statusEl.textContent = "";
  }, 4000);
}

function renderProducts(products) {
  if (!products || products.length === 0) {
    listEl.innerHTML = '<div class="empty">No products tracked yet.</div>';
    return;
  }
  listEl.innerHTML = products
    .map(
      (p) => `
        <div class="item">
          <span class="name">${escapeHtml(p.name)}</span>
          <span class="meta">
            ${p.price !== null ? `${p.currency}${p.price.toFixed(2)}` : "no price yet"}
            · ${p.in_stock === false ? "out of stock" : "in stock"}
          </span>
        </div>
      `
    )
    .join("");
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}


// --- Load current tab URL + product list on popup open ---
async function init() {
  // 1. Get the current tab's URL
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (tab && tab.url && /^https?:/i.test(tab.url)) {
      currentUrl = tab.url;
      urlEl.textContent = currentUrl;
      trackBtn.disabled = false;
    } else {
      urlEl.textContent = "(Not a valid HTTP page — open a product page first)";
      trackBtn.disabled = true;
    }
  } catch (e) {
    urlEl.textContent = "Could not read current tab: " + e.message;
  }

  // 2. Load existing products from the backend
  await loadProducts();
}


async function loadProducts() {
  try {
    const res = await fetch(`${API}/products`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const products = await res.json();
    renderProducts(products);
  } catch (e) {
    listEl.innerHTML = `<div class="empty">Cannot reach backend.<br>Is uvicorn running on :8000?</div>`;
  }
}


// --- Track button ---
trackBtn.addEventListener("click", async () => {
  if (!currentUrl) return;

  trackBtn.disabled = true;
  const originalText = trackBtn.textContent;
  trackBtn.textContent = "Tracking... (scraping takes ~5s)";

  try {
    const res = await fetch(`${API}/products`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url: currentUrl }),
    });

    const data = await res.json();

    if (!res.ok) {
      // Backend returns {"detail": "..."} for errors
      const msg = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail);
      showStatus("Failed: " + msg, "error");
    } else {
      showStatus(`Tracked: ${data.name} @ ${data.currency}${data.price}`, "success");
      await loadProducts();   // refresh the list
    }
  } catch (e) {
    showStatus("Network error: " + e.message, "error");
  } finally {
    trackBtn.disabled = false;
    trackBtn.textContent = originalText;
  }
});


// --- Boot ---
init();