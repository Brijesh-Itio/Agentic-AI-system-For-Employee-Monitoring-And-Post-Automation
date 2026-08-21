// MODULE 4.2 — Content script
// Runs on every page. Reports the current URL and title to the local
// WorkPulse agent every 5 seconds, so a session stays fresh even if the
// user lingers on one tab without triggering a tab-change event.

const WORKPULSE_URL_ENDPOINT = "http://localhost:8001/url";
const REPORT_INTERVAL_MS = 5000;

function reportCurrentPage() {
  fetch(WORKPULSE_URL_ENDPOINT, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      url: document.URL,
      title: document.title,
    }),
  }).catch(() => {
    // Agent not running or unreachable — fail silently, retry next interval.
  });
}

reportCurrentPage();
setInterval(reportCurrentPage, REPORT_INTERVAL_MS);
