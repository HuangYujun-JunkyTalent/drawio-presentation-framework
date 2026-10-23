# draw.io presentations: the slide template, the build, and the editor set-up

A presentation of this repository is a folder of draw.io files, one per section, that a person edits in the draw.io editor and an agent edits as XML text.
A build turns the folder into two things, both made of the same SVG of each page.
The first is one HTML file that presents the slides in a browser with their links, videos and interactive pages, and the second is a PDF.
This folder holds what every such presentation shares as a format: the template of the slides, the palette and the colour configurations of the editor.
The build, the plugins of the editor and the scripts that write the colour settings are tools, in `tools/draw-io/` of the repository, which `tools/README.md` lists.

| file | what it is |
|---|---|
| `slide-format.drawio.xml` | the template: six pages to copy slides from |
| `example-palette.tex` | an example palette, to replace with that of your own decks: the `\definecolor` lines of the colours that the formulas of the co-design decks of the author name, whose header says where they come from |
| `named-colors.template.jsonc` | a colour configuration of the editor to copy, with the names of the parts of draw.io that read its three settings |
| `named-colors-example.json` | an example colour configuration of the editor, to replace with that of your own decks: the 26 colours of a deck of the author, with the names of their `\definecolor` for the colours of the example palette and of the codesign package, such as `dpgreen` and `cdF`, and names edited by hand for the others, so that no two names differ by a bracket or a shade word alone |

## Start a presentation with three commands

The build needs Python 3, git, Node.js 20 or later with npm, which Playwright needs, and VS Code with the extension `hediet.vscode-drawio`.
The build draws each page with the diagrams.net viewer, the library of draw.io that draws a page in a web page, in the headless Chromium that `npm install` in `tools/` fetches.
The viewer is the copy that the newest installed extension bundles, so the build needs no network and draws with the draw.io of the editor.
`DRAWIO_VIEWER` names another `viewer-static.min.js`, as a path, a `file:` address or an address on the web, and without the extension the build loads the viewer from `viewer.diagrams.net`.
A viewer on this machine finds MathJax, the stencils and the pictures in the folder `webapp` of draw.io around it, so it sits in `webapp/js/`.
The build stops on a local viewer outside `webapp/js/` of draw.io, and on a path that names no file.
The three commands below run once Playwright is installed in `tools/`, as `tools/README.md` says.

```sh
python3 tools/draw-io/build-slides.py init my-talk --title "My talk" \
    --palette formatsAndTemplates/draw-io/example-palette.tex
cd my-talk
npm run build
```

`init` takes the folder relative to where it runs or as an absolute path, and creates the missing parent folders.
`init` refuses a folder that already holds a `package.json`, a `slides.drawio.xml`, a `sections/` that is not empty or a `.vscode/settings.json`, and a path below a file.
`init` prints what it wrote:

```
sections/1-my-talk.drawio.xml written with the pages title-slide-1, section-divider-1, title-and-body-1
package.json and .vscode/settings.json written, and .../my-talk is a git repository of its own
next, in .../my-talk: npm run build, after npm install in .../tools once. Open the folder in VS Code to edit the slides.
```

A presentation is a git repository of its own, nested in this repository at the place `init` gives it, and the `.gitignore` of this repository leaves its folder out, because it tracks only the folders it names.
The history, the remote and the commits of a presentation are its own, and this repository holds what every presentation shares: the template, the palettes and the tools.
The user makes the first commit of a presentation and adds its remote.

The new folder holds three slides, copied from the template: a title slide, a section divider and a slide of a title and a body.
Their text is placeholders in grey italic, to overwrite in the `value` of each cell.
The placeholders are the title, the date, the author and the affiliation of the title slide, and the title and the list of the body, whose formula and whose example of a word in italic stay as they are.

`--palette` names a palette, as the section on colours below says, and may be given more than once.
A palette's path is relative to the folder `init` runs in, and `init` writes it under the key `config` of `package.json` in the form of the paths of the tools, as the end of this section says.
Leave `--palette` out when the formulas use no colour names, or use them only on pages whose own `Equation colours` layer defines them, as the layer of `title-and-body-1` defines `dpgreen` and `dpred`.
`npm run build` prints what it did:

```
3 pages assembled from sections: 3 slides on 3 pages, and 0 backup slides on 0 pages
viewer: .../hediet.vscode-drawio-<version>/drawio/src/main/webapp/js/viewer-static.min.js
3 pages exported to .../my-talk/build/slides, 0 of them unchanged and copied from the cache
.vscode/deck-folder.plugin.js written. VS Code asks once to allow it.
.../my-talk/build/my-talk.html written: 3 pages, 0 links, 0 videos, 0 embedded pages, 0 files beside the pages
3 pages printed to .../my-talk/build/my-talk.pdf
```

The line of `deck-folder.plugin.js` shows only when the build writes the folder of the presentation for the media plugin for the first time or after the folder has moved, as the section on VS Code below says.
The build exports several pages at once and copies a page that has not changed since the last build from `build/export-cache/`, so a build after an edit exports the edited pages alone.
`EXPORT_FRESH=1 npm run build` exports every page again.
A viewer on the web keeps the SVGs of the cache until `EXPORT_FRESH=1`, because the key of the cache holds the address alone of such a viewer.
`EXPORT_WORKERS` sets the number of pages exported at once, and `PAGE_WAIT` the most milliseconds that a page may take to draw, with the defaults that the header of `tools/draw-io/export-pages.mjs` gives.
The pictures of the embedded pages have the waits `SNAPSHOT_LOAD_WAIT` and `SNAPSHOT_WAIT` of their own, as the header of `tools/draw-io/snapshot-pages.mjs` says.

