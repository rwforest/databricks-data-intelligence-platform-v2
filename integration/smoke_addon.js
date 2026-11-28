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
    const officialLinks=page.locator('.addon-official a');check('official docs and video remain visible beside the book',await officialLinks.count()>=2&&await page.locator('.addon-official').getByText('Documentation',{exact:true}).count()===1&&await page.locator('.addon-official').getByText('Video',{exact:true}).count()===1);
    check('promoted references use only official Databricks sources',await officialLinks.evaluateAll(links=>links.every(link=>{const host=new URL(link.href).hostname.replace(/^www\./,'');return ['databricks.com','docs.databricks.com','youtube.com','youtu.be'].some(domain=>host===domain||host.endsWith('.'+domain))})));
    check('the full native documentation and video sections are retained',(await page.locator('#d-body').innerText()).includes('LEARN MORE')&&(await page.locator('#d-body').innerText()).includes('DATABRICKS YOUTUBE CHANNEL'));
    await page.evaluate(()=>document.body.classList.add('theme-dark'));
    const contrast=await page.locator('.addon-context-link').first().evaluate(card=>{
      const rgb=value=>(value.match(/[\d.]+/g)||[]).slice(0,3).map(Number);
      const luminance=value=>{const [r,g,b]=rgb(value).map(channel=>{const x=channel/255;return x<=.04045?x/12.92:Math.pow((x+.055)/1.055,2.4)});return .2126*r+.7152*g+.0722*b};
      const ratio=(a,b)=>{const hi=Math.max(a,b),lo=Math.min(a,b);return(hi+.05)/(lo+.05)};
      const background=luminance(getComputedStyle(card).backgroundColor);
      return {
        heading:ratio(background,luminance(getComputedStyle(card.querySelector('h5')).color)),
        chapter:ratio(background,luminance(getComputedStyle(card.querySelector('span')).color)),
        preview:ratio(background,luminance(getComputedStyle(card.querySelector('p')).color))
      };
    });
    check('dark mode book card text meets readable contrast',Math.min(contrast.heading,contrast.chapter,contrast.preview)>=4.5,JSON.stringify(contrast));
    await page.locator('.addon-context-link').first().getByRole('button',{name:'Read section'}).click();
    const frame=page.frameLocator('.addon-shell iframe');await frame.locator('.passage').waitFor();
    check('only the selected passage opens',await frame.locator('.chapters').count()===0&&await frame.locator('.passage').count()===1);
    check('the section heading appears once',await frame.getByRole('heading',{name:'What Is Databricks Unity Catalog?',exact:true}).count()===1);
    check('the section reader stays compact',await frame.locator('.passage-head h1').evaluate(node=>parseFloat(getComputedStyle(node).fontSize))<=36);
    const chapterCta=frame.locator('.chapter-link');check('open complete chapter is a prominent full-width action',await chapterCta.evaluate(node=>{const style=getComputedStyle(node);return node.getBoundingClientRect().height>=50&&node.getBoundingClientRect().width>400&&style.backgroundColor!=='rgba(0, 0, 0, 0)'}));
    check('passage state reaches the parent URL',/[?&]chapter=/.test(page.url())&&/[?&]section=/.test(page.url()));
    await frame.locator('html.theme-dark').waitFor();check('passage follows board theme',await frame.locator('html').getAttribute('class')==='theme-dark');
    const fullscreen=page.locator('.addon-fullscreen');await fullscreen.click();await page.waitForFunction(()=>{const shell=document.querySelector('.addon-shell.is-fullscreen');return shell&&shell.getBoundingClientRect().width>=innerWidth-1});check('full screen reading mode fills the viewport',await fullscreen.getAttribute('aria-pressed')==='true');
    check('full screen reading mode makes the background inert',await page.locator('body > :not(.addon-shell)').evaluateAll(nodes=>nodes.every(node=>node.inert))&&await page.locator('.addon-shell').getAttribute('aria-modal')==='true');
    await frame.locator('#content').press('Escape');await page.locator('.addon-shell.is-fullscreen').waitFor({state:'detached'});check('Escape exits full screen before closing',await page.locator('.addon-shell').count()===1);
    await chapterCta.click();await frame.locator('.chapter-view').waitFor();check('opening the complete chapter preserves the selected section',await frame.locator('.chapter-toc a[aria-current="location"]').count()===1);
    await frame.locator('#content').press('Escape');await page.locator('.addon-shell').waitFor({state:'detached'});check('a second Escape closes the add-on',true);
    await page.locator('.addon-context-link').first().getByRole('button',{name:'Open complete chapter'}).click();
    const chapterFrame=page.frameLocator('.addon-shell iframe');await chapterFrame.locator('.chapter-view').waitFor();
    check('open chapter renders the complete chapter',await chapterFrame.locator('.chapter-view h2').count()>1);
    check('the chapter provides section navigation',await chapterFrame.locator('.chapter-toc a').count()>3);
    check('the complete chapter includes its introduction',await chapterFrame.locator('.chapter-view > p').count()>0);
    check('reader navigation updates the parent URL',/[?&]bookView=chapter/.test(page.url())&&!/[?&]section=/.test(page.url()));
    await page.locator('.addon-fullscreen').click();check('the side chapter navigation is hidden while the top TOC is visible',await chapterFrame.locator('.chapter-side-toc').isHidden());
    const scrolledHeading=chapterFrame.locator('.chapter-view h2').nth(3),scrolledHeadingText=(await scrolledHeading.textContent()).trim();await scrolledHeading.evaluate(node=>node.scrollIntoView({block:'start'}));const sideToc=chapterFrame.locator('.chapter-side-toc');await sideToc.waitFor({state:'visible'});check('chapter navigation stays visible at the side and tracks the visible section',await sideToc.evaluate(node=>getComputedStyle(node).position==='fixed')&&(await sideToc.locator('a[aria-current="location"]').textContent()).trim()===scrolledHeadingText);
    check('the off-screen top TOC leaves keyboard navigation when the side TOC takes over',await chapterFrame.locator('.chapter-toc').evaluate(node=>node.inert&&node.getAttribute('aria-hidden')==='true')&&await sideToc.evaluate(node=>!node.inert&&node.getAttribute('aria-hidden')==='false'));
    check('the active side link stays visible without changing reading position',await sideToc.locator('a[aria-current="location"]').evaluate(link=>{const nav=link.closest('nav'),before=scrollY,linkBox=link.getBoundingClientRect(),navBox=nav.getBoundingClientRect();link.focus({preventScroll:true});return scrollY===before&&document.activeElement===link&&linkBox.top>=navBox.top&&linkBox.bottom<=navBox.bottom}));
    await page.reload({waitUntil:'networkidle'});await boardReady(page);const restoredFrame=page.frameLocator('.addon-shell iframe');await restoredFrame.locator('.chapter-view').waitFor();check('refresh restores the chapter view',await restoredFrame.locator('.chapter-toc').isVisible());
  }finally{await browser.close();await new Promise(resolve=>server.close(resolve))}
  if(checks.some(value=>!value))process.exitCode=1;
})().catch(error=>{console.error(error);process.exitCode=1});
