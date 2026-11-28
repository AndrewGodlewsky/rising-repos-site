/* PROTOTYPE ONLY: three designs of a card view for a board's rows, switched by the bar at the foot or the arrow keys.
   The design and the view are kept in the address's hash, since the page's own filters own its query. */
document.addEventListener("DOMContentLoaded", function () {
  var DESIGNS = [
    { key: "A", name: "Grid", note: "Cards three across on a wide screen, two at 768 px, one on a phone. The switch sits in the filter row. Opening a card widens it to the whole line." },
    { key: "B", name: "Tiles", note: "Small tiles, the figures first, five or six across. The switch sits in the day bar, so it stays in reach as you scroll. A tile opens its row in the list." },
    { key: "C", name: "Feature cards", note: "Two wide cards across, the whole description and the reason always in view. The switch is a pair of tabs above the filter. A card opens where it is." }
  ];
  var ICONS = {
    list: '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true"><path d="M2 4h12M2 8h12M2 12h12"/></svg>',
    cards: '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true"><rect x="2" y="2" width="5" height="5" rx="1"/><rect x="9" y="2" width="5" height="5" rx="1"/><rect x="2" y="9" width="5" height="5" rx="1"/><rect x="9" y="9" width="5" height="5" rx="1"/></svg>'
  };
  var table = document.querySelector("table.chart");
  if (!table) return;
  var body = table.tBodies[0];
  var root = document.documentElement;
  var state = { design: "A", view: "cards" };

  function readHash() {
    var hash = new URLSearchParams(location.hash.slice(1));
    if (!hash.has("design") && !hash.has("view")) return false;
    var key = (hash.get("design") || "A").toUpperCase();
    if (DESIGNS.some(function (d) { return d.key === key; })) state.design = key;
    state.view = hash.get("view") === "list" ? "list" : "cards";
    return true;
  }
  function writeHash() {
    history.replaceState(history.state, "", location.pathname + location.search + "#design=" + state.design + "&view=" + state.view);
  }

  /* Design C shows each row's reason line in its card. The real page would show the line it already holds. */
  [].forEach.call(body.rows, function (tr) {
    var line = tr.querySelector(".rs .ln");
    var cell = document.createElement("td");
    cell.className = "proto-rs";
    cell.setAttribute("role", "cell");
    cell.textContent = line ? line.textContent : "";
    tr.appendChild(cell);
  });

  function group(className, icons) {
    var box = document.createElement("div");
    box.className = className;
    box.setAttribute("role", "group");
    box.setAttribute("aria-label", "View");
    ["list", "cards"].forEach(function (view) {
      var button = document.createElement("button");
      button.type = "button";
      button.setAttribute("data-view", view);
      var word = view === "list" ? "List" : "Cards";
      if (icons) { button.innerHTML = ICONS[view]; button.setAttribute("aria-label", word); button.title = word; }
      else button.textContent = word;
      button.addEventListener("click", function () { state.view = view; apply(); });
      box.appendChild(button);
    });
    return box;
  }
  function placeSwitch() {
    [].forEach.call(document.querySelectorAll(".proto-view"), function (node) { node.remove(); });
    var toolbar = document.querySelector(".board .toolbar");
    if (state.design === "A") toolbar.appendChild(group("segments proto-view proto-a", false));
    else if (state.design === "B") {
      document.querySelector(".strip .wrap").appendChild(group("segments proto-view proto-b in-strip", true));
      toolbar.appendChild(group("segments proto-view proto-b in-toolbar", true));
    } else toolbar.parentNode.insertBefore(group("proto-view proto-tabs", false), toolbar);
  }

  var bar = document.createElement("div");
  bar.className = "proto-bar";
  bar.innerHTML = '<button type="button" class="proto-prev" aria-label="Previous design">&#8249;</button><div class="proto-mid"><div class="proto-label"></div><div class="proto-note"></div><div class="proto-state"></div></div><button type="button" class="proto-next" aria-label="Next design">&#8250;</button>';
  document.body.appendChild(bar);
  bar.querySelector(".proto-prev").addEventListener("click", function () { cycle(-1); });
  bar.querySelector(".proto-next").addEventListener("click", function () { cycle(1); });

  function renderBar() {
    var design = DESIGNS.filter(function (d) { return d.key === state.design; })[0];
    var label = bar.querySelector(".proto-label");
    label.textContent = "Design " + design.key + " of 3: " + design.name;
    var small = document.createElement("small");
    small.textContent = "PROTOTYPE · ← → to switch";
    label.appendChild(small);
    bar.querySelector(".proto-note").textContent = design.note;
    var shown = [].filter.call(body.rows, function (tr) { return !tr.hidden; }).length;
    var opened = body.querySelector("details[open]");
    var name = opened ? opened.closest("tr").querySelector(".re a").textContent : "none";
    bar.querySelector(".proto-state").textContent = "view: " + state.view + " · showing " + shown + " of " + body.rows.length + " · opened: " + name + " · address: " + (location.search || "") + location.hash;
  }
  function apply() {
    root.setAttribute("data-proto", state.design);
    table.classList.toggle("cards", state.view === "cards");
    [].forEach.call(document.querySelectorAll(".proto-view button"), function (button) {
      button.setAttribute("aria-pressed", String(button.getAttribute("data-view") === state.view));
    });
    writeHash();
    renderBar();
  }
  function cycle(step) {
    var at = DESIGNS.map(function (d) { return d.key; }).indexOf(state.design);
    state.design = DESIGNS[(at + step + DESIGNS.length) % DESIGNS.length].key;
    placeSwitch();
    apply();
  }

  /* Design B: a tile opens its row in the list, scrolled to and opened, as the chevron would open it there. */
  document.addEventListener("click", function (event) {
    if (state.design !== "B" || !table.classList.contains("cards")) return;
    var tr = event.target.closest("tbody tr");
    if (!tr || !body.contains(tr) || event.target.closest("a")) return;
    event.preventDefault();
    event.stopPropagation();
    state.view = "list";
    apply();
    var summary = tr.querySelector("td.wy summary");
    if (summary && !summary.parentNode.open) summary.click();
    tr.scrollIntoView({ block: "start" });
    tr.classList.add("flash");
    setTimeout(function () { tr.classList.remove("flash"); }, 1200);
  }, true);

  document.addEventListener("keydown", function (event) {
    if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
    if (event.altKey || event.ctrlKey || event.metaKey) return;
    if (event.target.closest && event.target.closest("input, textarea, select, [contenteditable]")) return;
    cycle(event.key === "ArrowLeft" ? -1 : 1);
  });
  ["click", "input", "change"].forEach(function (kind) {
    document.addEventListener(kind, function () { setTimeout(renderBar, 0); });
  });
  table.addEventListener("toggle", function () { setTimeout(renderBar, 0); }, true);
  window.addEventListener("popstate", function () { setTimeout(renderBar, 0); });
  window.addEventListener("hashchange", function () { if (readHash()) { placeSwitch(); apply(); } });

  readHash();
  placeSwitch();
  apply();
});
