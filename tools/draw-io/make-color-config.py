#!/usr/bin/env python3
"""Write a draw.io colour configuration from the colours a deck actually uses.

draw.io takes three colour settings in its configuration. `colorNames` gives a name to a hex
value, which the colour dialog then shows as a tooltip. `presetColors` fills the top row of that
dialog. `customColorSchemes` adds rows of swatches, each a fill, a stroke and a font colour, to the
top of the Format panel's Style tab. This script reads a `.drawio` file, counts the colours in it,
names them, and writes the three settings as one JSON object ready to paste into a configuration.

A name comes from two places, in order. A colour that a LaTeX file gives a `\\definecolor` to
keeps the name of that definition as written, because it is the deck's own word for it. Anything
left is named after its hue, as `family_names` says, so that no two names differ by a shade word
alone.

  python3 make-color-config.py deck.drawio.xml \
      --out ../../formatsAndTemplates/draw-io/named-colors-deck.json \
      --definecolor ../../formatsAndTemplates/draw-io/example-palette.tex
"""
import argparse
import collections
import colorsys
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import tex_definitions  # noqa: E402

HUE_NAMES = [(15, "Red"), (45, "Orange"), (70, "Yellow"), (160, "Green"), (200, "Cyan"),
             (250, "Blue"), (290, "Violet"), (330, "Magenta"), (361, "Red")]


def read_definecolor(paths):
    """The colours the given LaTeX files name, as hex to name, read by `tex_definitions.py`.

    The first file that defines a value names it.
    """
    named = {}
    for path in paths or []:
        for definition in tex_definitions.read_palette_definitions(path):
            if definition.value is not None:
                named.setdefault(definition.value, definition.name)
    return named


def count_colours(path):
    text = open(path, encoding="utf-8").read()
    counts = collections.Counter()
    for pattern in (r"(?:fillColor|strokeColor|fontColor)=(#[0-9a-fA-F]{6})",
                    r"font color=&quot;(#[0-9a-fA-F]{6})",
                    r"textcolor\{(#[0-9a-fA-F]{6})\}",
                    r"color:\s*(#[0-9a-fA-F]{6})"):
        for match in re.finditer(pattern, text):
            counts[match.group(1).lower()] += 1
    return counts


def channels(value: str) -> tuple[float, float, float]:
    """The red, the green and the blue of a value `#rrggbb`, each from 0 to 1."""
    return tuple(int(value[i:i + 2], 16) / 255 for i in (1, 3, 5))


def hue_name(value):
    red, green, blue = channels(value)
    hue, lightness, saturation = colorsys.rgb_to_hls(red, green, blue)
    # The saturation of HLS grows as a colour nears white, so a near-white colour is a grey by its
    # chroma, the largest channel less the smallest, and a pale tint such as #dae8fc keeps its hue.
    chroma = max(red, green, blue) - min(red, green, blue)
    if saturation < 0.12 or (lightness > 0.9 and chroma < 0.05):
        return "Black" if lightness < 0.25 else ("White" if lightness > 0.9 else "Grey")
    degrees = hue * 360
    return next(name for limit, name in HUE_NAMES if degrees < limit)


def luminance(value):
    """How light a colour is, 0 for black and 1 for white."""
    red, green, blue = channels(value)
    return 0.299 * red + 0.587 * green + 0.114 * blue


def swatch_rows(ordered, count=8):
    """Two rows for the Format panel: filled shapes, then outlines.

    A swatch sets the fill, the stroke and the font colour together, so the font is chosen for
    contrast against the fill.  A colour close to white is left out of both rows, because a white
    fill with a white stroke, or a white outline, is a swatch that makes a shape vanish on the
    page and looks empty in the panel.
    """
    usable = [value for value in ordered if luminance(value) < 0.93][:count]
    filled = [{"fill": value, "stroke": value,
               "font": "#ffffff" if luminance(value) < 0.6 else "#000000"}
              for value in usable]
    outlined = [{"fill": "none", "stroke": value, "font": value} for value in usable]
    return [filled, outlined]


def family_names(base, members):
    """The names of the colours of one hue: the plain name of the hue when it has one colour, and
    the name followed by the hex value for each colour of a hue of several."""
    if len(members) == 1:
        return {members[0]: base}
    return {value: "%s %s" % (base, value[1:].upper()) for value in members}


def name_colours(counts, defined):
    """One name per colour: the name of a LaTeX file for a colour it names, and otherwise a name
    of the family of its hue."""
    families = collections.defaultdict(list)
    names = {}
    for value, _uses in sorted(counts.items(), key=lambda pair: -pair[1]):
        if value in defined:
            names[value] = defined[value]
            continue
        families[hue_name(value)].append(value)
    for base, members in families.items():
        names.update(family_names(base, members))
    return names


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("deck")
    parser.add_argument("--out", required=True)
    parser.add_argument("--definecolor", action="append",
                        help="a LaTeX file whose \\definecolor lines name the colours, which "
                             "may be given more than once")
    parser.add_argument("--least", type=int, default=8,
                        help="leave out a colour used fewer times than this")
    args = parser.parse_args()

    counts = count_colours(args.deck)
    kept = {value: uses for value, uses in counts.items() if uses >= args.least}
    names = name_colours(kept, read_definecolor(args.definecolor))
    ordered = sorted(kept, key=lambda value: -kept[value])

    config = {
        "colorNames": {value[1:].upper(): names[value] for value in ordered},
        "presetColors": [value[1:].upper() for value in ordered],
        "customColorSchemes": swatch_rows(ordered),
    }
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(config, handle, indent=2)
        handle.write("\n")
    print("%d colours of %d kept, %d uses" % (len(kept), len(counts), sum(kept.values())))
    for value in ordered:
        print("  %s  %-28s %5d uses" % (value, names[value], kept[value]))


if __name__ == "__main__":
    main()
