// Time an in-memory scan of the compact list, as a proxy for a Worker.
// Usage: node scan.mjs <all.tsv>
// A local Node timing is not Cloudflare's: a Worker's CPU time is metered on its
// own runtime and hardware. This shows only the order of magnitude.
// Wall-clock time of a single-threaded, CPU-bound call stands for its CPU time, because
// process.cpuUsage() on Windows ticks only every 15.6 ms.
import { readFileSync } from "node:fs";

const text = readFileSync(process.argv[2], "utf8");
const pdf = /pdf/i;
const words = ["pdf", "pars", "extract"];

function timeMs(fn, n) {
  fn();
  const t = [];
  for (let i = 0; i < n; i++) {
    const s = performance.now();
    fn();
    const d = performance.now() - s;
    t.push(d);
  }
  t.sort((a, b) => a - b);
  return { median_ms: +t[n >> 1].toFixed(3), p95_ms: +t[Math.floor(n * 0.95)].toFixed(3) };
}

// Cold request: parse the text into rows, then scan.
const cold = () => {
  const rows = text.split("\n").filter(Boolean).map((l) => l.split("\t"));
  return rows.filter((r) => pdf.test(r[0] + " " + r[5]));
};
// Warm request: rows already parsed and kept in the isolate's memory.
const rows = text.split("\n").filter(Boolean).map((l) => l.split("\t"));
const warmRegex = () => rows.filter((r) => pdf.test(r[0] + " " + r[5]));
// Warm, three terms that must all appear, case-folded, on a prepared lower-case haystack.
const hay = rows.map((r) => (r[0] + " " + r[5]).toLowerCase());
const warmAll = () => {
  const out = [];
  for (let i = 0; i < hay.length; i++) if (words.every((w) => hay[i].includes(w))) out.push(rows[i]);
  return out;
};
// Warm, ranked by stars and cut to 20.
const warmTop = () => warmRegex().sort((a, b) => b[2] - a[2]).slice(0, 20);

const mem0 = process.memoryUsage();
console.log(
  JSON.stringify(
    {
      rows: rows.length,
      text_bytes: Buffer.byteLength(text),
      matches_pdf: warmRegex().length,
      matches_pdf_pars_extract: warmAll().length,
      cold_parse_and_scan: timeMs(cold, 100),
      warm_regex_scan: timeMs(warmRegex, 300),
      warm_includes_scan_3_terms: timeMs(warmAll, 300),
      warm_scan_sort_top20: timeMs(warmTop, 300),
      heap_used_mb: +(mem0.heapUsed / 1048576).toFixed(1),
      rss_mb: +(mem0.rss / 1048576).toFixed(1),
    },
    null,
    1,
  ),
);
