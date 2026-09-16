(function () {
  var body = document.body;
  var readyClass = "page-ready";
  var leavingClass = "page-leave";

  if (!body) return;

  function fadeIn() {
    body.classList.remove(leavingClass);
    requestAnimationFrame(function () {
      body.classList.add(readyClass);
    });
  }

  // Initial fade in
  fadeIn();

  // Handle back/forward buttons
  window.addEventListener("pageshow", function (event) {
    if (event.persisted) fadeIn();
  });

  document.addEventListener("click", function (event) {
    var link = event.target.closest("a");
    if (!link) return;

    var href = link.getAttribute("href");
    if (!href || href.startsWith("#") || link.target === "_blank") return;

    if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;

    var url;
    try {
      url = new URL(href, window.location.href);
    } catch (err) {
      return;
    }

    if (url.origin !== window.location.origin) return;

    // Use modern View Transition if available (Chrome 126+)
    // If not, use manual fade-out
    if (!CSS.supports("view-transition-name", "none") && !document.startViewTransition) {
      event.preventDefault();
      body.classList.add(leavingClass);
      window.setTimeout(function () {
        window.location.href = url.href;
      }, 150);
    }
  });
})();
