{# The Baseline page's readout: the dot nearest a mouse's pointer names its repository, and a click goes to its line in
   the table. A tap, a key, or the find field chooses a dot (#29): the readout then names it, with its baseline, its
   recent pace, and its growth, until another dot is chosen or the choice is dismissed, since a finger fires no
   hover, and the browser says it has left the chart the moment it lifts. While a dot is chosen the stylesheet hides
   the ranks' marks, which crowd one another at the top of the chart, so that only the readout names a dot. It also
   sets the ranks' marks again at the size the chart is drawn, beside the dots they name and clear of the rest (#187).
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
  var plot = svg.parentNode;
  {# Where the dots and the table disagree, the build's marks are drawn as the build set them. #}
  if (points.length !== rows.length) { plot.classList.add("placed"); return; }
  var chosen = -1, kind = "mouse", matches = [], at = 0;
  {# The ranks' marks, set again at the size the chart is drawn (#187). The build groups the first ranks' dots by 6 %
     of the plot across and up, and sets a group's mark beside its first dot: on a desktop's wide chart that is 60 px,
     and the mark ran across the other dots it named. Here dots less than 12 px apart share a mark, and each mark is
     set beside one of its dots, to the right of the rightmost first and then to the left of the leftmost, at the
     first place that covers no top dot, meets no other label, and stays in the card, where it can one whose nearest
     top dot is one it names. Where no place is clear it is set where the build would set it, beside its first dot.
     How many ranks are named and how many dots are the top stay the build's: they are read from its marks and from
     the accent's path. Each rank is copied from the table, as the readout's is. The stylesheet hides the marks until
     they are placed, so that none is drawn in one place and then another, and a resize places them again. #}
  var marks = [].slice.call(plot.querySelectorAll(".rk")), card = plot.closest(".card");
  var named = marks.reduce(function (n, mark) { return n + mark.textContent.split(",").length; }, 0);
  var top = paths[1].getAttribute("d").split("M").length - 1;
  var others = [].slice.call(plot.querySelectorAll(".tick, .glabel, .axis"));
  {# How far a dot's centre is from a box, [left, top, right, bottom], 0 inside it. #}
  function gap(b, dot) {
    return Math.hypot(dot.x - Math.min(Math.max(dot.x, b[0]), b[2]), dot.y - Math.min(Math.max(dot.y, b[1]), b[3]));
  }
  function place() {
    var origin = plot.getBoundingClientRect(), width = svg.clientWidth, height = svg.clientHeight, groups = [];
    var radius = parseFloat(getComputedStyle(paths[1]).strokeWidth) / 2;
    function box(el) {
      var b = el.getBoundingClientRect();
      return [b.left - origin.left, b.top - origin.top, b.right - origin.left, b.bottom - origin.top];
    }
    var dots = points.slice(0, top).map(function (point, i) {
      return { i: i, x: point[0] / 100 * width, y: point[1] / 100 * height };
    });
    var taken = others.map(box), bounds = box(card);
    {# A dot joins every group it is near, and the groups it joins become one. #}
    dots.slice(0, named).forEach(function (dot) {
      var group = [dot];
      groups = groups.filter(function (g) {
        var near = g.some(function (o) { return Math.hypot(o.x - dot.x, o.y - dot.y) < 12; });
        if (near) group = g.concat(group);
        return !near;
      });
      groups.push(group);
    });
    groups.forEach(function (g) { g.sort(function (a, b) { return a.i - b.i; }); });
    groups.sort(function (a, b) { return a[0].i - b[0].i; });
    while (marks.length < groups.length) {
      marks.push(plot.insertBefore(marks[0].cloneNode(false), marks[marks.length - 1].nextSibling));
    }
    while (marks.length > groups.length) marks.pop().remove();
    groups.forEach(function (g, n) {
      var mark = marks[n];
      mark.textContent = g.map(function (dot) { return rows[dot.i].children[0].textContent; }).join(", ");
      mark.style.transform = "none";
      var w = mark.offsetWidth, h = mark.offsetHeight, across = g.slice().sort(function (a, b) { return b.x - a.x; });
      var tries = across.map(function (dot) { return [dot.x + 10, dot.y - h / 2]; }).concat(
        across.reverse().map(function (dot) { return [dot.x - 10 - w, dot.y - h / 2]; }));
      function clear(at) {
        var b = [at[0], at[1], at[0] + w, at[1] + h];
        return b[0] >= bounds[0] && b[1] >= bounds[1] && b[2] <= bounds[2] && b[3] <= bounds[3] &&
          dots.every(function (dot) { return gap(b, dot) >= radius; }) &&
          taken.every(function (t) { return t[2] <= b[0] || b[2] <= t[0] || t[3] <= b[1] || b[3] <= t[1]; });
      }
      function own(at) {
        var b = [at[0], at[1], at[0] + w, at[1] + h], mine = Infinity, theirs = Infinity;
        dots.forEach(function (dot) {
          if (g.indexOf(dot) >= 0) mine = Math.min(mine, gap(b, dot));
          else theirs = Math.min(theirs, gap(b, dot));
        });
        return mine <= theirs;
      }
      var at = tries.filter(function (t) { return clear(t) && own(t); })[0] || tries.filter(clear)[0] ||
        [g[0].x + 10, g[0].y - h / 2];
      taken.push([at[0], at[1], at[0] + w, at[1] + h]);
      mark.style.left = at[0] + "px";
      mark.style.top = at[1] + "px";
    });
    plot.classList.add("placed");
  }
  {# A mark's width is its face's, so the marks are set once that face has loaded: `document.fonts.load` asks for the
     marks' own face by name and waits for it, whatever else the page has asked for by then. #}
  document.fonts.load(getComputedStyle(marks[0]).font).then(place, place);
  window.addEventListener("resize", place);

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
