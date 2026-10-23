---
name: deck-html
description: How an agent builds the HTML file of a draw.io deck of this repository with `npm run html`, adds a link, a video or an embedded HTML page to a slide as text, sets up the editor of a deck to play its videos and show its pages, and checks the HTML file before handing it over.
read-when:
  - building the HTML file of a slide deck of this repository, or handing a deck over as an HTML file
  - adding a link, a video, an embedded HTML page or an animated edge to a slide of a deck of this repository
---

# Build the HTML file of a deck, give its slides links and videos, and check it in a browser

The paths in this skill are relative to the root of this repository.
`formatsAndTemplates/draw-io/README.md` gives the properties of a link and of a video, the keys of the HTML file, the set-up of the editor plugin and the warnings of the build, and this skill does not restate them.

## Resources of this skill

This skill has no resource folder.
The skill uses nine files of `tools/draw-io/`.

- `build-slides.py` in its modes `html`, `build` and `watch` exports the slides, then writes the HTML file through `deck_html.py`.
- `deck_html.py` reads the links, the videos and the embedded pages from the pages of the deck, and fills in `html-deck.html`.
  `deck_html.py` copies the videos and the pages, with the files that a page names beside it, into `media/` beside the HTML file.
- `html-deck.html` is the page of the HTML file, and its header says how a video or an embedded page sits inside its shape.
- `export-pages.mjs` marks the shape of each cell with a video or a page in the SVG of its page, which the page of the HTML file needs to put the video or the page inside the shape.
- `deck_page_snapshots.py` and `snapshot-pages.mjs` draw the cell of each embedded page as a picture of the page as it first draws, in every build.
- `media-bar.js` holds the bars of controls of a video and of a page, which the editor and the HTML file share.
- `media.plugin.js` is the editor plugin that plays the videos and shows the embedded pages of the cells inside their shapes, and gives the selected one a bar of controls, and every deck loads it from `tools/draw-io/`.
- `deck_media_plugin.py` writes `<deck>/.vscode/deck-folder.plugin.js`, the folder of the deck for the plugin, and every build runs it.

## Standard: the HTML file shows the deck as the build makes it, with its links and its videos

- The HTML file is `build/<deck folder>.html`, unless the user asks for another place, and every local video it plays is in `media/` beside it.
- The HTML file has one page per page of the deck that the build presents, in the order of the deck, as the PDF of the `deck-pdf` skill has.
- Every cell with a link opens its address or shows its page.
- Every cell with the property `video` plays its video inside its shape.
- Every cell with the property `html` shows its page inside its shape, and the page takes the pointer.
- The build prints no warning on a link or a video.
- The section files hold every link and every video, and nothing in `build/` is edited by hand.

## How-to: build the HTML file

1. In the folder of the deck, run `npm run html`.
   A deck whose `package.json` has no command `html` gets the line that `build-slides.py init` writes: the command `pdf` with the mode `pdf` replaced by `html`.
2. Fix what the warnings of the build name, as the table of warnings of `formatsAndTemplates/draw-io/README.md` says.
3. To write the HTML file to another place, run `python3 <path of build-slides.py> html --html <file>` in the folder of the deck.
   The mode reads the title and the palettes from the key `config` of the `package.json` of the deck, as the commands of the deck do.
   The videos then go into `media/` beside that file.

## How-to: add a link, a video or an embedded page to a slide as text

1. Put the video file into `assets/videos/` of the deck, as MP4 with H.264 or as WebM with VP9.
   Put a page into a folder of `assets/`, such as `assets/plots/`, as one HTML file whose scripts are inside it or come from the web.
2. Wrap the cell in a `UserObject` with the properties, as the section on editing a slide as text of `formatsAndTemplates/draw-io/README.md` shows.
   A cell of a video is a shape whose outline the video takes, such as a rectangle, a rounded rectangle or an ellipse.
   A cell of a page has the style `shape=image`, as `formatsAndTemplates/draw-io/README.md` says.
3. Give the shape a still of the video as its fill, as a picture referenced as `assets/<name>`, when the deck is also handed over as a PDF.
4. Keep the shape at the same place and with the same `id` on every step of a slide in steps, so that the video plays on from one step to the next.
5. Run `npm run html` and read its warnings.

An edge whose style holds `flowAnimation=1` moves in the HTML file.

## How-to: set up the editor of a deck to play its videos

A deck is a git repository of its own, nested in this repository, as `formatsAndTemplates/draw-io/README.md` says.
VS Code plays the videos of a deck when it has the folder of the deck open and the `.vscode/settings.json` of the deck loads `../tools/draw-io/media-bar.js`, then `../tools/draw-io/media.plugin.js`, and `.vscode/deck-folder.plugin.js`.
A settings file that lacks an entry of `EDITOR_PLUGINS` of `tools/draw-io/build-slides.py` gets it by hand, in the order of that list, because the mode `vscode` replaces no settings file.
The entry of `view-position.plugin.js` keeps the editor from writing the position of the view, the attributes `dx` and `dy` of `<mxGraphModel>`, into a page that it saves, and no option of draw.io or of the extension does the same.
A page that the editor does not show keeps the XML of its file.
A deck that gets the entry by hand therefore has `dx` and `dy` removed once from every `<mxGraphModel>` of its section files, with no other change to the files.

1. When the deck has no `.vscode/settings.json`, run `python3 ../tools/draw-io/build-slides.py vscode --colours <colour configuration>` in the folder of the deck.
   A deck that `init` started has the file already.
2. Run `npm run build` or `npm run html`, which writes `.vscode/deck-folder.plugin.js` with the folder of the deck.
3. When the build prints that it wrote the plugin, tell the user that the extension will ask again to allow it.

The section on VS Code of `formatsAndTemplates/draw-io/README.md` says which videos the editor plays.

## Required action: check the HTML file before handing it over

1. Open the HTML file in the headless Chromium of the Playwright of `tools/`, at the address of a slide with a video, such as `#12`.
2. Read in the page that every `<video>` sits inside a group `g[data-cell-id]` of the SVG, plays, and has the `object-fit` of its `fit`, `contain`, `fill` or `cover`.
   Read as well that every `iframe.cell-embed` sits inside such a group and that its page has loaded.
   Check with `document.elementFromPoint` at several points of each page, its corners as well as its centre, that the point reaches the `<iframe>`.
3. Take a screenshot of each slide with a video or a link, and look at it.
4. Press the key Right through every page, and check that the label at the bottom left reaches the last slide.
   The label reads the number of the last slide over the total, from the counts that the build prints, `N slides on P pages, and B backup slides on Q pages`.
   Without a backup section the label reads `<total>/<total>`, and with one `<last>/<total>-<total with backup>`.
   When the last slide has steps, `-<step>` follows the number of the slide, such as `3-2/3`, or `50-2/45-59` with a backup section.
   The number of presses before the label stops changing is the number of pages less one.
5. Say in the reply that the check ran in Chromium, and name the browser in which the user presents when the user has named one.

## Never-do

- Do not write a link or a video into the files of `build/`, because the build writes them again.
- Do not add `.vscode/deck-folder.plugin.js` to git, because it holds the folder of the deck on one machine.
- Do not copy `media.plugin.js` into a deck, because every deck loads the one in `tools/draw-io/`.
