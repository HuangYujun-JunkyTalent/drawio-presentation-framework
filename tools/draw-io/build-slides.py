#!/usr/bin/env python3
"""Build a draw.io presentation into one HTML file and one PDF, for any presentation folder.

A presentation is a folder that holds its slides as draw.io files and a `package.json` of its
commands, which installs nothing: Playwright is installed once for every presentation, by
`npm install` in `tools/`, the folder above this script. The slides are one file per section
under `sections/`, ordered by the numbers of the files and by the order of the pages inside each
file, and the build numbers the slides from the page names, as `deck_files.py` says. A single
multi-page file, `slides.drawio.xml`, is read instead when the folder is absent.

    my-talk/
    ├── package.json                    the commands below, and the title and the palettes
    ├── sections/
    │   ├── 1-opening.drawio.xml
    │   └── 2-results.drawio.xml
    └── build/                          written by the build
        ├── my-talk.html, media/        the HTML file and the videos and pages it shows
        ├── my-talk.pdf                 the PDF
        ├── slides/slide-NN.svg         one SVG per page, which both are made of
        ├── assembled.drawio.xml        every page in one file
        ├── outline.json                the bookmarks of the PDF
        ├── export-cache/               the SVG of each page, kept for the next build
        └── page-snapshots/             a picture of each embedded page

The build joins the section files into `build/assembled.drawio.xml`, fills in each cell that
holds `%slide%` or `%slides%` with the slide's number and the total without the backup slides,
writes into each page the TeX definitions its formulas use and it does not define, draws each
cell of an embedded page as a picture of that page as it first draws, as
`deck_page_snapshots.py` says, and exports each page to an SVG in `build/slides/`. A page whose
name ends in `-hide` is left out, as `deck_files.py` says.

The diagrams.net viewer, the library of draw.io that draws a page in a web page, exports the
SVGs in the headless Chromium that Playwright drives, through `export-pages.mjs`. The viewer is
the copy of the VS Code extension hediet.vscode-drawio, so the export needs no network and draws
with the draw.io of the editor. It exports four pages at once and copies a page that has not
changed since the last build from `build/export-cache/`, so a build after an edit exports the
edited pages alone. `EXPORT_FRESH=1` exports every page again. Each SVG is written in its light
colours on a white page, so a slide looks the same on a system in dark mode.

The commands work on the presentation folder, the working directory unless `--project` names
another, so a `package.json` can call this script wherever the tools folder is:

    python3 build-slides.py init ../my-talk --title "My talk"   # a new presentation, as a repository
    python3 build-slides.py vscode --colours ../colours.json     # .vscode/settings.json of a deck
    python3 build-slides.py build                                # build/<folder>.html and .pdf
    python3 build-slides.py html                                 # build/<folder>.html alone
    python3 build-slides.py pdf                                  # build/<folder>.pdf alone
    python3 build-slides.py watch                                # the HTML file, on every save
    python3 build-slides.py outline                              # the sections, slides and pages
    python3 build-slides.py check                                # spelling and grammar, by slide

`--outline` prints the same outline after a build, a watch, a pdf or an html.

The key `config` of the `package.json` of the presentation holds its title, its palettes, its
slides folder and its multi-page file, under the names of the options `--title`, `--palette`,
`--slides-dir` and `--deck`, as `deck_files.read_config` says.  `init` writes the key, and the
modes that `package.json` runs read it, so each command of `package.json` holds the mode alone.
An option on the command line takes the place of its key, apart from `--palette`, whose
palettes come after those of the key.

A presentation is a git repository of its own, which `init` creates.  When the presentation lies
inside the folder of the repository of this script, the `.gitignore` of that repository ignores
it already, because it names only the folders it tracks, and `init` adds a line only to a
`.gitignore` that does not.  Every path that `init` writes to the tools of such a presentation is
relative, so the two move together, and a presentation outside that folder gets absolute paths.
The mode `vscode` writes `.vscode/settings.json` of the presentation, for VS Code opened at the
presentation folder: the association of `.drawio.xml` with the draw.io editor, the plugins of the
editor beside this script, among them `media.plugin.js`, the file `.vscode/deck-folder.plugin.js`
of the presentation, which tells that plugin the folder and which every build writes as
`deck_media_plugin.py` says, and the colours of `--colours`, a configuration that
`make-color-config.py` writes.  `init` writes the same file without colours.

The HTML file presents the deck in a browser, with an outline of the sections, the slides and
the steps, the links of the cells, and the videos and the embedded pages of the cells, which it
copies into `build/media/`, as `deck_html.py` says.  The PDF has one page per SVG, so it carries
the slide numbers and leaves out the hidden pages, printed through `print-pdf.mjs`, with
bookmarks of three levels: a section per section file, under it its slides, each at the first
page of the slide, and under a slide in steps its pages, from `build/outline.json`.

The mode `check` checks the spelling and the grammar of every label with LanguageTool on this
machine and prints each issue with its slide, as `deck_language_check.py` says.  It ends with exit
status 1 when it finds an issue.
"""
from __future__ import annotations

