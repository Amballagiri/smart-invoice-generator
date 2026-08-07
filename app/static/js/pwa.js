let deferredPrompt;

window.addEventListener("beforeinstallprompt", (e) => {
    e.preventDefault();
    deferredPrompt = e;

    const installBtn = document.getElementById("installAppBtn");

    if (installBtn) {
        installBtn.style.display = "inline-block";

        installBtn.addEventListener("click", async () => {
            deferredPrompt.prompt();

            const { outcome } = await deferredPrompt.userChoice;

            if (outcome === "accepted") {
                console.log("App installed");
            }

            deferredPrompt = null;
            installBtn.style.display = "none";
        });
    }
});
if ("serviceWorker" in navigator) {
    window.addEventListener("load", () => {
        navigator.serviceWorker
            .register("/static/sw.js")
            .then(() => console.log("Service Worker Registered"))
            .catch((err) => console.log(err));
    });
}