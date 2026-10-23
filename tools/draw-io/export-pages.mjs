// Export every page of a .drawio.xml file to an SVG, through the diagrams.net viewer.
//
// The viewer is the library of draw.io that draws a page in a web page as the editor draws it.
// The script takes the viewer that the newest installed VS Code extension hediet.vscode-drawio
// bundles, so the export needs no network and draws with the draw.io of the editor.  DRAWIO_VIEWER
// names another viewer-static.min.js, as a path, a file: address or an address on the web, and
// without either the viewer loads from viewer.diagrams.net.  A viewer on this machine finds
// MathJax, its fonts, the stencils and the pictures in the folder `webapp` of draw.io around it
// instead of viewer.diagrams.net, so it must sit in `webapp/js/`, and the script stops when that
// folder holds no math4/es5/startup.js.  The viewer draws the page into an SVG element, and that
// element, given the page's own size and viewBox, is the exported asset.  Labels stay HTML inside
// a foreignObject, so an equation stays MathJax output rather than a picture.  The group that
// draws the shape of a cell with the property `video` or `html` carries `data-cell-id`, so that
// the HTML deck that deck_html.py writes puts the video or the page in that group, behind the
// cells drawn after it.  The group draws the shape in the coordinates of the page, and a group
// around the drawing applies the offset of the view, so the rectangle of the cell in the draw.io
// file places the video.
//
//   node export-pages.mjs slides.drawio.xml outdir pageCount [width] [height] [cache]
//
// EXPORT_WORKERS pages, 4 by default, export at once, each in a tab of its own.  A page is ready
// when the viewer has drawn it and the fonts have loaded, and on a page with mathematical
// typesetting on, when every formula is typeset as well.  A page with the typesetting off keeps
// its TeX as text.  PAGE_WAIT, 15000 ms by default, is the most a page may take.  A page that is
// not ready by then is exported as it stood, with a warning, and the next build exports it again.
// When a page gives no SVG, the script removes the SVG of an earlier build at its place and ends
// with exit status 1.  The pictures of embedded pages have a wait of their own,
// SNAPSHOT_LOAD_WAIT of snapshot-pages.mjs.
//
// The folder `cache`, when given, keeps the SVG of each ready page under a hash of the page, its
// size, the rules of the list markers and this script, so a page that has not changed since an
// earlier build is copied rather than exported again.  The key holds the viewer and the version of
// Chromium, so a new version of the extension or of playwright-chromium exports every page again.
// The key holds the address alone of a viewer on the web, so a new release of viewer.diagrams.net
// keeps the SVGs of the old one until EXPORT_FRESH=1, which exports every page again at any time.
// After the export, the cache holds the files of its pages and the files that another export
// wrote or copied since its start, so the cache does not grow with every edit.
//
// Two exports of one deck may run at once, such as `npm run watch` and `npm run pdf`.  Each page
// shell carries the process id in its name.  An SVG and a cache file are written under a name
// that holds the process id and then renamed over their target, so the other export finds the
// earlier file or the new one, and the SVG of an earlier build stays at its place until the page
// gives its own.  An export gives each cache file that it copies the time of the copy, which
// keeps the file in the cache of the other export.  At its start, an export removes the page
// shells and the partial SVGs of an export whose process no longer runs, such as one stopped by
// Ctrl-C.
//
// Playwright is the one of `tools/package.json`, which Node finds from the folder of this script.
// An SVG that a page loads through <img> fetches nothing, so the drawing holds each of its pictures
// as data already, as build-slides.py writes them into the assembled deck.
import crypto from 'crypto';
import fs from 'fs';
import os from 'os';
import path from 'path';
import { fileURLToPath, pathToFileURL } from 'url';
import playwrightChromium from 'playwright-chromium';

const { chromium } = playwrightChromium;

const file = process.argv[2];
const outdir = process.argv[3];
const pageCount = parseInt(process.argv[4], 10);
const width = parseInt(process.argv[5] || '1920', 10);
const height = parseInt(process.argv[6] || '1080', 10);
const cache = process.argv[7] ? path.resolve(process.argv[7]) : null;
const fresh = process.env.EXPORT_FRESH === '1';
const workers = Math.max(1, parseInt(process.env.EXPORT_WORKERS, 10) || 4);
const pageWait = parseInt(process.env.PAGE_WAIT || '15000', 10);
const started = Date.now();
const script = fs.readFileSync(new URL(import.meta.url), 'utf8');

// The rules of the list markers, which list-styles.plugin.js gives the editor, so that a slide
// shows its markers as the editor does.  They are read from the array MARKER_CSS of that plugin.
const listPlugin = fs.readFileSync(new URL('./list-styles.plugin.js', import.meta.url), 'utf8');
const markerArray = /var MARKER_CSS = (\[[\s\S]*?\])\.join/.exec(listPlugin);
if (!markerArray) throw new Error('list-styles.plugin.js holds no array MARKER_CSS');
const markerCss = Function('"use strict"; return ' + markerArray[1])().join('\n');