import argparse
import dataclasses
import html
import json
import os
import re
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(HERE)
TEMPLATE = os.path.join(os.path.dirname(TOOLS), "formatsAndTemplates", "draw-io",
                        "slide-format.drawio.xml")
# The folder of the SVGs, below the presentation folder.
SLIDES = os.path.join("build", "slides")
sys.path.insert(0, HERE)

import deck_files
import deck_html
import deck_language_check
import deck_media_plugin
import deck_page_snapshots
import deck_pictures
import tex_definitions

# What a cell writes to have the build fill in the slide's number and the deck's total.  draw.io
# leaves a placeholder it cannot resolve as it stands, so the editor shows the token itself.
SLIDE_PLACEHOLDER = "%slide%"
TOTAL_PLACEHOLDER = "%slides%"

DEFINITIONS_LAYER = "Equation colours, added by the build"
# The root cell of a page, written as a bare cell, or by the editor as an object that carries
# data, `<UserObject id="0"><mxCell /></UserObject>`.
ROOT_CELL = re.compile(r'<mxCell id="([^"]+)"(?![^>]*parent=)[^>]*/>'
                       r'|<(UserObject|object)\b[^>]*?\bid="([^"]+)"[^>]*>\s*<mxCell\s*/>\s*</\2>')
COLOUR_USE = re.compile(r"\\(?:textcolor|color|colorbox)\{([^}]*)\}"
                        r"|\\fcolorbox\{([^}]*)\}\{([^}]*)\}")
FORMULA = re.compile(r"\\\(|\$\$")
CELL = re.compile(r"<mxCell\b([^>]*)>")
ATTRIBUTE = re.compile(r'(\w+)="([^"]*)"')
# Names MathJax draws without a definition.  Its colour extension knows the dvips names, which
# are capitalised, such as `Apricot`, and passes any other name on to the browser, which knows
# the colour keywords of CSS.  A lower-case name outside the palette and outside this list is
# most likely a typo, which MathJax would draw black.
CSS_COLOURS = set("""
aliceblue antiquewhite aqua aquamarine azure beige bisque black blanchedalmond blue blueviolet
brown burlywood cadetblue chartreuse chocolate coral cornflowerblue cornsilk crimson cyan darkblue
darkcyan darkgoldenrod darkgray darkgreen darkgrey darkkhaki darkmagenta darkolivegreen
darkorange darkorchid darkred darksalmon darkseagreen darkslateblue darkslategray darkslategrey
darkturquoise darkviolet deeppink deepskyblue dimgray dimgrey dodgerblue firebrick floralwhite
forestgreen fuchsia gainsboro ghostwhite gold goldenrod gray green greenyellow grey honeydew
hotpink indianred indigo ivory khaki lavender lavenderblush lawngreen lemonchiffon lightblue
lightcoral lightcyan lightgoldenrodyellow lightgray lightgreen lightgrey lightpink lightsalmon
lightseagreen lightskyblue lightslategray lightslategrey lightsteelblue lightyellow lime
limegreen linen magenta maroon mediumaquamarine mediumblue mediumorchid mediumpurple
mediumseagreen mediumslateblue mediumspringgreen mediumturquoise mediumvioletred midnightblue
mintcream mistyrose moccasin navajowhite navy oldlace olive olivedrab orange orangered orchid
palegoldenrod palegreen paleturquoise palevioletred papayawhip peachpuff peru pink plum
powderblue purple rebeccapurple red rosybrown royalblue saddlebrown salmon sandybrown seagreen
seashell sienna silver skyblue slateblue slategray slategrey snow springgreen steelblue tan teal
thistle tomato turquoise violet wheat white whitesmoke yellow yellowgreen
""".split())


def page_definitions(diagram):
    """The text of the labels in the page's layers of definitions.

    A definition counts only there, in a layer declared before the drawing, because a definition
    in a tooltip or in a label typeset after the formula does not reach the formula in the
    viewer or in the editor.
    """
    cells = [dict(ATTRIBUTE.findall(match.group(1))) for match in CELL.finditer(diagram)]
    layers = {cell.get("id") for cell in cells
              if cell.get("value") in ("Equation colours", DEFINITIONS_LAYER)}
    return "".join(html.unescape(cell.get("value", "")) for cell in cells
                   if cell.get("parent") in layers)


def missing_definitions(diagram, colours):
    """The definitions a page's formulas use and the page does not write, and the names unknown.

    A person who types `\\textcolor{dpgreen}{x}` on a page without definitions sees the colour in
    the editor through the plugin, and every other renderer needs the definition on the page.
    A definition the page writes in its own layer of definitions is left to the page.
    """
    needed, unknown = [], []
    own = page_definitions(diagram)
    names = {name for match in COLOUR_USE.finditer(diagram) for name in match.groups() if name}
    for name in sorted(names):
        if re.search(r"\\definecolor\{%s\}" % re.escape(name), own):
            continue
        if name in colours:
            needed.append(tex_definitions.colour_definition(name, colours[name]))
        elif name[:1].islower() and name not in CSS_COLOURS:
            unknown.append(name)
    for name in sorted(tex_definitions.MATHJAX_MISSING):
        if (re.search(r"\\%s(?![A-Za-z])" % name, diagram)
                and not re.search(r"\\def\\%s(?![A-Za-z])" % name, own)):
            needed.append(tex_definitions.command_definition(name))
    return "".join(needed), unknown


