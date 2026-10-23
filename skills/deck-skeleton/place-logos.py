"""Writes a row of logos into one page of a draw.io section file.

Usage, from the root of the repository:

    python3 -I skills/deck-skeleton/place-logos.py <section file> <page name> <cell id>=<logo file> ...
        [--height 100] [--centre-y 925] [--left 160] [--right 1760] [--scale 3]

The logos are given from left to right.
Each logo is cropped to the box of its pixels that are not transparent, and resampled with Lanczos
filtering to `scale` times its height on the slide.
The page holds each logo as a PNG data URI, because the draw.io editor shows no picture that a path names.
Every logo gets the same height, the logos are centred on one horizontal line, and they spread from
`left` to `right` with equal gaps.
A cell with a given id is replaced in place, and a missing cell is added at the end of the page.
The script prints the place of each logo and the gap, so that the gap can be checked against the
clear space that a guideline asks for.

The script needs Pillow.
With `-I`, Python loads no module from the folder that it runs in.
"""
import argparse
import base64
import io
import re

from PIL import Image

PICTURE_STYLE = "shape=image;html=1;imageAspect=1;aspect=fixed;image=data:image/png,%s;"


def logo_data(path, height):
    """The aspect ratio of the cropped logo, and the logo as a base64 PNG `height` pixels high."""
    image = Image.open(path).convert("RGBA")
    box = image.getchannel("A").point(lambda alpha: 255 if alpha > 16 else 0).getbbox()
    image = image.crop(box)
    width = round(image.width * height / image.height)
    image = image.resize((width, height), Image.Resampling.LANCZOS)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    return image.width / image.height, base64.b64encode(buffer.getvalue()).decode()


def number(value):
    return ("%.2f" % value).rstrip("0").rstrip(".")


def picture_cell(cell_id, parent, data, x, y, width, height, indent):
    """The cell in the layout that the draw.io editor saves, so that a save in the editor changes no line."""
    return ('<mxCell id="%s" parent="%s" style="%s" value="" vertex="1">\n'
            '%s    <mxGeometry height="%s" width="%s" x="%s" y="%s" as="geometry"/>\n'
            '%s</mxCell>'
            % (cell_id, parent, PICTURE_STYLE % data, indent, number(height), number(width),
               number(x), number(y), indent))


def cell_indent(page):
    """The indentation of the cells of the page."""
    found = re.search(r"\n([ \t]*)<mxCell ", page)
    return found.group(1) if found else ""


def drawing_layer(page):
    """The id of the last layer of the page that carries only an id and a parent."""
    layers = re.findall(r'<mxCell id="([^"]+)" parent="[^"]+"\s*/>', page)
    if not layers:
        raise SystemExit("the page has no layer to put the logos on")
    return layers[-1]


def place(page, cells):
    for cell_id, cell in cells:
        existing = re.compile(r'<mxCell id="%s"[^>]*?(?:/>|>.*?</mxCell>)' % re.escape(cell_id), re.S)
        if existing.search(page):
            page = existing.sub(lambda match: cell, page, count=1)
        else:
            closing = re.search(r"\n([ \t]*)</root>", page)
            page = page.replace("\n%s</root>" % closing.group(1),
                                "\n%s%s\n%s</root>" % (cell_indent(page), cell, closing.group(1)), 1)
    return page


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("section_file")
    parser.add_argument("page_name")
    parser.add_argument("logos", nargs="+", metavar="cell-id=logo-file")
    parser.add_argument("--height", type=float, default=100)
    parser.add_argument("--centre-y", type=float, default=925)
    parser.add_argument("--left", type=float, default=160)
    parser.add_argument("--right", type=float, default=1760)
    parser.add_argument("--scale", type=float, default=3)
    arguments = parser.parse_args()

    text = open(arguments.section_file, encoding="utf-8").read()
    diagram = re.compile(r'<diagram [^>]*name="%s"[^>]*>.*?</diagram>' % re.escape(arguments.page_name), re.S)
    found = diagram.search(text)
    if not found:
        raise SystemExit("%s has no page named %s" % (arguments.section_file, arguments.page_name))
    page = found.group(0)

    logos = []
    for pair in arguments.logos:
        cell_id, _, path = pair.partition("=")
        ratio, data = logo_data(path, round(arguments.height * arguments.scale))
        logos.append((cell_id, arguments.height * ratio, data))
    gap = (arguments.right - arguments.left - sum(width for _, width, _ in logos)) / max(len(logos) - 1, 1)

    cells = []
    x = arguments.left
    for cell_id, width, data in logos:
        old = re.search(r'<mxCell id="%s" parent="([^"]+)"' % re.escape(cell_id), page)
        parent = old.group(1) if old else drawing_layer(page)
        top = arguments.centre_y - arguments.height / 2
        cells.append((cell_id, picture_cell(cell_id, parent, data, x, top, width, arguments.height,
                                            cell_indent(page))))
        print("%s at x %.1f, %.1f wide and %.1f high" % (cell_id, x, width, arguments.height))
        x += width + gap
    print("gap between two logos: %.1f" % gap)

    text = text[:found.start()] + place(page, cells) + text[found.end():]
    with open(arguments.section_file, "w", encoding="utf-8") as handle:
        handle.write(text)


if __name__ == "__main__":
    main()