The pages count every step of a slide, so a slide in three steps is one slide on three pages.
`--outline` after `build`, `html`, `pdf` or `watch` in `package.json`, or `npm run outline` without a build, also prints the outline: each section file, and under it each slide with its number as the deck shows it and its pages.

Six commands of `package.json` work on the presentation:

| command | what it does |
|---|---|
| `npm run build` | exports the slides, then writes the HTML file and the PDF |
| `npm run html` | exports the slides, then writes `build/<folder>.html`, which presents the deck in a browser with an outline, the links, the videos and the embedded pages, and copies the videos and the pages into `build/media/` |
| `npm run pdf` | exports the slides, then prints them into `build/<folder>.pdf`, with bookmarks of the sections, of their slides and of the pages of a slide in steps |
| `npm run watch` | writes the HTML file again whenever a section file is saved, renamed, added or deleted, a file under `assets/` changes, or a palette changes. `watch` reads the key `config` of `package.json` at its start, so a change of the key takes effect when `watch` starts again |
| `npm run outline` | prints the sections, the slides and their pages, without building |
| `npm run check` | checks the spelling and the grammar of every label with LanguageTool on this machine, and prints each issue with its slide, as the section on spelling below says, and ends with exit status 1 when it finds an issue |

The `package.json` of a presentation holds these commands and no dependencies.
Each command runs `tools/draw-io/build-slides.py` with its mode alone, such as `python3 '../tools/draw-io/build-slides.py' build`.
The facts of the presentation that the commands share stand once, under the key `config`:

```json
"config": {
  "title": "My talk",
  "palette": ["../formatsAndTemplates/draw-io/example-palette.tex"]
}
```

`init` writes `title` and the palettes of `--palette`, and writes `slides-dir` and `deck` only for a slides folder other than `sections` or a file other than `slides.drawio.xml`, the values of `--slides-dir` and `--deck`.
An option given after the `--` of `npm run` takes the place of its key, so `npm run html -- --title "Another title"` gives the HTML file another title.
`--palette` given once or more adds its palettes after those of the key instead, as in `npm run html -- --palette extra.tex`.
An unknown key of `config`, or a value of the wrong kind, such as one path in place of a list of palettes, stops each of the six commands with a message that names the key.
`init` writes into `package.json` and into `.vscode/settings.json` the paths of the tools relative to the presentation when the presentation lies inside the folder of this repository, so the two folders move together.
A presentation outside the folder gets absolute paths.
A clone of a presentation therefore goes inside a clone of this repository, at the same place, such as `my-talk/` at the root of the clone.

## A presentation folder holds its sections and what the build writes

```
my-talk/
├── .git/                             the repository of the presentation
├── .gitignore                        leaves out what the build, macOS and Claude Code write
├── .vscode/settings.json             the editor set-up of the presentation, written by init or by vscode
├── .vscode/deck-folder.plugin.js     written by the build: this folder for the media plugin, left out of git
├── package.json                      the commands, and the title and the palettes under config
├── sections/
│   ├── 1-opening.drawio.xml          section 1, edited by hand
│   └── 2-results.drawio.xml          section 2, edited by hand
├── assets/                           pictures referenced as assets/<name>, and videos, when there are any
└── build/                            written by the build
    ├── <folder>.html, media/         the HTML file and the videos and pages it shows
    ├── <folder>.pdf                  the PDF
    ├── slides/slide-NN.svg           one SVG per page, which both are made of
    ├── assembled.drawio.xml          every page in one file
    ├── outline.json                  the bookmarks of the PDF
    ├── export-cache/                 the SVG of each page, kept for the next build
    └── page-snapshots/               a picture of each embedded page
```

Edit only the section files and the pictures.
The build writes everything else again on every run.
A picture is a cell whose style holds `shape=image;image=assets/<name>`, and the build writes the picture into the page as data from its file, because the export reads no file beside the page.
The editor of VS Code shows such a picture only after `tools/draw-io/embed-pictures.py` has written it into its cell, with its name kept in the style key `assetSource`.
The build writes the picture of such a cell from its file again, so a changed picture shows in the next build.
A presentation of a single file `slides.drawio.xml` instead of `sections/` builds as well.

## The file names order the sections, and the page names give the slides

A section file is named `<number>-<name>.drawio.xml`, and the numbers order the sections.
Two files may not share a number, and the build stops with an error when they do.

A page is named `<name>-<step>`, such as `point-wise-probability-2`.
The pages present in the order of the files, and inside a file in the order of its page tabs in draw.io.
Pages that follow one another under one name are one slide shown in steps, which is how a slide makes something appear, so they share one slide number.

| page name | slide number shown |
|---|---|
| `title-slide-1` | 1/4 |
| `point-wise-probability-1` | 2/4 |
| `point-wise-probability-2` | 2/4 |
| `composition-1` | 3/4 |
| `summary-1` | 4/4 |

Nobody numbers a slide by hand.
Moving a page tab moves a slide, and renaming a file moves a section.
A name that ends in no `-<step>` is step 1.
Give two different slides two different names, or the build takes them for the steps of one slide.
A page whose name ends in `-hide`, such as `reset-metrics-example-1-hide`, stays in its file and out of the deck, and takes no slide number.

## The slide number reads current over total

A text cell whose value holds `%slide%` gets the slide's number, and `%slides%` gets the number of slides.
The template's number cell holds `%slide%/%slides%`, so the slide shows `45/61`.
The number of slides leaves out the slides of a section file whose name contains `backup-slides`, such as `7-backup-slides.drawio.xml`.
Those slides go on with the numbers past the total, and their `%slides%` adds the total with the backup slides, so after 40 slides and 14 backup slides the first backup slide shows `41/40-54`.
The editor shows the tokens themselves, because only the build fills them in.