def math_enabled(diagram):
    return re.search(r'<mxGraphModel\b[^>]*\bmath="1"', diagram) is not None


def add_definitions(diagram, definitions, page_id):
    """The page with the definitions in a layer of their own, declared before every other layer.

    The viewer of the export and the editor keep a definition only for the labels typeset after
    it, and they typeset the layers in the order the root lists them.
    """
    if not definitions:
        return diagram
    root = ROOT_CELL.search(diagram)
    if not root:
        raise ValueError("the page %s has no root cell to put its definitions under" % page_id)
    layer = "%s-build-definitions" % page_id
    cells = ('<mxCell id="%s" parent="%s" style="locked=1;" value="%s" />'
             '<mxCell id="%s-label" parent="%s" style="text;html=1;strokeColor=none;fillColor=none;'
             'align=left;verticalAlign=top;whiteSpace=nowrap;overflow=visible;fontSize=1;" '
             'value="\\(%s\\)" vertex="1"><mxGeometry width="1" height="1" as="geometry" />'
             '</mxCell>' % (layer, root.group(1) or root.group(3), DEFINITIONS_LAYER, layer, layer,
                            html.escape(definitions, quote=True)))
    return diagram[:root.end()] + cells + diagram[root.end():]


def assemble(slides, target, project, palette=None, pictures=None):
    """Write the slide files into one deck, with the slide numbers filled in.

    A cell that holds `%slide%` or `%slides%` gets the slide's own number and the deck's total,
    which leaves out the backup slides, as `deck_files.py` says.  On a backup slide `%slides%`
    gets the total and the total with the backup slides, so `%slide%/%slides%` reads `54/40-54`.
    The build counts the slides itself: pages that follow one another under one name are one
    slide shown in steps and keep one number, so the number does not move while the slide builds.
    A cell of an embedded page is drawn as the picture of its page in `pictures`, as
    `deck_page_snapshots.py` says.  Every picture of a file of `assets/` is written into its page
    as data from the file, for the reason that `deck_pictures.py` gives, and so an SVG that the
    PDF or the HTML file shows needs no file beside it.
    """
    if not slides:
        raise SystemExit("%s holds no pages" % project)
    numbers, everything = deck_files.number_slides(slides)
    total = deck_files.main_total(slides)
    palette = palette or {}
    for name, found in sorted(deck_files.repeated_names(slides).items()):
        print("warning: the name %r starts slides %s, so they are counted as different slides. "
              "Rename one of them or move its pages next to the others."
              % (name, ", ".join(str(n) for n in found)), file=sys.stderr)
    for number, name, steps in deck_files.step_problems(slides):
        print("warning: slide %d, %r, has the steps %s in page order, where 1 to %d was expected"
              % (number, name, ", ".join(str(n) for n in steps), len(steps)), file=sys.stderr)
    body, pages = [], []
    for index, slide in enumerate(slides):
        diagram = slide.diagram
        diagram = diagram.replace(SLIDE_PLACEHOLDER, str(numbers[index]))
        diagram = diagram.replace(TOTAL_PLACEHOLDER, "%d-%d" % (total, everything)
                                  if slide.backup else str(total))
        diagram = deck_page_snapshots.apply(diagram, pictures or {}, "slide %d, %r"
                                            % (numbers[index], slide.page_name))
        embedded = deck_pictures.embed_text(diagram, project)
        diagram = embedded.text
        for name in embedded.missing:
            print("warning: slide %d, %r, names the picture %s, which does not exist"
                  % (numbers[index], slide.page_name, name), file=sys.stderr)
        if math_enabled(diagram):
            definitions, unknown = missing_definitions(diagram, palette)
            diagram = add_definitions(diagram, definitions, "page-%d" % (index + 1))
        else:
            unknown = []
            if FORMULA.search(diagram):
                print("warning: slide %d, %r, holds a formula and has mathematical typesetting "
                      "off, so the formula shows as raw text. Switch on Extras > Mathematical "
                      "Typesetting on that page." % (numbers[index], slide.page_name),
                      file=sys.stderr)
        if unknown:
            print("warning: slide %d, %r, colours formulas with %s, which neither the page nor the "
                  "palette defines" % (numbers[index], slide.page_name, ", ".join(unknown)),
                  file=sys.stderr)
        model = re.search(r"<mxGraphModel ([^>]*)>", diagram)
        attrs = dict(ATTRIBUTE.findall(model.group(1))) if model else {}
        body.append("  " + diagram.strip() + "\n")
        pages.append({
            "name": deck_files.PAGE_NAME.search(diagram).group(1),
            "width": int(float(attrs.get("pageWidth", 1920))),
            "height": int(float(attrs.get("pageHeight", 1080))),
        })
    with open(target, "w", encoding="utf-8") as handle:
        handle.write('<mxfile host="build-slides.py" pages="%d">\n' % len(slides))
        handle.write("".join(body))
        handle.write("</mxfile>\n")
    return pages, total


