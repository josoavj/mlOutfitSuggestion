(function () {
  var body = document.body;
  var readyClass = "page-ready";

  if (!body) return;

  // On lance l'apparition fluide de la NOUVELLE page
  requestAnimationFrame(function () {
    body.classList.add(readyClass);
  });

  // On laisse le navigateur gérer le départ naturellement pour éviter le flash noir
  // (Pas de preventDefault, pas de fade-out manuel)
})();
