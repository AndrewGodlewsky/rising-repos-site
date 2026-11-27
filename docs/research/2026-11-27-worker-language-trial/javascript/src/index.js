// PROTOTYPE, throw away: does a search over every repository ever on a board fit a plain JavaScript Worker? (#174)
// The same search, list, and replies as the Python and Rust trials, so that the timings compare. No packages.
import DATA from "../repos.tsv";

// Built once, when the isolate starts: one row a repository, newest board day first, then better rank.
const ROWS = DATA.split("\n").map((line) => {
  const [name, language, stars, day, rank, description] = line.split("\t");
  return { name, language, languageLower: language.toLowerCase(), stars, day, rank: Number(rank), description, hay: `${name} ${description}`.toLowerCase() };
});
ROWS.sort((a, b) => (a.day < b.day ? 1 : a.day > b.day ? -1 : a.rank - b.rank));
let CALLS = 0;

export default {
  async fetch(request) {
    CALLS += 1;
    const query = new URL(request.url).searchParams;
    const headers = { "x-calls": String(CALLS), "x-rows": String(ROWS.length) };
    if (query.has("ping")) return new Response("pong\n", { headers });
    const words = (query.get("q") || "").toLowerCase().slice(0, 100).split(/\s+/).filter(Boolean);
    const language = (query.get("lang") || "").toLowerCase();
    const page = Math.max(1, Number(query.get("page")) || 1);
    const hits = ROWS.filter((row) => words.every((word) => row.hay.includes(word)) && (!language || row.languageLower === language));
    const lines = [`${hits.length} match; page ${page}.`];
    for (const row of hits.slice((page - 1) * 20, page * 20)) {
      lines.push(`${row.name} | ${row.language || "no language"} | stars ${row.stars} | last on ${row.day} at #${row.rank} | "${row.description}"`);
    }
    return new Response(lines.join("\n") + "\n", { headers });
  },
};
