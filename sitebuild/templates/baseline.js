{# The Baseline page's readout: the dot nearest the pointer names its repository, and a click goes to its line in the
   table. It reads the chart's paths, which the build writes one dot to a row in the board's order, and the table's
   rows; it writes only text and attributes, makes no request, and stores nothing.
   It waits for the page to be parsed, since it runs from the one script in the head. #}
document.addEventListener("DOMContentLoaded", function () {
  var svg = document.querySelector(".plot svg");
  var readout = document.getElementById("readout");
  var here = document.getElementById("here");
  if (!svg || !readout || !here) return;
  var rows = [].slice.call(document.querySelectorAll(".numbers tbody tr"));
  var paths = svg.querySelectorAll("path.dot");
  var points = [];
  (paths[1].getAttribute("d") + paths[0].getAttribute("d")).replace(/M([\d.]+) ([\d.]+)h0/g, function (_, x, y) {
    points.push([Number(x), Number(y)]);
  });
  if (points.length !== rows.length) return;
  var plot = svg.parentNode;
  var nearest = -1;
  plot.addEventListener("pointermove", function (event) {
    var box = svg.getBoundingClientRect();
    var best = 24 * 24;
    nearest = -1;
    points.forEach(function (point, i) {
      var dx = point[0] / 100 * box.width - (event.clientX - box.left);
      var dy = point[1] / 100 * box.height - (event.clientY - box.top);
      if (dx * dx + dy * dy < best) { best = dx * dx + dy * dy; nearest = i; }
    });
    if (nearest < 0) { readout.hidden = true; here.setAttribute("d", ""); plot.style.cursor = ""; return; }
    var cells = rows[nearest].children;
    readout.textContent = cells[0].textContent + "  " + cells[1].textContent + "  " + cells[4].textContent;
    readout.style.left = points[nearest][0] + "%";
    readout.style.top = points[nearest][1] + "%";
    readout.classList.toggle("flip", points[nearest][0] > 60);
    readout.hidden = false;
    here.setAttribute("d", "M" + points[nearest][0] + " " + points[nearest][1] + "h0");
    plot.style.cursor = "pointer";
  });
  plot.addEventListener("pointerleave", function () { readout.hidden = true; here.setAttribute("d", ""); nearest = -1; });
  plot.addEventListener("click", function () {
    if (nearest < 0) return;
    var row = rows[nearest];
    row.scrollIntoView({ block: "center" });
    row.classList.add("flash");
    row.querySelector("a").focus({ preventScroll: true });
    setTimeout(function () { row.classList.remove("flash"); }, 1600);
  });
});
