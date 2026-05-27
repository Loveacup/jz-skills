#!/usr/bin/env node
/**
 * Xiaohongshu Card Renderer
 * Reads slides.html, screenshots each .slide div as 1080×1440 PNG,
 * then optionally merges into PDF via Pillow.
 *
 * Usage:
 *   node generate-slides.mjs [--dir <output-dir>] [--pdf <name.pdf>]
 *
 * Defaults:
 *   --dir  = current working directory (looks for slides.html there)
 *   --pdf  = auto-generated from directory name
 */
import { chromium } from 'playwright';
import { fileURLToPath } from 'url';
import path from 'path';
import fs from 'fs';
import { execSync } from 'child_process';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// Parse args
const args = process.argv.slice(2);
let dir = process.cwd();
let pdfName = '';

for (let i = 0; i < args.length; i++) {
  if (args[i] === '--dir' && args[i + 1]) dir = path.resolve(args[++i]);
  if (args[i] === '--pdf' && args[i + 1]) pdfName = args[++i];
}

const htmlPath = path.join(dir, 'slides.html');
if (!fs.existsSync(htmlPath)) {
  console.error(`Error: slides.html not found in ${dir}`);
  process.exit(1);
}

async function main() {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1440 } });

  await page.goto(`file://${htmlPath}`);
  // Wait for web fonts to load
  await page.waitForTimeout(3000);

  // Auto-discover all .slide elements
  const slideIds = await page.$$eval('.slide', els => els.map(el => el.id));
  if (slideIds.length === 0) {
    console.error('No .slide elements found in slides.html');
    await browser.close();
    process.exit(1);
  }

  const pngFiles = [];
  for (let i = 0; i < slideIds.length; i++) {
    const id = slideIds[i];
    const num = String(i + 1).padStart(2, '0');
    // Derive slug from id, fallback to number
    const slug = id ? id.replace(/^slide-?\d*-?/, '') || `page` : `page`;
    const filename = `${num}-slide-${slug}.png`;
    const el = await page.$(`#${id}`);
    if (!el) {
      console.error(`Element #${id} not found, skipping`);
      continue;
    }
    await el.screenshot({ path: path.join(dir, filename), type: 'png' });
    console.log(`Generated: ${filename}`);
    pngFiles.push(filename);
  }

  await browser.close();
  console.log(`\nDone! ${pngFiles.length} slides generated.`);

  // Merge to PDF
  if (pngFiles.length > 0) {
    if (!pdfName) {
      pdfName = path.basename(dir) + '.pdf';
    }
    const pdfPath = path.join(dir, pdfName);
    const fileList = pngFiles.map(f => `'${f}'`).join(', ');
    const pyScript = `
import os, sys
os.chdir('${dir.replace(/'/g, "\\'")}')
from PIL import Image
files = [${fileList}]
imgs = [Image.open(f).convert('RGB') for f in files]
imgs[0].save('${pdfName.replace(/'/g, "\\'")}', save_all=True, append_images=imgs[1:], resolution=150)
print(f'PDF: ${pdfName} ({len(imgs)} pages)')
`;
    try {
      execSync(`python3 -c ${JSON.stringify(pyScript)}`, { stdio: 'inherit' });
    } catch {
      console.log('PDF merge skipped (Pillow not available). PNGs are ready.');
    }
  }
}

main().catch(console.error);
