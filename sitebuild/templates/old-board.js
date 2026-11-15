// The notice of an old board: old-board.html and README.md's design note say what it does.
(function () {
  var MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
    "November", "December"];
  var notice = document.getElementById("old-board");
  var day = notice.getAttribute("data-newest-board-day");
  var published = notice.getAttribute("data-newest-published-at");
  // Each only in the shape the page writes it, naming a real day and moment.
  if (!/^\d{4}-\d{2}-\d{2}$/.test(day) || iso(day + "T00:00:00Z").slice(0, 10) !== day) return;
  if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$/.test(published) || iso(published).slice(0, 19) + "Z" !== published) {
    return;
  }
  var hours = (Date.now() - Date.parse(published)) / 3600000;
  if (!(hours >= 26)) return;
  var age = hours < 48 ? Math.floor(hours) + " hours" : Math.floor(hours / 24) + " days";
  var board = "It is the board for " + Number(day.slice(8)) + " " + MONTHS[Number(day.slice(5, 7)) - 1] + " " +
    day.slice(0, 4) + ".";
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

  // The moment as ISO 8601 in UTC, or "" for none.
  function iso(text) {
    var time = Date.parse(text);
    return isNaN(time) ? "" : new Date(time).toISOString();
  }
})();