The cell is right-aligned on one line, 200 px wide at x 1696 and y 1037, so the number ends at x 1896 and a longer number grows to the left and stays on the page.
Its style is `text;html=1;strokeColor=none;fillColor=none;align=right;verticalAlign=middle;whiteSpace=nowrap;overflow=visible;spacing=0;spacingTop=0;spacingBottom=0;spacingLeft=0;spacingRight=0;fontSize=22;fontFamily=Helvetica;fontColor=#000000;`.
A title slide carries no number cell, and still counts, so the three slides of a new presentation show nothing, `2/3` and `3/3`.

## A formula is written inside the sentence it belongs to

A formula goes between `\(` and `\)` inside the label of its sentence, so the sentence stays one cell:

```html
The cost \(\textcolor{dpred}{c}\) of a design is at most \(\textcolor{dpred}{r_1} + \textcolor{dpred}{r_2}\).
```

draw.io typesets a formula when the edit of the label ends, on a page whose mathematical typesetting is on.
A page made with the + tab of the editor starts with it off, unless the plugin of the next section is loaded, and *Extras > Mathematical Typesetting* switches it on for the page on screen.
A duplicated page keeps the switch of the page it copies.

MathJax sets the formula in the font size of the words around it.
A `span` with a `font-size` and `font-family: Helvetica` sets it apart, `<span style="font-size: 40px; font-family: Helvetica">\(...\)</span>`, because MathJax scales a formula to the face around it.
A symbol set as text, such as e₁, is `<i>e</i><sub style="line-height: 0">1</sub>`, and the `line-height` keeps the line as tall as the others.
The page `text-with-mathematics-1` of the template shows each of these with its source beside it.

### The colours of a formula come from a palette

draw.io's MathJax knows no colour by a name such as `dpgreen` and draws it black, so a name needs a `\definecolor` before the formula is typeset.
A palette is a TeX file of `\definecolor` lines, such as `example-palette.tex`.
Two places give the definitions, both read from the palette:

- In the editor, `tools/draw-io/mathjax-definitions.plugin.js` defines every colour of the palette on every page, so a new page needs no definitions of its own.
- In the build, every page gets a locked layer `Equation colours, added by the build` with the definitions its formulas use, before the export.
  The section files stay as they were saved.

A page may still carry its own locked layer `Equation colours`, as the pages of the template do, and the build then leaves the colours it defines to the page.
`\fatsemi` and `\mathds` are defined the same way, from `MATHJAX_MISSING` in `tools/draw-io/tex_definitions.py`.
The editor loads one plugin for every presentation it opens, so the plugin holds the colours of every palette in use.
After a palette is added or changed, write the plugin again from all of them, the first palette winning where two define one name:

```sh
# from the repository root
python3 tools/draw-io/make-mathjax-plugin.py --palette formatsAndTemplates/draw-io/example-palette.tex \
    --palette path/to/other-palette.tex
```

## A cell links to an address or to a slide, and a shape plays a video or shows an HTML page

Three properties of a cell reach the HTML file of `npm run html`: a link, a video and an HTML page.
The PDF shows the cell as it is drawn.

A link is set with *Edit Link*, Alt and Shift and L, on the cell.
The link is an address, such as `https://example.org`, which the HTML file opens in a new tab, or a page of the deck, chosen under *Page* in the same dialog, which the HTML file shows.
A link written inside the text of a label works as well.

A video is set on a shape, such as a rectangle, a rounded rectangle or an ellipse, with *Edit Data*, Cmd and M on a Mac and Ctrl and M elsewhere.
*Add Property* adds each property below to the cell.

| property | value | what it does |
|---|---|---|
| `video` | `assets/videos/demo.mp4` | the video, relative to the presentation folder, or an address that starts with `https://` |
| `fit` | `contain`, the default | the whole video, smaller than the shape where the two differ in proportion, with the fill of the shape around it |
| | `stretch` | the video rescaled to the shape, out of its proportion |
| | `crop` | the video filling the shape, with the parts outside the shape cut |
| `autoplay` | `1` | starts the video when its slide shows |
| `loop` | `1` | plays the video again from the start when it ends |
| `muted` | `1` | plays the video without sound |
| `barHideDelay` | `0`, the default | the seconds the bar of the HTML file stays after the pointer has left the video and the bar |
| `barFadeOut` | `0.25`, the default | the seconds the bar of the HTML file takes to fade out after that |

The video shows only inside the outline of its shape, so an ellipse shows an elliptic video.
The video lies where the shape lies among the cells: a cell later in the file covers it, as it covers the shape, and the video covers no cell in front of it.
A label of the cell itself shows above the video.
Fill the shape with a still of the video, so that the PDF and the editor without the plugin show the still.
A slide in steps whose pages keep the shape at the same place plays the video on from one step to the next.
On each step the video takes the `barHideDelay`, the `barFadeOut` and the `fit` of its cell there, and its loop and its sound stay as the bar left them.
Encode a video as MP4 with H.264, which every common browser plays, or as WebM with VP9.
The HTML file has been tried in Chromium alone, so try it in the browser of the talk before presenting.

The HTML file shows the same bar of controls as the editor, which the section on VS Code below describes, in place of the controls of the browser.
Every video has the bar, and the build reads no property `controls`, so a cell that still carries `controls="0"` shows the bar as well.
The menu of the right button of the browser stays on the video.
The bar shows right under the picture of a video while the pointer is over the shape of the video or over the bar, and while a field of the bar has the focus.
The bar touches the picture, so the pointer goes from the video to the bar without the bar going away.
When the pointer has left both, the bar waits `barHideDelay` and then fades out in `barFadeOut`, and it shows whole again when the pointer comes back meanwhile.
Set the two with *Edit > Edit Data* on the cell, such as `barHideDelay` to `1` for a bar that stays a second.
The editor shows its bar while the shape is selected, under the arrows of draw.io, and reads neither property.
An embedded page shows a bar of `Page ⟳ Reload` in the same way, right under its shape and with the same two properties, and its page takes the pointer without an Interact.
A browser seeks a video only when it can read any part of the file, which it can when the HTML file is opened as a file and when a server answers requests for ranges of a file, so a server that sends whole files makes the bar unable to jump.

