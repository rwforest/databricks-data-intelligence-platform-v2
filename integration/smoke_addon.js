#!/usr/bin/env node
'use strict';
const { chromium } = require('playwright');
const { serve, boardReady } = require('./lib_serve');

const checks = [];
function check(name, value, detail) {
  checks.push(!!value);
  console.log((value ? 'PASS ' : 'FAIL ') + name + (detail ? ' :: ' + detail : ''));
}

(async () => {
  const server = await serve();
  const browser = await chromium.launch();
  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
    await page.addInitScript(() => localStorage.setItem('dbx-arch-tour-v1', '1'));
    await page.goto('http://127.0.0.1:' + server.address().port + '/index.html?industry=banking', { waitUntil: 'networkidle' });
    await boardReady(page);
    await page.waitForSelector('.addon-launcher');
    check('book launcher is installed', await page.locator('.addon-launcher').textContent() === 'Book');
    await page.click('.addon-launcher');
    const frame = page.frameLocator('.addon-shell iframe');
    await frame.locator('.chapter-link').first().waitFor();
    check('reader exposes every manuscript file', await frame.locator('.chapter-link').count() === 32);
    await frame.locator('#search').fill('Unity Catalog');
    await frame.locator('.result').first().waitFor();
    check('full-text search returns results', await frame.locator('.result').count() > 0);
    await frame.locator('.result').first().click();
    check('chapter state reaches the parent URL', /[?&]chapter=/.test(page.url()));
    await page.evaluate(() => document.body.classList.add('theme-dark'));
    await frame.locator('html.theme-dark').waitFor();
    check('reader follows board theme', await frame.locator('html').getAttribute('class') === 'theme-dark');
    await frame.locator('#content').press('Escape');
    check('Escape closes the add-on', await page.locator('.addon-shell').count() === 0);
  } finally {
    await browser.close();
    await new Promise(resolve => server.close(resolve));
  }
  if (checks.some(value => !value)) process.exitCode = 1;
})().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
