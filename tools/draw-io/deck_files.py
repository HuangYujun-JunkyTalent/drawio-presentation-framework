"""The deck as a folder of section files, and the names that carry its order.

One file per slide makes too many files and one file for the whole deck makes the draw.io editor
slow, so the deck is one file per section under `sections/`:

    sections/3-uncertain-co-design.drawio.xml
             │ └── the section's name, for a reader
             └── the section number, which orders the files

    a page of that file named   point-wise-probability-2
                                │                     └── the step of the slide
                                └── the name of the slide

The pages present in the order of the files, and inside a file in the order of its pages, which
is the order of the page tabs in draw.io. Nobody numbers a slide by hand: the build counts them.
Pages that follow one another under one name are one slide shown in steps, which is how a slide
makes something appear or disappear, so they get one number and the number the audience sees does
not move while the slide builds.

    page name                   slide number
    title-slide-1               1
    point-wise-probability-1    2
    point-wise-probability-2    2
    composition-1               3

A name that comes back after another slide starts a new slide with a new number, because a number
that goes back down would confuse an audience, and `repeated_names` reports it. `step_problems`
reports a slide whose steps do not run 1, 2, 3. A name that ends
in no `-<step>` is step 1.

A page whose name ends in `-hide`, such as `reset-metrics-example-1-hide`, stays in its file and
out of the deck: `shown_pages` leaves it out before the slides are counted, so it takes no number.

A section file whose name contains `backup-slides`, such as `7-backup-slides.drawio.xml`, holds
backup slides, kept for questions after the talk. Its slides go on with the numbers, so each
still has a number of its own to ask for, and `main_total` leaves them out of the total, so the
total is the length of the talk. On a backup slide the build writes the total with the backup
slides after it: a deck of 40 slides and then 14 backup slides shows 20/40 on a slide of the talk,
and 41/40-54 to 54/40-54 on the backup slides.

Moving a page tab moves a slide, and renaming a file moves a section.

A deck without `sections/` is read from one multi-page file, `slides.drawio.xml`, as one section.
The key `config` of the deck's `package.json` names another slides folder or file, and holds the
title and the palettes of the deck, as `read_config` says.
"""
from __future__ import annotations

import html
import json
import os
import re

SUFFIX = ".drawio.xml"
FILE_NAME = re.compile(r"^(?P<number>\d+)-(?P<name>.+)$")
STEP = re.compile(r"^(?P<name>.+)-(?P<step>\d+)$")
DIAGRAM = re.compile(r"<diagram [\s\S]*?</diagram>")
PAGE_NAME = re.compile(r'name="([^"]*)"')

# The slides folder and the multi-page file of a deck, when neither the command line nor the
# configuration of the deck names another.
SLIDES_DIR = "sections"
SINGLE_FILE = "slides.drawio.xml"
PACKAGE = "package.json"
# The keys of `config` in `package.json`, each the long option of `build-slides.py` of the same
# name, with the type of its value.  `palette` lists every palette, as `--palette` given once per
# palette does.
CONFIG_KEYS = {"title": str, "palette": list, "slides-dir": str, "deck": str}
DEFAULTS = {"slides-dir": SLIDES_DIR, "deck": SINGLE_FILE}

HIDDEN = "-hide"
BACKUP = "backup-slides"


def split_step(page_name):
    """A page name's slide name and its step, which is the trailing number when there is one."""
    match = STEP.match(page_name)
    if match:
        return match.group("name"), int(match.group("step"))
    return page_name, 1


class Page:
    """One page of one section file."""

    def __init__(self, section, section_name, position, page_name, diagram, source):
        self.section = section
        self.section_name = section_name
        self.position = position
        self.page_name = page_name
        self.name, self.step = split_step(page_name)
        self.diagram = diagram
        self.source = source

    @property
    def backup(self):
        """Whether the page is a backup slide, in a section file whose name contains `backup-slides`."""
        return BACKUP in self.section_name

    @property
    def order(self):
        return (self.section, self.position)

    def __repr__(self):
        return "<Page %d:%s step %d>" % (self.section, self.name, self.step)


def read_pages(path: str, section: int, section_name: str) -> list[Page]:
    """The pages of one file as pages of the given section, in the order of their tabs."""
    text = open(path, encoding="utf-8").read()
    pages = []
    for position, diagram in enumerate(DIAGRAM.findall(text)):
        name = PAGE_NAME.search(diagram)
        pages.append(Page(section, section_name, position,
                          html.unescape(name.group(1)) if name else "slide-1", diagram, path))
    return pages


def read_section_file(path):
    """The pages of one section file, in the order the deck presents them."""
    base = os.path.basename(path)[:-len(SUFFIX)]
    match = FILE_NAME.match(base)
    if not match:
        raise ValueError("%s does not start with its section number" % os.path.basename(path))
    return read_pages(path, int(match.group("number")), match.group("name"))


def read_single_file(path: str) -> list[Page]:
    """The pages of a deck of one file, numbered as one section."""
    return read_pages(path, 1, "slides")


