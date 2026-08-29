/* ==========================================================================
   report.js — Report tab: triggers PDF download from the backend.
   ========================================================================== */

async function downloadReport() {
  if (!AppState.hasDataset) {
    showToast("Upload a dataset first.", "error");
    return;
  }
  showLoading("Generating your PDF report…");
  try {
    const res = await fetch("/api/report");
    if (!res.ok) {
      let msg = "Failed to generate report.";
      try {
        const body = await res.json();
        msg = body.error || msg;
      } catch (e) {}
      throw new Error(msg);
    }
    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    const disposition = res.headers.get("Content-Disposition") || "";
    const match = disposition.match(/filename="?([^"]+)"?/);
    a.download = match ? match[1] : "analysis_report.pdf";
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);
    showToast("Report downloaded successfully.", "success");
  } catch (err) {
    showToast(err.message, "error");
  } finally {
    hideLoading();
  }
}
