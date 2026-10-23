"""Write a built draw.io deck into one HTML file that presents it in a browser.

The modes `build`, `html` and `watch` of `build-slides.py` export the slides and then run
`write_html_deck`.  The HTML file
holds every exported SVG, the outline of the deck, and the links, the videos and the embedded
pages of the cells, and the page `html-deck.html` beside this module shows them.  The exported
SVGs keep no property of a cell, the link of the cell among them, so all three are read from the
draw.io pages, with the rectangle of each cell.

Three properties of a cell, set in the editor with Edit Link and with Edit Data, reach the HTML
file, a link in two forms, a video and a page:

    link="https://example.org"          an address, opened in a new tab
    link="data:page/id,<page id>"        a page of the deck, as Edit Link > Page writes it
    video="assets/videos/demo.mp4"      a video in the shape, relative to the presentation
    html="assets/plots/surface.html"    an HTML page in the shape, such as an interactive plot

A link to an address opens in a new tab, unless its cell carries `linkTarget="_self"`, which an
edit as text may add.  The HTML file follows the link of a vertex alone, and the build warns about
the link of an edge.  A link written inside the text of a label is in the SVG of its page, and the
build points a link to a page there at the address of the page in the HTML file.

A video cell may also carry `autoplay`, `loop` and `muted` set to 1, and `fit`, which says how
the video fills the shape of the cell:

    fit="contain"    the whole video, smaller than the shape where the two differ in proportion
    fit="stretch"    the video rescaled to the shape, out of its proportion
    fit="crop"       the video filling the shape, with the parts outside it cut

`contain` is the default.  A video cell and a page cell may carry two times in seconds for the
bar of controls that the HTML file shows under the shape while the pointer is over it:

    barHideDelay="0"     how long the bar stays after the pointer has left the shape and the bar
    barFadeOut="0.25"    how long the bar takes to fade out after that

The two defaults are 0 and 0.25.  The page of the HTML file cuts a video or an embedded page to the
outline of the shape, and draws it in the place of the cell among the cells, as `html-deck.html`
says.  An embedded page takes the pointer, so the user turns or zooms a plot on the slide.  A
cell with both a video and a page shows the video.  The PDF shows the cell itself, so a still of
the video as the fill of its cell is what it shows in its place, and the cell of a page shows the
picture of the page as it first draws, which `deck_page_snapshots.py` takes for every build.

Each video and each page is copied into `media/` beside the HTML file, at its path relative to
the presentation folder, with the files that a page names beside it in its `src` and `href`
attributes, such as the `plotly.min.js` of a Plotly figure written with
`include_plotlyjs="directory"`.  A file outside the presentation folder goes to
`media/outside/<first 8 hex digits of the SHA-1 of its absolute path>/`, and the files that a page
there names beside it go into the same folder, at their paths relative to the page.  A file that a
script of the page loads in another way, such as by `fetch`, is not copied, so such a page keeps
its data inside it.  An address that starts with `http:` or `https:` is used as it stands.

`media/.deck-media.json` lists the files that the last build of each HTML file beside `media/`
copied.  A build removes each file that the list of its HTML file from the build before names and
that every list now leaves out.  A video taken out of the deck thus leaves `media/`, and a file put
there by hand stays.
"""
from __future__ import annotations

import dataclasses
import hashlib
import html
import json
import os
import re
import shutil
import sys
import urllib.parse
import xml.etree.ElementTree as ElementTree

import deck_files

HERE = os.path.dirname(os.path.abspath(__file__))
PAGE_TEMPLATE = os.path.join(HERE, "html-deck.html")
# The bars of a video and of a page, which the editor plugin shares, written into the HTML file.
MEDIA_BAR_SCRIPT = os.path.join(HERE, "media-bar.js")
PAGE_LINK = "data:page/id,"
# The `data:` address of a link inside the text of a label, in the SVG of a page.
LABEL_LINK = re.compile(r"""(<a\b[^>]*?\s(?:xlink:)?href\s*=\s*)(["'])(data:[^"']*)\2""",
                        re.IGNORECASE)