An HTML page, such as an interactive three-dimensional plot, is set on a shape in the same way, with the property `html`:

| property | value | what it does |
|---|---|---|
| `html` | `assets/plots/surface.html` | the page, relative to the presentation folder, or an address that starts with `https://` |

The page shows inside the outline of its shape and in its place among the cells, as a video does, and a cell with both a video and a page shows the video.
In the HTML file the page takes the pointer at once, so a drag turns the plot and the wheel zooms it.
After a click in the page, the keys go to the page, and when the pointer leaves it they go back to the slide.
A slide in steps that keeps the shape at the same place keeps the page and its state, such as the angle of a plot, from one step to the next and back, in a browser with `Element.moveBefore`, such as Chrome or Edge from version 133.
Another browser loads the page again on each step.
Every build shows the page as it first draws.
The build loads the page in headless Chromium at the size of its shape on the slide, takes a picture once it has drawn, and draws the shape as that picture in the PDF and in the exported SVGs.
The build keeps the pictures of its last run in `build/page-snapshots/`.
The build takes the picture of a local page again when the file of the page is newer than the picture, or a file that the page names in its `src` and `href` attributes is.
The build takes the picture of a page of another server on every build.
A page that gives no picture keeps the picture of an earlier build, with a warning, so a build offline still shows a page of another server.
The HTML file shows the picture under the page until the page has drawn, and the editor leaves the shape empty until then, so none of them shows a fill of your own.
Give the shape the shape image, because the build draws the picture as an image in its rectangle, and a picture as its fill shows only in the editor without the plugin.

The build copies the file of the page into `build/media/`, with the files that the page names beside it in its `src` and `href` attributes, with or without quotes, such as a script or a picture.
A video or a page outside the presentation folder goes to `build/media/outside/<hash>/`, and a page there takes along the files that it names in its own folder or below it.
A build removes from `build/media/` each file that the previous build of the same HTML file copied and the deck no longer uses, and names the files it removes.
The lists of the copied files are in `build/media/.deck-media.json`, and a file of your own in `build/media/` stays.
A file that a script of the page loads in another way, such as by `fetch`, is missing from the HTML file, although the editor finds it, so such a page keeps its data inside it.
A Plotly figure works in both places when it is written with its library inside, `fig.write_html("surface.html", include_plotlyjs=True)`, about 4 MB, or with its library beside it, `include_plotlyjs="directory"`.
A figure with its library from the web, `include_plotlyjs="cdn"`, works as well, and needs a network connection during the talk.
A page runs with the rights of the HTML file that shows it, and in the editor with the rights of the editor, where it could change the drawing, so embed only pages that you trust.

The page of the HTML file takes these keys:

| key | what it does |
|---|---|
| Right, Down, Page Down, Space | the next page |
| Left, Up, Page Up, Backspace | the page before |
| Home, End | the first and the last page |
| a slide number, then Enter | that slide |
| O | opens and closes the outline of sections, slides and steps |
| Escape | closes the outline |
| F | full screen |

The address of a page is its slide number, `#12`, and `#12.3` or `#12-3` is the third step of slide 12, so a link to the HTML file may open at a slide.
A move of the mouse shows a bar at the bottom left with the same commands, and the number of the page as the slides number theirs: `12-3/45` for the third step of slide 12, with the step only for a slide in steps, and `50/45-59` for a backup slide, after 45 slides and 14 backup slides.
The HTML file loads the font STIX Two Text from Google Fonts, so a computer offline shows the text in another serif face where the font is not installed.

The table of keys above is the one place that gives them, and `onKey` of `tools/draw-io/html-deck.html` handles them.
`tools/draw-io/deck_html.py` gives the properties in its header.

## Set up VS Code to edit the slides as drawings

The extension `hediet.vscode-drawio` edits a draw.io file in VS Code.
The extension opens a `.drawio.xml` file as a drawing only when a setting associates the two, and the plugins are loaded by a setting as well.
Open the folder of a presentation in VS Code, with *File > Open Folder…* or `code my-talk`, and its `.vscode/settings.json` holds both.
`init` writes that file, and for a presentation that has none, the mode `vscode` writes it, with the colours of a colour configuration:

```sh
# in the folder of the presentation
python3 ../tools/draw-io/build-slides.py vscode --colours ../formatsAndTemplates/draw-io/named-colors-example.json
```

The mode refuses to replace a settings file that exists.
The file it writes for a presentation inside this repository reads:

```jsonc
{
  "workbench.editorAssociations": { "*.drawio.xml": "hediet.vscode-drawio-text" },
  "files.associations": { "*.drawio.xml": "drawio" },
  "hediet.vscode-drawio.plugins": [
    { "file": "${workspaceFolder}/../tools/draw-io/mathjax-definitions.plugin.js" },
    { "file": "${workspaceFolder}/../tools/draw-io/label-colours.plugin.js" },
    { "file": "${workspaceFolder}/../tools/draw-io/single-page.plugin.js" },
    { "file": "${workspaceFolder}/../tools/draw-io/click-through.plugin.js" },
    { "file": "${workspaceFolder}/../tools/draw-io/edit-at-click.plugin.js" },
    { "file": "${workspaceFolder}/../tools/draw-io/list-styles.plugin.js" },
    { "file": "${workspaceFolder}/../tools/draw-io/language-check.plugin.js" },
    { "file": "${workspaceFolder}/../tools/draw-io/view-position.plugin.js" },
    { "file": "${workspaceFolder}/../tools/draw-io/media-bar.js" },
    { "file": "${workspaceFolder}/../tools/draw-io/media.plugin.js" },
    { "file": "${workspaceFolder}/.vscode/deck-folder.plugin.js" }
  ]
}
```

