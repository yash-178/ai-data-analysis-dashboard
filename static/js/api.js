/* ==========================================================================
   api.js — thin fetch wrapper + shared UI helpers (toasts, loading overlay,
   table rendering) used by every other module.
   ========================================================================== */

const API = {
  async _handle(res) {
    let body;
    try {
      body = await res.json();
    } catch (e) {
      throw new Error("Unexpected server response.");
    }
    if (!res.ok || body.success === false) {
      throw new Error(body.error || "Something went wrong.");
    }
    return body;
  },

  async get(url) {
    const res = await fetch(url);
    return this._handle(res);
  },

  async post(url, data) {
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data || {}),
    });
    return this._handle(res);
  },

  async postForm(url, formData) {
    const res = await fetch(url, { method: "POST", body: formData });
    return this._handle(res);
  },
};

/* ---------------- Loading overlay ---------------- */
function showLoading(text) {
  const overlay = document.getElementById("loadingOverlay");
  document.getElementById("loadingText").textContent = text || "Processing…";
  overlay.classList.remove("hidden");
}
function hideLoading() {
  document.getElementById("loadingOverlay").classList.add("hidden");
}

/* ---------------- Toasts ---------------- */
const ICONS = {
  success: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none"><path d="M20 6L9 17l-5-5" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  error: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="9" stroke="currentColor" stroke-width="2"/><path d="M12 8v5M12 16h.01" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"/></svg>',
  info: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="9" stroke="currentColor" stroke-width="2"/><path d="M12 11v5M12 8h.01" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"/></svg>',
};

function showToast(message, type = "info", timeout = 4200) {
  const container = document.getElementById("toastContainer");
  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `<span class="toast-icon">${ICONS[type] || ICONS.info}</span><span>${escapeHtml(message)}</span>`;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transition = "opacity 0.25s ease";
    setTimeout(() => toast.remove(), 260);
  }, timeout);
}

/* ---------------- Small helpers ---------------- */
function escapeHtml(str) {
  if (str === null || str === undefined) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function formatNumber(n) {
  if (n === null || n === undefined || Number.isNaN(n)) return "—";
  if (typeof n !== "number") return n;
  if (Number.isInteger(n)) return n.toLocaleString();
  return n.toLocaleString(undefined, { maximumFractionDigits: 2 });
}

function badgeForType(dtype) {
  const d = (dtype || "").toLowerCase();
  if (d.includes("float") || d.includes("int")) return '<span class="badge badge-numeric">numeric</span>';
  if (d.includes("datetime")) return '<span class="badge badge-datetime">datetime</span>';
  if (d.includes("bool")) return '<span class="badge badge-boolean">boolean</span>';
  return '<span class="badge badge-categorical">categorical</span>';
}

/** Build an HTML <table> from an array of objects (records). */
function renderTable(records, opts = {}) {
  if (!records || records.length === 0) {
    return `<p style="color:var(--ink-faint); font-size:13px; padding:8px 0;">${opts.emptyMessage || "No data to display."}</p>`;
  }
  const columns = opts.columns || Object.keys(records[0]);
  let html = '<table class="data-table"><thead><tr>';
  columns.forEach((c) => (html += `<th>${escapeHtml(opts.headerLabels?.[c] || c)}</th>`));
  html += "</tr></thead><tbody>";
  records.forEach((row) => {
    html += "<tr>";
    columns.forEach((c) => {
      let val = row[c];
      if (val === null || val === undefined) val = '<span style="color:var(--ink-faint)">null</span>';
      else val = escapeHtml(val);
      html += `<td>${val}</td>`;
    });
    html += "</tr>";
  });
  html += "</tbody></table>";
  return html;
}
