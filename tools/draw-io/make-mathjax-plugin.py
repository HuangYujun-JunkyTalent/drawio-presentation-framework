#!/usr/bin/env python3
"""Write the draw.io plugin that defines the deck's colours and commands for the whole editor.

draw.io gives a file no place for TeX definitions: it sets MathJax up once when the editor
starts, and nothing in a file reaches that set-up. MathJax keeps a definition for as long as the
editor runs, though, so a definition typeset once holds for every page of every file opened
after it. The plugin this script writes hands the definitions to draw.io's own queue of
typesetting in a hidden element, the way draw.io typesets a label, and draws the page again,
so a page with no definitions of its own shows its colours.

The plugin also starts every page the editor creates, and the page of a new empty file, with
mathematical typesetting on. Such a page starts with it off, so a formula typed into it stays
raw text. A page read from a file keeps its own switch.

The definitions come from two places and from nowhere else: the `\\definecolor` lines of the
palettes, and `MATHJAX_MISSING` of `tex_definitions.py` beside this script, the commands MathJax
lacks. `build-slides.py` writes the same definitions into each page it exports, so the plugin is
for the editor alone.

  python3 make-mathjax-plugin.py --palette ../../formatsAndTemplates/draw-io/example-palette.tex \
      --palette path/to/other-palette.tex

The editor loads one plugin for every presentation it opens, so the plugin is written from the
palettes of all of them at once, and a run with one palette drops the colours of the others.
A name that two palettes define keeps the value of the first palette given.

The plugin is loaded by the setting `hediet.vscode-drawio.plugins` of the VS Code extension,
which asks once whether to allow it, and again whenever the file changes.
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import tex_definitions  # noqa: E402

PLUGIN = """\
// Written by tools/draw-io/make-mathjax-plugin.py from
// %(sources)s.
// Do not edit by hand: change the palette and run the script again.
//
// Defines the deck's colours and commands for every page of every file the draw.io editor
// opens, and starts every new page with mathematical typesetting on.
Draw.loadPlugin(function (ui) {
  var DEFINITIONS = %(definitions)s;
  var graph = ui.editor.graph;

  // A page the editor creates takes this value, and a page read from a file keeps its own.
  // Switching mathematics on a page copies the switch into the default, so the default is put
  // back, and an empty file is read as a model whose page carries no switch, so it is given one.
  graph.defaultMathEnabled = true;
  var setMathEnabled = ui.setMathEnabled;
  ui.setMathEnabled = function (value) {
    setMathEnabled.apply(this, arguments);
    this.editor.graph.defaultMathEnabled = true;
  };
  if (typeof ui.emptyDiagramXml === 'string') {
    ui.emptyDiagramXml = ui.emptyDiagramXml.replace('<mxGraphModel>', '<mxGraphModel math="1">');
  }

  // The definitions go through draw.io's own queue of typesetting, in a hidden element, the way
  // draw.io typesets a label.  The queue runs one typesetting at a time, and MathJax loads parts
  // of TeX input on demand, so a typesetting of its own beside draw.io's would race it and leave
  // a command half loaded.  Once the element is typeset, the definitions are in the TeX input
  // that every label is typeset with, and the page is drawn again, so that a label typeset
  // before them shows its colours.
  var tries = 0;
  function define() {
    if (typeof Editor === 'undefined' || typeof Editor.MathJaxRender !== 'function') {
      if (tries++ < 600) window.setTimeout(define, 100);
      return;
    }
    var holder = document.createElement('div');
    holder.style.cssText = 'position:absolute;left:-10000px;top:0;visibility:hidden';
    holder.textContent = '\\\\(' + DEFINITIONS + '\\\\)';
    document.body.appendChild(holder);
    var previous = Editor.onMathJaxDone;
    var hook = function () {
      previous.apply(this, arguments);
      finish();
    };
    var finish = function () {
      if (holder.parentNode == null || holder.querySelector('mjx-container') == null) return;
      // A listener that hooked in after this one calls this one, so this one leaves only when
      // it is the last.
      if (Editor.onMathJaxDone === hook) Editor.onMathJaxDone = previous;
      holder.parentNode.removeChild(holder);
      // No file of the editor reads this flag.  A headless check of the definitions reads it to
      // know that they are loaded.
      window.__deckDefinitionsLoaded = true;
      graph.refresh();
    };
    Editor.onMathJaxDone = hook;
    Editor.MathJaxRender(holder);
    finish();
  }
  define();
});
"""


def definitions(palettes):
    """The TeX that defines every colour of the palettes and every command MathJax lacks."""
    return tex_definitions.everything(tex_definitions.read_palettes(palettes))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--palette", action="append", required=True,
                        help="a TeX file of \\definecolor lines.  Give every palette the "
                             "presentations use, once each.")
    parser.add_argument("--out", default=os.path.join(HERE, "mathjax-definitions.plugin.js"))
    args = parser.parse_args()
    palettes = args.palette
    for path in palettes:
        if not os.path.isfile(path):
            raise SystemExit("the palette %s does not exist" % path)
    text = definitions(palettes)
    sources = "%s and MATHJAX_MISSING of tex_definitions.py" % ", ".join(
        os.path.basename(path) for path in palettes)
    with open(args.out, "w", encoding="utf-8") as handle:
        handle.write(PLUGIN % {"sources": sources, "definitions": json.dumps(text)})
    print("%s: %d characters of definitions" % (args.out, len(text)))


if __name__ == "__main__":
    main()