# The list in `media/` of the files that the last build of each HTML file beside it copied.
MEDIA_LIST = ".deck-media.json"
REMOTE = re.compile(r"^(https?:)?//", re.IGNORECASE)
WRAPPERS = ("UserObject", "object")
FITS = ("contain", "stretch", "crop")
# The times of the bar of a video or a page, by their properties, with their defaults in seconds.
BAR_TIMES = (("barHideDelay", "bar_hide_delay", 0.0), ("barFadeOut", "bar_fade_out", 0.25))


@dataclasses.dataclass(frozen=True)
class Rectangle:
    x: float
    y: float
    width: float
    height: float


@dataclasses.dataclass(frozen=True)
class CellLink:
    cell: str
    rectangle: Rectangle
    href: str
    opens_new_tab: bool


@dataclasses.dataclass(frozen=True)
class CellVideo:
    cell: str
    rectangle: Rectangle
    source: str
    autoplay: bool
    loop: bool
    muted: bool
    fit: str
    bar_hide_delay: float
    bar_fade_out: float


@dataclasses.dataclass(frozen=True)
class CellPage:
    cell: str
    rectangle: Rectangle
    source: str
    bar_hide_delay: float = BAR_TIMES[0][2]
    bar_fade_out: float = BAR_TIMES[1][2]


@dataclasses.dataclass(frozen=True)
class Cell:
    """A cell of a page: the attributes of its wrapper `UserObject`, if any, and its `mxCell`."""
    properties: dict[str, str]
    element: ElementTree.Element

    @property
    def parent(self) -> str | None:
        return self.element.get("parent")

    @property
    def is_vertex(self) -> bool:
        return self.element.get("vertex") == "1"

    @property
    def is_visible(self) -> bool:
        return self.element.get("visible") != "0"


def read_cells(diagram: str) -> dict[str, Cell]:
    """The cells of one `<diagram>` page, by their id."""
    root = ElementTree.fromstring(diagram).find("./mxGraphModel/root")
    if root is None:
        return {}
    cells = {}
    for element in root:
        if element.tag in WRAPPERS:
            inner = element.find("mxCell")
            cells[element.get("id")] = Cell(dict(element.attrib),
                                            inner if inner is not None else ElementTree.Element("mxCell"))
        elif element.tag == "mxCell":
            cells[element.get("id")] = Cell({}, element)
    return cells


def offset(geometry: ElementTree.Element | None) -> tuple[float, float]:
    if geometry is None:
        return 0.0, 0.0
    return float(geometry.get("x", 0)), float(geometry.get("y", 0))


def page_rectangle(cells: dict[str, Cell], cell_id: str) -> Rectangle | None:
    """The rectangle of a vertex in the coordinates of the page, or None when it shows nowhere.

    The geometry of a cell inside a group or a container is relative to its parent, so the offsets
    of the vertices above it are added.  A cell is hidden when it or a cell above it, its layer
    among them, is invisible.
    """
    cell = cells[cell_id]
    geometry = cell.element.find("mxGeometry")
    if not cell.is_vertex or geometry is None or geometry.get("relative") == "1":
        return None
    x, y = offset(geometry)
    ancestor = cells.get(cell.parent)
    while ancestor is not None:
        if not ancestor.is_visible:
            return None
        if ancestor.is_vertex:
            dx, dy = offset(ancestor.element.find("mxGeometry"))
            x, y = x + dx, y + dy
        ancestor = cells.get(ancestor.parent)
    if not cell.is_visible:
        return None
    return Rectangle(x, y, float(geometry.get("width", 0)), float(geometry.get("height", 0)))


def is_on(properties: dict[str, str], name: str, default: bool) -> bool:
    value = properties.get(name)
    return default if value is None else value.strip().lower() in ("1", "true", "yes")


