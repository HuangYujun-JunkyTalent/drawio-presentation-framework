# draw.io presentation framework: slides drawn in draw.io, built into one HTML file and a PDF

This repository holds what every draw.io presentation made with the framework shares: the slide template and the palette, the build and the plugins of the editor, and the skills of a deck.
A deck is a repository of its own, nested here, whose slides are draw.io XML that version control tracks and an agent can edit.
The build turns the slides into one HTML file that presents in a browser, with links, videos and interactive pages, and into a PDF of the same slides.

## The folders of the repository

| folder or file | what it holds |
|---|---|
| `formatsAndTemplates/` | what a new presentation starts from: the slide template, the palette and the colour configurations in `draw-io/` |
| `tools/` | the tools of the repository: the build of a draw.io presentation and the plugins of the editor in `draw-io/`, and the one `package.json` that installs Playwright for every presentation |
| `GOALS.md` | the goals of the framework, the principles of building the slides and of their content, which a fork may change to steer an agent that changes the fork |
| `LICENSE`, `LICENSE-EXCEPTION.md` | the license of the framework and the exception for the presentations made with it, as the section on the license says |
| `CONTRIBUTING.md` | the terms of a contribution |
| `skills/` | the skills of this repository, such as `deck-skeleton` for starting a deck and `deck-pdf` for its PDF, which an agent follows here and in each presentation nested here. A skill `skills/<name>.md` keeps its scripts in the folder `skills/<name>/` |

Each folder's own `README.md` says what its files are and how to use them.

## Make a new presentation in four steps

The steps need the software that the section on starting a presentation of `formatsAndTemplates/draw-io/README.md` names, VS Code with its extension for draw.io among it.

1. Install Playwright into `tools/` once for the repository, as `tools/README.md` says.
2. Start the folder from the template, from the repository root:

   ```sh
   python3 tools/draw-io/build-slides.py init my-talk --title "My talk"
   ```

   The folder is a git repository of its own, as the section on starting a presentation of `formatsAndTemplates/draw-io/README.md` says.
   The folder holds three slides to overwrite in `sections/1-my-talk.drawio.xml`, the commands below and the title in `package.json`, the settings of VS Code and a `.gitignore`.
   The folder may also be an absolute path outside the repository.
   Add `--palette <your palette>.tex` when the formulas are to use colour names, such as `dpgreen` of the example palette `formatsAndTemplates/draw-io/example-palette.tex`, on any slide.
3. Edit the slides in the draw.io editor or as text, as the next section says.
4. Build and present, in the folder of the presentation:

   ```sh
   cd my-talk
   npm run build      # build/my-talk.html, with its videos in build/media/, and build/my-talk.pdf
   npm run html       # build/my-talk.html alone
   npm run pdf        # build/my-talk.pdf alone
   npm run check      # the spelling and the grammar of every slide, by LanguageTool on this machine
   ```

`formatsAndTemplates/draw-io/README.md` gives every command of a presentation, `npm run watch` and `npm run outline` among them, what a build prints, and the key `config` of `package.json`, which holds the title and the palettes.
A cell may link to an address or to another slide, and a shape may play a video, in the HTML file and in the editor, as `formatsAndTemplates/draw-io/README.md` says.

## Edit the slides in the draw.io editor or as text

Each file in `sections/` is one section of the deck, and each page of a file is a slide or a step of a slide.
The files are uncompressed XML, so the editor and an agent change the same text.

A person opens the folder of the presentation in VS Code with the extension `hediet.vscode-drawio`, or a section file in the draw.io desktop application.
The `.vscode/settings.json` of the presentation, which `init` writes, opens the files as drawings and loads the plugins of the editor, as `formatsAndTemplates/draw-io/README.md` says.

An agent edits the XML directly, as the same README describes.
The four rules below restate the rules of that README that an agent needs most.

- Change only the files in `sections/` and in `assets/`.
  The build writes `build/` again on every run.
- Name a page `<name>-<step>`, and give two different slides two different names.
  The build numbers the slides from the names, and pages that follow one another under one name are one slide shown in steps.
- Write a formula between `\(` and `\)` inside the label of its sentence.
- Run `npm run build` after a change, and fix what its warnings name, as the table of warnings of `formatsAndTemplates/draw-io/README.md` says.

## Slide numbers, formulas and colours come from the template

The table points to the place of each part of a slide, and the sections of `formatsAndTemplates/draw-io/README.md` on slide numbers, formulas and colours say more.

| what the slide shows | where it is defined |
|---|---|
| `45/61` at the bottom right of every slide that carries the number cell, which the template's title slide does not | a cell holding `%slide%/%slides%`, which the build fills in |
| a formula inside a sentence | `\(...\)` in the label, typeset by MathJax in draw.io |
| a coloured formula such as `\textcolor{dpgreen}{F}` | a palette of the deck, such as the example `formatsAndTemplates/draw-io/example-palette.tex`, given to the editor by a plugin and to each page by the build |
| the title, the body and the fonts | the pages of `formatsAndTemplates/draw-io/slide-format.drawio.xml` |
| no slide at all for a page whose name ends in `-hide` | the build, which leaves the page out and gives it no number |

## Files that git does not track

`.gitignore` ignores every entry at the root apart from those that its lines with `!` name.
The folder of each deck, a repository of its own, and the `.vscode/` settings at the root therefore stay out without a line of their own.
The folder `.claude/` of the settings of Claude Code stays out as well, so each set-up of an agent keeps its own.
Inside the tracked folders `.gitignore` leaves out what each machine makes for itself, such as `node_modules/`, as its comments say.
A new file or folder at the root is tracked only after its own line with `!` in `.gitignore`.
`init` writes the `.gitignore` of a deck, which the tree of a presentation folder in `formatsAndTemplates/draw-io/README.md` describes.
The `.vscode/settings.json` of a presentation folder is tracked, so the settings of that folder travel with it.

## The license leaves every presentation to its author

Copyright (C) 2026 Yujun Huang.
The framework is free software under the GNU Affero General Public License, version 3, in `LICENSE`, so a changed version of it that anyone shares or runs as a service stays open source under the same license.
Commercial use of the framework is allowed under the same terms.
The additional permission in `LICENSE-EXCEPTION.md` frees every file that the framework writes or copies for a presentation, so the author of a presentation may keep it closed, sell it and give it under terms of the author's choice.
A contribution comes under the same license and the same permission, with no signed agreement, as `CONTRIBUTING.md` says.