def first_of_light_dark(text):
    """The text with every `light-dark(<light>, <dark>)` replaced by its light colour.

    A colour may hold commas and brackets of its own, as `rgb(0, 136, 43)` does, so the two
    arguments are split at the comma outside every bracket.
    """
    out, index = [], 0
    while True:
        start = text.find("light-dark(", index)
        if start < 0:
            out.append(text[index:])
            return "".join(out)
        out.append(text[index:start])
        depth, cursor, comma = 1, start + len("light-dark("), None
        while cursor < len(text) and depth:
            character = text[cursor]
            if character == "(":
                depth += 1
            elif character == ")":
                depth -= 1
            elif character == "," and depth == 1 and comma is None:
                comma = cursor
            cursor += 1
        inner_start = start + len("light-dark(")
        out.append(text[inner_start:comma if comma is not None else cursor - 1].strip())
        index = cursor


def make_light(path):
    """Write an exported SVG in its light colours on a white page.

    draw.io writes a colour as `light-dark(<light>, <dark>)` and the root as
    `color-scheme: light dark` on a transparent background, so a browser on a system in dark mode
    draws the slide dark.  A slide is shown in its light colours whatever the system's scheme.
    """
    with open(path, encoding="utf-8") as handle:
        svg = handle.read()
    svg = first_of_light_dark(svg).replace("color-scheme: light dark", "color-scheme: light")
    head_end = svg.index(">", svg.index("<svg")) + 1
    head = svg[:head_end]
    light = "background-color: #ffffff; color-scheme: light;"
    if re.search(r'<svg\b[^>]*\bstyle="', head):
        head = re.sub(r'(<svg\b[^>]*\bstyle=")[^"]*"', lambda m: m.group(1) + light + '"', head, count=1)
    else:
        head = head[:-1] + ' style="%s">' % light
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(head + svg[head_end:])


def export_with_viewer(deck, outdir, pages, project):
    """Export through `export-pages.mjs`, which copies a page unchanged since an earlier build from
    `build/export-cache/` rather than exporting it again."""
    subprocess.run(["node", os.path.join(HERE, "export-pages.mjs"), deck, outdir,
                    str(len(pages)), str(pages[0]["width"]), str(pages[0]["height"]),
                    os.path.join(project, "build", "export-cache")],
                   check=True)


def project_path(args, *parts):
    return os.path.join(os.path.abspath(args.project), *parts)


def deck_name(args: argparse.Namespace) -> str:
    """The name of the presentation folder, which names the HTML file and the PDF."""
    return os.path.basename(os.path.abspath(args.project))


def with_deck_config(args: argparse.Namespace) -> argparse.Namespace:
    """The options with each one that the command line leaves out taken from the key `config` of
    the `package.json` of the presentation, or else from its default.

    The modes of `DECK_COMMANDS` read the key.  `init` writes it, and `vscode` needs none of it.
    """
    try:
        config = (deck_files.read_config(os.path.abspath(args.project))
                  if args.mode in DECK_COMMANDS else {})
    except ValueError as error:
        raise SystemExit(str(error))
    return argparse.Namespace(**{
        **vars(args),
        "title": deck_files.setting("title", args.title, config),
        "palette": deck_files.setting("palette", args.palette, config),
        "slides_dir": deck_files.setting("slides-dir", args.slides_dir, config),
        "deck": deck_files.setting("deck", args.deck, config),
    })


def slides_location(args):
    """The folder of the section files, or else the file of a deck of one file, that the deck
    reads its pages from, and whether it is the folder."""
    location = deck_files.slides_location(os.path.abspath(args.project), args.slides_dir,
                                          args.deck)
    if location is None:
        raise SystemExit("%s holds neither %s/ nor %s. Run `init` to start a presentation."
                         % (os.path.abspath(args.project), args.slides_dir, args.deck))
    return location


def read_slides(args):
    """The pages that the deck presents, and where they were read from.

    Pages whose name ends in `-hide` are left out and listed.  A section file that `deck_files.py`
    refuses, such as a second file of one section number, stops the build with its reason.
    """
    location, is_folder = slides_location(args)
    try:
        slides = (deck_files.read_folder(location) if is_folder
                  else deck_files.read_single_file(location))
    except ValueError as error:
        raise SystemExit("%s: %s" % (location, error))
    source = args.slides_dir if is_folder else args.deck
    hidden = [page.page_name for page in slides if page.page_name.endswith(deck_files.HIDDEN)]
    slides = deck_files.shown_pages(slides)
    if hidden:
        print("%d %s hidden: %s" % (len(hidden), "page" if len(hidden) == 1 else "pages",
                                    ", ".join(hidden)))
    return slides, source


def count_line(sections, source):
    """The pages and the slides of the talk and of the backup slides, in one line."""
    def part(backup):
        slides = [slide for section in sections for slide in section.slides
                  if slide.backup == backup]
        return len(slides), sum(len(slide.pages) for slide in slides)
    talk, backup = part(False), part(True)
    return ("%d pages assembled from %s: %d slides on %d pages, and %d backup slides on %d pages"
            % (talk[1] + backup[1], source, talk[0], talk[1], backup[0], backup[1]))