def read_config(folder: str) -> dict:
    """The key `config` of the `package.json` of a deck, or an empty dictionary without one.

    The key holds the facts of the deck that its commands share, so that each is written once:
    `{"title": "My talk", "palette": ["../palette.tex"], "slides-dir": "parts", "deck":
    "talk.drawio.xml"}`, each key optional.  A relative path is read from the deck folder.  A key
    outside `CONFIG_KEYS`, or a value of another type, raises `ValueError`.
    """
    path = os.path.join(folder, PACKAGE)
    if not os.path.isfile(path):
        return {}
    with open(path, encoding="utf-8") as handle:
        try:
            config = json.load(handle).get("config", {})
        except (json.JSONDecodeError, AttributeError) as error:
            raise ValueError("%s does not read as a JSON object: %s" % (path, error))
    if not isinstance(config, dict):
        raise ValueError("the key config of %s holds %r, where an object was expected"
                         % (path, config))
    for key, value in config.items():
        kind = CONFIG_KEYS.get(key)
        if kind is None:
            raise ValueError("the key config of %s holds %r, which is none of %s"
                             % (path, key, ", ".join(CONFIG_KEYS)))
        if not isinstance(value, kind) or (kind is list
                                           and not all(isinstance(item, str) for item in value)):
            raise ValueError("config.%s of %s holds %r, where %s was expected"
                             % (key, path, value, "a list of paths" if kind is list else "a text"))
    return config


def setting(key: str, given: str | list[str] | None, config: dict) -> str | list[str] | None:
    """The value of a key of `config`: the one given on the command line, or else the one of the
    configuration, or else the default that `DEFAULTS` gives, which `title` and `palette` lack.

    The palettes given on the command line come after those of the configuration instead."""
    if key == "palette":
        return (config.get(key) or []) + (given or []) or None
    return given or config.get(key) or DEFAULTS.get(key)


def slides_location(folder: str, slides_dir: str, single: str) -> tuple[str, bool] | None:
    """The slides folder of a deck when it exists, or else its multi-page file when that exists,
    with whether it is the folder, or None when the deck holds neither."""
    sections = os.path.join(folder, slides_dir)
    if os.path.isdir(sections):
        return sections, True
    path = os.path.join(folder, single)
    if os.path.isfile(path):
        return path, False
    return None


def read_folder(folder):
    """Every page of every section file, in the order the deck presents them.

    Two files of one section number would leave their order to chance, so they are refused.
    """
    pages, owners = [], {}
    for name in sorted(os.listdir(folder)):
        if name.endswith(SUFFIX):
            found = read_section_file(os.path.join(folder, name))
            if found:
                other = owners.setdefault(found[0].section, name)
                if other != name:
                    raise ValueError("%s and %s both carry the section number %d"
                                     % (other, name, found[0].section))
            pages.extend(found)
    pages.sort(key=lambda page: page.order)
    return pages


def shown_pages(pages):
    """The pages that the deck presents, which are those whose name does not end in `-hide`."""
    return [page for page in pages if not page.page_name.endswith(HIDDEN)]


def slide_starts(pages):
    """Whether each page starts a slide: its name differs from the page before it.

    A slide whose steps run on into the next file stays one slide.
    """
    starts, last = [], None
    for page in pages:
        starts.append(page.name != last)
        last = page.name
    return starts


def number_slides(pages):
    """The slide number of each page, by its index, and the deck's total."""
    numbers, total = {}, 0
    for index, start in enumerate(slide_starts(pages)):
        total += start
        numbers[index] = total
    return numbers, total


def main_total(pages):
    """The number of slides outside the backup sections, which is the total the deck shows."""
    numbers, _ = number_slides(pages)
    return len({numbers[index] for index, page in enumerate(pages) if not page.backup})


class Slide:
    """One numbered slide: its number, its name, and its pages, by their index in the deck."""

    def __init__(self, number, name, backup):
        self.number, self.name, self.backup, self.pages = number, name, backup, []


class Section:
    """One section file in the deck, with its slides in order."""

    def __init__(self, number, name, backup):
        self.number, self.name, self.backup, self.slides = number, name, backup, []

    @property
    def pages(self):
        return [index for slide in self.slides for index in slide.pages]


def outline(pages):
    """The sections of the deck, each with its slides, and each slide with its pages.

    A slide whose steps run on into the next file is listed in the file where it starts.
    """
    numbers, _ = number_slides(pages)
    sections, slide = [], None
    for index, (page, start) in enumerate(zip(pages, slide_starts(pages))):
        if not sections or sections[-1].number != page.section:
            sections.append(Section(page.section, page.section_name, page.backup))
        if start:
            slide = Slide(numbers[index], page.name, page.backup)
            sections[-1].slides.append(slide)
        slide.pages.append(index)
    return [section for section in sections if section.slides]


def title(name):
    """A title read from a page name or a section name: `point-wise-probability` becomes
    `Point wise probability`."""
    words = name.replace("-", " ").strip()
    return (words[:1].upper() + words[1:]) or name


def repeated_names(pages):
    """The names that start a slide more than once, each with the slide numbers it starts."""
    numbers, _ = number_slides(pages)
    seen = {}
    for index, start in enumerate(slide_starts(pages)):
        if start:
            seen.setdefault(pages[index].name, []).append(numbers[index])
    return {name: found for name, found in seen.items() if len(found) > 1}


def step_problems(pages):
    """The slides whose steps do not run 1, 2, 3 in page order, each with the steps it has."""
    numbers, _ = number_slides(pages)
    steps = {}
    for index, page in enumerate(pages):
        steps.setdefault(numbers[index], (page.name, []))[1].append(page.step)
    return [(number, name, found) for number, (name, found) in sorted(steps.items())
            if found != list(range(1, len(found) + 1))]


def file_name(section, name):
    return "%d-%s%s" % (section, name, SUFFIX)


def slug(text, length=48):
    """A name from a title, without its footnote markers, of as many whole words as fit."""
    text = re.sub(r"\[\d+(?:\s*,\s*\d+)*\]", " ", html.unescape(text))
    name = ""
    for word in re.findall(r"[A-Za-z0-9]+", text.lower()):
        longer = word if not name else name + "-" + word
        if len(longer) > length and name:
            break
        name = longer[:length]
    return name or "slide"
