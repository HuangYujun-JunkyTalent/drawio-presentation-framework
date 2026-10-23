// Writes a PNG of each built slide of a deck, and contact sheets of twelve slides each.
//
// Usage, from the root of the repository, after `npm run html` or `npm run build` in the deck:
//
//     node skills/deck-skeleton/screenshot-slides.mjs <deck folder> <output folder>
//
// The script loads playwright-chromium from `tools/node_modules/`, where `npm install` in `tools/` puts it.
// It opens each SVG of `build/slides/` at 1920 by 1080 and writes `slide-NN.png`.
// It then lays the PNGs out three across and four down, at a third of their size, in `sheet-N.png`.
import fs from 'fs';
import path from 'path';
import { createRequire } from 'module';
import { fileURLToPath, pathToFileURL } from 'url';

const [deck, out] = process.argv.slice(2).map(p => path.resolve(p));
if (!deck || !out) {
  console.error('usage: node screenshot-slides.mjs <deck folder> <output folder>');
  process.exit(2);
}
const tools = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..', 'tools');
const { chromium } = createRequire(path.join(tools, 'package.json'))('playwright-chromium');
const built = path.join(deck, 'build', 'slides');
const slides = fs.readdirSync(built).filter(name => /^slide-\d+\.svg$/.test(name))
  .sort((a, b) => parseInt(a.slice(6), 10) - parseInt(b.slice(6), 10));
fs.mkdirSync(out, { recursive: true });

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
const shots = [];
for (const name of slides) {
  await page.goto(pathToFileURL(path.join(built, name)).href, { waitUntil: 'networkidle' });
  await page.waitForTimeout(500);
  const shot = path.join(out, name.replace(/\.svg$/, '.png'));
  await page.screenshot({ path: shot });
  shots.push(shot);
}

const across = 3, down = 4, width = 640, height = 360, margin = 10;
await page.setViewportSize({ width: across * (width + margin) + margin, height: down * (height + margin) + margin });
for (let first = 0; first < shots.length; first += across * down) {
  const images = shots.slice(first, first + across * down)
    .map(shot => `<img src="${pathToFileURL(shot).href}" style="width:${width}px;height:${height}px;background:#fff">`).join('');
  const sheet = path.join(out, `sheet-${first / (across * down) + 1}`);
  fs.writeFileSync(sheet + '.html', `<!doctype html><body style="margin:0;padding:${margin}px;background:#888;`
    + `display:grid;grid-template-columns:repeat(${across},${width}px);gap:${margin}px">${images}</body>`);
  await page.goto(pathToFileURL(sheet + '.html').href, { waitUntil: 'load' });
  await page.screenshot({ path: sheet + '.png', fullPage: true });
  fs.unlinkSync(sheet + '.html');
}
await browser.close();
console.log(`${shots.length} slides and ${Math.ceil(shots.length / (across * down))} sheets written to ${out}`);
