"""Pictures of the embedded pages of a deck as each page first draws, so that every build shows them.

A cell with the property `html` shows its page live in the editor with `media.plugin.js` and in the
HTML file, which leave the cell's own picture undrawn.  The PDF and the exported SVGs, which the
HTML file is made of, draw the cell itself.  So that every build shows the same thing, the build loads each page in
headless Chromium at the size of its cell on the slide, as the editor and the HTML file lay it out,
takes a picture once the page has drawn, through `snapshot-pages.mjs`, and draws the cell in the
assembled deck as that picture, in place of its own fill, such as a still of the page.  The HTML
file shows the picture under its live page until the page has drawn.

The pictures are kept in `build/page-snapshots/`, which keeps the pictures of the last build alone.
A picture of a local page is taken again when its file, or a file that it names in a `src` or an
`href` attribute, such as its data script, is newer than the picture.  A page of another server is
taken again on every build.  A page that gives no picture keeps the picture of an earlier build,
so that a build without the network still shows a page of another server, and leaves its cell as
it is when it has none, with a warning in both cases.  A cell whose shape is not `image` becomes
an image of its page, which drops the outline of the shape, with a warning.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ElementTree

import deck_html

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "snapshot-pages.mjs")

Key = tuple[str, float, float]


def page_cells(diagram: str) -> list[tuple[deck_html.CellPage, deck_html.Cell]]:
    """The embedded pages of one `<diagram>` page, with their cells."""
    if "html=" not in diagram:
        return []
    cells = deck_html.read_cells(diagram)
    return [(page, cells[page.cell]) for page in deck_html.read_pages(cells)]


def address(source: str, project: str) -> str | None:
    """The address that headless Chromium loads for a page, or None for a missing file."""
    if deck_html.REMOTE.match(source):
        return source if not source.startswith("//") else "https:" + source
    path = os.path.normpath(os.path.join(project, source))
    return "file://" + path if os.path.isfile(path) else None


def changed_at(page: str) -> float:
    """The time of the newest of a local page and of the files that it names in `src` and `href`,
    which the HTML file copies beside it."""
    return max(os.path.getmtime(path) for path in [page] + deck_html.named_page_files(page))


def remove_unused(folder: str, pictures: dict[Key, str]) -> None:
    """Remove each picture of the folder that no cell of this build shows."""
    if not os.path.isdir(folder):
        return
    kept = {os.path.basename(path) for path in pictures.values()}
    for name in os.listdir(folder):
        if name.endswith(".png") and name not in kept:
            os.remove(os.path.join(folder, name))


def take(slides, project: str, folder: str) -> dict[Key, str]:
    """The PNG of each embedded page of the slides at the size of its cell, taking what is missing."""
    wanted: dict[Key, str] = {}
    for slide in slides:
        for page, _ in page_cells(slide.diagram):
            wanted[(page.source, page.rectangle.width, page.rectangle.height)] = page.cell
    if not wanted:
        remove_unused(folder, {})
        return {}
    os.makedirs(folder, exist_ok=True)
    pictures, jobs, earlier = {}, [], []
    for key, cell in wanted.items():
        source, width, height = key
        target = address(source, project)
        if target is None:
            print("warning: the page %s of the cell %s is missing, so the builds draw the cell as "
                  "it is" % (source, cell), file=sys.stderr)
            continue
        name = hashlib.sha1(("%s|%r|%r" % key).encode()).hexdigest()[:16]
        output = os.path.join(folder, "%s-%s.png" % (os.path.splitext(os.path.basename(
            source.rstrip("/")))[0] or "page", name))
        pictures[key] = output
        local = target.startswith("file://")
        if (local and os.path.exists(output)
                and os.path.getmtime(output) >= changed_at(target[len("file://"):])):
            continue
        jobs.append({"address": target, "width": width, "height": height, "output": output})
        earlier.append((source, cell, os.path.getmtime(output) if os.path.exists(output) else None))
    if jobs:
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as handle:
            json.dump(jobs, handle)
        try:
            subprocess.run(["node", SCRIPT, handle.name], check=True)
        finally:
            os.remove(handle.name)
    for job, (source, cell, before) in zip(jobs, earlier):
        after = os.path.getmtime(job["output"]) if os.path.exists(job["output"]) else None
        if after is not None and after != before:
            continue
        shows = "as it is" if after is None else "with the picture of an earlier build"
        print("warning: the page %s of the cell %s gave no picture, so the builds draw the cell %s"
              % (source, cell, shows), file=sys.stderr)
    pictures = {key: path for key, path in pictures.items() if os.path.exists(path)}
    remove_unused(folder, pictures)
    return pictures


def parse_style(style: str) -> list[tuple[str, str | None]]:
    entries = []
    for part in style.split(";"):
        if not part:
            continue
        name, equals, value = part.partition("=")
        entries.append((name, value if equals else None))
    return entries


def picture_style(style: str, data: str) -> tuple[str, str | None]:
    """The style that draws a cell as the picture, and the shape it had when that was not `image`."""
    entries = parse_style(style)
    shape = next((value for name, value in entries if name == "shape"), None)
    kept = [(name, value) for name, value in entries
            if name not in ("shape", "image", "imageAspect")]
    kept = [("shape", "image"), ("image", data), ("imageAspect", "0")] + kept
    text = ";".join(name if value is None else "%s=%s" % (name, value) for name, value in kept) + ";"
    return text, (None if shape == "image" else shape or "rectangle")


def apply(diagram: str, pictures: dict[Key, str], where: str) -> str:
    """The page with each cell of an embedded page drawn as the picture of its page."""
    styles = {}
    for page, cell in page_cells(diagram) if pictures else []:
        path = pictures.get((page.source, page.rectangle.width, page.rectangle.height))
        if path is None:
            continue
        with open(path, "rb") as handle:
            data = "data:image/png," + base64.b64encode(handle.read()).decode()
        styles[page.cell], shape = picture_style(cell.element.get("style", ""), data)
        if shape is not None:
            print("warning: %s, the cell %s of the page %s is a %s shape, so the builds draw it as "
                  "a rectangular picture of its page; give it the shape image"
                  % (where, page.cell, page.source, shape), file=sys.stderr)
    return rewrite(diagram, styles) if styles else diagram


def rewrite(diagram: str, styles: dict[str, str]) -> str:
    """The page with the style of each named cell replaced."""
    root = ElementTree.fromstring(diagram)
    model = root.find("./mxGraphModel/root")
    for element in model if model is not None else []:
        cell_id = element.get("id")
        if cell_id not in styles:
            continue
        inner = element.find("mxCell") if element.tag in deck_html.WRAPPERS else element
        if inner is not None:
            inner.set("style", styles[cell_id])
    return ElementTree.tostring(root, encoding="unicode")
