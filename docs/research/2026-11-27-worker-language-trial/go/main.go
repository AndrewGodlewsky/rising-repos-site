// PROTOTYPE, throw away: does a search over every repository ever on a board fit a Go Worker? (#174)
// The same search, list, and replies as the Rust, JavaScript, and Python trials, so that the timings compare.
package main

import (
	_ "embed"
	"fmt"
	"net/http"
	"sort"
	"strconv"
	"strings"
	"sync"
	"sync/atomic"

	"github.com/syumai/workers"
)

//go:embed repos.tsv
var data string

type row struct {
	name, language, languageLower, stars, day, description, hay string
	rank                                                        int
}

var (
	rows  []row
	once  sync.Once
	calls atomic.Int64
)

// load builds the rows once, on the first request an isolate serves: newest board day first, then better rank.
func load() {
	for _, line := range strings.Split(data, "\n") {
		f := strings.Split(line, "\t")
		if len(f) < 6 {
			continue
		}
		rank, _ := strconv.Atoi(f[4])
		rows = append(rows, row{
			name: f[0], language: f[1], languageLower: strings.ToLower(f[1]), stars: f[2], day: f[3],
			rank: rank, description: f[5], hay: strings.ToLower(f[0] + " " + f[5]),
		})
	}
	sort.SliceStable(rows, func(i, j int) bool {
		if rows[i].day != rows[j].day {
			return rows[i].day > rows[j].day
		}
		return rows[i].rank < rows[j].rank
	})
}

func handler(w http.ResponseWriter, r *http.Request) {
	n := calls.Add(1)
	once.Do(load)
	w.Header().Set("x-calls", strconv.FormatInt(n, 10))
	w.Header().Set("x-rows", strconv.Itoa(len(rows)))
	query := r.URL.Query()
	if query.Has("ping") {
		fmt.Fprint(w, "pong\n")
		return
	}
	q := []rune(strings.ToLower(query.Get("q")))
	if len(q) > 100 {
		q = q[:100]
	}
	words := strings.Fields(string(q))
	language := strings.ToLower(query.Get("lang"))
	page, err := strconv.Atoi(query.Get("page"))
	if err != nil || page < 1 {
		page = 1
	}
	var hits []*row
	for i := range rows {
		matches := language == "" || rows[i].languageLower == language
		for _, word := range words {
			if !matches {
				break
			}
			matches = strings.Contains(rows[i].hay, word)
		}
		if matches {
			hits = append(hits, &rows[i])
		}
	}
	var b strings.Builder
	fmt.Fprintf(&b, "%d match; page %d.\n", len(hits), page)
	for i := (page - 1) * 20; i < len(hits) && i < page*20; i++ {
		lang := hits[i].language
		if lang == "" {
			lang = "no language"
		}
		fmt.Fprintf(&b, "%s | %s | stars %s | last on %s at #%d | \"%s\"\n", hits[i].name, lang, hits[i].stars, hits[i].day, hits[i].rank, hits[i].description)
	}
	fmt.Fprint(w, b.String())
}

func main() {
	workers.Serve(http.HandlerFunc(handler))
}
