{# The light and dark switch, in every page's head so that a reader's choice applies before the page is first drawn.
   It also marks the root element (data-js), so that the stylesheet shows the controls that need the script from the
   first frame, rather than the script showing them later and moving what is under them.
   The site follows the browser's own setting until a reader presses the switch; their choice is then kept in this
   browser's localStorage, under "theme", and nothing leaves it. A press that comes back to the browser's own setting
   clears the kept choice, so the site follows the browser again, with no third state on the switch. Without this
   script the switch is not shown and the site follows the browser. #}
(function () {
  var root = document.documentElement;
  root.setAttribute("data-js", "");
  var saved = null;
  try { saved = localStorage.getItem("theme"); } catch (error) {}
  if (saved === "light" || saved === "dark") root.setAttribute("data-theme", saved);
  var system = window.matchMedia ? window.matchMedia("(prefers-color-scheme: dark)") : null;
  function dark() {
    var chosen = root.getAttribute("data-theme");
    return chosen ? chosen === "dark" : !!(system && system.matches);
  }
  document.addEventListener("DOMContentLoaded", function () {
    var button = document.getElementById("theme");
    if (!button) return;
    function show() { button.setAttribute("aria-pressed", dark() ? "true" : "false"); }
    button.addEventListener("click", function () {
      var next = dark() ? "light" : "dark";
      if ((next === "dark") === !!(system && system.matches)) {
        root.removeAttribute("data-theme");
        try { localStorage.removeItem("theme"); } catch (error) {}
      } else {
        root.setAttribute("data-theme", next);
        try { localStorage.setItem("theme", next); } catch (error) {}
      }
      show();
    });
    if (system && system.addEventListener) system.addEventListener("change", show);
    show();
  });
})();