def diagram_id(diagram: str) -> str | None:
    match = re.match(r'<diagram\b[^>]*\bid="([^"]*)"', diagram)
    return html.unescape(match.group(1)) if match else None


def page_numbers(sections: list[deck_files.Section]) -> dict[int, dict]:
    """The number of each page as the HTML file shows it: its slide, its step, the steps of its
    slide, and whether it is a backup slide."""
    numbers = {}
    for section in sections:
        for slide in section.slides:
            for step, index in enumerate(slide.pages, 1):
                numbers[index] = {"slide": slide.number, "step": step, "steps": len(slide.pages),
                                  "backup": slide.backup}
    return numbers


def page_locations(sections: list[deck_files.Section]) -> dict[int, str]:
    """The address of each page in the HTML file: `12` for the first step of slide 12, `12.3` for
    its third."""
    locations = {}
    for section in sections:
        for slide in section.slides:
            for step, index in enumerate(slide.pages, 1):
                locations[index] = str(slide.number) if step == 1 else "%d.%d" % (slide.number, step)
    return locations


def read_links(cells: dict[str, Cell], targets: dict[str, str]) -> tuple[list[CellLink], list[str]]:
    """The links of the cells of a page, and a warning for each link the HTML file cannot follow.

    `targets` gives the address in the HTML file of each page id of the deck.
    """
    links, problems = [], []
    for cell_id, cell in cells.items():
        link = cell.properties.get("link", "").strip()
        if not link:
            continue
        if not cell.is_vertex:
            problems.append("the cell %s is no vertex, such as an edge, and the HTML file follows "
                            "the link of a vertex alone" % cell_id)
            continue
        rectangle = page_rectangle(cells, cell_id)
        if rectangle is None:
            continue
        if link.startswith(PAGE_LINK):
            page = link[len(PAGE_LINK):]
            if page not in targets:
                problems.append("the cell %s links to the page %s, which the deck does not show"
                                % (cell_id, page))
                continue
            links.append(CellLink(cell_id, rectangle, "#" + targets[page], False))
        elif link.startswith("data:"):
            problems.append("the cell %s has the link %s, which only the editor follows"
                            % (cell_id, link[:40]))
        else:
            links.append(CellLink(cell_id, rectangle, link,
                                  cell.properties.get("linkTarget") != "_self"))
    return links, problems


def point_label_links(svg: str, targets: dict[str, str]) -> tuple[str, list[str]]:
    """The SVG of a page with each link to a page inside the text of a label pointed at the address
    of that page in the HTML file, and a warning for each `data:` link of a label that the HTML
    file cannot follow."""
    problems = []

    def point(match: re.Match) -> str:
        link = html.unescape(match.group(3))
        if not link.startswith(PAGE_LINK):
            problems.append("a label has the link %s, which only the editor follows" % link[:40])
            return match.group(0)
        page = link[len(PAGE_LINK):]
        if page not in targets:
            problems.append("a label links to the page %s, which the deck does not show" % page)
            return match.group(0)
        quote = match.group(2)
        return match.group(1) + quote + "#" + html.escape(targets[page]) + quote

    return LABEL_LINK.sub(point, svg), problems


def bar_times(cell_id: str, properties: dict[str, str], problems: list[str]) -> dict[str, float]:
    """The times of the bar of a cell, with a warning for a value that is no time of 0 s or more."""
    times = {}
    for name, field, default in BAR_TIMES:
        value = properties.get(name, "").strip()
        try:
            seconds = float(value) if value else default
        except ValueError:
            seconds = -1.0
        if not seconds >= 0 or seconds == float("inf"):
            problems.append("the cell %s has %s=%s, which is no time of 0 s or more, so it takes %g"
                            % (cell_id, name, value, default))
            seconds = default
        times[field] = seconds
    return times


