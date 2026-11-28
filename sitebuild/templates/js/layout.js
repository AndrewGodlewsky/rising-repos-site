{# The board's search, filters, order, and opened rows. Without this script the page is the whole board, by rank,
   and a row's chevron opens it on its reason line. It reads the page: each row's name, description, total stars,
   growth figure, and New mark from its own cells, and its language and how many of the last 14 boards listed it from
   its data- attributes. The All and New buttons count what the search and the other filters leave. When a reader
   first opens a row it fetches the board day's history.json from the site's own address, once, and opens the row
   only when the file is in, so its detail arrives in one step and nothing under it moves twice: the sum behind its
   reason, the drawing of its own pace against what it gained, its facts, its last 30 board days, and the boards it
   was on. If the file cannot be had, the row opens on its reason line and says the rest could not be loaded. It
   writes only text, elements, classes, and attributes, keeps the view in the address and the board's layout in this
   browser too, and a new order moves rows without renumbering one: each keeps the rank its file gives it. In the "Most
   often" order each row says after its name the count it is sorted by, from the two numbers the build wrote (#186).
   It waits for the page to be parsed, since it runs from the one script in the head, but for the board's layout. #}
{# The board's layout: the list, as the board has always been and the first view, or the cards, the same rows as boxes
   in a grid (#227). A reader who presses Cards keeps that choice in the address, as view=cards, which the links to
   other board days carry, and in this browser, under "layout", as the theme is kept, so that the board opens in the
   cards on their next visit. The address that asks for the cards wins, since it is a link someone chose to share.
   Only the word "cards" is read as the cards, and any other value is the list (P22). The root is marked here, before
   the board is parsed, so that the first frame drawn is the cards and never the list, and the stylesheet draws the
   cards from that mark alone, so that with scripts off the board is the list. A page loads, and Back and Forward
   come to a page, by the same reading, so this one function is shared by the mark below and the filters. #}
function laidAsCards() {
  if (new URLSearchParams(location.search).get("view") === "cards") return true;
  try { return localStorage.getItem("layout") === "cards"; } catch (error) { return false; }
}
if (laidAsCards()) document.documentElement.setAttribute("data-layout", "cards");
