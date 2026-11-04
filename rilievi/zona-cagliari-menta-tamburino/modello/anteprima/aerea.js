// Viste aeree del modello (camere libere, nessuna immagine Google) → anteprima/vista_*.png
const { chromium } = require('playwright'); const fs = require('fs'), path = require('path');
(async () => {
  const Z = path.resolve(__dirname, '..', '..');
  const ctx = JSON.parse(fs.readFileSync(path.join(Z, 'modello/contesto.json')));
  const b = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
  const p = await b.newPage({ viewport: { width: 640, height: 640 } });
  await p.goto('file://' + path.join(__dirname, 'anteprima.html'));
  await p.evaluate(c => { buildCtx(c); renderer.setSize(1600, 1000); }, ctx);
  const viste = { aerea_SO: [-40, -30, 38, -32, 55, 30], aerea_NE: [45, 70, 215, -30, 55, 28], angolo_pedone: [-12, 4, 40, 4, 75, 1.6] };
  for (const [n, a] of Object.entries(viste)) {
    const url = await p.evaluate(a => { const cam = new THREE.PerspectiveCamera(a[4], 1.6, 0.3, 2000);
      const z = window.tz(a[0], a[1]) + a[5], h = a[2]*Math.PI/180, q = a[3]*Math.PI/180;
      cam.position.copy(Vv([a[0], a[1], z])); cam.lookAt(cam.position.clone().add(Vv([Math.sin(h)*Math.cos(q), Math.cos(h)*Math.cos(q), Math.sin(q)])));
      renderer.render(scene, cam); return renderer.domElement.toDataURL('image/png'); }, a);
    fs.writeFileSync(path.join(__dirname, `vista_${n}.png`), Buffer.from(url.split(',')[1], 'base64'));
  }
  await b.close(); console.log('ok');
})();