The `${workspaceFolder}` above is the folder of the presentation, which the extension puts in the path of each plugin.
`mathjax-definitions.plugin.js` gives the editor the colours of formulas.
`label-colours.plugin.js` lets the words, the bullets and the formulas of a label show its font colour.
Without it the extension's own page shows them in the colour of the interface, black, while the build shows the font colour.
`single-page.plugin.js` keeps a page of 1920 by 1080 at one page in the page view, so content past the edge is cut as the build cuts it.
`click-through.plugin.js` lets a click on the empty inside of a shape or a text box without fill select the shape behind it.
`edit-at-click.plugin.js` keeps the view still when a double-click starts editing a label, and puts the caret at the character under the double-click.
Without it, draw.io scrolls to show the whole source of the label, which is far longer than a formula drawn, and selects the whole label, so the next key would replace it.
An edit started with F2, Enter or a typed letter keeps the behaviour of draw.io.
`list-styles.plugin.js` gives a list the style of the template's lists, by its level, when the buttons Bulleted List, Numbered List, Increase Indent and Decrease Indent of *Format panel › Text*, or Tab in a list, make or move it.
The first level takes the marker `disclosure-closed` and an indent of 26.07 px, the second the marker `'-  '` and an indent of 43.93 px, and a deeper level a dot.
Every item but the first of a first level sits 8.44 px below the one before.
A numbered list takes 1., a. and i. by level.
The same plugin adds the menu *List style* under those buttons, which shows while a label is edited and names the marker of the list at the caret.
Choosing a marker sets it on that list alone, and *Template* gives the list the template's style of its level again.
Both write the style into the HTML of the label, so the HTML file and the PDF show the same marker.
A choice in the menu stays out of the history of the browser, so Undo inside the label takes back the change before the choice instead.
The Undo of the drawing after the edit takes back the whole edit, the choice included.
The plugin draws the triangle and the dash in the colour and the size of the points of the Keynote deck of the template, as its header says.
The build copies the rules of the markers into the SVG of each slide with a list.
`language-check.plugin.js` underlines the spelling and the grammar of the label being edited, as the section on spelling below says.
`view-position.plugin.js` leaves the position of the view, the attributes `dx` and `dy` of `<mxGraphModel>`, out of every page that the editor saves, so a scroll alone changes no section file.
A file then opens at the default view of the editor.
`media-bar.js` holds the bars of controls of a video and of a page, which `media.plugin.js` uses and the HTML file shares, so it loads before `media.plugin.js`.
`media.plugin.js` plays the video of a shape with the property `video` and shows the page of a shape with the property `html`, inside the shape, as the HTML file shows them.
`deck-folder.plugin.js` tells `media.plugin.js` the folder of the presentation, as the paragraphs below say.
Reload the window after a change, with *Developer: Reload Window* in the command palette.
The extension asks once whether to allow each plugin, and again after a plugin file changes.
The `.drawio.xml` name keeps the editor from compressing the XML on save, so the file stays readable as text.

The media plugin lives in `tools/draw-io/` of this repository, and every presentation loads it from there, so a change to the plugin reaches every presentation.
The page of the editor does not know the folder of the drawing, so each presentation also loads `.vscode/deck-folder.plugin.js`, one line that names its folder, and the media plugin reads it when a video loads.
Every build writes that line, and its text changes only when the folder moves, so the extension asks again only then.
The line holds a path of this machine, so git leaves it out, and the first build on another machine writes it there.
In the editor the video plays muted and in a loop, and a click goes through it to the shape, so the shape is selected, moved and resized as before.
When the shape of a video is the one selected cell, a bar under the shape controls the video.
The bar sits below the arrows that draw.io shows around a selected shape, or above the shape when the view has no room below:

| control | what it does |
|---|---|
| ⏮ | back to the start |
| «5, 5» | back or forward 5 seconds |
| ▶, ❚❚ | play or pause |
| the slider | the position. A drag holds the video while it moves and plays it again on release. While the slider has the focus, the arrows move it by 0.1 s, or by 1 s with Shift |
| `0:01.250 / 0:05.000` | the time and the length, always to the millisecond. A time typed into the field, such as `1:02.5`, `62.5` or `5`, and Enter go there. A value that does not parse changes nothing, a value outside the video goes to its nearer end, and Escape leaves the field |
| `1×` | the speed, from 0.25× to 2× |
| ↻ | the loop, on when bright |
| 🔇, 🔊 | the sound, off at the start |

A click or a drag on the bar selects and moves no cell.
After a click on a control of the bar, a drag of the slider or a choice in the list of speeds, the control keeps the focus.
The bar then takes the keys, so the arrows, Delete and the shortcuts of draw.io change no cell.
The arrows move the video while the slider has the focus, Space and Enter press a button, and Tab and Shift and Tab go round the controls of the bar.
Enter or Escape in the field of the time leaves the focus on the bar, and the field shows the time of the video again.
A press of the pointer outside the shape and its bar gives the keys back to the drawing, and a press on the shape or a drag of it keeps them in the bar.
A double-click that edits the label of the cell gives the keys to the label.
A paste, a cut or a copy while a control of the bar has the focus stays in the bar, so it never adds a cell to the drawing or takes one out.
In the HTML file the focus goes back to the slide after a click on a button, a drag of the slider and a choice of a speed with the pointer.
The arrows of the HTML file move the video while the slider has the focus, after Tab has given it the focus through the buttons of the bar.
A video keeps its time, its pause, its speed and its sound through zooms, edits, redraws of the page, and the undo of a move, a resize or a change of style.
When the drawing shows another of its pages, a cell there with the id and the file of a cell of the page before takes the video over as it was, wherever the cell sits.
Every other video starts again from the beginning, muted, as after the undo of the deletion of its cell.
A bar that reads `not playable` belongs to a video that did not load, and the console of the webview names the cause.
The bar does not show in the PDF or in a drawing exported from the editor, and the HTML file shows it while the pointer is over the shape, as the section on the HTML file says.

