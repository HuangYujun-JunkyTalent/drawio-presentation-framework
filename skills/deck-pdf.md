---
name: deck-pdf
description: How an agent builds a PDF of a draw.io deck of this repository with `npm run pdf`, which prints the built SVGs with the slide numbers filled in and the hidden pages left out, and how the agent checks the PDF before handing it over.
read-when:
  - building a PDF of a slide deck of this repository, or handing a deck over as a PDF
---

# Build the PDF of a deck from its built slides, and check its pages, its numbers and its formulas

The paths in this skill are relative to the root of this repository.
`README.md` gives the steps that start a presentation from the template and build it.

## Resources of this skill

This skill has no resource folder.
The skill uses two scripts of `tools/draw-io/`.

- `build-slides.py` in its modes `pdf` and `build` exports the slides, then runs `print-pdf.mjs`.
- `print-pdf.mjs` prints the SVGs of `build/slides/` into one PDF, one page per SVG, at the size of the slide, through the Chromium of the Playwright of `tools/`.

## Standard: the PDF shows the deck as the build makes it

- The PDF has one page per page of the deck that the build presents, in the order of the deck.
- Each slide number and each total reads as the build fills in `%slide%` and `%slides%`.
- A page whose name ends in `-hide` is absent and takes no number, as `tools/draw-io/deck_files.py` says.
- The total leaves out the slides of a section file whose name contains `backup-slides`, which go on with the numbers and show the total with the backup slides after a dash, as the same file says.
- The formulas render, and no page shows raw TeX.
- The bookmarks of the PDF have three levels: a section per section file, under it each slide at its first page, and under a slide in steps each of its pages, from the `build/outline.json` that the build writes.
- The PDF is `build/<deck folder>.pdf` in the folder of the deck, unless the user asks for another place.

## How-to: build the PDF

1. In the folder of the deck, run `npm run pdf`, or `npm run build`, which writes the HTML file as well.
   A deck whose `package.json` has no command `pdf` gets the line that `build-slides.py init` writes: the command `build` with the mode `build` replaced by `pdf`.
2. Fix what the warnings of the build name, as the table of warnings of `formatsAndTemplates/draw-io/README.md` says.
3. To write the PDF to another place, run `python3 <path of build-slides.py> pdf --pdf <file>` in the folder of the deck.
   The mode reads the title and the palettes from the key `config` of the `package.json` of the deck, as the commands of the deck do.

The mode `pdf` needs the `playwright-chromium` that `npm install` in `tools/` installs once for every deck.

## Required action: check the PDF before handing it over

1. Read the page count and the page size with `pdfinfo build/<deck folder>.pdf`.
   The count equals the page count that the build printed.
2. List the slide numbers with `pdftotext build/<deck folder>.pdf - | grep -E '^[0-9]+/[0-9]+(-[0-9]+)?$'`, and check that they rise to the total and past it in the backup slides.
3. Render pages with `pdftoppm -r 40 -png build/<deck folder>.pdf <output folder>/page`, with an output folder outside the repository.
   Look at the title slide and at each page with formulas.
4. Print the bookmarks with `pdftohtml -xml -i -q -stdout build/<deck folder>.pdf`, and compare the `<outline>` part with the outline that `npm run outline` prints.
