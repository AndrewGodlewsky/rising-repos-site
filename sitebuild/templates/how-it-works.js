{# How it works's examples (#214): four made-up repositories, each a button that lights the path it takes down the
   diagram. A button names the boxes it passes through, in `data-path`, and the box where it stops, in `data-stop`;
   "finish" is "On the board", which no way off marks. Pressing one presses it alone, shows its own readout, which the
   build wrote with the others, and marks the boxes and the links between them. It writes only attributes and classes,
   and no text, makes no request, and stores nothing. Breaks out is lit in the markup, so that the page is whole with
   scripts off. It waits for the page to be parsed, since it runs from the one script in the head. #}
document.addEventListener("DOMContentLoaded", function () {
  var buttons = [].slice.call(document.querySelectorAll(".examples button[data-example]"));
  var traces = [].slice.call(document.querySelectorAll(".trace"));
  var boxes = [].slice.call(document.querySelectorAll(".flow [data-step]"));
  var links = [].slice.call(document.querySelectorAll(".flow [data-to]"));
  if (!buttons.length) return;
  function choose(button) {
    var path = button.getAttribute("data-path").split(" ");
    var stop = button.getAttribute("data-stop");
    var name = button.getAttribute("data-example");
    buttons.forEach(function (each) { each.setAttribute("aria-pressed", String(each === button)); });
    traces.forEach(function (trace) { trace.hidden = trace.getAttribute("data-example") !== name; });
    boxes.forEach(function (box) {
      var step = box.getAttribute("data-step");
      var lit = step === "begin" || path.indexOf(step) >= 0;
      box.classList.toggle("lit", lit);
      box.classList.toggle("pass", lit && step !== stop);
      box.classList.toggle("stop", step === stop && step !== "finish");
    });
    links.forEach(function (link) { link.classList.toggle("lit", path.indexOf(link.getAttribute("data-to")) >= 0); });
  }
  buttons.forEach(function (button) {
    button.addEventListener("click", function () { choose(button); });
  });
});
