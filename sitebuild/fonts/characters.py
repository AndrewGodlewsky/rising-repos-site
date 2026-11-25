"""The characters the site's two faces hold, which `subset.py` beside this file cuts them to.

It is a file of its own, which imports nothing, so that a test can read the list as `subset.py` does (#102).
`subset.py` needs fontTools, which neither the build nor the tests install, so a test that imported the list from
it failed, and the first one to need it read the script's text instead.
"""

# Beyond ASCII: no-break space, middle dot, », ×, ÷, en dash, em dash, ellipsis, ‹, ›, the up arrow, and the minus
# sign, which a loss is written with, as wide as the plus and the figures.
CHARACTERS = "U+0020-007E,U+00A0,U+00B7,U+00BB,U+00D7,U+00F7,U+2013,U+2014,U+2026,U+2039,U+203A,U+2191,U+2212"
