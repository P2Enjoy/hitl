// Minimal content script — relays messages from the page to the background
// service worker. Only injected on localhost:7331 (native host relay page).

window.addEventListener("message", (event: MessageEvent) => {
  if (event.source !== window) return;
  if (!event.data || typeof event.data !== "object") return;
  if (event.data.direction !== "page-to-bg") return;

  chrome.runtime.sendMessage(event.data.message).then((response) => {
    window.postMessage({ direction: "bg-to-page", response }, "*");
  });
});
