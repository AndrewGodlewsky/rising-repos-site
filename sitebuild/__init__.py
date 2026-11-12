"""The site's generator: renders the Jinja2 templates into static pages."""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

TEMPLATES = Path(__file__).parent / "templates"


def build(out: Path, *, noindex: bool) -> None:
    """Write every page into `out`, a folder that does not exist yet or is empty.

    With `noindex`, every page asks search engines not to index it.
    """
    if out.exists() and (not out.is_dir() or any(out.iterdir())):
        raise FileExistsError(f"{out} already exists and is not an empty folder. Build into a new one.")
    templates = Environment(
        loader=FileSystemLoader(TEMPLATES),
        autoescape=True,
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )
    out.mkdir(parents=True, exist_ok=True)
    page = templates.get_template("index.html").render(noindex=noindex)
    (out / "index.html").write_text(page, encoding="utf-8", newline="\n")