def print_outline(sections, total):
    """The sections, each slide with its number as the deck shows it, and its pages."""
    everything = sections[-1].slides[-1].number
    for section in sections:
        pages = section.pages
        print("%d %s%s, pages %d-%d" % (section.number, deck_files.title(section.name),
                                       " (backup)" if section.backup else "",
                                       pages[0] + 1, pages[-1] + 1))
        for slide in section.slides:
            shown = ("%d/%d-%d" % (slide.number, total, everything) if slide.backup
                     else "%d/%d" % (slide.number, total))
            first, last = slide.pages[0] + 1, slide.pages[-1] + 1
            print("  %-9s %-48s %s" % (shown, slide.name,
                                        "page %d" % first if first == last
                                        else "pages %d-%d, %d steps" % (first, last,
                                                                        last - first + 1)))


def outline(args):
    """Print the outline of the deck without building it."""
    slides, source = read_slides(args)
    if not slides:
        raise SystemExit("%s holds no pages" % os.path.abspath(args.project))
    sections = deck_files.outline(slides)
    print(count_line(sections, source))
    print_outline(sections, deck_files.main_total(slides))


def write_pdf_outline(path, sections):
    """The bookmarks of the PDF as JSON: a section per file, under it its slides, and under a
    slide in steps its pages."""
    entries = []
    for section in sections:
        entries.append({"level": 1, "page": section.pages[0] + 1,
                        "title": "%d %s" % (section.number, deck_files.title(section.name))})
        for slide in section.slides:
            entries.append({"level": 2, "page": slide.pages[0] + 1,
                            "title": "%d %s" % (slide.number, deck_files.title(slide.name))})
            if len(slide.pages) > 1:
                for step, index in enumerate(slide.pages, 1):
                    entries.append({"level": 3, "page": index + 1,
                                    "title": "Step %d, page %d" % (step, index + 1)})
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(entries, handle, indent=1)


@dataclasses.dataclass(frozen=True)
class BuiltDeck:
    pages: list[dict]
    slides: list[deck_files.Page]
    sections: list[deck_files.Section]


def palette_paths(args: argparse.Namespace) -> list[str]:
    """The palette files of `--palette` or of `config.palette`, a relative path read from the
    presentation folder."""
    return [path if os.path.isabs(path) else project_path(args, path)
            for path in args.palette or []]


def export_slides(args: argparse.Namespace) -> BuiltDeck:
    """Assemble the deck and export each page to an SVG in `build/slides/`, which both formats
    are made of."""
    project = os.path.abspath(args.project)
    outdir = project_path(args, SLIDES)
    os.makedirs(outdir, exist_ok=True)
    slides, source = read_slides(args)
    deck = project_path(args, "build", "assembled.drawio.xml")
    palettes = palette_paths(args)
    for path in palettes:
        if not os.path.isfile(path):
            raise SystemExit("the palette %s does not exist" % path)
    pictures = deck_page_snapshots.take(slides, project,
                                        project_path(args, "build", "page-snapshots"))
    pages, total = assemble(slides, deck, project, tex_definitions.read_palettes(palettes),
                            pictures)
    sections = deck_files.outline(slides)
    print(count_line(sections, source))
    if args.outline:
        print_outline(sections, total)
    write_pdf_outline(project_path(args, "build", "outline.json"), sections)
    export_with_viewer(deck, outdir, pages, project)
    for index in range(1, len(pages) + 1):
        make_light(os.path.join(outdir, "slide-%02d.svg" % index))
    # A deck that lost pages, to `-hide` or to a deletion, would otherwise keep the SVGs of its
    # last pages from the build before.
    for name in os.listdir(outdir):
        match = re.match(r"^slide-(\d+)\.svg$", name)
        if match and int(match.group(1)) > len(pages):
            os.remove(os.path.join(outdir, name))
    plugin, changed = deck_media_plugin.write_deck_folder_plugin(project)
    if changed:
        print("%s written. VS Code asks once to allow it." % os.path.relpath(plugin, project))
    return BuiltDeck(pages, slides, sections)


def write_pdf(args: argparse.Namespace, built: BuiltDeck) -> None:
    """Print the SVGs into one PDF, `build/<folder>.pdf` by default."""
    output = (os.path.abspath(args.pdf) if args.pdf
              else project_path(args, "build", deck_name(args) + ".pdf"))
    first = built.pages[0]
    subprocess.run(["node", os.path.join(HERE, "print-pdf.mjs"), project_path(args, SLIDES),
                    str(len(built.pages)), output, str(first["width"]), str(first["height"]),
                    project_path(args, "build", "outline.json")],
                   check=True)


def write_html(args: argparse.Namespace, built: BuiltDeck) -> None:
    """Write the SVGs into one HTML file, `build/<folder>.html` by default."""
    output = (os.path.abspath(args.html) if args.html
              else project_path(args, "build", deck_name(args) + ".html"))
    first = built.pages[0]
    deck_html.write_html_deck(output, args.title or deck_name(args),
                              os.path.abspath(args.project), project_path(args, SLIDES),
                              built.slides, built.sections, (first["width"], first["height"]))


