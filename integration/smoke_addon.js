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
    check('book references are prioritized above other resources',await page.locator('#d-body > :first-child').evaluate(node=>node.classList.contains('addon-context-card')));
    const labels=await page.locator('.addon-context-link').allTextContents();
    check('the selected architecture box gets mapped to subsections',labels.length>0&&labels.join(' ').includes('Unity Catalog')&&!labels[0].startsWith('14. Open Data Governance'),labels.join(' | '));
    check('the concise book preview is readable without hover',await page.locator('.addon-context-link p').first().isVisible());
    check('section and chapter actions are both available',await page.locator('.addon-context-link').first().getByRole('button').count()===2);
    await page.evaluate(()=>document.body.classList.add('theme-dark'));
    const contrast=await page.locator('.addon-context-link').first().evaluate(card=>{
      const rgb=value=>(value.match(/[\d.]+/g)||[]).slice(0,3).map(Number);
      const luminance=value=>{const [r,g,b]=rgb(value).map(channel=>{const x=channel/255;return x<=.04045?x/12.92:Math.pow((x+.055)/1.055,2.4)});return .2126*r+.7152*g+.0722*b};
      const ratio=(a,b)=>{const hi=Math.max(a,b),lo=Math.min(a,b);return(hi+.05)/(lo+.05)};
      const background=luminance(getComputedStyle(card).backgroundColor);
      return {
        heading:ratio(background,luminance(getComputedStyle(card.querySelector('strong')).color)),
        chapter:ratio(background,luminance(getComputedStyle(card.querySelector('span')).color)),
        preview:ratio(background,luminance(getComputedStyle(card.querySelector('p')).color))
      };
    });
    check('dark mode book card text meets readable contrast',Math.min(contrast.heading,contrast.chapter,contrast.preview)>=4.5,JSON.stringify(contrast));
    await page.locator('.addon-context-link').first().getByRole('button',{name:'Read section'}).click();
    const frame=page.frameLocator('.addon-shell iframe');await frame.locator('.passage').waitFor();
    check('only the selected passage opens',await frame.locator('.chapters').count()===0&&await frame.locator('.passage').count()===1);
    check('passage state reaches the parent URL',/[?&]chapter=/.test(page.url())&&/[?&]section=/.test(page.url()));
    await frame.locator('html.theme-dark').waitFor();check('passage follows board theme',await frame.locator('html').getAttribute('class')==='theme-dark');
    await frame.locator('#content').press('Escape');check('Escape closes the add-on',await page.locator('.addon-shell').count()===0);
    await page.locator('.addon-context-link').first().getByRole('button',{name:'Open chapter'}).click();
    const chapterFrame=page.frameLocator('.addon-shell iframe');await chapterFrame.locator('.chapter-view').waitFor();
    check('open chapter renders the complete chapter',await chapterFrame.locator('.chapter-view h2').count()>1);
  }finally{await browser.close();await new Promise(resolve=>server.close(resolve))}
  if(checks.some(value=>!value))process.exitCode=1;
})().catch(error=>{console.error(error);process.exitCode=1});
