// Print the SVGs of a built deck into one PDF, one page per SVG, at the size of the slide.
//
// build-slides.py runs this script in its modes `build` and `pdf`, after the export, so the SVGs
// already carry the slide numbers, the TeX definitions and the pictures, and leave out the hidden
// pages.  The SVGs are printed as they are, by the Chromium of the Playwright of `tools/`, so the
// PDF shows what the HTML file shows.
//
//   node print-pdf.mjs svgdir pageCount output.pdf [width] [height] [outline.json]
//
// outline.json, which the build writes, lists the bookmarks of the PDF, each with its level, its
// page and its title.  Chromium makes the bookmarks from the headings of the page it prints, so
// each bookmark is a heading on its page that holds a transparent picture of one pixel with the
// title as its alternative text.  The title is then no text of the PDF, so a search and a copy of
// the text do not find it.
//
// Playwright is the one of `tools/package.json`, which Node finds from the folder of this script.
import fs from 'fs';
import path from 'path';
import { pathToFileURL } from 'url';
import playwrightChromium from 'playwright-chromium';

const { chromium } = playwrightChromium;

const svgdir = path.resolve(process.argv[2]);
const pageCount = parseInt(process.argv[3], 10);
const output = path.resolve(process.argv[4]);
const width = parseInt(process.argv[5] || '1920', 10);
const height = parseInt(process.argv[6] || '1080', 10);
const outlineFile = process.argv[7];
const bookmarks = outlineFile && fs.existsSync(outlineFile)
  ? JSON.parse(fs.readFileSync(outlineFile, 'utf8')) : [];

const escape = text => text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  .replace(/"/g, '&quot;');
const PIXEL = 'data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==';

const images = [];
for (let index = 1; index <= pageCount; index++) {
  const file = path.join(svgdir, `slide-${String(index).padStart(2, '0')}.svg`);
  if (!fs.existsSync(file)) throw new Error(`${file} is missing; run the build first`);
  const headings = bookmarks.filter(mark => mark.page === index)
    .map(mark => `<h${mark.level}><img alt="${escape(mark.title)}" src="${PIXEL}"></h${mark.level}>`)
    .join('');
  images.push(`<div class="page">${headings}<img src="${pathToFileURL(file).href}"></div>`);
}

// The shell sits beside the SVGs, so that the file URLs load, and is removed after printing.
const shell = path.join(svgdir, '.print-pdf.html');
fs.writeFileSync(shell, `<!doctype html><html><head><meta charset="utf-8"><style>
@page { size: ${width}px ${height}px; margin: 0; }
html, body { margin: 0; background: #fff; }
.page { position: relative; width: ${width}px; height: ${height}px; overflow: hidden;
  break-after: page; }
.page h1, .page h2, .page h3 { position: absolute; top: 0; left: 0; margin: 0; font-size: 1px; }
.page h1 img, .page h2 img, .page h3 img { width: 1px; height: 1px; }
.page:last-child { break-after: auto; }
.page > img { display: block; width: ${width}px; height: ${height}px; }
</style></head><body>
${images.join('\n')}
</body></html>`);

const browser = await chromium.launch();
try {
  const page = await browser.newPage({ viewport: { width, height } });
  await page.goto(pathToFileURL(shell).href);
  const broken = await page.evaluate(async () => {
    const all = [...document.querySelectorAll('.page > img')];
    await Promise.all(all.map(image => image.decode().catch(() => null)));
    return all.filter(image => !image.naturalWidth).map(image => image.src);
  });
  if (broken.length) throw new Error(`these SVGs did not load: ${broken.join(', ')}`);
  fs.mkdirSync(path.dirname(output), { recursive: true });
  await page.pdf({ path: output, width: `${width}px`, height: `${height}px`,
    printBackground: true, preferCSSPageSize: true, outline: bookmarks.length > 0,
    tagged: bookmarks.length > 0 });
} finally {
  await browser.close();
  fs.rmSync(shell, { force: true });
}
console.log('%d pages printed to %s', pageCount, output);
