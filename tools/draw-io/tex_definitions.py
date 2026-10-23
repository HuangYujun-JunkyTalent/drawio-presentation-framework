"""The TeX definitions a draw.io page needs before MathJax can typeset its formulas.

draw.io's MathJax knows no colour by the name a deck gives it and lacks a few commands of LaTeX
packages, so a page carries the definitions in a label of its own. This module reads the colours
out of a palette, a TeX file of `\\definecolor` lines, and writes the definitions a text uses.
The build of a presentation, the plugin that defines the colours in the draw.io editor and that
`make-mathjax-plugin.py` writes, and the colour configuration that `make-color-config.py` writes
all take the colours from here.

    >>> colours = read_colours(r"\\definecolor{dpgreen}{rgb}{0.0, 0.5, 0.0}")
    >>> colours
    {'dpgreen': '#008000'}
    >>> colour_definition("dpgreen", colours["dpgreen"]) + command_definition("fatsemi")
    '\\\\definecolor{dpgreen}{RGB}{0,128,0}\\\\def\\\\fatsemi{\\\\mathbin{\\\\unicode{x2A1F}}}'
"""
from __future__ import annotations

import dataclasses
import re
import sys

# Commands of LaTeX packages that MathJax does not carry, each defined from what MathJax does
# have. `\fatsemi` is stmaryrd's fat semicolon, which Unicode writes as Z notation schema
# composition, and `\mathds` is dsfont's double-struck alphabet.
MATHJAX_MISSING = {
    "fatsemi": r"\mathbin{\unicode{x2A1F}}",
    "mathds": r"\mathbb",
}
DEFINE_COLOUR = re.compile(r"\\definecolor\s*\{([^}]*)\}\s*\{([^}]*)\}\s*\{([^}]*)\}")


@dataclasses.dataclass(frozen=True)
class ColourDefinition:
    """One `\\definecolor` of a TeX text: the name, the colour as `#rrggbb`, or None for a model
    or values this module does not read, and the model."""
    name: str
    value: str | None
    model: str


def to_red_green_blue(model: str, values: str) -> tuple[float, float, float] | None:
    """The red, green and blue between 0 and 1 of a colour of the models `rgb`, `RGB`, `gray`,
    `Gray`, `cmy` and `cmyk`, converted as the package xcolor converts them, or None."""
    try:
        numbers = [float(value) for value in values.replace(" ", "").split(",") if value]
    except ValueError:
        return None
    if model in ("rgb", "RGB", "cmy") and len(numbers) == 3:
        scale = 255.0 if model == "RGB" else 1.0
        red, green, blue = (number / scale for number in numbers)
        return (1 - red, 1 - green, 1 - blue) if model == "cmy" else (red, green, blue)
    if model in ("gray", "Gray") and len(numbers) == 1:
        grey = numbers[0] / (15.0 if model == "Gray" else 1.0)
        return grey, grey, grey
    if model == "cmyk" and len(numbers) == 4:
        black = numbers[3]
        return tuple(1 - min(1.0, ink + black) for ink in numbers[:3])
    return None


def colour_value(model: str, values: str) -> str | None:
    """A colour of one of the models of `\\definecolor` as `#rrggbb`, or None."""
    if model == "HTML":
        digits = values.strip().lower()
        return "#" + digits if re.fullmatch(r"[0-9a-f]{6}", digits) else None
    channels = to_red_green_blue(model, values)
    if channels is None:
        return None
    return "#%02x%02x%02x" % tuple(max(0, min(255, round(channel * 255))) for channel in channels)


def read_definitions(text: str) -> list[ColourDefinition]:
    """Every `\\definecolor` of a TeX text, in the order of the text."""
    return [ColourDefinition(name, colour_value(model.strip(), values), model.strip())
            for name, model, values in DEFINE_COLOUR.findall(text)]


def read_colours(text: str) -> dict[str, str]:
    """The colours a TeX text defines, as name to `#rrggbb`, the first definition of a name kept."""
    colours = {}
    for definition in read_definitions(text):
        if definition.value is not None:
            colours.setdefault(definition.name, definition.value)
    return colours


def read_palette_definitions(path: str) -> list[ColourDefinition]:
    """The definitions of a palette file, with a warning for each one this module cannot read.

    A colour left out this way would make the build report it as defined by no palette.
    """
    definitions = read_definitions(open(path, encoding="utf-8").read())
    for definition in definitions:
        if definition.value is None:
            print("warning: %s defines %s in the model %s with values that tex_definitions.py "
                  "does not convert, so the colour is left out"
                  % (path, definition.name, definition.model), file=sys.stderr)
    return definitions


def read_palettes(paths: list[str] | None) -> dict[str, str]:
    """The colours of every palette file given, the first file's definition of a name kept."""
    colours = {}
    for path in paths or []:
        for definition in read_palette_definitions(path):
            if definition.value is not None:
                colours.setdefault(definition.name, definition.value)
    return colours


def colour_definition(name: str, value: str) -> str:
    red, green, blue = (int(value[i:i + 2], 16) for i in (1, 3, 5))
    return r"\definecolor{%s}{RGB}{%d,%d,%d}" % (name, red, green, blue)


def command_definition(name: str) -> str:
    return r"\def\%s{%s}" % (name, MATHJAX_MISSING[name])


def everything(colours: dict[str, str]) -> str:
    """The definitions of every colour given and every command MathJax lacks."""
    return ("".join(colour_definition(name, value) for name, value in sorted(colours.items()))
            + "".join(command_definition(name) for name in sorted(MATHJAX_MISSING)))