def read_videos(cells: dict[str, Cell]) -> tuple[list[CellVideo], list[str]]:
    """The videos of the cells of a page, and a warning for each value of `fit` outside `FITS`."""
    videos, problems = [], []
    for cell_id, cell in cells.items():
        source = cell.properties.get("video", "").strip()
        rectangle = page_rectangle(cells, cell_id) if source else None
        if rectangle is None:
            continue
        fit = cell.properties.get("fit", FITS[0]).strip().lower()
        if fit not in FITS:
            problems.append("the cell %s has fit=%s, which is none of %s, so it shows as %s"
                            % (cell_id, fit, ", ".join(FITS), FITS[0]))
            fit = FITS[0]
        videos.append(CellVideo(cell=cell_id, rectangle=rectangle, source=source,
                                autoplay=is_on(cell.properties, "autoplay", False),
                                loop=is_on(cell.properties, "loop", False),
                                muted=is_on(cell.properties, "muted", False),
                                fit=fit, **bar_times(cell_id, cell.properties, problems)))
    return videos, problems


def read_pages(cells: dict[str, Cell], problems: list[str] | None = None) -> list[CellPage]:
    """The embedded pages of the cells of a page, without a cell that has a video, which shows the
    video.  A warning for a time of the bar goes to `problems`, when given."""
    problems = [] if problems is None else problems
    pages = []
    for cell_id, cell in cells.items():
        source = cell.properties.get("html", "").strip()
        if not source or cell.properties.get("video", "").strip():
            continue
        rectangle = page_rectangle(cells, cell_id)
        if rectangle is not None:
            pages.append(CellPage(cell=cell_id, rectangle=rectangle, source=source,
                                  **bar_times(cell_id, cell.properties, problems)))
    return pages


def is_outside(relative: str) -> bool:
    """Whether a relative path leads out of the folder it is relative to."""
    return relative == os.pardir or relative.startswith(os.pardir + os.sep)


def media_path(path: str, project: str) -> str:
    """The path in `media/` of the copy of a local file: its path relative to the presentation
    folder, or a folder of its own under `outside/` for a file outside the presentation folder, so
    that two files of one name in two folders get two copies."""
    relative = os.path.relpath(path, project)
    if not is_outside(relative):
        return relative
    digest = hashlib.sha1(os.path.abspath(path).encode("utf-8")).hexdigest()[:8]
    return os.path.join("outside", digest, os.path.basename(path))


def copy_file(path: str, target: str) -> None:
    """Copy a file, unless the copy is as new as the file and of the same size."""
    os.makedirs(os.path.dirname(target), exist_ok=True)
    if not (os.path.exists(target) and os.path.getmtime(target) >= os.path.getmtime(path)
            and os.path.getsize(target) == os.path.getsize(path)):
        shutil.copy2(path, target)


def media_address(relative: str) -> str:
    """The address in the HTML file of a file at the path `relative` in `media/`."""
    return "media/" + urllib.parse.quote(relative.replace(os.sep, "/"))


def copy_media_file(source: str, project: str, media: str) -> str | None:
    """The address of a video or a page as the HTML file loads it, after copying a local file into
    `media/`, or None when the file is missing."""
    if REMOTE.match(source):
        return source
    path = os.path.normpath(os.path.join(project, source))
    if not os.path.isfile(path):
        return None
    relative = media_path(path, project)
    copy_file(path, os.path.join(media, relative))
    return media_address(relative)


# A file that a page names in a `src` or `href` attribute, with or without quotes, relative to the
# page: no scheme, no leading slash, no fragment or query.
PAGE_FILE_REFERENCE = re.compile(r"""\b(?:src|href)\s*=\s*(?:"([^"#?:]+)["#?]|'([^'#?:]+)['#?]"""
                                 r"""|([^\s"'<>`=#?:]+)(?=[\s>#?]|$))""", re.IGNORECASE)