The editor shows an HTML page of the property `html` in its shape as well, and the page takes no pointer, so the shape is selected, moved and resized as before.
When the shape of a page is the one selected cell, a bar under it reads `Page ☐ Interact ⟳ Reload`.
*Interact* lets the pointer act on the page, such as a drag that turns a plot, until it is clicked again or the shape is deselected.
A double-click on the shape selects it and switches Interact on, and F2 or Enter edits its label instead.
*Reload* loads the page again, after its file has changed, and keeps the page shown until the new one has drawn, in the editor and in the HTML file.
The bar reads `loading` until the page has loaded, and the shape stays empty meanwhile, because the image of a page's shape is left out.
The page lays out at the size of its shape on the slide and is scaled to the zoom, as in the HTML file, so its text keeps its size against the slide at every zoom.
Interact changes only where the pointer goes, so the page looks the same with it on and off, until the pointer acts on the page.
A page keeps its state through zooms, moves, redraws, and the undo of a move, a resize or a change of style, and passes to a cell of another page of the drawing as a video does.
Every other page loads again when its page of the drawing is shown again, and after the undo of the deletion of its cell.
The bar of a page keeps the focus after a click as the bar of a video does.
After a click in the page with Interact on, the keys go to the page, also after the pointer has left it, until a press of the pointer outside the shape and its bar.
A key that the page leaves unused, such as an arrow in a page without a scroll bar, may still scroll the view of the drawing.
`click-through.plugin.js` passes a click on the empty inside of the shape of a page to the shape behind it, so the click counts as a press outside.
The build of a deck gives the shape of each page its picture as an image, so a click inside the shape of a built deck keeps the keys in the page.
The editor reads a page of the deck and hands its text to the frame, with the folder of its file as the base of its links, because VS Code serves the files of the open folder only to the page of the editor itself, so the page finds every file beside it.
A page of another server loads from its address.
The bar says `not loaded` when that address cannot be reached, and the frame shows the page of the browser when the server answers with an error or refuses to be shown in a frame.

VS Code plays an MP4 file from its address.
Its media library opens no WebM file, so the plugin reads a WebM file whole and plays it through the Media Source Extensions of the page, which read WebM on their own.
A WebM file therefore waits until it is read whole.
The page holds about 150 MB of one video this way, so a larger WebM file plays its first part and loops there, and the console of the webview says how many seconds play.
A WebM file from another server plays only when that server allows the page to read it, which few servers do.
Give a long video, or one from another server, as MP4 with H.264.
VS Code serves the files of the folder it has open, so a video plays when it lies inside the presentation folder.
A shape whose video does not play shows its fill, and *Developer: Open Webview Developer Tools* in the command palette shows the failed address in its console.

To edit the template or the tools, open this repository at its root instead.
Its own `.vscode/settings.json`, which git leaves out, holds the same associations and the eight plugins at `${workspaceFolder}/tools/draw-io/`, where `${workspaceFolder}` is the repository root:

```jsonc
{
  "workbench.editorAssociations": { "*.drawio.xml": "hediet.vscode-drawio-text" },
  "files.associations": { "*.drawio.xml": "drawio" },
  "hediet.vscode-drawio.plugins": [
    { "file": "${workspaceFolder}/tools/draw-io/mathjax-definitions.plugin.js" },
    { "file": "${workspaceFolder}/tools/draw-io/label-colours.plugin.js" },
    { "file": "${workspaceFolder}/tools/draw-io/single-page.plugin.js" },
    { "file": "${workspaceFolder}/tools/draw-io/click-through.plugin.js" },
    { "file": "${workspaceFolder}/tools/draw-io/edit-at-click.plugin.js" },
    { "file": "${workspaceFolder}/tools/draw-io/list-styles.plugin.js" },
    { "file": "${workspaceFolder}/tools/draw-io/language-check.plugin.js" },
    { "file": "${workspaceFolder}/tools/draw-io/view-position.plugin.js" }
  ]
}
```

A window opened at the root plays no video and shows no page in the editor, because the folder of a presentation reaches the media plugin only through the settings of that presentation.

## Check the spelling and the grammar with LanguageTool on this machine

VS Code opens its windows with the spell check of the browser off, so the draw.io editor underlines nothing by itself.
LanguageTool, an open-source checker under the LGPL, runs on the Mac as a server that the editor plugin, `npm run check` and VS Code use, and no text leaves the machine.
Homebrew installs it with Java, and starts it now and at every login:

```sh
brew install languagetool
brew services start languagetool
```

The server answers at `http://localhost:8081`, for this Mac alone, and `brew services stop languagetool` stops it.

While a label is edited, `language-check.plugin.js` draws a wavy red line under a word that may be misspelt and a wavy blue line under a fault of grammar or of style.
The right button on an underlined word opens the message and up to five fixes, a fix replaces the word as typing would, so *Undo* takes it back, and *Ignore* hides the issue until the label is edited again.
A formula between `\(` and `\)` reads as the noun B, so its TeX is not checked, and the items of a list and the lines of a label read as paragraphs.
An item of a list may start with a small letter and end without a full stop, because the two rules of LanguageTool on them are left out.

`npm run check` checks every label of the deck the same way, one label at a time, and prints each issue with its slide, its page, its cell, the fixes and the words around it in brackets:

```
slide 47, conclusion-and-future-work-1, cell conclusion-and-future-work-1-future-work: spelling: Possible spelling mistake found.; Receiving, Receding
    ...ties [Receiding] horizon control, Markov process, and...
```

