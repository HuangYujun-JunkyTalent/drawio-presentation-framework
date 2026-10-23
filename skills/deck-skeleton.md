---
name: deck-skeleton
description: How an agent starts a new draw.io deck of this repository: the current official logos on the title slide, placed as their brand guidelines say, the outline and the section dividers that repeat it, the conclusion and backup slides, the placeholders, and the look at the built slides.
read-when:
  - starting a new slide deck or the skeleton of a talk in this repository
  - adding, replacing or placing the logo of an organization on a slide
---

# Start a deck with the current logos, placed as their guidelines say, and with an outline that every section repeats

The paths in this skill are relative to the root of this repository.
`README.md` gives the four steps that start a presentation from the template and build it.
`formatsAndTemplates/draw-io/README.md` gives the pages of the template and the way an agent edits a slide as text.
A new deck is a git repository of its own, which `init` creates inside this repository, and the user makes its first commit and adds its remote, as the same README says.
The git commands on the files of a deck run in the repository of the deck.

## Resources of this skill

The folder `skills/deck-skeleton/` holds two scripts.

- `place-logos.py` writes a row of logos into one page of a section file.
  Each logo is cropped to its pixels that are not transparent, resampled, and embedded as a PNG data URI.
  The logos get one height, sit on one horizontal line and spread with equal gaps.
  The header of the script gives its options and their defaults.
- `screenshot-slides.mjs` writes a PNG of each built slide of a deck and contact sheets of twelve slides.
  The script runs the Chromium that `npm install` in `tools/` installs for every deck.

## Standard: the title slide carries the current official logo of each organization of the speaker, placed as its guidelines say

- Each logo is the latest version that its organization publishes.
  The file comes from the brand site of the organization, or from a page of the organization that links the official file.
- A logo keeps its proportions, its colours and its drawing.
  The only changes are the crop of a transparent margin and the resampling.
- The variant of each logo suits the background of the slide, such as the colour or the black version on a white slide.
- The logos sit on one horizontal line with one height and equal gaps, unless a guideline asks for another arrangement.
- The logo of a university beside the logos of its units follows the rules of the university on that pairing.
  An example is the endorsed branding of MIT that the related item on MIT logos gives.
- Each logo has at least the clear space and the size that its guidelines give.
- When a guideline asks for the full name of the institution, the slide carries the name, such as in the affiliation line.
- `assets/logos/` of the deck holds the original files.
  `assets/logos/sources.md` names for each file the organization, the URL of the download, the page that links it and the date of the download.

## Standard: the deck opens with an outline and closes with a conclusion

- The outline slide follows the title slide and lists the sections of the talk.
- Each section of the outline opens with a divider slide.
  The title of the divider is the title of the section.
  The divider repeats the outline with the current section in bold and the other sections in grey `#8b959e`.
- The last section of the outline holds a conclusion slide that sums up the key points of the talk.
- Backup slides follow the conclusion, behind a divider of their own that the outline leaves out.
- When the talk presents a paper or another document, the sections follow the sections of the document.

## Standard: a placeholder says what goes on the slide and looks unfinished

- Text that the speaker still has to write is a placeholder in italic grey `#8b959e`, `<font color="#8b959e"><i>...</i></font>` in the value of its cell.
- A placeholder names what the slide will show, such as a definition, a result, a figure or a table.
- Text in black states what the source of the talk states, such as the paper that the talk presents.

## Required action: find the current logo and the guidelines of each organization before placing its logo

1. When the user names no organization for the logos of the title slide, ask the user which organizations the logos stand for, and wait for the answer.
2. When an earlier deck of this repository carries the logos of the same organizations, read its `assets/logos/sources.md` and open the pages that it names.
   `ls */assets/logos/sources.md` from the root of the repository lists the decks with logos.
   Copy the cells of its logos and its original files when the pages offer no newer version.
3. Otherwise find the files and the guidelines, as the how-to on finding the logo files says.
4. Read the guidelines on the logo: the versions, the colours, the clear space, the size, and the placement beside other logos.

## Required action: look at every built slide before delivering the deck

1. Run `npm run build` in the folder of the deck, and fix what its warnings name, as the table of warnings of `formatsAndTemplates/draw-io/README.md` says.
2. Run `node skills/deck-skeleton/screenshot-slides.mjs <deck folder> <output folder>` from the root of the repository, with an output folder outside the repository.
3. Look at the title slide at its full size and at every contact sheet.
   Check that no text runs past the page or into another cell, that the lists of all slides start at the same place, and that each logo has its clear space.

