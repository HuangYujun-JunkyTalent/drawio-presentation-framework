#!/usr/bin/env python3
"""Write the one line that tells the shared media plugin of the editor the folder of a deck.

`media.plugin.js` beside this script plays the videos and shows the embedded pages of the cells
inside their shapes in the draw.io editor.  The page of the editor in the VS Code extension does
not know the folder of the drawing it shows, so each deck carries
`<deck>/.vscode/deck-folder.plugin.js`, which sets `window.mediaPluginDeckFolders` to the
absolute folder of the deck.  The `.vscode/settings.json` of the deck loads both files when VS
Code has the deck open as its folder.

The build of `build-slides.py` writes the line on every run, and its text changes only when the
deck moves, so the extension asks again whether to allow it only then.  The line holds a path of
this machine, so the `.gitignore` of the deck leaves it out.  To write the line without a build,
run the script:

    python3 deck_media_plugin.py path/to/deck     # the working directory when the deck is left out
"""
from __future__ import annotations

import argparse
import json
import os

FOLDER_PLUGIN = os.path.join(".vscode", "deck-folder.plugin.js")
HEADER = ("// Written by tools/draw-io/deck_media_plugin.py on every build: the folder of this deck, "
          "which\n// tools/draw-io/media.plugin.js reads.  Git leaves this file out.\n")


def write_deck_folder_plugin(deck: str) -> tuple[str, bool]:
    """Write the line of the deck, and return its path and whether its text changed."""
    deck = os.path.abspath(deck)
    target = os.path.join(deck, FOLDER_PLUGIN)
    text = HEADER + "window.mediaPluginDeckFolders = %s;\n" % json.dumps([deck])
    if os.path.exists(target):
        with open(target, encoding="utf-8") as handle:
            if handle.read() == text:
                return target, False
    os.makedirs(os.path.dirname(target), exist_ok=True)
    with open(target, "w", encoding="utf-8") as handle:
        handle.write(text)
    return target, True


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("deck", nargs="?", default=".", help="the deck folder")
    deck = parser.parse_args().deck
    if not os.path.isdir(deck):
        raise SystemExit("the deck folder %s does not exist" % os.path.abspath(deck))
    target, changed = write_deck_folder_plugin(deck)
    print("%s %s" % (target, "written" if changed else "unchanged"))


if __name__ == "__main__":
    main()
