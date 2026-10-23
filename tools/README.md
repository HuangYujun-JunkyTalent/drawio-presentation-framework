# tools: the build of a presentation, the plugins of the editor, and the one install of Playwright

This folder holds the tools that every presentation of the repository runs.
The formats that a presentation starts from, the template, the palette and the colour configurations, are in `../formatsAndTemplates/`.

```
tools/
├── package.json            Playwright, the one npm install of the repository
├── package-lock.json       the versions installed
├── node_modules/           written by npm install, which git does not track
└── draw-io/                the build of a draw.io presentation and the plugins of the editor
```

## Install once for every presentation

```sh
cd tools
npm install
```

A presentation folder installs nothing.
Its `package.json` holds its commands, each of which runs `draw-io/build-slides.py`, and its title and its palettes under the key `config`, as `../formatsAndTemplates/draw-io/README.md` says.
The build runs the headless Chromium of the Playwright of this folder.
The section on starting a presentation of the same README names the version of Node.js that Playwright needs, and the draw.io viewer that the build draws the slides with.

## draw-io: the build and the plugins

| file | what it is |
|---|---|
| `build-slides.py` | starts a presentation as a repository of its own with `init`, writes its HTML file and its PDF with `build`, the HTML file alone with `html` and on every save with `watch`, the PDF alone with `pdf`, prints the sections, slides and pages with `outline`, checks the spelling and the grammar of its labels with `check`, and writes its VS Code settings with `vscode` |
| `deck_html.py` | writes the HTML file of a built deck: reads the links, the videos and the embedded pages of the cells, with the properties its header lists, and copies the videos and the pages into `media/` beside the file |
| `html-deck.html` | the page of the HTML file, with the outline and the addresses of the pages that its header lists, the keys of the table of keys of `../formatsAndTemplates/draw-io/README.md`, and the videos and the embedded pages inside their shapes |
| `deck_files.py` | the names of the section files and of the pages, how the slides are numbered from them, the pages that `-hide` leaves out, and the reading of the key `config` of the `package.json` of a deck |
| `tex_definitions.py` | the TeX definitions a page's formulas need: the colours of a palette, and the commands MathJax lacks |
| `export-pages.mjs` | the export of each page to an SVG in `build/slides/` through the draw.io viewer of the extension, with the cache and the settings that the section "Start a presentation with three commands" of `../formatsAndTemplates/draw-io/README.md` gives. The export marks the shape of each cell with a video or a page for the HTML file, and copies the rules of the list markers of `list-styles.plugin.js` into each slide with a list |
| `deck_page_snapshots.py` | draws the cell of each embedded page, in the assembled deck, as a picture of the page as it first draws, so that the PDF and the HTML file show what the page shows |
| `snapshot-pages.mjs` | takes those pictures in headless Chromium, at the size of each cell on the slide |
| `print-pdf.mjs` | prints the SVGs of a build into one PDF, one page per SVG |
| `make-mathjax-plugin.py` | writes `mathjax-definitions.plugin.js` from the palettes |
| `mathjax-definitions.plugin.js` | the plugin of the draw.io editor that defines the colours on every page and switches on mathematics on every new page, generated |
| `label-colours.plugin.js` | the plugin that lets the text, the bullets and the formulas of a label show its font colour in the VS Code extension, whose page gives them the colour of the interface |
| `single-page.plugin.js` | the plugin that keeps a page of 1920 by 1080 at one page in the page view of the editor |
| `click-through.plugin.js` | the plugin that lets a click on the empty inside of a shape or a text box without fill reach the shape behind it |
| `edit-at-click.plugin.js` | the plugin that keeps the view still when a double-click starts editing a label, and puts the caret where the double-click was instead of selecting the whole label |
| `language-check.plugin.js` | the plugin that underlines the spelling and the grammar of the label being edited, from LanguageTool on this machine, with its fixes on the right button |
| `deck_language_check.py` | the check of the spelling and the grammar of every label of a deck, `npm run check`, which reads the rules of `language-check.plugin.js` |
| `view-position.plugin.js` | the plugin that leaves the position of the view, `dx` and `dy`, out of every page that the editor saves, so a scroll alone changes no section file |
| `list-styles.plugin.js` | the plugin that gives a list made with the list buttons of the editor the template's style of its level, and adds the menu List style beside those buttons |
| `media-bar.js` | the bars of controls of a video and of an embedded page, with the field of the time, which the editor loads before `media.plugin.js` and the build writes into the HTML file |
| `media.plugin.js` | the plugin that plays the video and shows the HTML page of a cell inside its shape, and gives the selected one a bar of controls, which every presentation loads from here |
| `deck_media_plugin.py` | writes `<deck>/.vscode/deck-folder.plugin.js`, the one line that tells `media.plugin.js` the folder of the deck, which every build runs and git leaves out |
| `embed-pictures.py` | writes each picture `image=assets/<name>` of the slide files of a deck, `sections/*.drawio.xml` or `slides.drawio.xml`, or the folder or the file that the key `config` of its `package.json` names, into its cell as data, with the name kept in the style key `assetSource`, because the editor of VS Code finds no picture beside the drawing. The build writes the pictures from their files by itself, so only the editor needs the script |
| `deck_pictures.py` | the writing of a picture `assets/<name>` into its cell as data, which the build and `embed-pictures.py` share |
| `make-color-config.py` | writes a colour configuration of the editor from the colours a `.drawio` file uses |

`../formatsAndTemplates/draw-io/README.md` gives the commands of a presentation, the page names, the formulas, the links and the videos, the set-up of VS Code per presentation with the ten plugins, and the warnings of the build.
