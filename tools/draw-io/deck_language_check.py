"""Check the spelling and the grammar of every label of a deck with LanguageTool on this machine.

The mode `check` of `build-slides.py` runs `check_deck`, which returns the number of issues, and
the mode ends with exit status 1 when the number is above 0.  LanguageTool runs as a server, which
Homebrew installs and starts with `brew install languagetool` and `brew services start
languagetool`, at `http://localhost:8081`, or at the address of the environment variable
`LANGUAGETOOL_SERVER`, so no text leaves the machine.

Each label is read as the editor plugin `language-check.plugin.js` reads the label being edited:
its words as text, its tags as markup, the items of a list and the lines of a label as paragraphs,
and a formula between `\\(` and `\\)` or `$$` as markup that reads as a noun, so its TeX is not
checked.  A new line in the value of a label is a line break, as the editor shows it, unless the
style of a label of HTML holds `nl2Br=0`.  Each label goes to the server in a request of its own,
as the plugin sends the label being edited, so a rule that reads several sentences reads one label
alone.  The language and the rules left out are the object `CHECK` of that plugin, which this
module reads from it, so the two check alike.  A label that several pages share, such as the
steps of a slide, is checked once and reported at its first slide, with the count of the others.
A word of the list of the server counts as spelled right in every application.  A word of `language-check-words.txt` in the
folder of the deck, one per line, such as a name, counts as spelled right in that deck alone, and a
line that starts with `#` is a comment.
"""
from __future__ import annotations

import html.parser
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

import deck_files
import deck_html

HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.join(HERE, "language-check.plugin.js")
WORDS_FILE = "language-check-words.txt"
FORMULA = re.compile(r"\\\([\s\S]*?\\\)|\$\$[\s\S]*?\$\$")
BLOCKS = {"div", "p", "li", "ul", "ol", "br", "table", "tr", "td", "h1", "h2", "h3"}
LINE_BREAK = {"markup": "\n", "interpretAs": "\n\n"}


def check_options() -> dict:
    """The object `CHECK` of the editor plugin."""
    with open(PLUGIN, encoding="utf-8") as handle:
        match = re.search(r"var CHECK = (\{[\s\S]*?\});", handle.read())
    if match is None:
        raise SystemExit("%s holds no object CHECK" % PLUGIN)
    return json.loads(match.group(1))


def known_words(project: str) -> set[str]:
    path = os.path.join(project, WORDS_FILE)
    if not os.path.exists(path):
        return set()
    with open(path, encoding="utf-8") as handle:
        return {line.strip().lower() for line in handle
                if line.strip() and not line.strip().startswith("#")}


class LabelReader(html.parser.HTMLParser):
    """The pieces of a label of HTML for LanguageTool: its text, and its tags and formulas as
    markup."""

    def __init__(self, formula_reads_as: str, new_line_breaks: bool):
        super().__init__(convert_charrefs=True)
        self.formula_reads_as = formula_reads_as
        self.new_line_breaks = new_line_breaks
        self.pieces: list[dict] = []
        self.data = ""

    # The parser may hand a run of text over in parts, so a run is read whole at the next tag,
    # and a formula across two parts is found.
    def flush(self) -> None:
        if self.data:
            self.text(self.data)
            self.data = ""

    def text(self, data: str) -> None:
        last = 0
        for match in FORMULA.finditer(data):
            self.words(data[last:match.start()])
            self.pieces.append({"markup": match.group(0), "interpretAs": self.formula_reads_as})
            last = match.end()
        self.words(data[last:])

    def words(self, data: str) -> None:
        lines = data.split("\n") if self.new_line_breaks else [data]
        for index, line in enumerate(lines):
            if index:
                self.pieces.append(dict(LINE_BREAK))
            if line:
                self.pieces.append({"text": line})

    def handle_starttag(self, tag, attrs):
        self.flush()
        self.pieces.append({"markup": self.get_starttag_text() or "<%s>" % tag,
                            "interpretAs": "\n\n" if tag in BLOCKS else ""})

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        self.flush()
        self.pieces.append({"markup": "</%s>" % tag, "interpretAs": "\n\n" if tag in BLOCKS else ""})

    def handle_data(self, data):
        self.data += data

    def close(self):
        super().close()
        self.flush()


def label_pieces(label: str, is_html: bool, new_line_breaks: bool,
                 formula_reads_as: str) -> list[dict]:
    reader = LabelReader(formula_reads_as, new_line_breaks)
    if not is_html:
        reader.text(label)
        return reader.pieces
    reader.feed(label)
    reader.close()
    return reader.pieces


