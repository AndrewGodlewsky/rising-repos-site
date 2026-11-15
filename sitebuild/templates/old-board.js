// The notice of an old board: old-board.html and README.md's design note say what it does.
(function () {
  var notice = document.getElementById("old-board");
  var day = notice.getAttribute("data-newest-board-day");
  var published = notice.getAttribute("data-newest-published-at");
  // Only in the shape the page writes it, naming a real moment. Date.parse alone takes "2026-02-30" for 2 March,
  // and the round trip alone takes a year of six digits with no seconds.
  var time = Date.parse(published);
  if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$/.test(published) || isNaN(time) ||
    new Date(time).toISOString().slice(0, 19) + "Z" !== published) {
    return;
  }
  var hours = (Date.now() - time) / 3600000;
  if (!(hours >= 26)) return;
  var age = hours < 48 ? Math.floor(hours) + " hours" : Math.floor(hours / 24) + " days";
  var board = "It is the board for " + day + ".";
  var withheld = hours >= 7 * 24;
  document.getElementById("old-board-title").textContent = withheld
    ? "No board is shown: the newest is " + age + " old."
    : "The newest board is " + age + " old.";
  document.getElementById("old-board-text").textContent = withheld
    ? board + " When a week passes with no new board, the site stops showing its boards, so that an old ranking" +
      " is not taken for a current one."
    : board + " A board is due every day, and none has come out since.";
  notice.removeAttribute("hidden");
  if (withheld) document.documentElement.setAttribute("data-withheld", "");
})();