A label that several pages share, such as the steps of a slide, is checked once.
Two lists hold the words that are right though LanguageTool does not know them.
A word for every document, such as a term of the field, goes into the list of the server, `spelling_custom.txt` in `org/languagetool/resource/en/hunspell/` of the installation of LanguageTool, such as `/opt/homebrew/opt/languagetool/libexec/` for Homebrew.
Every application that checks with the server reads the list, Firefox and VS Code among them, and the server reads it at its start, so a new word takes effect after `brew services restart languagetool`.
An upgrade of LanguageTool brings a new folder without the added words, so keep the list elsewhere and link it there.
A word of one deck alone, such as a name, goes into `language-check-words.txt` in the folder of the deck, one per line, which the editor plugin and `npm run check` read.

VS Code checks text, Markdown, LaTeX and the other formats of the extension LTeX+, `ltex-plus.vscode-ltex-plus`, against the same server, with these user settings:

```jsonc
"ltex.languageToolHttpServerUri": "http://localhost:8081",
"ltex.language": "en-US",
"ltex.enabled": ["bibtex", "context", "context.tex", "html", "latex", "markdown", "mdx", "typst",
  "asciidoc", "neorg", "org", "quarto", "restructuredtext", "rsweave", "plaintext"]
```

## Edit a slide as text, the way an agent does

Every slide is uncompressed XML: a `<diagram name="...">` per page, and inside it an `mxCell` per object.

- To add a slide, copy a whole `<diagram>` from `slide-format.drawio.xml` or from a section file, give it a new `name` and a new `id`, and put it where the slide goes.
- To change text, change the `value` attribute.
  The value is escaped HTML, so `<b>` is written `&lt;b&gt;`.
- To move an object, change `x` and `y` of its `mxGeometry`.
  The page is 1920 by 1080 with the origin at the top left.
- To add an object, copy an `mxCell` of the same kind, give it an `id` no other cell of the page has, and put it inside the `<root>` of the page.
  A cell later in the file is drawn on top.
- To give a cell a link or a video, wrap it in a `UserObject` that carries the properties, its `id` and its text as `label`, and drop the `id` and the `value` of the `mxCell`:

  ```xml
  <UserObject label="" video="assets/videos/demo.mp4" fit="crop" autoplay="1" muted="1" id="s5-video">
    <mxCell style="ellipse;html=1;" vertex="1" parent="1">
      <mxGeometry x="960" y="300" width="640" height="360" as="geometry" />
    </mxCell>
  </UserObject>
  ```

  A link to a page is `link="data:page/id,<id of the diagram>"`.
- After a change, run `npm run build` in the presentation folder and read its warnings.

The page `every-construct-1` of the template shows each kind of object with the style keys that make it.

## The build warns about a slide it cannot show as intended

| warning or error | cause | what to do |
|---|---|---|
| `the name 'x' starts slides 3, 7` | two slides apart from each other share a name | rename one, or move its pages next to the others |
| `slide 4, 'x', has the steps 2, 1 in page order` | the steps of one slide are out of order | reorder the page tabs or rename the steps |
| `holds a formula and has mathematical typesetting off` | the page's switch is off | *Extras > Mathematical Typesetting* on that page |
| `colours formulas with dpgren, which neither the page nor the palette defines` | a colour name that no palette holds, often a typo | fix the name, or add it to the palette |
| `palette.tex defines x in the model y with values that tex_definitions.py does not convert` | a `\definecolor` in a model other than `rgb`, `RGB`, `HTML`, `gray`, `Gray`, `cmy` and `cmyk`, or with the wrong count of values | write the colour in one of those models |
| `names the picture assets/a.png, which does not exist` | the path of a picture `image=assets/<name>` names no file | fix the path, relative to the presentation folder |
| `3-a.drawio.xml and 3-b.drawio.xml both carry the section number 3` | two files share a section number | renumber one of them |
| `notes.drawio.xml does not start with its section number` | a file in `sections/` without its number | name it `<number>-<name>.drawio.xml` |
| `page 3 was not ready within PAGE_WAIT; exported as it stood and kept out of the cache` | the page did not finish drawing in time, or it shows `\(` or `$$` as text with mathematical typesetting on, which the export takes for a formula still to typeset, as the sources beside the constructs on the last three pages of the template do | look at the SVG of the page, and fix the page or set a longer `PAGE_WAIT` |
| `page 3 produced no SVG`, then `1 of 3 pages produced no SVG` | the viewer drew nothing, such as a viewer on the web without a network connection, and the build stops | fix the viewer or the connection, and build again |
| `DRAWIO_VIEWER names p, which does not exist` | the path of `DRAWIO_VIEWER` names no file, and the build stops | name a file, or leave the variable out |
| `the viewer v lies outside the folder webapp of draw.io` | a copy of `viewer-static.min.js` outside the folder `webapp/js/` of draw.io, and the build stops | name the `viewer-static.min.js` in `webapp/js/` |
| `the cell x links to the page p, which the deck does not show` | a link to a page that is gone or hidden with `-hide` | link to a page of the deck |
| `the cell x has the link data:..., which only the editor follows` | a link of another kind of draw.io, such as an action | link to an address or a page |
| `a label links to the page p, which the deck does not show` | a link inside the text of a label to a page that is gone or hidden | link to a page of the deck |
| `a label has the link data:..., which only the editor follows` | a link of another kind inside the text of a label | link to an address or a page |
| `the cell x is no vertex, such as an edge, and the HTML file follows the link of a vertex alone` | a link on an edge | put the link on a shape or a text |
| `the video assets/videos/a.mp4 of the cell x does not exist` | the path of the property `video` names no file | fix the path, relative to the presentation folder |
| `the cell x has fit=y, which is none of contain, stretch, crop` | a value of `fit` that the HTML file does not know | write one of the three |
| `the cell x has barHideDelay=y, which is no time of 0 s or more, so it takes 0` | a time of the bar, `barHideDelay` or `barFadeOut`, that is no number of 0 or more | write a number of seconds |
| `the page assets/plots/a.html of the cell x does not exist`, from the HTML file, and `the page assets/plots/a.html of the cell x is missing, so the builds draw the cell as it is`, from the picture of the page | the path of the property `html` names no file | fix the path, relative to the presentation folder |
| `the page p of the cell x gave no picture, so the builds draw the cell with the picture of an earlier build`, or `as it is` | the page did not load within `SNAPSHOT_LOAD_WAIT`, or a page of another server had no network connection | open the page in a browser, fix what stops it, and build again |
| `the cell x of the page p is a rectangle shape, so the builds draw it as a rectangular picture of its page` | an embedded page in a shape other than `image` | give the shape the style `shape=image` |
| `two pages have the id p` | two pages share an id, usually after copying a page as text | give one of them a new `id` |
| `the key config of .../package.json holds 'x', which is none of title, palette, slides-dir, deck`, or `config.palette of .../package.json holds 'a.tex', where a list of paths was expected` | a key of `config` that the build does not know, or a value of the wrong kind, and the build stops | write the key as the section on the commands above shows |
| `the palette p does not exist` | a palette of `config` or of `--palette` names no file, and the build stops | fix the path, relative to the presentation folder |