def build(args: argparse.Namespace) -> None:
    """Export the slides once, then write the HTML file and the PDF from them."""
    built = export_slides(args)
    write_html(args, built)
    write_pdf(args, built)


def check(args: argparse.Namespace) -> None:
    """Check the spelling and the grammar of the deck, and end with exit status 1 on an issue."""
    slides, _source = read_slides(args)
    if deck_language_check.check_deck(slides, os.path.abspath(args.project)):
        raise SystemExit(1)


def html_deck(args: argparse.Namespace) -> None:
    write_html(args, export_slides(args))


def pdf(args: argparse.Namespace) -> None:
    write_pdf(args, export_slides(args))


def modified(path):
    """The time a file last changed, or None when it has gone since it was listed."""
    try:
        return os.path.getmtime(path)
    except OSError:
        return None


def deck_state(args):
    """The name and the time of each file a build reads: the slides, the files of `assets/` and
    the palettes.  A file renamed, added or deleted changes the state as a saved one does."""
    location, is_folder = slides_location(args)
    paths = ([os.path.join(location, name) for name in os.listdir(location)] if is_folder
             else [location])
    paths += [os.path.join(folder, name)
              for folder, _folders, names in os.walk(project_path(args, "assets"))
              for name in names]
    paths += palette_paths(args)
    return [(path, modified(path)) for path in sorted(set(paths))]


def watch(args):
    """Write the HTML file again after every save, for a browser that shows it to reload."""
    location, _is_folder = slides_location(args)
    last = None
    print("watching %s until Ctrl-C" % location)
    while True:
        try:
            stamp = deck_state(args)
        except (OSError, SystemExit) as error:  # the slides moved away while the watch runs
            stamp = str(error)
        if stamp != last:
            last = stamp
            try:
                html_deck(args)
            except (Exception, SystemExit) as error:  # a half-written file is retried on the next tick
                print("build failed: %s" % error, file=sys.stderr)
        time.sleep(args.interval)


# The pages of the template a new presentation starts with, in this order.
STARTER_PAGES = ("title-slide-1", "section-divider-1", "title-and-body-1")
# The commands of the `package.json` of a presentation, each named after the mode it runs, and the
# modes that read the key `config` of the file.  The file holds no dependencies, which
# `tools/package.json` installs once for every presentation.
DECK_COMMANDS = ("build", "watch", "pdf", "html", "outline", "check")


def repository_of(path):
    """The folder holding `.git` that contains the path, or None."""
    folder = os.path.abspath(path)
    while True:
        if os.path.exists(os.path.join(folder, ".git")):
            return folder
        parent = os.path.dirname(folder)
        if parent == folder:
            return None
        folder = parent


def tools_repository() -> str | None:
    """The folder of the repository of this script, with its symbolic links resolved."""
    repository = repository_of(HERE)
    return os.path.realpath(repository) if repository else None


def is_inside(folder: str, path: str) -> bool:
    return os.path.commonpath([folder, path]) == folder


def path_from(project, path):
    """A path as the presentation's `package.json` and `.vscode/settings.json` write it.

    Relative to the presentation when both lie inside the folder of the repository of this
    script, also when the presentation is a repository of its own nested there, so that they
    move together, and absolute otherwise.  Symbolic links are resolved first, so `/tmp` and
    `/private/tmp` of macOS count as one folder.
    """
    project, path = os.path.realpath(project), os.path.realpath(path)
    repository = tools_repository()
    inside = repository is not None and all(is_inside(repository, place) for place in (project, path))
    return os.path.relpath(path, project) if inside else path


def shell_quote(text):
    """A path or a title quoted for the shell that `npm run` starts."""
    return "'" + text.replace("'", "'\\''") + "'"


# The file of the folder of the deck for the editor plugin, as git and VS Code write a path.
FOLDER_PLUGIN = deck_media_plugin.FOLDER_PLUGIN.replace(os.sep, "/")
# The `.gitignore` of a new presentation leaves out what the build and macOS write into its
# folder, the folder of the deck for the editor plugin, and the settings of Claude Code for this
# machine alone, which a session started in the presentation writes.
DECK_IGNORED = ("build/", ".DS_Store", FOLDER_PLUGIN, ".claude/settings.local.json")
# The plugins of the editor beside this script, which every presentation loads.
EDITOR_PLUGINS = ("mathjax-definitions.plugin.js", "label-colours.plugin.js",
                  "single-page.plugin.js", "click-through.plugin.js", "edit-at-click.plugin.js",
                  "list-styles.plugin.js", "language-check.plugin.js", "view-position.plugin.js",
                  "media-bar.js", "media.plugin.js")
COLOUR_SETTINGS = ("colorNames", "presetColors", "customColorSchemes")


def plugin_setting(project: str, path: str) -> dict[str, str]:
    location = path_from(project, path)
    return {"file": location if os.path.isabs(location)
            else "${workspaceFolder}/" + location.replace(os.sep, "/")}


def read_colour_configuration(path: str) -> dict:
    """A colour configuration of the editor, which `make-color-config.py` writes as plain JSON."""
    if not os.path.isfile(path):
        raise SystemExit("the colour configuration %s does not exist" % path)
    with open(path, encoding="utf-8") as handle:
        try:
            return json.load(handle)
        except json.JSONDecodeError as error:
            raise SystemExit("the colour configuration %s does not read as plain JSON: %s. A "
                             "file with comments reads only after they are removed."
                             % (path, error))