// The extensions of VS Code Insiders count as installed beside those of VS Code.
function bundledViewer() {
  const found = [];
  for (const root of ['.vscode', '.vscode-insiders'].map(name => path.join(os.homedir(), name, 'extensions'))) {
    if (!fs.existsSync(root)) continue;
    for (const name of fs.readdirSync(root)) {
      const match = /^hediet\.vscode-drawio-(\d+(?:\.\d+)*)$/.exec(name);
      const file = path.join(root, name, 'drawio', 'src', 'main', 'webapp', 'js', 'viewer-static.min.js');
      if (match && fs.existsSync(file)) found.push({ version: match[1].split('.').map(Number), file });
    }
  }
  found.sort((a, b) => {
    for (let i = 0; i < Math.max(a.version.length, b.version.length); i++) {
      if ((a.version[i] || 0) != (b.version[i] || 0)) return (a.version[i] || 0) - (b.version[i] || 0);
    }
    return 0;
  });
  return found.length ? found[found.length - 1].file : null;
}

const WEB_VIEWER = 'https://viewer.diagrams.net/js/viewer-static.min.js';
const named = process.env.DRAWIO_VIEWER || bundledViewer() || WEB_VIEWER;
const viewerIsFile = !/^https?:/.test(named);
const viewer = viewerIsFile ? path.resolve(/^file:/.test(named) ? fileURLToPath(named) : named) : named;
if (viewerIsFile && !fs.existsSync(viewer)) {
  console.error('DRAWIO_VIEWER names %s, which does not exist', viewer);
  process.exit(1);
}
const viewerAddress = viewerIsFile ? pathToFileURL(viewer).href : viewer;
const webappFolder = viewerIsFile ? path.dirname(path.dirname(viewer)) : null;
if (webappFolder && !fs.existsSync(path.join(webappFolder, 'math4', 'es5', 'startup.js'))) {
  console.error('the viewer %s lies outside the folder webapp of draw.io: %s holds no '
    + 'math4/es5/startup.js, so its formulas would stay TeX; name the viewer-static.min.js in webapp/js/',
    viewer, webappFolder);
  process.exit(1);
}
const webapp = webappFolder ? pathToFileURL(webappFolder).href : null;
const viewerPaths = webapp ? `<script>
window.DRAW_MATH_URL = '${webapp}/math4/es5';
window.STENCIL_PATH = '${webapp}/stencils';
window.SHAPES_PATH = '${webapp}/shapes';
window.IMAGE_PATH = '${webapp}/images';
window.STYLE_PATH = '${webapp}/styles';
window.mxBasePath = '${webapp}/mxgraph/';
window.mxImageBasePath = '${webapp}/mxgraph/images';
</script>
` : '';
const viewerStat = viewerIsFile ? fs.statSync(viewer) : null;
const viewerKey = viewerIsFile ? `${viewer} ${viewerStat.size} ${viewerStat.mtimeMs}` : viewer;
console.log('viewer: %s', viewer);

const whole = fs.readFileSync(file, 'utf8');
fs.mkdirSync(outdir, { recursive: true });

const browser = await chromium.launch();
const browserVersion = browser.version();
const written = [];
const used = new Set();
let copied = 0;

const diagrams = whole.match(/<diagram [\s\S]*?<\/diagram>/g) || [];

function processRuns(pid) {
  try {
    process.kill(pid, 0);
    return true;
  } catch (error) {
    return error.code !== 'ESRCH';
  }
}

for (const name of fs.readdirSync(outdir)) {
  const match = /^(?:\.page-(\d+)-\d+\.html|slide-\d+\.svg\.(\d+)\.tmp)$/.exec(name);
  if (match && !processRuns(Number(match[1] || match[2]))) {
    fs.rmSync(path.join(outdir, name), { force: true });
  }
}

function replaceFile(target, write) {
  const partial = `${target}.${process.pid}.tmp`;
  write(partial);
  fs.renameSync(partial, target);
}

