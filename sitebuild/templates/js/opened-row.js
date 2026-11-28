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
    list.appendChild(make("caption", "part-title", "The boards it was on, of the last " + days.length));
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
    {# A repository also on boards older than those: how many, the first, and its best rank on any board, as the file
       words them, and where every board day is (#221). The part it is in scrolls sideways, and so cuts what falls
       outside it: the room under it keeps its link's focus ring whole, and is set here so that only a board with
       rows carries it. #}
    if (entry.before) {
      var before = make("p", "drawing-note", entry.before + " Every board day is in ");
      before.style.paddingBottom = "4px";
      var all = make("a", "", "History");
      all.href = "/days/";
      before.appendChild(all);
      before.appendChild(document.createTextNode("."));
      {# Progressive enhancement via the same-origin query service (/api/repo/, #242): only requested when a reader
         explicitly asks to expand boards older than the 30-day window. #}
      if (/^[A-Za-z0-9._-]+\/[A-Za-z0-9._-]+$/.test(row.name)) {
        var more = make("button", "more-before", "Show all earlier boards");
        more.type = "button";
        more.addEventListener("click", function () {
          more.disabled = true;
          more.textContent = "Loading earlier boards\u2026";
          fetch("/api/repo/" + row.name + "?format=json", { credentials: "same-origin" })
            .then(function (response) {
              if (!response.ok) throw new Error(response.status);
              return response.json();
            })
            .then(function (payload) {
              var repo = payload && payload.repository;
              var items = (repo && Array.isArray(repo.history) ? repo.history : []).filter(function (h) {
                return h && typeof h.board_day === "string" && /^\d{4}-\d{2}-\d{2}$/.test(h.board_day) && h.board_day < days[0];
              }).sort(function (a, b) { return a.board_day < b.board_day ? 1 : -1; });
              var prevErr = wrap.querySelector(".more-before-err");
              if (prevErr) wrap.removeChild(prevErr);
              if (items.length) {
                var ul = make("ul", "earlier-list");
                items.forEach(function (h) {
                  var li = make("li");
                  var link = make("a", "", h.board_day);
                  link.href = "/days/" + h.board_day + "/";
                  li.appendChild(link);
                  li.appendChild(document.createTextNode(" (#" + String(h.rank) + ")"));
                  ul.appendChild(li);
                });
                wrap.appendChild(ul);
              }
              if (more.parentNode) more.parentNode.removeChild(more);
            }, function () {
              more.disabled = false;
              more.textContent = "Try loading earlier boards again";
              if (!wrap.querySelector(".more-before-err")) {
                wrap.appendChild(make("p", "drawing-note more-before-err", "Earlier boards could not be loaded right now."));
              }
            });
        });
        before.appendChild(more);
      }
      wrap.appendChild(before);
    }
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
  {# Keep ?open= synced with whichever visible row is open via replaceState, using only the built row's own name
     so no untrusted query string is ever written back (P22, #238). #}
  body.addEventListener("toggle", function (event) {
    var details = event.target;
    if (!details || details.tagName !== "DETAILS") return;
    var row = rows.filter(function (r) { return r.element.contains(details); })[0];
    if (!row) return;
    if (details.open) {
      openedName = row.name;
      write(false);
    } else if (openedName === row.name) {
      var other = rows.filter(function (r) {
        var d = !r.element.hidden && r.element.querySelector("td.wy details");
        return d && d.open;
      });
      openedName = other.length ? other[other.length - 1].name : "";
      write(false);
    }
  }, true);
  {# Deep-link to a specific row via ?open=<owner>/<name>: match only against existing visible rows and silently
     ignore any unknown or hidden value (P22, #238). #}
  function openFromQuery(scroll) {
    var wanted = (new URLSearchParams(location.search).get("open") || "").trim().toLowerCase();
    if (!wanted) return;
    var match = rows.filter(function (r) { return r.name.toLowerCase() === wanted; })[0];
    if (!match || match.element.hidden) return;
    var details = match.element.querySelector("td.wy details");
    if (!details) return;
    open(details);
    if (scroll) match.element.scrollIntoView({ block: "center" });
  }
  table.classList.add("clickable");
