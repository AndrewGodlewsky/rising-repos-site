# The type is a renamed cut of IBM Plex, inside the page

The site is set in IBM Plex Sans and IBM Plex Mono, cut down to the characters
its own text uses, so that the four faces fit inside every page
([0004](0004-a-page-holds-everything-it-needs.md)). The SIL Open Font License
counts a cut as a modified version and reserves the name "Plex" to the
original. So the files here are named Rising Sans and Rising Mono, and no
record inside them holds the old name.

## Status

Accepted, at the redesign (RisingRepos#199).

## Consequences

- A font file is committed only under a `rising-` name, made by
  `sitebuild/fonts/subset.py`, whose docstring gives the licence's terms.
- A character the site's own text newly uses, outside the set that script
  names, is drawn in the fallback face until the faces are cut again, and a
  larger cut adds bytes to every page. No test finds such a character.
- Text a repository's owner wrote, in any script, falls back to the reader's
  own faces.
- The licence is published with the site, and How it works names the type and
  links to it.

## Confirmed by

`tests/test_build.py::TheType::test_each_page_holds_the_four_faces_as_data_and_no_font_file_is_published`
and
`tests/test_build.py::TheType::test_the_licence_is_published_as_the_fonts_carry_it_and_how_it_works_names_the_type_and_links_to_it`.
No test reads the names inside the font files: the script that makes them
checks for the old name when it runs, and the reviewer holds the rest
(STANDARDS.md, C15).
