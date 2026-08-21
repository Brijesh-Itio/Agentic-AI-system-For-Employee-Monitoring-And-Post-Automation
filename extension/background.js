// MODULE 4.2 — Background service worker
// Listens for tab-change events and immediately reports the new URL,
// instead of waiting for content.js's 5-second interval, so a fast tab
// switch is captured right away.

const WORKPULSE_URL_ENDPOINT = "http://localhost:8001/url";

function reportTab(tab) {
  if (!tab || !tab.url || !tab.url.startsWith("http")) return;
  fetch(WORKPULSE_URL_ENDPOINT, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      url: tab.url,
      title: tab.title || "",
    }),
  }).catch(() => {
    // Agent not running or unreachable — fail silently.
  });
}

chrome.tabs.onActivated.addListener((activeInfo) => {
  chrome.tabs.get(activeInfo.tabId, (tab) => reportTab(tab));
});

chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (changeInfo.status === "complete") {
    reportTab(tab);
  }
});
