  var table = document.querySelector("table.chart");
  var q = document.getElementById("q");
  {# The day bar's search box, which is drawn from 768 px up in the place of the filter's, which a phone draws. The two
     hold the same words, so that the box a reader sees is the search at whatever width the window has (#213). #}
  var bar = document.getElementById("day-q");
  function say(words) { [q, bar].forEach(function (box) { if (box && box.value !== words) box.value = words; }); }
  var kinds = document.getElementById("kinds");
  var bands = document.getElementById("bands");
  var language = document.getElementById("language");
  var sort = document.getElementById("sort");
  var shown = document.getElementById("shown");
  var none = document.getElementById("none-shown");
  var root = document.documentElement;
  var layoutButtons = [].slice.call(document.querySelectorAll("#layout button"));
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
  {# How many boards the "Most often" order counted, which the build writes on the table: 14, or fewer on the site's
     first board days (#186). #}
  var boardsCounted = Number(table.getAttribute("data-w"));
  var countsMade = false;
  var kindButtons = [].slice.call(kinds.querySelectorAll("button"));
  var bandButtons = [].slice.call(bands.querySelectorAll("button"));
  var kind = "";
  var band = "";
  {# The order the table's rows currently sit in, starting in rank order as built (#244). #}
  var currentOrder = "rank";
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
    {# In the "Most often" order each row says the count it is sorted by, after its name and its New mark (#186). The
       counts are made the first time the order is chosen, for every row, so that a row a filter shows later has its
       own, and the table's class shows them in that order alone. The space keeps the count a word apart. #}
    var often = sort.value === "often";
    if (often && !countsMade) {
      countsMade = true;
      rows.forEach(function (row) {
        var head = row.element.querySelector("th.re");
        head.appendChild(document.createTextNode(" "));
        head.appendChild(make("span", "often",
          "on " + row.often + " of " + boardsCounted + (boardsCounted === 1 ? " board" : " boards")));
      });
    }
    table.classList.toggle("by-often", often);
    {# Only re-sort and re-attach rows when the order actually changes, so typing in the search box or toggling
       filters does not detach and re-insert every row in the table body (#244). #}
    var wanted = orders.hasOwnProperty(sort.value) ? sort.value : "rank";
    if (wanted !== currentOrder) {
      currentOrder = wanted;
      var order = orders[wanted];
      var fragment = document.createDocumentFragment();
      rows.slice().sort(function (a, b) { return order(a, b) || a.index - b.index; })
        .forEach(function (row) { fragment.appendChild(row.element); });
      body.appendChild(fragment);
    }
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
  {# Lay the board out as the cards or as the list: the root's mark, which the stylesheet draws from, and the switch's
     pressed button. #}
  function lay(cards) {
    if (cards) root.setAttribute("data-layout", "cards"); else root.removeAttribute("data-layout");
    press(layoutButtons, "data-layout", cards ? "cards" : "");
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
    say(query.get("q") || "");
    press(kindButtons, "data-kind", kind);
    press(bandButtons, "data-band", band);
    lay(laidAsCards());
  }
  {# The query of the filters and the order, each left out at its default: one function for the address and the
     links alike, so that they cannot disagree (C17). #}
  function view() {
    var query = new URLSearchParams();
    if (kind) query.set("show", kind);
    if (band !== "") query.set("band", bandWords[band]);
    if (language.value) query.set("lang", language.value);
    if (sort.value !== "rank") query.set("sort", sort.value);
    if (root.getAttribute("data-layout") === "cards") query.set("view", "cards");
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
  [q, bar].forEach(function (box) {
    if (box) box.addEventListener("input", function () { say(box.value); var started = !new URLSearchParams(location.search).get("q"); apply(); write(started); });
  });
  language.addEventListener("change", function () { apply(); write(true); });
  {# A press of the switch keeps the choice in this browser, or clears it for the list, as a press back to the
     browser's own theme does, so that a browser keeps nothing for a reader on the first view. It replaces the address's
     entry in the history and adds none: with a new entry, Back to the plain address would read the kept cards again,
     and seem to do nothing. #}
  layoutButtons.forEach(function (button) {
    button.addEventListener("click", function () {
      var cards = button.getAttribute("data-layout") === "cards";
      try { if (cards) localStorage.setItem("layout", "cards"); else localStorage.removeItem("layout"); } catch (error) {}
      lay(cards);
      apply();
      write(false);
    });
  });
  sort.addEventListener("change", function () { apply(); write(true); });
  window.addEventListener("popstate", function () { read(); apply(); });
  {# Clear search and filters: the whole board again, in the order chosen, as a new entry that Back leaves. The
     button hides with its line, so the keyboard goes to the All button, the first of the filter's controls, rather
     than to the search, which would open a phone's keyboard (#33). #}
  if (none) none.lastElementChild.addEventListener("click", function () {
    kind = band = language.value = "";
    say("");
    press(kindButtons, "data-kind", kind);
    press(bandButtons, "data-band", band);
    apply();
    write(true);
    kindButtons[0].focus();
  });
