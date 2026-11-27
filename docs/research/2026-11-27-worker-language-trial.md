# Which language the query service is written in: a trial of four

**Date:** 27 November 2026. Ticket: #174, under the map #151. Decided by the owner: **Rust**.

The query service (#157, #173) searches every repository that has been on a board, and Cloudflare's Free plan gives a
Worker 10 ms of CPU for each request. #172 left open whether a Python Worker fits. The owner asked for Rust and then Go
to be tried as well, so the same search was written four times, in Python, Rust, JavaScript, and Go, and run side by
side on one machine.

## 1. Short answer

| | Rust | Go | JavaScript | Python |
| --- | ---: | ---: | ---: | ---: |
| A request that searches nothing | 5.2 ms | 258.6 ms | 5.2 ms | 6.1 ms |
| A search's cost above that, at its worst | +1.8 ms | (below the noise of the 250 ms) | +2.6 ms | +5.9 ms |
| That worst, as a share of the 10 ms | 18% | far over | 26% | 59% |
| The Worker's size | 2,132,240 bytes of WebAssembly | 7,475,718 bytes of WebAssembly | 1,737,319 bytes of list and a short script | 1,761.70 KiB of module, and the Python runtime |
| Third-party code | 82 crates in `Cargo.lock` | 2 modules | none | none |
| Keeps the list between requests | yes | no: starts again on every request | yes | yes |

- **Rust is the fastest**, about twice JavaScript's speed for this search and four to five times Python's.
- **Go starts again on every request.** Its request counter read 1 every time, so each request paid about 250 ms to
  start Go's runtime and read the list again. That is how standard Go runs as WebAssembly through `syumai/workers`, the
  community library it needs; Cloudflare supports Go only through WebAssembly. TinyGo was not tried.
- **Python fits, with little room.** A word index made its searches cost about 1 ms, but building the index took
  3.4 s at start, past the 1 s Cloudflare allows, unless the memory snapshot taken at deploy absorbs it, which no page
  of Cloudflare's says.
- All four gave the same count, 132 matches for "pdf", led by the same row.

The owner chose Rust, for its speed and its room to grow, over JavaScript's smaller toolchain and lack of third-party
code.

## 2. How it was measured

Each Worker held the same list, 10,987 repositories from 120 board days, one line each, and answered
`?q=<words>&lang=<language>&page=<n>` with the same 20-line page, or `?ping=1` with nothing searched. Each ran under
`wrangler dev` at wrangler 4.155.0, the version the deploy workflow pins, with the compatibility date 2026-10-30, the
newest its runtime knew. The requests went to the four in turn, 30 times for each search, so that the machine's noise
fell on all four alike; each figure above is a median, less the same Worker's median for `?ping=1`.

The figures are wall-clock times on one Windows machine, through wrangler's local proxy. They are a guide to
Cloudflare's CPU accounting and not a measure of it, and a first request's time locally does not show a cold start on
Cloudflare, since each language starts differently there.

## 3. What each needed

- **Rust:** the `worker` crate 0.9.0 and `worker-build` 0.9.0, which compiles from source and downloads wasm-bindgen
  0.2.130, wasm-opt 133, and esbuild 0.28.2 at build time. On this Windows machine the GNU toolchain could not build
  `worker-build` (`dlltool.exe` not found); the MSVC toolchain, with Visual Studio's build tools, built it and the
  Worker. Git's own `link.exe` was kept off the path, as it shadows Microsoft's linker.
- **Go:** Go 1.27.4, `github.com/syumai/workers` and `github.com/syumai/workers-go` 0.36.0, whose generator writes a
  JavaScript loader, built with `GOOS=js GOARCH=wasm`.
- **JavaScript:** nothing beyond wrangler; the list is a text module.
- **Python:** `pywrangler`, Cloudflare's tool, needed uv 0.13.4 or newer, where the repository pins 0.11.6, and then
  failed on Windows when it made its Pyodide environment. Plain wrangler ran the Worker once the compatibility flag
  `disable_python_external_sdk` was set.

## 4. The trials

The four Workers, the scripts that write their list, and the Rust lock file, in
`docs/research/2026-11-27-worker-language-trial/`. Their lists and build output are left out, being made from
`site-data/` and by the build.
