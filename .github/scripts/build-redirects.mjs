import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const root = fileURLToPath(new URL('../..', import.meta.url));
const output = path.join(root, '.legacy-redirects');
const primary = 'https://olajumokemedunoye.com';
const pages = ['index.html', ...fs.readdirSync(path.join(root, 'projects')).filter(name => name.endsWith('.html')).map(name => 'projects/' + name)];

function redirectPage(file, fallback = false) {
  const target = primary + (file === 'index.html' || fallback ? '/' : '/' + file);
  return `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Olajumoke Medunoye — Portfolio</title>
<link rel="canonical" href="${target}">
<meta http-equiv="refresh" content="0;url=${target}">
<script>location.replace(${JSON.stringify(primary)} + (location.pathname === '/index.html' ? '/' : location.pathname) + location.search + location.hash);</script>
</head>
<body><p>My portfolio has moved to <a href="${target}">OlajumokeMedunoye.com</a>.</p></body>
</html>
`;
}

for (const file of [...pages, '404.html']) {
  const target = path.join(output, file);
  fs.mkdirSync(path.dirname(target), {recursive: true});
  fs.writeFileSync(target, redirectPage(file, file === '404.html'));
}
fs.writeFileSync(path.join(output, '.nojekyll'), '');
fs.writeFileSync(path.join(output, 'robots.txt'), 'User-agent: *\nAllow: /\nSitemap: ' + primary + '/sitemap.xml\n');
console.log('Built ' + pages.length + ' legacy page redirects and a fallback.');
