{# The Baseline page's readout: the dot nearest a mouse's pointer names its repository, and a click goes to its line in
   the table. A tap, a key, or the find field chooses a dot (#29): the readout then names it, with its baseline, its
   recent pace, and its growth, until another dot is chosen or the choice is dismissed, since a finger fires no
   hover, and the browser says it has left the chart the moment it lifts. While a dot is chosen the stylesheet hides
   the ranks' marks, which crowd one another at the top of the chart, so that only the readout names a dot.
   It reads the chart's paths, which the build writes one dot to a row in the board's order, and the table's rows,
   whose words the build wrote: the readout copies them, so that it and the table never disagree. It writes only
   text and attributes, makes no request, and stores nothing. What a reader types in the field is only compared
   with the names. It waits for the page to be parsed, since it runs from the one script in the head. #}
document.addEventListener("DOMContentLoaded", function () {
  var svg = document.querySelector(".plot svg");
  var readout = document.getElementById("readout");
  var here = document.getElementById("here");
  var find = document.getElementById("find");
  var found = document.getElementById("found");
  if (!svg || !readout || !here || !find || !found) return;
  var rows = [].slice.call(document.querySelectorAll(".numbers tbody tr"));
  var paths = svg.querySelectorAll("path.dot");
  var points = [];
  (paths[1].getAttribute("d") + paths[0].getAttribute("d")).replace(/M([\d.]+) ([\d.]+)h0/g, function (_, x, y) {
    points.push([Number(x), Number(y)]);
  });
  if (points.length !== rows.length) return;
  var plot = svg.parentNode;
  var chosen = -1, kind = "mouse", matches = [], at = 0;
  {# The chart takes the keyboard's focus only where this script runs to answer it. #}
  svg.setAttribute("tabindex", "0");

  {# The dot within 24 px of where the event is, or -1. #}
  function nearest(event) {
    var box = svg.getBoundingClientRect(), best = 24 * 24, near = -1;
    points.forEach(function (point, i) {
      var dx = point[0] / 100 * box.width - (event.clientX - box.left);
      var dy = point[1] / 100 * box.height - (event.clientY - box.top);
      if (dx * dx + dy * dy < best) { best = dx * dx + dy * dy; near = i; }
    });
    return near;
  }

  {# Names dot `i` in the readout and marks it, or, for -1, shows neither. The readout sits beside its dot, on the
     side it fits, or over or under it where it fits beside it on neither, as on a phone, so that it stays inside
     the chart's card. #}
  function show(i) {
    if (i < 0) { readout.hidden = true; here.setAttribute("d", ""); return; }
    var cells = rows[i].children, x = points[i][0], y = points[i][1];
    readout.textContent = cells[0].textContent + "  " + cells[1].textContent + "\nBaseline  " + cells[2].textContent +
      " a day\nRecent    " + cells[3].textContent + " a day\nGrowth    " + cells[4].textContent;
    here.setAttribute("d", "M" + x + " " + y + "h0");
    readout.hidden = false;
    var width = plot.clientWidth, height = plot.clientHeight, w = readout.offsetWidth, h = readout.offsetHeight;
    x = x / 100 * width;
    y = y / 100 * height;
    var left = x + 12, top = y - h / 2;
    if (left + w > width) left = x - 12 - w;
    if (left < -40) {
      left = Math.max(-40, Math.min(x - w / 2, width - w));
      top = y - 12 - h < -28 ? y + 12 : y - 12 - h;
    }
    readout.style.left = left + "px";
    readout.style.top = top + "px";
  }

  function choose(i) {
    chosen = i;
    plot.classList.toggle("chosen", i >= 0);
    show(i);
  }

  {# Goes to dot `i`'s line in the table, as a click on it always has. #}
  function go(i) {
    var row = rows[i];
    row.scrollIntoView({ block: "center" });
    row.classList.add("flash");
    row.querySelector("a").focus({ preventScroll: true });
    setTimeout(function () { row.classList.remove("flash"); }, 1600);
  }

  {# A mouse names the dot under it for as long as it is there, and then the chosen one again. #}
  plot.addEventListener("pointermove", function (event) {
    if (event.pointerType === "touch") return;
    var near = nearest(event);
    show(near < 0 ? chosen : near);
    plot.style.cursor = near < 0 ? "" : "pointer";
  });
  plot.addEventListener("pointerleave", function () { show(chosen); });
  plot.addEventListener("pointerdown", function (event) { kind = event.pointerType; });
  {# A click or a tap chooses the dot nearest it, and a tap away from every dot dismisses. A mouse's click goes on to
     the dot's line in the table, as it did before; a tap goes there from the dot already chosen. #}
  plot.addEventListener("click", function (event) {
    var near = nearest(event), again = near >= 0 && near === chosen;
    choose(near);
    if (near >= 0 && (kind === "mouse" || again)) go(near);
  });

  {# From the keyboard, the chart's focus chooses the first rank, the arrows step through the ranks, Home and End go
     to the first and the last, Enter goes to the line in the table, and Escape dismisses. #}
  svg.addEventListener("focus", function () {
    if (chosen < 0 && svg.matches(":focus-visible")) choose(0);
  });
  svg.addEventListener("keydown", function (event) {
    var last = points.length - 1, step = { ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1 }[event.key];
    if (step) choose(Math.min(last, Math.max(0, chosen + step)));
    else if (event.key === "Home") choose(0);
    else if (event.key === "End") choose(last);
    else if (event.key === "Enter" && chosen >= 0) go(chosen);
    else if (event.key === "Escape") choose(-1);
    else return;
    event.preventDefault();
  });

  {# The field chooses the first by rank whose name holds what is typed, in any case, and Enter the next. #}
  function count() {
    found.textContent = !find.value.trim() ? "" : !matches.length ? "None on this board" :
      matches.length > 1 ? at + 1 + " of " + matches.length + ", Enter for the next" : "";
  }
  find.addEventListener("input", function () {
    var typed = find.value.trim().toLowerCase();
    matches = [];
    if (typed) rows.forEach(function (row, i) {
      if (row.children[1].textContent.toLowerCase().indexOf(typed) >= 0) matches.push(i);
    });
    at = 0;
    choose(matches.length ? matches[0] : -1);
    count();
  });
  find.addEventListener("keydown", function (event) {
    if (event.key !== "Enter" || !matches.length) return;
    event.preventDefault();
    at = (at + 1) % matches.length;
    choose(matches[at]);
    count();
  });
});