def named_page_files(page: str) -> list[str]:
    """The paths of the files that a local page names beside it in its `src` and `href`
    attributes, such as a script or a picture, and that exist.

    A file that a script of the page loads in another way, such as by `fetch`, is not seen.
    """
    try:
        with open(page, encoding="utf-8", errors="replace") as handle:
            text = handle.read()
    except OSError:
        return []
    paths = set()
    for groups in PAGE_FILE_REFERENCE.findall(text):
        reference = urllib.parse.unquote(html.unescape("".join(groups).strip()))
        if not reference or reference.startswith("/"):
            continue
        path = os.path.normpath(os.path.join(os.path.dirname(page), reference))
        if os.path.isfile(path):
            paths.add(path)
    return sorted(paths)


def copy_page_files(source: str, project: str, media: str) -> list[str]:
    """Copy into `media/` the files that a local page names beside it, and return their paths in
    `media/`.

    The copy of a page inside the presentation folder takes each file of that folder at its path
    relative to the folder, as `copy_media_file` copies a file.  The copy of a page outside the
    presentation folder takes each file of the folder of the page or below it beside it, at its
    path relative to the page.
    """
    if REMOTE.match(source):
        return []
    page = os.path.normpath(os.path.join(project, source))
    if is_outside(os.path.relpath(page, project)):
        root, folder = os.path.dirname(page), os.path.dirname(media_path(page, project))
    else:
        root, folder = project, ""
    copied = []
    for path in named_page_files(page):
        relative = os.path.relpath(path, root)
        if is_outside(relative):
            continue
        target = os.path.join(folder, relative)
        copy_file(path, os.path.join(media, target))
        copied.append(target)
    return copied


def remove_stale_media(media: str, html_file: str, copied: set[str]) -> list[str]:
    """Write the list of the files that this build of `html_file` copied into `media/`, and remove
    the files of its list before that every list now leaves out, which the deck no longer uses.

    Each HTML file beside `media/` has a list of its own, so a build keeps the files of the others,
    and a file outside every list, such as one put into `media/` by hand, stays.  Return the paths
    in `media/` of the files removed.
    """
    list_path = os.path.join(media, MEDIA_LIST)
    try:
        with open(list_path, encoding="utf-8") as handle:
            lists = json.load(handle)
    except (OSError, ValueError):
        lists = {}
    if not isinstance(lists, dict):
        lists = {}
    before = set(lists.get(html_file, []))
    lists[html_file] = sorted(path.replace(os.sep, "/") for path in copied)
    named = {path for files in lists.values() if isinstance(files, list) for path in files}
    removed = []
    for relative in sorted(before - named):
        path = os.path.normpath(os.path.join(media, relative))
        if is_outside(os.path.relpath(path, media)) or not os.path.isfile(path):
            continue
        os.remove(path)
        removed.append(relative)
        folder = os.path.dirname(path)
        while folder != os.path.normpath(media) and not os.listdir(folder):
            os.rmdir(folder)
            folder = os.path.dirname(folder)
    if os.path.isdir(media):
        with open(list_path, "w", encoding="utf-8") as handle:
            json.dump(lists, handle, indent=1, sort_keys=True)
            handle.write("\n")
    return removed


def read_svg(path: str) -> str:
    with open(path, encoding="utf-8") as handle:
        svg = handle.read()
    return svg[svg.index("<svg"):]


def outline_entries(sections: list[deck_files.Section]) -> list[dict]:
    return [{"title": "%d %s" % (section.number, deck_files.title(section.name)),
             "slides": [{"number": slide.number, "title": deck_files.title(slide.name),
                         "pages": slide.pages} for slide in section.slides]}
            for section in sections]


def script_json(value: object) -> str:
    """JSON that may sit inside a `<script>` element, with every `<` written as an escape.

    `</` ends the element, and `<!--` followed by `<script` makes the browser read on past its end.
    """
    return json.dumps(value, separators=(",", ":")).replace("<", "\\u003c")


# A placeholder of `html-deck.html`.
PLACEHOLDER = re.compile(r"\{\{(title|media_bar|deck)\}\}")


