//! PROTOTYPE, throw away: does a search over every repository ever on a board fit a Rust Worker? (#174)
//! The same search, list, and replies as the Python trial, so that the timings compare.

use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::OnceLock;
use worker::*;

static DATA: &str = include_str!("../repos.tsv");
static CALLS: AtomicU64 = AtomicU64::new(0);
static ROWS: OnceLock<Vec<Row>> = OnceLock::new();

struct Row {
    name: &'static str,
    language: &'static str,
    language_lower: String,
    stars: &'static str,
    day: &'static str,
    rank: u32,
    description: &'static str,
    hay: String,
}

/// Built once, on the first request an isolate serves: one row a repository, newest board day first, then better rank.
fn load() -> Vec<Row> {
    let mut rows: Vec<Row> = DATA
        .split('\n')
        .map(|line| {
            let mut field = line.split('\t');
            let name = field.next().unwrap_or("");
            let language = field.next().unwrap_or("");
            let stars = field.next().unwrap_or("");
            let day = field.next().unwrap_or("");
            let rank = field.next().unwrap_or("0").parse().unwrap_or(0);
            let description = field.next().unwrap_or("");
            Row {
                name,
                language,
                language_lower: language.to_lowercase(),
                stars,
                day,
                rank,
                description,
                hay: format!("{name} {description}").to_lowercase(),
            }
        })
        .collect();
    rows.sort_by(|a, b| b.day.cmp(a.day).then(a.rank.cmp(&b.rank)));
    rows
}

#[event(fetch)]
async fn fetch(req: Request, _env: Env, _ctx: Context) -> Result<Response> {
    let calls = CALLS.fetch_add(1, Ordering::Relaxed) + 1;
    let rows = ROWS.get_or_init(load);
    let url = req.url()?;
    let (mut words, mut language, mut page, mut ping) = (String::new(), String::new(), 1usize, false);
    for (key, value) in url.query_pairs() {
        match key.as_ref() {
            "q" => words = value.to_lowercase().chars().take(100).collect(),
            "lang" => language = value.to_lowercase(),
            "page" => page = value.parse().unwrap_or(1).max(1),
            "ping" => ping = true,
            _ => {}
        }
    }
    let headers = Headers::new();
    headers.set("x-calls", &calls.to_string())?;
    headers.set("x-rows", &rows.len().to_string())?;
    if ping {
        return Ok(Response::ok("pong\n")?.with_headers(headers));
    }
    let words: Vec<&str> = words.split_whitespace().collect();
    let hits: Vec<&Row> = rows
        .iter()
        .filter(|row| words.iter().all(|word| row.hay.contains(word)) && (language.is_empty() || row.language_lower == language))
        .collect();
    let mut body = format!("{} match; page {}.\n", hits.len(), page);
    for row in hits.iter().skip((page - 1) * 20).take(20) {
        let language = if row.language.is_empty() { "no language" } else { row.language };
        body.push_str(&format!("{} | {} | stars {} | last on {} at #{} | \"{}\"\n", row.name, language, row.stars, row.day, row.rank, row.description));
    }
    Ok(Response::ok(body)?.with_headers(headers))
}