## The template's six pages

| page | what it carries |
|---|---|
| `title-slide-1` | the title over two lines, the date, the author and the affiliation, each centred, and no slide number |
| `section-divider-1` | a section title and the slide number |
| `title-and-body-1` | a title, a two-level bullet list with a formula inside one item, and the slide number |
| `every-construct-1` | one example of each construct, with its style keys beside it |
| `text-with-mathematics-1` | a formula inside a sentence, inside a list item, as a symbol set as text, at a size of its own, and on its own |
| `text-with-mathematics-2` | the same slide as its second step, titled *Text with mathematics in one cell continues* |

`init` copies the first three into a new presentation.
The furniture of a slide is a title of 44 points at y 33, the slide number at the bottom right, and a body whose first level starts at x 486 and whose second starts at x 521.
The face is STIX Two Text throughout, apart from the slide number in Helvetica.

A bullet list is one `ul` with one `li` per item, and the marker is the `list-style-type` of its level.
A nested level is a `ul` inside its `li`, and each `li` carries the space between items as its `margin-top`.

The page `every-construct-1` draws twelve constructs:

- a text box of one line, and one of several lines with its own line height
- a rectangle, a rounded rectangle with an absolute corner radius, and an ellipse
- a path that matches no draw.io shape, as `shape=stencil(...)`
- an edge attached at both ends by a fraction along the side of its shape
- a curved edge with one waypoint, and an edge whose end carries a round terminal
- an equation label, a picture embedded as a data URI, and the slide-number cell

## The colour configuration gives each hex value a name in the colour dialog

draw.io shows a colour as a hex value, and its configuration can give each value a name, so the colour dialog offers `cdF`, the green of functionality of the codesign package, where it offered `#0E8005`.
A configuration carries three settings, and `named-colors.template.jsonc` is one to copy.

- `colorNames` gives a name to a hex value.
  The key is the value in upper case with no leading `#`.
  draw.io shows the name as a tooltip in the colour dialog and matches it when you type there.
- `presetColors` fills the top row of that dialog, in the order given, with values in the same form.
- `customColorSchemes` adds rows of swatches to the top of the Format panel's Style tab, before the rows of draw.io.
  A swatch takes `fill`, `stroke`, `font` and `gradient`, each a hex value with a leading `#`, or `none`.

A name does not travel with the drawing, because a cell's style still holds the hex value.
A deck opened without the configuration therefore looks the same and shows hex values in place of the names.
A swatch sets the fill, the stroke and the font of everything selected at once, so a swatch of white on white makes the selection vanish from the page.
`make-color-config.py` therefore gives each swatch a font that contrasts with its fill and leaves white out of both rows, and a configuration written by hand does the same.

The VS Code extension ignores a configuration pasted into draw.io and offers no dialog for one.
The three settings are settings of the extension instead, `hediet.vscode-drawio.colorNames`, `hediet.vscode-drawio.presetColors` and `hediet.vscode-drawio.customColorSchemes`, in `.vscode/settings.json`.
The mode `vscode` writes them from a configuration in plain JSON, such as `named-colors-example.json` or a copy of `named-colors.template.jsonc` without its comments, as the section on VS Code above says, and a settings file that exists takes them by hand.
In the desktop and web applications, paste them into *Extras > Configuration…*, save, and restart the application, which reads the configuration once at start.

`tools/draw-io/make-color-config.py` writes the three settings from the colours a deck uses:

```sh
# from the repository root
python3 tools/draw-io/make-color-config.py path/to/deck.drawio.xml \
    --out formatsAndTemplates/draw-io/named-colors-deck.json \
    --definecolor formatsAndTemplates/draw-io/example-palette.tex
```

The script keeps every colour used at least `--least` times, eight by default.
The script names a colour that a file passed to `--definecolor` defines after the name of its `\definecolor`, such as `dpgreen`, and any other colour after its hue.
A near-white colour, of lightness above 0.9 and a chroma, the largest channel less the smallest, below 0.05, takes the name White, so a pale tint such as `#dae8fc` keeps the name of its hue.
A hue of one colour gives it the plain name, such as `Blue`, and each colour of a hue of several carries its hex value after the name, such as `Grey 8B959E`, so that no two names differ by a shade word alone.
`--definecolor` may be given more than once, such as for a palette and a `.sty` file of the deck.
Run it again after the deck changes, because its output is generated.