def write_html_deck(target: str, title: str, project: str, svg_folder: str,
                    pages: list[deck_files.Page], sections: list[deck_files.Section],
                    size: tuple[int, int]) -> None:
    """Write the HTML file of a built deck, and copy its videos and pages into `media/` beside it."""
    locations = page_locations(sections)
    numbers = page_numbers(sections)
    _, everything = deck_files.number_slides(pages)
    targets = {}
    for index, page in enumerate(pages):
        page_id = diagram_id(page.diagram)
        if page_id in targets:
            print("warning: two pages have the id %s, so a link to it goes to the first"
                  % page_id, file=sys.stderr)
        elif page_id:
            targets[page_id] = locations[index]
    media = os.path.join(os.path.dirname(target), "media")
    deck_pages, video_count, embed_count = [], 0, 0
    copied, page_files = set(), set()
    for index, page in enumerate(pages):
        cells = read_cells(page.diagram)
        links, link_problems = read_links(cells, targets)
        cell_videos, video_problems = read_videos(cells)
        page_problems = []
        cell_pages = read_pages(cells, page_problems)
        svg, label_problems = point_label_links(
            read_svg(os.path.join(svg_folder, "slide-%02d.svg" % (index + 1))), targets)
        for problem in link_problems + label_problems + video_problems + page_problems:
            print("warning: page %d, %r: %s" % (index + 1, page.page_name, problem), file=sys.stderr)
        videos = []
        for video in cell_videos:
            address = copy_media_file(video.source, project, media)
            if address is None:
                print("warning: page %d, %r: the video %s of the cell %s does not exist"
                      % (index + 1, page.page_name, video.source, video.cell), file=sys.stderr)
                continue
            videos.append(dict(dataclasses.asdict(video), source=address))
        video_count += len(videos)
        embeds = []
        for embed in cell_pages:
            address = copy_media_file(embed.source, project, media)
            if address is None:
                print("warning: page %d, %r: the page %s of the cell %s does not exist"
                      % (index + 1, page.page_name, embed.source, embed.cell), file=sys.stderr)
                continue
            page_files.update(copy_page_files(embed.source, project, media))
            embeds.append(dict(dataclasses.asdict(embed), source=address))
        embed_count += len(embeds)
        copied.update(urllib.parse.unquote(item["source"][len("media/"):])
                      for item in videos + embeds if item["source"].startswith("media/"))
        deck_pages.append({
            "location": locations[index],
            "number": numbers[index],
            "svg": svg,
            "links": [dataclasses.asdict(link) for link in links],
            "videos": videos,
            "embeds": embeds,
        })
    deck = {"title": title, "width": size[0], "height": size[1],
            "total": deck_files.main_total(pages), "totalWithBackup": everything,
            "outline": outline_entries(sections), "pages": deck_pages}
    with open(PAGE_TEMPLATE, encoding="utf-8") as handle:
        page_html = handle.read()
    with open(MEDIA_BAR_SCRIPT, encoding="utf-8") as handle:
        media_bar = handle.read()
    if "</script" in media_bar.lower():
        raise ValueError("%s holds </script, which would end its <script> element" % MEDIA_BAR_SCRIPT)
    # One pass, so that a title holding `{{deck}}` is not filled in again.
    fillings = {"title": html.escape(title), "media_bar": media_bar, "deck": script_json(deck)}
    page_html = PLACEHOLDER.sub(lambda match: fillings[match.group(1)], page_html)
    os.makedirs(os.path.dirname(target), exist_ok=True)
    with open(target, "w", encoding="utf-8") as handle:
        handle.write(page_html)
    removed = remove_stale_media(media, os.path.basename(target), copied | page_files)
    link_count = sum(len(page["links"]) for page in deck_pages)
    print("%s written: %d pages, %d links, %d videos, %d embedded pages, %d files beside the pages"
          % (target, len(deck_pages), link_count, video_count, embed_count, len(page_files)))
    if removed:
        print("%s: removed %s, which the deck no longer uses" % (media, ", ".join(removed)))