def write_vscode_settings(project: str, colours: str | None = None) -> str:
    """Write `.vscode/settings.json` of a presentation, and refuse to replace one that exists."""
    target = os.path.join(project, ".vscode", "settings.json")
    if os.path.exists(target):
        raise SystemExit("%s exists. Add the settings that `vscode` writes to it by hand." % target)
    configuration = read_colour_configuration(colours) if colours else {}
    settings = {
        "workbench.editorAssociations": {"*.drawio.xml": "hediet.vscode-drawio-text"},
        "files.associations": {"*.drawio.xml": "drawio"},
        "hediet.vscode-drawio.plugins": [plugin_setting(project, os.path.join(HERE, name))
                                         for name in EDITOR_PLUGINS]
        + [{"file": "${workspaceFolder}/" + FOLDER_PLUGIN}],
    }
    for name in COLOUR_SETTINGS:
        if name in configuration:
            settings["hediet.vscode-drawio." + name] = configuration[name]
    os.makedirs(os.path.dirname(target), exist_ok=True)
    with open(target, "w", encoding="utf-8") as handle:
        json.dump(settings, handle, indent=2)
        handle.write("\n")
    return target


def vscode(args: argparse.Namespace) -> None:
    """Write `.vscode/settings.json` of an existing presentation."""
    project = os.path.abspath(args.project)
    colours = os.path.abspath(args.colours) if args.colours else None
    print("%s written" % write_vscode_settings(project, colours))


# The characters that a line of `.gitignore` reads as a pattern, and a trailing space it drops.
GITIGNORE_PATTERN = re.compile(r"([\\\[\]*?])")


def ignore_in_tools_repository(project: str) -> str | None:
    """Add a presentation inside the repository of this script to its `.gitignore`, and return
    the line, or None when the presentation lies outside it or git ignores it already, as the
    `.gitignore` of this repository does for every folder it does not name."""
    project = os.path.realpath(project)
    repository = tools_repository()
    if repository is None or project == repository or not is_inside(repository, project):
        return None
    if subprocess.run(["git", "-C", repository, "check-ignore", "-q", project]).returncode == 0:
        return None
    relative = os.path.relpath(project, repository).replace(os.sep, "/")
    relative = GITIGNORE_PATTERN.sub(r"\\\1", relative)
    if relative.endswith(" "):
        relative = relative[:-1] + "\\ "
    line = "/%s/" % relative
    ignore = os.path.join(repository, ".gitignore")
    existing = open(ignore, encoding="utf-8").read() if os.path.exists(ignore) else ""
    if line in existing.splitlines():
        return None
    with open(ignore, "a", encoding="utf-8") as handle:
        handle.write(("" if existing.endswith("\n") or not existing else "\n") + line + "\n")
    ignored = subprocess.run(["git", "-C", repository, "check-ignore", "-q", project])
    if ignored.returncode != 0:
        print("warning: %s added %s to %s, and git still does not ignore %s. Fix the line by hand."
              % (__file__, line, ignore, project), file=sys.stderr)
    return line


def write_deck_gitignore(project: str) -> None:
    """Add the lines of `DECK_IGNORED` that the `.gitignore` of a presentation lacks, after the
    lines it holds."""
    path = os.path.join(project, ".gitignore")
    existing = open(path, encoding="utf-8").read() if os.path.exists(path) else ""
    lacking = [line for line in DECK_IGNORED if line not in existing.splitlines()]
    if not lacking:
        return
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(("" if existing.endswith("\n") or not existing else "\n")
                     + "".join(line + "\n" for line in lacking))


