{# The board's search, filters, order, and opened rows. Without this script the page is the whole board, by rank,
   and a row's chevron opens it on its reason line. It reads the page: each row's name, description, total stars,
   growth figure, and New mark from its own cells, and its language and how many of the last 14 boards listed it from
   its data- attributes. The All and New buttons count what the search and the other filters leave. When a reader
   first opens a row it fetches the board day's history.json from the site's own address, once, and opens the row
   only when the file is in, so its detail arrives in one step and nothing under it moves twice: the sum behind its
   reason, the drawing of its own pace against what it gained, its facts, its last 30 board days, and the boards it
   was on. If the file cannot be had, the row opens on its reason line and says the rest could not be loaded. It
   writes only text, elements, classes, and attributes, stores nothing but the view in the address, and a new order
   moves rows without renumbering one: each keeps the rank its file gives it.
   It waits for the page to be parsed, since it runs from the one script in the head. #}
document.addEventListener("DOMContentLoaded", function () {
  var table = document.querySelector("table.chart");
  var q = document.getElementById("q");
  var kinds = document.getElementById("kinds");
  var bands = document.getElementById("bands");
  var language = document.getElementById("language");
  var sort = document.getElementById("sort");
  var shown = document.getElementById("shown");
  var none = document.getElementById("none-shown");
  if (!table || !q || !kinds || !bands || !language || !sort || !shown) return;
  {# The star bands, from their buttons: where each stops (data-below, none for the top band), and its word in the
     address (data-word, "30k-plus"), which the build makes from the band's limits. #}
  var bandButtonsByNumber = [].slice.call(bands.querySelectorAll("button[data-below]"));
  var below = bandButtonsByNumber.map(function (b) { return b.getAttribute("data-below") ? Number(b.getAttribute("data-below")) : Infinity; });
  var bandWords = bandButtonsByNumber.map(function (b) { return b.getAttribute("data-word"); });
  function bandOf(stars) { var band = 0; while (stars >= below[band]) band++; return band; }
  var rows = [].slice.call(table.querySelectorAll("tbody tr")).map(function (row, i) {
    var stars = Number(row.querySelector(".st").textContent.replace(/\D/g, ""));
    {# Its gain, read back from its growth cell for the "Most stars gained" order: a loss is written with the true
       minus, which parseFloat does not read, so it becomes the hyphen first, and the dash of no count reads as 0. #}
    var grew = row.querySelector("td.gr");
    {# The language: in the row's data-l, or in its own cell on a board whose file predates the rows' numbers. #}
    var cell = row.querySelector("td.language");
    var written = row.getAttribute("data-l") || (cell ? cell.textContent : "");
    var description = row.querySelector(".de");
    {# The search reads the name, which is the link's text, and the description. The cell's own text would bring
       the New mark with it, and a search for "new" would then show every new row. #}
    return {
      element: row,
      index: i,
      band: String(bandOf(stars)),
      language: written,
      text: (row.querySelector(".re a").textContent + " " +
        (description.classList.contains("none") ? "" : description.textContent)).toLowerCase(),
      stars: stars,
      daily: grew ? parseFloat(grew.textContent.replace(/[+,]/g, "").replace("−", "-")) || 0 : 0,
      often: Number(row.getAttribute("data-o")) || 0,
      fresh: !!row.querySelector(".re .new")
    };
  });
  var body = table.tBodies[0];
  var kindButtons = [].slice.call(kinds.querySelectorAll("button"));
  var bandButtons = [].slice.call(bands.querySelectorAll("button"));
  var kind = "";
  var band = "";
  {# Each order; ties keep rank order. #}
  var orders = {
    rank: function () { return 0; },
    gained: function (a, b) { return b.daily - a.daily; },
    often: function (a, b) { return b.often - a.often; },
    small: function (a, b) { return a.stars - b.stars; },
    large: function (a, b) { return b.stars - a.stars; }
  };

  {# The board's links to another board day: the day bar's previous, next, and Latest, the foot's previous and next,
     and the earlier-board note's link to the newest board. On a board's page only these have rel=prev, rel=next,
     the class latest, or sit in the note. #}
  var steps = document.querySelectorAll("[rel=prev],[rel=next],.latest,.earlier a");
  function apply() {
    var words = q.value.trim().toLowerCase().split(/\s+/).filter(Boolean);
    var count = 0, all = 0, fresh = 0;
    rows.forEach(function (row) {
      var others = (band === "" || row.band === band) && (language.value === "" || row.language === language.value) &&
        words.every(function (word) { return row.text.indexOf(word) >= 0; });
      var fits = others && (kind === "" || row.fresh);
      row.element.hidden = !fits;
      if (fits) count++;
      if (others) { all++; if (row.fresh) fresh++; }
    });
    {# The buttons say what the search and the other filters leave: with Rust chosen, the Rust rows and the new ones. #}
    var countAll = document.getElementById("count-all");
    var countNew = document.getElementById("count-new");
    if (countAll) countAll.textContent = all;
    if (countNew) countNew.textContent = fresh;
    var order = orders[sort.value] || orders.rank;
    rows.slice().sort(function (a, b) { return order(a, b) || a.index - b.index; })
      .forEach(function (row) { body.appendChild(row.element); });
    {# Said to a screen reader only: the buttons carry the counts on the screen. #}
    shown.textContent = (count === rows.length ? "All " + count + " shown" : count + " of " + rows.length + " shown") +
      (sort.value !== "rank" ? ", " + sort.options[sort.selectedIndex].text.toLowerCase().replace(/ first$/, "") + " first; each keeps its rank" : "");
    if (none) {
      none.hidden = count > 0;
      if (!count) none.firstElementChild.textContent = nothing(words.length);
    }
    {# Each link to another board day carries the filters and the order, so that stepping a day keeps them (#148).
       apply() runs on load, on each change of the view, and on Back and Forward, so the links follow the view the
       page settled on. Without the script they stay the plain addresses the build wrote. #}
    var kept = String(view());
    steps.forEach(function (a) { a.href = a.pathname + (kept && "?" + kept); });
  }
  {# The line that says nothing matches names each part of the view that is chosen, by the words its control shows: New,
     a band's label, a language (#33). A search is named "the search" and not by its words, which come from the address
     and so are not written into the page (P22): they stay in view in the search field. #}
  function nothing(searched) {
    var chosen = [];
    if (kind) chosen.push("New");
    if (band !== "") chosen.push(bandButtonsByNumber[band].textContent + " stars");
    if (language.value) chosen.push(language.value);
    var last = chosen.pop();
    var listed = chosen.length ? chosen.join(", ") + (chosen.length > 1 ? "," : "") + " and " + last : last;
    return "No repository on this board matches " + (searched ? "the search" + (last ? " among " + listed : "") :
      "the filter" + (chosen.length ? "s" : "") + ": " + listed) + ".";
  }
  function press(buttons, name, value) {
    buttons.forEach(function (button) { button.setAttribute("aria-pressed", button.getAttribute(name) === value ? "true" : "false"); });
  }
  {# The view is kept in the address's query, so that it can be shared, bookmarked, and walked with Back and
     Forward: show=new, band=1k-3k, lang=Rust, sort=gained, and q=the search, each left out at its default. The
     server sends the same page whatever the query says, and a value the page does not know is ignored, as is a
     band the board holds back. The links to other board days carry the view without the search: its words come
     from the address or the reader's typing, and stay in the search field alone (P22; the owner's answer on #148,
     26 November 2026). The rest is built from words the build wrote, never from the address, so a value the
     board does not hold is carried by no link. #}
  function read() {
    var query = new URLSearchParams(location.search);
    kind = query.get("show") === "new" && kindButtons.some(function (b) { return b.getAttribute("data-kind") === "new"; }) ? "new" : "";
    var number = bandWords.indexOf(query.get("band"));
    band = number >= 0 && !bandButtonsByNumber[number].hidden ? String(number) : "";
    var wanted = (query.get("lang") || "").toLowerCase();
    language.value = "";
    [].forEach.call(language.options, function (option) { if (option.value && option.value.toLowerCase() === wanted) language.value = option.value; });
    sort.value = orders.hasOwnProperty(query.get("sort")) ? query.get("sort") : "rank";
    q.value = query.get("q") || "";
    press(kindButtons, "data-kind", kind);
    press(bandButtons, "data-band", band);
  }
  {# The query of the filters and the order, each left out at its default: one function for the address and the
     links alike, so that they cannot disagree (C17). #}
  function view() {
    var query = new URLSearchParams();
    if (kind) query.set("show", kind);
    if (band !== "") query.set("band", bandWords[band]);
    if (language.value) query.set("lang", language.value);
    if (sort.value !== "rank") query.set("sort", sort.value);
    return query;
  }
  function write(push) {
    var query = view();
    if (q.value.trim()) query.set("q", q.value.trim());
    var search = query.toString() ? "?" + query.toString() : "";
    if (search === location.search) return;
    window.history[push ? "pushState" : "replaceState"](null, "", location.pathname + search + location.hash);
  }
  function group(buttons, name, set) {
    buttons.forEach(function (button) {
      button.addEventListener("click", function () {
        set(button.getAttribute(name));
        press(buttons, name, button.getAttribute(name));
        apply();
        write(true);
      });
    });
  }
  group(kindButtons, "data-kind", function (value) { kind = value; });
  group(bandButtons, "data-band", function (value) { band = value; });
  {# A search starts a new entry in the history, and its typing then refines that entry. #}
  q.addEventListener("input", function () { var started = !new URLSearchParams(location.search).get("q"); apply(); write(started); });
  language.addEventListener("change", function () { apply(); write(true); });
  sort.addEventListener("change", function () { apply(); write(true); });
  window.addEventListener("popstate", function () { read(); apply(); });
  {# Clear search and filters: the whole board again, in the order chosen, as a new entry that Back leaves. The
     button hides with its line, so the keyboard goes to the All button, the first of the filter's controls, rather
     than to the search, which would open a phone's keyboard (#33). #}
  if (none) none.lastElementChild.addEventListener("click", function () {
    kind = band = language.value = q.value = "";
    press(kindButtons, "data-kind", kind);
    press(bandButtons, "data-band", band);
    apply();
    write(true);
    kindButtons[0].focus();
  });

  {# An opened row's history, from the board day's history.json, fetched once on first opening. #}
  var history = null;
  function load() {
    if (!history) {
      history = fetch(table.getAttribute("data-history"), { credentials: "same-origin" }).then(function (response) {
        if (!response.ok) throw new Error(response.status);
        return response.json();
      });
      history.catch(function () { history = null; });
    }
    return history;
  }
  {# Every word and figure an opened row shows comes worded in the file, as the board words the same ones
     (sitebuild/__init__.py's history_file): the script places them, and keeps numbers only for the lines it draws. #}
  {# A path through `points`, each [x, y] or null, broken where a point is null, so that a missing day is a gap. #}
  function trace(points) {
    var d = "", pen = false;
    points.forEach(function (point) {
      if (!point) { pen = false; return; }
      d += (pen ? "L" : "M") + point[0] + " " + point[1];
      pen = true;
    });
    return d;
  }
  function make(tag, className, text) {
    var element = document.createElement(tag);
    if (className) element.className = className;
    if (text !== undefined) element.textContent = text;
    return element;
  }
  function role(element, name) { element.setAttribute("role", name); return element; }
  var SVG = "http://www.w3.org/2000/svg";
  {# A figure of the opened row, named by its caption through aria-labelledby, so that its name does not rest on a
     browser taking it from the figcaption. #}
  var captions = 0;
  function figureOf(className, title) {
    var box = make("figure", className);
    var caption = make("figcaption", "part-title", title);
    caption.id = "caption-" + (++captions);
    box.setAttribute("aria-labelledby", caption.id);
    box.appendChild(caption);
    return box;
  }
  function shape(tag, attributes) {
    var element = document.createElementNS(SVG, tag);
    Object.keys(attributes).forEach(function (name) { element.setAttribute(name, attributes[name]); });
    return element;
  }

  {# Its own pace against what it gained, as How it works draws its worked example, from the row's own numbers over
     the ranking's 14 days. Where the file gives the row's daily star counts, the line of what it gained is its real
     count day by day, broken where a day has none, and the dashed line of its own pace runs through its count before
     the recent days. Where it does not, the file gives two averages, not a count for each day, so each run is
     straight: the dashed line of its own pace over the 12 days before and on through the recent days, and the line
     of what it gained over those. Either way the part between the two over the recent days is shaded, its edge
     through the very points of the line of what it gained and back along the dashed line, so that the shading and
     the line never part where the recent days were uneven (#89). The tag that names it stands above the highest of
     the line and of the dashed line's end, so that it covers no part of the line nor the tag under the dashed line.
     Where that is near the height of the dashed line's start, at the top of a row that had been losing stars, the
     tag of its usual pace stands there too, so the drawing leaves more room at its top and the tag of the gain
     stands above the other: both are placed as the drawing is made, so nothing moves once it is drawn.
     `pace` is what its lines are drawn from, and `said` its three labels and its sentence for a screen reader; `real`
     is the 15 counts from 14 days before the board day to the board day. #}
  function drawing(pace, said, counts) {
    var baseline = pace[0], gained = pace[1], days = pace[2];
    var end = 12 + days;
    var real = counts ? counts.slice(16) : null;
    if (real && (real[12] === null || real[end] === null)) real = null;
    var start, own, got, values;
    if (real) {
      start = real[12];
      own = start + days * baseline;
      got = real[end];
      values = real.filter(function (n) { return n !== null; }).concat([start - 12 * baseline, own]);
    } else {
      start = 12 * baseline;
      own = start + days * baseline;
      got = start + gained;
      values = [0, start, own, got];
    }
    var low = Math.min.apply(null, values), high = Math.max.apply(null, values), room = 8;
    function y(value) { return high === low ? 50 : 94 - (value - low) / (high - low) * (94 - room); }
    var from = real ? start - 12 * baseline : 0;
    var top = Math.max.apply(null, (real ? real.filter(function (n) { return n !== null; }) : [start, got]).concat([own]));
    var stacked = Math.abs(y(from) - y(top)) < 12;
    if (stacked) room = 24;
    function x(day) { return day / 14 * 100; }
    var box = figureOf("drawing", "Its own pace against what it gained");
    var plot = make("div", "drawing-plot");
    var svg = shape("svg", { viewBox: "0 0 100 100", preserveAspectRatio: "none", "aria-hidden": "true" });
    if (!real) svg.appendChild(shape("path", { "class": "floor", d: "M0 " + y(0) + "H100" }));
    svg.appendChild(shape("path", { "class": "mark-days", d: "M" + x(12) + " 0V100" }));
    var recent = real
      ? real.slice(12, end + 1).map(function (n, i) { return n === null ? null : [x(12 + i), y(n)]; }).filter(Boolean)
      : [[x(12), y(start)], [x(end), y(got)]];
    svg.appendChild(shape("path", { "class": "above", d: trace(recent) + "V" + y(own) + "Z" }));
    svg.appendChild(shape("path", { "class": "own", d: "M0 " + y(from) + (real ? "" : "L" + x(12) + " " + y(start)) + "L" + x(end) + " " + y(own) }));
    svg.appendChild(shape("path", { "class": "gained", d: real
      ? trace(real.map(function (n, day) { return n === null ? null : [x(day), y(n)]; }))
      : "M" + x(12) + " " + y(start) + "L" + x(end) + " " + y(got) }));
    svg.appendChild(shape("path", { "class": "ends", d: "M" + x(end) + " " + y(got) + "h0" }));
    plot.appendChild(svg);
    function label(className, text, left, top) {
      var tag = make("span", className, text);
      tag.style.left = left + "%";
      tag.style.top = top + "%";
      tag.setAttribute("aria-hidden", "true");
      plot.appendChild(tag);
    }
    label(stacked ? "tag got over" : "tag got", said[0], x(end), stacked ? Math.min(y(from), y(top)) : y(top));
    label("tag own", said[1], x(end), y(own));
    label("tag usual", said[2], 0, y(from));
    box.appendChild(plot);
    var axis = make("div", "drawing-axis");
    axis.setAttribute("aria-hidden", "true");
    axis.appendChild(make("span", "", "14 days before"));
    axis.appendChild(make("span", "", days === 1 ? "The day kept" : "The last 2 days"));
    box.appendChild(axis);
    box.appendChild(make("p", "drawing-note", real
      ? "Its stars, day by day, where a gap is a day with no count. The dashed line is its usual pace, carried on from its count before the recent days."
      : "Stars gained, added up. The file gives each window's average a day, not each day's count, so each run is a straight line."));
    box.appendChild(make("p", "sr", said[3]));
    return box;
  }

  {# Its total stars over the 31 days the file gives, as a line broken where a day has no count, with `words`, the
     first and last counts at its ends and its sentence for a screen reader. The file gives `words` only where two
     days or more have a count. #}
  function month(counts, words) {
    var known = counts.filter(function (n) { return n !== null; });
    var low = Math.min.apply(null, known), high = Math.max.apply(null, known);
    function y(value) { return high === low ? 50 : 92 - (value - low) / (high - low) * 84; }
    var box = figureOf("month-line", "Its stars over the last 30 days");
    var plot = make("div", "month-plot");
    var svg = shape("svg", { viewBox: "0 0 100 100", preserveAspectRatio: "none", "aria-hidden": "true" });
    svg.appendChild(shape("path", { "class": "stars", d: trace(counts.map(function (n, i) { return n === null ? null : [i / 30 * 100, y(n)]; })) }));
    plot.appendChild(svg);
    box.appendChild(plot);
    var axis = make("div", "run-axis");
    axis.setAttribute("aria-hidden", "true");
    axis.appendChild(make("span", "", words[0]));
    axis.appendChild(make("span", "", words[1]));
    box.appendChild(axis);
    box.appendChild(make("p", "sr", words[2]));
    return box;
  }

  function draw(row, data, opened) {
    var entry = data.rows[row.index];
    var days = data.days, dates = data.dates;
    var on = entry.on;
    var listed = {};
    on.forEach(function (e) { listed[e[0]] = e; });

    {# The sum behind its reason, under the reason line, and its facts, each a term and its value, and a loss's class. #}
    opened.querySelector(".rs").appendChild(make("p", "su", entry.sum));
    var facts = make("dl", "fa");
    opened.appendChild(facts);
    entry.facts.forEach(function (fact) {
      var pair = make("div");
      pair.appendChild(make("dt", "", fact[0]));
      pair.appendChild(make("dd", fact[2], fact[1]));
      facts.appendChild(pair);
    });

    if (entry.pace) opened.insertBefore(drawing(entry.pace, entry.said, entry.stars), facts);
    if (entry.month) {
      opened.classList.add("m");
      opened.appendChild(month(entry.stars, entry.month));
    }

    {# The running 30 board days, oldest first: a day a board listed it carries its rank that day and links to that
       board; the others are quiet. The table under it says the same in words, so the strip is hidden from readers. #}
    var run = figureOf("run", "Its rank on the last " + days.length + " board days");
    var strip = make("div", "run-days");
    strip.setAttribute("aria-hidden", "true");
    days.forEach(function (day, place) {
      var e = listed[place];
      var cell;
      if (e) {
        cell = make("a", e[1] <= 10 ? "on top" : "on", String(e[1]));
        cell.href = "/days/" + day + "/";
        cell.tabIndex = -1;
        cell.title = dates[place][1] + ": rank " + e[1];
      } else {
        cell = make("span", "", "");
        cell.title = dates[place][1] + ": not on the board";
      }
      strip.appendChild(cell);
    });
    run.appendChild(strip);
    var axis = make("div", "run-axis");
    axis.setAttribute("aria-hidden", "true");
    axis.appendChild(make("span", "", dates[0][0]));
    axis.appendChild(make("span", "", dates[dates.length - 1][0]));
    run.appendChild(axis);
    opened.appendChild(run);

    {# The boards it was on, newest first. On a phone the stylesheet stacks each board day, and draws over each
       figure its column's heading, which its cell carries in data-h (#27). So the table and each of its parts names
       its role, as the board's own do: some browsers stop telling assistive technology that a table whose display
       changes is a table. #}
    var list = role(make("table", "more-days"), "table");
    list.appendChild(make("caption", "part-title", "The boards it was on"));
    var names = ["Board day", "Rank", "Total stars", "Stars a day", "Multiple"];
    var head = role(role(list.createTHead(), "rowgroup").insertRow(), "row");
    names.forEach(function (name) {
      var th = role(make("th", "", name), "columnheader"); th.scope = "col"; head.appendChild(th);
    });
    var rowsBody = role(list.createTBody(), "rowgroup");
    on.slice().reverse().forEach(function (e) {
      var tr = role(rowsBody.insertRow(), "row");
      var th = role(make("th"), "rowheader"); th.scope = "row";
      var link = make("a", "", dates[e[0]][1]);
      link.href = "/days/" + days[e[0]] + "/";
      th.appendChild(link);
      tr.appendChild(th);
      var figures = [make("td", "num", String(e[1])), make("td", "num", e[2]), make("td", "num gain " + e[4], e[3]), make("td", "num", e[5])];
      figures.forEach(function (td, at) {
        td.setAttribute("data-h", names[at + 1]);
        tr.appendChild(role(td, "cell"));
      });
    });
    var wrap = make("div", "more-days-wrap");
    wrap.appendChild(list);
    opened.appendChild(wrap);
  }
  {# A row opens once its detail is drawn, or once the file has failed, never before: the browser's own opening is
     held back, and the row is opened here. #}
  function open(details) {
    if (details.getAttribute("data-drawn")) { details.open = true; return; }
    if (details.getAttribute("aria-busy")) return;
    details.setAttribute("aria-busy", "true");
    var row = rows.filter(function (r) { return r.element.contains(details); })[0];
    var opened = details.querySelector(".op");
    load().then(function (data) {
      var stale = opened.querySelector(".more-wait");
      if (stale) opened.removeChild(stale);
      draw(row, data, opened);
      details.setAttribute("data-drawn", "1");
    }, function () {
      if (!opened.querySelector(".more-wait")) {
        opened.appendChild(make("p", "more-wait", "The rest of this row could not be loaded."));
      }
    }).then(function () {
      details.removeAttribute("aria-busy");
      details.open = true;
    });
  }
  body.addEventListener("click", function (event) {
    var summary = event.target.closest("td.wy summary");
    if (!summary) return;
    var details = summary.parentNode;
    if (details.open) return;
    event.preventDefault();
    open(details);
  });

  {# A click anywhere on a row's own line opens or closes it, as its chevron does; a link, a control, or a click in
     what it opened keeps its own job, and so does selecting text. #}
  body.addEventListener("click", function (event) {
    var target = event.target;
    if (target.closest("a, summary, button, input, select, .op")) return;
    var selected = window.getSelection && String(window.getSelection());
    if (selected) return;
    var tr = target.closest("tr");
    var details = tr && tr.querySelector("td.wy details");
    if (details) { if (details.open) details.open = false; else open(details); }
  });
  table.classList.add("clickable");

  read();
  apply();
});
