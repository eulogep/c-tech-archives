/* Chargé avant le rendu : applique le thème et l’état de la barre latérale
   mémorisés, sans flash. Script externe pour respecter la CSP (pas d’inline). */
(() => {
  "use strict";
  try {
    const root = document.documentElement;
    const theme = window.localStorage.getItem("ctech-theme");
    if (theme === "light" || theme === "dark") {
      root.dataset.theme = theme;
    }
    if (window.localStorage.getItem("ctech-sidebar") === "collapsed") {
      root.dataset.sidebar = "collapsed";
    }
  } catch (error) {
    /* Stockage indisponible (navigation privée) : préférences système. */
  }
})();