def init(args):
    """Start a presentation as a git repository of its own.

    `init` writes a section file from the template's pages, a `package.json` of the commands of
    `DECK_COMMANDS` and of the key `config`, the lines of `DECK_IGNORED` that the `.gitignore` of
    the folder lacks, and `.vscode/settings.json`, runs `git init`, and adds the presentation to
    the `.gitignore` of the repository of this script when it lies inside that repository and git
    does not ignore it already.  The section file takes its pages from `slide-format.drawio.xml`,
    so the template stays the one place a page is defined.  The paths to the tools are relative
    or absolute, as `path_from` says.  Every check runs before the first file is written, so a
    refused `init` leaves the folder as it was.
    """
    project = os.path.realpath(os.path.abspath(args.project))
    sections = os.path.join(project, args.slides_dir)
    existing = project
    while not os.path.exists(existing):
        existing = os.path.dirname(existing)
    if not os.path.isdir(existing):
        raise SystemExit("%s is a file, so init cannot make the folder %s" % (existing, project))
    if project == tools_repository():
        raise SystemExit("%s is the repository of the tools. Give the folder of the new "
                         "presentation, such as my-talk." % project)
    if (os.path.exists(os.path.join(project, "package.json"))
            or os.path.exists(os.path.join(project, args.deck))
            or (os.path.isdir(sections) and os.listdir(sections))):
        raise SystemExit("%s already holds a presentation, and init writes only into a new folder"
                         % project)
    if os.path.exists(os.path.join(project, ".vscode", "settings.json")):
        raise SystemExit("%s/.vscode/settings.json exists, and init writes only into a new folder"
                         % project)
    if shutil.which("git") is None:
        raise SystemExit("git is not installed, and init makes the presentation a repository")
    for path in args.palette or []:
        if not os.path.isfile(path):
            raise SystemExit("the palette %s does not exist. Give its path from the folder this "
                             "command runs in." % path)
    template = open(TEMPLATE, encoding="utf-8").read()
    diagrams = {deck_files.PAGE_NAME.search(d).group(1): d
                for d in deck_files.DIAGRAM.findall(template)}
    missing = [name for name in STARTER_PAGES if name not in diagrams]
    if missing:
        raise SystemExit("the template %s has no page %s" % (TEMPLATE, ", ".join(missing)))
    os.makedirs(sections, exist_ok=True)
    if not os.path.exists(os.path.join(project, ".git")):
        subprocess.run(["git", "init", "-q", "-b", "main", project], check=True)
    title = args.title or os.path.basename(project)
    first = os.path.join(sections, deck_files.file_name(1, deck_files.slug(title)))
    with open(first, "w", encoding="utf-8") as handle:
        handle.write('<mxfile host="build-slides.py init" pages="%d">\n' % len(STARTER_PAGES))
        handle.write("".join("  " + diagrams[name].strip() + "\n" for name in STARTER_PAGES))
        handle.write("</mxfile>\n")
    script = shell_quote(path_from(project, __file__))
    # The commands read the facts of the deck from `config`, and a fact at its default is left out.
    config = {"title": title}
    if args.palette:
        config["palette"] = [path_from(project, path) for path in args.palette]
    if args.slides_dir != deck_files.SLIDES_DIR:
        config["slides-dir"] = args.slides_dir
    if args.deck != deck_files.SINGLE_FILE:
        config["deck"] = args.deck
    package = {"name": deck_files.slug(title), "private": True, "config": config,
               "scripts": {mode: "python3 %s %s" % (script, mode) for mode in DECK_COMMANDS}}
    with open(os.path.join(project, "package.json"), "w", encoding="utf-8") as handle:
        json.dump(package, handle, indent=2)
        handle.write("\n")
    write_deck_gitignore(project)
    settings = write_vscode_settings(project)
    ignored = ignore_in_tools_repository(project)
    print("%s written with the pages %s" % (os.path.relpath(first, project), ", ".join(STARTER_PAGES)))
    print("package.json and %s written, and %s is a git repository of its own"
          % (os.path.relpath(settings, project), project))
    if ignored:
        print("%s added to the .gitignore of %s" % (ignored, repository_of(HERE)))
    print("next, in %s: npm run build, after npm install in %s once. Open the folder in VS Code "
          "to edit the slides." % (project, TOOLS))


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("mode", choices=MODES)
    parser.add_argument("project", nargs="?", default=".",
                        help="the presentation folder, the working directory by default")
    parser.add_argument("--project", dest="project_option",
                        help="the presentation folder, as an option")
    parser.add_argument("--deck",
                        help="a multi-page file, read when the slides folder is absent, from "
                             "config.deck of package.json, or %s by default"
                             % deck_files.SINGLE_FILE)
    parser.add_argument("--slides-dir",
                        help="the folder of one file per section, preferred when it exists, from "
                             "config.slides-dir of package.json, or %s by default"
                             % deck_files.SLIDES_DIR)
    parser.add_argument("--title",
                        help="the title of the HTML file, from config.title of package.json, or "
                             "the folder's name by default")
    parser.add_argument("--palette", action="append",
                        help="a TeX file of \\definecolor lines whose colours the formulas use, "
                             "relative to the presentation folder for build, html, pdf and watch, "
                             "and to the folder the command runs in for init. The option may be "
                             "given more than once, and adds to config.palette of package.json.")
    parser.add_argument("--interval", type=float, default=1.0,
                        help="for watch, the seconds between two looks at the slides")
    parser.add_argument("--outline", action="store_true",
                        help="for build, watch, pdf and html, also print the outline: the sections, "
                             "the slides with their numbers, and their pages")
    parser.add_argument("--pdf", help="for build and pdf, the file to write, build/<folder>.pdf "
                                      "by default")
    parser.add_argument("--colours", help="for vscode, a colour configuration of the editor, such "
                                          "as formatsAndTemplates/draw-io/named-colors-*.json")
    parser.add_argument("--html", help="for build, html and watch, the file to write, "
                                       "build/<folder>.html by default, with the videos in media/ "
                                       "beside it")
    args = parser.parse_args()
    # Each line shows when it is printed, in order with the lines of the Node scripts it runs.
    sys.stdout.reconfigure(line_buffering=True)
    if args.project_option:
        args.project = args.project_option
    MODES[args.mode](with_deck_config(args))


MODES = {"build": build, "html": html_deck, "pdf": pdf, "watch": watch, "init": init,
         "outline": outline, "check": check, "vscode": vscode}


if __name__ == "__main__":
    main()
