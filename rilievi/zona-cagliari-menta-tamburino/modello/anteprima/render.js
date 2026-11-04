// Renderizza la scena dalle camere delle riprese Street View (manifest) → anteprima/out/SV-xx.png
// Uso: node render.js   (Playwright e Chromium preinstallati)
const { chromium } = require('playwright');
const fs = require('fs'), path = require('path');
(async () => {
  const Z = path.resolve(__dirname, '..', '..');
  const scena = JSON.parse(fs.readFileSync(path.join(Z, 'modello/scena.json')));
  const pal = JSON.parse(fs.readFileSync(path.join(Z, 'scheda.json'))).palette;
  const man = JSON.parse(fs.readFileSync(path.join(Z, '_rif_google/manifest_riprese.json')));
  const O = scena.origine, KX = 111320 * Math.cos(O.lat * Math.PI / 180), KY = 111320;
  const out = path.join(__dirname, 'out'); fs.mkdirSync(out, { recursive: true });
  const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
  const page = await browser.newPage({ viewport: { width: 640, height: 640 } });
  page.on('console', m => { if (m.type() === 'error') console.error('PAGE', m.text()); });
  await page.goto('file://' + path.join(__dirname, 'anteprima.html'));
  await page.evaluate(([s, p]) => build(s, p), [scena, pal]);
  const only = process.argv.slice(2);
  for (const r of man.riprese) {
    if (only.length && !only.includes(r.id)) continue;
    const x = (r.lng - O.lng) * KX, y = (r.lat - O.lat) * KY;
    const url = await page.evaluate(a => shoot(...a), [x, y, r.heading, r.pitch, r.fov]);
    fs.writeFileSync(path.join(out, r.id + '.png'), Buffer.from(url.split(',')[1], 'base64'));
  }
  await browser.close(); console.log('ok');
})();
