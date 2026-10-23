"""Write the pictures of a deck into its slide files as data, so that the draw.io editor shows them.

The build writes every picture into the slides from its file by itself, also for a cell that this
script wrote, so the slides show the current file either way, and only the editor needs this
script, for the reason that `deck_pictures.py` gives.

    python3 embed-pictures.py <deck folder>

The script reads the section files `<deck folder>/sections/*.drawio.xml`, or
`<deck folder>/slides.drawio.xml` when the deck has no folder `sections/`, as the build does.
`--slides-dir` and `--deck`, or else the key `config` of the deck's `package.json`, name another
folder or file, as they do for `build-slides.py`.  The script writes the picture of each cell of
those files as data, as `deck_pictures.py` says, and names each picture whose file does not exist.
"""
import argparse
import glob
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import deck_files  # noqa: E402
import deck_pictures  # noqa: E402


def slide_files(deck, slides_dir, single):
    """The files that hold the pages of the deck, the section files before a single file, as the
    build reads them."""
    location = deck_files.slides_location(deck, slides_dir, single)
    if location is None:
        raise SystemExit("%s holds no file %s/*.drawio.xml and no %s" % (deck, slides_dir, single))
    path, is_folder = location
    if not is_folder:
        return [path]
    paths = sorted(glob.glob(os.path.join(path, "*" + deck_files.SUFFIX)))
    if not paths:
        raise SystemExit("%s/ holds no file *%s" % (path, deck_files.SUFFIX))
    return paths


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("deck", help="the deck folder")
    parser.add_argument("--slides-dir",
                        help="the folder of one file per section, preferred when it exists, from "
                             "config.slides-dir of package.json, or %s by default"
                             % deck_files.SLIDES_DIR)
    parser.add_argument("--deck", dest="single",
                        help="a multi-page file, read when the slides folder is absent, from "
                             "config.deck of package.json, or %s by default"
                             % deck_files.SINGLE_FILE)
    args = parser.parse_args()
    deck = os.path.abspath(args.deck)
    try:
        config = deck_files.read_config(deck)
    except ValueError as error:
        raise SystemExit(str(error))
    paths = slide_files(deck, deck_files.setting("slides-dir", args.slides_dir, config),
                        deck_files.setting("deck", args.single, config))
    missing = set()
    for path in paths:
        text = open(path, encoding="utf-8").read()
        embedded = deck_pictures.embed_text(text, deck)
        if embedded.text != text:
            open(path, "w", encoding="utf-8").write(embedded.text)
        if embedded.written:
            noun = "picture" if embedded.written == 1 else "pictures"
            print("%s: %d %s written as data"
                  % (os.path.relpath(path, deck), embedded.written, noun))
        missing.update(embedded.missing)
    for name in sorted(missing):
        print("warning: %s does not exist, so its cells stay as they are" % name, file=sys.stderr)


if __name__ == "__main__":
    main()
