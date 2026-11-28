{# The page's one script: written in the page and allowed by the hash of its text, which
   page.html works out. It runs in the head, so the reader's theme is set before the first paint. Each page carries
   only the parts it uses: every page the theme; the pages with the notice of an old board, the notice; a board's
   page, its filters; the Baseline page, its readout; and How it works, its examples (#214). #}
{% include "theme.js" %}
{% if notice %}
{% include "old-board.js" %}
{% endif %}
{% if filtering and board.rows %}
{% include "filters.js" %}
{% endif %}
{% if template == "baseline.html" and chart %}
{% include "baseline.js" %}
{% endif %}
{% if template == "how-it-works.html" %}
{% include "how-it-works.js" %}
{% endif %}
{% if template == "search.html" %}
{% include "search.js" %}
{% endif %}
