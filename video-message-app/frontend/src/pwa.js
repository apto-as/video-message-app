/**
 * PWA Service Worker registration helper.
 * Call registerSW() from index.js after app renders.
 */
export function registerSW() {
  if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
      navigator.serviceWorker
        .register('/sw.js')
        .then((registration) => {
          // Check for updates every hour
          setInterval(() => registration.update(), 60 * 60 * 1000);
        })
        .catch((err) => {
          console.warn('Service Worker registration failed:', err);
        });
    });
  }
}
