// Builds PullSignal Guard: esbuild bundles -> dist/, then dist-chrome/ and dist-firefox/ with their own manifests.
import { build } from 'esbuild';
import { cpSync, existsSync, mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { execFileSync } from 'node:child_process';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const pkg = JSON.parse(readFileSync(join(ROOT, 'package.json'), 'utf8'));
const RENDER_API = 'https://pullsignal.onrender.com';
const FLAVORS = [
  { suffix: '', api: RENDER_API, name: 'PullSignal Guard', gecko: 'guard@pullsignal.dev' },
  { suffix: '-local', api: 'http://localhost:8001', name: 'PullSignal Guard Local', gecko: 'guard-local@pullsignal.dev' },
];

if (!existsSync(join(ROOT, 'static', 'icons', 'icon-128.png'))) {
  execFileSync(process.execPath, [join(ROOT, 'scripts', 'icons.mjs')], { stdio: 'inherit' });
}

const HOSTS = [
  'https://pullsignal.onrender.com/*',
  '*://*.amazon.com/*',
  '*://*.ebay.com/*',
  '*://*.walmart.com/*',
  '*://*.target.com/*',
  'https://*.ondigitalocean.app/*',
  'http://localhost:8000/*',
  'http://localhost:8001/*',
  'http://127.0.0.1:8000/*',
  '<all_urls>', // generic schema.org fallback + a configurable (deployed) API base
];


async function bundle(DIST, api) {
rmSync(DIST, { recursive: true, force: true });
await build({
  entryPoints: {
    background: join(ROOT, 'src', 'background.ts'),
    content: join(ROOT, 'src', 'content.ts'),
    popup: join(ROOT, 'src', 'popup.ts'),
  },
  outdir: DIST,
  bundle: true,
  format: 'iife', // classic scripts: MV3 content scripts can't be modules; works for both backgrounds
  target: ['chrome110', 'firefox121'],
  minify: false,
  sourcemap: false,
  legalComments: 'none',
  logLevel: 'info',
  define: { __API__: JSON.stringify(api) },
});
cpSync(join(ROOT, 'static'), DIST, { recursive: true });

}

const icons = { 16: 'icons/icon-16.png', 32: 'icons/icon-32.png', 48: 'icons/icon-48.png', 128: 'icons/icon-128.png' };
for (const f of FLAVORS) {
const DIST = join(ROOT, 'dist' + f.suffix);
await bundle(DIST, f.api);
const base = {
  manifest_version: 3,
  name: f.name,
  version: pkg.version,
  description: 'Tags products that match U.S. CPSC recalls while you shop, and warns you before you buy.',
  icons,
  action: { default_popup: 'popup.html', default_title: f.name, default_icon: icons },
  permissions: ['storage'],
  host_permissions: HOSTS,
  content_scripts: [{ matches: ['<all_urls>'], js: ['content.js'], run_at: 'document_idle', all_frames: false }],
  // Explicit CSP without upgrade-insecure-requests so http://localhost:8000 works from extension pages.
  content_security_policy: { extension_pages: "script-src 'self'; object-src 'self'" },
};

const targets = {
  'dist-chrome': { ...base, background: { service_worker: 'background.js' }, minimum_chrome_version: '110' },
  'dist-firefox': {
    ...base,
    background: { scripts: ['background.js'] },
    browser_specific_settings: { gecko: { id: f.gecko, strict_min_version: '121.0' } },
  },
};

for (const [dir, manifest] of Object.entries(targets)) {
  const out = join(ROOT, dir + f.suffix);
  rmSync(out, { recursive: true, force: true });
  mkdirSync(out, { recursive: true });
  cpSync(DIST, out, { recursive: true });
  writeFileSync(join(out, 'manifest.json'), JSON.stringify(manifest, null, 2));
  console.log(`built ${dir}${f.suffix}/ -> ${f.api}`);
}
}