## How-to: find the official logo files of an organization

1. Search the web for the brand guidelines of the organization, its logo downloads and its brand assets.
2. Take the files from the first source that offers them, in this order:
   - the brand site of the organization
   - a page of the organization on logos or brand assets
   - a page of the parent institution that links the files of the unit
   - the logo in the header of the site of the organization
3. When a download needs a login of the user, ask the user to download the file, or take the same official file from a page of the organization that links it.
   Name both in `sources.md`.
4. Download each file into a new empty folder of its own, outside the repository.
   Extract an archive with a script that skips every name that starts with `/` or holds `..`.
5. Measure the box of the pixels of each file that are not transparent, to compare the variants and to find a transparent margin.
6. Look at each file, and choose the variant for the background of the slide.

For the units of MIT, the related item on MIT logos names the pages.

## How-to: place the logos on the title slide

1. Copy the original files into `assets/logos/` of the deck, under names of the form `<organization>-logo-<variant>.png`.
2. Order the logos as the guidelines of the largest organization show.
   The endorsed branding of MIT puts the logos of the units first and the MIT logo at the right end.
3. Run `place-logos.py` from the root of the repository, with the logos from left to right:

   ```sh
   python3 -I skills/deck-skeleton/place-logos.py my-talk/sections/1-my-talk.drawio.xml title-slide-1 \
       title-logo-lab=my-talk/assets/logos/lab-logo-colour.png \
       title-logo-department=my-talk/assets/logos/department-logo-colour.png \
       title-logo-university=my-talk/assets/logos/university-logo-black.png
   ```

   The defaults give logos 100 px high, centred on y 925 and spread from x 160 to x 1760, below the affiliation of the title slide of the template.
   The script prints the place of each logo and the gap between two logos.
4. Compare the gap with the clear space of each guideline.
   For the MIT logo, the clear space is the width of its M, which the related item on MIT logos gives as a fraction of the height of the logo.
5. Write `assets/logos/sources.md`.

## How-to: write the outline slide and the section dividers

1. Copy the page `title-and-body-1` of the template for the outline slide, name the copy `outline-1`, and title it Outline.
   Put the list of the sections into the body, at y 380 so that the list sits near the middle of the page.
2. For each section, copy the page `section-divider-1` of the template, name the copy `section-<key>-1`, and give it the title of the section.
   Add a cell in the style of the body of `title-and-body-1`, at x 486.62 and y 380, 932.66 wide, that holds the outline.
3. Write the outline in the list markup of the body of the template, with the current section and the other sections set as the standard on the outline says:

   ```html
   <div style="line-height: 40px"><ul style="margin: 0; padding-left: 26.07px; list-style-type: disclosure-closed">
   <li><font color="#8b959e">The first section</font></li>
   <li style="margin-top: 8.44px"><b>The current section</b></li>
   <li style="margin-top: 8.44px"><font color="#8b959e">The last section</font></li>
   </ul></div>
   ```

   The value of a cell holds this HTML escaped, as `formatsAndTemplates/draw-io/README.md` says.
   The marker of the first level is `disclosure-closed`, which the browser draws as a shape and not as a glyph of the font.
   The marker therefore has one size in the editor, the PDF and the HTML deck, whichever copy of STIX Two Text each one loads.
   `tools/draw-io/list-styles.plugin.js` gives the markers their colour and size in the editor and in every build, so the markup leaves out the colour and the size of the marker.
4. Give the backup slides a copy of `section-divider-1` named `section-backup-1`, with the title Backup slides and no outline.
5. Break an item of a body list with `<br>` at about 60 characters, because the template writes its lists on one line each and a longer line runs past the right edge of the body.

## Guidance

- Prefer the raster file of the highest resolution that the organization offers, because `place-logos.py` resamples it to three times its height on the slide.
- Prefer one kind of variant across the row, such as each logo with its word mark, so that the logos look alike in weight.

## Never-do

- Do not recolour, redraw, stretch or rebuild a logo.
- Do not crop a logo past its transparent margin.
- Do not take a logo from a site that collects the logos of other organizations.
- Do not sign in to a site with an account of the user to download a logo.