async function exportPage(page, index) {
  const xml = `<mxfile host="export-pages.mjs" pages="1">\n${diagrams[index]}\n</mxfile>\n`;
  const target = path.join(outdir, `slide-${String(index + 1).padStart(2, '0')}.svg`);
  const key = crypto.createHash('sha1')
    .update(`${width}x${height}\n${viewerKey}\n${browserVersion}\n${script}\n${markerCss}\n${xml}`)
    .digest('hex');
  const cached = cache ? path.join(cache, `${key}.svg`) : null;
  if (cached) used.add(path.basename(cached));
  if (cached && !fresh && fs.existsSync(cached)) {
    replaceFile(target, partial => fs.copyFileSync(cached, partial));
    const now = new Date();
    fs.utimesSync(cached, now, now);
    written.push(target);
    copied++;
    return;
  }
  const cfg = JSON.stringify({ nav: false, resize: false, toolbar: '', xml, border: 0, math: true, zoom: 1, page: 0 });
  const esc = cfg.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/"/g, '&quot;');
  const shell = path.resolve(outdir, `.page-${process.pid}-${index}.html`);
  fs.writeFileSync(shell, `<!doctype html><html><head><meta charset="utf-8"></head>
<body style="margin:0;background:#fff">
<div id="page" data-mxgraph="${esc}"></div>
${viewerPaths}<script src="${viewerAddress}"></script>
<script>GraphViewer.createViewerForElement(document.getElementById('page'),
  function (viewer) { window.pageViewer = viewer; });</script></body></html>`);
  let svg = null;
  let ready = true;
  try {
    await page.goto(pathToFileURL(shell).href);
    await page.waitForFunction(() => {
      const svg = document.querySelector('#page svg');
      if (!svg || !window.pageViewer || document.fonts.status !== 'loaded') return false;
      return !window.pageViewer.graph.mathEnabled || ![...svg.querySelectorAll('foreignObject')]
        .some(node => /\\\(|\$\$/.test(node.textContent));
    }, null, { timeout: pageWait, polling: 250 })
      .catch(() => {
        ready = false;
        console.error('page %d was not ready within PAGE_WAIT; exported as it stood and kept out of '
          + 'the cache', index + 1);
      });
    // Two frames of drawing after the page is ready, so the last layout is on the page.
    await page.evaluate(() => new Promise(done =>
      requestAnimationFrame(() => requestAnimationFrame(done))));
    svg = await page.evaluate(([w, h, markers]) => {
      const element = document.querySelector('#page svg');
      if (!element) return null;
      const graph = window.pageViewer.graph;
      for (const cell of Object.values(graph.model.cells)) {
        const state = graph.view.getState(cell);
        const value = cell.value && cell.value.getAttribute ? cell.value : null;
        const media = value ? value.getAttribute('video') || value.getAttribute('html') : null;
        if (!media || !state || !state.shape || !state.shape.node) continue;
        state.shape.node.setAttribute('data-cell-id', cell.id);
      }
      const clone = element.cloneNode(true);
      clone.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
      clone.setAttribute('xmlns:xlink', 'http://www.w3.org/1999/xlink');
      clone.removeAttribute('style');
      // The view box starts at the offset of the group that the header names.  The viewer wraps the
      // drawing in groups that carry no transform, so the group is found by its transform rather
      // than taken as the first one.
      let transform = '';
      for (const group of element.querySelectorAll('g')) {
        const value = group.getAttribute('transform') || '';
        if (/translate\(/.test(value)) { transform = value; break; }
      }
      const translate = /translate\(([-\d.]+)[, ]+([-\d.]+)\)/.exec(transform);
      const zoom = /scale\(([-\d.]+)\)/.exec(transform);
      const scale = zoom ? parseFloat(zoom[1]) : 1;
      const tx = translate ? parseFloat(translate[1]) : 0;
      const ty = translate ? parseFloat(translate[2]) : 0;
      clone.setAttribute('width', w);
      clone.setAttribute('height', h);
      clone.setAttribute('viewBox', `${tx} ${ty} ${w * scale} ${h * scale}`);
      // An edge with flowAnimation=1 names a @keyframes rule that the viewer writes into the head
      // of the page, outside the SVG, so the rules that the SVG names travel inside it.
      const markup = clone.outerHTML;
      const animations = [...document.head.querySelectorAll('style')]
        .map(style => style.textContent)
        .filter(css => [...css.matchAll(/@keyframes\s+([\w-]+)/g)].some(m => markup.includes(m[1])));
      // A slide with a list carries the rules of the markers.
      const rules = animations.concat(clone.querySelector('ul, ol') ? [markers] : []);
      if (rules.length) {
        const style = document.createElementNS('http://www.w3.org/2000/svg', 'style');
        style.textContent = rules.join('\n');
        clone.insertBefore(style, clone.firstChild);
      }
      return new XMLSerializer().serializeToString(clone);
    }, [width, height, markerCss]);
  } finally {
    fs.rmSync(shell, { force: true });
  }
  if (!svg) {
    fs.rmSync(target, { force: true });
    console.error('page %d produced no SVG', index + 1);
    return;
  }
  const text = '<?xml version="1.0" encoding="UTF-8"?>\n' + svg + '\n';
  replaceFile(target, partial => fs.writeFileSync(partial, text));
  if (cached && ready) replaceFile(cached, partial => fs.writeFileSync(partial, text));
  written.push(target);
}

if (cache) fs.mkdirSync(cache, { recursive: true });
let next = 0;
await Promise.all(Array.from({ length: Math.min(workers, pageCount) }, async () => {
  const page = await browser.newPage({ viewport: { width: width + 200, height: height + 200 } });
  while (next < pageCount) await exportPage(page, next++);
  await page.close();
}));
await browser.close();
if (cache) {
  for (const name of fs.readdirSync(cache)) {
    const file = path.join(cache, name);
    if (!/\.(svg|tmp)$/.test(name) || used.has(name)) continue;
    const stat = fs.statSync(file, { throwIfNoEntry: false });
    if (stat && stat.mtimeMs < started) fs.rmSync(file, { force: true });
  }
}
console.log('%d pages exported to %s, %d of them unchanged and copied from the cache',
  written.length, outdir, copied);
if (written.length < pageCount) {
  console.error('%d of %d pages produced no SVG', pageCount - written.length, pageCount);
  process.exitCode = 1;
}
