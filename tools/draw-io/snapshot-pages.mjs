// Take a picture of each embedded page of a deck as it first draws, for deck_page_snapshots.py.
//
//   node snapshot-pages.mjs jobs.json
//
// jobs.json holds a list of {address, width, height, output}: the page as a file:// or https://
// address, the size of its cell on the slide, and the PNG to write.  Each page loads in headless
// Chromium in a window of the size of its cell, as the editor and the HTML deck lay it out, and the
// picture is taken after its load, two frames of drawing, and SNAPSHOT_WAIT more milliseconds,
// 500 by default, so that a plot has drawn.  The picture has twice the pixels of the cell, and
// keeps the parts of the page without a background transparent.  A page that does not load within
// SNAPSHOT_LOAD_WAIT milliseconds, 30000 by default, is reported, and its PNG is left as it was.
// The wait of a slide in export-pages.mjs is PAGE_WAIT, a variable of its own.
//
// Playwright is the one of `tools/package.json`, which Node finds from the folder of this script.
import fs from 'fs';
import playwrightChromium from 'playwright-chromium';

const { chromium } = playwrightChromium;
const jobs = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const settle = parseInt(process.env.SNAPSHOT_WAIT || '500', 10);
const timeout = parseInt(process.env.SNAPSHOT_LOAD_WAIT || '30000', 10);

const browser = await chromium.launch();
let failed = 0;
for (const job of jobs) {
  const page = await browser.newPage({
    viewport: { width: Math.ceil(job.width), height: Math.ceil(job.height) },
    deviceScaleFactor: 2,
  });
  try {
    await page.goto(job.address, { waitUntil: 'load', timeout });
    await page.evaluate(() => new Promise(done =>
      requestAnimationFrame(() => requestAnimationFrame(done))));
    await page.waitForTimeout(settle);
    await page.screenshot({ path: job.output, omitBackground: true });
  } catch (error) {
    failed++;
    console.error('the page %s gave no picture: %s', job.address, error.message.split('\n')[0]);
  } finally {
    await page.close();
  }
}
await browser.close();
console.log('%d pictures of embedded pages taken', jobs.length - failed);