def page_labels(diagram: str) -> list[tuple[str, str, bool, bool]]:
    """The cell id, the label, whether it is HTML and whether a new line of it is a line break, of
    each labelled cell of a page."""
    labels = []
    for cell_id, cell in deck_html.read_cells(diagram).items():
        label = cell.properties.get("label") if cell.properties else cell.element.get("value")
        if not label or not label.strip() or "%slide%" in label:
            continue
        style = cell.element.get("style", "")
        is_html = re.search(r"(^|;)html=1", style) is not None
        new_lines = re.search(r"(?:^|;)nl2Br=([^;]*)", style)
        labels.append((cell_id, label, is_html,
                       not is_html or new_lines is None or new_lines.group(1) == "1"))
    return labels


def plain_context(pieces: list[dict], start: int, length: int, around: int = 40) -> str:
    """The text around an issue, with each tag and formula as it reads, the issue in brackets, and
    `...` where the text goes on.  The offsets are indexes of the text and the markup of the pieces
    joined."""
    before, inside, after, place = "", "", "", 0
    for piece in pieces:
        source = piece.get("text", piece.get("markup", ""))
        reading = piece["text"] if "text" in piece else piece.get("interpretAs", "")
        end = place + len(source)
        if end <= start:
            before += reading
        elif place >= start + length:
            after += reading
        elif "text" in piece:
            before += source[:max(0, start - place)]
            inside += source[max(0, start - place):start + length - place]
            after += source[max(0, start + length - place):]
        else:
            inside += reading
        place = end
    flat = lambda text: re.sub(r"\s+", " ", text)
    before, after = flat(before).lstrip(), flat(after).rstrip()
    if len(before) > around:
        before = "..." + before[-around:].lstrip()
    if len(after) > around:
        after = after[:around].rstrip() + "..."
    return before + "[" + flat(inside) + "]" + after


def python_index(text: str, units: int) -> int:
    """The index of `text` at an offset of LanguageTool, which counts UTF-16 code units, so that
    a character outside the Basic Multilingual Plane, such as an emoji, counts twice."""
    index = count = 0
    while index < len(text) and count < units:
        count += 2 if ord(text[index]) > 0xFFFF else 1
        index += 1
    return index


def ask(server: str, pieces: list[dict], options: dict) -> list[dict]:
    body = urllib.parse.urlencode({
        "data": json.dumps({"annotation": pieces}),
        "language": options["language"],
        "disabledRules": ",".join(options.get("disabledRules", [])),
    }).encode()
    request = urllib.request.Request(server + "/v2/check", data=body)
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            return json.load(response)["matches"]
    except (urllib.error.URLError, OSError) as error:
        raise SystemExit("LanguageTool did not answer at %s (%s); start it with "
                         "brew services start languagetool" % (server, error))


def check_deck(slides, project: str) -> int:
    """Print the issues of the labels of the slides, and return their number."""
    server = os.environ.get("LANGUAGETOOL_SERVER", "http://localhost:8081").rstrip("/")
    options = check_options()
    words = known_words(project)
    numbers, _ = deck_files.number_slides(slides)
    # Each distinct label once, with the places it shows.
    labels: dict[tuple[str, bool, bool], dict] = {}
    for index, slide in enumerate(slides):
        for cell_id, label, is_html, new_line_breaks in page_labels(slide.diagram):
            entry = labels.setdefault((label, is_html, new_line_breaks), {
                "pieces": label_pieces(label, is_html, new_line_breaks, options["formulaReadsAs"]),
                "places": []})
            entry["places"].append((numbers[index], slide.page_name, cell_id))
    entries = [entry for entry in labels.values()
               if any("text" in piece and piece["text"].strip() for piece in entry["pieces"])]
    found = 0
    for entry in entries:
        pieces = entry["pieces"]
        full = "".join(piece.get("text", piece.get("markup", "")) for piece in pieces)
        for match in ask(server, pieces, options):
            start = python_index(full, match["offset"])
            end = python_index(full, match["offset"] + match["length"])
            word = full[start:end]
            spelling = match["rule"].get("category", {}).get("id") == "TYPOS"
            if spelling and word.lower() in words:
                continue
            found += 1
            number, page_name, cell_id = entry["places"][0]
            others = len({place[0] for place in entry["places"]}) - 1
            fixes = ", ".join(fix["value"] for fix in match["replacements"][:5])
            print("slide %s, %s, cell %s%s: %s %s%s" % (
                number, page_name, cell_id,
                " and %d other slide%s" % (others, "s" if others > 1 else "") if others else "",
                "spelling:" if spelling else "grammar or style:", match["message"],
                ("; " + fixes) if fixes else ""))
            print("    %s" % plain_context(pieces, start, end - start))
    print("%d issues in %d distinct labels of %d pages, checked by LanguageTool at %s"
          % (found, len(entries), len(slides), server))
    return found
