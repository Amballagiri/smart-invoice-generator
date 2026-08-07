const CACHE_NAME = "smart-invoice-v1";

self.addEventListener("install", (event) => {
    console.log("Service Worker Installed");
    self.skipWaiting();
});

self.addEventListener("activate", (event) => {
    console.log("Service Worker Activated");
});

self.addEventListener("fetch", (event) => {
    // Allow normal network requests.
});