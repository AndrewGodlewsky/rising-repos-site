{# Archive search client for /search/ (#242): sends no request until the reader submits a query or opens a shared
   search address with query parameters, and renders every owner-written field through textContent alone (P5, P6). #}
document.addEventListener("DOMContentLoaded", function () {
  var form = document.getElementById("archive-search");
  var q = document.getElementById("archive-q");
  var lang = document.getElementById("archive-lang");
  var since = document.getElementById("archive-since");
  var status = document.getElementById("archive-status");
  var results = document.getElementById("archive-results");
  var pager = document.getElementById("archive-pager");
  if (!form || !q || !lang || !since || !status || !results || !pager) return;
  var REPO_NAME = /^[A-Za-z0-9._-]+\/[A-Za-z0-9._-]+$/;
  var ISO_DAY = /^\d{4}-\d{2}-\d{2}$/;
  var token = 0;

  function make(tag, className, text) {
    var element = document.createElement(tag);
    if (className) element.className = className;
    if (text !== undefined) element.textContent = text;
    return element;
  }

  function clear(node) {
    while (node.firstChild) node.removeChild(node.firstChild);
  }

  function currentParams(page) {
    var params = new URLSearchParams();
    var words = q.value.trim();
    if (words) params.set("q", words);
    if (lang.value) params.set("lang", lang.value);
    if (since.value) params.set("since", since.value);
    if (page && page > 1) params.set("page", String(page));
    return params;
  }

  function render(data, page) {
    clear(results);
    clear(pager);
    pager.hidden = true;
    var items = data && Array.isArray(data.repositories) ? data.repositories : [];
    var matches = typeof data.matches === "number" ? data.matches : items.length;
    var totalPages = typeof data.pages === "number" ? data.pages : 1;
    var shownPage = typeof data.page === "number" ? data.page : page;
    if (!items.length) {
      status.textContent = "No repository in the archive matches that search.";
      return;
    }
    status.textContent = matches === 1
      ? "1 repository matched."
      : matches.toLocaleString("en-US") + " repositories matched (page " + shownPage + " of " + totalPages + ").";
    var fragment = document.createDocumentFragment();
    items.forEach(function (repo) {
      var li = make("li", "search-item");
      var top = make("div", "search-item-head");
      var fullName = typeof repo.full_name === "string" ? repo.full_name : "";
      if (REPO_NAME.test(fullName)) {
        var link = make("a", "search-name", fullName);
        link.href = "https://github.com/" + fullName;
        link.target = "_blank";
        link.title = "Opens on GitHub";
        top.appendChild(link);
      } else {
        top.appendChild(make("span", "search-name", fullName));
      }
      var meta = make("div", "search-meta");
      if (typeof repo.language === "string" && repo.language) {
        meta.appendChild(make("span", "search-lang", repo.language));
      }
      if (typeof repo.stars === "number") {
        meta.appendChild(make("span", "num", repo.stars.toLocaleString("en-US") + " stars"));
      }
      if (typeof repo.last_board_day === "string" && ISO_DAY.test(repo.last_board_day)) {
        var seen = make("span", "search-seen", "Last on ");
        var dayLink = make("a", "", repo.last_board_day);
        dayLink.href = "/days/" + repo.last_board_day + "/";
        seen.appendChild(dayLink);
        if (typeof repo.last_rank === "number") {
          seen.appendChild(document.createTextNode(", rank " + repo.last_rank));
        }
        meta.appendChild(seen);
      }
      top.appendChild(meta);
      li.appendChild(top);
      var descText = typeof repo.description === "string" && repo.description.trim() ? repo.description : "";
      var desc = make("p", descText ? "search-desc" : "search-desc none", descText || "No description");
      if (descText) desc.dir = "auto";
      li.appendChild(desc);
      fragment.appendChild(li);
    });
    results.appendChild(fragment);

    if (totalPages > 1) {
      var prev = make("button", "search-page", "Previous");
      prev.type = "button";
      prev.disabled = shownPage <= 1;
      prev.addEventListener("click", function () { run(shownPage - 1, true); });
      var info = make("span", "search-page-info", "Page " + shownPage + " of " + totalPages);
      var next = make("button", "search-page", "Next");
      next.type = "button";
      next.disabled = shownPage >= totalPages;
      next.addEventListener("click", function () { run(shownPage + 1, true); });
      pager.appendChild(prev);
      pager.appendChild(info);
      pager.appendChild(next);
      pager.hidden = false;
    }
  }

  function run(page, updateUrl) {
    var params = currentParams(page);
    if (!params.get("q") && !params.get("lang") && !params.get("since")) {
      clear(results);
      clear(pager);
      pager.hidden = true;
      status.textContent = "Enter words or choose a language, then press Search.";
      if (updateUrl && location.search) window.history.replaceState(null, "", location.pathname);
      return;
    }
    if (updateUrl) {
      var nextSearch = "?" + params.toString();
      if (nextSearch !== location.search) {
        window.history.replaceState(null, "", location.pathname + nextSearch);
      }
    }
    var apiParams = new URLSearchParams(params.toString());
    apiParams.set("format", "json");
    var id = ++token;
    status.textContent = "Searching the archive\u2026";
    fetch("/api/search?" + apiParams.toString(), { credentials: "same-origin" })
      .then(function (response) {
        if (!response.ok) throw new Error(response.status);
        return response.json();
      })
      .then(function (data) {
        if (id !== token) return;
        render(data, page);
      }, function () {
        if (id !== token) return;
        clear(results);
        clear(pager);
        pager.hidden = true;
        status.textContent = "The search service could not be reached right now. Every board day is still in History.";
      });
  }

  form.addEventListener("submit", function (event) {
    event.preventDefault();
    run(1, true);
  });

  var initial = new URLSearchParams(location.search);
  var initQ = initial.get("q") || "";
  var initLang = (initial.get("lang") || "").toLowerCase();
  var initSince = initial.get("since") || "";
  var initPage = Math.max(1, parseInt(initial.get("page") || "1", 10) || 1);
  q.value = initQ;
  [].forEach.call(lang.options, function (opt) { if (opt.value && opt.value.toLowerCase() === initLang) lang.value = opt.value; });
  [].forEach.call(since.options, function (opt) { if (opt.value && opt.value === initSince) since.value = opt.value; });
  if (q.value.trim() || lang.value || since.value) {
    run(initPage, false);
  }
});
