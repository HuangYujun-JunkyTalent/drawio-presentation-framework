"""The pictures of a deck, written into the cells that show them as data.

A picture is a cell whose style names a file of the deck, `image=assets/<name>`.  The draw.io
editor of VS Code and the viewer of the export look such a path up beside their own page and find
nothing there, so the editor shows the placeholder of a missing picture.  The build and
`embed-pictures.py` therefore write the file into the cell as a data URI and keep its name in the
style key `assetSource=assets/<name>`, which draw.io keeps and ignores.  A cell that carries
`assetSource` gets the data of its file again, so a picture whose file changed shows the new file.
`embed-pictures.py` writes the data into the slide files, for the editor, and the build writes it
into the pages it assembles, for the slides.
"""
from __future__ import annotations

import base64
import dataclasses
import html
import os
import re

MEDIA = {".svg": "image/svg+xml", ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
         ".gif": "image/gif"}
STYLE = re.compile(r'(<mxCell\b[^>]*?\bstyle=")([^"]*)(")')
SOURCE = re.compile(r"(?:^|;)assetSource=(assets/[^;]+)")
LINKED = re.compile(r"(?:^|;)image=(assets/[^;]+)")


@dataclasses.dataclass(frozen=True)
class EmbeddedText:
    """A text with its pictures written as data, the count of the cells whose data changed, and
    the names of the pictures whose files do not exist, in the order of the text."""
    text: str
    written: int
    missing: list[str]


def data_uri(path: str) -> str:
    media = MEDIA.get(os.path.splitext(path)[1].lower(), "image/png")
    with open(path, "rb") as handle:
        return "data:%s,%s" % (media, base64.b64encode(handle.read()).decode())


def picture_name(keys: str) -> str | None:
    """The file a style names as its picture, `assetSource` first, or None.

    The keys are the style with its XML entities read, so a name that holds `&` is whole.
    """
    source = SOURCE.search(keys) or LINKED.search(keys)
    return source.group(1) if source else None


def embed_keys(keys: str, name: str, path: str) -> str:
    """The keys with the data of the file in `image=`, and the name in `assetSource=`."""
    embedded = re.sub(r"(^|;)image=[^;]*", lambda match: match.group(1) + "image=" + data_uri(path),
                      keys, count=1)
    if SOURCE.search(embedded):
        return embedded
    return embedded.rstrip(";") + ";assetSource=%s;" % name


def embed_text(text: str, deck: str) -> EmbeddedText:
    """The text of a drawing with the picture of each cell written as data from its file.

    A style whose data already equals its file is left as it stands, so a second run changes
    nothing, and a picture whose file does not exist leaves its cell as it is.
    """
    written, missing = [0], []

    def embed(match: re.Match) -> str:
        style = match.group(2)
        keys = html.unescape(style)
        name = picture_name(keys)
        if name is None:
            return match.group(0)
        path = os.path.join(deck, name)
        if not os.path.isfile(path):
            missing.append(name)
            return match.group(0)
        embedded = embed_keys(keys, name, path)
        if embedded == keys:
            return match.group(0)
        written[0] += 1
        return match.group(1) + html.escape(embedded, quote=True) + match.group(3)

    return EmbeddedText(STYLE.sub(embed, text), written[0], missing)
