#!/usr/bin/env node
'use strict';
const { chromium } = require('playwright');
const { serve, boardReady } = require('./lib_serve');

const checks=[];
function check(name,value,detail){checks.push(!!value);console.log((value?'PASS ':'FAIL ')+name+(detail?' :: '+detail:''))}

(async()=>{
  const server=await serve();const browser=await chromium.launch();
  try{
    const page=await browser.newPage({viewport:{width:1440,height:900}});await page.addInitScript(()=>localStorage.setItem('dbx-arch-tour-v1','1'));
    await page.goto('http://127.0.0.1:'+server.address().port+'/index.html?industry=banking',{waitUntil:'networkidle'});await boardReady(page);await page.waitForSelector('.addon-launcher');
    check('book launcher is installed',await page.locator('.addon-launcher').textContent()==='Book');
    const unity=page.locator('.atom:visible').filter({hasText:'Unity Catalog'}).first();await unity.click();
    await page.locator('.addon-context-link').first().waitFor();
    const labels=await page.locator('.addon-context-link').allTextContents();
    check('the selected architecture box gets mapped book passages',labels.length>0&&labels.join(' ').includes('Unity Catalog'),labels.join(' | '));
    await page.locator('.addon-context-link').first().click();
    const frame=page.frameLocator('.addon-shell iframe');await frame.locator('.passage').waitFor();
    check('only the selected passage opens',await frame.locator('.chapters').count()===0&&await frame.locator('.passage').count()===1);
    check('passage state reaches the parent URL',/[?&]chapter=/.test(page.url())&&/[?&]section=/.test(page.url()));
    await page.evaluate(()=>document.body.classList.add('theme-dark'));await frame.locator('html.theme-dark').waitFor();check('passage follows board theme',await frame.locator('html').getAttribute('class')==='theme-dark');
    await frame.locator('#content').press('Escape');check('Escape closes the add-on',await page.locator('.addon-shell').count()===0);
  }finally{await browser.close();await new Promise(resolve=>server.close(resolve))}
  if(checks.some(value=>!value))process.exitCode=1;
})().catch(error=>{console.error(error);process.exitCode=1});
